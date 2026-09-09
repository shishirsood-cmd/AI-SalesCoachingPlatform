import uuid
from pathlib import Path

from app.core.config import settings


def _org_dir(org_id: uuid.UUID) -> Path:
    path = Path(settings.storage_root) / str(org_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(org_id: uuid.UUID, doc_id: uuid.UUID, filename: str, content: bytes) -> str:
    """Persist an uploaded file to local disk and return its storage path.

    This is intentionally a thin, swappable interface — moving to S3-compatible
    object storage later only requires changing this module, not its callers.
    """
    safe_name = Path(filename).name
    destination = _org_dir(org_id) / f"{doc_id}_{safe_name}"
    destination.write_bytes(content)
    return str(destination)


def delete_file(storage_path: str) -> None:
    path = Path(storage_path)
    if path.exists():
        path.unlink()
