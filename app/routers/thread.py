import uuid
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.requests import Request

from app.db import DBClient
from app.db.services import ThreadService, MessageService
from app.models import BaseResponse, ThreadListRespModel, \
    ThreadMessageListRespModel

thread_router = APIRouter()


@thread_router.get("/")
async def get_all_threads(
        request: Request,
        db: AsyncSession = Depends(DBClient.get_db_session)
):
    user_id = request.state.user.id
    thread_service = ThreadService(db)
    threads = await thread_service.get_all_by_filter(user_id=user_id)
    return BaseResponse(
        message="Fetched all threads",
        payload=list(map(
            lambda x: ThreadListRespModel.model_validate(x),
            threads
        ))
    )


@thread_router.get("/{thread_id}/")
async def get_thread_conversation(
        request: Request,
        thread_id: UUID,
        db: AsyncSession = Depends(DBClient.get_db_session)
):
    user_id = request.state.user.id
    message_service = MessageService(db)
    thread_service = ThreadService(db)

    if not await thread_service.get_by_filter(user_id=user_id, id=thread_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )

    messages = await message_service.get_messages_for_thread(
        thread_id=thread_id)
    return BaseResponse(
        message="Thread Messages found",
        payload=list(map(
            lambda x: ThreadMessageListRespModel.model_validate(x),
            messages
        ))
    )

@thread_router.post("/{thread_id}/query")
async def query(
        request: Request,
        query: str,
        thread_id: Optional[uuid.UUID],
        db: AsyncSession = Depends(DBClient.get_db_session),
):
    user_id = request.state.user.id
    rag_bot = request.app.state.rag_bot
    response_state = await rag_bot.ainvoke(
        input={
            "question": query
        },
        config={"configurable": {
            "thread_id": thread_id,
            "db": db,
            "user_id": user_id,
        }}
    )
    print(f"response_state: {response_state}")
    answer = response_state["answer"]
    return BaseResponse(
        message="Got your response",
        payload=answer
    )
