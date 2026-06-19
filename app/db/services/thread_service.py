import uuid

from sqlalchemy import select

from app.db.models.thread import Thread
from app.db.services.base import BaseDB


class ThreadService(BaseDB[Thread]):
    def __init__(self, db):
        super().__init__(db, Thread)

    async def get_threads_for_user(self, user_id: uuid.UUID):
        stmt = select(self.model).filter_by(user_id=user_id).order_by(
            Thread.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
