import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class AIQualityEvalType(str, enum.Enum):
    transcript_analysis = "transcript_analysis"
    roleplay_simulation = "roleplay_simulation"
    coaching_safety = "coaching_safety"


class AIQualityEval(Base):
    __tablename__ = "ai_quality_evals"
    __table_args__ = (UniqueConstraint("session_id", "eval_type", name="uq_ai_quality_eval_session_type"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    eval_type: Mapped[AIQualityEvalType] = mapped_column(
        Enum(AIQualityEvalType, name="ai_quality_eval_type"), nullable=False
    )
    # Shape varies by eval_type — see app/services/ai_quality_evals.py for what each type stores.
    scores: Mapped[dict] = mapped_column(JSON, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
