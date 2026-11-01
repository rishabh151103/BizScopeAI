from .analytics_registry import ANALYTICS_REGISTRY
from .execution_resolver import resolve_execution_parameters


def execute_analysis(df, selection):
    """
    Execute one selected analytics tool against a canonical DataFrame.

    The planner decides WHAT analysis is required.
    The execution resolver determines any required parameters.
    The analytics registry provides the actual Python function.
    """

    analysis_name = selection.analysis_name

    if analysis_name not in ANALYTICS_REGISTRY:
        raise ValueError(
            f"Unknown analysis: {analysis_name}"
        )

    tool = ANALYTICS_REGISTRY[analysis_name]

    analysis_function = tool["function"]

    parameters = resolve_execution_parameters(
        selection
    )

    return analysis_function(
        df,
        **parameters,
    )