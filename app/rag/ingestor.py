from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.services import DocumentService, ChunkService


class pdfIngestor:
    def __init__(
            self,
            db: AsyncSession,
            user_id: int,
            filename: str,
            file_path: str,
            chunk_size: int = 1000,
            chunk_overlap: int = 100
    ):
        self.user_id = user_id
        self.doc_service = DocumentService(db)
        self.chunk_service = ChunkService(db)

        self.filename = filename
        self.file_path = file_path

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.embedding_batch_size = 50
        self.embedding_model = GoogleGenerativeAIEmbeddings(
            model=settings.GEMINI_EMBEDDING_MODEL,
            output_dimensionality=settings.EMBEDDING_DIM
        )

    async def _validate_file(self) -> None:
        if await self.doc_service.is_ingested(
                user_id=self.user_id,
                filename=self.filename
        ):
            raise Exception("Given file is already processed")

    async def ainvoke(self):
        # validating file paths
        await self._validate_file()

        # Loading data
        document, docs = await self._load_documents()

        # Chunking data
        chunks = await self._chunk_docs(docs)

        # Embedding data
        embeddings = await self._embed_docs(chunks)

        # Storing data
        await self._store_chunks(document, chunks, embeddings)

    async def _load_documents(self):
        file_path = self.file_path
        documents = await PyPDFLoader(file_path=file_path).aload()
        document = await self.doc_service.create({
            "user_id": self.user_id,
            "filename": self.filename
        })
        return document, documents

    async def _chunk_docs(self, docs: list[Document]) -> list[Document]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        chunks = splitter.split_documents(documents=docs)
        return chunks

    async def _embed_docs(self, chunks: list[Document]):
        embeddings = []

        embedder = self.embedding_model
        batch_size = self.embedding_batch_size

        for idx in range(0, len(chunks), batch_size):
            batch = chunks[idx: idx + batch_size]
            text = list(map(lambda x: x.page_content, batch))
            batch_embeddings = await embedder.aembed_documents(text)
            embeddings.extend(batch_embeddings)

        return embeddings

    async def _store_chunks(self, document, chunks, embeddings) -> None:
        chunk_data = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_data.append({
                "document_id": document.id,
                "content": chunk.page_content,
                "embedding": embedding,
                "chunk_index": idx,
                "metadata": chunk.metadata,
            })

        await self.chunk_service.create_many(chunk_data)
