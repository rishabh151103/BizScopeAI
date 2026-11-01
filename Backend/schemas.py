from pydantic import BaseModel,Field
from typing import List,Literal,Optional


class Hypotheses(BaseModel):

    id:int
    statement:str=Field(min_length=10)
    basis:str=Field(min_length=10)
    evidence_needed: List[str]
    status:Literal[
        "active", "supported", "weakened", "rejected",
        "inconclusive", "superseded",
    ]="active"
    priority:Literal["high","medium","low"]="medium"
    

class BusinessDiagnosis(BaseModel):
    problem_summary:str
    confirmed_facts: List[str]
    hypotheses: List[Hypotheses] = Field(default_factory=list, max_length=3)
    conclusion: str=Field(min_length=10)
    



class HypothesesUpdate(BaseModel):

    hypotheses_id:int=Field(ge=1)
    status:Literal[
        "active",
        "supported",
        "weakened",
        "rejected",
        "inconclusive",
        "superseded",
        ]
    basis:str=Field(min_length=10, max_length=2000)
    priority:Optional[Literal["high","medium","low"]]=None


class StateUpdate(BaseModel):
    new_facts: List[str] = Field(default_factory=list, max_length=20)
    hypotheses_updates: List[HypothesesUpdate] = Field(default_factory=list, max_length=10)
    new_hypotheses: List[Hypotheses] = Field(default_factory=list, max_length=3)
    new_evidence_needed: List[str] = Field(default_factory=list, max_length=20)
    current_focus: str = Field(default="", max_length=500)
    history_entry: str = Field(default="Investigation state reviewed.", min_length=10, max_length=400)

class InvestigationState(BaseModel):

    problem:str
    business_context:str
    confirmed_facts:List[str]
    hypotheses:List[Hypotheses]
    evidence_needed:List[str]
    current_focus:str
    investigation_history:List[str]
    dataset_id: int | None = None


class ScopeCheck(BaseModel):

    is_business_related: bool


class ProblemClarity(BaseModel):
    problem: str
    metric: Optional[str]=None
    time_period: Optional[str]=None
    clarification_needed: str=""


class EvidenceDecision(BaseModel):
    needs_new_evidence: bool
    evidence_request: Optional[str] = None


class EvidenceRequirement(BaseModel):
    question: str
    metric: Optional[str] = None
    dimension: Optional[str] = None
    operation: Optional[str] = None
    start_month: Optional[str] = None
    end_month: Optional[str] = None



class BusinessColumnMapping(BaseModel):
    """
    Maps uploaded dataset columns to BizScopeAI business concepts.

    The values contain the actual column names from the user's dataset.
    """

    date: Optional[str] = None
    revenue: Optional[str] = None
    profit: Optional[str] = None
    cost: Optional[str] = None
    units: Optional[str] = None
    unit_price: Optional[str] = None
    marketing_spend: Optional[str] = None

    customer_id: Optional[str] = None
    order_id: Optional[str] = None

    product: Optional[str] = None
    category: Optional[str] = None
    region: Optional[str] = None
    customer_type: Optional[str] = None
    discount: Optional[str] = None

class AnalysisRequirement(BaseModel):
    requirement: str
    metric: Optional[str] = None
    dimension: Optional[str] = None
    operation: Optional[str] = None
    start_month: Optional[str] = None
    end_month: Optional[str] = None
    category_filter: Optional[str] = None

class AnalysisSelection(BaseModel):
    analysis_name: Literal[
        "revenue_trend",
        "profitability",
        "product_performance",
        "customer_performance",
        "customer_type",
        "category_performance",
        "discount_performance",
        "category_revenue_trend",
        "regional_performance",
        "monthly_performance",
        "correlations",
        "business_comparisons",
        "significant_changes",
        "segment_changes",
        "change_contribution",
        "order_metrics",
        "marketing_performance",
        "customer_retention",
        "distribution_statistics",
        "outliers",
    ]
    requirement: AnalysisRequirement



class AnalysisPlan(BaseModel):
    question_summary: str
    analyses: List[AnalysisSelection] = Field(
        min_length=1,
        max_length=5
    )    



class RequirementPlan(BaseModel):
    question_summary: str
    requirements: List[AnalysisRequirement] = Field(
        min_length=1,
        max_length=5
    )        

class ToolSelection(BaseModel):
    analysis_name: Literal[
        "revenue_trend",
        "profitability",
        "product_performance",
        "customer_performance",
        "customer_type",
        "category_performance",
        "discount_performance",
        "category_revenue_trend",
        "regional_performance",
        "monthly_performance",
        "correlations",
        "business_comparisons",
        "significant_changes",
        "segment_changes",
        "change_contribution",
        "order_metrics",
        "marketing_performance",
        "customer_retention",
        "distribution_statistics",
        "outliers",
    ]

class AnalysisResultEnvelope(BaseModel):
    """
    Common envelope for persisted analytical outputs.

    `result` remains analysis-specific; the envelope standardizes provenance
    without forcing unrelated analyses into the same result shape.
    """
    schema_version: str = "1.0"
    analysis_name: str = Field(min_length=1)
    result: dict | list | str | int | float | bool | None
    dataset_id: int | None = None
    metric: str | None = None
    dimension: str | None = None
    operation: str | None = None
    period_start: str | None = None      
