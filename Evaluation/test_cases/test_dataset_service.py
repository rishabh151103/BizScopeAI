import pandas as pd
import pytest

from Backend.dataset_service import DatasetService
from Backend.repositories import DatasetRepository
from Backend.db_models import Dataset


class MockUploadedFile:

    def __init__(self, filename, content):
        self.name = filename
        self._content = content

    def read(self):
        return self._content


class MockDatabase:

    def __init__(self):
        self.added_objects = []
        self.committed = False
        self.refreshed_objects = []

    def add(self, obj):
        self.added_objects.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed_objects.append(obj)


def test_dataset_service_initializes():

    service = DatasetService(db=None)

    assert service.db is None


def test_dataset_service_persists_dataset(
    monkeypatch,
    tmp_path,
):

    expected_df = pd.DataFrame(
        {
            "date": ["2025-01-01"],
            "revenue": [1000],
        }
    )

    expected_result = {
        "data": expected_df,
        "profile": {
            "rows": 1,
            "columns": 2,
        },
        "warnings": [],
        "changes": [],
        "column_types": {
            "date": "datetime",
            "revenue": "numeric",
        },
        "column_mapping": {
            "date": "date",
            "revenue": "revenue",
        },
    }

    def mock_prepare_uploaded_dataset(uploaded_file):
        return expected_result

    monkeypatch.setattr(
        "Backend.dataset_service.prepare_uploaded_dataset",
        mock_prepare_uploaded_dataset,
    )

    monkeypatch.setattr(
        "Backend.dataset_service.DATASET_STORAGE_DIR",
        tmp_path,
    )

    db = MockDatabase()

    service = DatasetService(db=db)

    uploaded_file = MockUploadedFile(
        "sales.csv",
        b"date,revenue\n2025-01-01,1000",
    )

    result = service.ingest_dataset(uploaded_file)

    # Dataset object was created
    assert len(db.added_objects) == 1

    dataset = db.added_objects[0]

    # Basic dataset information
    assert dataset.filename == "sales.csv"
    assert dataset.row_count == 1
    assert dataset.column_count == 2

    # Metadata was persisted
    assert dataset.profile_json == expected_result["profile"]
    assert dataset.warnings == expected_result["warnings"]
    assert dataset.changes == expected_result["changes"]
    assert dataset.column_mapping == expected_result["column_mapping"]

    # Database transaction occurred
    assert db.committed is True
    assert dataset in db.refreshed_objects

    # Returned object is the persisted Dataset
    assert result is dataset

    # CSV was actually written to storage
    saved_files = list(tmp_path.glob("*.csv"))
    assert len(saved_files) == 1
    saved_file = saved_files[0]
    assert dataset.storage_path == str(saved_file)

    saved_df = pd.read_csv(saved_file)

    assert list(saved_df.columns) == [
        "date",
        "revenue",
    ]

    assert len(saved_df) == 1
    assert saved_df["revenue"].iloc[0] == 1000


def test_dataset_service_rolls_back_on_database_failure(
    monkeypatch,
    tmp_path,
):

    expected_df = pd.DataFrame(
        {
            "date": ["2025-01-01"],
            "revenue": [1000],
        }
    )

    expected_result = {
        "data": expected_df,
        "profile": {},
        "warnings": [],
        "changes": [],
        "column_types": {},
        "column_mapping": {},
    }

    monkeypatch.setattr(
        "Backend.dataset_service.prepare_uploaded_dataset",
        lambda uploaded_file: expected_result,
    )

    monkeypatch.setattr(
        "Backend.dataset_service.DATASET_STORAGE_DIR",
        tmp_path,
    )

    class FailingDatabase(MockDatabase):

        def rollback(self):
            self.rolled_back = True

        def commit(self):
            raise RuntimeError("Database failure")

    db = FailingDatabase()
    db.rolled_back = False

    service = DatasetService(db=db)

    uploaded_file = MockUploadedFile(
        "sales.csv",
        b"date,revenue\n2025-01-01,1000",
    )

    with pytest.raises(
        RuntimeError,
        match="Database failure",
    ):
        service.ingest_dataset(uploaded_file)

    assert db.rolled_back is True
    assert list(tmp_path.glob("*.csv")) == []


