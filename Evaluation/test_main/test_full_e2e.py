from fastapi.testclient import TestClient
import os
import re
from decimal import Decimal, InvalidOperation
import pytest

from Backend.main import app


client = TestClient(app)


def score_numeric_response(response, expected_values):
    """Score numeric fact coverage against the fixture's known monthly totals."""
    observed = set()
    response = re.sub(r"\b(?:19|20)\d{2}-\d{2}(?:-\d{2})?\b", " ", response)
    for token in re.findall(r"(?<![A-Za-z])[-+]?\$?\d[\d,]*(?:\.\d+)?%?", response):
        token = token.replace("$", "").replace(",", "").replace("%", "")
        try:
            value = Decimal(token)
            if not Decimal("1900") <= value <= Decimal("2100"):
                observed.add(value)
        except InvalidOperation:
            continue
    expected = {Decimal(str(value)) for value in expected_values}
    true_positive = len(observed & expected)
    precision = true_positive / len(observed) if observed else 0.0
    recall = true_positive / len(expected) if expected else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"accuracy": true_positive / len(expected), "precision": precision,
            "recall": recall, "f1": f1, "observed": sorted(observed)}


@pytest.fixture(autouse=True)
def require_local_ollama():
    """Avoid an unbounded live-model run unless explicitly enabled."""
    if os.getenv("RUN_LIVE_OLLAMA_E2E") != "1":
        pytest.skip(
            "Set RUN_LIVE_OLLAMA_E2E=1 to run the Ollama-backed E2E test."
        )


def test_full_real_e2e_business_investigation():
    # ---------------------------------------------------------
    # 1. REAL CSV UPLOAD
    # ---------------------------------------------------------

    csv_content = (
        "Order ID,Date,Revenue,Profit\n"
        "1,2025-01-01,100,20\n"
        "2,2025-01-15,150,30\n"
        "3,2025-02-01,200,40\n"
        "4,2025-02-15,250,50\n"
        "5,2025-03-01,300,60\n"
        "6,2025-03-15,350,70\n"
    )

    upload_response = client.post(
        "/datasets/upload",
        files={
            "file": (
                "e2e_business_dataset.csv",
                csv_content,
                "text/csv",
            )
        },
    )

    assert upload_response.status_code == 200, upload_response.text

    upload_data = upload_response.json()

    assert "dataset_id" in upload_data
    assert upload_data["filename"] == "e2e_business_dataset.csv"
    assert upload_data["rows"] == 6
    assert upload_data["columns"] == 4

    dataset_id = upload_data["dataset_id"]

    print(f"\n[E2E] Uploaded dataset: {dataset_id}")

    # ---------------------------------------------------------
    # 2. REAL CHAT — START INVESTIGATION
    # ---------------------------------------------------------

    first_response = client.post(
        "/chat",
        json={
            "message": (
                "My business revenue appears to be changing over time. "
                "I want to understand the monthly revenue trend."
            ),
            "dataset_id": dataset_id,
        },
    )

    assert first_response.status_code == 200, first_response.text

    first_data = first_response.json()

    print("[E2E] First chat response:")
    print(first_data)

    assert isinstance(first_data, dict)
    assert isinstance(first_data["response"], str)
    assert isinstance(first_data["visualizations"], list)
    assert first_data["response"].strip()

    # ---------------------------------------------------------
    # 3. REAL CHAT — TRIGGER EVIDENCE INVESTIGATION
    # ---------------------------------------------------------
    #
    # This is intentionally a second message.
    # The first message establishes the investigation.
    # The second message asks for evidence, allowing the real:
    #
    # Llama
    #   -> evidence needed
    #   -> Qwen
    #   -> evidence requirement
    #   -> planner
    #   -> analytics
    #   -> visualization
    #   -> evidence persistence
    #   -> Llama evidence update
    #   -> final response
    #
    # to execute.
    # ---------------------------------------------------------

    second_response = client.post(
        "/chat",
        json={
            "message": (
                "Please analyze the actual dataset and create a chart "
                "of the monthly revenue trend using the available business data."
            ),
            "investigation_id": first_data["investigation_id"],
            "dataset_id": dataset_id,
        },
    )

    assert second_response.status_code == 200, second_response.text

    second_data = second_response.json()

    print("[E2E] Final chat response:")
    print(second_data)

    # ---------------------------------------------------------
    # 4. RESPONSE CONTRACT
    # ---------------------------------------------------------

    assert "response" in second_data
    assert isinstance(second_data["response"], str)
    assert second_data["response"].strip()

    # The request is for monthly revenue. Gold values are Jan/Feb/Mar revenue
    # (250, 450, 650), plus the derivable monthly changes (80%, 44.4444%) and
    # first-to-last change (160%). Profit is intentionally not required.
    response_scores = score_numeric_response(
        second_data["response"], [250, 450, 650, 80, 44.4444, 160]
    )
    print(f"[E2E] Full-response numeric fact scores: {response_scores}")
    assert response_scores["recall"] >= 5 / 6, response_scores
    assert response_scores["precision"] >= 0.5, response_scores

    # Visualization should be returned by the real V2 pathway.
    assert "visualizations" in second_data
    assert isinstance(second_data["visualizations"], list)

    assert len(second_data["visualizations"]) >= 1

    visualization = second_data["visualizations"][0]

    assert visualization is not None

    print("[E2E] Visualization returned:")
    print(visualization)

    # Plotly serialization should have produced a JSON-compatible
    # figure representation.
    assert isinstance(visualization, dict)

    assert "data" in visualization
    assert "layout" in visualization

    print("[E2E] REAL END-TO-END PIPELINE PASSED")
