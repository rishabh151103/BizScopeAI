
from pydantic import BaseModel,Field
from typing import List,Literal,Optional


class Hypotheses(BaseModel):

    id:int
    statement:str=Field(min_length=10)
    basis:str=Field(min_length=10)
    evidence_needed: List[str]
    status:Literal["active","supported","weakened","rejected","inconclusive"]="active"
    

class BusinessDiagnosis(BaseModel):
    problem_summary:str
    confirmed_facts: List[str]
    hypotheses: List[Hypotheses] = Field(min_length=1, max_length=3)
    conclusion: str=Field(min_length=10)
    



class HypothesesUpdate(BaseModel):

    hypotheses_id:int
    status:Literal["active","supported","weakened","rejected","inconclusive"]
    basis:str


class StateUpdate(BaseModel):

    new_facts:List[str]
    hypotheses_updates:List[HypothesesUpdate]
    new_evidence_needed:List[str]
    current_focus:str
    history_entry:str


class InvestigationState(BaseModel):

    problem:str
    business_context:str
    confirmed_facts:List[str]
    hypotheses:List[Hypotheses]
    evidence_needed:List[str]
    current_focus:str
    investigation_history:List[str]


class ScopeCheck(BaseModel):

    is_business_related: bool


class ProblemClarity(BaseModel):
    problem: str
    metric: Optional[str]=None
    time_period: Optional[str]=None
    clarification_needed: str=""        