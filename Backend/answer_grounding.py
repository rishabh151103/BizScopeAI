import json
import math
import re
from dataclasses import asdict,dataclass
from typing import Any 



@dataclass
class VerifiedMetric:
    name: str
    value: float | int | str
    unit: str | None = None
    dimension: str | None = None
    dimension_value: str | None = None
    source_analysis: str | None = None
    source_path: str | None = None



def to_json_safe(value: Any) -> Any:
    """
    Convert common Python data structures into JSON-safe values.

    Does not guess metric meanings or silently convert NaN/Infinity
    into valid numerical values.
    """

    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        return value if math.isfinite(value) else None

    if isinstance(value, dict):
        return {
            str(key): to_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [to_json_safe(item) for item in value]

    if hasattr(value, "model_dump"):
        return to_json_safe(value.model_dump(mode="python"))

    if hasattr(value, "item"):
        try:
            return to_json_safe(value.item())
        except (ValueError, TypeError):
            pass

    if hasattr(value, "tolist"):
        try:
            return to_json_safe(value.tolist())
        except (ValueError, TypeError):
            pass

    # Avoid inventing a structure for unknown objects.
    return str(value)


def normalize_analysis_result(
    analysis_name: str,
    result_data: Any,
) -> dict:
    """
    Preserve the original result and attach provenance.

    This function does not rename metrics, calculate rankings,
    infer units, or change the meaning of the source result.
    """

    safe_result = to_json_safe(result_data)

    return {
        "analysis_name": analysis_name,
        "result": safe_result,
    }


def collect_analysis_results(
    investigation_service,
    investigation_id: int,
) -> list[dict]:
    """
    Collect completed persisted runs for an investigation.

    Dataset/time-period filtering must be applied separately when
    the application can mix datasets or periods in one investigation.
    """

    runs = investigation_service.get_analysis_runs(
        investigation_id
    )

    results = []

    for run in runs:
        if run.status != "completed":
            continue

        results.append(
            normalize_analysis_result(
                analysis_name=run.analysis_name,
                result_data=run.result_data,
            )
        )

    return results


def extract_numeric_facts(
    analysis_result: dict,
) -> list[dict]:
    """
    Recursively extract finite numeric values from common result
    structures.

    The output preserves the original key path. It does not assume
    that a number is revenue, profit, a percentage, or a ranking
    unless the source explicitly identifies it that way.
    """

    facts = []
    analysis_name = analysis_result.get("analysis_name", "")
    root = analysis_result.get("result")

    def walk(value: Any, path: str = "result"):
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, f"{path}.{key}")

        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")

        elif (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
        ):
            if math.isfinite(value):
                facts.append({
                    "source_analysis": analysis_name,
                    "source_path": path,
                    "value": value,
                })

    walk(root)
    return facts


ANALYSIS_KEYWORDS = {
    "revenue_trend": (
        "revenue trend", "revenue over time", "revenue increase",
        "revenue decrease", "revenue growth", "sales trend",
    ),
    "profitability": (
        "profitability", "profit margin", "most profitable",
        "overall profit", "overall profitability",
    ),
    "product_performance": (
        "product", "products", "best-selling product",
        "product performance",
    ),
    "customer_performance": (
        "customer", "customers", "top customer",
        "customer revenue", "customer profit",
    ),
    "customer_type": (
        "customer type", "new customers", "returning customers",
        "new versus returning", "customer segment",
    ),
    "category_performance": (
        "category", "categories", "category ranking",
        "category revenue", "category profit", "profit margin",
        "aggregate margin", "average margin",
    ),
    "discount_performance": (
        "discount", "discount level", "discount band",
    ),
    "category_revenue_trend": (
        "category revenue trend", "revenue by category over time",
        "sales by category over time", "monthly revenue by category",
        "monthly sales by category", "category-level revenue trend",
    ),
    "regional_performance": (
        "region", "regional", "geographic", "geographical",
        "which region",
    ),
    "monthly_performance": (
        "monthly", "month by month", "by month",
        "monthly revenue", "monthly profit",
    ),
    "correlations": (
        "correlation", "correlated", "relationship between variables",
    ),
    "business_comparisons": (
        "compare", "comparison", "compare performance",
        "across segments",
    ),
    "significant_changes": (
        "largest change", "biggest change", "sharpest",
        "significant change", "largest increase", "largest decrease",
    ),
    "segment_changes": (
        "change between periods", "period over period",
        "segment change", "changed between",
    ),
    "change_contribution": (
        "contributed to the change", "contribution to the decline",
        "caused the decline", "drove the change",
        "contributed most",
    ),
    "order_metrics": (
        "average order value", "median order value", "orders",
        "units per order", "revenue per unit",
    ),
    "marketing_performance": (
        "marketing", "marketing spend", "marketing spending",
        "return on marketing", "marketing effectiveness",
    ),
    "customer_retention": (
        "retention", "repeat customer", "repeat customers",
        "one-time customer", "one-time customers",
    ),
    "distribution_statistics": (
        "distribution", "standard deviation", "quartile",
        "median", "mean", "minimum", "maximum",
    ),
    "outliers": (
        "outlier", "outliers", "unusual values",
        "unusually high", "unusually low", "anomalies",
    ),
}


