import asyncio
import uuid
from pathlib import Path

from pypdf import PdfReader

from app.db.session import AsyncSessionLocal
from app.models.knowledge import DocChunk, DocStatus, KnowledgeDoc
from app.services.embeddings import embed_texts

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def extract_text(path: str) -> str:
    file_path = Path(path)
    if file_path.suffix.lower() == ".pdf":
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return file_path.read_text(errors="ignore")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    chunks = []
    start = 0
    while start < len(normalized):
        end = start + chunk_size
        chunks.append(normalized[start:end])
        start = end - overlap
    return chunks


def _extract_chunk_embed(storage_path: str) -> tuple[list[str], list[list[float]]]:
    text = extract_text(storage_path)
    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("No extractable text found in this file")
    vectors = embed_texts(chunks)
    return chunks, vectors


async def ingest_document(doc_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        doc = await db.get(KnowledgeDoc, doc_id)
        if doc is None:
            return
        try:
            chunks, vectors = await asyncio.to_thread(_extract_chunk_embed, doc.storage_path)
            for index, (content, vector) in enumerate(zip(chunks, vectors)):
                db.add(
                    DocChunk(
                        doc_id=doc.id,
                        org_id=doc.org_id,
                        chunk_index=index,
                        content=content,
                        embedding=vector,
                    )
                )
            doc.status = DocStatus.ready
        except Exception as exc:  # noqa: BLE001 — surfaced to the admin as error_message
            doc.status = DocStatus.failed
            doc.error_message = str(exc)[:500]
        await db.commit()
