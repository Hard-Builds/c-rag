from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi import UploadFile, File
from sqlalchemy.ext.asyncio.session import AsyncSession
from starlette import status
from starlette.requests import Request

from app.api.controller import DocumentController
from app.api.models import BaseResponse, DocumentListResponse, DocumentResp
from app.db import DBClient

document_router = APIRouter()

@document_router.post("/ingest")
async def ingest_document(
        requests: Request,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(DBClient.get_db_session),
):
    document_service = DocumentController(db)
    await document_service.handle_document_ingestion(
        file=file,
        user_id=requests.state.user.id
    )
    return BaseResponse(
        status=status.HTTP_202_ACCEPTED,
        message=f"{file.filename} processing in progress"
    )


@document_router.get("/")
async def list_documents(
        request: Request,
        db: AsyncSession = Depends(DBClient.get_db_session),
):
    document_service = DocumentController(db)
    document_list = await document_service.list_all_documents(
        user_id=request.state.user.id)
    return DocumentListResponse(
        message="Documents fetched successfully.",
        payload=[
            DocumentResp.model_validate(doc) for doc in document_list
        ]
    )


@document_router.get("/{document_id}")
async def get_document(
        request: Request,
        document_id: UUID,
        db: AsyncSession = Depends(DBClient.get_db_session),
):
    document_service = DocumentController(db)
    document = await document_service.get_document(
        user_id=request.state.user.id,
        document_id=document_id
    )
    return DocumentListResponse(
        message="Document fetched successfully.",
        payload=DocumentResp.model_validate(document)
    )


@document_router.delete("/")
async def delete_document(
        request: Request,
        document_id: UUID,
        db: AsyncSession = Depends(DBClient.get_db_session),
):
    document_service = DocumentController(db)
    await document_service.delete_document(
        user_id=request.state.user.id,
        document_id=document_id
    )
    return BaseResponse(
        message="Deleted the document"
    )
