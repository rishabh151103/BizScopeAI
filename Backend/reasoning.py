from typing import Optional

from .schemas import AnalysisRequirement
from .analytics_registry import ANALYTICS_REGISTRY


# ---------------------------------------------------------------------------
# Canonical intent normalization
# ---------------------------------------------------------------------------

METRIC_ALIASES = {
    "sales": "revenue",
    "sales revenue": "revenue",
    "revenue": "revenue",
    "revenue change": "revenue",
    "change in revenue": "revenue",
    "sales change": "revenue",
    "profit": "profit",
    "profits": "profit",
    "profit change": "profit",
    "profit margin": "profit_margin",
    "profit margins": "profit_margin",
    "average profit margin": "average_profit_margin",
    "average margin": "average_profit_margin",
    "aggregate profit margin": "aggregate_profit_margin",
    "overall profit margin": "aggregate_profit_margin",
    "margin": "profit_margin",
    "margins": "profit_margin",
    "units": "units",
    "unit": "units",
    "quantity": "units",
    "orders": "orders",
    "order count": "orders",
    "average order value": "average_order_value",
    "aov": "average_order_value",
    "repeat revenue": "repeat_revenue",
    "revenue from repeat customers": "repeat_revenue",
    "retention": "retention",
    "marketing efficiency": "marketing_efficiency",
    "revenue per marketing spend": "revenue_per_marketing_spend",
    "profit per marketing spend": "profit_per_marketing_spend",
    "correlation": "correlation",
    "correlations": "correlation",
    "outlier": "outlier",
    "outliers": "outlier",
    "anomaly": "outlier",
    "anomalies": "outlier",
    "distribution": "distribution",
    "variability": "distribution",
    "volatility": "distribution",
    "spread": "distribution",
}

DIMENSION_ALIASES = {
    "business": "business",
    "overall business": "business",
    "overall": "business",
    "time": "time",
    "date": "time",
    "time period": "time",
    "month": "month",
    "monthly": "month",
    "product": "product",
    "products": "product",
    "category": "category",
    "categories": "category",
    "discount": "discount",
    "discount level": "discount",
    "discount band": "discount",
    "region": "region",
    "regions": "region",
    "customer": "customer",
    "customers": "customer",
    "customer type": "customer_type",
    "customer_type": "customer_type",
    "customer types": "customer_type",
    "returning customers": "customer_type",
    "repeat customers": "customer_type",
    "order": "order",
    "orders": "order",
    "marketing spend": "marketing_spend",
    "marketing_spend": "marketing_spend",
    "marketing spending": "marketing_spend",
    "data": "data",
    "data point": "data",
    "data points": "data",
    "numeric variables": "numeric_variables",
    "numerical variables": "numeric_variables",
    "numeric variable": "numeric_variables",
}

OPERATION_ALIASES = {
    "trend": "trend",
    "change over time": "trend",
    "growth": "trend",
    "increasing": "trend",
    "decreasing": "trend",
    "comparison": "comparison",
    "compare": "comparison",
    "maximum": "maximum",
    "max": "maximum",
    "highest": "maximum",
    "most": "maximum",
    "best": "maximum",
    "minimum": "minimum",
    "min": "minimum",
    "lowest": "minimum",
    "largest increase": "largest_increase",
    "biggest increase": "largest_increase",
    "largest decrease": "largest_decrease",
    "biggest decrease": "largest_decrease",
    "biggest drop": "largest_decrease",
    "largest drop": "largest_decrease",
    "sharpest decline": "largest_decrease",
    "sharpest drop": "largest_decrease",
    "efficiency": "efficiency",
    "return": "return",
    "correlation": "correlation",
    "relationship": "correlation",
    "detect": "detect",
    "detection": "detect",
    "distribution": "distribution",
    "variability": "distribution",
    "volatility": "distribution",
    "spread": "distribution",
    "share": "share",
    "contribution": "contribution",
    "retention": "retention",
    "repeat": "repeat",
    "overall": "overall",
    "summary": "summary",
    "performance": "performance",
    # Generic calculation requests over a business dimension mean
    # aggregate/compare the requested metric by that dimension.
    "calculate": "performance",
    "calculation": "performance",
    "calculate totals": "performance",
    "calculate total": "performance",
    "calculate the total": "performance",
    "change": "change",
    "count": "count",
    "average": "average",
    "mean": "average",
    "median": "median",
}




