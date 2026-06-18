import uuid

from sqlalchemy import select

from app.db.models.message import Message
from app.db.services.base import BaseDB


class MessageService(BaseDB[Message]):
    def __init__(self, db):
        super().__init__(db, Message)

    async def get_messages_for_thread(self, thread_id: uuid.UUID):
        stmt = select(self.model).filter_by(thread_id=thread_id).order_by(
            Message.created_at)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
