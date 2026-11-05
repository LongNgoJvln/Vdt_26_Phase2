# Architecture

> **Baseline hiện trạng:** Trước khi thay đổi kiến trúc network-focused, đọc
> [`ARCHITECTURE_BASELINE_2026-09-14_VI.md`](ARCHITECTURE_BASELINE_2026-09-14_VI.md).
> Tài liệu này ghi lại monolith trước refactor, gồm sequence diagram, chức năng
> legacy, gap register và định dạng đối chiếu hậu refactor. Bản tiếng Anh được
> giữ tại [`ARCHITECTURE_BASELINE_2026-09-14.md`](ARCHITECTURE_BASELINE_2026-09-14.md).

This document describes the internal structure of VHT Network Automation: the
layer boundaries, the FastAPI middleware stack, the startup lifecycle, the agent
loop, and how the pieces find each other at runtime.

For storage backends (PostgreSQL / SQLite, Qdrant, MinIO), see
[`STORAGE.md`](STORAGE.md). For document ingestion and retrieval, see
[`RAG_PIPELINE.md`](RAG_PIPELINE.md). For environment variables and feature
flags, see [`CONFIGURATION.md`](CONFIGURATION.md).

## Layer boundaries

```
app.py                  → FastAPI entry point (middleware stack, startup/shutdown, router registration)
                          ⚠ slim orchestrator: keep imports light or Docker startups slow.
core/                   → Foundation layer. No dependency on src/ or routes/.
  database.py             SQLAlchemy models + schema migrations (init_db())
  auth.py                 AuthManager: hashing, tokens, user CRUD
  middleware.py           RequestIdMiddleware, SecurityHeadersMiddleware
  constants.py            BASE_DIR, DATA_DIR, env defaults
  feature_flags.py        FeatureFlags singleton (deploy-mode + per-var gating)
  exceptions.py           SessionNotFoundError, LLMServiceError, …
  response_types.py       Standard JSON response helpers
  models.py               Pydantic request/response schemas
  session_manager.py      Legacy JSON session store (superseded by DB)
src/                   → Business logic
  llm_core.py             LLM call dispatch — sync/async HTTP, streaming, cache, cooldown
  agent_loop.py           The agent loop — tool selection, execution, continuation
  agent_tools.py          Tool definitions exposed to the agent
  chat_processor.py       Memory retrieval, web search, skill matching
  chat_handler.py         Chat session orchestration: create/continue/stream
  memory.py / .py         Persistent KV + vector memory (Chroma/HTTP fallback)
  rag_manager.py          Personal document RAG (per-user + global collections)
  rag_vector.py           Qdrant-backed vector store for documents
  tool_index.py           Tool retrieval for agent (vector + keyword)
  tool_implementations.py Built-in tool implementations
  tool_execution.py       Tool call execution engine
  tool_parsing.py         Tool-call parsing from LLM responses
  tool_schemas.py         Tool JSON schemas
  tool_security.py        Per-user tool access control
  settings.py             User/admin settings load/save
  task_scheduler.py       Cron-style + event-driven scheduler
  mcp_manager.py          MCP server lifecycle (stdio/SSE/HTTP)
  agent_runs.py           Background agent execution (deep research …)
  database.py             DB helper functions (separate from core/models)
  object_store.py         MinIO/S3 client wrapper — per-user prefix isolation
  …                       (see src/ for the full list)
routes/                → FastAPI APIRouters, one file per feature area
  auth_routes.py / chat_routes.py / session_routes.py / document_routes.py
  memory_routes.py / skills_routes.py / research_routes.py / model_routes.py
  email_routes.py / calendar_routes.py / note_routes.py / task_routes.py
  mcp_routes.py / webhook_routes.py / preset_routes.py / api_token_routes.py
  gallery_routes.py / …
services/              → External-service integrations
  docs/ memory/ search/ shell/ hwfit/ research/ faces/ cache/ stt/ tts/ youtube/
static/                → Frontend SPA (HTML + CSS + JS modules)
alembic/               → Migrations (Postgres-path only)
scripts/               → Operational + migration CLIs  (see SCRIPTS.md)
data/                  → Runtime data (gitignored): app.db, auth.json, settings.json, uploads/, …
```

Two strict rules hold across this layout:

1. **`core/` never imports from `src/` or `routes/`.** The foundation layer is
   the bottom of the stack; everything above depends on it, never the reverse.