def normalize_value(value: Optional[str], aliases: dict) -> Optional[str]:
    """Normalize extracted intent fields to canonical capability values."""

    if value is None:
        return None

    normalized = str(value).strip().lower().replace("-", "_")
    if not normalized:
        return None

    if aliases is METRIC_ALIASES:
        # Check specific margin definitions before generic profit margin.
        if "aggregate_profit_margin" in normalized or "aggregate profit margin" in normalized:
            return "aggregate_profit_margin"
        if "average_profit_margin" in normalized or "average profit margin" in normalized:
            return "average_profit_margin"

    if normalized in aliases:
        return aliases[normalized]

    if normalized in set(aliases.values()):
        return normalized

    if aliases is METRIC_ALIASES:
        if "profit margin" in normalized or "profit_margin" in normalized:
            return "profit_margin"
        if "repeat" in normalized and "revenue" in normalized:
            return "repeat_revenue"
        if "average order" in normalized or "aov" in normalized:
            return "average_order_value"
        if "marketing" in normalized and "efficiency" in normalized:
            return "marketing_efficiency"
        if "profit per marketing spend" in normalized:
            return "profit_per_marketing_spend"
        if "revenue per marketing spend" in normalized:
            return "revenue_per_marketing_spend"
        if "correlat" in normalized:
            return "correlation"
        if "outlier" in normalized or "anomal" in normalized:
            return "outlier"
        if any(word in normalized for word in (
            "variability", "volatility", "distribution", "spread"
        )):
            return "distribution"
        if "profit" in normalized:
            return "profit"
        if "revenue" in normalized or "sales" in normalized:
            return "revenue"
        if "quantity" in normalized or "units" in normalized:
            return "units"
        if "order" in normalized:
            return "orders"

    if aliases is DIMENSION_ALIASES:
        if "customer" in normalized and "type" in normalized:
            return "customer_type"
        if "returning customer" in normalized or "repeat customer" in normalized:
            return "customer_type"
        if "marketing" in normalized and "spend" in normalized:
            return "marketing_spend"
        if "numeric" in normalized and "variable" in normalized:
            return "numeric_variables"
        if "category" in normalized:
            return "category"
        if "region" in normalized:
            return "region"
        if "product" in normalized:
            return "product"
        if "customer" in normalized:
            return "customer"
        if "month" in normalized:
            return "month"
        if normalized in {"time", "date", "period"}:
            return "time"
        if "order" in normalized:
            return "order"

    if aliases is OPERATION_ALIASES:
        if normalized in {"sum", "total", "aggregation", "aggregate"}:
            return "performance"
        if normalized in {"group by", "grouped comparison"}:
            return "comparison"
        if any(x in normalized for x in ("biggest", "largest", "sharpest")):
            if any(x in normalized for x in (
                "drop", "decrease", "decline", "fall"
            )):
                return "largest_decrease"
            if "increase" in normalized:
                return "largest_increase"
        if "correlat" in normalized or "relationship" in normalized:
            return "correlation"
        if any(x in normalized for x in (
            "variability", "volatility", "distribution", "spread"
        )):
            return "distribution"
        if any(x in normalized for x in ("compare", "comparison")):
            return "comparison"
        if any(x in normalized for x in ("highest", "maximum", "most")):
            return "maximum"
        if any(x in normalized for x in ("lowest", "minimum", "least")):
            return "minimum"

    return normalized


def normalize_metrics(value: Optional[str]) -> set[str]:
    """Extract all metrics explicitly requested in a requirement."""

    if value is None:
        return set()

    text = str(value).strip().lower().replace("-", "_")
    if not text:
        return set()

    metrics = set()

    # Identify compound concepts before individual words.
    if "aggregate_profit_margin" in text or "aggregate profit margin" in text:
        metrics.add("aggregate_profit_margin")
        text = text.replace("aggregate_profit_margin", "")
        text = text.replace("aggregate profit margin", "")
    elif "average_profit_margin" in text or "average profit margin" in text:
        metrics.add("average_profit_margin")
        text = text.replace("average_profit_margin", "")
        text = text.replace("average profit margin", "")
    elif "profit margin" in text or "profit_margin" in text:
        metrics.add("profit_margin")
        text = text.replace("profit margin", "")
        text = text.replace("profit_margin", "")

    if "repeat" in text and "revenue" in text:
        metrics.add("repeat_revenue")
    elif "revenue per marketing spend" in text:
        metrics.add("revenue_per_marketing_spend")
    elif "profit per marketing spend" in text:
        metrics.add("profit_per_marketing_spend")
    else:
        if "sales" in text or "revenue" in text:
            metrics.add("revenue")
        if "profit" in text:
            metrics.add("profit")

    if "average order value" in text or "aov" in text:
        metrics.add("average_order_value")
    if "marketing efficiency" in text:
        metrics.add("marketing_efficiency")
    if "correlat" in text:
        metrics.add("correlation")
    if "outlier" in text or "anomal" in text:
        metrics.add("outlier")
    if any(word in text for word in (
        "distribution", "variability", "volatility", "spread"
    )):
        metrics.add("distribution")
    if "retention" in text:
        metrics.add("retention")
    if "units" in text or "quantity" in text:
        metrics.add("units")
    if "orders" in text or "order count" in text:
        metrics.add("orders")

    # Fall back to the existing canonical metric normalization.
    if not metrics:
        canonical = normalize_value(value, METRIC_ALIASES)
        if canonical:
            metrics.add(canonical)

    return metrics


