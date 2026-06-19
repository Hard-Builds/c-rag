from uuid import UUID

from fastapi import HTTPException
from starlette import status

from app.db.services import ThreadService, MessageService


class ThreadController:
    def __init__(self, db):
        self.thread_service = ThreadService(db)
        self.message_service = MessageService(db)

    async def get_all_threads(self, user_id: UUID):
        return await self.thread_service.get_threads_for_user(user_id=user_id)

    async def get_thread_messages(self, user_id: UUID, thread_id: UUID):
        if not await self.thread_service.get_by_filter(user_id=user_id,
                                                       id=thread_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found"
            )

        messages = await self.message_service.get_messages_for_thread(
            thread_id=thread_id)
        return messages
