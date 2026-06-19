from typing import Any, AsyncGenerator

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, \
    async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from starlette.requests import Request

from app.core import settings


class Base(DeclarativeBase):
    pass


class DBClient:
    _engine: AsyncEngine
    _session_factory: Any = None

    @classmethod
    async def initialise(cls, app: FastAPI) -> None:
        cls._engine = create_async_engine(
            settings.db_url,
            echo=settings.DB_ECHO,
            # SQLite doesn't support connection pooling options like pool_size
        )
        cls._session_factory = async_sessionmaker(
            bind=cls._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            class_=AsyncSession,
        )
        app.state.db_engine = cls._engine
        app.state.db_session_factory = cls._session_factory
        await cls._create_tables()

    @classmethod
    async def _create_tables(cls) -> None:
        async with cls._engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)

    @staticmethod
    async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
        session: AsyncSession = request.app.state.db_session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @classmethod
    def get_session(cls):
        if cls._session_factory is None:
            cls._engine = create_async_engine(
                settings.db_url,
                echo=settings.DB_ECHO
            )
            cls._session_factory = async_sessionmaker(
                bind=cls._engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
                class_=AsyncSession,
            )
        return cls._session_factory()
