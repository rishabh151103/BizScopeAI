import pandas as pd
import pytest
from io import BytesIO

from Backend.data_loader import (
    load_dataset, 
    validate_file,
    clean_column_names,
    detect_column_types,
    profile_business_data,
    preprocess_dataset,
    load_uploaded_dataset
    )


def test_load_sales_dataset():

    file_path = r"N:\BizScopeAI\dataset\sales_dataset.csv"

    result = load_dataset(file_path)

    assert isinstance(result, pd.DataFrame)
    assert not result.empty


def test_load_superstore_dataset():

    file_path = r"N:\BizScopeAI\dataset\samplesuperstore.csv"

    result = load_dataset(file_path)

    assert isinstance(result, pd.DataFrame)
    assert not result.empty



def test_file_not_found():

    with pytest.raises(FileNotFoundError):

        load_dataset(
            r"N:\BizScopeAI\dataset\does_not_exist.csv"
        )


def test_directory_instead_of_file(tmp_path):

    with pytest.raises(ValueError):

        load_dataset(tmp_path)


def test_unsupported_file_format(tmp_path):

    file_path = tmp_path / "business.xlsx"

    file_path.write_text("test")

    with pytest.raises(ValueError):

        load_dataset(file_path)


def test_empty_csv(tmp_path):

    file_path = tmp_path / "empty.csv"

    file_path.write_text("")

    with pytest.raises(ValueError):

        load_dataset(file_path)


def test_csv_with_header_but_no_rows(tmp_path):

    file_path = tmp_path / "empty_data.csv"

    file_path.write_text(
        "product,revenue\n"
    )

    with pytest.raises(ValueError):

        load_dataset(file_path)


def test_non_string_path():

    with pytest.raises(TypeError):

        validate_file(12345)


def test_clean_column_names():

    df = pd.DataFrame({
        "Customer Name": ["A", "B"],
        "Order Date": ["2025-01-01", "2025-01-02"],
        "Sales Amount": [100, 200]
    })

    result = clean_column_names(df)

    assert list(result.columns) == [
        "customer_name",
        "order_date",
        "sales_amount"
    ]


def test_clean_column_names_with_whitespace():

    df = pd.DataFrame({
        " Customer Name ": ["A"],
        "  Revenue  ": [100]
    })

    result = clean_column_names(df)

    assert list(result.columns) == [
        "customer_name",
        "revenue"
    ]


def test_clean_column_names_with_special_characters():

    df = pd.DataFrame({
        "Country/Region": ["India"],
        "State/Province": ["Delhi"],
        "Product-Name": ["Laptop"]
    })

    result = clean_column_names(df)

    assert list(result.columns) == [
        "country_region",
        "state_province",
        "product_name"
    ]


def test_clean_column_names_with_repeated_separators():

    df = pd.DataFrame({
        "Customer   Name": ["A"],
        "Sales---Amount": [100]
    })

    result = clean_column_names(df)

    assert list(result.columns) == [
        "customer_name",
        "sales_amount"
    ]


def test_clean_column_names_with_uppercase():

    df = pd.DataFrame({
        "CUSTOMER NAME": ["A"],
        "TOTAL SALES": [100]
    })

    result = clean_column_names(df)

    assert list(result.columns) == [
        "customer_name",
        "total_sales"
    ]


def test_clean_column_names_invalid_input():

    with pytest.raises(TypeError):

        clean_column_names("not a dataframe")

def test_clean_column_names_duplicate_columns():

    df = pd.DataFrame(
        [
            ["A", "A", 100]
        ],
        columns=[
            "Customer Name",
            "Customer-Name",
            "Revenue"
        ]
    )

    with pytest.raises(ValueError, match="Duplicate column names"):

        clean_column_names(df)


def test_detect_column_types():

    df = pd.DataFrame({
        "revenue": [100.0, 200.0, 300.0],
        "quantity": [1, 2, 3],
        "order_date": [
            "2025-01-01",
            "2025-01-02",
            "2025-01-03"
        ],
        "customer_id": [
            "C001",
            "C002",
            "C003"
        ],
        "region": [
            "North",
            "South",
            "East"
        ],
        "is_active": [
            True,
            False,
            True
        ]
    })

    result = detect_column_types(df)

    assert "revenue" in result["numerical"]
    assert "quantity" in result["numerical"]

    assert "order_date" in result["datetime"]

    assert "customer_id" in result["identifier"]

    assert "region" in result["categorical"]

    assert "is_active" in result["boolean"]                        


