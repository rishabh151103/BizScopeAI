import pandas as pd

from .schemas import BusinessColumnMapping


def adapt_dataset(
    df: pd.DataFrame,
    mapping: BusinessColumnMapping
) -> pd.DataFrame:
    """
    Adapt a business dataset to BizScopeAI's canonical analytics schema.

    The original DataFrame is never modified.

    Parameters
    ----------
    df : pd.DataFrame
        Preprocessed business dataset.

    mapping : BusinessColumnMapping
        Mapping between BizScopeAI business concepts and the
        actual columns in the dataset.

    Returns
    -------
    pd.DataFrame
        A copy of the dataset with mapped columns renamed to
        BizScopeAI's canonical names.

    Raises
    ------
    TypeError
        If df or mapping has an invalid type.

    ValueError
        If a mapped column does not exist in the DataFrame.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    if not isinstance(mapping, BusinessColumnMapping):
        raise TypeError(
            "mapping must be a BusinessColumnMapping."
        )

    result = df.copy()

    rename_map = {}

    for concept, actual_column in mapping.model_dump().items():

        if actual_column is None:
            continue

        if actual_column not in result.columns:
            raise ValueError(
                f"Mapped column '{actual_column}' for "
                f"'{concept}' does not exist in the DataFrame."
            )

        rename_map[actual_column] = concept

    result = result.rename(columns=rename_map)

    # ---------------------------------------------------------
    # Derive cost when revenue and profit are available.
    #
    # Assumption:
    # profit = revenue - cost
    # Therefore:
    # cost = revenue - profit
    # ---------------------------------------------------------

    if (
        "cost" not in result.columns
        and "revenue" in result.columns
        and "profit" in result.columns
    ):
        result["cost"] = (
            result["revenue"]
            - result["profit"]
        )

    # ---------------------------------------------------------
    # Derive profit margin when revenue and profit are available.
    # ---------------------------------------------------------

    if (
        "profit_margin_percent" not in result.columns
        and "revenue" in result.columns
        and "profit" in result.columns
    ):
        result["profit_margin_percent"] = pd.NA

        non_zero_revenue = result["revenue"] != 0

        result.loc[
            non_zero_revenue,
            "profit_margin_percent"
        ] = (
            result.loc[
                non_zero_revenue,
                "profit"
            ]
            / result.loc[
                non_zero_revenue,
                "revenue"
            ]
        ) * 100

    if "discount" in result.columns:
        result["discount"] = pd.to_numeric(
            result["discount"],
            errors="coerce",
        )

    return result
