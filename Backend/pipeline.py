from .data_loader import (
    clean_column_names,
    detect_column_types,
    load_uploaded_dataset,
    preprocess_dataset,
    profile_business_data,
)
import inspect

import pandas as pd

from .schema_mapper import map_business_columns
from .analytics_adapter import adapt_dataset

from .analytics_registry import (
    ANALYTICS_REGISTRY,
    VISUALIZATION_REGISTRY,
)

from .analysis_planner import select_analyses
from .execution_resolver import resolve_execution_parameters


def prepare_uploaded_dataset(uploaded_file):
    df = load_uploaded_dataset(uploaded_file)

    df = clean_column_names(df)

    column_types = detect_column_types(df)

    profile = profile_business_data(df)

    preprocessing_result = preprocess_dataset(df)

    cleaned_data = preprocessing_result["data"]

    column_mapping = map_business_columns(
        cleaned_data
    )

    return {
        "data": cleaned_data,
        "profile": profile,
        "warnings": preprocessing_result["warnings"],
        "changes": preprocessing_result["changes"],
        "column_types": column_types,
        "column_mapping": column_mapping,
    }


def run_analysis(df, mapping, analysis_name, **kwargs):

    if analysis_name not in ANALYTICS_REGISTRY:
        raise ValueError(
            f"Unknown analysis: '{analysis_name}'. "
            f"Available analyses: {list(ANALYTICS_REGISTRY.keys())}"
        )

    adapted_df = adapt_dataset(
        df,
        mapping
    )

    analysis_config = ANALYTICS_REGISTRY[analysis_name]

    analysis_function = analysis_config["function"]

    return analysis_function(
        adapted_df,
        **kwargs
    )


def run_visualization(
    analysis_name,
    analysis_result,
    **kwargs
):

    if analysis_name not in VISUALIZATION_REGISTRY:
        raise ValueError(
            f"No visualization registered for analysis: "
            f"'{analysis_name}'"
        )

    visualization_config = VISUALIZATION_REGISTRY[
        analysis_name
    ]

    visualization_function = visualization_config["function"]

    result_key = visualization_config["result_key"]

    if result_key is not None:

        if isinstance(analysis_result, dict):

            if result_key not in analysis_result:
                raise KeyError(
                    f"Analysis result does not contain "
                    f"required key: '{result_key}'"
                )

            visualization_input = analysis_result[
                result_key
            ]

        else:

            visualization_input = analysis_result

    else:

        visualization_input = analysis_result

    # ---------------------------------------------------------
    # Restore tabular analysis results for visualization.
    #
    # AnalysisRun stores JSON-safe results, so DataFrames become
    # lists of dictionaries. Visualization functions expect
    # pandas DataFrames for tabular analysis results.
    # ---------------------------------------------------------

    if (
        isinstance(visualization_input, list)
        and visualization_input
        and all(
            isinstance(item, dict)
            for item in visualization_input
        )
    ):
        visualization_input = pd.DataFrame(
            visualization_input
        )

    accepted_parameters = inspect.signature(
        visualization_function
    ).parameters
    visualization_kwargs = {
        name: value
        for name, value in kwargs.items()
        if name in accepted_parameters
    }

    return visualization_function(
        visualization_input,
        **visualization_kwargs
    )

def investigate_business_question(
    uploaded_file,
    question,
    visualization=True,
    **kwargs
):

    if not question or not question.strip():
        raise ValueError(
            "Business question cannot be empty."
        )


    prepared = prepare_uploaded_dataset(
        uploaded_file
    )

    df = prepared["data"]

    mapping = prepared["column_mapping"]

    analysis_plan = select_analyses(
        question
    )

    selected_analyses = [
        selection.analysis_name
        for selection in analysis_plan.analyses
    ]


    analysis_results = {}

    for selection in analysis_plan.analyses:

        analysis_name = selection.analysis_name

        execution_parameters = resolve_execution_parameters(
            selection
        )

        analysis_results[analysis_name] = run_analysis(
            df,
            mapping,
            analysis_name,
            **execution_parameters,
            **kwargs
        )

    visualizations = {}

    if visualization:

        for analysis_name in selected_analyses:

            if analysis_name not in VISUALIZATION_REGISTRY:
                visualizations[analysis_name] = None
                continue

            visualization_parameters = {
                **execution_parameters,
                **kwargs,
            }
            visualizations[analysis_name] = run_visualization(
                analysis_name,
                analysis_results[analysis_name],
                **visualization_parameters,
            )


    result = {
        "question": question,

        "plan": analysis_plan,

        "analysis_names": selected_analyses,

        "data": {
            "rows": len(df),
            "columns": len(df.columns),
            "warnings": prepared["warnings"],
            "changes": prepared["changes"],
        },

        "column_mapping": mapping,

        "analyses": analysis_results,

        "visualizations": visualizations,
    }

    if len(selected_analyses) == 1:

        analysis_name = selected_analyses[0]

        result["analysis_name"] = analysis_name

        result["analysis"] = analysis_results[
            analysis_name
        ]

        result["visualization"] = visualizations.get(
            analysis_name
        )

    return result
