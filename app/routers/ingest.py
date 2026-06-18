import os
import shutil

from fastapi import APIRouter, Depends
from fastapi import UploadFile, File
from sqlalchemy.ext.asyncio.session import AsyncSession
from starlette.requests import Request

from app.db import DBClient
from app.models import BaseResponse
from app.rag.ingestor import PdfIngestor

ingest_router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@ingest_router.post("/")
async def ingest_file(
        requests: Request,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(DBClient.get_db_session),
):
    filename: str = file.filename
    file_path: str = os.path.join(UPLOAD_DIR, filename)

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
