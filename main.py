import os
import shutil
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, UploadFile, File

from db import Database
from rag_core.ingestor import pdfIngestor
from rag_core.retiever import Retriever

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = Database()
    await app.state.db.create_tables()

    app.state.retriever = Retriever()
    await app.state.retriever.load()

    yield

    # clean up resources


app = FastAPI(lifespan=lifespan)


@app.post("/ingest")
async def ingest_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as tmp:
        shutil.copyfileobj(file.file, tmp)

    ingestor = pdfIngestor(file_path=file_path)
    await ingestor.ainvoke()
    await app.state.retriever.load()
    return {"message": f"{file.filename} ingested successfully"}


@app.get("/query")
async def query(query: str):
    retriever = app.state.retriever
    samples = await retriever.get(query)
    return {"data": samples}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