def test_dataset_service_uses_unique_storage_for_same_filename(
    monkeypatch,
    tmp_path,
):
    expected_df = pd.DataFrame({"revenue": [100, 200]})
    prepared = {
        "data": expected_df,
        "profile": {},
        "warnings": [],
        "changes": [],
        "column_types": {},
        "column_mapping": {"revenue": "revenue"},
    }
    monkeypatch.setattr(
        "Backend.dataset_service.prepare_uploaded_dataset",
        lambda uploaded_file: prepared,
    )
    monkeypatch.setattr(
        "Backend.dataset_service.DATASET_STORAGE_DIR",
        tmp_path,
    )

    first = DatasetService(MockDatabase()).ingest_dataset(
        MockUploadedFile("sales.csv", b"revenue\n100\n")
    )
    second = DatasetService(MockDatabase()).ingest_dataset(
        MockUploadedFile("sales.csv", b"revenue\n200\n")
    )

    assert first.filename == second.filename == "sales.csv"
    assert first.storage_path != second.storage_path
    assert len(list(tmp_path.glob("*.csv"))) == 2


def test_dataset_service_loads_dataset_for_analysis(
    monkeypatch,
):

    class MockDataset:

        storage_path = "N:/BizScopeAI/dataset/sales.csv"

        column_mapping = {
            "date": "date",
            "revenue": "revenue",
            "profit": "profit",
        }

        metadata_json = {
            "column_types": {
                "datetime": ["date"],
                "numerical": [
                    "revenue",
                    "profit",
                ],
            }
        }

    raw_df = pd.DataFrame(
        {
            "date": ["2025-01-01"],
            "revenue": [1000],
            "profit": [200],
        }
    )

    adapted_df = pd.DataFrame(
        {
            "date": ["2025-01-01"],
            "revenue": [1000],
            "profit": [200],
            "cost": [800],
            "profit_margin_percent": [20.0],
        }
    )

    class MockDatabase:
        pass

    service = DatasetService(
        db=MockDatabase()
    )

    monkeypatch.setattr(
        "Backend.dataset_service.DatasetRepository.get",
        lambda db, dataset_id: MockDataset(),
    )

    monkeypatch.setattr(
        "Backend.dataset_service.Path.exists",
        lambda self: True,
    )

    monkeypatch.setattr(
        "Backend.dataset_service.load_dataset",
        lambda path: raw_df,
    )

    monkeypatch.setattr(
        "Backend.dataset_service.adapt_dataset",
        lambda df, mapping: adapted_df,
    )

    result = service.load_dataset_for_analysis(1)

    assert isinstance(result, pd.DataFrame)

    assert list(result.columns) == [
        "date",
        "revenue",
        "profit",
        "cost",
        "profit_margin_percent",
    ]

    assert result["revenue"].iloc[0] == 1000
    assert result["profit"].iloc[0] == 200
    assert result["cost"].iloc[0] == 800
    assert result["profit_margin_percent"].iloc[0] == 20.0


def test_dataset_service_analysis_dataset_not_found(
    monkeypatch,
):

    class MockDatabase:
        pass

    service = DatasetService(
        db=MockDatabase()
    )

    monkeypatch.setattr(
        "Backend.dataset_service.DatasetRepository.get",
        lambda db, dataset_id: None,
    )

    with pytest.raises(
        ValueError,
        match="Dataset with id 999 was not found",
    ):
        service.load_dataset_for_analysis(999)


