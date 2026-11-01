import os
import pandas as pd
import re


def validate_file(file_path):
    """
    Validate that the supplied path points to a supported CSV file.
    """

    if not isinstance(file_path, (str, os.PathLike)):
        raise TypeError(
            "file_path must be a string or path-like object."
        )

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Dataset file not found: {file_path}"
        )

    if not os.path.isfile(file_path):
        raise ValueError(
            f"The supplied path is not a file: {file_path}"
        )

    extension = os.path.splitext(file_path)[1].lower()

    if extension != ".csv":
        raise ValueError(
            "Unsupported file format. Currently only CSV files are supported."
        )


def clean_column_names(df):
    """
    Normalize DataFrame column names into a consistent format.

    Transformations include:
    - remove leading/trailing whitespace
    - convert to lowercase
    - replace non-alphanumeric characters with underscores
    - collapse repeated underscores
    - remove leading/trailing underscores

    Returns:
        pandas.DataFrame
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            "df must be a pandas DataFrame."
        )

    result = df.copy()

    cleaned_columns = []

    for column in result.columns:

        column = str(column).strip().lower()

        column = re.sub(
            r"[^a-z0-9]+",
            "_",
            column
        )

        column = re.sub(
            r"_+",
            "_",
            column
        )

        column = column.strip("_")

        cleaned_columns.append(column)

        

    result.columns = cleaned_columns

    duplicated_columns = result.columns[
            result.columns.duplicated()
            ].tolist()
    
    if duplicated_columns:
        raise ValueError(
            "Duplicate column names detected after normalization: "
                f"{duplicated_columns}"
            )

    return result



def load_dataset(file_path):
    """
    Load a business dataset from a CSV file.

    Returns:
        pandas.DataFrame
    """

    validate_file(file_path)

    try:
        df = pd.read_csv(file_path)

    except pd.errors.EmptyDataError:
        raise ValueError(
            "The CSV file is empty."
        )

    except pd.errors.ParserError as error:
        raise ValueError(
            f"Unable to parse the CSV file: {error}"
        )

    except UnicodeDecodeError:
        raise ValueError(
            "Unable to decode the CSV file. "
            "Please ensure it is saved using UTF-8 encoding."
        )

    if df.empty:
        raise ValueError(
            "The CSV file does not contain any data rows."
        )

    if len(df.columns) == 0:
        raise ValueError(
            "The CSV file does not contain any columns."
        )

    return df

def load_uploaded_dataset(uploaded_file):
    """
    Load a CSV dataset from an uploaded file-like object.

    The object must provide:
        - read()
        - name

    Returns:
        pandas.DataFrame
    """

    if uploaded_file is None:
        raise ValueError(
            "Uploaded file cannot be None."
        )

    if not hasattr(uploaded_file, "read"):
        raise TypeError(
            "uploaded_file must be a file-like object."
        )

    filename = getattr(
        uploaded_file,
        "name",
        ""
    )

    if filename:
        extension = os.path.splitext(
            filename
        )[1].lower()

        if extension != ".csv":
            raise ValueError(
                "Unsupported file format. "
                "Currently only CSV files are supported."
            )

    try:

        df = pd.read_csv(uploaded_file)

    except pd.errors.EmptyDataError:

        raise ValueError(
            "The CSV file is empty."
        )

    except pd.errors.ParserError as error:

        raise ValueError(
            f"Unable to parse the CSV file: {error}"
        )

    except UnicodeDecodeError:

        raise ValueError(
            "Unable to decode the CSV file. "
            "Please ensure it is saved using UTF-8 encoding."
        )

    if df.empty:
        raise ValueError(
            "The CSV file does not contain any data rows."
        )

    if len(df.columns) == 0:
        raise ValueError(
            "The CSV file does not contain any columns."
        )

    return df


def _is_boolean_series(series):
    """
    Detect actual or textual boolean columns.
    """

    if pd.api.types.is_bool_dtype(series):
        return True

    non_null = series.dropna()

    if non_null.empty:
        return False

    normalized = (
        non_null
        .astype(str)
        .str.strip()
        .str.lower()
    )

    boolean_values = {
        "true",
        "false",
        "yes",
        "no",
        "y",
        "n"
    }

    unique_values = set(normalized.unique())

    return (
        len(unique_values) <= 2
        and unique_values.issubset(boolean_values)
    )

def _looks_like_identifier(column_name, series):
    """
    Determine whether a column is likely to represent an identifier.

    Identifier detection is primarily based on column-name semantics.
    Uniqueness alone is not sufficient because numerical business
    measurements can also contain highly unique values.
    """

    name = column_name.lower().strip()

    identifier_patterns = (
        "_id",
        "_code",
        "_key",
        "_number",
        "_no",
    )

    exact_identifier_names = {
        "id",
        "uuid",
        "identifier",
        "row_id",
        "account_number",
        "account_no",
        "postal_code",
        "zip_code",
    }

    if name in exact_identifier_names:
        return True

    if name.endswith(identifier_patterns):
        return True

    return False

def _looks_like_datetime(column_name, series):
    """
    Determine whether a column is likely to contain datetime values.
    """

    name = column_name.lower().strip()

    datetime_keywords = (
        "date",
        "time",
        "timestamp",
        "datetime"
    )

    name_signal = any(
        keyword in name
        for keyword in datetime_keywords
    )

    if not name_signal:
        return False

    non_null = series.dropna()

    if non_null.empty:
        return False

    converted = pd.to_datetime(
        non_null,
        errors="coerce",
        format="mixed"
    )

    parse_ratio = converted.notna().mean()

    return parse_ratio >= 0.95

def _classify_text_column(series):
    """
    Classify a string/object column as categorical or text.

    Low-cardinality columns are treated as categorical even when
    their uniqueness ratio is high in small datasets.
    """

    non_null = series.dropna()

    if non_null.empty:
        return "categorical"

    unique_count = non_null.nunique()
    total_count = len(non_null)

    uniqueness_ratio = unique_count / total_count

    if unique_count <= 20:
        return "categorical"

    if uniqueness_ratio <= 0.20:
        return "categorical"

    if uniqueness_ratio >= 0.80:
        return "text"

    return "categorical"

def detect_column_types(df):
    """
    Detect semantic column types in a business dataset.

    Returns:
        dict containing:
        numerical
        categorical
        datetime
        identifier
        boolean
        text
        unknown
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            "df must be a pandas DataFrame."
        )

    result = {
        "numerical": [],
        "categorical": [],
        "datetime": [],
        "identifier": [],
        "boolean": [],
        "text": [],
        "unknown": []
    }

    for column in df.columns:

        series = df[column]

       

        if _is_boolean_series(series):

            result["boolean"].append(column)

            continue

        

        if pd.api.types.is_datetime64_any_dtype(series):

            result["datetime"].append(column)

            continue

        if _looks_like_datetime(column, series):

            result["datetime"].append(column)

            continue

        
        if pd.api.types.is_numeric_dtype(series):

            if _looks_like_identifier(column, series):

                result["identifier"].append(column)

            else:

                result["numerical"].append(column)

            continue

        

        if _looks_like_identifier(column, series):

            result["identifier"].append(column)

            continue

        

        if (
            pd.api.types.is_object_dtype(series)
            or pd.api.types.is_string_dtype(series)
        ):

            classification = _classify_text_column(series)

            result[classification].append(column)

            continue

        

        result["unknown"].append(column)

    return result

