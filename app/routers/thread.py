import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from langchain_core.documents import Document
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.db import DBClient
from app.models import BaseResponse
from app.rag import Retriever

thread_router = APIRouter()


@thread_router.post("/{thread_id}/query")
async def query(
        requests: Request,
        query: str,
        thread_id: Optional[uuid.UUID],
        db: Session = Depends(DBClient.get_db_session),
):
    chunks = await Retriever.get(
        db=db,
        user_id=requests.state.user.id,
        query=query
    )
    chunks_payload = list(map(
        lambda x: Document(
            page_content=x.content,
            metadata=x.metadata_
        ), chunks
    ))
    return BaseResponse(
        message="Context retrieved.",
        payload=chunks_payload
    )
