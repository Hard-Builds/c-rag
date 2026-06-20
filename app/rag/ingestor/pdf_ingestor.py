from langchain_community.document_loaders import PyPDFLoader

from app.rag.ingestor.abstract import BaseIngestor


class PdfIngestor(BaseIngestor):

    async def _load_documents(self):
        file_path = self.file_path
        documents = await PyPDFLoader(file_path=file_path).aload()
        return documents
