from datetime import datetime

import aiosqlite
import numpy as np


class Database:
    schemas = [
        """
        CREATE TABLE IF NOT EXISTS documents(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE NOT NULL,
            ingested_at TIMESTAMP NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS chunks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL REFERENCES documents(id),
            page_number INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            embedding BLOB NOT NULL
        )
        """
    ]

    def __init__(self, db_path: str = "vector_store.db"):
        self.db_path = db_path

    async def create_tables(self):
        async with aiosqlite.connect(self.db_path) as conn:
            for schema in self.schemas:
                await conn.execute(schema)
            await conn.commit()

    # ---- operations ----
    async def is_ingested(self, file_path: str) -> bool:
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                "SELECT id FROM documents WHERE file_path = ?",
                (file_path,)
            )
            row = await cursor.fetchone()
            return row is not None

    async def insert_document(self, file_path: str):
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                "INSERT INTO documents (file_path, ingested_at)"
                "VALUES (?, ?);",
                (file_path, datetime.utcnow())
            )
            await conn.commit()
            return cursor.lastrowid

    async def insert_chunks(self, document_id: int, chunk_data: list[dict]) \
            -> None:
        rows = list(map(
            lambda x: (
                document_id,
                x["page_number"],
                x["chunk_index"],
                x["text"],
                np.array(x["embedding"], dtype="float32").tobytes()
            ),
            chunk_data
        ))
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.executemany(
                """
                INSERT INTO chunks(document_id, page_number, chunk_index, text, embedding)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows
            )
            await conn.commit()

    async def fetch_all_chunks(self):
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                """
                SELECT id, text, embedding, page_number
                from chunks
                """
            )
            rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "text": row[1],
                "embedding": np.frombuffer(row[2], dtype="float32").tolist(),
                "page_number": row[3]
            }
            for row in rows
        ]
