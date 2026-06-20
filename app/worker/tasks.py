from uuid import UUID

from app.celery_app import celery_app
from app.core import logger
from app.db import DBClient
from app.rag import PdfIngestor


@celery_app.task(
    name="ingest_document",
    bind=True,
    max_retries=3
)
async def ingest_document(
        self, document_id: UUID, user_id: UUID, filename: str, file_path: str
):
    async with DBClient.get_session() as db:
        try:
            logger.info(f"Processing {document_id}")
            ingestor = PdfIngestor(
                db=db,
                user_id=user_id,
                document_id=document_id,
                filename=filename,
                file_path=file_path,
            )
            await ingestor.ainvoke()
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error(f"Task failed for document {document_id}: {exc}")
            raise self.retry(exc=exc, countdown=60)
