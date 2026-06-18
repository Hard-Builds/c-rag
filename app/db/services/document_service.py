import uuid

from app.db.models.document import Document
from app.db.services.base import BaseDB


class DocumentService(BaseDB[Document]):
    def __init__(self, db):
        super().__init__(db, Document)

    async def get_documents_for_user(self, user_id: uuid.UUID):
        return await self.get_all_by_filter(user_id=user_id)

    async def is_ingested(self, user_id: int, filename: str):
        row = await self.get_by_filter(user_id=user_id, filename=filename)
        return row is not None
