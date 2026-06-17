import os

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from db import Database

load_dotenv()


class pdfIngestor:
    def __init__(self, file_path: str,
                 chunk_size: int = 1000, chunk_overlap: int = 100):
        self._db = Database()

        self.file_path = file_path

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.embedding_batch_size = 50
        self.embedding_model = GoogleGenerativeAIEmbeddings(
            model=os.getenv("GEMINI_EMBEDDING_MODEL")
        )

    async def _validate_file(self) -> None:
        file_path = self.file_path
        if await self._db.is_ingested(file_path=file_path):
            raise Exception("Given file is already processed")

    async def ainvoke(self):
        # validating file paths
        await self._validate_file()

        # Loading data
        document_id, docs = await self._load_documents()

        # Chunking data
        chunks = await self._chunk_docs(docs)

        # Embedding data
        embeddings = await self._embed_docs(chunks)

        # Storing data
        await self._store_chunks(document_id, chunks, embeddings)

    async def _load_documents(self) -> tuple[int, list[Document]]:
        file_path = self.file_path
        documents = await PyPDFLoader(file_path=file_path).aload()
        document_id = await self._db.insert_document(file_path)
        return document_id, documents

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

    async def _store_chunks(self, document_id, chunks, embeddings) -> None:
        chunk_data = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_data.append({
                "page_number": chunk.metadata.get("page"),
                "chunk_index": idx,
                "text": chunk.page_content,
                "embedding": embedding
            })

        await self._db.insert_chunks(document_id, chunk_data)
