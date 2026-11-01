from Backend.database import SessionLocal
from Backend.investigation_service import InvestigationService
from Backend.schemas import BusinessDiagnosis
import pandas as pd


def test_investigation_service_persistence():
    db = SessionLocal()

    try:
        service = InvestigationService(db)

        # ---------------------------------------------------------
        # Initial diagnosis -> persistent investigation state
        # ---------------------------------------------------------

        diagnosis = BusinessDiagnosis(
            problem_summary="Revenue declined in February.",
            confirmed_facts=[
                "February revenue was lower than January."
            ],
            hypotheses=[
                {
                    "id": 1,
                    "statement": "Monitor sales declined significantly.",
                    "basis": "Monitor revenue appears to have decreased.",
                    "evidence_needed": [
                        "Compare Monitor revenue between January and February."
                    ],
                    "status": "active",
                }
            ],
            conclusion=(
                "The revenue decline requires "
                "product-level investigation."
            ),
        )

        investigation = service.create_initial_state(
            diagnosis
        )

        service.commit()

        investigation_id = investigation.id

        # Reload the state from PostgreSQL.
        state = service.load_state(
            investigation_id
        )

        assert state.problem == (
            "Revenue declined in February."
        )

        assert state.confirmed_facts == [
            "February revenue was lower than January."
        ]

        assert len(state.hypotheses) == 1

        assert state.hypotheses[0].statement == (
            "Monitor sales declined significantly."
        )

        assert state.hypotheses[0].basis == (
            "Monitor revenue appears to have decreased."
        )

        assert state.hypotheses[0].status == "active"

        assert state.hypotheses[0].evidence_needed == [
            "Compare Monitor revenue between January and February."
        ]

        assert state.evidence_needed == [
            "Compare Monitor revenue between January and February."
        ]

        assert state.current_focus == (
            "The revenue decline requires "
            "product-level investigation."
        )

        assert state.investigation_history == [
            "Initial investigation created."
        ]

        # ---------------------------------------------------------
        # Other persistence operations
        # ---------------------------------------------------------

        service.add_message(
            investigation_id,
            "user",
            "Why did revenue fall in February?",
        )

        service.add_fact(
            investigation_id,
            "February revenue was lower than January.",
        )

        hypothesis = service.add_hypothesis(
            investigation_id,
            "Laptop sales may have changed.",
            status="active",
            basis="Further product-level investigation is required.",
        )

        service.add_evidence_request(
            investigation_id,
            "Compare Laptop revenue between January and February.",
            hypothesis_id=hypothesis.id,
        )

        service.add_analysis_run(
            investigation_id,
            analysis_name="segment_changes",
            requirement={
                "metric": "revenue",
                "dimension": "product",
                "operation": "change",
            },
            execution_parameters={
                "dimension": "product",
                "start_month": "2025-01",
                "end_month": "2025-02",
            },
            result_data={
                "Laptop": {
                    "revenue_change": 500
                }
            },
        )

        service.add_evidence(
            investigation_id,
            content="Laptop revenue increased by 500.",
            structured_data={
                "product": "Laptop",
                "revenue_change": 500,
            },
        )

        service.add_history(
            investigation_id,
            "Product-level revenue analysis was requested.",
        )

        service.update_current_focus(
            investigation_id,
            "Determine which product caused the revenue change.",
        )

        service.commit()

        # ---------------------------------------------------------
        # Reload everything through the service
        # ---------------------------------------------------------

        loaded = service.get_investigation(
            investigation_id
        )

        messages = service.get_messages(
            investigation_id
        )

        facts = service.get_facts(
            investigation_id
        )

        hypotheses = service.get_hypotheses(
            investigation_id
        )

        evidence_requests = service.get_evidence_requests(
            investigation_id
        )

        evidence = service.get_evidence(
            investigation_id
        )

        analysis_runs = service.get_analysis_runs(
            investigation_id
        )

        history = service.get_history(
            investigation_id
        )

        # Investigation
        assert loaded is not None

        assert loaded.problem == (
            "Revenue declined in February."
        )

        assert loaded.current_focus == (
            "Determine which product caused the revenue change."
        )

        # Messages
        assert len(messages) == 1

        assert messages[0].content == (
            "Why did revenue fall in February?"
        )

        # Facts
        assert len(facts) == 2

        assert facts[0].content == (
            "February revenue was lower than January."
        )

        # Hypotheses
        assert len(hypotheses) == 2

        assert hypotheses[0].statement == (
            "Monitor sales declined significantly."
        )

        assert hypotheses[1].statement == (
            "Laptop sales may have changed."
        )

        # Evidence requests
        assert len(evidence_requests) == 2

        assert any(
            request.request
            == "Compare Monitor revenue between January and February."
            for request in evidence_requests
        )

        assert any(
            request.request
            == "Compare Laptop revenue between January and February."
            for request in evidence_requests
        )

        # Evidence
        assert len(evidence) == 1

        assert evidence[0].content == (
            "Laptop revenue increased by 500."
        )

        # Analysis runs
        assert len(analysis_runs) == 1

        assert analysis_runs[0].analysis_name == (
            "segment_changes"
        )

        # History
        assert len(history) == 2

        assert history[0].entry == (
            "Initial investigation created."
        )

        assert history[1].entry == (
            "Product-level revenue analysis was requested."
        )

        # ---------------------------------------------------------
        # Reconstruct the complete V1 state again
        # ---------------------------------------------------------

        final_state = service.load_state(
            investigation_id
        )

        assert final_state.problem == (
            "Revenue declined in February."
        )

        assert len(final_state.confirmed_facts) == 2

        assert len(final_state.hypotheses) == 2

        assert final_state.current_focus == (
            "Determine which product caused the revenue change."
        )

        assert len(final_state.evidence_needed) == 2

        assert len(final_state.investigation_history) == 2

    finally:
        db.close()