# ---------------------------------------------------------------------------
# Tool capability contracts
# ---------------------------------------------------------------------------

ANALYSIS_CAPABILITIES = {
    "revenue_trend": {
        "metrics": {"revenue"},
        "dimensions": {"time", "month"},
        "operations": {"trend"},
    },
    "category_revenue_trend": {
        "metrics": {"revenue"},
        "dimensions": {"category"},
        "operations": {"trend"},
    },
    "profitability": {
        "metrics": {"profit", "profit_margin"},
        "dimensions": {"business"},
        "operations": {"overall", "summary"},
    },
    "product_performance": {
        "metrics": {"revenue", "profit", "profit_margin", "units"},
        "dimensions": {"product"},
        "operations": {"maximum", "minimum", "comparison", "performance"},
    },
    "customer_performance": {
        "metrics": {"revenue", "profit"},
        "dimensions": {"customer"},
        "operations": {"maximum", "minimum", "comparison", "performance"},
    },
    "customer_type": {
        "metrics": {"revenue", "profit", "orders", "units", "average_order_value"},
        "dimensions": {"customer_type"},
        "operations": {"maximum", "minimum", "comparison", "share"},
    },
    "category_performance": {
        "metrics": {"revenue", "profit", "profit_margin","average_profit_margin","aggregate_profit_margin","units"},
        "dimensions": {"category"},
        "operations": {"maximum", "minimum", "comparison", "performance", "average"},
    },
    "discount_performance": {
        "metrics": {
            "revenue", "profit", "profit_margin",
            "average_profit_margin", "aggregate_profit_margin",
        },
        "dimensions": {"discount"},
        "operations": {"comparison", "performance", "distribution"},
    },
    "regional_performance": {
        "metrics": {
            "revenue", "profit", "profit_margin",
            "average_profit_margin", "units",
        },
        "dimensions": {"region"},
        "operations": {
            "maximum", "minimum", "comparison", "performance", "average",
        },
    },
    "monthly_performance": {
        "metrics": {"revenue", "profit", "units", "orders"},
        "dimensions": {"time", "month"},
        "operations": {"comparison", "performance"},
    },
    "correlations": {
        "metrics": {"correlation"},
        "dimensions": {"numeric_variables"},
        "operations": {"correlation"},
    },
    "business_comparisons": {
        "metrics": {"revenue", "profit", "profit_margin", "units", "orders"},
        "dimensions": {"business"},
        "operations": {"comparison"},
    },
    "significant_changes": {
        "metrics": {"revenue", "profit"},
        "dimensions": {"time", "month"},
        "operations": {"largest_decrease", "largest_increase"},
    },
    "segment_changes": {
        "metrics": {"revenue"},
        "dimensions": {"product", "category", "region", "customer_type"},
        "operations": {"change"},
    },
    "change_contribution": {
        "metrics": {"revenue"},
        "dimensions": {"product", "category", "region", "customer_type"},
        "operations": {"contribution"},
    },
    "order_metrics": {
        "metrics": {"average_order_value", "orders", "units", "revenue"},
        "dimensions": {"order"},
        "operations": {"average", "median", "count", "performance"},
    },
    "marketing_performance": {
        "metrics": {
            "revenue_per_marketing_spend",
            "profit_per_marketing_spend",
            "marketing_efficiency",
            "revenue",
            "profit",
        },
        "dimensions": {"marketing_spend"},
        "operations": {"efficiency", "return", "performance"},
    },
    "customer_retention": {
    "metrics": {
        "repeat_revenue",
        "retention",
        "repeat_customers",
        "one_time_customers",
    },
    "dimensions": {
        "customer",
    },
    "operations": {
        "retention",
        "share",
        "repeat",
    },
},
    "distribution_statistics": {
        "metrics": {"revenue", "profit", "units", "distribution"},
        "dimensions": {"data"},
        "operations": {"distribution"},
    },
    "outliers": {
        "metrics": {"outlier"},
        "dimensions": {"data"},
        "operations": {"detect"},
    },
}


