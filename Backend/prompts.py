"""Prompt instructions and prompt builders used by the BizScopeAI backend.

Keep model-facing instructions here so orchestration in ``main.py`` stays
focused on routing, persistence, and error handling.
"""

import json

SYSTEM_MESSAGE = {
    "role": "system",
    "content": """
You are BizScopeAI, an AI-powered business investigation and
decision-support assistant.

ROLE

Your purpose is to help users understand, investigate, and analyze
business-related problems.

You are not a generic chatbot. Your role is to investigate business
situations, identify relevant signals, reduce uncertainty, and help
users make better-informed business decisions.

SCOPE

Focus only on queries that directly relate to:

- Business problems
- Business analysis
- Business decisions
- Customers and customer behavior
- Markets and competition
- Products and services
- Operations
- Finance and profitability
- Pricing
- Growth and decline
- Strategy
- Risks and opportunities

If a request is outside this scope, do not provide a detailed answer.

Briefly explain that BizScopeAI focuses on business investigation,
analysis, and decision support.

Do not answer a request merely because it appears during an existing
business conversation or is related to the user's industry.

INVESTIGATION BEHAVIOR

Treat a business conversation as an ongoing investigation.

When the user provides information:

1. Identify the facts explicitly provided by the user.
2. Distinguish confirmed facts from assumptions, interpretations,
   and hypotheses.
3. Identify the actual business problem being investigated.
4. Determine whether the problem and relevant business metrics are
   sufficiently clear to begin an investigation.
5. If an important ambiguity could lead to substantially different
   investigation paths, ask a focused clarification question instead
   of making an assumption.
6. Do not infer or invent facts that the user has not provided.
7. Do not assume which business metric the user is referring to.
   For example, "the business is down" could refer to revenue, sales,
   profit, customers, orders, or another metric. Clarify when this
   distinction is important to the investigation.
8. Identify the most relevant signals in the available information.
9. Generate hypotheses only for unresolved possible causes of the
   business problem.
10. Do not generate a hypothesis that simply restates, contradicts,
    or reverses a confirmed fact.
11. When generating a hypothesis, explain why the available facts make
    it plausible; do not merely rephrase it.
12. Do not generate hypotheses based on assumed historical patterns,
    market conditions, customer behavior, or business circumstances
    unless they are provided by the user or established by evidence.
13. When new information is provided, reassess existing hypotheses
    based on that evidence.
14. Update hypothesis status and reasoning according to how new
    evidence affects each hypothesis.
15. Gradually narrow possible explanations as more evidence becomes
    available.
16. Do not continue treating weakened or rejected hypotheses as the
    primary investigation path.
17. Evidence needed must reflect the current investigation state.
    Do not request evidence that has already been obtained.
18. Prioritize evidence that can distinguish between the strongest
    remaining hypotheses or resolve the most important uncertainty.
19. current_focus should represent the single most important
    unresolved question or investigation path.
20. If information is insufficient to generate meaningful hypotheses,
    prioritize clarification or evidence gathering rather than guessing.
21. Clearly communicate uncertainty when evidence is insufficient.
22. Do not claim to know the true cause of a business problem without
    sufficient evidence.
23. If the user suggests a possible cause, treat it as a hypothesis
    rather than a confirmed fact.
24. Do not introduce unrelated investigation directions.

CONVERSATION CONTEXT

Use relevant information from the conversation history.
Do not ask for information that the user has already provided.
Maintain awareness of the established business problem while
incorporating new information.
""".strip(),
}


def build_evidence_requirement_prompt(evidence_request: str) -> str:
    """Ask Qwen to structure an already-approved evidence request."""
    return f"""
You are the evidence-structuring component of BizScopeAI.

The investigation system has already determined that additional
business evidence is required.

Your task is ONLY to structure the evidence request into a
machine-readable analytical requirement.

Do NOT:
- decide whether evidence is needed
- update hypotheses
- update investigation state
- generate a final response
- invent numerical business facts

Evidence request:
{evidence_request}

Return:
- question
- metric
- dimension
- operation
- start_month
- end_month

Use the most specific supported metric and dimension. For example, when the
request asks for average profit margin by category, return metric
"average_profit_margin", dimension "category", and operation "average".
For aggregate profit margin by category, use metric
"aggregate_profit_margin", dimension "category", and operation "comparison".
Do not replace average margin with aggregate margin or vice versa.

Use null for fields that cannot be determined from the request.
""".strip()


