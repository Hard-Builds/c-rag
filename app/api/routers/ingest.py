import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi import UploadFile, File
from sqlalchemy.ext.asyncio.session import AsyncSession
from starlette import status
from starlette.requests import Request

from app.api.models import BaseResponse
from app.db import DBClient
from app.rag.ingestor import PdfIngestor

ingest_router = APIRouter()

UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@ingest_router.post("/")
async def ingest_file(
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