def test_load_state_preserves_dataset_id(monkeypatch):
    
    class MockInvestigation:
        id = 1
        dataset_id = 42
        problem = "Revenue is declining"
        business_context = ""
        current_focus = "Revenue decline"

    class MockDB:
        pass

    service = InvestigationService(MockDB())

    monkeypatch.setattr(
        service,
        "get_investigation",
        lambda investigation_id: MockInvestigation(),
    )

    monkeypatch.setattr(
        service,
        "get_facts",
        lambda investigation_id: [],
    )

    monkeypatch.setattr(
        service,
        "get_hypotheses",
        lambda investigation_id: [],
    )

    monkeypatch.setattr(
        service,
        "get_evidence_requests",
        lambda investigation_id: [],
    )

    monkeypatch.setattr(
        service,
        "get_history",
        lambda investigation_id: [],
    )

    state = service.load_state(1)

    assert state.dataset_id == 42        


def test_execute_analysis_selection_persists_analysis_run(
    monkeypatch,
):

    class MockDB:
        def flush(self):
            pass

    service = InvestigationService(MockDB())

    class MockAnalysisRun:
        id = 1
        analysis_name = "revenue_trend"
        status = "completed"

    def fake_execute_analysis(df, selection):

        assert isinstance(df, pd.DataFrame)
        assert selection.analysis_name == "revenue_trend"

        return {
            "trend": "increasing",
            "summary": pd.DataFrame(
                {
                    "Month": [
                        "January",
                        "February",
                    ],
                    "Revenue": [
                        100,
                        125,
                    ],
                }
            ),
        }

    def fake_resolve_execution_parameters(selection):
        return {}

    def fake_add_analysis_run(
        investigation_id,
        analysis_name,
        requirement=None,
        execution_parameters=None,
        result_data=None,
        status="completed",
    ):

        assert investigation_id == 10
        assert analysis_name == "revenue_trend"

        assert requirement["metric"] == "revenue"

        assert execution_parameters == {}

        assert result_data["trend"] == "increasing"

        assert result_data["summary"] == [
            {
                "Month": "January",
                "Revenue": 100,
            },
            {
                "Month": "February",
                "Revenue": 125,
            },
        ]

        assert status == "completed"

        return MockAnalysisRun()

    monkeypatch.setattr(
        "Backend.analysis_executor.execute_analysis",
        fake_execute_analysis,
    )

    monkeypatch.setattr(
        "Backend.execution_resolver.resolve_execution_parameters",
        fake_resolve_execution_parameters,
    )

    monkeypatch.setattr(
        service,
        "add_analysis_run",
        fake_add_analysis_run,
    )

    class Requirement:

        def model_dump(self):
            return {
                "requirement": "Determine revenue trend",
                "metric": "revenue",
                "dimension": "time",
                "operation": "trend",
                "start_month": None,
                "end_month": None,
            }

    class Selection:
        analysis_name = "revenue_trend"
        requirement = Requirement()

    df = pd.DataFrame(
        {
            "month": [
                "2025-01",
                "2025-02",
            ],
            "revenue": [
                100,
                125,
            ],
        }
    )

    result = service.execute_analysis_selection(
        investigation_id=10,
        df=df,
        selection=Selection(),
    )

    assert result.id == 1
    assert result.analysis_name == "revenue_trend"
    assert result.status == "completed"

    def fake_resolve_execution_parameters(selection):
        return {}

    def fake_add_analysis_run(
        investigation_id,
        analysis_name,
        requirement=None,
        execution_parameters=None,
        result_data=None,
        status="completed",
    ):
        assert investigation_id == 10
        assert analysis_name == "revenue_trend"
        assert requirement["metric"] == "revenue"
        assert execution_parameters == {}
        assert result_data["trend"] == "increasing"
        assert result_data["summary"] == [
    {
        "Month": "January",
        "Revenue": 100,
    },
    {
        "Month": "February",
        "Revenue": 125,
    },
    ]
        assert status == "completed"

        return MockAnalysisRun()

    monkeypatch.setattr(
        "Backend.analysis_executor.execute_analysis",
        fake_execute_analysis,
    )

    monkeypatch.setattr(
        "Backend.execution_resolver.resolve_execution_parameters",
        fake_resolve_execution_parameters,
    )

    monkeypatch.setattr(
        service,
        "add_analysis_run",
        fake_add_analysis_run,
    )

    class Requirement:
        def model_dump(self):
            return {
                "requirement": "Determine revenue trend",
                "metric": "revenue",
                "dimension": "time",
                "operation": "trend",
                "start_month": None,
                "end_month": None,
            }

    class Selection:
        analysis_name = "revenue_trend"
        requirement = Requirement()

    result = service.execute_analysis_selection(
        investigation_id=10,
        df=pd.DataFrame(
            {
                "month": ["2025-01", "2025-02"],
                "revenue": [100, 125],
            }
        ),
        selection=Selection(),
    )

    assert result.id == 1
    assert result.analysis_name == "revenue_trend"
    assert result.status == "completed"  