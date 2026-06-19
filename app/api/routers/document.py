import os
import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi import UploadFile, File
from sqlalchemy.ext.asyncio.session import AsyncSession
from starlette import status
from starlette.requests import Request

from app.api.models import BaseResponse, DocumentListResponse, DocumentResp
from app.core import logger
from app.db import DBClient
from app.db.services import DocumentService
from app.rag.ingestor import PdfIngestor

document_router = APIRouter()

UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@document_router.post("/ingest")
async def ingest_document(
        requests: Request,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(DBClient.get_db_session),
):
    filename: str = file.filename
    file_path: str = os.path.join(UPLOAD_DIR, filename)

    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files allowed"
        )

    content = await file.read(4)
    if not content.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PDF file"
        )

    await file.seek(0)

    with open(file_path, "wb") as tmp:
        shutil.copyfileobj(file.file, tmp)

    ingestor = PdfIngestor(
        db=db,
        user_id=requests.state.user.id,
        filename=filename,
        file_path=file_path
    )
    await ingestor.ainvoke()
    return BaseResponse(message=f"{file.filename} ingested successfully")


@document_router.get("/")
async def list_documents(
        request: Request,
        db: AsyncSession = Depends(DBClient.get_db_session),
):
    document_service = DocumentService(db)
    document_list = await document_service.get_all_by_filter(
        user_id=request.state.user.id)
    return DocumentListResponse(
        message="Documents fetched successfully.",
        payload=[
            DocumentResp.model_validate(doc) for doc in document_list
        ]
    )


@document_router.delete("/")
async def delete_document(
        request: Request,
        document_id: UUID,
        db: AsyncSession = Depends(DBClient.get_db_session),
):
    document_service = DocumentService(db)

    document = await document_service.get_by_filter(
        id=document_id,
        user_id=request.state.user.id
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    await document_service.delete_by_id(id=document_id)
    if os.path.exists(document.file_path):
        os.remove(document.file_path)
        logger.info(f"Deleted local file: {document.file_path}")

    logger.info(f"Deleted : {document_id}")
    return BaseResponse(
        message="Deleted the document"
    )
