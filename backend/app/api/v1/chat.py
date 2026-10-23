from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import get_pg, get_rag, require_session
from app.config import get_settings
from app.core.security import ValidationError, new_session_id, sanitize_text, sign_session
from app.services.embeddings import EmbeddingError
from app.services.llm import LLMError

router = APIRouter(prefix="/chat", tags=["chat"])


class MessageIn(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=5000)  # hard cap; sanitize_text applies the configured one


def _new_session() -> dict:
    sid = new_session_id()
    get_pg().create_session(sid)
    return {"session_id": sid, "token": sign_session(sid, get_settings().session_secret)}


@router.post("/session", status_code=201)
def create_session() -> dict:
    """Mint a session. The client stores `session_id` + `token` and sends them as X-Session-Id / X-Session-Token."""
    return _new_session()


@router.post("/message")
def send_message(body: MessageIn, session_id: str = Depends(require_session)) -> dict:
    if body.session_id != session_id:
        raise HTTPException(status_code=400, detail="session_id in body does not match X-Session-Id header.")
    status = get_pg().session_status(session_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Session not found. Create a new one.")
    if status == "archived":
        raise HTTPException(status_code=409, detail="This session was archived by a reset. Create a new one.")
    try:
        question = sanitize_text(body.message, get_settings().max_message_chars)
        return get_rag().answer(session_id, question)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except (EmbeddingError, LLMError) as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/history")
def history(session_id: str = Query(...), header_session: str = Depends(require_session)) -> dict:
    if session_id != header_session:
        raise HTTPException(status_code=403, detail="You can only read your own session.")
    if get_pg().session_status(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found. Create a new one.")
    return {"session_id": session_id, "messages": get_pg().get_messages(session_id)}


@router.post("/reset")
def reset(session_id: str = Depends(require_session)) -> dict:
    """Archive the current conversation (kept in Postgres) and return a brand-new session."""
    get_pg().archive_session(session_id)
    return {"archived_session_id": session_id, **_new_session()}
