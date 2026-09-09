import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.knowledge import DocStatus


class KnowledgeDocOut(BaseModel):
    id: uuid.UUID
    filename: str
    status: DocStatus
    error_message: str | None
    created_at: datetime
    chunk_count: int = 0

    model_config = {"from_attributes": True}
