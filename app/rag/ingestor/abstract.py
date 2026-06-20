import asyncio
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from starlette import status
from tenacity import retry, wait_exponential, stop_after_attempt, \
    retry_if_result

from app.constants import DocumentStatusEnum
from app.core import settings, logger
from app.db.services import DocumentService, ChunkService


def is_rate_limited(response):
    return getattr(response, "status_code",
                   None) == status.HTTP_429_TOO_MANY_REQUESTS

class BaseIngestor(ABC):
    _embedding_model = None

    def __init__(
            self,
            db,
            user_id: str | UUID,
            document_id: str | UUID,
            filename: str,
            file_path: str,
            chunk_size: int = 1000,
            chunk_overlap: int = 100
    ):
        self.user_id = user_id
        self.document_id = document_id
        self.filename = filename
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_batch_size = settings.EMBEDDING_BATCH_SIZE
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
        try:
            # Loading data
            docs = await self._load_documents()

            # Chunking data
            chunks = await self._split_documents(docs)
            logger.info(
                f"[{self.document_id}] : Found {len(chunks)} document_chunks"
            )

            # Embedding and store data
            await self._embed_and_store(chunks)

            await self._document_status_update(DocumentStatusEnum.COMPLETED)
        except Exception as exc:
            logger.error(f"Something went wrong while processing document "
                         f"{self.document_id} : {exc}")
            await self._document_status_update(
                status=DocumentStatusEnum.FAILED,
                error_msg=str(exc)
            )
            raise exc

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

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_result(is_rate_limited)
    )
    async def _embed_batch(self, texts):
        return await self._embedder.aembed_documents(texts)

    async def _embed_and_store(self, chunks: list[Document]):
        embeddings = []

        batch_size = self.embedding_batch_size

        for idx in range(0, len(chunks), batch_size):
            batch = chunks[idx: idx + batch_size]
            texts = list(map(lambda x: x.page_content, batch))
            batch_embeddings = await self._embed_batch(texts)
            embeddings.extend(batch_embeddings)
            logger.info(
                f"chunk processed: "
                f"{min(idx + batch_size, len(chunks))}/{len(chunks)}"
            )

            await asyncio.sleep(5)

        # Updating DB with the records
        chunk_data = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_data.append({
                "document_id": self.document_id,
                "content": chunk.page_content,
                "embedding": embedding,
                "chunk_index": idx,
                "metadata_": chunk.metadata,
            })

        await self.chunk_service.create_many(chunk_data, commit=False)

    async def _document_status_update(
            self,
            status: DocumentStatusEnum,
            error_msg: Optional[str] = None
    ):
        update_info = {"status": status}
        if error_msg:
            update_info["error"] = str(error_msg)
        await self.doc_service.update(
            _id=self.document_id,
            obj_in=update_info
        )
