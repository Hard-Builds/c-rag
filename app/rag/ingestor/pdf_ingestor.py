from langchain_community.document_loaders import PyPDFLoader

from app.rag.ingestor.abstract import BaseIngestor


class PdfIngestor(BaseIngestor):

    async def _load_documents(self):
        if await self.doc_service.is_ingested(
                user_id=self.user_id,
                filename=self.filename
        ):
            raise Exception("Given file is already processed")

        file_path = self.file_path
        documents = await PyPDFLoader(file_path=file_path).aload()
        return documents