def test_dataset_service_analysis_missing_storage_path(
    monkeypatch,
):

    class MockDataset:

        storage_path = None

        column_mapping = {
            "revenue": "revenue",
        }

    class MockDatabase:
        pass

    service = DatasetService(
        db=MockDatabase()
    )

    monkeypatch.setattr(
        "Backend.dataset_service.DatasetRepository.get",
        lambda db, dataset_id: MockDataset(),
    )

    with pytest.raises(
        ValueError,
        match="Dataset 1 has no storage path",
    ):
        service.load_dataset_for_analysis(1)


def test_dataset_service_analysis_missing_mapping(
    monkeypatch,
):

    class MockDataset:

        storage_path = "N:/BizScopeAI/dataset/sales.csv"

        column_mapping = None

    class MockDatabase:
        pass

    service = DatasetService(
        db=MockDatabase()
    )

    monkeypatch.setattr(
        "Backend.dataset_service.DatasetRepository.get",
        lambda db, dataset_id: MockDataset(),
    )

    monkeypatch.setattr(
        "Backend.dataset_service.Path.exists",
        lambda self: True,
    )

    with pytest.raises(
        ValueError,
        match="Dataset 1 has no column mapping",
    ):
        service.load_dataset_for_analysis(1)


def test_load_dataset_for_analysis_returns_canonical_dataframe(
    tmp_path,
    monkeypatch,
):

    csv_path = tmp_path / "sales.csv"

    pd.DataFrame(
        {
            "Order Date": [
                "2025-01-01",
                "2025-02-01",
            ],
            "Sales": [
                100,
                200,
            ],
            "Profit": [
                20,
                50,
            ],
        }
    ).to_csv(
        csv_path,
        index=False,
    )

    class MockDB:
        pass

    service = DatasetService(
        MockDB()
    )

    dataset = Dataset(
        id=1,
        filename="sales.csv",
        storage_path=str(csv_path),
        metadata_json={
            "column_types": {
                "datetime": ["Order Date"],
                "numerical": [
                    "Sales",
                    "Profit",
                ],
            }
        },
        column_mapping={
            "date": "Order Date",
            "revenue": "Sales",
            "profit": "Profit",
        },
    )

    monkeypatch.setattr(
        "Backend.dataset_service.DatasetRepository.get",
        lambda db, dataset_id: dataset,
    )

    result = service.load_dataset_for_analysis(1)

    assert isinstance(result, pd.DataFrame)

    assert "date" in result.columns
    assert "revenue" in result.columns
    assert "profit" in result.columns

    assert list(result["revenue"]) == [
        100,
        200,
    ]

    assert list(result["profit"]) == [
        20,
        50,
    ]


def test_load_dataset_for_analysis_restores_persisted_types(
    monkeypatch,
    tmp_path,
):

    raw_df = pd.DataFrame(
        {
            "date": [
                "2025-01-01",
                "2025-02-01",
            ],
            "revenue": [
                "100",
                "200",
            ],
        }
    )

    dataset = type(
        "MockDataset",
        (),
        {
            "storage_path": str(
                tmp_path / "sales.csv"
            ),
            "column_mapping": {
                "date": "date",
                "revenue": "revenue",
            },
            "metadata_json": {
                "column_types": {
                    "datetime": ["date"],
                    "numerical": ["revenue"],
                    "categorical": [],
                    "identifier": [],
                    "boolean": [],
                    "text": [],
                    "unknown": [],
                }
            },
        },
    )()

    raw_df.to_csv(
        dataset.storage_path,
        index=False,
    )

    monkeypatch.setattr(
        DatasetRepository,
        "get",
        lambda db, dataset_id: dataset,
    )

    service = DatasetService(
        db=None
    )

    result = service.load_dataset_for_analysis(1)

    assert pd.api.types.is_datetime64_any_dtype(
        result["date"]
    )

    assert pd.api.types.is_numeric_dtype(
        result["revenue"]
    )

    assert result["date"].iloc[0] == pd.Timestamp(
        "2025-01-01"
    )

    assert result["revenue"].tolist() == [
        100,
        200,
    ]
