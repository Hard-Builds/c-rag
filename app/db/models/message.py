import uuid

import uuid6
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.client import Base
from app.db.models.defaults import PostgresDefaults


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid6.uuid7,
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("threads.id"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String, nullable=False)  # user|assistant|system|tool
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # "metadata" is reserved by SQLAlchemy's DeclarativeBase — column name remapped via positional arg
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=PostgresDefaults.UTC_NOW(),
    )

    __table_args__ = (Index("ix_messages_thread_id", "thread_id"),)