def test_numeric_identifier_detection():

    df = pd.DataFrame({
        "row_id": [1, 2, 3, 4],
        "quantity": [1, 2, 3, 4],
        "revenue": [100.0, 200.0, 300.0, 400.0]
    })

    result = detect_column_types(df)

    assert "row_id" in result["identifier"]

    assert "quantity" in result["numerical"]

    assert "revenue" in result["numerical"]

def test_string_identifier_detection():

    df = pd.DataFrame({
        "customer_id": [
            "C001",
            "C002",
            "C003",
            "C004"
        ],
        "region": [
            "North",
            "South",
            "East",
            "West"
        ]
    })

    result = detect_column_types(df)

    assert "customer_id" in result["identifier"]

    assert "region" in result["categorical"]


def test_low_cardinality_column_is_categorical():

    df = pd.DataFrame({
        "region": [
            "North",
            "South",
            "East",
            "West"
        ]
    })

    result = detect_column_types(df)

    assert "region" in result["categorical"]
    assert "region" not in result["text"]

def test_detect_column_types_with_missing_values():

    df = pd.DataFrame({
        "revenue": [100.0, 200.0, None, 400.0],
        "region": ["North", "South", None, "West"]
    })

    result = detect_column_types(df)

    assert "revenue" in result["numerical"]
    assert "region" in result["categorical"]

def test_detect_column_types_all_null_column():

    df = pd.DataFrame({
        "unknown_column": [None, None, None]
    })

    result = detect_column_types(df)

    assert (
        "unknown_column" in result["categorical"]
        or "unknown_column" in result["unknown"]
    )

def test_detect_text_boolean_column():

    df = pd.DataFrame({
        "is_active": ["Yes", "No", "Yes", "No"]
    })

    result = detect_column_types(df)

    assert "is_active" in result["boolean"]

def test_numeric_strings_are_not_silently_numerical():

    df = pd.DataFrame({
        "revenue": ["100", "200", "300", "400"]
    })

    result = detect_column_types(df)

    assert "revenue" not in result["numerical"]

def test_mixed_date_formats():

    df = pd.DataFrame({
        "order_date": [
            "2025-01-01",
            "01/02/2025",
            "March 3 2025",
            "2025-04-04"
        ]
    })

    result = detect_column_types(df)

    assert "order_date" in result["datetime"]

def test_high_cardinality_text():

    df = pd.DataFrame({
        "product_description": [
            f"Product description {i}"
            for i in range(100)
        ]
    })

    result = detect_column_types(df)

    assert "product_description" in result["text"]

def test_numeric_identifier():

    df = pd.DataFrame({
        "postal_code": [
            110001,
            110002,
            110003,
            110004
        ]
    })

    result = detect_column_types(df)

    assert "postal_code" in result["identifier"]

def test_existing_datetime_dtype():

    df = pd.DataFrame({
        "order_date": pd.to_datetime([
            "2025-01-01",
            "2025-01-02",
            "2025-01-03"
        ])
    })

    result = detect_column_types(df)

    assert "order_date" in result["datetime"]


def test_profile_business_data():
    df = pd.DataFrame({
        "revenue": [100, 200, 300],
        "region": ["North", "South", "North"],
        "order_date": pd.to_datetime([
            "2025-01-01",
            "2025-01-02",
            "2025-01-03"
        ])
    })

    result = profile_business_data(df)

    assert result["rows"] == 3
    assert result["columns"] == 3

    assert "revenue" in result["column_types"]["numerical"]
    assert "region" in result["column_types"]["categorical"]
    assert "order_date" in result["column_types"]["datetime"]        


def test_profile_business_data_missing_values():
    df = pd.DataFrame({
        "revenue": [100, None, 300],
        "region": ["North", "South", None]
    })

    result = profile_business_data(df)

    assert result["missing_values"]["revenue"] == 1
    assert result["missing_values"]["region"] == 1


def test_profile_business_data_duplicates():
    df = pd.DataFrame({
        "revenue": [100, 200, 200],
        "region": ["North", "South", "South"]
    })

    result = profile_business_data(df)

    assert result["duplicate_rows"] == 1


def test_profile_business_data_numeric_summary():
    df = pd.DataFrame({
        "revenue": [100, 200, 300, 400]
    })

    result = profile_business_data(df)

    summary = result["numeric_summary"]["revenue"]

    assert summary["count"] == 4
    assert summary["mean"] == 250.0
    assert summary["median"] == 250.0
    assert summary["min"] == 100.0
    assert summary["max"] == 400.0



