from sqlalchemy.orm import Session

from .schemas import Hypotheses, InvestigationState

from .pipeline import run_visualization

from . import analysis_executor

from .execution_resolver import resolve_execution_parameters

from .db_models import Fact, Hypothesis

from .repositories import (
    AnalysisRunRepository,
    EvidenceRepository,
    EvidenceRequestRepository,
    InvestigationHistoryRepository,
    InvestigationRepository,
    MessageRepository,
)

from .result_serializer import serialize_result

import logging

logger = logging.getLogger(__name__)


class InvestigationService:

    def __init__(self, db: Session):
        self.db = db

    # =========================================================
    # Investigation
    # =========================================================

    def create_investigation(
        self,
        problem: str,
        business_context: str = "",
        current_focus: str = "",
        dataset_id: int | None = None,
    ):
        investigation = InvestigationRepository.create(
            self.db,
            problem=problem,
            business_context=business_context,
            current_focus=current_focus,
            dataset_id=dataset_id,
        )

        # Explicitly persist the parent investigation before
        # returning it to callers that may immediately create
        # child records.
        self.db.flush()

        if investigation.id is None:
            raise RuntimeError(
                "Failed to generate investigation ID."
            )

        return investigation

    def get_investigation(self, investigation_id: int):
        return InvestigationRepository.get(
            self.db,
            investigation_id,
        )

    # =========================================================
    # Messages
    # =========================================================

    def add_message(
        self,
        investigation_id: int,
        role: str,
        content: str,
    ):
        return MessageRepository.add(
            self.db,
            investigation_id=investigation_id,
            role=role,
            content=content,
        )

    def get_messages(self, investigation_id: int):
        return MessageRepository.get_for_investigation(
            self.db,
            investigation_id,
        )

    # =========================================================
    # Facts
    # =========================================================

    def add_fact(
        self,
        investigation_id: int,
        content: str,
    ):
        fact = Fact(
            investigation_id=investigation_id,
            content=content,
        )

        self.db.add(fact)
        self.db.flush()

        return fact

    def get_facts(self, investigation_id: int):
        return list(
            self.db.query(Fact)
            .filter(
                Fact.investigation_id == investigation_id
            )
            .order_by(Fact.id)
            .all()
        )

    # =========================================================
    # Hypotheses
    # =========================================================

    def add_hypothesis(
        self,
        investigation_id: int,
        hypothesis: str,
        status: str = "active",
        basis: str = "",
        priority: str = "medium",
    ):
        item = Hypothesis(
            investigation_id=investigation_id,
            statement=hypothesis,
            status=status,
            basis=basis,
            priority=priority,
        )

        self.db.add(item)
        self.db.flush()

        return item

    def get_hypotheses(self, investigation_id: int):
        return list(
            self.db.query(Hypothesis)
            .filter(
                Hypothesis.investigation_id == investigation_id
            )
            .order_by(Hypothesis.id)
            .all()
        )

    # =========================================================
    # Evidence Requests
    # =========================================================

    def add_evidence_request(
        self,
        investigation_id: int,
        request: str,
        hypothesis_id: int | None = None,
        status: str = "needed",
    ):
        return EvidenceRequestRepository.add(
            self.db,
            investigation_id=investigation_id,
            request=request,
            hypothesis_id=hypothesis_id,
            status=status,
        )

    def get_evidence_requests(self, investigation_id: int):
        return EvidenceRequestRepository.get_for_investigation(
            self.db,
            investigation_id,
        )

    # =========================================================
    # Evidence
    # =========================================================

    def add_evidence(
        self,
        investigation_id: int,
        content: str,
        structured_data=None,
        analysis_run_id: int | None = None,
    ):
        return EvidenceRepository.add(
            self.db,
            investigation_id=investigation_id,
            content=content,
            structured_data=structured_data,
            analysis_run_id=analysis_run_id,
        )

    def get_evidence(self, investigation_id: int):
        return EvidenceRepository.get_for_investigation(
            self.db,
            investigation_id,
        )

    # =========================================================
    # Analysis Runs
    # =========================================================

    def add_analysis_run(
        self,
        investigation_id: int,
        analysis_name: str,
        requirement=None,
        execution_parameters=None,
        result_data=None,
        status: str = "completed",
    ):
        return AnalysisRunRepository.add(
            self.db,
            investigation_id=investigation_id,
            analysis_name=analysis_name,
            requirement=requirement,
            execution_parameters=execution_parameters,
            result_data=result_data,
            status=status,
        )

    def get_analysis_runs(self, investigation_id: int):
        return AnalysisRunRepository.get_for_investigation(
            self.db,
            investigation_id,
        )

    def execute_analysis_selection(
        self,
        investigation_id: int,
        df,
        selection,
    ):

        result = analysis_executor.execute_analysis(
            df,
            selection,
        )

        execution_parameters = resolve_execution_parameters(
            selection
        )

        requirement = selection.requirement.model_dump()

        result_data = serialize_result(result)

        analysis_run = self.add_analysis_run(
            investigation_id=investigation_id,
            analysis_name=selection.analysis_name,
            requirement=requirement,
            execution_parameters=execution_parameters,
            result_data=result_data,
            status="completed",
        )

        return analysis_run
        

    def execute_visualization_for_analysis_run(
        self,
        analysis_run,
    ):
        return run_visualization(
            analysis_name=analysis_run.analysis_name,
            analysis_result=analysis_run.result_data,
        )

    # =========================================================
    # History
    # =========================================================

    def add_history(
        self,
        investigation_id: int,
        entry: str,
    ):
        return InvestigationHistoryRepository.add(
            self.db,
            investigation_id=investigation_id,
            entry=entry,
        )

    def get_history(self, investigation_id: int):
        return InvestigationHistoryRepository.get_for_investigation(
            self.db,
            investigation_id,
        )

    # =========================================================
    # Initial Investigation State
    # =========================================================

    def create_initial_state(
        self,
        diagnosis,
        business_context="",
        dataset_id=None,
    ):
        """
        Create a complete initial investigation state.

        The investigation parent is flushed before child records
        are inserted. This guarantees that facts, hypotheses,
        evidence requests, and history rows reference an existing
        investigation row.
        """

        investigation = self.create_investigation(
            problem=diagnosis.problem_summary,
            business_context=business_context,
            current_focus=diagnosis.conclusion,
            dataset_id=dataset_id,
        )

        # -----------------------------------------------------
        # Persist parent investigation first
        # -----------------------------------------------------

        self.db.flush()

        if investigation.id is None:
            raise RuntimeError(
                "Investigation ID was not generated after flush."
            )

        investigation_id = investigation.id

        # -----------------------------------------------------
        # Confirmed facts
        # -----------------------------------------------------

        for fact in diagnosis.confirmed_facts:

            self.add_fact(
                investigation_id,
                fact,
            )

        # -----------------------------------------------------
        # Hypotheses + evidence requirements
        # -----------------------------------------------------

        for hypothesis in diagnosis.hypotheses:

            db_hypothesis = self.add_hypothesis(
                investigation_id,
                hypothesis=hypothesis.statement,
                status=hypothesis.status,
                basis=hypothesis.basis,
                priority=hypothesis.priority,
            )

            # Make sure hypothesis ID exists before creating
            # evidence requests that reference it.

            self.db.flush()

            if db_hypothesis.id is None:
                raise RuntimeError(
                    "Hypothesis ID was not generated after flush."
                )

            for evidence_request in hypothesis.evidence_needed:

                self.add_evidence_request(
                    investigation_id,
                    request=evidence_request,
                    hypothesis_id=db_hypothesis.id,
                )

        # -----------------------------------------------------
        # Initial history
        # -----------------------------------------------------

        self.add_history(
            investigation_id,
            "Initial investigation created.",
        )

        # -----------------------------------------------------
        # Final persistence
        # -----------------------------------------------------

        self.db.flush()

        return investigation

    # =========================================================
    # Current Focus
    # =========================================================

    def update_current_focus(
        self,
        investigation_id: int,
        current_focus: str,
    ):
        investigation = self.get_investigation(
            investigation_id
        )

        if investigation is None:
            raise ValueError(
                f"Investigation {investigation_id} not found."
            )

        investigation.current_focus = current_focus

        self.db.flush()

        return investigation

    # =========================================================
    # State Update
    # =========================================================

    def apply_state_update(
        self,
        investigation_id,
        state_update,
    ):
        """
        Apply a V1 investigation state update.

        This method updates persistent V1 state only.
        It does not execute V2 analytics.
        """

        # -----------------------------------------------------
        # Validate investigation
        # -----------------------------------------------------

        investigation = self.get_investigation(
            investigation_id
        )

        if investigation is None:
            raise ValueError(
                f"Investigation {investigation_id} not found."
            )

        # -----------------------------------------------------
        # Facts
        # -----------------------------------------------------

        existing_facts = {
            fact.content
            for fact in self.get_facts(
                investigation_id
            )
        }

        for fact in state_update.new_facts:

            if fact not in existing_facts:

                self.add_fact(
                    investigation_id,
                    fact,
                )

                existing_facts.add(fact)

        # -----------------------------------------------------
        # Hypothesis updates
        # -----------------------------------------------------

        existing_hypotheses = {
            hypothesis.id: hypothesis
            for hypothesis in self.get_hypotheses(
                investigation_id
            )
        }

        # Persist new testable hypotheses, deduplicated by statement.
        existing_statements = {
            item.statement.strip().casefold()
            for item in existing_hypotheses.values()
        }
        active_statuses = {"active", "supported", "weakened", "inconclusive"}
        updated_statuses = {
            update.hypotheses_id: update.status
            for update in state_update.hypotheses_updates
        }
        active_count = sum(
            updated_statuses.get(item.id, item.status) in active_statuses
            for item in existing_hypotheses.values()
        )
        for proposed in getattr(state_update, "new_hypotheses", []):
            statement_key = proposed.statement.strip().casefold()
            if not statement_key or statement_key in existing_statements:
                continue
            if active_count >= 3:
                logger.info(
                    "Skipping proposed hypothesis: three active-hypothesis limit reached "
                    "(investigation_id=%s)", investigation_id
                )
                break
            db_hypothesis = self.add_hypothesis(
                investigation_id=investigation_id,
                hypothesis=proposed.statement,
                status="active",
                basis=proposed.basis,
                priority=proposed.priority,
            )
            self.db.flush()
            existing_hypotheses[db_hypothesis.id] = db_hypothesis
            existing_statements.add(statement_key)
            active_count += 1

            # Attach the proposed hypothesis's evidence requirements.
            for request in proposed.evidence_needed:
                if request and request.strip():
                    self.add_evidence_request(
                        investigation_id,
                        request=request.strip(),
                        hypothesis_id=db_hypothesis.id,
                    )

        for hypothesis_update in state_update.hypotheses_updates:
            hypothesis_id = hypothesis_update.hypotheses_id

            hypothesis = existing_hypotheses.get(hypothesis_id)

            if hypothesis is None:
                logger.warning(
                    "Skipping invalid hypothesis update: "
                    "hypothesis_id=%s, investigation_id=%s",
                    hypothesis_id,
                    investigation_id,
                )
                continue

            hypothesis.status = hypothesis_update.status
            hypothesis.basis = hypothesis_update.basis   
            if hypothesis_update.priority is not None:
                hypothesis.priority = hypothesis_update.priority
            

        # -----------------------------------------------------
        # Evidence requests
        # -----------------------------------------------------

        existing_evidence = {
            evidence.request
            for evidence in self.get_evidence_requests(
                investigation_id
            )
        }

        for evidence in state_update.new_evidence_needed:

            if evidence not in existing_evidence:

                self.add_evidence_request(
                    investigation_id,
                    request=evidence,
                )

                existing_evidence.add(evidence)

        # -----------------------------------------------------
        # Current focus
        # -----------------------------------------------------
        if state_update.current_focus:
            self.update_current_focus(
                investigation_id,
                state_update.current_focus,
            )

        # -----------------------------------------------------
        # Investigation history
        # -----------------------------------------------------

        history_entry = " ".join(
            (state_update.history_entry or "Investigation state reviewed.").split()
        )[:400]
        if history_entry:
            self.add_history(investigation_id, history_entry)

        # -----------------------------------------------------
        # Persist
        # -----------------------------------------------------

        self.db.flush()

    # =========================================================
    # Load Investigation State
    # =========================================================

    def load_state(
        self,
        investigation_id: int,
    ):
        investigation = self.get_investigation(
            investigation_id
        )

        if investigation is None:
            raise ValueError(
                f"Investigation {investigation_id} not found."
            )

        facts = self.get_facts(
            investigation_id
        )

        hypotheses = self.get_hypotheses(
            investigation_id
        )

        evidence_requests = self.get_evidence_requests(
            investigation_id
        )

        history = self.get_history(
            investigation_id
        )

        return InvestigationState(
            problem=investigation.problem,
            business_context=investigation.business_context,
            confirmed_facts=[
                fact.content
                for fact in facts
            ],
            hypotheses=[
                Hypotheses(
                    id=hypothesis.id,
                    statement=hypothesis.statement,
                    basis=hypothesis.basis,
                    evidence_needed=[
                        request.request
                        for request in hypothesis.evidence_needed
                    ],
                    status=hypothesis.status,
                    priority=hypothesis.priority or "medium",
                )
                for hypothesis in hypotheses
            ],
            evidence_needed=[
                request.request
                for request in evidence_requests
                if request.status == "needed"
            ],
            current_focus=investigation.current_focus,
            investigation_history=[
                " ".join((item.entry or "").split())[:400]
                for item in history[-5:]
            ],
            dataset_id=investigation.dataset_id,
        )

    # =========================================================
    # Transaction
    # =========================================================

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
