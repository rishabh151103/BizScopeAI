from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .db_models import (
    AnalysisRun,
    Dataset,
    Evidence,
    EvidenceRequest,
    Investigation,
    InvestigationHistory,
    Message,
)


class DatasetRepository:

    @staticmethod
    def get(
        db: Session,
        dataset_id: int,
    ) -> Dataset | None:

        return db.execute(
            select(Dataset)
            .where(
                Dataset.id == dataset_id
            )
        ).scalar_one_or_none()


class InvestigationRepository:

    @staticmethod
    def create(
        db: Session,
        problem: str,
        business_context: str = "",
        current_focus: str = "",
        dataset_id: int | None = None,
    ) -> Investigation:

        investigation = Investigation(
            problem=problem,
            business_context=business_context,
            current_focus=current_focus,
            dataset_id=dataset_id,
        )

        db.add(investigation)
        db.flush()

        return investigation

    @staticmethod
    def get(
        db: Session,
        investigation_id: int,
    ) -> Investigation | None:

        return db.execute(
            select(Investigation)
            .where(
                Investigation.id == investigation_id
            )
        ).scalar_one_or_none()


class MessageRepository:

    @staticmethod
    def add(
        db: Session,
        investigation_id: int,
        role: str,
        content: str,
    ) -> Message:

        message = Message(
            investigation_id=investigation_id,
            role=role,
            content=content,
        )

        db.add(message)
        db.flush()
        db.execute(
            update(Investigation)
            .where(Investigation.id == investigation_id)
            .values(updated_at=func.now())
        )

        return message

    @staticmethod
    def get_for_investigation(
        db: Session,
        investigation_id: int,
    ) -> list[Message]:

        return list(
            db.execute(
                select(Message)
                .where(
                    Message.investigation_id
                    == investigation_id
                )
                .order_by(Message.created_at, Message.id)
            ).scalars()
        )


class EvidenceRepository:

    @staticmethod
    def add(
        db: Session,
        investigation_id: int,
        content: str,
        structured_data=None,
        analysis_run_id: int | None = None,
    ) -> Evidence:

        evidence = Evidence(
            investigation_id=investigation_id,
            analysis_run_id=analysis_run_id,
            content=content,
            structured_data=structured_data,
        )

        db.add(evidence)
        db.flush()

        return evidence

    @staticmethod
    def get_for_investigation(
        db: Session,
        investigation_id: int,
    ) -> list[Evidence]:

        return list(
            db.execute(
                select(Evidence)
                .where(
                    Evidence.investigation_id
                    == investigation_id
                )
                .order_by(Evidence.created_at, Evidence.id)
            ).scalars()
        )


class AnalysisRunRepository:

    @staticmethod
    def add(
        db: Session,
        investigation_id: int,
        analysis_name: str,
        requirement=None,
        execution_parameters=None,
        result_data=None,
        status: str = "completed",
    ) -> AnalysisRun:

        analysis_run = AnalysisRun(
            investigation_id=investigation_id,
            analysis_name=analysis_name,
            requirement=requirement,
            execution_parameters=execution_parameters,
            result_data=result_data,
            status=status,
        )

        db.add(analysis_run)
        db.flush()

        return analysis_run

    @staticmethod
    def get_for_investigation(
        db: Session,
        investigation_id: int,
    ) -> list[AnalysisRun]:

        return list(
            db.execute(
                select(AnalysisRun)
                .where(
                    AnalysisRun.investigation_id
                    == investigation_id
                )
                .order_by(
                    AnalysisRun.created_at,
                    AnalysisRun.id,
                )
            ).scalars()
        )


class EvidenceRequestRepository:

    @staticmethod
    def add(
        db: Session,
        investigation_id: int,
        request: str,
        hypothesis_id: int | None = None,
        status: str = "needed",
    ) -> EvidenceRequest:

        evidence_request = EvidenceRequest(
            investigation_id=investigation_id,
            hypothesis_id=hypothesis_id,
            request=request,
            status=status,
        )

        db.add(evidence_request)
        db.flush()

        return evidence_request

    @staticmethod
    def get_for_investigation(
        db: Session,
        investigation_id: int,
    ) -> list[EvidenceRequest]:

        return list(
            db.execute(
                select(EvidenceRequest)
                .where(
                    EvidenceRequest.investigation_id
                    == investigation_id
                )
                .order_by(
                    EvidenceRequest.created_at,
                    EvidenceRequest.id,
                )
            ).scalars()
        )


class InvestigationHistoryRepository:

    @staticmethod
    def add(
        db: Session,
        investigation_id: int,
        entry: str,
    ) -> InvestigationHistory:

        history = InvestigationHistory(
            investigation_id=investigation_id,
            entry=entry,
        )

        db.add(history)
        db.flush()

        return history

    @staticmethod
    def get_for_investigation(
        db: Session,
        investigation_id: int,
    ) -> list[InvestigationHistory]:

        return list(
            db.execute(
                select(InvestigationHistory)
                .where(
                    InvestigationHistory.investigation_id
                    == investigation_id
                )
                .order_by(
                    InvestigationHistory.created_at,
                    InvestigationHistory.id,
                )
            ).scalars()
        )