2. **Almost every DB model has an `owner` column.** Routes filter by
   `request.state.current_user`; admin users bypass owner filters. Legacy
   `owner=NULL` data is periodically re-attributed (`scripts/claim_ownerless.py`,
   `core/database.py::_migrate_assign_legacy_owner`).

## FastAPI middleware stack

`app.py` builds the middleware stack in a deliberate order — outermost first,
so each layer sees the request before the layer it protects:

| Order | Middleware | Responsibility |
|---|---|---|
| 1 | `RequestIdMiddleware` | Tags every request with `X-Request-Id`; thread-local for logs |
| 2 | `CORSMiddleware` | `ALLOWED_ORIGINS` from env (defaults to localhost) |
| 3 | `SecurityHeadersMiddleware` | CSP with per-request nonce, `X-Frame-Options`, `X-Content-Type-Options`, referrer policy |
| 4 | `RequestTimeoutMiddleware` | Cancel requests that exceed the configured ceiling |
| 5 | `AuthMiddleware` | Cookie session → user, OR `ody_*` Bearer API token → user, OR (loopback-only) `LOCALHOST_BYPASS` |

Auth resolution order:
1. **Exempt path** (login, setup, health, static) → continue.
2. **Bearer `ody_*` token** in `Authorization` header → look up `ApiToken`, load user, invalidate cache on revoke.
3. **Session cookie** → look up auth session, load user.
4. **`LOCALHOST_BYPASS=true`** + loopback source (spoof-guarded against `X-Forwarded-For`) → admin auto-login. **Local dev only.**

The CSP nonce is injected into HTML pages by replacing `{{CSP_NONCE}}` in the
template. The nonce is rotated per request.

## Startup lifecycle

`app.py` runs three lifecycle phases.

### 1. Pre-load (module import)
- `register_static_mime_types()` forces `.js` / `.mjs` MIME types (some Windows registries break ES module loading).
- On Windows, `HF_HUB_DISABLE_SYMLINKS=1` is set so HF hub copies (not symlinks) the embedding model — network shares can't follow HF symlinks.
- `load_dotenv(encoding="utf-8-sig")` reads `.env`. The `utf-8-sig` codec tolerates a Windows-Notepad BOM; without it `AUTH_ENABLED` would parse as `﻿AUTH_ENABLED` and silently be ignored.

### 2. `initialize_managers()`
Factory in `src/app_initializer.py` — builds singletons in dependency order:

| Component | Built from | Failure mode |
|---|---|---|
| AuthManager | `core/auth.py` | Hard fail |
| Database | `DATABASE_URL`, `ODYSSEUS_MULTITENANT_POSTGRES` | Hard fail |
| Vector RAG | `QDRANT_URL`, embedding model | Degrades — keyword-only retrieval |
| Object store | `ODYSSEUS_USE_MINIO`, `MINIO_*` | Degrades — DB still works |
| Memory + skills | DB + Chroma/Qdrant | Degrades |
| MCP manager | Per-server config | Per-server failures, logged |
| Task scheduler | DB-backed | Hard fail |
| Webhook dispatcher | DB-backed | Hard fail |

Each router is registered via `setup_<name>_routes(app, deps…)` factory functions
in `routes/`, receiving the components it needs.

### 3. `startup` / `shutdown` event hooks
- **Startup**: MCP servers launched, task scheduler resumed, background monitors started (legacy owner attribution, session cleanup, log rotation).
- **Shutdown**: MCP servers cleanly stopped, scheduler checkpoints in-flight tasks, HTTP clients closed.

## Database backend switch

`core/database.py::_init_db_postgres_alembic()` vs `Base.metadata.create_all` is
the central branch:

```python
if features.infra_enabled("multitenant_postgres"):
    _init_db_postgres_alembic()    # Postgres path: alembic upgrade head
                                  # under a pg_advisory_lock so concurrent
                                  # workers converge on a single migrator.
else:
    Base.metadata.create_all(...)  # SQLite path: idempotent schema create
```

