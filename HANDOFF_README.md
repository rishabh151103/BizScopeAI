# BizScopeAI — Project Handoff and Current State

This document is a detailed handoff for continuing BizScopeAI work in another ChatGPT session. It records the product goal, current architecture, work reflected in the workspace, what has been verified, known gaps, and recommended next steps. Treat the source code as authoritative if a detail here differs from implementation.

## 1. Product goal

BizScopeAI is intended to behave like a general business analyst for a user's uploaded business data. It is not meant to assume a particular industry or store type. The conversation should help the user frame a business question, explore plausible explanations, decide what evidence would be useful, and interpret findings in context.

The desired conversational and evidence cycle is:

1. The user asks an exploratory business question. Gemma responds conversationally, helps frame the issue, and offers plausible hypotheses. It should make clear what is known, what is only a possibility, and what cannot be concluded yet. It should not launch calculations if the user says not to.
2. When the user asks for a new numerical or visual finding, the system determines whether existing evidence already answers the request. If it does, reuse that result. If it does not, plan and execute a suitable registered Python analysis. Qwen is used to structure an evidence request into the tool parameters where needed; Qwen should not be invoked for ordinary conversational follow-ups.
3. The analysis tools, not the language model, own numerical calculations, rankings, arithmetic, tables, and chart data.
4. Once new analysis is completed, the system persists the result and refreshes the investigation hypotheses against that evidence. A hypothesis can be supported, weakened, rejected, remain unresolved, or be inconclusive only when a relevant analysis has actually tested it.
5. Gemma interprets verified results conversationally, in the context of the ongoing investigation. It should not invent values or duplicate calculations from memory.
6. Visualizations should be created only when asked for or otherwise clearly needed, and should reflect only analyses relevant to the current question. Existing matching results should be reused rather than needlessly recalculated.

The product should remain AI-led in conversation and hypothesis framing, while deterministic code guarantees the integrity of measurable evidence. “AI system” does not mean delegating arithmetic to a small language model: its business reasoning is useful, but it must not be trusted to calculate exact numbers or identify category rankings from long prompts.

## 2. Runtime and how the user accesses the app

The current intended first deployment is a single local user on a Windows workstation. Keep the service bound to loopback (`127.0.0.1`). It is not ready for multiple employees, network exposure, or public hosting.

### Prerequisites described in the project README

- Python 3.10 or newer and the project virtual environment.
- PostgreSQL running locally and a configured `DATABASE_URL` in `.env`.
- Ollama with `gemma3:4b` and `qwen3:4b` installed.
- The dependencies in `requirements.txt`.

### Start the app

From PowerShell at `N:\BizScopeAI`:

```powershell
cd N:\BizScopeAI
.\venv\Scripts\python.exe -m uvicorn Backend.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`. FastAPI serves the current browser UI and API from one process. Backend request and model logs appear in the same terminal running Uvicorn. Stop it with `Ctrl+C`.

The old Streamlit UI is retained as a fallback:

```powershell
cd N:\BizScopeAI
.\venv\Scripts\python.exe -m streamlit run frontend\app.py --server.address 127.0.0.1 --server.port 8501
```

The frontend is organized under `frontend/`. The active UI is a native HTML/CSS/JavaScript single page app, not a React build, so it does not require Node or npm. `frontend/app.py` is the legacy Streamlit client.

An earlier browser log showed `/favicon.ico` returning 404 before the favicon asset was requested from its actual path. The later requests to `/assets/favicon.svg` returned 200; it was not a backend chat failure. Current health routes are `/health/live` and `/health/ready`.

## 3. Architecture and file map

### API and conversation orchestration

