import uuid

from app.db.models.message import Message
from app.db.services.base import BaseDB


class MessageService(BaseDB[Message]):
    def __init__(self, db):
        super().__init__(db, Message)

    async def get_messages_for_thread(self, thread_id: uuid.UUID):
        return await self.get_all_by_filter(thread_id=thread_id)
