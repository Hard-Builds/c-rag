from abc import ABC, abstractmethod

from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core import settings
from app.db.services import DocumentService, ChunkService


class BaseIngestor(ABC):
    _embedding_model = None

    def __init__(self, db, user_id, filename, file_path, chunk_size=1000,
                 chunk_overlap=100):
        self.user_id = user_id
        self.filename = filename
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_batch_size = 50
        self.doc_service = DocumentService(db)
        self.chunk_service = ChunkService(db)

    @property
    def _embedder(self):
        if not getattr(self, "_embedding_model", None):
            self._embedding_model = GoogleGenerativeAIEmbeddings(
                model=settings.GEMINI_EMBEDDING_MODEL,
                output_dimensionality=settings.EMBEDDING_DIM
            )
        return self._embedding_model

    @abstractmethod
    async def _load_documents(self) -> None:
        pass

    async def ainvoke(self):
        # Loading data
        docs = await self._load_documents()

        # Chunking data
        chunks = await self._chunk_docs(docs)

        # Embedding data
        embeddings = await self._embed_docs(chunks)

        # Storing data
        await self._store_chunks(chunks, embeddings)

    @abstractmethod
    async def _load_documents(self) -> list[Document]:
        pass

    async def _chunk_docs(self, docs: list[Document]) -> list[Document]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        chunks = splitter.split_documents(documents=docs)
        return chunks

    async def _embed_docs(self, chunks: list[Document]):
        embeddings = []

        batch_size = self.embedding_batch_size

        for idx in range(0, len(chunks), batch_size):
            batch = chunks[idx: idx + batch_size]
            text = list(map(lambda x: x.page_content, batch))
            batch_embeddings = await self._embedder.aembed_documents(text)
            embeddings.extend(batch_embeddings)

        return embeddings

    async def _store_chunks(self, chunks, embeddings) -> None:
        document = await self.doc_service.create({
            "user_id": self.user_id,
            "filename": self.filename
        })

        chunk_data = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_data.append({
                "document_id": document.id,
                "content": chunk.page_content,
                "embedding": embedding,
                "chunk_index": idx,
                "metadata_": chunk.metadata,
            })

        await self.chunk_service.create_many(chunk_data)