- `Backend/main.py` — FastAPI app, health and dataset/investigation endpoints, upload handling, standard and streaming chat endpoints, routing between conversational responses and evidence work, persistence, result selection, hypothesis updates, and final response construction. This is the central orchestration module and remains large; consider extracting coherent services as future work.
- `Backend/llm_client.py` — Ollama HTTP calls, structured response parsing/retries, streaming text generation, timeout handling, and continuation behavior when a response hits the generation limit or ends without a final chunk.
- `Backend/response_prompt.py` — Builds the Gemma response instructions and context. Current instructions emphasize grounding in saved analysis and prohibit redoing numeric work from memory.
- `Backend/reasoning.py` — Normalizes analysis requirements and ranks/resolves candidate tools.
- `Backend/analysis_planner.py` — Converts the user's analytical request into analysis requirements and registered tool selections. Qwen can structure new-evidence requests.
- `Backend/pipeline.py` — Dataset preparation and the reusable analysis/visualization/investigation pipeline functions.
- `Backend/analysis_executor.py` and `Backend/execution_resolver.py` — Resolve and execute planned analyses.
- `Backend/analytics_registry.py` and `Backend/analytics_adapter.py` — Registered analytics catalogue and adapter layer between standardized analysis requests and implementations.
- `Backend/analytics.py` — Deterministic business metrics and aggregations. This is where numerical values should originate.
- `Backend/answer_grounding.py` — Selects evidence/results relevant to a user question and formats verified answers. Recent work adds deterministic category ranking and top-two gap generation, and filters unrelated product-performance evidence from category-only questions.
- `Backend/visualization.py` — Validated Plotly visualization builders.
- `Backend/result_serializer.py` — Serializes saved analysis results and chart/evidence context for the client and model.
- `Backend/schema_mapper.py` — Maps user dataset columns to canonical business concepts used by analyses.
- `Backend/data_loader.py` — Loads, normalizes, profiles, and preprocesses uploaded tabular data. The intended policy is conservative: improve structural cleanliness without silently deleting meaningful business values such as negative profit.

### Persistence and data management

- `Backend/database.py` — Database configuration and SQLAlchemy session setup.
- `Backend/db_models.py` — Database models.
- `Backend/repositories.py` — Persistence access layer.
- `Backend/dataset_service.py` — Dataset persistence and metadata.
- `Backend/investigation_service.py` — Investigation, message, evidence, and analysis-run persistence.
- `Backend/schemas.py` — API request/response and investigation-state schemas.
- `Backend/init_db.py`, `Backend/migration_runner.py`, `Backend/migrations/` — Database initialization and ordered SQL migrations. Applied migration checksums are tracked; add a new migration rather than changing an applied migration.
- `scripts/backup_restore.py` — Local backup/restore utility. The main README describes backups using Windows DPAPI, so archives are tied to the Windows account/installation and must be included in workstation recovery planning.
- `.env.example` — Environment variable template. Keep `.env` private; do not share secrets in a chat or commit them.

### Frontend

- `frontend/web/index.html` — Single-page chat shell served by FastAPI.
- `frontend/web/assets/css/styles.css` — Layout and visual styling.
- `frontend/web/assets/js/app.js` — Browser behavior, API interaction, message editing/history behavior, streaming display, analysis tables and charts.
- `frontend/web/assets/favicon.svg` and `frontend/web/favicon.ico` — Browser icons.
- `frontend/app.py` — Streamlit fallback.

The browser UI calls `POST /chat/stream` for token/event streaming and uses the related dataset/investigation routes. The non-streaming `POST /chat` remains available to JSON clients and the fallback UI. Analysis and hypothesis update work may happen before the final assistant response begins streaming, so streaming improves perceived response progress but does not eliminate model/tool latency.

### Tests and evaluation

- `Evaluation/test_cases/` — Unit, integration, and domain tests for data loading, schema mapping, analytics, planning, evidence selection, execution, persistence, visualization, and backup safety.
- `Evaluation/test_main/` — API, dataset, state, model, and end-to-end-oriented tests.
- `Evaluation/results/` — Test reports and evaluation summaries. Some older reports have different suite totals because they describe different test groupings/runs; see verification notes below.
- `dataset/` — Evaluation/sample business datasets including `samplesuperstore.csv`, dirty Superstore data, and synthetic business fixtures.

## 4. Work applied to the project so far

The following is based on the current source tree, the project README, and the recent code changes in this conversation. The workspace contains many modified and untracked project files, so do not assume there is a clean commit history or that all current files have been committed.

### Product and backend direction

