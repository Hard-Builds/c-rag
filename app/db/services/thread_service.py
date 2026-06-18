import uuid

from app.db.models.thread import Thread
from app.db.services.base import BaseDB


class ThreadService(BaseDB[Thread]):
    def __init__(self, db):
        super().__init__(db, Thread)

    async def get_threads_for_user(self, user_id: uuid.UUID):
        return await self.get_all_by_filter(user_id=user_id)
