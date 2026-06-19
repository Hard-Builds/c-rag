import uuid

import uuid6
from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.client import Base
from app.db.models.defaults import PostgresDefaults


class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid6.uuid7,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=PostgresDefaults.UTC_NOW(),
    )
    updated_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=PostgresDefaults.UTC_NOW(),
        onupdate=PostgresDefaults.UTC_NOW(),
    )

    __table_args__ = (Index("ix_threads_user_id", "user_id"),)
