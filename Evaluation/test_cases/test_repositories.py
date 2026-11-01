from Backend.repositories import (
    DatasetRepository,
    InvestigationRepository,
    MessageRepository,
    EvidenceRepository,
    AnalysisRunRepository,
    EvidenceRequestRepository,
    InvestigationHistoryRepository,
)


class MockResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def __iter__(self):
        return iter(self.value)


class MockDB:
    def __init__(self, result):
        self.result = result
        self.added = []
        self.flushed = False

    def execute(self, statement):
        return MockResult(self.result)

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flushed = True


def test_dataset_repository_get():
    dataset = object()
    db = MockDB(dataset)

    result = DatasetRepository.get(db, 1)

    assert result is dataset


def test_investigation_repository_create():
    db = MockDB(None)

    result = InvestigationRepository.create(
        db,
        problem="Revenue is declining",
        business_context="Retail business",
        current_focus="Revenue trend",
        dataset_id=42,
    )

    assert result.problem == "Revenue is declining"
    assert result.business_context == "Retail business"
    assert result.current_focus == "Revenue trend"
    assert result.dataset_id == 42
    assert result in db.added
    assert db.flushed is True


def test_investigation_repository_get():
    investigation = object()
    db = MockDB(investigation)

    result = InvestigationRepository.get(db, 1)

    assert result is investigation


def test_message_repository_add():
    db = MockDB(None)

    result = MessageRepository.add(
        db,
        investigation_id=1,
        role="user",
        content="Why is revenue declining?",
    )

    assert result.investigation_id == 1
    assert result.role == "user"
    assert result.content == "Why is revenue declining?"
    assert result in db.added
    assert db.flushed is True


def test_message_repository_get_for_investigation():
    messages = [object(), object()]
    db = MockDB(messages)

    result = MessageRepository.get_for_investigation(db, 1)

    assert result == messages


def test_evidence_repository_add():
    db = MockDB(None)

    result = EvidenceRepository.add(
        db,
        investigation_id=1,
        content="Revenue decreased by 20%.",
        structured_data={"change_percent": -20},
        analysis_run_id=5,
    )

    assert result.investigation_id == 1
    assert result.content == "Revenue decreased by 20%."
    assert result.structured_data == {"change_percent": -20}
    assert result.analysis_run_id == 5
    assert result in db.added
    assert db.flushed is True


def test_evidence_repository_get_for_investigation():
    evidence = [object(), object()]
    db = MockDB(evidence)

    result = EvidenceRepository.get_for_investigation(db, 1)

    assert result == evidence


def test_analysis_run_repository_add():
    db = MockDB(None)

    result = AnalysisRunRepository.add(
        db,
        investigation_id=1,
        analysis_name="revenue_trend",
        requirement={"metric": "revenue"},
        execution_parameters={},
        result_data={"trend": "declining"},
    )

    assert result.investigation_id == 1
    assert result.analysis_name == "revenue_trend"
    assert result.requirement == {"metric": "revenue"}
    assert result.execution_parameters == {}
    assert result.result_data == {"trend": "declining"}
    assert result.status == "completed"
    assert result in db.added
    assert db.flushed is True


def test_analysis_run_repository_get_for_investigation():
    analysis_runs = [object(), object()]
    db = MockDB(analysis_runs)

    result = AnalysisRunRepository.get_for_investigation(db, 1)

    assert result == analysis_runs


def test_evidence_request_repository_add():
    db = MockDB(None)

    result = EvidenceRequestRepository.add(
        db,
        investigation_id=1,
        request="Analyze monthly revenue trend.",
        hypothesis_id=7,
    )

    assert result.investigation_id == 1
    assert result.request == "Analyze monthly revenue trend."
    assert result.hypothesis_id == 7
    assert result.status == "needed"
    assert result in db.added
    assert db.flushed is True


def test_evidence_request_repository_get_for_investigation():
    requests = [object(), object()]
    db = MockDB(requests)

    result = EvidenceRequestRepository.get_for_investigation(db, 1)

    assert result == requests


def test_investigation_history_repository_add():
    db = MockDB(None)

    result = InvestigationHistoryRepository.add(
        db,
        investigation_id=1,
        entry="Revenue trend analysis completed.",
    )

    assert result.investigation_id == 1
    assert result.entry == "Revenue trend analysis completed."
    assert result in db.added
    assert db.flushed is True


def test_investigation_history_repository_get_for_investigation():
    history = [object(), object()]
    db = MockDB(history)

    result = InvestigationHistoryRepository.get_for_investigation(db, 1)

    assert result == history