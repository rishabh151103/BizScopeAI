import asyncio
from fastapi import FastAPI,UploadFile,File,HTTPException,Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, StreamingResponse
from io import BytesIO
from pathlib import Path
import logging
import os
import sqlite3
from pydantic import BaseModel, Field
from typing import Literal
from plotly.utils import PlotlyJSONEncoder
from plotly.offline import get_plotlyjs
import json
from sqlalchemy import text
from sqlalchemy.orm import Session
from contextvars import ContextVar
from time import perf_counter
from uuid import uuid4
from .database import get_db, SessionLocal
from .db_models import Dataset, Investigation
from .investigation_service import InvestigationService
from .dataset_service import DatasetService
from .analysis_planner import (
    select_analyses,
    select_analyses_from_requirement
    )
from .pipeline import run_visualization
from .analytics_registry import ANALYTICS_REGISTRY
from .execution_resolver import resolve_execution_parameters
from .answer_grounding import (
    collect_analysis_results,
    serialize_grounded_context,
    is_analytical_question,
    select_relevant_analysis_results,
    format_deterministic_analytics_answer,
    answer_category_comparison,
)
from .schemas import (
    BusinessDiagnosis,
    InvestigationState,
    StateUpdate,
    ScopeCheck,
    ProblemClarity,
    EvidenceRequirement,
    EvidenceDecision
)

from .llm_client import (
    call_ollama,
    call_structured_ollama,
    call_text_ollama,
    OllamaCallError,
    OllamaTimeoutError,
    OllamaUnavailableError,
    GENERAL_MODEL,
    PLANNER_MODEL)
from .response_prompt import (
    build_response_messages,
    normalize_assistant_response,
    strip_visualization_placeholder,
)
from .prompts import (
    SYSTEM_MESSAGE,
    build_evidence_requirement_prompt,
    build_evidence_state_update_prompt,
    build_hypothesis_generation_prompt,
    build_scope_check_prompt,
    build_problem_clarity_prompt,
    build_new_information_state_prompt,
)
from .investigation_graph import invoke_chat_workflow, invoke_staged_investigation_graph


_investigation_service_context: ContextVar[InvestigationService | None] = (
    ContextVar("investigation_service", default=None)
)

_dataset_service_context: ContextVar[DatasetService | None] = (
    ContextVar("dataset_service", default=None)
)


def get_investigation_service() -> InvestigationService:
    service = _investigation_service_context.get()

    if service is None:
        raise RuntimeError(
            "InvestigationService is not configured for this request."
        )

    return service


def get_dataset_service() -> DatasetService:
    service = _dataset_service_context.get()

    if service is None:
        raise RuntimeError(
            "DatasetService is not configured for this request."
        )

    return service

app = FastAPI()
logger = logging.getLogger(__name__)


@app.middleware("http")
async def log_request_summary(request, call_next):
    """Log request timing and outcome without recording user supplied data."""
    request_id = uuid4().hex
    started = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        logger.info(
            "http_request request_id=%s method=%s path=%s status_code=%s duration_ms=%.1f",
            request_id,
            request.method,
            request.url.path,
            status_code,
            (perf_counter() - started) * 1000,
        )

try:
    MAX_UPLOAD_BYTES = max(
        1,
        int(os.getenv("BIZSCOPE_MAX_UPLOAD_MB", "50")),
    ) * 1024 * 1024
except ValueError as exc:
    raise RuntimeError("BIZSCOPE_MAX_UPLOAD_MB must be an integer.") from exc


@app.get("/health/live")
def health_live():
    """Process liveness probe; does not require external services."""
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    """Readiness probe that checks whether the configured database responds."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("Database readiness check failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable.",
        ) from exc
    return {"status": "ready"}


@app.get("/vendor/plotly.min.js")
def plotly_bundle():
    """Serve Plotly from the installed Python package; no CDN is required."""
    return Response(get_plotlyjs(), media_type="application/javascript")


class BranchMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message: str
    investigation_id: int | None = None
    dataset_id: int | None = None
    branch_context: list[BranchMessage] = Field(default_factory=list, max_length=16)



@app.post("/chat")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    investigation_service = InvestigationService(db)
    dataset_service = DatasetService(db)

    investigation_token = _investigation_service_context.set(
        investigation_service
    )
    dataset_token = _dataset_service_context.set(
        dataset_service
    )

    try:
        try:
            return process_message(
                request.message,
                investigation_id=request.investigation_id,
                dataset_id=request.dataset_id,
                branch_context=[turn.model_dump() for turn in request.branch_context],
                include_visualizations=True
            )
        except ValueError as e:
            if (
                request.investigation_id is not None
                and str(e) == (
                    f"Investigation with ID "
                    f"{request.investigation_id} not found."
                )
            ):
                raise HTTPException(
                    status_code=404,
                    detail=str(e)
                ) from e
            raise
        except OllamaTimeoutError as exc:
            logger.warning(
                "Chat request ended after Ollama timeout; model=%s timeout_seconds=%s",
                exc.model,
                exc.timeout_seconds,
            )
            raise HTTPException(
                status_code=504,
                detail=(
                    f"The local AI model {exc.model} did not respond within "
                    f"{exc.timeout_seconds} seconds. Check Ollama and retry."
                ),
                headers={"Retry-After": "5"},
            ) from exc
        except OllamaUnavailableError as exc:
            logger.warning(
                "Chat request failed because Ollama is unavailable; model=%s",
                exc.model,
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    "BizScopeAI cannot reach the local Ollama service. "
                    "Start or check Ollama, then retry."
                ),
            ) from exc
        except OllamaCallError as exc:
            logger.error(
                "Chat request failed in Ollama; error_type=%s",
                type(exc).__name__,
            )
            raise HTTPException(
                status_code=502,
                detail=(
                    "The local AI service could not complete this request. "
                    "Check the Ollama server log and retry."
                ),
            ) from exc
    finally:
        _dataset_service_context.reset(dataset_token)
        _investigation_service_context.reset(investigation_token)


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream the final Gemma response while analysis runs in a worker thread."""
    loop = asyncio.get_running_loop()
    events = asyncio.Queue()
    request_id = uuid4().hex

    def emit(event):
        try:
            loop.call_soon_threadsafe(events.put_nowait, event)
        except RuntimeError:
            # The browser may have disconnected and closed the event loop.
            pass

    def work():
        db = SessionLocal()
        investigation_token = _investigation_service_context.set(
            InvestigationService(db)
        )
        dataset_token = _dataset_service_context.set(DatasetService(db))
        try:
            emit({"type": "status", "message": "Reviewing the investigation…"})
            result = process_message(
                request.message,
                investigation_id=request.investigation_id,
                dataset_id=request.dataset_id,
                branch_context=[turn.model_dump() for turn in request.branch_context],
                include_visualizations=True,
                stream_callback=lambda text: emit({"type": "token", "text": text}),
                progress_callback=lambda message: emit(
                    {"type": "status", "message": message}
                ),
            )
            emit({"type": "done", "result": result})
        except ValueError as exc:
            status = 404 if (
                request.investigation_id is not None
                and str(exc) == (
                    f"Investigation with ID {request.investigation_id} not found."
                )
            ) else 400
            emit({"type": "error", "status": status, "detail": str(exc)})
        except OllamaTimeoutError as exc:
            emit({
                "type": "error",
                "status": 504,
                "detail": (
                    f"The local AI model {exc.model} did not respond within "
                    f"{exc.timeout_seconds} seconds. Check Ollama and retry."
                ),
            })
        except OllamaUnavailableError:
            emit({
                "type": "error",
                "status": 503,
                "detail": "BizScopeAI cannot reach Ollama. Start or check Ollama, then retry.",
            })
        except OllamaCallError:
            emit({
                "type": "error",
                "status": 502,
                "detail": "The local AI service could not complete this request. Check the Ollama server log and retry.",
            })
        except Exception:
            logger.exception(
                "Streaming chat request failed; request_id=%s",
                request_id,
            )
            emit({
                "type": "error",
                "status": 500,
                "detail": f"The chat request failed. Check the backend log (request {request_id}).",
            })
        finally:
            _dataset_service_context.reset(dataset_token)
            _investigation_service_context.reset(investigation_token)
            db.close()
            emit(None)

    worker_task = asyncio.create_task(asyncio.to_thread(work))

    async def event_stream():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(events.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                if event is None:
                    break
                yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
            await worker_task
        finally:
            if not worker_task.done():
                worker_task.cancel()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )



@app.post("/datasets/upload")
async def upload_dataset(file: UploadFile = File(...),
 db: Session = Depends(get_db)):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A file is required."
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported."
        )

    try:
        file_content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(file_content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=(
                    "The uploaded CSV exceeds the configured size limit "
                    f"of {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
                ),
            )
        if not file_content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded CSV is empty.",
            )

        uploaded_file = BytesIO(file_content)
        uploaded_file.name = file.filename

        request_dataset_service = DatasetService(db)

        dataset = request_dataset_service.ingest_dataset(uploaded_file)

        return {
            "dataset_id": dataset.id,
            "filename": dataset.filename,
            "rows": dataset.row_count,
            "columns": dataset.column_count,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            "Dataset ingestion failed; error_type=%s",
            type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail="Dataset ingestion failed. Check server logs for details.",
        ) from e


