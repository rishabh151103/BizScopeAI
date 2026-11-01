from Backend.database import SessionLocal
from Backend.investigation_service import InvestigationService
from Backend.schemas import StateUpdate


def create_service():
    db = SessionLocal()
    return db, InvestigationService(db)


def create_investigation(service):
    investigation = service.create_investigation(
        problem="Revenue decline",
        business_context="E-commerce business",
        current_focus="Revenue decline",
    )

    service.commit()

    return investigation


def test_new_facts_are_added():
    db, service = create_service()

    try:
        investigation = create_investigation(service)

        update = StateUpdate(
            new_facts=[
                "Revenue declined by 20%",
                "Decline started in January",
            ],
            hypotheses_updates=[],
            new_evidence_needed=[],
            current_focus="Investigate revenue decline",
            history_entry="Revenue decline confirmed.",
        )

        service.apply_state_update(
            investigation.id,
            update,
        )

        service.commit()

        state = service.load_state(
            investigation.id
        )

        assert state.confirmed_facts == [
            "Revenue declined by 20%",
            "Decline started in January",
        ]

    finally:
        db.close()


def test_duplicate_facts_are_not_added():
    db, service = create_service()

    try:
        investigation = create_investigation(service)

        service.add_fact(
            investigation.id,
            "Revenue declined by 20%",
        )

        service.commit()

        update = StateUpdate(
            new_facts=[
                "Revenue declined by 20%",
                "Revenue declined by 10%",
            ],
            hypotheses_updates=[],
            new_evidence_needed=[],
            current_focus="Investigate revenue decline",
            history_entry="New revenue information received.",
        )

        service.apply_state_update(
            investigation.id,
            update,
        )

        service.commit()

        state = service.load_state(
            investigation.id
        )

        assert state.confirmed_facts == [
            "Revenue declined by 20%",
            "Revenue declined by 10%",
        ]

    finally:
        db.close()


def test_hypothesis_is_updated():
    db, service = create_service()

    try:
        investigation = create_investigation(service)

        hypothesis = service.add_hypothesis(
            investigation.id,
            hypothesis="Customers are buying less",
            status="active",
            basis="Initial assumption",
        )

        service.commit()

        update = StateUpdate(
            new_facts=[],
            hypotheses_updates=[
                {
                    "hypotheses_id": hypothesis.id,
                    "status": "supported",
                    "basis": (
                        "Customer sales data confirms "
                        "the decline."
                    ),
                }
            ],
            new_evidence_needed=[],
            current_focus="Customer demand",
            history_entry=(
                "Customer demand hypothesis strengthened."
            ),
        )

        service.apply_state_update(
            investigation.id,
            update,
        )

        service.commit()

        state = service.load_state(
            investigation.id
        )

        assert state.hypotheses[0].status == "supported"

        assert (
            state.hypotheses[0].basis
            == "Customer sales data confirms the decline."
        )

    finally:
        db.close()


def test_new_evidence_is_added():
    db, service = create_service()

    try:
        investigation = create_investigation(service)

        update = StateUpdate(
            new_facts=[],
            hypotheses_updates=[],
            new_evidence_needed=[
                "Customer purchase history",
                "Pricing data",
            ],
            current_focus="Investigate customer behavior",
            history_entry="Additional evidence identified.",
        )

        service.apply_state_update(
            investigation.id,
            update,
        )

        service.commit()

        state = service.load_state(
            investigation.id
        )

        assert state.evidence_needed == [
            "Customer purchase history",
            "Pricing data",
        ]

    finally:
        db.close()


def test_duplicate_evidence_is_not_added():
    db, service = create_service()

    try:
        investigation = create_investigation(service)

        service.add_evidence_request(
            investigation.id,
            request="Customer purchase history",
        )

        service.commit()

        update = StateUpdate(
            new_facts=[],
            hypotheses_updates=[],
            new_evidence_needed=[
                "Customer purchase history",
                "Pricing data",
            ],
            current_focus="Investigate customer behavior",
            history_entry="Additional evidence identified.",
        )

        service.apply_state_update(
            investigation.id,
            update,
        )

        service.commit()

        state = service.load_state(
            investigation.id
        )

        assert state.evidence_needed == [
            "Customer purchase history",
            "Pricing data",
        ]

    finally:
        db.close()


def test_current_focus_is_updated():
    db, service = create_service()

    try:
        investigation = create_investigation(service)

        update = StateUpdate(
            new_facts=[],
            hypotheses_updates=[],
            new_evidence_needed=[],
            current_focus="Investigate returning customers",
            history_entry="Investigation focus changed.",
        )

        service.apply_state_update(
            investigation.id,
            update,
        )

        service.commit()

        state = service.load_state(
            investigation.id
        )

        assert (
            state.current_focus
            == "Investigate returning customers"
        )

    finally:
        db.close()


def test_history_entry_is_added():
    db, service = create_service()

    try:
        investigation = create_investigation(service)

        update = StateUpdate(
            new_facts=[],
            hypotheses_updates=[],
            new_evidence_needed=[],
            current_focus="Investigate revenue decline",
            history_entry=(
                "New evidence indicates customer churn."
            ),
        )

        service.apply_state_update(
            investigation.id,
            update,
        )

        service.commit()

        state = service.load_state(
            investigation.id
        )

        assert state.investigation_history == [
            "New evidence indicates customer churn.",
        ]

    finally:
        db.close()


def test_complete_state_update():
    db, service = create_service()

    try:
        investigation = create_investigation(service)

        hypothesis = service.add_hypothesis(
            investigation.id,
            hypothesis="Customer churn caused the decline",
            status="active",
            basis="Initial assumption",
        )

        service.commit()

        update = StateUpdate(
            new_facts=[
                "Returning customer revenue declined",
            ],
            hypotheses_updates=[
                {
                    "hypotheses_id": hypothesis.id,
                    "status": "supported",
                    "basis": (
                        "Returning customer revenue "
                        "declined significantly."
                    ),
                }
            ],
            new_evidence_needed=[
                "Customer retention data",
            ],
            current_focus="Investigate customer retention",
            history_entry=(
                "Returning customer decline confirmed."
            ),
        )

        service.apply_state_update(
            investigation.id,
            update,
        )

        service.commit()

        state = service.load_state(
            investigation.id
        )

        assert state.confirmed_facts == [
            "Returning customer revenue declined"
        ]

        assert (
            state.hypotheses[0].status
            == "supported"
        )

        assert (
            state.hypotheses[0].basis
            == "Returning customer revenue "
               "declined significantly."
        )

        assert state.evidence_needed == [
            "Customer retention data"
        ]

        assert (
            state.current_focus
            == "Investigate customer retention"
        )

        assert state.investigation_history == [
            "Returning customer decline confirmed.",
        ]

    finally:
        db.close()