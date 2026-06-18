from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings
from app.db.services import ChunkService


class Retriever:
    _retriever = None

    @classmethod
    async def load(cls):
        chunk_data = await ChunkService().fetch_all_chunks()
        embedding_model = GoogleGenerativeAIEmbeddings(
            model=settings.GEMINI_EMBEDDING_MODEL
        )

        cls._retriever = await FAISS.afrom_embeddings(
            text_embeddings=list(map(
                lambda x: (x["text"], x["embedding"]),
                chunk_data
            )),
            embedding=embedding_model,
            metadatas=list(map(
                lambda x: {"id": x["id"], "page_number": x["page_number"]},
                chunk_data
            ))
        )

    @classmethod
    async def get(cls, query: str, top_k: int = 5) -> list[Document]:
        return await cls._retriever.asimilarity_search(query, k=top_k)
