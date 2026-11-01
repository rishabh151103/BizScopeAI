from .llm_client import OllamaCallError, call_ollama, PLANNER_MODEL
from .schemas import (
    RequirementPlan,
    AnalysisPlan,
    ToolSelection,
    AnalysisSelection,
    AnalysisRequirement,
    EvidenceRequirement
)
from .analytics_registry import ANALYTICS_REGISTRY
from .reasoning import (
    resolve_deterministically,
    is_ambiguous,
    validate_resolved_tool,
)

# ============================================================
# Stage 1: Question Understanding
# ============================================================

def build_requirement_prompt(question):
       
    """Build the Stage-1 prompt for structured analytical intent extraction."""
    return f"""
You are the analytical-intent extraction component of BizScopeAI.
Convert the user's business question into the minimum number of
structured analytical requirements needed to answer it. Do not choose
tools and do not perform calculations.
For every requirement return:
- requirement: concise description of the exact analytical ask
- metric: one canonical metric from the allowed list, or null
- dimension: one canonical dimension from the allowed list, or null
- operation: one canonical operation from the allowed list, or null
- start_month: starting month of the requested comparison period, if explicitly stated, otherwise null
- end_month: ending month of the requested comparison period, if explicitly stated, otherwise null
CANONICAL METRICS
-----------------
revenue
profit
profit_margin
units
orders
average_order_value
repeat_revenue
retention
marketing_efficiency
revenue_per_marketing_spend
profit_per_marketing_spend
correlation
outlier
distribution
CANONICAL DIMENSIONS
--------------------
business
time
month
product
category
region
customer
customer_type
order
marketing_spend
data
numeric_variables
CANONICAL OPERATIONS
--------------------
trend
comparison
maximum
minimum
largest_increase
largest_decrease
efficiency
correlation
detect
distribution
share
contribution
retention
overall
summary
performance
change
count
average
median
return
repeat
SEMANTIC RULES
--------------
1. Use the most specific canonical metric, dimension, and operation.
2. "Why" does not imply causal analysis. Extract the measurable ask.
3. "How has revenue changed over time?" means revenue + time + trend.
4. "Biggest/largest/sharpest drop or increase" means the corresponding
   largest_decrease or largest_increase operation, not trend.
5. Product/category/region/customer/customer_type questions use that
   dimension explicitly.
6. Overall business profitability uses business + profit/profit_margin
   + overall/summary. Product profitability uses product +
   profit/profit_margin + comparison/maximum/minimum/performance.
7. Marketing efficiency means marketing_spend + efficiency/return.
   Statistical correlation means numeric_variables + correlation.
8. Repeat/returning customer revenue or retention uses customer_type
   or customer + repeat_revenue/retention + repeat/share/retention.
9. Unusual, abnormal, or outlier values use data + outlier + detect.
10. Variability, volatility, spread, or statistical distribution uses
    data + distribution.
11. Average order value uses order + average_order_value + average.
12. Do not invent dimensions, metrics, operations, or external causes.
13. If one question contains two genuinely distinct analytical asks,
    create two requirements. Otherwise create exactly one.
14. Each requirement must contain exactly ONE canonical metric.
    If a question requests multiple metrics, create one requirement
    per metric, preserving the same dimension and relevant operation.
    Example: "Compare total sales and profit by category" produces:
    - revenue + category + performance
    - profit + category + performance
    Use "performance" for aggregating totals by a dimension.
    Never combine "revenue, profit" into one metric field.
    Never infer that a metric increased, decreased, or performed well
    before the dataset has been analyzed.
EXAMPLES
--------
Question: Why has our revenue declined?
Requirement: Determine the overall revenue trend over time
metric: revenue
dimension: time
operation: trend
start_month: null
end_month: null
Question: How did product revenue change between January and February 2025?
Requirement: Compare product revenue between January and February 2025
metric: revenue
dimension: product
operation: change
start_month: 2025-01
end_month: 2025-02
Question: What was the biggest monthly revenue drop?
Requirement: Identify the largest monthly revenue decrease
metric: revenue
dimension: month
operation: largest_decrease
Question: How has revenue changed over time by category?
Requirement: Calculate monthly revenue trends separately for each category
metric: revenue
dimension: category
operation: trend
Question: Which product has the highest profit margin?
Requirement: Compare product profit margins
metric: profit_margin
dimension: product
operation: maximum
Question: Is marketing spending generating enough revenue?
Requirement: Evaluate revenue generated from marketing spending
metric: revenue
dimension: marketing_spend
operation: efficiency
Question: Is marketing spend correlated with revenue?
Requirement: Measure the statistical correlation between marketing spend and revenue
metric: correlation
dimension: numeric_variables
operation: correlation
Question: How much revenue comes from repeat customers?
Requirement: Measure revenue contribution from repeat customers
metric: repeat_revenue
dimension: customer_type
operation: share
CUSTOMER TYPE VS CUSTOMER RETENTION
-----------------------------------
These concepts are related but they are NOT interchangeable.
Use customer_type when the question compares New and Returning
customers as business segments.
Examples:
"Which customer type generates the most revenue?"
→ requirement: "Compare revenue contribution by customer type"
→ metric: "revenue"
→ dimension: "customer_type"
→ operation: "maximum"
"Are returning customers contributing most of our revenue?"
→ requirement: "Compare revenue contribution by customer type"
→ metric: "revenue"
→ dimension: "customer_type"
→ operation: "share"
"How much revenue comes from New versus Returning customers?"
→ requirement: "Compare revenue by customer type"
→ metric: "revenue"
→ dimension: "customer_type"
→ operation: "comparison"
Use customer_retention when the question is specifically about
repeat-purchase behavior, retention, or one-time versus repeat
customers.
Examples:
"How much revenue comes from repeat customers?"
→ requirement: "Measure revenue contribution from repeat customers"
→ metric: "repeat_revenue"
→ dimension: "customer"
→ operation: "share"
"What percentage of customers are repeat customers?"
→ requirement: "Measure repeat customer retention"
→ metric: "retention"
→ dimension: "customer"
→ operation: "share"
"How many customers are one-time versus repeat?"
→ requirement: "Compare repeat and one-time customers"
→ metric: "repeat_customers"
→ dimension: "customer"
→ operation: "comparison"
"How strong is customer retention?"
→ requirement: "Measure customer retention"
→ metric: "retention"
→ dimension: "customer"
→ operation: "retention"
IMPORTANT:
"returning customer" does NOT automatically mean
"repeat_revenue".
If the question asks whether Returning customers contribute
more revenue than another customer type, use:
metric = revenue
dimension = customer_type
If the question explicitly asks about repeat-customer behavior
or retention, use customer_retention.
INDIVIDUAL CUSTOMER VS CUSTOMER TYPE
------------------------------------
These concepts are different.
Use dimension = customer when the question refers to
individual customers or asks which specific customers generate
the most revenue or profit.
Examples:
"Which customers generate the most revenue?"
→ requirement: "Compare revenue contribution by individual customer"
→ metric: "revenue"
→ dimension: "customer"
→ operation: "maximum"
"Which customers are most profitable?"
→ requirement: "Compare profit contribution by individual customer"
→ metric: "profit"
→ dimension: "customer"
→ operation: "maximum"
"Which customer generates the most revenue?"
→ requirement: "Identify the customer generating the most revenue"
→ metric: "revenue"
→ dimension: "customer"
→ operation: "maximum"
Use dimension = customer_type only when the question refers to
customer groups or types such as New versus Returning.
Examples:
"Which customer type generates the most revenue?"
→ metric: "revenue"
→ dimension: "customer_type"
→ operation: "maximum"
"Do Returning customers contribute more revenue than New customers?"
→ metric: "revenue"
→ dimension: "customer_type"
→ operation: "comparison"
IMPORTANT:
"customers" means individual customers.
"customer type" means groups such as New and Returning.
Do NOT convert "customers" into "customer_type" unless the
question explicitly refers to customer types or customer groups.
USER QUESTION
-------------
{question}
Return a structured RequirementPlan using only the canonical values above.
"""



