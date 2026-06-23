import uuid
from uuid import UUID

from app.constants import DocumentStatusEnum
from app.db.models.document import Document
from app.db.services.base import BaseDB


class DocumentService(BaseDB[Document]):
    def __init__(self, db):
        super().__init__(db, Document)

    async def is_ingested(self, user_id: int | UUID, filename: str):
        row = await self.get_by_where(
            Document.user_id == user_id,
            Document.filename == filename,
            Document.status != DocumentStatusEnum.FAILED
        )
        return row is not None