The 30+ legacy SQLite-only `_migrate_*` steps (column adds for older installs)
are skipped on the Postgres path — Alembic handles migrations there. The two
paths share the same `Base.metadata` so model definitions stay in sync. For the
migration recipe, see [`STORAGE.md`](STORAGE.md#postgresql-multi-tenant-path).

## The agent loop

`src/agent_loop.py` is a tool-using continuation loop.

```
┌─ user turn ──────────────────────────────────────────────────────────────────┐
│ 1. chat_processor: memory + skill match + web hints                         │
│ 2. build context window within token budget (context_budget.py)             │
│ 3. LLM call with tool schemas                                              │
│ 4. tool_parsing.parse(response) → list of tool calls                       │
│ 5. for each call:                                                          │
│        - tool_security.check(user, tool_name, args)                        │
│        - tool_execution.dispatch → result dict                             │
│        - format_tool_result → string (NOT a list — TypeError trap fixed)   │
│        - append result to history                                          │
│ 6. context_compactor.trim if budget exceeded                              │
│ 7. continue LLM call until: no tool calls | MAX_AGENT_ROUNDS=20 | error   │
└─────────────────────────────────────────────────────────────────────────────┘
```

Tool index (`src/tool_index.py`) retrieves which tools the LLM is allowed to
see this turn. Sources:

- `ALWAYS_AVAILABLE` — core tools the model always sees (read_file, create_document, …).
- RAG-retrieved tools — skills the user has saved that score high on the query embedding.
- Keyword hints — exact-string matches from the user message against registered tool names.

The retrieval set is then intersected with the user's permission flags
(`can_use_documents`, `can_use_shell`, `can_use_web`, …) before being sent to
the LLM. A tool that exists but the user can't call is removed from the schema
itself — so the model can't even attempt it.

`MAX_AGENT_ROUNDS=20` is a hard ceiling. A run hitting it stops with a
"user-facing 'agent hit step limit'" message rather than spinning forever.

## RAG pipeline (one-paragraph summary)

Document life-cycle:

```
upload ─→ documents table (current_content) ─→ _sync_document_to_minio ─→ ✅
                                           └─→ _ingest_document_to_rag  ─→ Qdrant
                                                 chunks → embed → upsert (UUID5 id)
```

**Important caveat:** RAG ingest is only called from **creator** paths (POST,
`import_pdf`, AI tool creators). The PUT/PATCH update paths only call
`_sync_document_to_minio` — content edits do **not** currently re-index into
Qdrant. For the full pipeline (chunking, UUID5 IDs, hybrid retrieval), see
[`RAG_PIPELINE.md`](RAG_PIPELINE.md).

## Multi-tenant ownership

Almost every model in `core/database.py` has:

```python
class Document(Base, TimestampMixin):
    ...
    owner = Column(String, index=True, nullable=True)
```

Filtering happens at the route layer:

```python
q = db.query(Document).filter(Document.owner == request.state.current_user.username)
if request.state.current_user.is_admin:
    q = q  # admin bypass
# else: enforced scoping
```

`owner=NULL` legacy rows are invisible to normal users under auth. Two safety
valves keep them recoverable:

1. `core/database.py::_migrate_assign_legacy_owner` — runs at startup, assigns
   ownerless rows to the configured admin user.
2. `scripts/claim_ownerless.py` — operator CLI to re-assign ownerless rows to
   any user.

See [`STORAGE.md`](STORAGE.md#multi-tenant-ownership) for which tables carry
the `owner` column and how MinIO/Qdrant enforce the same partition.

## Testing

Tests live in `tests/` with pytest-asyncio style (`asyncio_mode = "auto"` in
`pyproject.toml`). `conftest.py` stubs heavy / impossible deps
(`sqlalchemy`, `bcrypt`, `httpx`, `fastapi`) at module level so unit tests run
without a working DB / GPU / network.

Run:
```bash
pytest                                  # all
pytest tests/test_specific_file.py -v   # one file
pytest tests/ -k "test_name_substring"  # by name match
```

## Where to make changes

| If you want to… | Edit |
|---|---|
| Add an LLM provider | `src/llm_core.py` + admin UI under `static/js/` |
| Add a tool the agent can call | `src/agent_tools.py` + `src/tool_implementations.py` |
| Add a per-user filter / privilege | `src/tool_security.py` + `core/auth.py` |
| Migrate schema | Postgres: add an Alembic revision. SQLite: edit `_migrate_*` in `core/database.py`. |
| Add a route | new file `routes/<feature>_routes.py` + `setup_<feature>_routes()` factory in `app.py` |
| Add a Cron task trigger | `src/task_scheduler.py` + `routes/task_routes.py` |
| Change CSP nonce / headers | `core/middleware.py::SecurityHeadersMiddleware` |
| Change embeddings source | `.env` (`LOCAL_EMBEDDING_PATH` / `EMBEDDING_URL`); logic in `src/embeddings.py` |