@app.get("/datasets")
def list_datasets(db: Session = Depends(get_db)):
    items = db.query(Dataset).order_by(Dataset.created_at.desc(), Dataset.id.desc()).limit(100).all()
    return {
        "datasets": [
            {
                "dataset_id": item.id,
                "filename": item.filename,
                "rows": item.row_count,
                "columns": item.column_count,
            }
            for item in items
        ]
    }


@app.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    item = db.get(Dataset, dataset_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return {
        "dataset_id": item.id,
        "filename": item.filename,
        "rows": item.row_count,
        "columns": item.column_count,
    }


def load_legacy_visualizations(investigation_id: int) -> dict[str, list]:
    """Read chart attachments created by the former Streamlit frontend."""
    history_path = Path(os.getenv(
        "BIZSCOPE_HISTORY_DB",
        str(Path(__file__).resolve().parents[1] / "frontend" / "bizscope_chat_history.sqlite3"),
    )).expanduser().resolve()
    if not history_path.is_file():
        return {}
    try:
        connection = sqlite3.connect(
            f"{history_path.as_uri()}?mode=ro",
            uri=True,
            timeout=2,
        )
        try:
            row = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='turn_visualizations'"
            ).fetchone()
            if not row:
                return {}
            rows = connection.execute(
                "SELECT assistant_message_index, visualizations_json "
                "FROM turn_visualizations WHERE investigation_id = ?",
                (investigation_id,),
            ).fetchall()
        finally:
            connection.close()
        return {
            str(index): json.loads(value)
            for index, value in rows
            if value
        }
    except (sqlite3.Error, ValueError, TypeError) as exc:
        logger.warning("Legacy chart cache unavailable; error_type=%s", type(exc).__name__)
        return {}

@app.get("/investigations/{investigation_id}")
def get_investigation(
    investigation_id: int,
    db: Session = Depends(get_db),
):
    service = InvestigationService(db)

    investigation = service.get_investigation(
        investigation_id
    )

    if investigation is None:
        raise HTTPException(
            status_code=404,
            detail=f"Investigation with ID {investigation_id} not found.",
        )

    state = service.load_state(investigation_id)
    messages = service.get_messages(investigation_id)
    evidence = service.get_evidence(investigation_id)
    analysis_runs = service.get_analysis_runs(investigation_id)

    return {
        "investigation_id": investigation.id,
        "problem": investigation.problem,
        "business_context": investigation.business_context,
        "current_focus": investigation.current_focus,
        "dataset_id": investigation.dataset_id,
        "state": state.model_dump(),
        "messages": [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in messages
        ],
        "evidence": [
            {
                "id": item.id,
                "content": item.content,
                "structured_data": item.structured_data,
                "analysis_run_id": item.analysis_run_id,
            }
            for item in evidence
        ],
        "analysis_runs": [
            {
                "id": run.id,
                "analysis_name": run.analysis_name,
                "status": run.status,
                "result_data": run.result_data,
            }
            for run in analysis_runs
        ],
        "visualizations_by_assistant_index": load_legacy_visualizations(investigation_id),
    }        


diagnosis_schema = BusinessDiagnosis.model_json_schema()
state_update_schema = StateUpdate.model_json_schema()
scope_check_schema = ScopeCheck.model_json_schema()
problem_clarity_schema = ProblemClarity.model_json_schema()

def validate_problem_clarity(clarity):
    if clarity.metric is None:
        return

    if not clarity.metric.strip():
        raise ValueError(
            "Metric cannot be an empty string."
        )



def plan_analysis_for_evidence_request(evidence_request):
    if not evidence_request or not evidence_request.strip():
        raise ValueError("Evidence request cannot be empty.")
    
    selection=select_analyses(evidence_request)

    if selection is None:
        raise ValueError(
            f"unable to create an analysis plan for evidence request:"
            f"{evidence_request}"
        )

    return selection

def execute_analysis_plan(
    investigation_id,
    df,
    analysis_plan,
    include_visualizations=True,
):
    execution_results = []

    for selection in analysis_plan.analyses:

        analysis_run = (
            get_investigation_service().execute_analysis_selection(
                investigation_id=investigation_id,
                df=df,
                selection=selection,
            )
        )

        visualization = None

        if include_visualizations:
            try:
                visualization = run_visualization(
                    analysis_name=analysis_run.analysis_name,
                    analysis_result=analysis_run.result_data,
                )
            except (KeyError, ValueError, TypeError):
                # Visualization failure must not invalidate a successful calculation.
                visualization = None

        execution_results.append(
            {
                "analysis_run": analysis_run,
                "visualization": visualization,
            }
        )

    return execution_results

def persist_analysis_evidence(
    investigation_id,
    analysis_run,
):
    content = (
        f"Analysis '{analysis_run.analysis_name}' produced "
        f"the following result: "
        f"{analysis_run.result_data}"
    )

    return get_investigation_service().add_evidence(
        investigation_id=investigation_id,
        content=content,
        structured_data=analysis_run.result_data,
        analysis_run_id=analysis_run.id,
    )

def build_evidence_context(
    investigation_id,
    question=None,
):
    evidence_items = get_investigation_service().get_evidence(
        investigation_id
    )

    if not evidence_items:
        return ""

    if question:
        runs = get_investigation_service().get_analysis_runs(investigation_id)
        selected_results = select_relevant_analysis_results(
            [
                {
                    "analysis_name": run.analysis_name,
                    "result": run.result_data,
                }
                for run in runs
                if run.status == "completed"
            ],
            question,
        )
        selected_names = {
            item.get("analysis_name") for item in selected_results
        }
        if selected_names:
            selected_run_ids = {
                run.id for run in runs if run.analysis_name in selected_names
            }
            evidence_items = [
                item
                for item in evidence_items
                if item.analysis_run_id is None
                or item.analysis_run_id in selected_run_ids
            ]

    context_parts = []

    # Keep active prompts focused on recent, persisted analysis outputs. The
    # full evidence history remains stored and available through the API.
    for evidence in evidence_items[-10:]:
        context_parts.append(
            f"Evidence:\n"
            f"{(evidence.content or '')[:6000]}\n"
        )

    return "\n".join(context_parts)


def format_unverified_hypotheses_response(state, limitations=None):
    """Render an initial investigation without implying any test has run."""
    lines = ["## Initial investigation framing"]
    if state.problem:
        lines.append(state.problem.strip())

    if state.confirmed_facts:
        lines.extend(["", "**What you have told me:**"])
        lines.extend(f"- {fact}" for fact in state.confirmed_facts)

    if state.hypotheses:
        lines.extend([
            "",
            "No analytical test has run yet. These are candidate explanations, not findings:",
        ])
        for index, hypothesis in enumerate(state.hypotheses, start=1):
            lines.extend(["", f"### Hypothesis {index} · {hypothesis.priority.title()} priority"])
            lines.append(
                f"**{hypothesis.statement.strip()}** — status: untested"
            )
            if hypothesis.basis.strip():
                lines.append(f"   Why it is worth considering: {hypothesis.basis.strip()}")
            if hypothesis.evidence_needed:
                tests = "; ".join(
                    item.strip()
                    for item in hypothesis.evidence_needed
                    if item and item.strip()
                )
                if tests:
                    lines.append(f"   Evidence that could test it: {tests}")
    else:
        lines.extend([
            "",
            "There is not enough measured evidence to rank causal explanations yet.",
        ])

    if limitations:
        lines.extend(["", "**Current limitation:**"])
        lines.extend(f"- {item}" for item in limitations)
    else:
        lines.extend([
            "",
            "The cause remains uncertain until a relevant analysis tests these possibilities.",
        ])
    return "\n".join(lines)


def format_hypothesis_status_response(state):
    """Present persisted hypothesis states and their current evidence basis."""
    if not state.hypotheses:
        return "No hypotheses are currently being tracked in this investigation."

    status_labels = {
        "active": "Unresolved",
        "supported": "Supported by evidence",
        "weakened": "Weakened by evidence",
        "rejected": "Rejected by evidence",
        "inconclusive": "Inconclusive",
        "superseded": "Superseded",
    }
    lines = ["### Hypothesis status after this analysis"]
    priority_order = {"high": 0, "medium": 1, "low": 2}
    hypotheses = sorted(
        state.hypotheses,
        key=lambda item: (
            priority_order.get(item.priority, 3),
            item.id,
        ),
    )
    for index, hypothesis in enumerate(hypotheses, start=1):
        status = status_labels.get(hypothesis.status, "Unresolved")
        lines.append(
            f"**Hypothesis {index} · {status} · "
            f"{hypothesis.priority.title()} priority:** "
            f"{hypothesis.statement.strip()}"
        )
        if hypothesis.basis.strip():
            basis_label = (
                "Reason to keep investigating"
                if hypothesis.status == "active"
                else "Evidence update"
            )
            lines.append(f"  {basis_label}: {hypothesis.basis.strip()}")
    return "\n".join(lines)


