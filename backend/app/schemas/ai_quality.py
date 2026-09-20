import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.ai_quality import AIQualityEvalType


class AIQualityEvalOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    eval_type: AIQualityEvalType
    scores: dict[str, Any]
    summary: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AIQualityEvalsOut(BaseModel):
    transcript_analysis: AIQualityEvalOut | None = None
