"""Postgres repository: conversations (sessions + question/answer turns)."""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from typing import Iterator, List, Optional

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.repositories.models import Base, ChatSession, ChatTurn

_engine = None
_SessionLocal: Optional[sessionmaker] = None


def init_db() -> None:
    global _engine, _SessionLocal
    _engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    Base.metadata.create_all(_engine)


@contextmanager
def db_session() -> Iterator[Session]:
    assert _SessionLocal is not None, "init_db() was not called"
    s = _SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def ping() -> bool:
    try:
        with db_session() as s:
            s.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def turns_to_messages(turns: List[dict]) -> List[dict]:
    """Expand stored turns (one row = question + answer) into the flat chat-message list the UI and the LLM prompt use."""
    out: List[dict] = []
    for t in turns:
        out.append({"id": f"{t['id']}-q", "role": "user", "content": t["question"], "sources": None, "trace": None, "created_at": t["created_at"]})
        out.append({"id": f"{t['id']}-a", "role": "assistant", "content": t["answer"], "sources": t["sources"], "trace": t["trace"], "created_at": t["created_at"]})
    return out


class PgRepository:
    def create_session(self, session_id: str) -> None:
        with db_session() as s:
            s.add(ChatSession(id=uuid.UUID(session_id)))

    def session_status(self, session_id: str) -> Optional[str]:
        """None (unknown), 'active' or 'archived'."""
        with db_session() as s:
            row = s.get(ChatSession, uuid.UUID(session_id))
            if row is None:
                return None
            return "archived" if row.archived else "active"

    def archive_session(self, session_id: str) -> None:
        with db_session() as s:
            row = s.get(ChatSession, uuid.UUID(session_id))
            if row:
                row.archived = True

    def add_turn(self, session_id: str, question: str, answer: str, sources=None, trace=None) -> None:
        with db_session() as s:
            s.add(ChatTurn(session_id=uuid.UUID(session_id), question=question, answer=answer, sources=sources, trace=trace))

    def get_turns(self, session_id: str, limit: Optional[int] = None) -> List[dict]:
        """Oldest first. With `limit`, returns the most recent `limit` turns (still oldest first)."""
        with db_session() as s:
            stmt = select(ChatTurn).where(ChatTurn.session_id == uuid.UUID(session_id)).order_by(ChatTurn.id.desc())
            if limit:
                stmt = stmt.limit(limit)
            rows = list(reversed(s.scalars(stmt).all()))
            return [
                {
                    "id": r.id,
                    "question": r.question,
                    "answer": r.answer,
                    "sources": r.sources,
                    "trace": r.trace,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]

    def get_messages(self, session_id: str) -> List[dict]:
        """The whole conversation as a flat list of user/assistant messages (what the UI renders)."""
        return turns_to_messages(self.get_turns(session_id))
