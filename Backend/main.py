import requests
from fastapi import FastAPI
from pydantic import BaseModel

from schemas import (
    BusinessDiagnosis,
    InvestigationState,
    StateUpdate,
    ScopeCheck,
    ProblemClarity
)

app=FastAPI()

class ChatRequest(BaseModel):
    message:str

@app.post("/chat")
def chat(request: ChatRequest):
    response = process_message(request.message)

    return {
        "response": response
    }
     


url = "http://localhost:11434/api/chat"


diagnosis_schema = BusinessDiagnosis.model_json_schema()
state_update_schema = StateUpdate.model_json_schema()
scope_check_schema = ScopeCheck.model_json_schema()
problem_clarity_schema = ProblemClarity.model_json_schema()


def call_ollama(data):
    response = requests.post(url, json=data)
    response.raise_for_status()

    return response.json()


messages = [
    {
        "role": "system",
        "content": """
You are BizScopeAI, an AI-powered business investigation and decision-support assistant.

ROLE

Your purpose is to help users understand, investigate, and analyze business-related problems.

You are not a generic chatbot. Your role is to investigate business situations, identify relevant signals, reduce uncertainty, and help users make better-informed business decisions.

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

11. When generating a hypothesis, the reasoning must explain why the
    available facts make that hypothesis plausible. Do not simply
    repeat or rephrase the hypothesis as its reasoning.

12. Do not generate hypotheses based on assumed historical patterns,
    market conditions, customer behavior, or business circumstances
    unless they are provided by the user or established by evidence.

13. When new information is provided, reassess the existing
    hypotheses based on that evidence.

14. Update hypothesis status and reasoning according to how the new
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

21. Clearly communicate uncertainty when the available evidence is
    insufficient.

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
"""
        
    }
]

# ============================================================
# Investigation State
# ============================================================

investigation_state = InvestigationState(
    problem="",
    business_context="",
    confirmed_facts=[],
    hypotheses=[],
    evidence_needed=[],
    current_focus="",
    investigation_history=[]
)

investigation_started = False

# ============================================================
# State Update
# ============================================================

def apply_state_update(state, update):
    for fact in update.new_facts:
        if fact not in state.confirmed_facts:
            state.confirmed_facts.append(fact)

    for hypotheses_update in update.hypotheses_updates:
        for hypotheses in state.hypotheses:
            if hypotheses.id == hypotheses_update.hypotheses_id:
                hypotheses.status = hypotheses_update.status
                hypotheses.basis = hypotheses_update.basis

    for evidence in update.new_evidence_needed:
        if evidence not in state.evidence_needed:
            state.evidence_needed.append(evidence)

    state.current_focus = update.current_focus
    state.investigation_history.append(update.history_entry)

