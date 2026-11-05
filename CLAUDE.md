# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run development server
python -m uvicorn app:app --host 127.0.0.1 --port 7000

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-optional.txt  # optional extras

# Run tests
pytest
pytest tests/test_specific_file.py -v
pytest tests/ -k "test_name_substring"

# Database setup
python setup.py

# Docker
docker compose up -d --build
docker compose logs --tail=120 odysseus

# macOS native
./start-macos.sh

# Windows native
.\launch-windows.ps1

# GPU diagnostic (Docker)
scripts/check-docker-gpu.sh
```

## Architecture

**VHT Network Automation** is a self-hosted AI workspace — a FastAPI Python server that serves a frontend SPA and exposes REST + streaming endpoints.

### Directory Layout

```
app.py              # FastAPI entry point — middleware stack, startup/shutdown, router registration
core/               # Foundation layer (no dependency on src/ or routes/)
  database.py       #   SQLAlchemy models + schema migrations (all run at init_db())
  auth.py           #   AuthManager — password hashing, token management, user CRUD
  middleware.py     #   RequestIdMiddleware, SecurityHeadersMiddleware
  constants.py      #   BASE_DIR, DATA_DIR, env defaults
  feature_flags.py  #   FeatureFlags singleton — deploy-mode + env-var gating
  exceptions.py     #   SessionNotFoundError, LLMServiceError, etc.
  response_types.py #   Standard JSON response helpers
  models.py         #   Pydantic request/response schemas
  session_manager.py#   Session CRUD (legacy JSON-based, now superseded by DB)
src/                # Business logic
  llm_core.py       #   LLM call dispatch — sync/async HTTP, streaming, caching, dead-host detection
  agent_loop.py     #   Agent loop — tool selection, execution, continuation
  agent_tools.py    #   Tool definitions exposed to the agent
  chat_processor.py #   Chat message processing — memory retrieval, web search, skill matching
  chat_handler.py   #   Chat session orchestration — create/continue/stream messages
  memory.py         #   Memory manager — persistent key-value + keyword retrieval
  memory_vector.py  #   ChromaDB vector memory
  settings.py       #   User/admin settings load/save
  task_scheduler.py #   Cron-style + event-driven task scheduler
  mcp_manager.py    #   MCP server lifecycle (stdio/SSE/HTTP)
  rag_manager.py    #   Personal document RAG (ChromaDB)
  rag_singleton.py  #   Lazy RAG manager init
  tool_index.py     #   Tool retrieval for agent (vector + keyword)
  search/           #   Web search (SearXNG + direct fallback)
  agent_runs.py     #   Background agent execution (deep research, etc.)
  database.py       #   DB helper functions (separate from core/database.py models)
  config.py         #   App configuration
  app_initializer.py#   Component initialization factory
  app_helpers.py    #   Utility helpers
  auth_helpers.py   #   Request-level auth helpers (get_current_user)
  event_bus.py      #   In-process event pub/sub (webhook triggers, task events)
  webhook_manager.py#   Outbound webhook dispatch
  secret_storage.py #   Fernet encryption for DB secrets
  embeddings.py     #   ONNX embedding model for vector search
  chroma_client.py  #   ChromaDB HTTP client
  prompt_security.py#   Untrusted content guard (prompt injection)
  context_budget.py #   Token budget management for agent turns
  context_compactor.py # Message history compression
  model_discovery.py#   LLM endpoint model list discovery
  model_context.py  #   Context length mappings per model
  endpoint_resolver.py # Endpoint URL resolution
  tool_execution.py #   Tool call execution engine
  tool_implementations.py # Built-in tool implementations
  tool_parsing.py   #   Tool call parsing from LLM responses
  tool_schemas.py   #   Tool JSON schemas
  tool_security.py  #   Tool access control
  search/           #   Web search implementation
  document_actions.py  # Document CRUD actions
  document_processor.py # Document processing pipeline
  upload_handler.py #   File upload handler
  preset_manager.py #   Chat preset management