def _regional_result_rows(analysis_results):
    for item in reversed(analysis_results or []):
        if item.get("analysis_name") != "regional_performance":
            continue
        result = item.get("result")
        if isinstance(result, dict):
            rows = result.get("regional_analysis")
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def _regional_measured_summary(rows):
    profits = [
        (row.get("region"), row.get("total_profit"))
        for row in rows
        if isinstance(row.get("region"), str)
        and isinstance(row.get("total_profit"), (int, float))
    ]
    margins = [
        (row.get("region"), row.get("average_profit_margin"))
        for row in rows
        if isinstance(row.get("region"), str)
        and isinstance(row.get("average_profit_margin"), (int, float))
    ]
    parts = []
    if len(profits) >= 2:
        profits.sort(key=lambda pair: pair[1], reverse=True)
        lead, runner_up = profits[:2]
        parts.append(
            f"{lead[0]} leads total profit at ${lead[1]:,.2f}; "
            f"{runner_up[0]} is next at ${runner_up[1]:,.2f}, "
            f"a total-profit gap of ${abs(lead[1] - runner_up[1]):,.2f}."
        )
    if margins:
        low = min(margins, key=lambda pair: pair[1])
        high = max(margins, key=lambda pair: pair[1])
        parts.append(
            f"Average row-level profit margin ranges from {low[0]} "
            f"({low[1]:.2f}%) to {high[0]} ({high[1]:.2f}%)."
        )
    return " ".join(parts)


def format_regional_hypothesis_review(state, analysis_results):
    """Review saved hypotheses without letting a follow-up change their status."""
    rows = _regional_result_rows(analysis_results)
    if not rows:
        return None
    hypotheses = sorted(
        state.hypotheses,
        key=lambda item: (
            {"high": 0, "medium": 1, "low": 2}.get(item.priority, 3),
            item.id,
        ),
    )
    if not hypotheses:
        return None

    status_labels = {
        "active": "Unresolved",
        "supported": "Supported",
        "weakened": "Weakened",
        "rejected": "Rejected",
        "inconclusive": "Inconclusive",
        "superseded": "Superseded",
    }
    lines = [
        "The regional analysis measures revenue, profit, units, and average "
        "profit margin by region. It shows outcomes, but does not establish "
        "their causes.",
        "",
        _regional_measured_summary(rows),
        "",
        "**Hypothesis review**",
    ]
    for index, hypothesis in enumerate(hypotheses, start=1):
        text = hypothesis.statement.casefold()
        if "product" in text or "mix" in text:
            evidence_note = (
                "Unresolved: the result is grouped by region, not by product "
                "within each region, so it does not test product mix."
            )
        elif any(term in text for term in ("cost", "expense", "operational")):
            evidence_note = (
                "Unresolved: this result contains no regional cost or expense "
                "measure."
            )
        elif any(term in text for term in ("pricing", "price", "discount")):
            evidence_note = (
                "Unresolved: this result contains no regional price or discount "
                "breakdown."
            )
        else:
            evidence_note = (
                "The result is descriptive and does not establish this "
                "hypothesis's proposed cause."
            )
        status = status_labels.get(hypothesis.status, "Unresolved")
        lines.append(
            f"**Hypothesis {index} · {status} · "
            f"{hypothesis.priority.title()} priority:** "
            f"{hypothesis.statement.strip()}"
        )
        lines.append(f"   {evidence_note}")
    return "\n".join(line for line in lines if line is not None)


def format_regional_business_takeaway(analysis_results):
    rows = _regional_result_rows(analysis_results)
    if len(rows) < 2:
        return None
    summary = _regional_measured_summary(rows)
    return (
        f"{summary} These are descriptive results; they do not show why the "
        "regions differ or establish statistical significance. The most useful "
        "next question is whether product-level results within each region "
        "explain the margin differences. This regional summary cannot answer "
        "that by itself."
    )


def format_regional_analysis_recommendation(question, available_fields):
    text = (question or "").casefold()
    if not any(term in text for term in ("region", "regional")):
        return None
    fields = set(available_fields or [])
    required = {"region", "revenue", "profit"}
    missing = sorted(required - fields)
    if missing:
        return (
            "The dataset cannot yet support the regional performance comparison "
            "because these required fields are not mapped: "
            + ", ".join(missing)
            + "."
        )
    return (
        "The dataset can test where regional outcomes differ: the registered "
        "regional analysis compares total revenue, total profit, units sold, "
        "and average row-level profit margin by region. The most useful first "
        "test is to compare and rank those measured outcomes by region. This "
        "can show where profitability differs, but it cannot establish whether "
        "costs, product mix, or pricing caused the differences. The regional "
        "tool does not calculate statistical significance."
    )



def decide_followup_evidence(
    investigation_id: int,
    original_question: str,
) -> EvidenceDecision:
    """
    Decide whether another distinct analytics pass can materially
    resolve an active hypothesis.

    This is intentionally hypothesis-driven: descriptive requests
    without active hypotheses finish after their requested analysis.
    """
    # For descriptive requests, the initial analysis is the requested work.
    # Do not let speculative hypotheses create unrelated follow-up requests.

    service = get_investigation_service()
    state = service.load_state(investigation_id)

    active_hypotheses = [
        hypothesis.model_dump()
        for hypothesis in state.hypotheses
        if hypothesis.status in {"active", "weakened", "inconclusive"}
    ]

    if not active_hypotheses:
        return EvidenceDecision(
            needs_new_evidence=False,
            evidence_request=None,
        )

    # A direct request to run a specific analysis gets one requested cycle.
    # Its results still update the hypotheses; do not spend another model call
    # on an optional automatic follow-up decision.
    if is_explicit_analysis_request(original_question):
        return EvidenceDecision(
            needs_new_evidence=False,
            evidence_request=None,
        )

    evidence_context = build_evidence_context(investigation_id)
    runs = service.get_analysis_runs(investigation_id)
    prior_analyses = [
        {
            "analysis_name": run.analysis_name,
            "requirement": run.requirement,
            "status": run.status,
        }
        for run in runs
    ]

    decision_context = f"""
ORIGINAL BUSINESS QUESTION:
{original_question}

CURRENT INVESTIGATION STATE:
{state.model_dump_json(indent=2)}

UNRESOLVED HYPOTHESES THAT MAY NEED FURTHER TESTING:
{json.dumps(active_hypotheses, indent=2, default=str)}

ANALYSES ALREADY EXECUTED:
{json.dumps(prior_analyses, indent=2, default=str)}

EXISTING ANALYTICAL EVIDENCE:
{evidence_context or "No analytical evidence stored yet."}

TASK:
Decide whether one more distinct calculation from the existing dataset
would materially help test an active hypothesis or answer the original
business question.

Set needs_new_evidence=false when:
- the active hypotheses have been adequately tested with available evidence;
- no relevant, unexecuted analysis is available;
- another analysis would repeat an existing analysis with the same requirement;
- the remaining question cannot be answered from the available dataset;
- the evidence is insufficient and the next step requires user-provided information.

Set needs_new_evidence=true only when a specific additional calculation can
meaningfully distinguish between active hypotheses or resolve a material
uncertainty. If true, evidence_request must describe ONE concrete calculation.

For diagnostic questions, use active hypotheses and their evidence_needed fields
to choose a discriminating calculation, not a generic repeat of the original
summary. Prefer a test that can support one hypothesis while weakening another.
If existing results already have the required metric at the required granularity,
do not request it again. If the dataset lacks the necessary fields, stop rather
than repeatedly requesting an impossible calculation.

Do not request external data or ask the user to upload the same dataset again.
Do not repeat an analysis and requirement already listed above.
Do not treat correlation or temporal overlap as proof of causation.
Do not invent numerical facts.
"""

    data = {
        "messages": [
            SYSTEM_MESSAGE,
            {"role": "user", "content": decision_context},
        ],
        "format": EvidenceDecision.model_json_schema(),
        "stream": False,
    }

    try:
        decision = call_structured_ollama(
            data,
            GENERAL_MODEL,
            EvidenceDecision,
        )
    except OllamaCallError as exc:
        # The first analysis and hypothesis refresh are already persisted.
        # Failure of the optional next-test decision should not discard them.
        logger.warning(
            "Follow-up evidence decision stopped; error_type=%s",
            type(exc).__name__,
        )
        return EvidenceDecision(
            needs_new_evidence=False,
            evidence_request=None,
        )

    if not decision.needs_new_evidence or not (
        decision.evidence_request and decision.evidence_request.strip()
    ):
        return EvidenceDecision(
            needs_new_evidence=False,
            evidence_request=None,
        )

    return decision


@app.get("/investigations")
def list_investigations(db: Session = Depends(get_db)):
    items = (
        db.query(Investigation)
        .order_by(Investigation.updated_at.desc(), Investigation.id.desc())
        .limit(100)
        .all()
    )
    service = InvestigationService(db)
    conversations = []
    for item in items:
        messages = service.get_messages(item.id)
        first_user_message = next(
            (message.content for message in messages if message.role == "user"),
            item.problem,
        )
        conversations.append({
            "investigation_id": item.id,
            "title": first_user_message[:90] or "Business investigation",
            "dataset_id": item.dataset_id,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        })
    return {"conversations": conversations}


@app.delete("/investigations/{investigation_id}")
def delete_investigation(investigation_id: int, db: Session = Depends(get_db)):
    investigation = db.get(Investigation, investigation_id)
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    db.delete(investigation)
    db.commit()
    return {"deleted": True, "investigation_id": investigation_id}

