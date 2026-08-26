# Masteacon — Your beacon to mastery.

Masteacon is a multi-user, multi-workspace Retrieval-Augmented Generation (RAG) knowledge
assistant built with FastAPI, PostgreSQL and pgvector, with a React web app on top. Upload PDF,
DOCX or TXT documents into a workspace, then ask natural-language questions about their content
— Masteacon retrieves the most relevant passages via semantic vector search and answers using
OpenAI or Anthropic, always citing its sources and never inventing an answer it can't ground in
your own documents. Every workspace, document, conversation and agent tool call is scoped to the
account that owns it.

> The underlying repository, package names and technical identifiers still use the project's
> original working name (`ai-knowledge-assistant`) — only the product-facing name changed.

## Features

- **Accounts & workspaces** — JWT-based auth; every user gets isolated workspaces, and no
  endpoint can read, search or act on a workspace it doesn't own
- **Document ingestion** — upload PDF, DOCX or TXT; text extraction, chunking and embedding run
  asynchronously (Celery + Redis) so an upload returns immediately and indexing continues in the
  background, with bounded automatic retries on transient failures
- **Semantic search** — vector similarity search over indexed chunks, optionally filtered by
  document or content type
- **Hybrid search** — an optional fusion of vector similarity with PostgreSQL full-text (keyword)
  search via Reciprocal Rank Fusion, so an exact technical term a pure embedding match can miss
  (an error code, a config key) still surfaces (disabled by default)
- **Grounded question answering (RAG)** — answers are generated strictly from retrieved context,
  with source attribution for every claim; conversations keep bounded prior-turn history so
  follow-up questions stay coherent without letting the prompt grow without limit
- **Agent / tool use** — ask a question and let the model decide whether it needs to call a
  read-only tool (list workspaces, list documents, fetch a document, summarize a document); every
  tool call is authorization-checked server-side before it runs, regardless of what the model asks
  for
- **Pluggable chat providers** — OpenAI or Anthropic, selected via configuration; embeddings
  always use OpenAI (no public Anthropic embeddings API)
- **Reranking** — an optional lightweight second-stage pass that blends vector similarity with
  lexical overlap to reorder retrieved candidates before they're used to answer (disabled by
  default; off means byte-for-byte the same retrieval behavior as without it)
- **Structured observability** — every request is tagged with a correlation id and logged as a
  single structured JSON event (counts, durations, ids — never prompts, answers or document
  content)
- **File upload security** — extension/MIME validation, size limits, safe generated filenames
- **Clean layered architecture** (routes → services → repositories → database), fully async
  FastAPI + SQLAlchemy stack, Dockerized for one-command local startup

## Tech Stack

