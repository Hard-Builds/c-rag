import asyncio
from uuid import UUID

from fastapi import HTTPException
from starlette import status

from app.core import logger
from app.db import DBClient
from app.db.services import ThreadService, MessageService
from app.rag import RAGGraph


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

    async def ask_a_query(
            self,
            user_id: UUID,
            thread_id: UUID,
            rag_bot: RAGGraph,
            query: str
    ):
        queue = asyncio.Queue()

        async def run_graph():
            async with DBClient._session_factory() as session:
                try:
                    final_state = await rag_bot.ainvoke(
                        input={
                            "question": query
                        },
                        config={"configurable": {
                            "thread_id": thread_id,
                            "db": session,
                            "user_id": user_id,
                            "stream_queue": queue,
                        }}
                    )
                    await session.commit()
                    logger.info(f"final_state : {final_state}")
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Graph error: {e}")
                    await queue.put(None)

        async def token_generator():
            asyncio.create_task(run_graph())
            while True:
                token = await queue.get()
                if token is None:
                    break
                yield token

        return token_generator()