def profile_business_data(df):
    """
    Generate a structural and statistical profile of a business dataset.

    The function does not modify the input DataFrame.

    Returns:
        dict containing:
        - rows
        - columns
        - column_types
        - missing_values
        - duplicate_rows
        - numeric_summary
        - categorical_summary
        - datetime_summary
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    if df.empty:
        raise ValueError("Business dataset cannot be empty.")

    column_types = detect_column_types(df)

    profile = {
        "rows": len(df),
        "columns": len(df.columns),
        "column_types": column_types,
        "missing_values": {},
        "duplicate_rows": int(df.duplicated().sum()),
        "numeric_summary": {},
        "categorical_summary": {},
        "datetime_summary": {}
    }

    missing_counts = df.isna().sum()

    profile["missing_values"] = {
        column: int(count)
        for column, count in missing_counts.items()
        if count > 0
    }


    for column in column_types["numerical"]:

        series = df[column]

        profile["numeric_summary"][column] = {
            "count": int(series.count()),
            "mean": float(series.mean()) if series.count() > 0 else None,
            "median": float(series.median()) if series.count() > 0 else None,
            "std": float(series.std()) if series.count() > 1 else None,
            "min": float(series.min()) if series.count() > 0 else None,
            "max": float(series.max()) if series.count() > 0 else None
        }

    for column in column_types["categorical"]:

        series = df[column]

        value_counts = series.value_counts(dropna=False)

        profile["categorical_summary"][column] = {
            "unique_values": int(series.nunique(dropna=True)),
            "top_values": {
                str(value): int(count)
                for value, count in value_counts.head(10).items()
            }
        }

    for column in column_types["datetime"]:

        series = df[column]

        converted = pd.to_datetime(
            series,
            errors="coerce",
            format="mixed"
        )

        valid_dates = converted.dropna()

        if valid_dates.empty:
            profile["datetime_summary"][column] = {
                "min": None,
                "max": None
            }
        else:
            profile["datetime_summary"][column] = {
                "min": valid_dates.min().isoformat(),
                "max": valid_dates.max().isoformat()
            }

    return profile    


def _clean_text_columns(df, text_columns):
    """
    Remove leading/trailing whitespace from text-like columns.
    """

    result = df.copy()
    changes = {}

    for column in text_columns:
        if column not in result.columns:
            continue

        if not (
            pd.api.types.is_object_dtype(result[column])
            or pd.api.types.is_string_dtype(result[column])
        ):
            continue

        original = result[column].copy()

        result[column] = result[column].apply(
            lambda value: value.strip()
            if isinstance(value, str)
            else value
        )

        changed_count = int(
            (original != result[column]).fillna(False).sum()
        )

        if changed_count:
            changes[column] = changed_count

    return result, changes


def _normalize_categorical_values(df, categorical_columns):
    """
    Normalize whitespace and casing in categorical columns.

    Example:
        " north " -> "North"
        "NORTH"   -> "North"
        "north"   -> "North"
    """

    result = df.copy()
    changes = {}

    for column in categorical_columns:
        if column not in result.columns:
            continue

        original = result[column].copy()

        result[column] = result[column].apply(
            lambda value: value.strip().title()
            if isinstance(value, str)
            else value
        )

        changed_count = int(
            (original != result[column]).fillna(False).sum()
        )

        if changed_count:
            changes[column] = changed_count

    return result, changes

def normalize_numeric_columns(df):
    """
    Convert columns containing numeric-like values into numeric dtype.

    Handles:
    - integers/floats
    - numeric strings
    - currency-formatted strings
    - percentage-formatted strings

    The original DataFrame is not modified.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    result = df.copy()

    for column in result.columns:

        if not (
            pd.api.types.is_object_dtype(result[column])
            or pd.api.types.is_string_dtype(result[column])
        ):
            continue

        series = result[column]

        cleaned = (
            series.astype("string")
            .str.strip()
            .str.replace(",", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.replace("₹", "", regex=False)
            .str.replace("%", "", regex=False)
        )

        converted = pd.to_numeric(
            cleaned,
            errors="coerce"
        )

        original_non_null = series.notna()

        conversion_ratio = (
            converted[original_non_null].notna().mean()
            if original_non_null.any()
            else 0
        )

        if conversion_ratio >= 0.95:
            result[column] = converted

    return result


def preprocess_dataset(df):
    """
    Clean a business dataset using conservative preprocessing rules.

    The function does not perform business-specific imputation or
    remove potentially meaningful numerical values.

    Returns:
        dict containing:
        - data
        - warnings
        - changes
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    if df.empty:
        raise ValueError("Business dataset cannot be empty.")

    result = df.copy()

    warnings = []
    changes = {}

    # Detect column types before preprocessing.
    column_types = detect_column_types(result)

    # ---------------------------------------------------------
    # 1. Remove completely empty columns
    # ---------------------------------------------------------

    empty_columns = [
        column
        for column in result.columns
        if result[column].isna().all()
    ]

    if empty_columns:
        result = result.drop(columns=empty_columns)
        changes["removed_empty_columns"] = empty_columns

    # ---------------------------------------------------------
    # 2. Remove exact duplicate rows
    # ---------------------------------------------------------

    duplicate_count = int(result.duplicated().sum())

    if duplicate_count:
        result = result.drop_duplicates().reset_index(drop=True)
        changes["removed_duplicate_rows"] = duplicate_count

    # ---------------------------------------------------------
    # 3. Clean text columns
    # ---------------------------------------------------------

    text_columns = (
        column_types["text"]
        + column_types["categorical"]
    )

    result, text_changes = _clean_text_columns(
        result,
        text_columns
    )

    if text_changes:
        changes["trimmed_text_values"] = text_changes

    # ---------------------------------------------------------
    # 4. Normalize categorical values
    # ---------------------------------------------------------

    result, categorical_changes = _normalize_categorical_values(
        result,
        column_types["categorical"]
    )

    if categorical_changes:
        changes["normalized_categorical_values"] = (
            categorical_changes
        )

    # ---------------------------------------------------------
    # 5. Convert datetime columns
    # ---------------------------------------------------------

    for column in column_types["datetime"]:

        if column not in result.columns:
            continue

        if not pd.api.types.is_datetime64_any_dtype(
            result[column]
        ):

            original_non_null = result[column].notna()

            converted = pd.to_datetime(
                result[column],
                errors="coerce",
                format="mixed"
            )

            invalid_count = int(
                (
                    original_non_null
                    & converted.isna()
                ).sum()
            )

            result[column] = converted

            if invalid_count:
                warnings.append(
                    f"{invalid_count} invalid date value(s) "
                    f"found in '{column}' and converted to NaT."
                )

    result = normalize_numeric_columns(result)

    remaining_missing = result.isna().sum()

    missing_summary = {
        column: int(count)
        for column, count in remaining_missing.items()
        if count > 0
    }

    if missing_summary:
        warnings.append(
            f"Missing values remain in dataset: "
            f"{missing_summary}"
        )

    return {
        "data": result,
        "warnings": warnings,
        "changes": changes
    }