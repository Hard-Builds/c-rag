# C-RAG — Claude Code Guide

## Running the project

```bash
# Start infrastructure
docker compose up -d

# Start API server
uv run uvicorn app.main:app --reload

# Start Celery worker (separate terminal)
uv run celery -A app.celery_app worker --loglevel=info
```

The API runs on `http://localhost:8000`. Migrations run automatically on startup.

## Package management

This project uses **uv**. To add or remove dependencies:

```bash
uv add <package>
uv remove <package>
uv sync          # install from lockfile
```

Do not use `pip` directly.

## Database migrations

Alembic manages schema migrations. The connection URL is `db_url_psycopg` (sync psycopg2 driver) from `app/core/config.py`.

```bash
# Create a new migration after changing ORM models
uv run alembic revision --autogenerate -m "describe the change"

# Apply all pending migrations
uv run alembic upgrade head
```

Migrations live in `migrations/versions/`. The initial schema and admin user seed are already applied.

## Environment variables

All configuration lives in `.env` (read by `app/core/config.py` via `pydantic-settings`). Copy `.env.example` as a starting point. Required at startup:

```
CORS_ALLOWED_URL          # comma-separated allowed origins
GEMINI_API_KEY            # Google Gemini API key
GEMINI_MODEL              # e.g. gemini-2.0-flash
GEMINI_EMBEDDING_MODEL    # e.g. models/text-embedding-004
TAVILY_API_KEY            # Tavily web search API key (used by web_search node)
```

Optional tuning knobs (with defaults):

```
CONTEXT_EVAL_HIGHER_THR=0.7   # chunk score above this → CORRECT verdict
CONTEXT_EVAL_LOWER_THR=0.3    # all chunks below this → INCORRECT verdict
EMBEDDING_DIM=768              # must match your embedding model output size
EMBEDDING_BATCH_SIZE=10
MAX_CHAT_HISTORY=6
```

`EMBEDDING_DIM` must match the chosen embedding model output size (768 for Gemini text-embedding-004).

## Architecture decisions

### LangGraph for the RAG pipeline
The chat flow is a compiled LangGraph `StateGraph`. The graph is built once at startup (`RAGGraph.init()`) and stored on `app.state.rag_bot`. State is checkpointed to PostgreSQL via `langgraph-checkpoint-postgres`, keyed by `thread_id`.

Node execution order:
```
START → upsert_thread → should_use_rag
          ├─(use_rag=True)→ context_retriever → context_eval
          │                      ├─(CORRECT)──────────────────────┐
          │                      ├─(INCORRECT/AMBIGUOUS)→ rewrite_query → web_search
          │                                                                    │
          │                                                             knowledge_refiner
          │                                                                    │
          └─(use_rag=False)────────────────────────────────────────→ chat_bot ◄┘
                                                   └─(messages > MAX_CHAT_HISTORY)→ summarizer → END
```

### Context evaluation and web search fallback
After retrieval, `context_eval` scores each chunk independently against the question using a structured LLM call (score 0.0–1.0). The verdict drives routing:
- `CORRECT` → pass `good_docs` to `knowledge_refiner`
- `INCORRECT` / `AMBIGUOUS` → `rewrite_query` reformulates the question into search keywords, `web_search` fetches up to 3 live results via Tavily, then `knowledge_refiner` processes both web docs and any good docs together

Thresholds are configurable: `CONTEXT_EVAL_HIGHER_THR` (default 0.7) and `CONTEXT_EVAL_LOWER_THR` (default 0.3).

### Knowledge refiner
`knowledge_refiner` decomposes context into individual sentences, filters each one with the LLM (`keep=true/false`), and recomposes only the relevant sentences into a single `refined_context` string. The `chat_bot` node receives this string directly instead of raw document chunks.

### pgvector for similarity search
Chunks are stored in the `chunks` table with a `Vector(768)` column. Retrieval uses cosine distance via pgvector's `.cosine_distance()` method. An HNSW index is created in the Alembic initial migration for fast approximate nearest-neighbor search.

### Celery for async ingestion
PDF ingestion (load → chunk → embed → store) is offloaded to a Celery task using `celery-aio-pool` so that async SQLAlchemy sessions work inside tasks. Rate-limit retries use `tenacity` with exponential backoff on embedding API calls.

### Streaming responses
`chat_bot` node pushes tokens to an `asyncio.Queue` as they arrive from the LLM's `astream_events`. The controller drains the queue and yields chunks into a `SafeStreamingResponse` (`text/plain`).

## Key files

| File | Purpose |
|---|---|
| `app/main.py` | App factory, lifespan, middleware/router wiring |
| `app/core/config.py` | All settings — add new env vars here |
| `app/rag/graph.py` | LangGraph graph definition |
| `app/rag/retriever.py` | Embedding model init + similarity search |
| `app/rag/ingestor/abstract.py` | Ingestor base class (load → chunk → embed → store) |
| `app/rag/ingestor/pdf_ingestor.py` | PDF-specific loader (extend here for new file types) |
| `app/bot/nodes/context_eval.py` | Per-chunk relevance scoring + CORRECT/INCORRECT/AMBIGUOUS verdict |
| `app/bot/nodes/web_query_rewrite.py` | Rewrites user question into a web search query |
| `app/bot/nodes/web_search.py` | Tavily web search, returns `list[Document]` |
| `app/bot/nodes/knowledge_refiner.py` | Sentence-level context filter → `refined_context` string |
| `app/bot/nodes/generator.py` | `chat_bot` — prompt assembly, streaming, message persistence |
| `app/bot/state.py` | `RAGState` — the shared graph state |
| `app/db/models/chunk.py` | `Chunk` ORM model with pgvector column |
| `app/db/services/chunk_service.py` | `similarity_search()` query |
| `app/worker/tasks.py` | Celery `ingest_document` task |
| `app/middlewares/auth.py` | Auth stub — TODO: replace with real token validation |

## Adding a new file type

1. Create `app/rag/ingestor/<type>_ingestor.py` extending `BaseIngestor`
2. Implement `_load_documents()` to return `list[Document]`
3. Update `DocumentController.handle_document_ingestion()` to dispatch the right ingestor
4. Update the file validation in `_validate_pdf_doc()` (or replace it)

## Authentication (current state)

Auth is stubbed — all private/admin routes attach the seeded admin user automatically. The TODO in `app/middlewares/auth.py` marks where bearer token validation should be wired in. `INTERNAL_TOKEN` is used for service-to-service calls on `/internal` routes.

## Code conventions

- Async everywhere: use `async def` and `await` for all DB and LLM calls
- DB access goes through services in `app/db/services/` — do not write raw queries in controllers or routes
- Use `app/core/logger` for logging, not `print`
- Pydantic models for request/response schemas live in `app/api/models/`
- ORM models live in `app/db/models/` — add new tables here and generate a migration