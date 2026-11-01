"""Offline benchmark of deterministic analytics-tool selection."""
import json
from collections import defaultdict
from pathlib import Path

from Backend.reasoning import resolve_deterministically
from Backend.schemas import AnalysisRequirement


# Gold labels are expected registered analysis names, reviewed against the
# catalogue. This measures capability routing only, not LLM answer quality.
CASES = [
    ("Revenue trend", "revenue", "month", "trend", "revenue_trend"),
    ("Category revenue trend", "revenue", "category", "trend", "category_revenue_trend"),
    ("Product profit", "profit", "product", "maximum", "product_performance"),
    ("Regional results", "profit", "region", "performance", "regional_performance"),
    ("Category results", "profit", "category", "performance", "category_performance"),
    ("Discount results", "profit_margin", "discount", "performance", "discount_performance"),
    ("Monthly results", "profit", "month", "performance", "monthly_performance"),
    ("Customer revenue", "revenue", "customer", "maximum", "customer_performance"),
    ("Customer type revenue", "revenue", "customer_type", "comparison", "customer_type"),
    ("Customer retention", "retention", "customer", "retention", "customer_retention"),
    ("Overall profitability", "profit_margin", "business", "overall", "profitability"),
    ("Correlation", "correlation", "numeric_variables", "correlation", "correlations"),
    ("Largest revenue drop", "revenue", "month", "largest_decrease", "significant_changes"),
    ("Order value", "average_order_value", "order", "average", "order_metrics"),
    ("Marketing efficiency", "marketing_efficiency", "marketing_spend", "efficiency", "marketing_performance"),
    ("Distribution", "distribution", "data", "distribution", "distribution_statistics"),
    ("Outlier detection", "outlier", "data", "detect", "outliers"),
]


def score():
    labels = sorted({case[4] for case in CASES})
    matrix = defaultdict(lambda: defaultdict(int))
    correct = 0
    rows = []
    for title, metric, dimension, operation, expected in CASES:
        req = AnalysisRequirement(
            requirement=title, metric=metric, dimension=dimension,
            operation=operation,
        )
        prediction = resolve_deterministically(req).get("tool") or "unsupported"
        matrix[expected][prediction] += 1
        correct += prediction == expected
        rows.append({"case": title, "expected": expected, "predicted": prediction,
                     "correct": prediction == expected})

    per_class = {}
    for label in labels:
        tp = matrix[label][label]
        fp = sum(matrix[actual][label] for actual in labels if actual != label)
        fn = sum(matrix[label][pred] for pred in set(labels + ["unsupported"]) if pred != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1}

    macro = {key: sum(v[key] for v in per_class.values()) / len(labels)
             for key in ("precision", "recall", "f1")}
    return {"scope": "deterministic tool routing only; not end-to-end model accuracy",
            "cases": len(CASES), "accuracy": correct / len(CASES),
            "macro": macro, "per_class": per_class, "case_results": rows}


if __name__ == "__main__":
    result = score()
    output = Path(__file__).parent / "results" / "routing_benchmark.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("scope", "cases", "accuracy", "macro")}, indent=2))
    print(f"Detailed results: {output}")
