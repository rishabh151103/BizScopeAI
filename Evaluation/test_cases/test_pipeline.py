import sys
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest


sys.path.append(
    str(Path(__file__).resolve().parents[2] / "Backend")
)

from Backend.pipeline import (
    prepare_uploaded_dataset,
    investigate_business_question
    )


def test_full_question_to_analysis_integration(monkeypatch):
    from Backend import analysis_planner
    from Backend.schemas import AnalysisRequirement, RequirementPlan

    monkeypatch.setattr(
        analysis_planner,
        "extract_requirements",
        lambda question: RequirementPlan(
            question_summary=question,
            requirements=[AnalysisRequirement(
                requirement="Compare product revenue between January and February 2025.",
                metric="revenue",
                dimension="product",
                operation="change",
                start_month="2025-01",
                end_month="2025-02",
            )],
        ),
    )

    csv_content = (
        "Order ID,Product,Region,Sales,Profit,Order Date\n"
        "1001,Laptop,North,500,100,2025-01-01\n"
        "1002,Laptop,South,700,150,2025-01-01\n"
        "1003,Monitor,North,300,50,2025-01-01\n"
        "1004,Monitor,South,400,80,2025-01-01\n"
        "1005,Laptop,North,900,200,2025-02-01\n"
        "1006,Laptop,South,800,180,2025-02-01\n"
        "1007,Monitor,North,200,30,2025-02-01\n"
        "1008,Monitor,South,350,60,2025-02-01\n"
    )

    uploaded_file = BytesIO(
        csv_content.encode("utf-8")
    )

    uploaded_file.name = "integration_test.csv"

    question = (
        "How did product revenue change "
        "between January and February 2025?"
    )

    result = investigate_business_question(
        uploaded_file,
        question,
        visualization=True,
    )

    # --------------------------------------------------
    # Overall pipeline
    # --------------------------------------------------

    assert isinstance(result, dict)

    assert result["question"] == question

    assert "plan" in result
    assert "analyses" in result
    assert "analysis_names" in result

    # --------------------------------------------------
    # Planner output
    # --------------------------------------------------

    assert len(result["plan"].analyses) >= 1

    selection = result["plan"].analyses[0]

    requirement = selection.requirement

    assert requirement.metric == "revenue"
    assert requirement.dimension == "product"
    assert requirement.operation == "change"
    assert requirement.start_month == "2025-01"
    assert requirement.end_month == "2025-02"

    # --------------------------------------------------
    # Analytics selection
    # --------------------------------------------------

    assert selection.analysis_name == "segment_changes"

    assert "segment_changes" in result["analysis_names"]

    # --------------------------------------------------
    # Actual analytics execution
    # --------------------------------------------------

    analysis = result["analyses"]["segment_changes"]

    assert isinstance(analysis, pd.DataFrame)
    
    comparison = analysis

    assert not comparison.empty

    # --------------------------------------------------
    # Verify that the requested dimension and
    # requested periods actually reached the analysis
    # --------------------------------------------------

    assert "product" in comparison.columns

    assert "start_revenue" in comparison.columns
    assert "end_revenue" in comparison.columns

    # --------------------------------------------------
    # Verify actual business result
    # --------------------------------------------------

    laptop = comparison[
        comparison["product"] == "Laptop"
    ].iloc[0]

    monitor = comparison[
        comparison["product"] == "Monitor"
    ].iloc[0]

    assert laptop["start_revenue"] == 1200
    assert laptop["end_revenue"] == 1700

    assert monitor["start_revenue"] == 700
    assert monitor["end_revenue"] == 550    

    # --------------------------------------------------
    # Visualization
    # --------------------------------------------------

    assert "visualizations" in result

    assert "segment_changes" in result["visualizations"]

    figure = result["visualizations"]["segment_changes"]

    assert figure is not None

    assert hasattr(figure, "to_dict")
