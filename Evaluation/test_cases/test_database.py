from sqlalchemy import select

from Backend.database import SessionLocal
from Backend.db_models import (
    Dataset,
    Fact,
    Hypothesis,
)
from Backend.repositories import (
    AnalysisRunRepository,
    EvidenceRepository,
    InvestigationRepository,
    MessageRepository,
)


def test_repository_persistence_integration():

    with SessionLocal() as db:

        dataset = Dataset(
            filename="repository_test.csv",
            row_count=10,
            column_count=6,
        )

        db.add(dataset)
        db.flush()

        investigation = InvestigationRepository.create(
            db=db,
            problem="Why did revenue change?",
            business_context="Repository integration test.",
            current_focus="Revenue",
            dataset_id=dataset.id,
        )

        MessageRepository.add(
            db=db,
            investigation_id=investigation.id,
            role="user",
            content="Why did revenue change?",
        )

        investigation.facts.append(
            Fact(
        content="Revenue changed between two periods."
        )
    )

        hypothesis = Hypothesis(
            investigation_id=investigation.id,
            statement="Product performance affected revenue.",
            basis="Product-level evidence is required.",
            status="active",
        )

        db.add(hypothesis)
        db.flush()

        analysis_run = AnalysisRunRepository.add(
            db=db,
            investigation_id=investigation.id,
            analysis_name="segment_changes",
            requirement={
                "metric": "revenue",
                "dimension": "product",
                "operation": "change",
                "start_month": "2025-01",
                "end_month": "2025-02",
            },
            execution_parameters={
                "dimension": "product",
                "start_month": "2025-01",
                "end_month": "2025-02",
            },
            result_data={
                "Laptop": {
                    "start_revenue": 1200,
                    "end_revenue": 1700,
                }
            },
        )

        EvidenceRepository.add(
            db=db,
            investigation_id=investigation.id,
            analysis_run_id=analysis_run.id,
            content="Laptop revenue increased from 1200 to 1700.",
            structured_data={
                "product": "Laptop",
                "start_revenue": 1200,
                "end_revenue": 1700,
            },
        )

        db.commit()

        investigation_id = investigation.id

    with SessionLocal() as db:

        saved = InvestigationRepository.get(
            db,
            investigation_id,
        )

        assert saved is not None
        assert saved.problem == "Why did revenue change?"

        messages = MessageRepository.get_for_investigation(
            db,
            investigation_id,
        )

        evidence = EvidenceRepository.get_for_investigation(
            db,
            investigation_id,
        )

        analysis_runs = AnalysisRunRepository.get_for_investigation(
            db,
            investigation_id,
        )

        assert len(messages) == 1
        assert len(evidence) == 1
        assert len(analysis_runs) == 1

        assert analysis_runs[0].analysis_name == (
            "segment_changes"
        )

        assert evidence[0].structured_data["product"] == (
            "Laptop"
        )

        assert evidence[0].analysis_run_id == (
            analysis_runs[0].id
        )

