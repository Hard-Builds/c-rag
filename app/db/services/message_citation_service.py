import uuid

from app.db.models.message_citation import MessageCitation
from app.db.services.base import BaseDB


class MessageCitationService(BaseDB[MessageCitation]):
    def __init__(self, db):
        super().__init__(db, MessageCitation)

    async def get_citations_for_message(self, message_id: uuid.UUID):
        return await self.get_all_by_filter(message_id=message_id)
