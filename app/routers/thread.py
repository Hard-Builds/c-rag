import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.db import DBClient

thread_router = APIRouter()


@thread_router.post("/{thread_id}/query")
async def query(
        requests: Request,
        thread_id: Optional[uuid.UUID],
        db: Session = Depends(DBClient.get_db_session),
):
    rag_bot = requests.state.rag_bot
    response_state = await rag_bot.ainvoke(
        input={"question": query},
        config={"configurable": {"thread_id": str(thread_id)}}
    )
    return {"data": response_state["answer"]}