routes/             # FastAPI APIRouters, one per feature area
  auth_routes.py    #   Login/signup/setup/logout/session
  chat_routes.py    #   Chat send, stream, suggest, title generation
  session_routes.py #   Session CRUD, list, archive, sort
  memory_routes.py  #   Memory CRUD
  skills_routes.py  #   Skill definitions + audit
  research_routes.py#   Deep research start/status/results
  document_routes.py#   Document CRUD + versions
  email_routes.py   #   IMAP/SMTP email
  calendar_routes.py#   CalDAV sync + event management
  note_routes.py    #   Notes/todos CRUD
  task_routes.py    #   Scheduled task CRUD + webhook trigger
  model_routes.py   #   Model endpoint management
  gallery_routes.py #   Image gallery
  mcp_routes.py     #   MCP server CRUD
  webhook_routes.py #   Webhook CRUD
  preset_routes.py  #   Preset CRUD
  api_token_routes.py # API token management
  ... (one file per feature)
services/           # External service integrations
static/             # Frontend SPA (HTML + CSS + JS modules)
tests/              # Pytest test files (one file per feature area)
data/               # Runtime data (gitignored) — app.db, auth.json, settings.json, uploads/
```

### Key Patterns

**App initialization** (`app.py`): FastAPI app with layered middleware (RequestId → CORS → SecurityHeaders → RequestTimeout → Auth). Components initialized via `initialize_managers()`. Routes registered as `setup_<name>_routes()` factory functions that receive their dependencies. Startup/shutdown lifecycle hooks for MCP, task scheduler, background monitors.

**Auth system** (`core/auth.py`, `app.py`): Cookie-based session auth + Bearer API tokens (`ody_*`). In-memory token cache with invalidation flag. LOCALHOST_BYPASS gate for loopback (guarded against proxy spoofing). Middleware checks exempt paths, API tokens, session cookies in order.

**Feature flags** (`core/feature_flags.py`): Immutable singleton read from env vars at import time. Two deploy modes: `enterprise` (all on) and `minimal` (only research/documents/settings). `OFFLINE_MODE` disables internet features. Individual `ODYSSEUS_FEATURE_*` env vars override everything. Routes and UI panels gate on these.

**Database** (`core/database.py`): SQLAlchemy with SQLite default. Models: Session, ChatMessage, Document, DocumentVersion, Memory, EmailAccount, ModelEndpoint, McpServer, ScheduledTask, TaskRun, GalleryImage, GalleryAlbum, Note, CalendarCal, CalendarEvent, Comparison, Signature, ApiToken, Webhook, UserTool, CrewMember, EditorDraft, Integration. All schema migrations run at startup via `init_db()`.

**LLM dispatch** (`src/llm_core.py`): OpenAI-compatible HTTP calls. Dead-host cooldown (tracks consecutive failures per host). Optional response cache. Configurable timeout, temperature, max_tokens. Streaming support.

**Agent loop** (`src/agent_loop.py`): Tool-based agent with max-step limit, tool result handling, context budget enforcement. Skills, MCP tools, and built-in tools all feed into `tool_index.py` for retrieval.

**Testing pattern**: Tests live in `tests/` with `conftest.py` that stubs heavy/impossible deps (sqlalchemy, bcrypt, httpx, fastapi) at module level. Tests are pytest-asyncio style (no `@pytest.mark.asyncio` needed if test is async; `asyncio_mode = "auto"` in pyproject.toml).

**Datetime convention**: Python floor 3.10 — no 3.11+ datetime APIs. All datetimes are aware-UTC via `core/time_utils.py` (`utcnow()`, never `datetime.utcnow()`). Columns use `UtcDateTime` (naive-UTC storage, aware reads). API output serializes through `iso_utc()` (trailing `Z`). Legacy TEXT stores and calendar wall-times use `utcnow_naive()`.

**Multi-tenant ownership**: Almost every DB table has an `owner` column (username string). Routes filter by `request.state.current_user`. Admin users bypass owner filters. Legacy null-owner data is periodically assigned to the admin user (`_migrate_assign_legacy_owner`).

**CSP + Nonce pattern**: HTML pages are served with a CSP nonce injected via `{{CSP_NONCE}}` template replacement. The nonce is set by `SecurityHeadersMiddleware` on each request.