def select_relevant_analysis_results(
    analysis_results: list[dict],
    question: str,
) -> list[dict]:
    """
    Select stored analyses that may answer the question.

    This selects existing results only. It does not calculate metrics,
    change values, or claim an analysis was executed.
    """
    question_lower = (question or "").casefold()

    matched_names = {
        analysis_name
        for analysis_name, keywords in ANALYSIS_KEYWORDS.items()
        if any(keyword in question_lower for keyword in keywords)
    }

    if "discount" in question_lower and "discount_performance" in matched_names:
        matched_names.intersection_update({"discount_performance"})
    elif "category_performance" in matched_names and not any(
        term in question_lower for term in ("overall business", "whole business")
    ):
        matched_names.discard("profitability")

    # "Product category" names the category dimension, not individual
    # product performance. Avoid pulling product-level results into a
    # category-only answer or chart.
    if "product categor" in question_lower or "by categor" in question_lower:
        matched_names.discard("product_performance")
    if any(term in question_lower for term in (
        "monthly revenue by category", "revenue by category over time",
        "sales by category over time", "category revenue trend",
    )):
        # This is a grouped time series. Do not also select the overall series
        # just because the request contains the words "monthly revenue".
        matched_names.discard("revenue_trend")
        matched_names.discard("monthly_performance")

    if not matched_names:
        # Ambiguous or broad questions retain all available evidence.
        return analysis_results

    selected = [
        item
        for item in analysis_results
        if item.get("analysis_name") in matched_names
    ]

    # Never imply evidence exists if the matching analysis was not stored.
    # Returning an empty list allows the caller to report that limitation.
    return selected


def build_grounded_context(
    analysis_results: list[dict],
    question: str | None = None,
) -> dict:
    """
    Build traceable context from persisted Python analysis results.
    If a question is supplied, select potentially relevant analyses.
    """
    available_results = analysis_results

    if question:
        available_results = select_relevant_analysis_results(
            analysis_results,
            question,
        )

    all_facts = []

    for analysis_result in available_results:
        all_facts.extend(extract_numeric_facts(analysis_result))

    return {
        "question": question,
        "available_analysis_names": sorted({
            item.get("analysis_name", "")
            for item in analysis_results
        }),
        "selected_analysis_names": sorted({
            item.get("analysis_name", "")
            for item in available_results
        }),
        "analysis_results": available_results,
        "numeric_facts": all_facts,
        "rules": [
            "Original Python analysis results are authoritative.",
            "Every numerical claim must map to a source path.",
            "Do not infer units or metric meanings from numbers alone.",
            "Do not mix results from different datasets or periods.",
            "Do not claim an analysis ran unless its result is present.",
            "Do not claim a ranking unless the complete relevant "
            "comparison set is available.",
            "Do not treat correlation as causation.",
            "If relevant evidence is missing, state that limitation.",
        ],
    }


def serialize_grounded_context(
    analysis_results: list[dict],
    question: str | None = None,
) -> str:
    """Serialize grounded results for the final-response prompt."""
    context = build_grounded_context(
        analysis_results=analysis_results,
        question=question,
    )

    return json.dumps(
        to_json_safe(context),
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    )

