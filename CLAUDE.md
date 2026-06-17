# C-RAG Project

## Stack
- Python + FastAPI (async)
- SQLite via `aiosqlite` — persistent storage for chunks + embeddings
- FAISS via `langchain-community` — in-memory vector search loaded from SQLite at startup
- Gemini via `langchain-google-genai` — embeddings (`GoogleGenerativeAIEmbeddings`)

## File Structure
```
c-rag/
├── main.py              # FastAPI app, lifespan, endpoints
├── db.py                # Database class (SQLite)
└── rag_core/
    ├── ingestor.py      # pdfIngestor class
    └── retriever.py     # Retriever class
```

## Architecture

### SQLite Schema
- `documents(id, file_path, ingested_at)` — tracks ingested files, UNIQUE on file_path
- `chunks(id, document_id, page_number, chunk_index, text, embedding BLOB)` — chunk id doubles as FAISS vector ID

### Ingestor Flow (one-time)
```
upload PDF → save to static/uploads/ → load → chunk → embed (batched, size=50) → store in SQLite
```

### Retriever Flow (every startup)
```
SQLite fetch_all_chunks() → FAISS.from_embeddings() → ready for search
```

### Query Flow (not yet built)
```
question → embed → FAISS similarity search → fetch Document objects → LLM chain → answer
```

## Key Design Decisions
- `pdfIngestor` takes a single file for now (multiple files planned later)
- `is_ingested()` check prevents re-ingestion of same file path
- After ingestion, `retriever.load()` is called to reload FAISS with new vectors
- LangChain FAISS wrapper used (not raw FAISS) — returns `Document` objects directly
- `fetch_all_chunks()` returns embeddings as `.tolist()` (plain Python list, required by LangChain)
- `aiosqlite` uses per-call `async with` connections — no persistent connection stored on `app.state`

## What's Left
1. `POST /query` endpoint
2. LLM chain (retrieved chunks + question → Gemini → answer)
3. Multiple file ingestion support
4. Error handling (empty DB on startup, duplicate uploads, bad PDFs)

## Working Conventions
- Show code in chat only — never write files directly, user writes code himself
- Process one file at a time in ingestor, expand to multiple files progressively