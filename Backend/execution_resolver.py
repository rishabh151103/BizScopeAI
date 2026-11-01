
def resolve_execution_parameters(selection):
    """Convert planner requirements into analytics arguments."""

    analysis_name = selection.analysis_name
    requirement = selection.requirement

    if analysis_name in {
        "segment_changes",
        "change_contribution",
    }:
        required_fields = (
            "dimension",
            "start_month",
            "end_month",
        )

        missing = [
            field
            for field in required_fields
            if not getattr(requirement, field, None)
        ]

        if missing:
            raise ValueError(
                f"{analysis_name} requires: "
                f"{', '.join(missing)}"
            )

        return {
            "dimension": requirement.dimension,
            "start_month": requirement.start_month,
            "end_month": requirement.end_month,
        }

    if analysis_name == "discount_performance":
        return {
            "category_filter": requirement.category_filter,
        }

    return {}
