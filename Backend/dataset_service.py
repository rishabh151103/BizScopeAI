import os
from pathlib import Path
from uuid import uuid4

import pandas as pd
from sqlalchemy.orm import Session

from .analytics_adapter import adapt_dataset
from .data_loader import load_dataset
from .db_models import Dataset
from .pipeline import prepare_uploaded_dataset
from .repositories import DatasetRepository
from .schema_mapper import map_business_columns
from .schemas import BusinessColumnMapping


PROJECT_DATASET_DIR = (
    Path(__file__).resolve().parents[1] / "dataset" / "uploads"
)
DATASET_STORAGE_DIR = Path(
    os.getenv("BIZSCOPE_DATA_DIR", str(PROJECT_DATASET_DIR))
).expanduser().resolve()


class DatasetService:

    def __init__(self, db: Session):
        self.db = db

    def ingest_dataset(self, uploaded_file):
        """
        Ingest an uploaded CSV dataset.

        Steps:
        1. Prepare the dataset using the existing V2 pipeline.
        2. Save the processed dataset to disk.
        3. Create a Dataset record in PostgreSQL.
        4. Return the persisted Dataset object.
        """

        # ---------------------------------------------------------
        # 1. Run existing V2 preparation pipeline
        # ---------------------------------------------------------

        prepared = prepare_uploaded_dataset(uploaded_file)

        df = prepared["data"]

        # ---------------------------------------------------------
        # 2. Create storage directory
        # ---------------------------------------------------------

        DATASET_STORAGE_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ---------------------------------------------------------
        # 3. Determine filename
        # ---------------------------------------------------------

        filename = getattr(
            uploaded_file,
            "name",
            "dataset.csv",
        )

        filename = Path(filename).name

        # Preserve the user's filename as metadata while keeping each upload
        # at a unique path. Re-uploading "sales.csv" must not silently replace
        # a dataset already referenced by an investigation.
        storage_path = DATASET_STORAGE_DIR / f"{uuid4().hex}.csv"

        # ---------------------------------------------------------
        # 4. Save processed dataset
        # ---------------------------------------------------------

        # ---------------------------------------------------------
        # 5. Create PostgreSQL Dataset record
        # ---------------------------------------------------------

        column_mapping = prepared["column_mapping"]

        if hasattr(column_mapping, "model_dump"):
            column_mapping = column_mapping.model_dump()

        dataset = Dataset(
            filename=filename,
            storage_path=str(storage_path),
            row_count=len(df),
            column_count=len(df.columns),
            metadata_json={
                "column_types": prepared["column_types"],
            },
            profile_json=prepared["profile"],
            warnings=prepared["warnings"],
            changes=prepared["changes"],
            column_mapping=column_mapping,
        )

        try:
            df.to_csv(
                storage_path,
                index=False,
            )
            self.db.add(dataset)
            self.db.commit()
            self.db.refresh(dataset)

        except Exception:
            self.db.rollback()
            try:
                storage_path.unlink(missing_ok=True)
            except OSError:
                # Keep the original database error as the actionable failure.
                pass
            raise

        return dataset

    def _restore_dataset_types(
        self,
        df: pd.DataFrame,
        dataset: Dataset,
    ) -> pd.DataFrame:
        """
        Restore persisted semantic column types after loading
        the dataset from CSV.

        CSV storage does not preserve pandas datetime dtype, so
        datetime columns recorded during ingestion must be restored
        before analytical execution.

        The original DataFrame is never modified.
        """

        result = df.copy()

        metadata = getattr(
            dataset,
            "metadata_json",
            None,
        ) or {}

        column_types = metadata.get(
            "column_types",
            {},
        )

        if not isinstance(column_types, dict):
            return result

        # ---------------------------------------------------------
        # Restore datetime columns
        # ---------------------------------------------------------

        datetime_columns = column_types.get(
            "datetime",
            [],
        )

        for column in datetime_columns:

            if column not in result.columns:
                continue

            if not pd.api.types.is_datetime64_any_dtype(
                result[column]
            ):
                result[column] = pd.to_datetime(
                    result[column],
                    errors="coerce",
                    format="mixed",
                )

        # ---------------------------------------------------------
        # Restore numerical columns
        # ---------------------------------------------------------

        numerical_columns = column_types.get(
            "numerical",
            [],
        )

        for column in numerical_columns:

            if column not in result.columns:
                continue

            if not pd.api.types.is_numeric_dtype(
                result[column]
            ):
                result[column] = pd.to_numeric(
                    result[column],
                    errors="coerce",
                )

        return result

    def load_dataset_for_analysis(
        self,
        dataset_id: int,
    ) -> pd.DataFrame:

        dataset = DatasetRepository.get(
            self.db,
            dataset_id,
        )

        if dataset is None:
            raise ValueError(
                f"Dataset with id {dataset_id} was not found."
            )

        if not dataset.storage_path:
            raise ValueError(
                f"Dataset {dataset_id} has no storage path."
            )

        storage_path = Path(
            dataset.storage_path
        )

        if not storage_path.exists():
            raise FileNotFoundError(
                f"Dataset file not found: {storage_path}"
            )

        if not dataset.column_mapping:
            raise ValueError(
                f"Dataset {dataset_id} has no column mapping."
            )

        # ---------------------------------------------------------
        # 1. Load persisted dataset
        # ---------------------------------------------------------

        df = load_dataset(
            storage_path
        )

        # ---------------------------------------------------------
        # 2. Restore semantic pandas dtypes
        # ---------------------------------------------------------

        df = self._restore_dataset_types(
            df,
            dataset,
        )

        # ---------------------------------------------------------
        # 3. Adapt to canonical BizScopeAI schema
        # ---------------------------------------------------------

        mapping = BusinessColumnMapping.model_validate(
            dataset.column_mapping
        )

        # Older uploads were ingested before optional business columns were
        # mapped. Recover the new discount mapping from the stored CSV without
        # requiring users to upload the dataset again.
        if mapping.discount is None:
            mapping.discount = map_business_columns(df).discount

        return adapt_dataset(
            df,
            mapping,
        )

    def get_available_analysis_columns(self, dataset_id: int) -> set[str]:
        """Return canonical columns available for analysis without loading rows."""
        dataset = DatasetRepository.get(self.db, dataset_id)
        if dataset is None:
            return set()

        mapping = dataset.column_mapping or {}
        if not isinstance(mapping, dict):
            mapping = {}
        available = {
            str(concept)
            for concept, source_column in mapping.items()
            if source_column is not None
        }

        # Detect newly supported optional fields in datasets uploaded before
        # their mapping was introduced, using only the stored CSV header.
        if "discount" not in available and dataset.storage_path:
            try:
                headers = pd.read_csv(dataset.storage_path, nrows=0)
                from .data_loader import clean_column_names
                from .schema_mapper import map_business_columns

                headers = clean_column_names(headers)
                if map_business_columns(headers).discount is not None:
                    available.add("discount")
            except (OSError, ValueError, pd.errors.ParserError):
                pass

        return available
