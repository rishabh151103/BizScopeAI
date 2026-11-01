from Backend.schemas import (
    StateUpdate,
    HypothesesUpdate,
    InvestigationState,
    Hypotheses,
    BusinessDiagnosis,
)

from Backend.investigation_service import InvestigationService


def make_state_update(
    new_evidence_needed=None,
):
    return StateUpdate(
        new_facts=[],
        hypotheses_updates=[],
        new_evidence_needed=new_evidence_needed or [],
        current_focus="Determine the main cause of the revenue decline.",
        history_entry="Investigation state updated.",
    )


def make_investigation_state():
    return InvestigationState(
        problem="Revenue has declined.",
        business_context="Retail business.",
        confirmed_facts=[
            "Revenue declined during the observed period."
        ],
        hypotheses=[
            Hypotheses(
                id=1,
                statement="Customer retention has declined.",
                basis="The revenue decline may be related to repeat customer behavior.",
                evidence_needed=[
                    "Customer retention data"
                ],
                status="active",
            )
        ],
        evidence_needed=[],
        current_focus="Determine the main cause of the revenue decline.",
        investigation_history=[],
        dataset_id=1,
    )


def test_state_update_can_request_new_evidence():
    state_update = make_state_update(
        [
            "Analyze monthly revenue trend."
        ]
    )

    assert state_update.new_evidence_needed == [
        "Analyze monthly revenue trend."
    ]


def test_state_update_can_require_no_new_evidence():
    state_update = make_state_update()

    assert state_update.new_evidence_needed == []


def test_apply_state_update_creates_evidence_request():
    service = InvestigationService.__new__(InvestigationService)

    service.get_investigation = lambda investigation_id: object()
    service.get_facts = lambda investigation_id: []
    service.get_hypotheses = lambda investigation_id: []
    service.get_evidence_requests = lambda investigation_id: []

    added_requests = []

    def add_evidence_request(
        investigation_id,
        request,
        hypothesis_id=None,
        status="needed",
    ):
        added_requests.append(
            {
                "investigation_id": investigation_id,
                "request": request,
                "hypothesis_id": hypothesis_id,
                "status": status,
            }
        )

    service.add_evidence_request = add_evidence_request

    service.update_current_focus = lambda *args, **kwargs: None
    service.add_history = lambda *args, **kwargs: None
    service.db = type(
        "FakeDB",
        (),
        {
            "get": lambda *args, **kwargs: None,
            "flush": lambda *args, **kwargs: None,
        },
    )()

    state_update = make_state_update(
        [
            "Analyze monthly revenue trend."
        ]
    )

    service.apply_state_update(
        investigation_id=1,
        state_update=state_update,
    )

    assert len(added_requests) == 1
    assert added_requests[0]["investigation_id"] == 1
    assert (
        added_requests[0]["request"]
        == "Analyze monthly revenue trend."
    )


def test_apply_state_update_does_not_create_duplicate_evidence_request():
    service = InvestigationService.__new__(InvestigationService)

    service.get_investigation = lambda investigation_id: object()
    service.get_facts = lambda investigation_id: []
    service.get_hypotheses = lambda investigation_id: []

    existing_request = type(
        "EvidenceRequest",
        (),
        {
            "request": "Analyze monthly revenue trend."
        },
    )()

    service.get_evidence_requests = (
        lambda investigation_id: [existing_request]
    )

    added_requests = []

    service.add_evidence_request = (
        lambda *args, **kwargs: added_requests.append(
            kwargs.get("request")
        )
    )

    service.update_current_focus = lambda *args, **kwargs: None
    service.add_history = lambda *args, **kwargs: None

    service.db = type(
        "FakeDB",
        (),
        {
            "get": lambda *args, **kwargs: None,
            "flush": lambda *args, **kwargs: None,
        },
    )()

    state_update = make_state_update(
        [
            "Analyze monthly revenue trend."
        ]
    )

    service.apply_state_update(
        investigation_id=1,
        state_update=state_update,
    )

    assert added_requests == []


def test_investigation_state_contains_pending_evidence():
    state = make_investigation_state()

    state.evidence_needed.append(
        "Analyze monthly revenue trend."
    )

    assert (
        "Analyze monthly revenue trend."
        in state.evidence_needed
    )


def test_empty_evidence_requirement_means_no_evidence_step():
    state_update = make_state_update()

    assert not state_update.new_evidence_needed


def test_multiple_evidence_requirements_are_preserved():
    state_update = make_state_update(
        [
            "Analyze monthly revenue trend.",
            "Analyze customer retention.",
            "Analyze regional performance.",
        ]
    )

    assert len(state_update.new_evidence_needed) == 3

    assert (
        "Analyze monthly revenue trend."
        in state_update.new_evidence_needed
    )

    assert (
        "Analyze customer retention."
        in state_update.new_evidence_needed
    )

    assert (
        "Analyze regional performance."
        in state_update.new_evidence_needed
    )     
