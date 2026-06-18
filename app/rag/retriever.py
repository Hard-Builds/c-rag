from uuid import UUID

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings
from app.db.models import Chunk
from app.db.services import ChunkService


class Retriever:
    _embedding_model = None

    @classmethod
    def init(cls):
        if cls._embedding_model is None:
            cls._embedding_model = GoogleGenerativeAIEmbeddings(
                model=settings.GEMINI_EMBEDDING_MODEL,
                output_dimensionality=settings.EMBEDDING_DIM
            )
        return cls._embedding_model

    @classmethod
    async def get(cls, db, user_id: UUID, query: str, top_k: int = 5) -> \
            list[Chunk]:
        query_embedding = await cls._embedding_model.aembed_query(query)
        return await ChunkService(db).similarity_search(
            user_id=user_id,
            embedding=query_embedding,
            limit=top_k
        )