def extract_requirements(question):
    """
    Use the planner LLM to decompose the user's question
    into structured analytical requirements.
    """
    if not question or not question.strip():
        raise ValueError("Business question cannot be empty.")

    prompt = build_requirement_prompt(question)

    data = {
        "messages": [
            {
                "role": "system",
                "content": prompt,
            }
        ],
        "format": RequirementPlan.model_json_schema(),
        "stream": False,
        "think": False,
        "options": {
            "num_ctx": 8192
        },
    }

    result = call_ollama(data, PLANNER_MODEL)

    assistant_response = result["message"]["content"]

    plan = RequirementPlan.model_validate_json(
        assistant_response
    )

    return plan


# ============================================================
# Stage 2: Tool Catalogue
# ============================================================


def build_tool_catalogue():
    """
    Build the analytical tool catalogue directly from the
    analytics registry.

    The registry is the single source of truth.
    """
    catalogue = []

    for name, config in ANALYTICS_REGISTRY.items():
        catalogue.append(
            {
                "name": name,
                "description": config["description"],
                "answers": config["answers"],
            }
        )

    return catalogue


# ============================================================
# Stage 2: Deterministic Tool Resolution
# ============================================================


def select_tool_for_requirement(requirement):
    """
    Select exactly one analytical tool for one requirement.

    Resolution strategy:
    1. Deterministic capability matching.
    2. If the result is unambiguous, use it directly.
    3. If multiple candidates are genuinely ambiguous, use the
       planner LLM to choose only among those candidates.
    """
    result = resolve_deterministically(requirement)
    fallback_tool = result["tool"]

    if not result["supported"]:
        raise ValueError(
            "Unsupported analytical requirement:",
            f" {requirement.requirement}.",
            "No compatible analytical tool is available."
        )

    candidates = result["candidates"]

    # Clear deterministic winner.
    if not is_ambiguous(result):
        selected_tool = result["tool"]

        validate_resolved_tool(
            selected_tool,
            candidates
        )

        return ToolSelection(
            analysis_name=selected_tool
        )

    # --------------------------------------------------------
    # Ambiguous case
    # --------------------------------------------------------

    candidate_descriptions = []

    for tool_name in candidates:
        tool = ANALYTICS_REGISTRY[tool_name]

        candidate_descriptions.append(
            (
                f"TOOL: {tool_name}\n"
                f"DESCRIPTION: {tool['description']}\n"
                f"CAN ANSWER:\n"
                + "\n".join(
                    f"- {example}"
                    for example in tool["answers"]
                )
            )
        )

    candidate_text = "\n\n".join(candidate_descriptions)

    prompt = f"""
You are resolving an ambiguity between analytical tools.

The analytical requirement has already been extracted.

Do NOT reinterpret the original user question.

Choose exactly ONE tool from the candidate list below.

REQUIREMENT
-----------
Requirement: {requirement.requirement}
Metric: {requirement.metric}
Dimension: {requirement.dimension}
Operation: {requirement.operation}

CANDIDATE TOOLS
---------------
{candidate_text}

Choose the tool whose documented purpose most directly answers
the requirement.

You MUST choose one of the candidate tools.

Return ONLY the structured ToolSelection.
"""

    data = {
        "messages": [
            {
                "role": "system",
                "content": prompt,
            }
        ],
        "format": ToolSelection.model_json_schema(),
        "stream": False,
        "think": False,
    }

    result = call_ollama(
        data,
        PLANNER_MODEL
    )

    assistant_response = result["message"]["content"]

    try:
        selection = ToolSelection.model_validate_json(
            assistant_response
        )

        validate_resolved_tool(
            selection.analysis_name,
            candidates
        )

        return selection

    except (ValueError, TypeError):
        # Invalid LLM output: use the deterministic winner, already validated
        # against the candidate set, instead of reading a nonexistent response key.
        validate_resolved_tool(fallback_tool, candidates)
        return ToolSelection(analysis_name=fallback_tool)


