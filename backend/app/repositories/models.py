"""SQLAlchemy models. They mirror db/init.sql (init.sql runs first in Docker; create_all is a safety net for local runs)."""
from __future__ import annotations

import datetime as dt
import uuid
from typing import Optional

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text, func
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

    messages: Mapped[list["Message"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("idx_messages_session_created", "session_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[Optional[list]] = mapped_column(JsonType, nullable=True)
    trace: Mapped[Optional[dict]] = mapped_column(JsonType, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[ChatSession] = relationship(back_populates="messages")
