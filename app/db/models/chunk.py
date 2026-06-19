import uuid

import uuid6
from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core import settings
from app.db.client import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid6.uuid7,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list] = mapped_column(Vector(settings.EMBEDDING_DIM), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # "metadata" is reserved by SQLAlchemy's DeclarativeBase — column name remapped via positional arg
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    __table_args__ = (
        Index("ix_chunks_document_id", "document_id"),
        # HNSW vector index is created via raw DDL in the Alembic migration
    )
