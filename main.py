import os
import shutil
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, UploadFile, File
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from db import Database
from rag_core.graph import RAGGraph
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

    async with AsyncSqliteSaver.from_conn_string(
            os.getenv("DEFAULT_DB_NAME")
    ) as checkpointer:
        rag_bot = await RAGGraph(app.state.retriever).build(checkpointer)
        app.state.rag_bot = rag_bot

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
async def query(query: str, thread_id: Optional[uuid.UUID] = uuid.uuid4()):
    rag_bot = app.state.rag_bot
    response_state = await rag_bot.ainvoke(
        input={"question": query},
        config={"configurable": {"thread_id": str(thread_id)}}
    )
    return {"data": response_state["answer"]}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