# Keep the capability catalogue aligned with the actual registry.
_missing_registry_tools = set(ANALYSIS_CAPABILITIES) - set(ANALYTICS_REGISTRY)
if _missing_registry_tools:
    raise RuntimeError(
        "Reasoning capabilities reference unregistered analytics tools: "
        f"{sorted(_missing_registry_tools)}"
    )


def _normalized_requirement(requirement: AnalysisRequirement) -> dict:
    return {
        "metric": normalize_value(requirement.metric, METRIC_ALIASES),
        "dimension": normalize_value(requirement.dimension, DIMENSION_ALIASES),
        "operation": normalize_value(requirement.operation, OPERATION_ALIASES),
    }



def score_tool(requirement: AnalysisRequirement, tool_name: str) -> int:
    """Score tools against every explicitly requested intent field."""

    capability = ANALYSIS_CAPABILITIES[tool_name]
    normalized = _normalized_requirement(requirement)
    metrics = normalize_metrics(requirement.metric)

    score = 0

    if metrics:
        score += 8 if metrics.issubset(capability["metrics"]) else -8

    if normalized["dimension"] is not None:
        score += (
            5 if normalized["dimension"] in capability["dimensions"] else -5
        )

    if normalized["operation"] is not None:
        score += (
            6 if normalized["operation"] in capability["operations"] else -6
        )

    return score


def rank_tools(requirement: AnalysisRequirement):
    ranked = [
        (tool_name, score_tool(requirement, tool_name))
        for tool_name in ANALYSIS_CAPABILITIES
    ]
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked



def get_candidate_tools(requirement: AnalysisRequirement):
    """Return only tools supporting every explicitly requested field."""

    normalized = _normalized_requirement(requirement)
    metrics = normalize_metrics(requirement.metric)
    candidates = []

    for tool_name, capability in ANALYSIS_CAPABILITIES.items():
        if metrics and not metrics.issubset(capability["metrics"]):
            continue

        if (
            normalized["dimension"] is not None
            and normalized["dimension"] not in capability["dimensions"]
        ):
            continue

        if (
            normalized["operation"] is not None
            and normalized["operation"] not in capability["operations"]
        ):
            continue

        candidates.append(tool_name)

    return candidates



def resolve_candidates(requirement: AnalysisRequirement):
    """Resolve tools that match every explicitly specified intent field."""
    return get_candidate_tools(requirement)

def resolve_deterministically(requirement: AnalysisRequirement):
    """Resolve an extracted requirement without calling an LLM."""

    candidates = resolve_candidates(requirement)

    if not candidates:
        return {
            "tool": None,
            "score": 0,
            "second_score": 0,
            "candidates": [],
            "ranked": [],
            "normalized": _normalized_requirement(requirement),
            "supported": False,
            "reason": "No analytical tool supports this requirement.",
        }

    ranked = [
        item for item in rank_tools(requirement)
        if item[0] in candidates
    ]

    best_tool, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    return {
        "tool": best_tool,
        "score": best_score,
        "second_score": second_score,
        "candidates": candidates,
        "ranked": ranked,
        "normalized": _normalized_requirement(requirement),
        "supported": True,
        "reason": None,
    }


AMBIGUITY_MARGIN = 2


def is_ambiguous(result: dict) -> bool:
    """Return True only when multiple candidates are effectively tied."""

    return (
        len(result["candidates"]) > 1
        and result["score"] - result["second_score"] <= AMBIGUITY_MARGIN
    )


def validate_resolved_tool(tool_name: str, candidates):
    """Validate a final choice against the allowed candidate set."""

    if tool_name not in candidates:
        raise ValueError(
            f"Tool '{tool_name}' is not a valid candidate. "
            f"Candidates: {candidates}"
        )

    if tool_name not in ANALYTICS_REGISTRY:
        raise ValueError(
            f"Tool '{tool_name}' is not registered in ANALYTICS_REGISTRY."
        )

    return tool_name