- The application was moved toward an investigation-style business analyst: a conversational opening, ranked hypotheses, evidence requests, analytical tools, hypothesis updates, and follow-up interpretation.
- The system uses Gemma (`gemma3:4b`) for conversational/investigation language and Qwen (`qwen3:4b`) for structuring new evidence requests into analysis parameters. It has logic for deciding whether new evidence is needed and for reusing stored evidence for follow-ups.
- Deterministic registered Python analytics provide numerical evidence, including business comparisons, category and product performance, profitability, discounts, regional results, time trends, customer/segment behavior, correlations, outliers, and other analyses in the catalogue.
- Uploaded datasets are profiled and mapped to canonical business concepts, allowing supported tools to work across differing column names. Unsupported questions should be acknowledged as unsupported instead of silently answering with fabricated numbers.
- Analysis runs and their evidence are persisted and made available to later turns in an investigation.
- State update logic applies new analytical evidence to existing hypotheses so their status and basis can change as the investigation proceeds.
- Evidence context and serialized numerical results are sent into the language-model prompt; recent changes filter this context to the analysis most relevant to the latest question.

### Robustness, latency, and response streaming

- Ollama calls have configurable timeouts, connection timeouts, structured-call validation/retry behavior, and log messages that report model/operation outcomes without dumping chat text or dataset contents.
- Text generation has a configurable output-token limit (768 by default in the documented setup), an 8192-token context default, token streaming, and up to two continuation calls if generation ends at the token limit or the final stream marker is missing.
- The FastAPI app has `/chat` and `/chat/stream`. Streaming uses server-sent events and sends progress while analysis/model work occurs; the active browser client displays incremental response content.
- Request IDs and request summaries are included in server logging; uploaded data and chat contents are not intended to be logged.
- Upload size is configurable (50 MB default), and uploaded files are stored under the configured `BIZSCOPE_DATA_DIR` (project `uploads/` by default).

### Database and local-pilot operations

- The app uses PostgreSQL for datasets, investigations, messages, analysis runs, evidence, and state. The user ran `python -m Backend.init_db` successfully earlier (`Database tables created successfully.`).
- Ordered SQL migrations were introduced, with checksums recorded to prevent edits to migrations already applied.
- A backup/restore script was added. The documented restore path requires explicit database confirmation and refuses certain existing file targets to avoid accidental overwrite.
- The app has readiness/liveness routes, and the README documents a localhost-only single-user pilot. It explicitly says authentication, tenant separation, and ownership enforcement must be added before shared network/team use.

### Frontend

- A browser-based interface was added under `frontend/web`, served by the FastAPI application. The UI is a polished single-page HTML/CSS/JavaScript frontend organized away from the backend root and does not require React, Node, npm, or a build step.
- `frontend/app.py` was retained as the Streamlit fallback rather than used as the primary frontend.
- The browser UI includes chat and dataset/investigation interaction, streaming support, and display of stored analytics and visualizations. The user requested message editing, and the current frontend files should be inspected directly to confirm exact interaction behavior before making claims about edge cases.

### Recent fixes prompted by the screenshots

The screenshots showed that free-form model responses were asserting that hypotheses were “tested” before any analysis ran, inventing category labels and values, calculating the wrong top-two gap, repeating irrelevant analyses in a visualization request, or returning an unhelpful tool error even when a relevant saved result existed. The latest code changes target those issues:

- `Backend/main.py` now has a deterministic initial investigation response formatter. It marks hypotheses **untested** when no analysis exists, and presents candidate basis/evidence that could test them.
- `Backend/main.py` now formats hypothesis status from persisted investigation state after analysis. It distinguishes an unresolved/active hypothesis from evidence-backed statuses and includes the stored basis.
- `Backend/main.py` filters evidence context for the latest question, selects new and saved results relevant to that question, and narrows visualizations to matching analyses. When a chart request can use an existing relevant saved result, it reuses that result rather than launching the same analysis again.
- When a new analysis ran, its verified result summary is rendered deterministically so Gemma cannot overwrite the actual table, arithmetic, or ranking with hallucinated values. Hypothesis status is appended when the user asks about hypotheses/explanations/why/uncertainty.
- `Backend/answer_grounding.py` now filters unrelated `product_performance` results for category-only questions. `answer_category_comparison()` generates a sorted category comparison and the gap between the leading two categories using actual tool output.
- `Backend/response_prompt.py` now tells the model not to claim active hypotheses have been tested and not to reproduce numeric tables or rankings from memory when a verified summary is supplied.