def answer_category_comparison(
    user_question: str,
    analysis_results: list[dict],
) -> str | None:
    """Answer explicit category or region rankings from stored results.

    Supports the category_performance schema emitted by analytics.py:
    result["category_analysis"] with total_revenue, total_profit,
    average_profit_margin, aggregate_profit_margin, units_sold, etc.
    Returns None if the question or evidence is insufficient.
    """
    question = (user_question or "").casefold()

    direction = None
    ranking_terms = {
        "highest": ("highest", "maximum", "most", "best"),
        "lowest": ("lowest", "minimum", "least", "worst"),
    }
    for candidate, terms in ranking_terms.items():
        if any(re.search(rf"\b{re.escape(term)}\b", question) for term in terms):
            direction = candidate
            break
    # Longest aliases first to avoid matching "profit margin" as "profit".
    metric_aliases = [
        ("aggregate_profit_margin", ("aggregate profit margin", "overall profit margin")),
        ("average_profit_margin", ("average profit margin", "average margin", "profit margin", "margin")),
        ("revenue_share_percent", ("revenue share",)),
        ("total_revenue", ("total revenue", "revenue", "sales")),
        ("total_profit", ("total profit", "profit", "profits")),
        ("units_sold", ("units sold", "number of units", "quantity sold")),
    ]
    requested_metric = None
    ranked_metric = re.search(
        r"\brank\b[^.?!;]*?\bby\s+"
        r"(aggregate profit margin|average profit margin|total profit|profit|"
        r"total revenue|revenue|sales|units sold|units)\b",
        question,
    )
    if ranked_metric:
        ranked_label = ranked_metric.group(1)
        if "aggregate" in ranked_label:
            requested_metric = "aggregate_profit_margin"
        elif "margin" in ranked_label:
            requested_metric = "average_profit_margin"
        elif "profit" in ranked_label:
            requested_metric = "total_profit"
        elif ranked_label in {"revenue", "sales", "total revenue"}:
            requested_metric = "total_revenue"
        else:
            requested_metric = "units_sold"
    for metric, aliases in sorted(metric_aliases, key=lambda pair: max(map(len, pair[1])), reverse=True):
        if requested_metric:
            break
        if any(alias in question for alias in aliases):
            requested_metric = metric
            break
    if requested_metric is None:
        return None
    if direction is None and any(
        marker in question
        for marker in ("rank", "top two", "top 2", "top category", "top categories")
    ):
        # A request to rank categories and report the top-two gap implies a
        # descending ranking even when it does not use the word "highest".
        direction = "highest"
    if direction is None:
        return None

    grouped_result = None
    group_name = None
    result_name = None
    for item in reversed(analysis_results):
        analysis_name = str(item.get("analysis_name", "")).casefold()
        result = item.get("result")
        if "category_performance" in analysis_name and isinstance(result, (dict, list)):
            grouped_result = result
            group_name = "category"
            result_name = "category_analysis"
            break
        if "regional_performance" in analysis_name and isinstance(result, (dict, list)):
            grouped_result = result
            group_name = "region"
            result_name = "regional_analysis"
            break
    if grouped_result is None:
        return None

    records = None
    if isinstance(grouped_result, list):
        records = grouped_result
    elif isinstance(grouped_result, dict):
        # Actual analytics.py schema first, then legacy schemas.
        alternate_keys = (
            (result_name, "categories") if group_name == "category"
            else (result_name, "regions")
        )
        for key in alternate_keys:
            candidate_records = grouped_result.get(key)
            if isinstance(candidate_records, list):
                records = candidate_records
                break
        if records is None:
            nested = grouped_result.get("result")
            if isinstance(nested, dict):
                for key in alternate_keys:
                    candidate_records = nested.get(key)
                    if isinstance(candidate_records, list):
                        records = candidate_records
                        break
    if not isinstance(records, list) or not records:
        return None

    candidates = []
    legacy_fields = {
        "total_revenue": ("total_revenue", "revenue", "sales"),
        "total_profit": ("total_profit", "profit"),
        "average_profit_margin": ("average_profit_margin",),
        "aggregate_profit_margin": ("aggregate_profit_margin",),
        "revenue_share_percent": ("revenue_share_percent",),
        "units_sold": ("units_sold", "units_solds", "units"),
    }
    for record in records:
        if not isinstance(record, dict):
            continue
        category = record.get(group_name) or record.get(group_name.title())
        value = next((record.get(field) for field in legacy_fields[requested_metric] if field in record), None)
        if isinstance(category, str) and isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            candidates.append((category, float(value)))
    if len(candidates) < 2:
        return None

    candidates.sort(key=lambda pair: pair[1], reverse=(direction == "highest"))
    category, value = candidates[0]
    metric_labels = {
        "total_revenue": "revenue",
        "total_profit": "profit",
        "average_profit_margin": "average profit margin",
        "aggregate_profit_margin": "aggregate profit margin",
        "revenue_share_percent": "revenue share",
        "units_sold": "units sold",
    }
    if requested_metric in {"average_profit_margin", "aggregate_profit_margin", "revenue_share_percent"}:
        formatted_value = f"{value:.2f}%"
    elif requested_metric in {"total_revenue", "total_profit"}:
        formatted_value = f"{value:,.2f}"
    else:
        formatted_value = f"{value:,.2f}"

    asks_for_gap = any(
        marker in question
        for marker in (
            "gap", "difference", "next one", "next highest",
            "second highest", "second-highest", "runner-up",
        )
    )
    asks_for_ranking = any(
        marker in question
        for marker in ("rank", "ranking", "top two", "top 2", "top categories")
    )
    if asks_for_ranking:
        ranking = []
        for index, (name, amount) in enumerate(candidates, start=1):
            amount_text = (
                f"{amount:.2f}%"
                if requested_metric in {
                    "average_profit_margin",
                    "aggregate_profit_margin",
                    "revenue_share_percent",
                }
                else f"{amount:,.2f}"
            )
            ranking.append(
                f"{index}. **{name}** — "
                f"{metric_labels[requested_metric]}: {amount_text}"
            )
        lines = [
            f"**{group_name.title()} ranking by {metric_labels[requested_metric]}:**",
            *ranking,
        ]
        if asks_for_gap and len(candidates) >= 2:
            gap = abs(candidates[0][1] - candidates[1][1])
            if requested_metric in {
                "average_profit_margin",
                "aggregate_profit_margin",
                "revenue_share_percent",
            }:
                gap_text = f"{gap:.2f} percentage points"
            else:
                gap_text = f"{gap:,.2f}"
            lines.append(f"**Gap between the top two:** {gap_text}.")
        return "\n".join(lines)

    if asks_for_gap and len(candidates) >= 2:
        next_category, next_value = candidates[1]
        gap = abs(value - next_value)
        if requested_metric in {
            "average_profit_margin",
            "aggregate_profit_margin",
            "revenue_share_percent",
        }:
            formatted_next_value = f"{next_value:.2f}%"
            formatted_gap = f"{gap:.2f} percentage points"
        else:
            formatted_next_value = f"{next_value:,.2f}"
            formatted_gap = f"{gap:,.2f}"
        return (
            f"**{category}** contributes the most {metric_labels[requested_metric]} "
            f"({formatted_value}). **{next_category}** is next "
            f"({formatted_next_value}), a gap of **{formatted_gap}**."
        )

    return f"The {group_name} with the {direction} {metric_labels[requested_metric]} is **{category}**, at **{formatted_value}**."


