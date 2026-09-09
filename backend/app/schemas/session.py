import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.session import SessionStatus, Speaker


class SessionCreate(BaseModel):
    scenario_id: uuid.UUID


class TurnOut(BaseModel):
    id: uuid.UUID
    turn_index: int
    speaker: Speaker
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    id: uuid.UUID
    scenario_id: uuid.UUID
    rep_id: uuid.UUID
    status: SessionStatus
    started_at: datetime
    ended_at: datetime | None
    turns: list[TurnOut] = Field(default_factory=list)
    # Base64-encoded audio (mp3) for the most recently generated AI turn, when
    # voice mode produced one. Best-effort: null if TTS wasn't requested or failed.
    audio_base64: str | None = None

    model_config = {"from_attributes": True}


class MessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