For the sample Superstore values visible in the user's verified result screenshot, Technology ranked first for total profit at about 146,543.38, Office Supplies second at about 126,023.44, for a difference of about 20,519.93. A model answer that instead used Furniture and Office Supplies, or invented Electronics/Apparel categories, was incorrect. Use live dataset/tool output as authoritative; do not hardcode those screenshot figures in application logic.

## 5. Where the project stands

### Current state

BizScopeAI is a substantial local prototype with a FastAPI backend, persistent investigation/database layer, registered analytics, Ollama models, streaming, and a standalone web frontend. The owner has selected “one local user” as the first deployment target. It is not an enterprise production system and should not be exposed to a LAN or public endpoint yet.

### Latest verification in the just-completed coding turn

The following checks passed after the latest response-grounding changes:

```powershell
.\venv\Scripts\python.exe -m py_compile Backend\main.py Backend\answer_grounding.py Backend\response_prompt.py
.\venv\Scripts\python.exe -c "from Backend.main import app; print('Backend import OK:', app.title)"
```

The backend import printed `Backend import OK: FastAPI`.

**The full pytest suite was not rerun after these most recent changes.** This was intentionally left for the next session; the owner said monthly usage was nearly exhausted. Do not report the latest code as fully regression-tested.

### Existing test result records

The repository includes a historical evaluation report recording **203 passed, 0 failed, 0 errors** for `Evaluation/test_cases`. Another analytics-only report records **160 passed** for a different test grouping. These are prior runs recorded in files, not proof that the most recent edits pass. The end-to-end live Ollama test is opt-in and may be skipped unless explicitly enabled. Review the reports and test markers before combining totals or calling a skip a failure.

The app and database initialization were exercised by the owner previously. The local UI was also run and screenshots were reviewed, which led to the latest grounding fixes. Exact model behavior after those fixes still needs manual validation against Ollama.

## 6. Known limitations and open risks

1. **Recent changes need regression testing.** The deterministic answer formatting, question-specific evidence filtering, and chart reuse logic have only had Python syntax and app-import checks in the latest turn. Run unit tests relevant to these paths and then the full suite if resources allow.
2. **Local model behavior needs a fresh conversation test.** Verify the routing logs: ordinary follow-ups should not call Qwen; new numerical evidence should call the necessary planning path; matched saved evidence should be reused; and hypotheses should change only after an actual analysis plus state update.
3. **Hypothesis status refresh can fail independently.** The current code adds a limitation message and keeps prior statuses when the evidence refresh fails. Confirm this failure path in UI and API behavior.
4. **No multi-user security boundary.** No authentication/authorization or per-user isolation is documented as implemented. Do not expose this pilot beyond loopback.
5. **Database and backup recovery are workstation-specific.** Confirm PostgreSQL service/database availability, `.env`, upload path, chat history, and backup restore procedure on the target machine.
6. **Streaming does not make inference faster by itself.** It makes generation visible incrementally; the user may still wait for evidence planning, analytics, hypothesis refresh, and model calls before/during tokens.
7. **Ollama resource constraints remain.** `gemma3:4b` and `qwen3:4b` run locally; actual throughput depends on the host's RAM/VRAM and concurrent workload. Adjust documented context/output settings only after measuring quality and latency.
8. **Analysis capability is bounded by registered tools and mapped fields.** New business questions may require adding analytics functions, tests, schema mappings, and visualization support.
9. **Frontend behavior should be checked against the current JS.** Verify editing a sent message, regeneration, stream cancellation/error display, investigation switching, and chart rendering after the recent backend changes.
10. **Dataset quality and metric definitions matter.** A dataset may have fields named profit/revenue but lack costs or other causal drivers. Responses must separate measured patterns from causal explanations and state what the available data cannot establish.

