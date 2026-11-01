from fastapi.testclient import TestClient

from Backend.main import app

from unittest.mock import Mock

from Backend import main
from Backend.dataset_service import DatasetService


client = TestClient(app)


def test_dataset_upload_success():
    csv_content = (
        "Order ID,Revenue,Profit\n"
        "1,100,20\n"
        "2,200,50\n"
    )

    response = client.post(
        "/datasets/upload",
        files={
            "file": (
                "test_dataset.csv",
                csv_content,
                "text/csv",
            )
        },
    )

    assert response.status_code == 200,response.text

    data = response.json()

    assert "dataset_id" in data
    assert data["filename"] == "test_dataset.csv"
    assert data["rows"] == 2
    assert data["columns"] == 3


def test_dataset_upload_rejects_non_csv():
    response = client.post(
        "/datasets/upload",
        files={
            "file": (
                "test_dataset.txt",
                "some text",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only CSV files are supported."


def test_dataset_upload_requires_file():
    response = client.post("/datasets/upload")

    assert response.status_code == 422


def test_dataset_upload_rejects_oversized_csv(monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 8)
    response = client.post(
        "/datasets/upload",
        files={"file": ("large.csv", "a,b\n123,456\n", "text/csv")},
    )

    assert response.status_code == 413
    assert "size limit" in response.json()["detail"]


def test_dataset_upload_rejects_empty_csv():
    response = client.post(
        "/datasets/upload",
        files={"file": ("empty.csv", b"", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded CSV is empty."


def test_liveness_endpoint_does_not_need_database():
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert len(response.headers["x-request-id"]) == 32


def test_request_log_has_timing_and_no_user_input(caplog):
    with caplog.at_level("INFO", logger="Backend.main"):
        response = client.post(
            "/health/live?private=private-revenue-detail",
            json={"message": "private revenue detail"},
        )

    assert response.status_code == 405
    assert response.headers.get("x-request-id")
    assert "http_request" in caplog.text
    assert "duration_ms=" in caplog.text
    assert "private revenue detail" not in caplog.text
    assert "private-revenue-detail" not in caplog.text


def test_readiness_endpoint_checks_database(monkeypatch):
    class HealthyDatabase:
        def execute(self, statement):
            assert str(statement) == "SELECT 1"

    def override_get_db():
        yield HealthyDatabase()

    main.app.dependency_overrides[main.get_db] = override_get_db
    try:
        response = client.get("/health/ready")
    finally:
        main.app.dependency_overrides.pop(main.get_db, None)

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_endpoint_returns_503_when_database_is_down():
    class UnavailableDatabase:
        def execute(self, statement):
            raise RuntimeError("private connection detail")

    def override_get_db():
        yield UnavailableDatabase()

    main.app.dependency_overrides[main.get_db] = override_get_db
    try:
        response = client.get("/health/ready")
    finally:
        main.app.dependency_overrides.pop(main.get_db, None)

    assert response.status_code == 503
    assert response.json()["detail"] == "Database is unavailable."
    assert "private connection detail" not in response.text


def test_dataset_upload_uses_request_scoped_db(monkeypatch):

    fake_db=Mock()
    fake_dataset=Mock(
        id=123,
        filename="test_dataset.csv",
        row_count=2,
        column_count=3
    )

    class FakeDatasetService:
        def __init__(self, db):
            assert db is fake_db

        def ingest_dataset(self, uploaded_file):
            return fake_dataset

    monkeypatch.setattr(
        main,
        "DatasetService",
        FakeDatasetService,
    )

    def override_get_db():
        yield fake_db

    main.app.dependency_overrides[main.get_db] = override_get_db

    try:
        response = client.post(
            "/datasets/upload",
            files={
                "file": (
                    "test_dataset.csv",
                    "Order ID,Revenue,Profit\n1,100,20\n2,200,50\n",
                    "text/csv",
                )
            },
        )

        assert response.status_code == 200, response.text
        assert response.json()["dataset_id"] == 123

    finally:
        main.app.dependency_overrides.pop(main.get_db, None)
