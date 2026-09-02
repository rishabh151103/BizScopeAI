from pydantic import BaseModel,Field
from typing import List


class Hypothesis(BaseModel):

    statement:str=Field(min_length=10,max_length=100)
    reasoning:str=Field(min_length=10,max_length=100)
    confidence: float=Field(ge=0, le=1)
    evidence_needed: List[str]
    

class BusinessDiagnosis(BaseModel):
    problem_summary:str
    hypotheses: List[Hypothesis]
    conclusion: str=Field(min_length=10)



