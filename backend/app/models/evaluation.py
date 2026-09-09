import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    # List of {"name": str, "score": float (0-100), "feedback": str}
    criteria_scores: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    strengths: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    areas_for_improvement: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