def update_state_from_evidence(
    investigation_id,
    evidence_context,
):
    investigation_state = get_investigation_service().load_state(
        investigation_id
    )

    state_context = build_evidence_state_update_prompt(
        investigation_state, evidence_context
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You update a business investigation from verified analytics. "
                "Return only valid JSON matching the supplied StateUpdate schema. "
                "Be concise and preserve uncertainty."
            ),
        },
        {
            "role": "user",
            "content": state_context,
        },
    ]

    data = {
        "messages": messages,
        "format": StateUpdate.model_json_schema(),
        "stream": False,
        "options": {
            "num_ctx": 4096,
            "num_predict": 512,
        },
    }

    return call_structured_ollama(
        data,
        GENERAL_MODEL,
        StateUpdate,
        max_retries=0,
    )

def apply_evidence_state_update(
    investigation_id,
    state_update,
):
    investigation_service = get_investigation_service()

    try:
        investigation_state = investigation_service.load_state(
            investigation_id
        )

        existing_hypotheses_ids = {
            hypothesis.id
            for hypothesis in investigation_state.hypotheses
        }

        state_update.hypotheses_updates = [
            update
            for update in state_update.hypotheses_updates
            if update.hypotheses_id in existing_hypotheses_ids
        ]

        investigation_service.apply_state_update(
            investigation_id,
            state_update,
        )

        investigation_service.commit()

        return state_update

    except Exception:
        investigation_service.rollback()
        raise

def process_evidence_update(
    investigation_id,
    evidence_context,
):
    try:
        state_update = update_state_from_evidence(
            investigation_id=investigation_id,
            evidence_context=evidence_context,
        )
    except OllamaCallError as exc:
        # The numerical result is committed already. Preserve it and let the
        # response path show measured values even if this optional state refresh
        # fails; the caller will stop before asking for another analysis cycle.
        logger.warning(
            "Evidence hypothesis update unavailable; error_type=%s",
            type(exc).__name__,
        )
        return None
    except RuntimeError as exc:
        # The analytics result is already saved. A failed secondary state
        # summary must not turn a successful calculation into HTTP 500.
        logger.info(
            "Evidence hypothesis update skipped; error_type=%s",
            type(exc).__name__,
        )
        return None

    try:
        state_update.new_facts=[]

        apply_evidence_state_update(
            investigation_id=investigation_id,
            state_update=state_update,
        )

        return state_update
    
    except Exception:
        get_investigation_service().rollback()
        raise


def build_evidence_requirement(evidence_request: str) -> EvidenceRequirement:
    """
    Use Qwen to structure an already-identified evidence request.

    Gemma has already determined that additional evidence is needed.
    Qwen only structures that requirement for downstream analysis.

    Qwen does not:
    - decide whether evidence is needed
    - update hypotheses
    - update InvestigationState
    - generate the final response
    - calculate business metrics
    """

    if not evidence_request or not evidence_request.strip():
        raise ValueError("Evidence request cannot be empty")

    prompt = build_evidence_requirement_prompt(evidence_request)

    data={
        "messages":[
            {
                "role":"user",
                "content":prompt
            }
        ],
        "format":EvidenceRequirement.model_json_schema(),
        "stream":False,
        "think":False
    }

    result=call_structured_ollama(
        data,
        PLANNER_MODEL,
        EvidenceRequirement
    )
    return result

def resolve_analysis_dataset_id(
    investigation_id,
    dataset_id=None,
):
    if dataset_id is not None:
        return dataset_id

    investigation_state = get_investigation_service().load_state(
        investigation_id
    )

    return investigation_state.dataset_id

def serialize_visualization(visualization):
    """
    Convert a Plotly visualization into a JSON-safe object.
    """

    if visualization is None:
        return None

    return json.loads(
        json.dumps(
            visualization,
            cls=PlotlyJSONEncoder,
        )
    )

def is_diagnostic_question(question: str) -> bool:
    """Detect requests to investigate causes or business drivers."""
    text = (question or "").casefold().strip()
    markers = (
        "why ", "why is ", "why are ", "why did ", "why does ",
        "cause", "causes", "root cause", "reason", "reasons",
        "driver", "drivers", "what explains", "what could explain",
        "what might explain", "explain why", "explanation",
        "explanations", "possible cause", "possible causes",
        "testable explanation", "testable explanations",
    )
    return any(marker in text for marker in markers)


def is_hypothesis_update_request(question: str) -> bool:
    text = " ".join((question or "").casefold().split())
    return any(marker in text for marker in (
        "update the investigation hypotheses",
        "update investigation hypotheses",
        "update the hypotheses",
        "update hypotheses",
        "hypothesis status",
        "status of each hypothesis",
    ))


def is_takeaway_followup(question: str) -> bool:
    text = " ".join((question or "").casefold().split())
    return any(marker in text for marker in (
        "what should i take away",
        "what should we take away",
        "main takeaway",
        "main take away",
        "summarize the takeaway",
        "summarise the takeaway",
    ))


def is_conversational_evidence_followup(question: str) -> bool:
    """
    Fast deterministic routing guard for follow-ups that should use existing
    evidence. This intentionally does not classify explicit requests for new
    calculations, charts, forecasts, correlations, or breakdowns as conversational.
    """
    text = " ".join((question or "").casefold().split())

    explicit_new_analysis = (
        "calculate", "recalculate", "compute", "run an analysis",
        "run analysis", "run only the most useful", "run the most useful analysis",
        "run the regional", "run regional", "run the monthly", "run monthly",
        "run the category", "run category", "run the product", "run product",
        "run the customer", "run customer", "run the analysis of",
        "run only the available analysis", "analyze ", "analyse ", "break down",
        "drill down", "segment by", "group by", "correlation",
        "correlate", "forecast", "predict", "create a chart",
        "make a chart", "plot ", "show the trend", "compare by ",
        "compare across ", "calculate the contribution",
    )
    if any(term in text for term in explicit_new_analysis):
        return False

    conversational_intents = (
        "what does this mean", "what does that mean", "what does it mean",
        "what does ", "what do ",
        "explain this", "explain that", "explain the result",
        "explain the chart", "interpret this", "interpret that",
        "what can we conclude", "what does this tell us",
        "what remains uncertain", "what is still uncertain",
        "how should i interpret", "summarize this", "summarise this",
        "can you explain", "tell me more about",
        "what can we conclude", "what can i conclude", "what remains",
        "give me two testable explanations", "give me testable explanations",
        "give me plausible explanations", "possible explanations",
        "summarize what", "summarise what", "takeaway", "take away",
        "what should i take away", "summarize the case", "summarise the case",
        "update the investigation hypotheses", "update investigation hypotheses",
        "update the hypotheses", "update hypotheses", "hypothesis status",
        "status of each hypothesis",
    )
    return (
        is_diagnostic_question(text)
        or any(term in text for term in conversational_intents)
    )


def is_analysis_deferred_request(question: str) -> bool:
    """Identify clear instructions to discuss a test without running it yet."""
    text = " ".join((question or "").casefold().replace("’", "'").split())
    markers = (
        "don't run", "do not run", "dont run",
        "don't calculate", "do not calculate", "dont calculate",
        "don't analyze", "do not analyze", "don't analyse", "do not analyse",
        "without running", "before running", "before calculating",
        "before we calculate", "before any calculations", "not run yet",
        "haven't run it yet", "have not run it yet",
    )
    return any(marker in text for marker in markers)


def explicit_metric_signal(question: str) -> str | None:
    """Return an explicitly named business metric, without another model call."""
    text = (question or "").casefold()
    metrics = (
        "average order value", "profit margin", "profitability", "revenue",
        "sales", "profit", "margin", "discount", "orders", "order count",
        "order", "customers", "customer", "units", "quantity", "cost",
        "retention", "churn", "marketing spend",
    )
    return next((metric for metric in metrics if metric in text), None)


def existing_evidence_can_support_followup(
    question: str,
    analysis_results: list,
) -> bool:
    """Route conversational turns with saved evidence directly to Gemma.

    Numerical requests are intentionally left to the evidence decision prompt,
    which can compare the requested metric and granularity with all registered
    tools and saved results instead of relying on domain-specific keywords.
    """
    return bool(analysis_results) and is_conversational_evidence_followup(question)


def is_explicit_analysis_request(question: str) -> bool:
    text = " ".join((question or "").casefold().split())
    markers = (
        "calculate", "recalculate", "compute", "break down", "breakdown",
        "run the regional", "run regional", "run the monthly", "run monthly",
        "run the category", "run category", "run the product", "run product",
        "run the customer", "run customer", "run the analysis of",
        "compare ", "comparison of", "compare across ", "compare by ",
        "drill down", "by discount", "discount level", "discount band",
        "group by", "segment by", "forecast", "predict", "correlation",
        "run the first analysis", "run first analysis", "run the analysis",
        "run a calculation", "run the calculation",
        "run only the most useful", "run the most useful analysis",
        "run only the available analysis", "run an analysis", "run analysis",
        "plot ", "create a chart", "make a chart", "show the trend",
        "over time", "by month", "by region", "by product",
    )
    return any(marker in text for marker in markers)


def requests_visualization(question: str) -> bool:
    """Only build a chart when the user explicitly asks to see one."""
    text = " ".join((question or "").casefold().split())
    markers = (
        "chart", "plot", "graph", "visualize", "visualise",
        "visualization", "visualisation", "show me visually",
    )
    return any(marker in text for marker in markers)


