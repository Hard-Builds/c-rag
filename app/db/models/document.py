import uuid

import uuid6
from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.constants import DocumentStatusEnum
from app.db.client import Base
from app.db.models.defaults import PostgresDefaults


class Document(Base):
    __tablename__ = "documents"

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
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False,
        default=DocumentStatusEnum.PROCESSING
    )
    error: Mapped[str] = mapped_column(
        String,
        nullable=True
    )
    uploaded_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=PostgresDefaults.UTC_NOW(),
    )
    updated_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=PostgresDefaults.UTC_NOW(),
        onupdate=PostgresDefaults.UTC_NOW(),
    )

    __table_args__ = (Index("ix_documents_user_id", "user_id"),)