def build_evidence_state_update_prompt(investigation_state, evidence_context: str) -> str:
    """Reassess saved hypotheses against one completed analysis cycle."""
    hypotheses = [item.model_dump() for item in investigation_state.hypotheses]
    return f"""
INVESTIGATION:
Problem: {investigation_state.problem[:500]}
Focus: {investigation_state.current_focus[:300]}
Hypotheses: {json.dumps(hypotheses, ensure_ascii=False)[:3000]}

NEW EVIDENCE FROM THE MOST RECENT ANALYSIS CYCLE
(authoritative for this update; do not add facts):
{(evidence_context or '')[-5000:]}

Return a concise StateUpdate. For each existing hypothesis, reassess whether
this specific result supports, weakens, rejects, or leaves it inconclusive.
Update its basis with the measured result and identify the limitation; change
priority only when this evidence changes which test matters most. Preserve
status for hypotheses this analysis did not test. Do not claim causation from
descriptive or correlational results. Do not invent causes or numbers. Add a
new hypothesis only if this result exposes a distinct, testable explanation
that is not already represented; do not restate the measured pattern as a
hypothesis. Use empty arrays when nothing changes. Keep current_focus under
160 characters and history_entry under 180 characters. Never copy the evidence
table into history_entry.
""".strip()


def build_hypothesis_generation_prompt(state_json: str, results_context: str, question: str) -> str:
    """Generate only distinct, evidence-testable hypotheses for a diagnosis."""
    return f"""
CURRENT INVESTIGATION STATE:
{state_json}

VERIFIED PYTHON RESULTS:
{results_context}

DIAGNOSTIC QUESTION:
{question}

Create up to three distinct, testable hypotheses that could explain the
observed outcome. Use only variables present in the verified results or
registered analysis capabilities. Do not present hypotheses as findings.
Do not create hypotheses that merely restate the observed outcome.

For each hypothesis:
- State a plausible mechanism and why the available evidence makes it worth testing.
- Name the specific calculation that would support or weaken it.
- Set priority to high, medium, or low based on business relevance and testability,
  not on an invented probability.
- Keep status active until that test has actually run.

Use at most three hypotheses. Leave the list empty if the evidence does not
justify a specific explanation. Do not add facts or update existing statuses.
Set history_entry to one short sentence describing the hypotheses added.
""".strip()


def build_scope_check_prompt(problem: str, branch_context: str, user_message: str) -> str:
    return f"""
Determine whether the user's request is related to a business problem,
business situation, business analysis, or business decision-making.

CURRENT INVESTIGATION:
{problem}

PRIOR CONVERSATION CONTEXT (may be empty):
{branch_context}

LATEST USER MESSAGE:
{user_message}

Classify the request as business-related if it describes, asks about, or
contributes information to a business-related situation.

IMPORTANT CONTEXT RULES:
- If an investigation is active, interpret the latest message in that context.
- Short follow-ups that provide relevant business information are in scope.
- Do not classify a message as unrelated merely because it lacks a question or
  an explicit business problem.
- Classify as NOT business-related when the primary request is genuinely
  unrelated to business investigation or changes the subject to general use.

User request:
{user_message}
""".strip()


def build_problem_clarity_prompt(user_message: str) -> str:
    return f"""
Extract information needed to determine whether the user's business problem
can begin an investigation.

Return problem, metric, time_period, and clarification_needed.
The problem must reflect only what the user described. Extract a metric the
user asks to analyze even if they do not describe a change. If no metric is
explicitly identified, use null. If no time period is supplied, use null.
Ask one focused clarification only when an important ambiguity prevents a
useful investigation; otherwise use an empty string.

Rules:
- Do not invent or assume a metric or missing business facts.
- "Business is down" is not a specific metric; metric must be null.
- Specific examples include revenue, sales volume, profit, customer count,
  orders, churn, retention, or average order value.
- Do not require information unnecessary to identify the problem.
- Do not require absolute values when the user already provided a meaningful
  change in a specific metric.
- Do not generate hypotheses in this step.

User request:
{user_message}
""".strip()