def generate_diagnostic_hypotheses(
    investigation_id: int,
    question: str,
    analysis_results: list[dict],
):
    """Seed up to three ranked, testable hypotheses from verified evidence."""
    service = get_investigation_service()
    state = service.load_state(investigation_id)
    unresolved = [
        hypothesis
        for hypothesis in state.hypotheses
        if hypothesis.status in {"active", "weakened", "inconclusive"}
    ]
    if unresolved:
        return state

    results_context = serialize_grounded_context(
        analysis_results,
        question=question,
    )
    context = build_hypothesis_generation_prompt(
        state.model_dump_json(indent=2),
        results_context,
        question,
    )
    data = {
        "messages": [
            SYSTEM_MESSAGE,
            {"role": "user", "content": context},
        ],
        "format": StateUpdate.model_json_schema(),
        "stream": False,
    }
    update = call_structured_ollama(data, GENERAL_MODEL, StateUpdate)
    update.new_facts = []
    update.hypotheses_updates = []
    update.new_evidence_needed = []
    update.new_hypotheses = update.new_hypotheses[:3]
    for hypothesis in update.new_hypotheses:
        # Newly proposed explanations have not been tested by this request.
        hypothesis.status = "active"
    if update.new_hypotheses:
        update.current_focus = "Prioritize tests that distinguish the active explanations."
        service.apply_state_update(investigation_id, update)
        service.commit()
        return service.load_state(investigation_id)
    return state


