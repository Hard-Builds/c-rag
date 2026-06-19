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

    async def ainvoke(self):
        # Loading data
        docs = await self._load_documents()

        # Chunking data
        chunks = await self._split_documents(docs)

        # Embedding and store data
        await self._embed_and_store(chunks)

    @abstractmethod
    async def _load_documents(self) -> list[Document]:
        pass

    async def _split_documents(self, docs: list[Document]) -> list[Document]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        chunks = splitter.split_documents(documents=docs)
        return chunks

    async def _embed_and_store(self, chunks: list[Document]):
        embeddings = []

        batch_size = self.embedding_batch_size

        for idx in range(0, len(chunks), batch_size):
            batch = chunks[idx: idx + batch_size]
            text = list(map(lambda x: x.page_content, batch))
            batch_embeddings = await self._embedder.aembed_documents(text)
            embeddings.extend(batch_embeddings)

        # Updating DB with the records
        document = await self.doc_service.create({
            "user_id": self.user_id,
            "filename": self.filename,
            "file_path": self.file_path
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

        await self.chunk_service.create_many(chunk_data, commit=False)