def test_profile_business_data_categorical_summary():
    df = pd.DataFrame({
        "region": [
            "North",
            "South",
            "North",
            "North",
            "West"
        ]
    })

    result = profile_business_data(df)

    summary = result["categorical_summary"]["region"]

    assert summary["unique_values"] == 3
    assert summary["top_values"]["North"] == 3


def test_profile_business_data_datetime_summary():
    df = pd.DataFrame({
        "order_date": pd.to_datetime([
            "2025-01-01",
            "2025-03-15",
            "2025-06-30"
        ])
    })

    result = profile_business_data(df)

    summary = result["datetime_summary"]["order_date"]

    assert summary["min"].startswith("2025-01-01")
    assert summary["max"].startswith("2025-06-30")



def test_profile_business_data_invalid_input():
    with pytest.raises(TypeError):
        profile_business_data("not a dataframe")


def test_profile_business_data_empty_dataframe():
    df = pd.DataFrame()

    with pytest.raises(ValueError):
        profile_business_data(df)

def test_preprocess_removes_duplicate_rows():
    df = pd.DataFrame({
        "revenue": [100, 200, 200],
        "region": ["North", "South", "South"]
    })

    result = preprocess_dataset(df)

    assert len(result["data"]) == 2
    assert result["changes"]["removed_duplicate_rows"] == 1


def test_preprocess_trims_text_values():
    df = pd.DataFrame({
        "region": [" North ", "South ", " East"]
    })

    result = preprocess_dataset(df)

    assert result["data"]["region"].tolist() == [
        "North",
        "South",
        "East"
    ]


def test_preprocess_normalizes_categorical_values():
    df = pd.DataFrame({
        "region": [
            "north",
            "NORTH",
            " North ",
            "south"
        ]
    })

    result = preprocess_dataset(df)

    assert set(result["data"]["region"]) == {
        "North",
        "South"
    }

def test_preprocess_keeps_negative_business_values():
    df = pd.DataFrame({
        "revenue": [100, 200, 300],
        "profit": [20, -50, 40]
    })

    result = preprocess_dataset(df)

    assert -50 in result["data"]["profit"].tolist()


def test_preprocess_reports_missing_values():
    df = pd.DataFrame({
        "revenue": [100, None, 300]
    })

    result = preprocess_dataset(df)

    assert len(result["warnings"]) > 0
    assert result["data"]["revenue"].isna().sum() == 1


def test_preprocess_empty_dataframe():
    df = pd.DataFrame()

    with pytest.raises(ValueError):
        preprocess_dataset(df)

def test_preprocess_invalid_input():
    with pytest.raises(TypeError):
        preprocess_dataset("not a dataframe")                                                    

            
            
def test_process_dirty_superstore_dataset():

    file_path = r"N:\BizScopeAI\dataset\samplesuperstore_dirty.csv"

    df = load_dataset(file_path)

    df = clean_column_names(df)

    column_types = detect_column_types(df)

    profile = profile_business_data(df)

    result = preprocess_dataset(df)

    assert isinstance(df, pd.DataFrame)
    assert isinstance(column_types, dict)
    assert isinstance(profile, dict)

    assert "data" in result
    assert "warnings" in result
    assert "changes" in result

    assert isinstance(result["data"], pd.DataFrame)
    assert isinstance(result["warnings"], list)
    assert isinstance(result["changes"], dict)

    assert not result["data"].empty


def test_load_uploaded_dataset():

    csv_content = (
        "Order ID,Sales,Profit\n"
        "1001,500,100\n"
        "1002,750,150\n"
    )

    uploaded_file = BytesIO(
        csv_content.encode("utf-8")
    )

    uploaded_file.name = "test.csv"

    df = load_uploaded_dataset(
        uploaded_file
    )

    assert len(df) == 2
    assert list(df.columns) == [
        "Order ID",
        "Sales",
        "Profit"
    ]


def test_load_uploaded_dataset_invalid_extension():

    csv_content = (
        "Order ID,Sales\n"
        "1001,500\n"
    )

    uploaded_file = BytesIO(
        csv_content.encode("utf-8")
    )

    uploaded_file.name = "test.xlsx"

    with pytest.raises(ValueError):

        load_uploaded_dataset(
            uploaded_file
        )


def test_load_uploaded_dataset_invalid_input():

    with pytest.raises(TypeError):

        load_uploaded_dataset(
            "not a file object"
        )


def test_load_uploaded_dataset_empty_file():

    uploaded_file = BytesIO(
        b""
    )

    uploaded_file.name = "empty.csv"

    with pytest.raises(ValueError):

        load_uploaded_dataset(
            uploaded_file
        )    
        