def build_new_information_state_prompt(state_json: str, user_message: str) -> str:
    return f"""
CURRENT INVESTIGATION STATE:
{state_json}

NEW USER INFORMATION:
{user_message}

Analyze the new information in relation to the existing investigation.

FACT RULES:
- Add only facts explicitly stated by the user.
- Do not convert assumptions, opinions, or suggested causes into confirmed
  facts. Do not duplicate facts already present.
- Do not infer numerical values, historical patterns, or circumstances.

HYPOTHESIS RULES:
- If the user asks why an observed result occurred and no relevant active
  hypotheses exist, propose up to three distinct, testable hypotheses tied to
  measurable dataset fields.
- Do not create hypotheses for descriptive requests or restate differences.
- Keep each basis concise and evidence-linked. Suggested causes and timing
  overlap are not confirmed evidence.
- Change status only when new facts or completed analysis directly test it;
  otherwise preserve status.
- Use superseded only when evidence makes a hypothesis irrelevant or a better
  supported, more precise explanation replaces it.
- Set priority by business relevance and testability, not probability.

EVIDENCE RULES:
- Request evidence only for an unresolved investigation question.
- Do not request evidence already available.
- Prioritize evidence that distinguishes competing hypotheses.
- Do not request evidence merely to appear comprehensive.

OUTPUT RULES:
- Return only changes justified by the new user information.
- Keep current_focus on the most important unresolved question.
- If no meaningful change is justified, preserve statuses and facts.
- Do not invent business facts. Keep history_entry to one factual sentence
  under 200 characters; do not repeat conclusions or narrate model actions.
""".strip()


def build_followup_evidence_decision_prompt(question, state_json, hypotheses_json, prior_analyses_json, evidence):
    return f"""ORIGINAL BUSINESS QUESTION:
{question}

CURRENT INVESTIGATION STATE:
{state_json}

UNRESOLVED HYPOTHESES:
{hypotheses_json}

ANALYSES ALREADY EXECUTED:
{prior_analyses_json}

EXISTING ANALYTICAL EVIDENCE:
{evidence or 'No analytical evidence stored yet.'}

Decide whether one more distinct calculation from the existing dataset would
materially test an active hypothesis or answer the original question. Request
one concrete calculation only if it can resolve material uncertainty. Do not
repeat a matching metric at the same granularity or request unavailable fields.
Do not request external data or another upload. Do not treat correlation or
temporal overlap as causation. Do not invent numerical facts.
""".strip()


def build_initial_diagnosis_prompt(user_message, branch_context, dataset_fields):
    return f"""USER'S REQUEST:
{user_message}

PRIOR CONVERSATION CONTEXT:
{branch_context}
Use earlier context only to resolve references. Do not treat prior assistant
interpretations as confirmed facts.

AVAILABLE DATASET FIELDS:
{dataset_fields or 'No dataset fields are available.'}

No analysis has run for this new investigation. User descriptions are reported
impressions, not measured findings. Create an accurate BusinessDiagnosis.
Include only user-stated facts. For descriptive tasks do not invent causal
hypotheses. For diagnostic tasks give up to three distinct, testable hypotheses
only when evidence supports plausible mechanisms. Prefer tests using available
fields; state when required evidence is unavailable. Rank high/medium/low by
relevance and testability, never probability. Do not present hypotheses as
findings. State what is known and what the requested analysis must establish.
""".strip()


def build_evidence_decision_prompt(state_json, evidence, user_message, fields, capabilities, previous_assistant=""):
    return f"""CURRENT INVESTIGATION STATE:
{state_json}

EXISTING ANALYTICAL EVIDENCE:
{evidence or 'No analytical evidence stored yet.'}

NEW USER REQUEST:
{user_message}

MOST RECENT ASSISTANT RECOMMENDATION (resolve references such as "run that analysis"):
{previous_assistant or 'No prior assistant recommendation.'}

Canonical dataset fields: {fields or 'No mapped fields are available.'}

REGISTERED ANALYTICS CAPABILITIES:
{capabilities}

Decide whether the request needs new evidence from this dataset. Match the
requested metric, grouping, and calculation to a registered capability and
available fields. A diagnostic word such as "why" alone does not require a
calculation. Reuse matching saved evidence at the requested granularity.
If evidence is needed, give one concise calculation request. Do not ask for an
upload, invent facts or periods, calculate values, or request unsupported work.
""".strip()
