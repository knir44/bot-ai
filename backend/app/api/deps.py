"""Shared FastAPI dependencies: singletons and session authentication."""
from __future__ import annotations

from functools import lru_cache

from fastapi import Header, HTTPException

from app.config import get_settings
from app.core.security import verify_session
from app.repositories.es_repo import EsRepository
from app.repositories.pg_repo import PgRepository
from app.services.rag import RagService


@lru_cache
def get_es() -> EsRepository:
    return EsRepository()


@lru_cache
def get_pg() -> PgRepository:
    return PgRepository()


def get_rag() -> RagService:
    return RagService(get_es(), get_pg())


def require_session(
    x_session_id: str = Header(default=""),
    x_session_token: str = Header(default=""),
) -> str:
    """Every protected endpoint needs both headers; the token must be the HMAC of the id."""
    if not verify_session(x_session_id, x_session_token, get_settings().session_secret):
        raise HTTPException(status_code=401, detail="הסשן חסר או לא תקין. יוצרים סשן חדש עם POST /api/v1/chat/session.")
    return x_session_id
