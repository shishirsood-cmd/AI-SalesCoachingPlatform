import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.scenario import CallType, Difficulty


class RubricCriterion(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    weight: float = Field(gt=0, le=100)


class ScenarioBase(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    persona_description: str = Field(min_length=10)
    objections: list[str] = Field(default_factory=list)
    difficulty: Difficulty
    call_type: CallType
    rubric_criteria: list[RubricCriterion] = Field(min_length=1)

    @field_validator("rubric_criteria")
    @classmethod
    def weights_sum_to_100(cls, value: list[RubricCriterion]) -> list[RubricCriterion]:
        total = sum(c.weight for c in value)
        if abs(total - 100) > 0.01:
            raise ValueError(f"Rubric weights must sum to 100 (got {total})")
        return value


class ScenarioCreate(ScenarioBase):
    pass


class ScenarioUpdate(ScenarioBase):
    pass


class ScenarioOut(ScenarioBase):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