- **Framework:** FastAPI (async)
- **Database:** PostgreSQL + [pgvector](https://github.com/pgvector/pgvector)
- **ORM / Migrations:** SQLAlchemy 2.0 (async) + Alembic
- **Background jobs:** Celery + Redis (asynchronous document indexing)
- **Config:** Pydantic Settings
- **RAG orchestration:** [LangChain](https://python.langchain.com/) — token-aware chunking
  (`TokenTextSplitter`), embeddings, chat models and the retriever/vector-store interface all go
  through LangChain, behind this project's own `EmbeddingProvider`/`ChatProvider`/`VectorStore`
  abstractions so business logic never touches a provider SDK directly
- **LLM providers:** OpenAI and Anthropic/Claude (chat, via `ChatOpenAI` / `ChatAnthropic`),
  OpenAI (embeddings, via `OpenAIEmbeddings`) — function calling for both is driven by
  LangChain's `bind_tools`, which normalizes OpenAI's and Anthropic's very different native
  tool-calling formats into one shape
- **Auth:** JWT (PyJWT + bcrypt password hashing)
- **Parsing:** pypdf, python-docx
- **Tokenization:** tiktoken
- **Testing:** pytest, pytest-asyncio
- **Frontend:** React + Vite + TypeScript
- **Containerization:** Docker, Docker Compose

## Architecture

The codebase follows a strict layering discipline: `route → service → repository → database`.
Business logic never talks to SQLAlchemy directly, and services never talk to an LLM provider's
SDK directly — both are isolated behind a repository layer and a provider abstraction
(`EmbeddingProvider` / `ChatProvider`), so swapping OpenAI for Anthropic, or a real Celery
dispatcher for a synchronous test fake, never touches business logic.

```text
app/
├── main.py                      # FastAPI app, routers, middleware, exception handlers
│
├── api/
│   ├── dependencies.py          # Dependency-injection wiring
│   └── routes/                  # HTTP routes (thin — delegate to services)
│       ├── health.py, auth.py, workspaces.py, documents.py
│       ├── search.py, rag.py, conversations.py, agent.py
│
├── core/
│   ├── config.py                # Pydantic Settings
│   ├── database.py              # Async engine/session/Base
│   ├── security.py              # Password hashing + JWT issue/verify
│   ├── exceptions.py            # Domain exceptions → HTTP status mapping
│   ├── logging.py               # Structured JSON logging
│   └── request_context.py       # Per-request correlation id (contextvar)
│
├── models/                      # SQLAlchemy ORM models
│   └── user.py, workspace.py, document.py, document_chunk.py,
│       conversation.py, message.py
│
├── schemas/                     # Pydantic request/response models
├── repositories/                # Database queries only
│
├── services/                    # Business logic / orchestration
│   ├── auth_service.py, workspace_service.py
│   ├── document_service.py       # Validate → store → dispatch for indexing
│   ├── document_indexing_service.py  # Parse → chunk → embed (runs in the worker)
│   ├── parsing_service.py, chunking_service.py, embedding_service.py
│   ├── langchain_vector_store.py # ChunkVectorStore: a LangChain VectorStore over pgvector
│   ├── retrieval_service.py      # Semantic search (+ optional reranking)
│   ├── reranking_service.py      # Vector + lexical blended reranker
│   ├── rag_service.py            # Retrieval + prompt construction + generation
│   ├── conversation_service.py   # Bounded conversation history
│   ├── agent_service.py          # One bounded round of LLM tool-calling
│   └── tool_execution_service.py # Validates/authorizes/executes a single tool call
│
├── providers/                   # External API abstractions, backed by LangChain
│   ├── base_embedding_provider.py, base_chat_provider.py
│   ├── langchain_chat_provider.py  # Shared LangChain-backed complete()/tool-calling logic
│   ├── openai_provider.py       # ChatOpenAI + OpenAIEmbeddings
│   ├── anthropic_provider.py    # ChatAnthropic
│   └── chat_provider_factory.py
│
├── tools/                       # Read-only agent tools (list/get/summarize, workspace-scoped)
│
└── tasks/                       # Celery app + the document-indexing task (bounded retries)

tests/       # pytest suite (fully mocked providers/repositories — no real API calls)
alembic/     # Database migrations
uploads/     # Uploaded file storage (gitignored, safe generated filenames only)
frontend/    # React + Vite + TypeScript web app
```

## RAG Pipeline

1. **Upload:** a document is validated, safely stored, and its indexing job is dispatched to a
   Celery worker — the upload request returns immediately.
2. **Index (async, in the worker):** the document is parsed into plain text, split into
   overlapping token-bounded chunks by LangChain's `TokenTextSplitter` (`CHUNK_SIZE` /
   `CHUNK_OVERLAP`), embedded via LangChain's `OpenAIEmbeddings` (`OPENAI_EMBEDDING_MODEL`), and
   stored in PostgreSQL using `pgvector` columns. Transient failures are retried automatically,
   up to a bounded number of attempts with exponential backoff.
3. **Ask:** a question is embedded the same way; the most similar chunks are retrieved from the
   caller's own workspace through `ChunkVectorStore` — a LangChain `VectorStore` adapter over the
   pgvector-backed repository — via cosine similarity (`SEARCH_TOP_K` / `SIMILARITY_THRESHOLD`),
   with optional filtering by document or content type. `workspace_id` is a mandatory filter the
   adapter refuses to search without, so retrieval can never cross a workspace boundary. If
   `HYBRID_SEARCH_ENABLED` is on, this vector search is fused with a PostgreSQL full-text
   (keyword) search over the same chunks via Reciprocal Rank Fusion, so an exact technical term a
   pure embedding match can miss still surfaces.
4. **Rerank (optional):** if enabled, a wider candidate set is fetched and reordered by a blend
   of vector similarity and lexical overlap before being truncated to the final top-k.
5. **Generate:** the retrieved chunks — plus, inside a conversation, a bounded window of prior
   turns — are placed into a strict, context-only system prompt sent to the configured LangChain
   chat model (`ChatOpenAI` or `ChatAnthropic`). If no relevant context is found, the assistant
   explicitly says so instead of hallucinating an answer.
6. **Respond:** the answer is returned together with the list of source chunks that were used.

The **agent** endpoint follows a parallel, bounded path: the model is offered a small set of
read-only tools, decides whether it needs one, and — if so — the tool call is validated and
authorization-checked (workspace/document ownership) before it ever runs, then the tool's result
is fed back to the model for a final answer. No loop: at most one round of tool calls per request.

## Installation

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (recommended — see [Docker Usage](#docker-usage))
- An OpenAI API key (and, optionally, an Anthropic API key)

### Local (without Docker)

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env            # fill in OPENAI_API_KEY, DATABASE_URL, JWT_SECRET_KEY, REDIS_URL
alembic upgrade head
uvicorn app.main:app --reload
```

This requires a running PostgreSQL instance with the `pgvector` extension, and a Redis instance
for background indexing (the Docker setup below provisions both for you). To process uploads
locally you also need a Celery worker running: `celery -A app.tasks.celery_app worker --loglevel=info`.

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `APP_NAME` | Application name | `AI Knowledge Assistant` |
| `APP_ENV` | Environment name | `development` |
| `DEBUG` | Enable debug logging / SQL echo | `true` |
| `DATABASE_URL` | Async PostgreSQL connection string | — |
| `REDIS_URL` | Celery broker/result backend | `redis://localhost:6379/0` |
| `LLM_PROVIDER` | Chat provider: `openai` or `anthropic` | `openai` |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `OPENAI_CHAT_MODEL` | Chat completion model | `gpt-4o-mini` |
| `OPENAI_EMBEDDING_MODEL` | Embedding model | `text-embedding-3-small` |
| `ANTHROPIC_API_KEY` | Anthropic API key (only if `LLM_PROVIDER=anthropic`) | — |
| `ANTHROPIC_CHAT_MODEL` | Anthropic chat model | `claude-3-5-sonnet-20241022` |
| `JWT_SECRET_KEY` | JWT signing secret — **must** be overridden in production | dev-only default |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | `60` |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins | `http://localhost:5173,http://localhost:3000` |
| `EMAIL_DELIVERY_ENABLED` | Send verification emails via Resend | `false` |
| `RESEND_API_KEY` | [Resend](https://resend.com) API key (only needed when the above is `true`) | — |
| `EMAIL_FROM_ADDRESS` | Sender address, e.g. `Masteacon <onboarding@yourdomain.com>` | — |
| `CHUNK_SIZE` | Max tokens per chunk | `800` |
| `CHUNK_OVERLAP` | Token overlap between chunks | `150` |
| `SEARCH_TOP_K` | Default number of chunks retrieved | `5` |
| `SIMILARITY_THRESHOLD` | Minimum cosine similarity to keep a match | `0.3` |
| `RERANK_ENABLED` | Enable the reranking pass | `false` |
| `RETRIEVAL_CANDIDATE_COUNT` | Candidates fetched before reranking (also used by hybrid search) | `20` |
| `RERANK_TOP_K` | Chunks kept after reranking | `5` |
| `HYBRID_SEARCH_ENABLED` | Fuse vector + keyword (full-text) search via RRF | `false` |
| `CONVERSATION_HISTORY_MAX_MESSAGES` | Prior turns kept per conversation | `10` |
| `CONVERSATION_HISTORY_MAX_TOKENS` | Token budget for prior turns | `2000` |
| `MAX_UPLOAD_SIZE_MB` | Max upload size | `20` |
| `UPLOAD_DIRECTORY` | Directory for stored uploads | `uploads` |

Starting the API with `APP_ENV=production` while `JWT_SECRET_KEY` is still at its development
default is a hard startup error, by design — see [`.env.example`](.env.example) for a
ready-to-copy template. The real `.env` file is never committed.

## Docker Usage

```bash
docker compose up --build
```

This starts five services:

- `postgres` — PostgreSQL with the `pgvector` extension (health-checked)
- `redis` — Celery broker/result backend (health-checked)
- `api` — the FastAPI application: waits for PostgreSQL and Redis to be healthy, runs Alembic
  migrations automatically, then starts Uvicorn
- `celery_worker` — runs the async document-indexing pipeline
- `frontend` — the React web app, built and served by nginx

The API is available at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`. The web app is available at `http://localhost:5173`.

## Frontend

A React + Vite + TypeScript single-page app in [`frontend/`](frontend), covering:

- **Auth** — register / login (JWT stored client-side, attached to every API call)
- **Workspaces** — create and switch between workspaces
- **Documents** — upload PDF/DOCX/TXT, live indexing status
- **Chat** — per-workspace conversations with persistent history and source citations
- **Agent** — ask questions that may trigger LLM function-calling tools (list workspaces/
  documents, summarize a document), with a log of exactly which tools ran and their result
- Dark/light theme and Turkish/English language support throughout

Run it standalone against a local API:

```bash
cd frontend
cp .env.example .env   # VITE_API_BASE_URL, defaults to http://localhost:8000
npm install
npm run dev             # http://localhost:5173
```

## API Endpoints

The authoritative, up-to-date list is always at `/docs` (Swagger UI). As of this writing:

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Basic application info |
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/auth/register` | Create an account, returns an access token |
| `POST` | `/api/v1/auth/login` | Log in, returns an access token |
| `GET` | `/api/v1/auth/me` | Current authenticated user |
| `POST` | `/api/v1/workspaces` | Create a workspace |
| `GET` | `/api/v1/workspaces` | List your workspaces |
| `GET` | `/api/v1/workspaces/{id}` | Fetch one of your workspaces |
| `POST` | `/api/v1/documents` | Upload a PDF/DOCX/TXT document into a workspace |
| `GET` | `/api/v1/documents` | List documents in a workspace |
| `GET` | `/api/v1/documents/{id}` | Fetch a single document |
| `GET` | `/api/v1/documents/{id}/status` | Poll indexing status |
| `POST` | `/api/v1/search` | Semantic search within a workspace (optional document/content-type filter) |
| `POST` | `/api/v1/ask` | Ask a question — one-shot RAG, no history |
| `POST` | `/api/v1/conversations` | Start a conversation in a workspace |
| `GET` | `/api/v1/conversations` | List your conversations in a workspace |
| `GET` | `/api/v1/conversations/{id}` | Fetch a conversation with its messages |
| `POST` | `/api/v1/conversations/{id}/messages` | Ask within a conversation (RAG + history) |
| `POST` | `/api/v1/agent/ask` | Ask, letting the LLM call read-only tools if it needs to |

All endpoints except `/`, `/health`, `/docs` and `/api/v1/auth/*` require a `Bearer` access
token, and every workspace-scoped endpoint verifies you own that workspace (and, transitively,
any document, conversation or tool result it returns) before returning anything — an unowned or
nonexistent resource is rejected identically, so ownership can never be probed for.

## Example Requests

**Register and log in**

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "a-strong-password"}'
```

**Upload a document into a workspace**

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "workspace_id=1" \
  -F "file=@employee_handbook.pdf"
```

**Ask a question (RAG)**

```bash
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "Şirketin yıllık izin politikası nedir?", "workspace_id": 1}'
```

```json
{
  "answer": "Şirket politikasına göre çalışanlar yılda 14 gün izin hakkına sahiptir.",
  "sources": [
    {
      "document_id": 1,
      "filename": "employee_handbook.pdf",
      "chunk_index": 4,
      "similarity_score": 0.91
    }
  ]
}
```

## Testing

```bash
pytest
```

159 tests cover authentication, workspace/document/conversation ownership and isolation, parsing
(PDF/DOCX/TXT), chunking, embedding, semantic retrieval and filtering, hybrid search fusion,
reranking, the RAG and agent pipelines, tool authorization, async indexing (including bounded
retry behavior), and structured logging. All LLM/embedding calls are replaced with deterministic fake providers, and
the Celery dispatcher has a synchronous in-process fake — no real, billable API calls are made
during testing, and results are fully reproducible.

## Security Notes

- Passwords are hashed with bcrypt and never stored or logged in plain text.
- JWTs are signed with a fixed, explicit algorithm (no algorithm-confusion surface); the API
  refuses to start in production with the default signing secret.
- Every workspace-scoped repository query is filtered by `workspace_id` at the SQL level —
  ownership isn't just checked at the route, it's structurally impossible to bypass in retrieval.
- Agent tool calls are authorization-checked server-side before execution, independent of what
  the model itself decides or is told to do by document/user content.
- Structured logs record counts, ids, durations and booleans only — never API keys, prompts,
  questions, answers or document content.
