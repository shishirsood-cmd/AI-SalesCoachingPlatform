import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.config import settings
from app.db.session import get_db
from app.models.knowledge import DocChunk, DocStatus, KnowledgeDoc
from app.models.user import User, UserRole
from app.schemas.knowledge import KnowledgeDocOut
from app.services.ingestion import ingest_document
from app.services.storage import delete_file, save_upload

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

ALLOWED_EXTENSIONS = {".pdf", ".txt"}


@router.get("", response_model=list[KnowledgeDocOut])
async def list_docs(
    user: User = Depends(require_role(UserRole.team_lead)),
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeDocOut]:
    docs = (
        await db.scalars(
            select(KnowledgeDoc)
            .where(KnowledgeDoc.org_id == user.org_id)
            .order_by(KnowledgeDoc.created_at.desc())
        )
    ).all()
    counts = dict(
        (
            await db.execute(
                select(DocChunk.doc_id, func.count(DocChunk.id))
                .where(DocChunk.org_id == user.org_id)
                .group_by(DocChunk.doc_id)
            )
        ).all()
    )
    return [
        KnowledgeDocOut.model_validate(doc, from_attributes=True).model_copy(
            update={"chunk_count": counts.get(doc.id, 0)}
        )
        for doc in docs
    ]


@router.post("/upload", response_model=KnowledgeDocOut, status_code=status.HTTP_201_CREATED)
async def upload_doc(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    user: User = Depends(require_role(UserRole.team_lead)),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeDoc:
    filename = file.filename or "upload"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")

    doc = KnowledgeDoc(
        org_id=user.org_id,
        uploaded_by=user.id,
        filename=filename,
        storage_path="",
        status=DocStatus.processing,
    )
    db.add(doc)
    await db.flush()

    doc.storage_path = save_upload(user.org_id, doc.id, filename, content)
    await db.commit()
    await db.refresh(doc)

    background_tasks.add_task(ingest_document, doc.id)

    return doc


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doc(
    doc_id: uuid.UUID,
    user: User = Depends(require_role(UserRole.team_lead)),
    db: AsyncSession = Depends(get_db),
) -> None:
    doc = await db.get(KnowledgeDoc, doc_id)
    if doc is None or doc.org_id != user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    delete_file(doc.storage_path)
    await db.delete(doc)
    await db.commit()