def latest_analysis_results(analysis_results: list[dict]) -> list[dict]:
    """Keep the latest stored result for each analysis name."""
    latest = {}

    # The existing repository returns runs oldest-first.
    for item in analysis_results:
        name = item.get("analysis_name")
        if name:
            latest[name] = item

    return list(latest.values())


def is_analytical_question(question: str) -> bool:
    text = question.lower()

    terms = (
        "revenue", "sales", "profit", "margin", "category",
        "product", "customer", "region", "trend", "compare",
        "comparison", "highest", "lowest", "top", "bottom",
        "increase", "decrease", "growth", "percentage", "percent",
        "average", "median", "correlation", "outlier", "distribution",
        "retention", "marketing", "units", "orders", "metrics",
        "statistics", "chart", "visualize", "visualization",
        "how much", "how many", "rank", "performance", "discount",
    )

    return any(term in text for term in terms)

def display_value(value: Any) -> str:
    """Format a value for display without inferring its unit or meaning."""
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        if not math.isfinite(value):
            return "—"
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    if isinstance(value, (dict, list)):
        return json.dumps(to_json_safe(value), ensure_ascii=False, allow_nan=False)
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown_table(records: list[dict], max_rows: int = 25) -> list[str]:
    """Render a homogeneous list of records as a Markdown table."""
    if not records:
        return ["No records were returned."]
    keys = []
    for row in records:
        for key in row:
            if key not in keys:
                keys.append(key)
    if not keys:
        return ["No tabular fields were returned."]
    shown = records[:max_rows]
    lines = [
        "| " + " | ".join(str(k).replace("|", "\\|") for k in keys) + " |",
        "| " + " | ".join("---" for _ in keys) + " |",
    ]
    for row in shown:
        lines.append(
            "| " + " | ".join(display_value(row.get(k)) for k in keys) + " |"
        )
    if len(records) > max_rows:
        lines.append(
            f"\nShowing {max_rows} of {len(records)} rows. "
            "The stored analytical result contains the full result."
        )
    return lines

