import uuid
from uuid import UUID

from sqlalchemy import select

from app.db.models import Document
from app.db.models.chunk import Chunk
from app.db.services.base import BaseDB


class ChunkService(BaseDB[Chunk]):
    def __init__(self, db):
        super().__init__(db, Chunk)

    async def get_chunks_for_document(self, document_id: uuid.UUID):
        return await self.get_all_by_filter(document_id=document_id)

    async def similarity_search(self, user_id: UUID, embedding: list[float],
                                limit: int = 5) -> list[Chunk]:
        # cosine_distance works best for normalized embeddings (most semantic models)
        # swap to .l2_distance() if your model outputs unnormalized vectors
        stmt = (
            select(Chunk)
            .join(Document, Chunk.document_id == Document.id)
            .filter(Document.user_id == user_id)
            .order_by(Chunk.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
