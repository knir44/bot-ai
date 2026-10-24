"""SQLAlchemy models. They mirror db/init.sql (init.sql runs first in Docker; create_all is a safety net for existing volumes and local runs)."""
from __future__ import annotations

import datetime as dt
import uuid
from typing import Optional

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# JSONB on Postgres (indexable, binary); plain JSON elsewhere.
JsonType = JSON().with_variant(JSONB(), "postgresql")


class ChatSession(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    archived: Mapped[bool] = mapped_column(Boolean, default=False)

    turns: Mapped[list["ChatTurn"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ChatTurn(Base):
    """One row = one question and its answer."""

    __tablename__ = "chat_history"
    __table_args__ = (Index("idx_chat_history_session_created", "session_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    sources: Mapped[Optional[list]] = mapped_column(JsonType, nullable=True)
    trace: Mapped[Optional[dict]] = mapped_column(JsonType, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[ChatSession] = relationship(back_populates="turns")