def render_result_node(value: Any, depth: int = 0) -> list[str]:
    """
    Render arbitrary analytics result structures as readable Markdown.
    This is presentation only: it does not calculate, rank, relabel,
    infer units, or change the semantics of stored values.
    """
    if value is None:
        return ["No result was stored."]
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            title = str(key).replace("_", " ").strip().capitalize()
            if isinstance(item, list) and item and all(
                isinstance(row, dict) for row in item
            ):
                lines.append(f"\n**{title}**")
                lines.extend(markdown_table(item))
            elif isinstance(item, dict):
                lines.append(f"\n**{title}**")
                lines.extend(render_result_node(item, depth + 1))
            elif isinstance(item, list):
                lines.append(f"\n**{title}**")
                if not item:
                    lines.append("No values.")
                else:
                    for entry in item[:25]:
                        lines.append(f"- {display_value(entry)}")
                    if len(item) > 25:
                        lines.append(f"- … {len(item) - 25} more values")
            else:
                lines.append(f"- **{title}:** {display_value(item)}")
        return lines or ["No result fields were returned."]
    if isinstance(value, list) and value and all(
        isinstance(row, dict) for row in value
    ):
        return markdown_table(value)
    if isinstance(value, list):
        return [f"- {display_value(item)}" for item in value[:25]]
    return [f"- {display_value(value)}"]


def format_deterministic_analytics_answer(
    analysis_results: list[dict],
    question: str | None = None,
) -> str:
    """
    Render persisted Python analytics results for any registered analysis.

    If a question is supplied, only relevant stored analyses are selected.
    Displayed values come from persisted result objects. Requested category
    rankings and gaps are calculated deterministically from those stored rows;
    this function does not invent values or infer units.
    """
    results = latest_analysis_results(analysis_results)

    if question:
        results = select_relevant_analysis_results(results, question)

    if not results:
        return (
            "I couldn't find a completed analytical result that directly "
            "answers this question. Please run the relevant analysis or "
            "check that the requested tool is registered and supported."
        )

    if question:
        focused_category_answer = answer_category_comparison(
            question,
            results,
        )
        if focused_category_answer:
            return focused_category_answer

    sections = ["## Results calculated from your dataset"]
    for item in results:
        name = str(item.get("analysis_name") or "Analysis")
        sections.append(f"\n### {name.replace('_', ' ').title()}")
        result = item.get("result")
        if name == "category_performance" and isinstance(result, dict):
            # Keep the legacy alias out of user-facing output: its meaning was
            # average row-level margin, while users often interpret "margin"
            # as aggregate margin.
            result = dict(result)
            result.pop("highest_margin_category", None)
        sections.extend(render_result_node(result))

    sections.append(
        "\n*Figures and labels above are rendered from stored Python "
        "analytics results. Units and metric definitions are shown only "
        "when supplied by the analytical result; no causal explanation "
        "is inferred from descriptive statistics alone.*"
    )
    return "\n".join(sections)