def select_tools(requirement_plan):
    if not requirement_plan.requirements:
        raise ValueError(
            "Requirement plan must contain at least one requirement."
        )

    selections = []

    for requirement in requirement_plan.requirements:
        selection = select_tool_for_requirement(
            requirement
        )

        selections.append(
            AnalysisSelection(
                analysis_name=selection.analysis_name,
                requirement=requirement
            )
        )

    return AnalysisPlan(
        question_summary=requirement_plan.question_summary,
        analyses=selections
    )


def select_analyses_from_requirement(
    evidence_requirement: EvidenceRequirement,
) -> AnalysisPlan | None:
    """Plan a follow-up evidence request without crashing the chat endpoint.

    LLMs can express a monthly trend as "change", "cumulative change", or
    even return the literal string "null" for optional dates. Normalize those
    variations to a registered analysis. Unsupported follow-ups are skipped;
    they must not turn an otherwise usable investigation into HTTP 500.
    """
    question = (evidence_requirement.question or "").strip()
    if not question:
        return None

    def clean(value):
        value = (value or "")
        value = str(value).strip()
        return None if value.lower() in {"", "null", "none", "n/a"} else value

    metric = (clean(evidence_requirement.metric) or "").lower()
    dimension = (clean(evidence_requirement.dimension) or "").lower().replace("_", " ")
    operation = (clean(evidence_requirement.operation) or "").lower().replace("_", " ")
    question_lower = question.lower()

    mentions_revenue = "revenue" in question_lower or metric in {"revenue", "sales"}
    mentions_discount = (
        "discount" in question_lower
        or dimension in {"discount", "discount level", "discount band"}
    )
    category_scoped = (
        any(token in question_lower for token in ("category", "categories", "product category"))
        or dimension in {"category", "categories", "product category"}
    )
    describes_time_series = any(
        token in question_lower
        for token in ("trend", "over time", "monthly", "month by month", "cumulative", "from the start of the dataset")
    )
    describes_change = any(
        token in question_lower for token in ("change", "changed", "growth", "increase", "decrease", "decline")
    ) or "change" in operation or "change" in metric

    # Regional performance is one registered grouped analysis that returns
    # revenue, profit, units, and row-level average margin together. Normalize
    # multi-metric requests to its supported aggregation instead of allowing a
    # noisy single-metric Qwen label (often average_profit_margin/average) to
    # make the deterministic capability resolver reject the whole request.
    regional_scope = (
        dimension in {"region", "regions"}
        or any(token in question_lower for token in ("by region", "by regions", "regional performance"))
    )
    if regional_scope and not describes_time_series:
        if metric in {
            "revenue", "sales", "profit", "profit_margin",
            "average_profit_margin", "units",
        }:
            regional_metric = metric
        elif "average profit margin" in question_lower or "average margin" in question_lower:
            regional_metric = "average_profit_margin"
        elif "profit margin" in question_lower or "margin" in question_lower:
            regional_metric = "profit_margin"
        elif "profit" in question_lower:
            regional_metric = "profit"
        elif "unit" in question_lower or "quantity" in question_lower:
            regional_metric = "units"
        else:
            regional_metric = "revenue"
        requirement = AnalysisRequirement(
            requirement=question,
            metric=regional_metric,
            dimension="region",
            operation="performance",
            start_month=clean(evidence_requirement.start_month),
            end_month=clean(evidence_requirement.end_month),
        )
        try:
            return select_tools(
                RequirementPlan(
                    question_summary=question,
                    requirements=[requirement],
                )
            )
        except OllamaCallError:
            raise
        except (ValueError, TypeError, RuntimeError):
            return None

    # Discount is a row-level dimension, not a category-level aggregate.
    # Route it directly to the registered tool so noisy planner labels such as
    # a category name in `dimension` cannot select category_performance.
    if mentions_discount:
        requirement = AnalysisRequirement(
            requirement=question,
            metric=(
                "revenue"
                if mentions_revenue and "profit" not in question_lower
                else "profit_margin"
            ),
            dimension="discount",
            operation="performance",
            start_month=clean(evidence_requirement.start_month),
            end_month=clean(evidence_requirement.end_month),
        )
        try:
            return select_tools(
                RequirementPlan(
                    question_summary=question,
                    requirements=[requirement],
                )
            )
        except OllamaCallError:
            # Do not disguise a timed-out/unavailable planner as an unsupported
            # analytical request; the API layer turns it into a useful 5xx.
            raise
        except (ValueError, TypeError, RuntimeError):
            return None

    # These requests are covered by the monthly trend tool. Route based on
    # the user's actual dimension, not on noisy LLM-generated operation labels.
    if mentions_revenue and describes_time_series and (describes_change or "trend" in question_lower):
        dimension_value = "category" if category_scoped else "month"
        tool_requirement = (
            "Calculate monthly revenue trends separately for each category"
            if category_scoped else
            "Calculate the overall monthly revenue trend"
        )
        requirement = AnalysisRequirement(
            requirement=tool_requirement + f". Evidence request: {question}",
            metric="revenue",
            dimension=dimension_value,
            operation="trend",
            start_month=clean(evidence_requirement.start_month),
            end_month=clean(evidence_requirement.end_month),
        )
    else:
        requirement = AnalysisRequirement(
            requirement=question,
            metric=clean(evidence_requirement.metric),
            dimension=clean(evidence_requirement.dimension),
            operation=clean(evidence_requirement.operation),
            start_month=clean(evidence_requirement.start_month),
            end_month=clean(evidence_requirement.end_month),
        )

    requirement_plan = RequirementPlan(
        question_summary=question,
        requirements=[requirement],
    )

    try:
        return select_tools(requirement_plan)
    except OllamaCallError:
        raise
    except (ValueError, TypeError, RuntimeError):
        # This API is used for secondary evidence requests. If no registered
        # tool can answer one, skip it and preserve the already completed work.
        return None


# ============================================================
# Public Planner API
# ============================================================


def select_analyses(question):
    """
    Complete analytical planning pipeline.

    Stage 1:
        User question -> Qwen3 requirement extraction

    Stage 2:
        Requirement -> deterministic capability resolution
        -> Qwen only for genuine ambiguity
    """
    if not question or not question.strip():
        raise ValueError("Business question cannot be empty.")

    requirement_plan = extract_requirements(question)

    return select_tools(requirement_plan)