def _process_message_v2(
    user_input,
    investigation_id=None,
    dataset_id=None,
    branch_context=None,
    include_visualizations=False,
    stream_callback=None,
    progress_callback=None,
):
    # ---------------------------------------------------------
    # Load the Requested Investigation 
    # ---------------------------------------------------------

    is_new_investigation = investigation_id is None
    investigation_started=investigation_id is not None
    current_investigation_id=investigation_id
    branch_context = [
        {
            "role": item.get("role"),
            "content": str(item.get("content", ""))[:2000],
        }
        for item in (branch_context or [])[-16:]
        if isinstance(item, dict)
        and item.get("role") in {"user", "assistant"}
        and str(item.get("content", "")).strip()
    ]
    branch_context_text = json.dumps(
        branch_context,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    if progress_callback:
        progress_callback("Reviewing the investigation and available evidence…")

    investigation_state=InvestigationState(
        problem="",
        business_context="",
        confirmed_facts=[],
        hypotheses=[],
        evidence_needed=[],
        current_focus="",
        investigation_history=[]
    )
    existing_relevant_visualization = False

    if investigation_id is not None:
        investigation= get_investigation_service().get_investigation(
            investigation_id
        )

        if investigation is None:
            raise ValueError(
                f"Investigation with ID {investigation_id} not found."
            )

        investigation_state = get_investigation_service().load_state(
            investigation_id
        )

        # Conversational follow-ups do not need to repeat scope, state-update,
        # and evidence-decision model calls. A clear "don't run it yet" request
        # uses this path even when no analysis has been saved yet.
        existing_results = collect_analysis_results(
            get_investigation_service(),
            investigation_id,
        )
        existing_relevant_visualization = (
            requests_visualization(user_input)
            and bool(
                select_relevant_analysis_results(
                    existing_results,
                    user_input,
                )
            )
        )
        conversational_followup = (
            is_analysis_deferred_request(user_input)
            or existing_evidence_can_support_followup(
                user_input,
                existing_results,
            )
        )
        grounded_regional_followup = bool(existing_results) and (
            is_hypothesis_update_request(user_input)
            or is_takeaway_followup(user_input)
        )
        if (
            not requests_visualization(user_input)
            and (conversational_followup or grounded_regional_followup)
        ):
            if is_diagnostic_question(user_input) and existing_results:
                investigation_state = generate_diagnostic_hypotheses(
                    investigation_id,
                    user_input,
                    existing_results,
                )
            evidence_context = build_evidence_context(
                investigation_id,
                question=user_input,
            )
            if not evidence_context:
                evidence_context = (
                    "No verified numerical analysis has been run in this "
                    "investigation yet."
                )

            context_dataset_id = investigation_state.dataset_id or dataset_id
            available_fields = (
                sorted(get_dataset_service().get_available_analysis_columns(context_dataset_id))
                if context_dataset_id is not None
                else []
            )
            logger.info(
                "Model route=conversation_only model=%s stored_analysis_count=%s",
                GENERAL_MODEL,
                len(existing_results),
            )

            # Persist the user turn before the model call so its context survives
            # a timeout and is available if they continue the conversation.
            get_investigation_service().add_message(
                investigation_id,
                role="user",
                content=user_input,
            )
            get_investigation_service().commit()

            stored_messages = get_investigation_service().get_messages(
                investigation_id
            )
            followup_response = None
            if is_analysis_deferred_request(user_input):
                followup_response = format_regional_analysis_recommendation(
                    user_input,
                    available_fields,
                )
            if is_hypothesis_update_request(user_input):
                followup_response = format_regional_hypothesis_review(
                    investigation_state,
                    existing_results,
                )
                if followup_response is not None:
                    logger.info(
                        "Grounded regional follow-up selected kind=hypothesis_review"
                    )
            if followup_response is None and is_takeaway_followup(user_input):
                followup_response = format_regional_business_takeaway(
                    existing_results
                )
                if followup_response is not None:
                    logger.info(
                        "Grounded regional follow-up selected kind=business_takeaway"
                    )

            if followup_response is None:
                grounded_results = serialize_grounded_context(
                    existing_results,
                    question=user_input,
                )
                followup_response = normalize_assistant_response(call_text_ollama(
                    {
                        "messages": build_response_messages(
                            latest_question=user_input,
                            state=investigation_state,
                            recent_messages=stored_messages,
                            evidence_context=evidence_context,
                            structured_results=grounded_results,
                            available_dataset_fields=available_fields,
                        ),
                        "stream": False,
                    },
                    GENERAL_MODEL,
                    on_token=stream_callback,
                ))
            elif stream_callback:
                for offset in range(0, len(followup_response), 160):
                    stream_callback(followup_response[offset:offset + 48])

            get_investigation_service().add_message(
                investigation_id,
                role="assistant",
                content=followup_response,
            )
            get_investigation_service().commit()

            if include_visualizations:
                return {
                    "response": followup_response,
                    "investigation_id": investigation_id,
                    "visualizations": [],
                    "analysis_cycles_completed": 0,
                    "analysis_cycle_limit": 0,
                }
            return followup_response

    context_dataset_id = dataset_id or investigation_state.dataset_id
    available_dataset_columns_for_context = (
        get_dataset_service().get_available_analysis_columns(context_dataset_id)
        if context_dataset_id is not None
        else set()
    )

    # =========================================================
    # 1. BUSINESS SCOPE CHECK
    # =========================================================

    scope_messages = [
        SYSTEM_MESSAGE,
        {
            "role": "user",
            "content": build_scope_check_prompt(
                investigation_state.problem if investigation_started else "No active investigation",
                branch_context_text,
                user_input,
            ),
        },
    ]

    data = {
        "messages": scope_messages,
        "format": scope_check_schema,
        "stream": False,
    }

    if investigation_started and (
        is_explicit_analysis_request(user_input)
        or is_analytical_question(user_input)
    ):
        # A clearly analytical follow-up inside an active investigation is
        # already in scope. Avoid spending a Gemma call to classify it again.
        scope_check = ScopeCheck(is_business_related=True)
        logger.info("Business scope check skipped for analytical follow-up")
    elif dataset_id is not None and is_analytical_question(user_input):
        # A dataset-focused request that names business metrics is already
        # scoped; another Gemma classification call only adds latency.
        scope_check = ScopeCheck(is_business_related=True)
        logger.info("Business scope check skipped for dataset-focused request")
    else:
        scope_check = call_structured_ollama(
            data,
            GENERAL_MODEL,
            ScopeCheck,
        )

    if not scope_check.is_business_related:
        response_text=(
            "Sorry, I'm designed for business-related "
            "queries and decision support rather than general-purpose "
            "questions. If you have a business problem you'd like to "
            "investigate, feel free to ask me."
        )

        if include_visualizations:
            return {
                "response": response_text,
                "investigation_id": current_investigation_id,
                "visualizations": []
            }
        
        return response_text

    # =========================================================
    # 2. PROBLEM CLARITY CHECK
    # =========================================================

    clarity_messages = [
        {
            "role": "system",
            "content": build_problem_clarity_prompt(user_input),
        }
    ]

    data = {
        "messages": clarity_messages,
        "format": problem_clarity_schema,
        "stream": False
    }

    if investigation_started:
        # Clarity is only used to decide whether a new investigation needs a
        # metric clarification. Existing investigations already have that
        # context, so this model call cannot affect the subsequent branch.
        clarity = ProblemClarity(
            problem=investigation_state.problem,
            metric=None,
            time_period=None,
            clarification_needed="",
        )
    elif explicit_metric_signal(user_input):
        metric_signal = explicit_metric_signal(user_input)
        clarity = ProblemClarity(
            problem=user_input,
            metric=metric_signal,
            time_period=None,
            clarification_needed="",
        )
        logger.info("Problem clarity check skipped for explicit metric")
    else:
        clarity = call_structured_ollama(
            data,
            GENERAL_MODEL,
            ProblemClarity,
            validator=validate_problem_clarity,
        )

    if not investigation_started and not clarity.metric:
        if not clarity.clarification_needed.strip():
            response_text=(
                "Which business metric are you referring to? For example, is it "
                "revenue, sales, profit, customers, orders, "
                "or something else?"
            )
        else:
            response_text=clarity.clarification_needed

        if include_visualizations:
            return {
                "response": response_text,
                "investigation_id": current_investigation_id,
                "visualizations": []
            }        

        return response_text

    # =========================================================
    # 3. INITIAL INVESTIGATION
    # =========================================================
    
    state_update=None

    if not investigation_started:


        diagnosis_context = f"""
USER'S REQUEST:

{user_input}

PRIOR CONVERSATION CONTEXT (if provided):
{branch_context_text}

Interpret the current request using this earlier context when it resolves
references. Do not treat earlier assistant interpretations as confirmed facts.

AVAILABLE DATASET FIELDS:
{", ".join(sorted(available_dataset_columns_for_context)) or "No dataset fields are available."}

ANALYSIS STATUS:
No analytical result has been run for this new investigation. The user's
description of performance is a reported impression, not a measured finding.
Do not say that a hypothesis is tested or that the dataset shows an outcome.

TASK:
Create an initial business investigation record that accurately
represents the user's request.

PROBLEM SUMMARY:
Describe the business question or problem without adding facts
that the user has not provided.

CONFIRMED FACTS:
Include only facts explicitly stated by the user.
Do not treat assumptions or general business knowledge as facts.

HYPOTHESES:
First determine whether the request actually requires a hypothesis.

- For descriptive tasks such as calculating totals, comparing
  categories, ranking products, or summarizing trends, do not
  invent a causal or explanatory hypothesis.
- For diagnostic tasks asking why something happened, generate up to
  three plausible, specific, testable hypotheses when facts or analytical
  results identify an outcome that needs explaining.
- For each hypothesis, state a plausible mechanism, why the known evidence
  makes it worth testing, and the exact measurable evidence that could support
  or weaken it. Prefer tests possible with the uploaded dataset.
- Make each proposed test use fields listed above. If the needed field is absent,
  say that the hypothesis requires external data; do not imply it can be tested
  from this dataset.
- Rank priority as high, medium, or low using business relevance and testability;
  never invent a probability or confidence percentage.
- Do not claim any hypothesis is a finding until evidence tests it.
- Never justify a hypothesis merely by saying it is common in business,
  logically possible, or a typical industry pattern.
- Do not assume that a problem exists just because the user
  asks for an analysis.
- If no justified hypothesis can be formed from the available
  information, return an empty hypotheses list.
- Clearly distinguish a hypothesis from a confirmed fact.

EVIDENCE:
Identify the information needed to answer the user's actual
question. Do not claim that evidence has already been collected
when it has not.

CONCLUSION:
Summarize what is currently known and what the requested analysis
needs to establish. Do not present an unverified result as fact.

Return a structured BusinessDiagnosis matching the required schema.
"""

        data = {
            "messages": [
                SYSTEM_MESSAGE,
                {
                    "role": "user",
                    "content": diagnosis_context
                }
            ],
            "format": diagnosis_schema,
            "stream": False
        }

        diagnosis = call_structured_ollama(
            data,
            GENERAL_MODEL,
            BusinessDiagnosis,
        )

        # A fresh investigation has no completed analysis runs. Treat every
        # initial explanation as active/untested even if the model returns a
        # stronger status in its structured output.
        for hypothesis in diagnosis.hypotheses:
            hypothesis.status = "active"

        
        if not is_diagnostic_question(user_input):
            diagnosis.hypotheses = []


        investigation = get_investigation_service().create_initial_state(
            diagnosis,
            dataset_id=dataset_id
        )

        current_investigation_id = investigation.id

        for prior_turn in branch_context:
            get_investigation_service().add_message(
                current_investigation_id,
                role=prior_turn["role"],
                content=prior_turn["content"],
            )

        get_investigation_service().add_message(
            current_investigation_id,
            role="user",
            content=user_input
        )

        get_investigation_service().commit()

        investigation_state = get_investigation_service().load_state(
            current_investigation_id
        )

        investigation_started = True

 

    # =========================================================
    # 4. EXISTING INVESTIGATION — UPDATE STATE
    # =========================================================
    
    elif existing_relevant_visualization:
        # Reusing a saved result for a chart does not change investigation
        # facts or hypothesis status.
        state_update = None
        get_investigation_service().add_message(
            current_investigation_id,
            role="user",
            content=user_input,
        )
        get_investigation_service().commit()
        logger.info("Pre-visualization state update skipped for reusable evidence")

    elif is_explicit_analysis_request(user_input):
        # Direct analytical requests update focus after the result is verified.
        # Avoid a pre-analysis Gemma call that rewrites state before evidence
        # exists; the evidence update later will revise tested hypotheses.
        state_update = None
        get_investigation_service().add_message(
            current_investigation_id,
            role="user",
            content=user_input,
        )
        get_investigation_service().commit()
        logger.info("Pre-analysis state update skipped for direct analysis request")
    else:
        # Persist every follow-up user message. Previously only the initial
        # message was stored, so reopened conversations lost later turns.
        get_investigation_service().add_message(
            current_investigation_id,
            role="user",
            content=user_input,
        )
        get_investigation_service().commit()

        state_context = build_new_information_state_prompt(
            investigation_state.model_dump_json(indent=2),
            user_input,
        )

        state_messages = [
            SYSTEM_MESSAGE,
            {
                "role": "user",
                "content": state_context
            }
        ]

        data = {
            "messages": state_messages,
            "format": state_update_schema,
            "stream": False,
        }

        state_update = call_structured_ollama(
            data,
            GENERAL_MODEL,
            StateUpdate,
        )

    # =========================================================
    # 5. RESOLVE WHETHER A DATASET IS AVAILABLE
    # =========================================================
    #
    # This is the critical V1/V2 boundary.
    #
    # If there is no dataset, this remains a V1 investigation.
    # EvidenceDecision must NOT invoke another LLM call and V2
    # must NOT execute.
    #

    analysis_dataset_id = resolve_analysis_dataset_id(
        investigation_id=current_investigation_id,
        dataset_id=dataset_id,
    )
    existing_analysis_results = collect_analysis_results(
        get_investigation_service(),
        current_investigation_id,
    )
    analysis_limitations = []
    if analysis_dataset_id is None and is_analytical_question(user_input):
        analysis_limitations.append(
            "No dataset is attached to this investigation, so I cannot calculate "
            "or verify dataset-specific figures."
        )
    available_dataset_columns = (
        get_dataset_service().get_available_analysis_columns(
            analysis_dataset_id
        )
        if analysis_dataset_id is not None
        else set()
    )

    # =========================================================
    # 6. EVIDENCE DECISION
    # =========================================================
    #
    # EvidenceDecision only runs when a dataset actually exists.
    #
    # StateUpdate.new_evidence_needed does NOT independently
    # trigger V2.
    #

    if (
        analysis_dataset_id is not None
        and is_analysis_deferred_request(user_input)
    ):
        evidence_decision = EvidenceDecision(
            needs_new_evidence=False,
            evidence_request=None,
        )
        logger.info(
            "Evidence decision skipped because the user deferred analysis"
        )

    elif (
        analysis_dataset_id is not None
        and requests_visualization(user_input)
        and select_relevant_analysis_results(
            existing_analysis_results,
            user_input,
        )
    ):
        # A chart request should reuse matching stored calculations. It should
        # not trigger another planner/model cycle when the requested evidence
        # already exists.
        evidence_decision = EvidenceDecision(
            needs_new_evidence=False,
            evidence_request=None,
        )
        logger.info(
            "Evidence decision skipped because matching stored results can be visualized"
        )

    elif (
        analysis_dataset_id is not None
        and is_explicit_analysis_request(user_input)
        and not existing_analysis_results
    ):
        # A direct request to run a calculation on a new investigation already
        # answers the evidence-needed question. Let Qwen structure it instead
        # of paying for a redundant Gemma yes/no decision first.
        evidence_decision = EvidenceDecision(
            needs_new_evidence=True,
            evidence_request=user_input,
        )
        logger.info(
            "Evidence decision skipped for explicit analysis with no stored results"
        )

    elif analysis_dataset_id is not None:

        existing_evidence_context = build_evidence_context(
        current_investigation_id
        )
        registered_capabilities = "\n".join(
            f"- {name}: {tool['description']}"
            for name, tool in ANALYTICS_REGISTRY.items()
        )
        previous_assistant_recommendation = next((
            message.content[:2000]
            for message in reversed(get_investigation_service().get_messages(
                current_investigation_id
            ))
            if message.role == "assistant" and message.content
        ), "No prior assistant recommendation.")

        evidence_decision_context = f"""
CURRENT INVESTIGATION STATE:

{investigation_state.model_dump_json(indent=2)}

EXISTING ANALYTICAL EVIDENCE:

{existing_evidence_context or "No analytical evidence stored yet."}

NEW USER REQUEST:

{user_input}

MOST RECENT ASSISTANT RECOMMENDATION (use this to resolve references such as
"run that analysis"):
{previous_assistant_recommendation}

A business dataset is available for this investigation.
Canonical fields available for analysis:
{", ".join(sorted(available_dataset_columns)) or "No mapped fields are available."}

REGISTERED ANALYTICS CAPABILITIES:
{registered_capabilities}

Only request a new calculation if its required source fields exist and a
registered analytics capability above can produce the requested metric and
granularity. If no listed capability can answer it, do not route to Qwen; report
the specific limitation. Do not reject a request merely because its wording
differs from a capability description; match the requested metric, grouping,
and calculation to what the registered tool actually returns.

Determine whether answering this user request requires NEW
evidence calculated from the available business dataset.

Decide from the user's intent, the conversation, the investigation state,
and the granularity and contents of the stored results. Do not treat a
diagnostic word such as "why" or "explain" as sufficient reason to run
another analysis.

Set needs_new_evidence to true when the user is asking for:

- actual numerical analysis
- trends
- comparisons
- distributions
- correlations
- business metrics
- analysis of the uploaded dataset
- a chart or visualization based on business data
- any conclusion that requires calculating facts from the dataset

Set needs_new_evidence to false when the request can be answered
from the existing investigation state and conversation alone.

If needs_new_evidence is true:

Provide ONE concise evidence_request describing exactly what
should be calculated from the already-available dataset.

The evidence request must be grounded in the user's actual request.

Do NOT ask the user to provide the dataset.

Do NOT invent:

- historical periods
- numerical facts
- business facts
- market data
- customer data
- external data
- time ranges not stated by the user

Do not add requirements that were not expressed or implied by
the user's request.

For example:

User:
"Show me the monthly revenue trend."

Good evidence_request:
"Calculate the monthly revenue trend from the uploaded dataset."

Bad evidence_request:
"Provide historical sales data for the last 24 months."

Bad evidence_request:
"Provide market trends and customer demand data."

EXISTING EVIDENCE RULES:

- Inspect the existing analytical evidence before requesting new evidence.
- If the existing evidence already answers the user's request,
  set needs_new_evidence to false.
- Conversational interpretation, conclusions, and hypotheses can be answered
  from stored context without another calculation when no new measured fact is
  requested.
- A request for a new metric, breakdown, comparison, trend, forecast, or chart
  generally needs fresh evidence unless the same result already exists at the
  requested granularity.
- A follow-up asking to verify, explain, or restate an existing
  result does not automatically require another analysis.
- Request new evidence only when the requested metric, dimension,
  or calculation is genuinely missing from the existing evidence.
- Never invent numerical values or categories.

Do not calculate any business numbers yourself.
"""

        evidence_decision_messages = [
            SYSTEM_MESSAGE,
            {
                "role": "user",
                "content": evidence_decision_context
            }
        ]

        evidence_decision_data = {
            "messages": evidence_decision_messages,
            "format": EvidenceDecision.model_json_schema(),
            "stream": False,
        }

        asks_for_discount_breakdown = (
            "discount" in user_input.casefold()
            and any(
                marker in user_input.casefold()
                for marker in ("by discount", "discount level", "discount band", "discount tier")
            )
        )
        if asks_for_discount_breakdown and "discount" not in available_dataset_columns:
            analysis_limitations.append(
                "This dataset has no usable discount column, so a discount-level "
                "profitability breakdown cannot be calculated."
            )
            evidence_decision = EvidenceDecision(
                needs_new_evidence=False,
                evidence_request=None,
            )
        else:
            # Gemma decides whether evidence is needed. Qwen is reachable only
            # after this decision requests one actionable calculation.
            evidence_decision = call_structured_ollama(
                evidence_decision_data,
                GENERAL_MODEL,
                EvidenceDecision,
            )

        requested_evidence = (
            evidence_decision.evidence_request or ""
        ).strip()
        if not evidence_decision.needs_new_evidence or not requested_evidence:
            # A positive decision without an actionable request cannot be
            # executed safely. Keep the route conversational and grounded.
            evidence_decision = EvidenceDecision(
                needs_new_evidence=False,
                evidence_request=None,
            )

    else:

        # -----------------------------------------------------
        # NO DATASET
        # -----------------------------------------------------
        #
        # This is a pure V1 investigation.
        #
        # We deliberately avoid the additional EvidenceDecision
        # LLM call and we do not execute V2.
        #

        evidence_decision = EvidenceDecision(
            needs_new_evidence=False,
            evidence_request=None,
        )


    # =========================================================
    # 7. DEBUG OUTPUT
    # =========================================================
    if state_update is not None:
        logger.debug("Investigation state update generated")

    route = "clarify_or_explain_limitation" if analysis_limitations else (
        "new_analysis"
        if evidence_decision.needs_new_evidence
        else (
        "existing_evidence"
        if build_evidence_context(current_investigation_id)
        else "hypotheses_only"
        )
    )
    logger.info(
        "Model route=%s evidence_needed=%s limitations=%s",
        route,
        evidence_decision.needs_new_evidence,
        len(analysis_limitations),
    )

    # =========================================================
    # 8. APPLY STATE UPDATE
    # =========================================================
    if state_update is not None:
        try:
            get_investigation_service().apply_state_update(
            current_investigation_id,
            state_update
            )
            get_investigation_service().commit()

        except Exception:
            get_investigation_service().rollback()
            raise    

    investigation_state = get_investigation_service().load_state(
        current_investigation_id
    )

    # =========================================================
    # 9. DETERMINE WHETHER V2 SHOULD RUN
    # =========================================================
    #
    # IMPORTANT:
    #
    # state_update.new_evidence_needed belongs to V1 state.
    #
    # It does NOT automatically launch V2.
    #
    # V2 runs only when:
    #
    # 1. A dataset exists
    # 2. EvidenceDecision says fresh evidence is needed
    # 3. EvidenceDecision provides a concrete request
    #

    visualizations = []
    visualization_analysis_names = []
    visualization_requested = requests_visualization(user_input)
    visualize_analysis_results = (
        visualization_requested
    )

    evidence_requests = []

    if (
        analysis_dataset_id is not None
        and evidence_decision.needs_new_evidence
        and evidence_decision.evidence_request
        and evidence_decision.evidence_request.strip()
    ):

        evidence_requests.append(
            evidence_decision.evidence_request.strip()
        )

    logger.info("Evidence requests selected count=%s", len(evidence_requests))

    # =========================================================
    # 10. ITERATIVE V2 EVIDENCE PIPELINE
    # =========================================================
    #
    # Cycle:
    #   plan -> execute -> persist evidence -> reassess hypotheses
    #   -> decide whether another distinct analysis is useful.
    #
    # The limit protects latency and prevents unbounded tool loops.
    #

    # One analysis per user turn keeps investigations targeted and responsive.
    # A further test can be requested after the result updates hypothesis status.
    # One requested analysis plus at most one hypothesis-driven follow-up.
    # Each cycle must produce a distinct registered result and update state
    # before another evidence decision is allowed.
    MAX_ANALYSIS_CYCLES = (
        1 if is_explicit_analysis_request(user_input) else 2
    )
    completed_cycle_count = 0
    new_analysis_results = []
    hypothesis_update_failed = False

    def decision_stage(state):
        nonlocal investigation_state
        if state["cycle_index"] == 0:
            requests = list(evidence_requests)
        else:
            if progress_callback:
                progress_callback("Checking whether another distinct test is useful…")
            decision = decide_followup_evidence(current_investigation_id, user_input)
            requests = [decision.evidence_request] if (
                decision.needs_new_evidence and decision.evidence_request
            ) else []
        request = next((str(item).strip() for item in requests if item and str(item).strip()), None)
        return {"evidence_request": request or "", "stop": not bool(request)}

    def planning_stage(state):
        if progress_callback:
            progress_callback("Planning the requested analysis…")
        requirement = build_evidence_requirement(state["evidence_request"])
        plan = select_analyses_from_requirement(requirement)
        if not plan or not plan.analyses:
            analysis_limitations.append("No registered analytics tool can answer this request at the requested metric and granularity.")
            return {"analysis_plan": None, "dataset_frame": None, "stop": True}
        df = get_dataset_service().load_dataset_for_analysis(analysis_dataset_id)
        existing = {
            (run.analysis_name, json.dumps(run.execution_parameters or {}, sort_keys=True, default=str))
            for run in get_investigation_service().get_analysis_runs(current_investigation_id)
        }
        selections = [selection for selection in plan.analyses if (
            selection.analysis_name,
            json.dumps(resolve_execution_parameters(selection), sort_keys=True, default=str),
        ) not in existing]
        if not selections:
            return {"analysis_plan": None, "dataset_frame": None, "stop": True}
        plan.analyses = selections
        return {"analysis_plan": plan, "dataset_frame": df}

    def execution_stage(state):
        plan = state.get("analysis_plan")
        if plan is None:
            return {"execution_results": []}
        try:
            results = execute_analysis_plan(
                investigation_id=current_investigation_id,
                df=state["dataset_frame"],
                analysis_plan=plan,
                include_visualizations=visualize_analysis_results,
            )
        except (ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
            analysis_limitations.append(f"The requested calculation could not be run: {exc}")
            results = []
        return {"execution_results": results or []}

    def persistence_stage(state):
        evidence_results = []
        for item in state.get("execution_results", []):
            run = item["analysis_run"]
            persist_analysis_evidence(current_investigation_id, run)
            evidence_results.append({
                "analysis_name": run.analysis_name,
                "requirement": run.requirement,
                "result": run.result_data,
            })
            new_analysis_results.append({"analysis_name": run.analysis_name, "result": run.result_data})
            if item.get("visualization") is not None:
                visualizations.append(item["visualization"])
                visualization_analysis_names.append(run.analysis_name)
        if evidence_results:
            get_investigation_service().commit()
        return {"evidence_results": evidence_results}

    def hypothesis_update_stage(state):
        nonlocal investigation_state, completed_cycle_count, hypothesis_update_failed
        evidence_results = state.get("evidence_results", [])
        if not evidence_results:
            return {"update_ok": False, "stop": True}
        if progress_callback:
            progress_callback("Updating hypotheses from the measured results…")
        updated = process_evidence_update(
            current_investigation_id,
            json.dumps(evidence_results, ensure_ascii=False, default=str),
        )
        investigation_state = get_investigation_service().load_state(current_investigation_id)
        completed_cycle_count += 1
        if updated is None:
            hypothesis_update_failed = True
        return {
            "update_ok": updated is not None,
            "stop": updated is None,
            "cycle_index": state["cycle_index"] + 1,
        }

    try:
        invoke_staged_investigation_graph({
            "decision": decision_stage,
            "planning": planning_stage,
            "execution": execution_stage,
            "persistence": persistence_stage,
            "hypothesis_update": hypothesis_update_stage,
        }, MAX_ANALYSIS_CYCLES)
    except Exception:
        get_investigation_service().rollback()
        raise

    # Ensure the final answer uses the latest persisted evidence and state.
    evidence_context = build_evidence_context(
        current_investigation_id,
        question=user_input,
    )
    investigation_state = get_investigation_service().load_state(
        current_investigation_id
    )

    # =========================================================
    # 13. FINAL GEMMA INVESTIGATION RESPONSE
    # =========================================================

    analysis_results = collect_analysis_results(
        get_investigation_service(),
        current_investigation_id,
    )

    relevant_new_results = select_relevant_analysis_results(
        new_analysis_results,
        user_input,
    ) if new_analysis_results else []
    relevant_stored_results = select_relevant_analysis_results(
        analysis_results,
        user_input,
    ) if analysis_results else []
    results_for_visualization = relevant_new_results or relevant_stored_results
    summary_followup = any(term in user_input.casefold() for term in (
        "summarize", "summarise", "takeaway", "take away",
        "what do the results", "what do these results",
        "what can we conclude", "what does this show",
    ))
    results_for_summary = relevant_new_results or (
        relevant_stored_results
        if visualization_requested or summary_followup
        else []
    )

    completed_analysis_summary = ""
    if results_for_summary:
        focused_result = answer_category_comparison(
            user_input,
            results_for_summary,
        )
        complete_result_table = format_deterministic_analytics_answer(
            results_for_summary,
        )
        completed_analysis_summary = "\n\n".join(
            part for part in (focused_result, complete_result_table) if part
        )
    if hypothesis_update_failed:
        analysis_limitations.append(
            "The calculation completed and is saved, but the model could not "
            "refresh hypothesis status. Treat existing statuses as unchanged."
        )

    # If the user explicitly asks for a chart and existing evidence already
    # answers the request, render that saved result instead of rerunning its
    # analytics tool.
    relevant_visualization_names = {
        item.get("analysis_name") for item in results_for_visualization
    }
    retained_visualizations = [
        (name, visualization)
        for name, visualization in zip(
            visualization_analysis_names,
            visualizations,
        )
        if name in relevant_visualization_names
    ]
    visualization_analysis_names = [name for name, _ in retained_visualizations]
    visualizations = [item for _, item in retained_visualizations]

    if visualize_analysis_results and not visualizations:
        for item in results_for_visualization:
            try:
                visualization = run_visualization(
                    analysis_name=item.get("analysis_name"),
                    analysis_result=item.get("result"),
                )
            except (KeyError, ValueError, TypeError):
                visualization = None
            if visualization is not None:
                visualizations.append(visualization)
                visualization_analysis_names.append(item.get("analysis_name"))

    structured_results_context = serialize_grounded_context(
        analysis_results,
        question=user_input,
    )

    persisted_messages = get_investigation_service().get_messages(
        current_investigation_id
    )
    response_messages = build_response_messages(
        latest_question=user_input,
        state=investigation_state,
        recent_messages=persisted_messages,
        evidence_context=evidence_context,
        structured_results=structured_results_context,
        limitations=analysis_limitations,
        available_dataset_fields=sorted(available_dataset_columns),
        completed_analysis_summary=completed_analysis_summary,
    )
    data = {
        "messages": response_messages,
        "stream": False,
    }

    # Let code that owns the calculated values render them. Gemma handles
    # conversational interpretation when no new calculation is being shown.
    if progress_callback:
        progress_callback("Writing the business analyst response…")

    question_lower = user_input.casefold()
    asks_about_hypotheses = any(
        term in question_lower
        for term in ("hypothes", "explanation", "explanations", "why", "uncertain")
    )
    deterministic_response = None
    if is_new_investigation and not analysis_results:
        deterministic_response = format_unverified_hypotheses_response(
            investigation_state,
            analysis_limitations,
        )
    elif new_analysis_results and completed_analysis_summary:
        deterministic_response = completed_analysis_summary
        if asks_about_hypotheses:
            deterministic_response += "\n\n" + format_hypothesis_status_response(
                investigation_state
            )
        if hypothesis_update_failed:
            deterministic_response += (
                "\n\nHypothesis statuses were left unchanged because their "
                "evidence refresh did not complete."
            )
    elif summary_followup and relevant_stored_results and completed_analysis_summary:
        # Numeric takeaways come directly from the latest stored Python result.
        # Reusing free-form assistant history here allowed old or hallucinated
        # percentages to drift from the displayed evidence table.
        deterministic_response = completed_analysis_summary
    elif visualization_requested and relevant_stored_results:
        deterministic_response = (
            "The chart compares the requested saved results across the "
            "selected groups. It supports comparison of measured outcomes; "
            "it cannot establish what caused the differences.\n\n"
            + completed_analysis_summary
        )

    if deterministic_response is not None:
        assistant_response = deterministic_response
        if stream_callback:
            for offset in range(0, len(assistant_response), 160):
                stream_callback(assistant_response[offset:offset + 48])
    else:
        try:
            assistant_response = call_text_ollama(
                data,
                GENERAL_MODEL,
                on_token=stream_callback,
            )
        except OllamaCallError as exc:
            if not completed_analysis_summary:
                raise
            logger.warning(
                "Final model response unavailable; using verified analysis output; error_type=%s",
                type(exc).__name__,
            )
            assistant_response = (
                "The calculation completed successfully. The model explanation "
                "is unavailable right now, so here are the verified results."
            )

    if completed_analysis_summary and deterministic_response is None:
        assistant_response = (
            assistant_response.rstrip()
            + "\n\n---\n\n### Verified results from the executed analysis\n\n"
            + completed_analysis_summary
        )

    if visualization_requested:
        assistant_response = strip_visualization_placeholder(
            normalize_assistant_response(assistant_response)
        )
        if not results_for_visualization:
            assistant_response = (
                "I don't have a verified result for this request to visualize "
                "yet, so I can't report dataset figures or show a chart. The "
                "requested analysis may need to be run again with a dataset "
                "that includes the required fields."
            )
            if analysis_limitations:
                assistant_response += "\n\n" + "\n".join(
                    f"- {item}" for item in analysis_limitations
                )
        elif not visualizations:
            assistant_response = assistant_response.rstrip() + (
                "\n\nI couldn't render a chart for this result, but the "
                "verified figures above are available."
            )
        logger.info(
            "Visualization response requested=%s result_count=%s chart_count=%s",
            True,
            len(results_for_visualization),
            len(visualizations),
        )
    else:
        assistant_response = normalize_assistant_response(assistant_response)


    # =========================================================
    # 14. SAVE ASSISTANT RESPONSE
    # =========================================================

    try:
        get_investigation_service().add_message(
            current_investigation_id,
            role="assistant",
            content=assistant_response
        )

        get_investigation_service().commit()

    except Exception:
        get_investigation_service().rollback()
        raise

    # =========================================================
    # 15. API RESPONSE
    # =========================================================

    if include_visualizations:

        return {
            "response": assistant_response,
            "investigation_id": current_investigation_id,
            "visualizations": [
                serialize_visualization(visualization)
                for visualization in visualizations
            ],
            "analysis_cycles_completed": completed_cycle_count,
            "analysis_cycle_limit": MAX_ANALYSIS_CYCLES,
        }

    return assistant_response


def process_message(
    user_input,
    *,
    investigation_id=None,
    dataset_id=None,
    branch_context=None,
    include_visualizations=False,
    stream_callback=None,
    progress_callback=None,
):
    """Coordinate the existing V2 investigation through LangGraph."""
    return invoke_chat_workflow(
        _process_message_v2,
        user_input=user_input,
        investigation_id=investigation_id,
        dataset_id=dataset_id,
        branch_context=branch_context,
        include_visualizations=include_visualizations,
        stream_callback=stream_callback,
        progress_callback=progress_callback,
    )


# The local SPA is served by FastAPI so the browser and API share one origin.
# React-style interactions are implemented with native browser modules, so
# running the pilot does not require installing Node or a global React package.
FRONTEND_WEB_DIR = Path(__file__).resolve().parents[1] / "frontend" / "web"
app.mount("/", StaticFiles(directory=str(FRONTEND_WEB_DIR), html=True), name="web")
