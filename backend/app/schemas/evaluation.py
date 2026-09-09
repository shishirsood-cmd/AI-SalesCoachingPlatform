import uuid
from datetime import datetime

from pydantic import BaseModel


class CriterionScore(BaseModel):
    name: str
    score: float
    feedback: str


class EvaluationOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    overall_score: float
    criteria_scores: list[CriterionScore]
    strengths: list[str]
    areas_for_improvement: list[str]
    summary: str
    created_at: datetime

    model_config = {"from_attributes": True}
