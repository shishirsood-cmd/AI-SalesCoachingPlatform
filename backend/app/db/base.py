from app.db.base_class import Base

# Import all models here so Alembic autogenerate can discover them.
from app.models.organization import Organization  # noqa: E402,F401
from app.models.user import User  # noqa: E402,F401
from app.models.scenario import Scenario  # noqa: E402,F401
from app.models.knowledge import KnowledgeDoc, DocChunk  # noqa: E402,F401
from app.models.session import SimulationSession, Turn  # noqa: E402,F401
from app.models.evaluation import Evaluation  # noqa: E402,F401

__all__ = ["Base"]