## 7. Recommended continuation plan

For the next ChatGPT session, continue in this order:

1. Read this handoff and inspect the current source at `N:\BizScopeAI`; do not assume prior message context or that the workspace is clean. Do not overwrite the existing README without first checking it.
2. Inspect `Backend/main.py`, `Backend/answer_grounding.py`, and `Backend/response_prompt.py` around the recent changes. Add focused regression tests for: initial hypotheses remain untested, category ranking/gap correctness, no invented values in analysis responses, evidence relevance filtering, and chart reuse/filtering.
3. Run targeted tests first, then the full normal suite:

   ```powershell
   cd N:\BizScopeAI
   .\venv\Scripts\python.exe -m pytest Evaluation\test_cases Evaluation\test_main -q
   ```

   Inspect any intentionally skipped tests. The live Ollama E2E test is opt-in and may require:

   ```powershell
   $env:RUN_LIVE_OLLAMA_E2E='1'
   .\venv\Scripts\python.exe -m pytest Evaluation\test_main\test_full_e2e.py -q
   ```

4. Start PostgreSQL and Ollama, run the app locally, upload `dataset\samplesuperstore.csv`, and validate a fresh investigation with a sequence such as:

   - “I’m reviewing business performance. Help me frame up to three plausible explanations for why profit may not be keeping pace with revenue. Do not run calculations yet.”
   - “Which of those explanations can this dataset test? Recommend the most useful first analysis, but do not run it.”
   - “Run the comparison by category. Rank the categories by total profit and calculate the gap between the top two. Separate measured results from possible explanations.”
   - “Show a visualization of those category results. Reuse the analysis you already ran; do not add unrelated discount analysis.”
   - “Given the results and chart, what should management take away? Which hypotheses are supported, weakened, or still unresolved, and what would be the most useful next evidence?”

5. Inspect the Uvicorn terminal logs to confirm Qwen/model routing and actual analysis names. Confirm all displayed values and gap match persisted Python analysis output, the visualization contains only relevant traces, and hypothesis statuses correspond to actual state updates.
6. Fix any regression before expanding features. Keep the core response pattern: measured result first, interpretation second, limitations/uncertainty third, useful next evidence last.
7. Before any company/team deployment, design authentication, authorization, user/tenant ownership for datasets and investigations, safe secrets handling, network controls, retention, monitoring, encrypted/off-machine backups, and recovery drills. The current pilot is not ready for shared access.

## 8. Instructions for the next assistant

- Work in `N:\BizScopeAI`; changes here are what the user sees when they reopen the workspace in VS Code.
- The user wants a generalized AI business analyst, not a store-specific or industry-specific hard-coded agent.
- Preserve the intended division: Gemma for conversational framing and explanation; Qwen only when new evidence needs structuring; deterministic analytics for numbers and visual data; persisted investigation state for hypothesis updates.
- Do not let a model invent datasets, categories, metrics, rankings, or calculated gaps. Use exact saved analytics results and explain uncertainty honestly.
- Respect “don’t run it yet” and similar user constraints.
- Do not claim tests passed unless they were run after the current changes. Existing reports are historical evidence only.
- The user has said their monthly Codex usage is exhausted/near its limit. Keep the handoff actionable and avoid expensive live-model runs unless they ask or usage permits.

## 9. References in this workspace

- Project setup and operations: `README.md`
- Frontend structure: `frontend/README.md`
- API and orchestration: `Backend/main.py`
- LLM calls/streaming: `Backend/llm_client.py`
- Prompt construction: `Backend/response_prompt.py`
- Grounded result selection/formatting: `Backend/answer_grounding.py`
- Analytics/tool catalogue: `Backend/analytics.py`, `Backend/analytics_registry.py`, `Backend/analysis_planner.py`
- Investigation and evidence persistence: `Backend/investigation_service.py`, `Backend/repositories.py`, `Backend/db_models.py`
- Test suite: `Evaluation/test_cases/`, `Evaluation/test_main/`
- Recorded evaluation results: `Evaluation/results/`

