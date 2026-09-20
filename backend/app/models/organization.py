import secrets
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


def _generate_invite_code() -> str:
    return secrets.token_urlsafe(6)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    invite_code: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=_generate_invite_code
    )
    # Optional free-text enterprise constraints checked in the Coaching Safety
    # AI Quality Eval (e.g. "no medical advice, no discriminatory language").
    compliance_guidelines: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
