import uuid
from datetime import datetime

from pydantic import BaseModel


class ProgressEntry(BaseModel):
    session_id: uuid.UUID
    scenario_title: str
    completed_at: datetime
    overall_score: float


class MyProgressOut(BaseModel):
    entries: list[ProgressEntry]
    average_score: float | None


class RepStat(BaseModel):
    rep_id: uuid.UUID
    rep_name: str
    sessions_completed: int
    average_score: float


class ScenarioStat(BaseModel):
    scenario_id: uuid.UUID
    title: str
    attempts: int
    average_score: float


class CriterionStat(BaseModel):
    name: str
    average_score: float
    sample_count: int


class TeamAnalyticsOut(BaseModel):
    total_evaluated_sessions: int
    average_score: float | None
    by_rep: list[RepStat]
    by_scenario: list[ScenarioStat]
    by_criterion: list[CriterionStat]
