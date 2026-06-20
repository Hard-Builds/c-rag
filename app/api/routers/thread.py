import uuid
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.api.controller import ThreadController
from app.api.models import BaseResponse, ThreadListRespModel, \
    ThreadMessageListRespModel, QueryRequest
from app.api.utils import SafeStreamingResponse
from app.db import DBClient

thread_router = APIRouter()


@thread_router.get("/")
async def get_all_threads(
        request: Request,
        db: AsyncSession = Depends(DBClient.get_db_session)
):
    user_id = request.state.user.id
    thread_controller = ThreadController(db)
    threads = await thread_controller.get_all_threads(user_id=user_id)
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
    thread_controller = ThreadController(db)
    messages = await thread_controller.get_thread_messages(user_id, thread_id)
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
        body: QueryRequest,
        thread_id: uuid.UUID,
        db: AsyncSession = Depends(DBClient.get_db_session)
):
    thread_controller = ThreadController(db)
    return SafeStreamingResponse(
        await thread_controller.ask_a_query(
            user_id=request.state.user.id,
            thread_id=thread_id,
            rag_bot=request.app.state.rag_bot,
            query=body.query
        ),
        media_type="text/plain"
    )