def process_message(user_input):

    global investigation_started

    scope_messages = [
        messages[0],
        {
            "role": "user",
            "content": f"""
Determine whether the user's request is related to a business
problem, business situation, business analysis, or business
decision-making.

Classify the request as business-related if the user is describing,
asking about, or seeking help with any business-related situation,
even if the request is short, vague, informal, or lacks enough
information for a full investigation.

A request does NOT need to contain enough information to diagnose
the problem. Information sufficiency is handled later by the
investigation system.

Examples of business-related requests:

- "My sales are down."
- "My business is down by 20%."
- "Customers aren't coming back."
- "Why is my revenue declining?"
- "Should I increase my prices?"
- "Our churn has increased."
- "We're losing customers."

Classify as NOT business-related when the primary request is
general-purpose or unrelated to business.

Do not classify something as business-related merely because it
mentions a company, business, product, or commercial context.

Technical implementation, programming, coding, web development,
general knowledge, entertainment, and other general-purpose
requests should be classified as false unless the primary task
is itself a business problem, analysis, or decision.

User request:

{user_input}
"""
        }
    ]

    data = {
        "model": "llama3.2",
        "messages": scope_messages,
        "format": scope_check_schema,
        "stream": False
    }

    result = call_ollama(data)

    assistant_response = result["message"]["content"]

    scope_check = ScopeCheck.model_validate_json(assistant_response)

    if not scope_check.is_business_related:
        return (
            "Sorry, I'm designed for business-related "
            "queries and decision support rather than general-purpose "
            "questions. If you have a business problem you'd like to "
            "investigate, feel free to ask me."
        )

    clarity_messages = [
        {
            "role": "system",
            "content": f"""
Extract the information needed to determine whether the user's
business problem can begin an investigation.

Return:

- problem: the business problem explicitly described by the user.
- metric: the specific business metric or measurable outcome explicitly
identified by the user. If no specific metric is identified, return null.
- time_period: the time period explicitly identified by the user.
If none is provided, return null.
- clarification_needed: one focused question only if an important
piece of information is missing or ambiguous. Otherwise return an
empty string.

Important rules:

1. Do not invent or assume a metric.

2. "Business is down", "business is suffering", or similar wording is
NOT a specific metric. In these cases, metric must be null.

3. Examples of specific metrics include revenue, sales volume, profit,
customer count, orders, churn rate, retention rate, or average
order value.

4. Do not require information that is not necessary to identify the
business problem.

5. Do not require absolute values when the user has already provided
a meaningful change in a specific metric.

6. For example:
"Our monthly revenue declined by 20% over the last three months."
has metric = "monthly revenue" and time_period =
"last three months".

7. For example:
"My business is down by 20%."
has no specific metric, so metric must be null.

8. Do not generate hypotheses.

9. Do not invent missing business facts.

User request:

{user_input}
"""
        }
    ]

    data = {
        "model": "llama3.2",
        "messages": clarity_messages,
        "format": problem_clarity_schema,
        "stream": False
    }

    result = call_ollama(data)

    clarity_data = result["message"]["content"]

    clarity = ProblemClarity.model_validate_json(clarity_data)

    if not clarity.metric:
        return clarity.clarification_needed

    

    messages.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    if not investigation_started:

        data = {
            "model": "llama3.2",
            "messages": messages,
            "format": diagnosis_schema,
            "stream": False
        }

        result = call_ollama(data)

        assistant_response = result["message"]["content"]

        diagnosis = BusinessDiagnosis.model_validate_json(assistant_response)

        investigation_state.problem = diagnosis.problem_summary
        investigation_state.confirmed_facts = diagnosis.confirmed_facts
        investigation_state.hypotheses = diagnosis.hypotheses

        investigation_state.evidence_needed = [
            evidence
            for hypotheses in diagnosis.hypotheses
            for evidence in hypotheses.evidence_needed
        ]

        investigation_state.current_focus = diagnosis.conclusion

        investigation_started = True

        response = f"\n{diagnosis.problem_summary}\n\n"

        for hypotheses in diagnosis.hypotheses:
            response += f"Hypothesis: {hypotheses.statement}\n"
            response += f"Basis: {hypotheses.basis}\n"
            response += (
                f"Evidence Needed: "
                f"{', '.join(hypotheses.evidence_needed)}\n\n"
            )

        response += f"Conclusion: {diagnosis.conclusion}\n"

        return response

    else:

        state_context = f"""
CURRENT INVESTIGATION STATE:

{investigation_state.model_dump_json(indent=2)}

NEW USER INFORMATION:

{user_input}

Analyze the new information in relation to the existing investigation.

Return a StateUpdate describing what has changed.
"""

        state_messages = [
            messages[0],
            {
                "role": "user",
                "content": state_context
            }
        ]

        data = {
            "model": "llama3.2",
            "messages": state_messages,
            "format": state_update_schema,
            "stream": False
        }

        result = call_ollama(data)

        assistant_response = result["message"]["content"]

        state_update = StateUpdate.model_validate_json(assistant_response)

        apply_state_update(investigation_state, state_update)

        response_context = f"""
CURRENT INVESTIGATION STATE:

{investigation_state.model_dump_json(indent=2)}

LATEST USER INFORMATION:

{user_input}

Respond naturally to the user as BizScopeAI.

Explain what the new information means for the investigation,
which hypotheses became stronger or weaker, and what should
be investigated next if more evidence is needed.

Do not expose the internal investigation state, StateUpdate,
Pydantic models, or implementation details.
"""

        response_messages = [
            messages[0],
            {
                "role": "user",
                "content": response_context
            }
        ]

        data = {
            "model": "llama3.2",
            "messages": response_messages,
            "stream": False
        }

        result = call_ollama(data)

        assistant_response = result["message"]["content"]

        messages.append(
            {
                "role": "assistant",
                "content": assistant_response
            }
        )

        return assistant_response

    
        

if __name__ == "__main__":



    print("Welcome to BizScopeAI!")
    print("type 'exit' to quit the program.")


    while True:

        user_input = input("You: ")

        if user_input.lower() == "exit":
            print("\nBizScopeAI: Thank you for using BizScopeAI. Goodbye!")
            break

        response = process_message(user_input)

        print(f"\nBizScopeAI: {response}\n")

        

        
        

        