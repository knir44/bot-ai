from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_es, require_session
from app.config import get_settings
from app.core.security import ValidationError
from app.services import ingestion
from app.services.embeddings import EmbeddingError

router = APIRouter(prefix="/documents", tags=["documents"], dependencies=[Depends(require_session)])


@router.post("/upload", status_code=201)
def upload(file: UploadFile = File(...)) -> dict:
    """Upload PDF/TXT/DOCX -> parse -> chunk -> embed -> index into Elasticsearch.

    A plain `def` (not `async def`): ingestion makes slow blocking calls (Gemini, Elasticsearch),
    and FastAPI runs sync endpoints in a thread pool so they cannot freeze the event loop.
    """
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)  # read one byte past the limit so oversize files are detectable
    try:
        return ingestion.ingest_bytes(file.filename or "", data, get_es())
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except EmbeddingError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("")
def list_documents() -> dict:
    return {"documents": get_es().list_documents()}


@router.delete("/{doc_id}")
def delete_document(doc_id: str) -> dict:
    return {"deleted_chunks": get_es().delete_document(doc_id)}
