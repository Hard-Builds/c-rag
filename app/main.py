from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

import app.db.models
from app.core import (
    custom_exception_handler,
    get_generic_exception_handler,
    http_exception_handler,
    logger,
    settings,
    validation_exception_handler,
)
from app.core.custom_exceptions import CustomException
from app.db import DBClient, run_migrations
from app.middlewares import APITraceMiddleware, AuthMiddleware
from app.rag import Retriever, RAGGraph
from app.routers import v1_api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    await DBClient.initialise(app)

    Retriever.init()

    async with AsyncPostgresSaver.from_conn_string(
            settings.db_url_psycopg
    ) as checkpointer:
        await checkpointer.setup()
        rag_bot = await RAGGraph.init(checkpointer=checkpointer)
        app.state.rag_bot = rag_bot

        yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    redirect_slashes=False,
    lifespan=lifespan
)

# CORS
origins = [u.strip() for u in (settings.CORS_ALLOWED_URL or "").split(",") if u.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware (added last = runs first)
app.add_middleware(AuthMiddleware)
app.add_middleware(APITraceMiddleware)

# Routers
app.include_router(v1_api_router)

# Exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(CustomException, custom_exception_handler)
app.add_exception_handler(Exception, get_generic_exception_handler(logger))
app.add_exception_handler(RequestValidationError, validation_exception_handler)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
