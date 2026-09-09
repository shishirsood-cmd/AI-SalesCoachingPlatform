import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.knowledge import DocChunk
from app.services.embeddings import embed_texts


async def retrieve_relevant_chunks(
    db: AsyncSession, org_id: uuid.UUID, query: str, top_k: int | None = None
) -> list[str]:
    if not query.strip():
        return []
    [query_vector] = embed_texts([query])
    k = top_k or settings.rag_top_k
    rows = (
        await db.execute(
            select(DocChunk.content)
            .where(DocChunk.org_id == org_id)
            .order_by(DocChunk.embedding.cosine_distance(query_vector))
            .limit(k)
        )
    ).all()
    return [row[0] for row in rows]
