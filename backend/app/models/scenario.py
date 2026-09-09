import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class Difficulty(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class CallType(str, enum.Enum):
    cold_call = "cold_call"
    support = "support"


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    persona_description: Mapped[str] = mapped_column(Text, nullable=False)
    objections: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty, name="difficulty"), nullable=False)
    call_type: Mapped[CallType] = mapped_column(Enum(CallType, name="call_type"), nullable=False)
    # List of {"name": str, "description": str, "weight": float}; weights expressed as
    # percentages that should sum to 100 (enforced at the API layer, not the DB).
    rubric_criteria: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
