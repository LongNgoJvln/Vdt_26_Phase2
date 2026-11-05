# VHT Network Automation — Design Patterns

## Singleton

Immutable or mutable singletons initialized once and used globally.

```mermaid
flowchart LR
    subgraph Singletons["Global Singletons"]
        FF["FeatureFlags\nfeature_flags.py"]
        AC["AppConfig\nconfig.py"]
        AU["AuthManager\nauth.py"]
        MM["MCPManager\nmcp_manager.py"]
        EB["EventBus\nevent_bus.py"]
    end

    subgraph Consumers["Consumers"]
        RT["Routes"]
        SR["Services"]
        MW["Middleware"]
    end

    FF --> RT
    FF --> MW
    AC --> SR
    AU --> MW
    AU --> RT
    MM --> SR
    EB --> SR
```

### FeatureFlags (`core/feature_flags.py`)

Immutable after construction. Read from env vars at import time.

```python
class FeatureFlags:
    """Immutable after construction. Read from env at import time."""
    chat = True
    agent_mode = True
    research = True
    # ... (20+ feature flags)

features = FeatureFlags()  # Global singleton
```

- `ODYSSEUS_DEPLOY_MODE=minimal` or `enterprise` sets defaults
- `ODYSSEUS_FEATURE_<NAME>` overrides individual flags
- Runtime updates via PATCH `/api/features` use `object.__setattr__` on the singleton:

```python
@app.patch("/api/features")
async def update_features(payload: dict):
    for key, value in payload.items():
        if hasattr(features, key):
            object.__setattr__(features, key, value)
    # Persist to features.json
```

### AppConfig (`src/config.py`)

```python
class AppConfig(BaseSettings):
    llm: LLMConfig = LLMConfig()
    search: SearchConfig = SearchConfig()
    # ...

config = AppConfig()  # Global singleton
```

Pydantic-settings-based. Validates at startup with type checking.

### AuthManager (`core/auth.py`)

Created once in `app.py`, accessed via `request.app.state.auth_manager`. Not a module-level singleton — attached to app state for lifecycle management.

### MCPManager (`src/mcp_manager.py`)

Set once via `set_mcp_manager()`. Lazy singleton accessed from routes. Provides connection pooling for MCP server processes.

### EventBus (`src/event_bus.py`)

Module-level singleton used for in-process pub/sub. Subscribers register at startup; events are fired from route handlers.

---

## Factory Pattern

### `initialize_managers()` (`src/app_initializer.py`)

```mermaid
flowchart LR
    subgraph Products["Returns dict of services"]
        SM["SessionManager"]
        MM2["MemoryManager"]
        CP["ChatProcessor"]
        CH["ChatHandler"]
        RH["ResearchHandler"]
        MD["ModelDiscovery"]
        UH["UploadHandler"]
        RD["PersonalDocsManager"]
        PM["PresetManager"]
        SKM["SkillsManager"]
    end

    subgraph Inject["Injected Into"]
        RC["setup_chat_routes()"]
        RM2["setup_memory_routes()"]
        RS["setup_research_routes()"]
        RR["setup_session_routes()"]
    end

    FACTORY --> PRODUCTS
    PRODUCTS --> INJECT
    SM --> RC
    SM --> RR
    MM2 --> RM2
    CH --> RC
    CP --> RC
    RH --> RS
    MD --> MODEL
```

Returns a dictionary of all initialized services. Dependencies injected into route setup functions:

```python
# app.py
from src.app_initializer import initialize_managers

managers = initialize_managers(config)
app.include_router(setup_chat_routes(
    managers["session_manager"],
    managers["chat_handler"],
    managers["chat_processor"],
    managers["chat_history"],
    managers["model_discovery"],
    managers["auth_manager"],
))
```

This pattern makes dependencies explicit and testable — each route can be tested with mock managers.

---

## Dependency Injection via Factory Functions

```mermaid
graph LR
    subgraph Factory["setup_<name>_routes() Factory"]
        F1["setup_auth_routesauth_manager"]
        F2["setup_chat_routes(session_mgr,\nchat_handler, chat_processor, ...)"]
        F3["setup_memory_routes(memory_mgr,\nsession_mgr, memory_vector)"]
        F4["setup_mcp_routes(mcp_manager)"]
        F5["setup_model_routes(model_discovery)"]
        F6["setup_session_routes(session_mgr,\nconfig, webhook_manager)"]
    end

    subgraph Output["Returns APIRouter"]
        API1["auth router"]
        API2["chat router"]
        API3["memory router"]
        API4["MCP router"]
        API5["model router"]
        API6["session router"]
    end

    F1 --> API
    F2 --> API2
    F3 --> API3
    F4 --> API4
    F5 --> API5
    F6 --> API6
```

All routes are registered via factory functions that receive their dependencies:

```python
setup_auth_routes(auth_manager: AuthManager) -> APIRouter
setup_chat_routes(session_manager, chat_handler, chat_processor, ...) -> APIRouter
setup_memory_routes(memory_manager, session_manager, memory_vector) -> APIRouter
setup_mcp_routes(mcp_manager: McpManager) -> APIRouter
setup_model_routes(model_discovery) -> APIRouter
setup_session_routes(session_manager, config, webhook_manager) -> APIRouter
```

Benefits:
- Avoids global imports in route files (testable with mocks)
- Makes dependencies explicit at a glance
- Enables lazy initialization of expensive components
- Simplifies testing — pass `MagicMock()` instances:

```python
def test_chat_route():
    mock_sm = MagicMock()
    mock_ch = MagicMock()
    router = setup_chat_routes(mock_sm, mock_ch, ...)
    # Test the route
```

---

## Facade Pattern

### Tool System (`src/agent_tools.py`)

```mermaid
flowchart LR
    subgraph Client["Consumers"]
        AG["agent_loop.py"]
        CH2["chat_handler.py"]
        T["tool routes"]
    end

    subgraph Facade["agent_tools.py (Facade)"]
        AT["Unified import point\nRe-exports all tool modules"]
    end

    subgraph Subsystems["Internal Modules"]
        TP["tool_parsing.py\n5-format parser"]
        TSC["tool_schemas.py\n30+ function schemas"]
        TE["tool_execution.py\nDispatcher"]
        TI["tool_implementations.py\ndo_* functions"]
        TS2["tool_security.py\nAdmin blocks"]
    end

    AG --> AT
    CH2 --> AT
    T --> AT
    AT --> TP
    AT --> TS2
    AT --> TE
    AT --> TI
    AT --> SC5
```

Re-exports from `tool_parsing.py`, `tool_schemas.py`, `tool_execution.py`, and `tool_implementations.py` as a unified facade. Consumers import from `agent_tools` without knowing about the internal modules:

```python
# Consumers don't need to know the module structure
from src.agent_tools import (
    parse_tool_calls,       # From tool_parsing.py
    execute_tool_block,     # From tool_execution.py
    get_tool_schemas,       # From tool_schemas.py
    do_read_file,           # From tool_implementations.py
    blocked_tools_for_owner,# From tool_security.py
)
```

---

## Lazy Initialization

```mermaid
flowchart TD
    REQUEST["First Request Needs\nRAG / Embeddings / PDF"]

    REQUEST --> CHECK{"Instance exists?"}

    CHECK -->|No| INIT["Lazy Initialization"]
    INIT --> RAG2["get_rag_manager()\ntries HTTP ChromaDB → local"]
    INIT --> EMB2["get_embedding_client()\nHTTP API → ONNX → fastembed"]
    INIT --> PDF2["load_pymupdf()\nPDF viewer runtime"]

    CHECK -->|Yes| USE["Return cached instance"]
    RAG2 --> USE
    EMB2 --> USE
    PDF2 --> USE

    USE --> RESP["Process Request"]
```

### RAG Manager (`src/rag_singleton.py`)

RAG managers are scoped per user so that one user's document corpus is never visible to another. `get_rag_manager_for_user(user_id)` (`src/rag_singleton.py:63`) lazily builds a `VectorRAG` backed by a ChromaDB collection `ody-rag-{user_id}` and a persistence directory `data/userdata/{user_id}/rag`.

```python
def get_rag_manager_for_user(user_id):
    # 1. Resolve the per-user data dir → data/userdata/{user_id}/rag
    # 2. Lazy init a VectorRAG manager bound to that dir
    # 3. Return cached instance on subsequent calls
```

`get_rag_manager()` (`src/rag_singleton.py:125`) is a backward-compatible alias that delegates to `get_rag_manager_for_user(user_id=None)`.

Benefits:
- Reduces startup time (ChromaDB connection is deferred)
- Per-user isolation enforced at the collection level
- Graceful degradation (falls back through backends)

### Embedding Client (`src/embeddings.py`)

```python
_embedding_client = None

def get_embedding_client():
    """Tries HTTP API first, falls back through ONNX → fastembed."""
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = _create_embedding_client()
    return _embedding_client

def _create_embedding_client():
    """Fallback chain: HTTP → ONNX → fastembed."""
    if EMBEDDING_URL:
        return HTTPEmbeddingClient(EMBEDDING_URL, EMBEDDING_MODEL)
    try:
        return ONNXEmbeddingClient()
    except ImportError:
        return FastembedClient()
```

### PDF Runtime (`src/pdf_runtime.py`)

```python
_pymupdf = None

def load_pymupdf_for_pdf_viewer():
    """Loaded on-first PDF render. PyMuPDF is a heavy import."""
    global _pymupdf
    if _pymupdf is None:
        import fitz  # heavy import deferred
        _pymupdf = fitz
    return _pymupdf
```

---

## Event-Driven Architecture

```mermaid
sequenceDiagram
    participant Action as Action Handler
    participant EB as EventBus
    participant TS2["Task Scheduler"]
    participant WM["Webhook Manager"]
    participant BG as Background Jobs

    Action->>EB: fire_event("session_created", owner)
    par Task Scheduler
        EB->>TS2: Subscribe: session_created
        TS2->>TS2: Execute configured task
        TS2-->>EB: Task result
    and Webhook Manager
        EB->>WM: Subscribe: session_created
        WM->>WM: Fire-and-forget HTTP POST
        WM-->>EB: Dispatched
    and Background Jobs
        EB->>BG: Subscribe: document_created
        BG->>BG: Schedule background job
        BG-->>EB: Scheduled
    end
```

### EventBus (`src/event_bus.py`)

`src/event_bus.py` is **not** a generic in-process pub/sub — there is no subscriber callback list. It is a DB-driven task trigger. Module-level `fire_event(event_name, owner)` (`src/event_bus.py:31`) schedules `_handle_event(...)` on the running loop. `_handle_event` queries the DB for `ScheduledTask` rows whose `trigger_event` matches the fired event, increments each task's `trigger_counter`, and — once the counter reaches the task's configured `trigger_count` threshold — calls `_task_scheduler.run_task_now(task.id)`.

```python
# src/event_bus.py
def fire_event(event_name: str, owner: Optional[str] = None):
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_handle_event(event_name, owner))
    except RuntimeError:
        asyncio.run(_handle_event(event_name, owner))
```

`fire_event` is safe to call from sync routes (running in the FastAPI threadpool) and from async routes (running on the event loop). Events published by route handlers:

| Event | Triggered When | Data Payload |
|---|---|---|
| `session_created` | New chat session | `{"sid": "...", "owner": "..."}` |
| `message_sent` | Message sent to LLM | `{"sid": "...", "message": {...}}` |
| `document_created` | New document created | `{"doc_id": "...", "owner": "..."}` |
| `memory_added` | Memory entry added | `{"memory_id": "...", "content": "..."}` |

Owner-less events resolve to the first admin user (`_resolve_event_owner`, `src/event_bus.py:44-69`) — this avoids the previous behaviour where app-level events fired every user's tasks once per account.

### Background Job Monitor (`bg_monitor`)

Watches for background bash (`#!bg`) subprocess completion. When a job finishes, it reinjects the output into the agent loop via the session manager:

```python
async def bg_monitor_loop():
    while True:
        for job in active_bg_jobs:
            if job.process.poll() is not None:
                output = job.process.stdout.read()
                await reinject_output(job.sid, output)
                active_bg_jobs.remove(job)
        await asyncio.sleep(1)
```

### Webhook Manager (`src/webhook_manager.py`)

Reacts to events and dispatches HTTP POSTs to configured endpoints:

- `session.created`
- `message.sent`
- Research completion
- Custom events

Webhooks include HMAC signature headers for receiver verification:

```python
async def dispatch_webhook(url: str, event: str, payload: dict):
    body = json.dumps({
        "event": event,
        "data": payload,
        "timestamp": datetime.utcnow().isoformat(),
    })
    signature = hmac.new(SECRET.encode(), body.encode(), "sha256").hexdigest()
    await httpx.AsyncClient().post(url, content=body, headers={
        "X-VHTNA-Event": event,
        "X-VHTNA-Signature": signature,
        "User-Agent": "VHTNA-Webhook",
    })
```

---

## In-Memory Caching with Invalidation

```mermaid
flowchart TD
    subgraph Caches["In-Memory Caches"]
        CT["API Token Cache\nprefix-based lookup"]
        CR["LLM Response Cache\n128-entry LRU"]
        CS2["Settings/Features Cache\n2s TTL"]
        CM2["Model Cache\n30s TTL, per-user"]
        CI["Tool Index\npre-warmed at startup"]
    end

    subgraph Writers["Invalidation Triggers"]
        W1["Token cache dirty flag"]
        W2["Background probe refresh"]
        W3["Endpoint CRUD"]
        W4["Feature toggle PATCH"]
    end

    CT -.->|"invalidate_token_cache"| W1
    CM2 -.->|probe refresh| W2
    CI -.->|endpoint change| W3
    CS2 -.->|feature toggle| W4

    subgraph Benefits["Benefits"]
        B1["Avoid bcrypt on every request"]
        B2["Skip duplicate LLM calls"]
        B3["No disk reads per request"]
        B4["Instant model list"]
        B5["Agent tools ready instantly"]
    end

    CT --> B1
    CR --> B2
    CS2 --> B3
    CM2 --> B4
    CI --> B5
```

### Cache Details

| Cache | TTL | Invalidation | Purpose |
|---|---|---|---|
| API Token | dirty flag | explicit `invalidate_token_cache()` | Avoid bcrypt on every request |
| LLM Response | 128-entry LRU | N/A (implicit eviction) | Skip duplicate LLM calls |
| Settings/Features | 2s | on write | No disk reads per request |
| Model List | 30s, per-user | background refresh | Instant model picker |
| Tool Index | pre-warm | endpoint CRUD | Agent tools ready instantly |

### API Token Cache

```python
_token_cache: dict[str, CachedToken] = {}
_token_cache_dirty = False

def get_cached_token(prefix: str) -> CachedToken | None:
    if _token_cache_dirty:
        _token_cache.clear()
        _token_cache_dirty = False
    return _token_cache.get(prefix)

def set_cached_token(prefix: str, token: CachedToken):
    _token_cache[prefix] = token

def invalidate_token_cache():
    global _token_cache_dirty
    _token_cache_dirty = True
```

### LLM Response Cache

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def cached_llm_call(messages_hash: str, **params):
    # Only used for non-streaming, idempotent calls
    ...
```

---

## Dead-Host Cooldown

```mermaid
flowchart TD
    A["LLM Request to Host"] --> B{"Host alive?"}
    B -->|Yes| C["Clear failure counter"] --> RESP["Return response"]
    B -->|No| D{"Consecutive failures >= 2?"}
    D -->|No| E["Increment counter"] --> F{"More fallbacks?"}
    D -->|Yes| G{"Cooldown period < 20s?"}
    G -->|No| H["Mark host DEAD"] --> I["Skip for 20 seconds"] --> F
    G -->|Yes| J["Still cooling down"] --> F
    E --> F
    F -->|Yes| K["Try next fallback"] --> A
    F -->|No| L["Return error to caller"]

    classDef alive fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    classDef dead fill:#ffcdd2,stroke:#c62828,stroke-width:2px
    classDef neutral fill:#fff9c4,stroke:#f57f17,stroke-width:2px

    class C,B alive
    class H,I dead
    class A,D,E,F,G,J,K,L neutral
```

- Tracks consecutive failures per LLM host via in-memory dict
- Only marks hosts dead after threshold (2 consecutive failures)
- 20-second cooldown before retrying dead hosts
- Used in `llm_call_with_fallback()` and `stream_llm_with_fallback()`

```python
# src/llm_core.py:144-153 — failure tracking guarded by a Lock
DEAD_HOST_COOLDOWN = 20.0
_HOST_FAIL_THRESHOLD = 2
_dead_hosts: Dict[str, float] = {}
_host_fails: Dict[str, int] = {}
_host_health_lock = threading.Lock()

async def stream_llm_with_fallback(messages, endpoints, **kwargs):
    for endpoint in endpoints:
        if _is_host_dead(endpoint.url):
            continue
        try:
            async for chunk in stream_llm(messages, endpoint, **kwargs):
                yield chunk
            _record_success(endpoint.url)
            return
        except Exception:
            _record_failure(endpoint.url)
    raise LLMServiceError("All endpoints failed")
```

The synchronous `llm_call()` runs inside FastAPI's threadpool (used by sync routes like `/sessions/auto-sort`) while `llm_call_async()` runs on the event loop. Without the lock, the read-modify-write on `_host_fails` lost failure counts under concurrent connect errors (issue #659).

---

## Multi-Tenant Ownership

### Owner Column Pattern

```mermaid
flowchart TD
    REQ["Request with User ID"] --> FIND2["Query DB for resource"]
    FIND --> OWNER2{"Owner matches\ncurrent_user?"]
    OWNER2 -->|Yes| ALLOW["Proceed with request"]
    OWNER2 -->|No| DENY["404 Not Found"]
```

**404-not-403**: Ownership violations return 404 (not found), never 403 (forbidden), to avoid leaking the existence of resources belonging to other users.

### Owner Filter Helper

```python
def owner_filter(query, model, owner):
    """Filter query by owner. NULL-owner rows are shared."""
    return query.filter(
        or_(model.owner == owner, model.owner.is_(None))
    )
```

```mermaid
flowchart TD
    subgraph Query["DB Query Construction"]
        Q1["Base query"]
        Q2{"Owner filter"}
        Q3["model.owner == current_user"]
        Q4["model.owner IS NULL"]
        Q5["OR Q3, Q4"]
    end

    subgraph Result["Results"]
        R1["User's owned rows"]
        R2["NULL-owner shared/legacy rows"]
        R3["Other users' rows (excluded)"]
    end

    Q1 --> Q2
    Q2 --> Q3
    Q2 --> Q4
    Q3 --> Q5
    Q4 --> Q5
    Q5 --> R1
    Q5 --> R2

    classDef include fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    classDef exclude fill:#ffcdd2,stroke:#c62828,stroke-width:2px

    class R1,R2 include
    class R3 exclude
```

### Legacy Owner Migration

`_migrate_assign_legacy_owner()` runs at startup and hourly:

```mermaid
flowchart LR
    START2["Startup / Hourly"] --> FIND3["Find all NULL-owner rows"]
    FIND --> ADMIN["Get first admin user"]
    ADMIN --> ASSIGN["Set owner = admin"]
    ASSIGN --> DONE["All rows ownership-assigned"]
```

```python
def _migrate_assign_legacy_owner():
    """Assign null-owner rows to first admin user."""
    admin = db.query(User).filter(User.is_admin == True).first()
    if not admin:
        return
    for model in ALL_OWNER_MODELS:
        rows = db.query(model).filter(model.owner.is_(None)).all()
        for row in rows:
            row.owner = admin.username
    db.commit()
```

---

## CSP Nonce Pattern

```mermaid
sequenceDiagram
    participant REQ as Request
    participant MW as SecurityHeadersMiddleware
    participant STATE as request.state
    participant HTML as HTML Page
    participant BROWSER as Browser

    REQ->>MW: Incoming request
    MW->>MW: Generate random nonce\nbase64.token_bytes(32)
    MW->>STATE: Store request.state.csp_nonce
    MW->>HTML: Set CSP header with nonce
    HTML->>HTML: Replace {{CSP_NONCE}}\nwith actual nonce
    HTML->>BROWSER: Render HTML with nonce
    BROWSER->>BROWSER: CSP validates inline scripts\nonly if nonce matches
```

Provides defense-in-depth: CSP blocks inline scripts without a valid nonce, even if XSS vulnerabilities exist.

```python
# core/middleware.py
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        nonce = base64.b64encode(secrets.token_bytes(16)).decode()
        request.state.csp_nonce = nonce
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            f"script-src 'nonce-{nonce}' 'strict-dynamic'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response
```

---

## Template Method (Route Registration)

```mermaid
flowchart TD
    subgraph Features["Feature Flags"]
        FC2["features.chat"]
        FCA["features.calendar"]
        FE2["features.email"]
        FR2["features.research"]
        FN2["features.memory"]
        FGA["features.gallery"]
        FN3["features.notes"]
        FMO2["features.tasks"]
    end

    subgraph Register["app.py — Conditional Registration"]
        IF1["if features.chat:"]
        IF2["if features.calendar:"]
        IF3["if features.email:"]
        IF4["if features.research:"]
        IF5["if features.memory:"]
        IF6["if features.gallery:"]
        IF7["if features.notes:"]
        IF8["if features.tasks:"]
    end

    subgraph Routers["APIRouters Added"]
        CH3["chat_router"]
        CA2["calendar_router"]
        EM2["email_router"]
        RS2["research_router"]
        MB3["memory_router"]
        GA2["gallery_router"]
        NO2["notes_router"]
        TA2["tasks_router"]
    end

    FC2 --> IF1 --> CH3
    FCA --> IF2 --> CA2
    FE2 --> IF3 --> EM2
    FR2 --> IF4 --> RS2
    FN2 --> IF5 --> MB3
    FGA --> IF6 --> GA2
    FN3 --> IF7 --> NO2
    FMO2 --> IF8 --> TA2

    classDef feat fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef reg fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef rout fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px

    class FC2,FCA,FE2,FR2,FN2,FGA,FN3,FMO2 feat
    class IF1,IF2,IF3,IF4,IF5,IF6,IF7,IF8 reg
    class CH3,CA2,EM2,RS2,MB3,G2,NO2,TA2 rout
```

```python
# app.py — conditional route registration
if features.chat:
    app.include_router(setup_chat_routes(...))
if features.calendar:
    app.include_router(setup_calendar_routes(...))
if features.email:
    app.include_router(setup_email_routes(...))
# ... etc.
```

---

## Circuit Breaker (Endpoint Probing)

```mermaid
flowchart TD
    CHECK{"Endpoint in\nprobe cycle?"}
    CHECK --> LOOK2["Check probe_failures map"]
    LOOK --> COND{"Fails >= 3 AND\nlast fail < 5 min ago?"}
    COND -->|Yes| BACK["Back off\nSkip this endpoint"]
    COND -->|No| PROB["Probe endpoint\n2s timeout"]
    PROB --> RESP{"Probe success?"}
    RESP -->|Yes| CLEAR["Clear failure counter"]
    RESP -->|No| INCR["Increment counter"]
    BACK --> NEXT["Next endpoint"]
    CLEAR --> NEXT
    INCR --> NEX2
```

Model endpoint probing uses a failure counter with backoff. Implemented in `model_discovery.py`:

```python
probe_failures: dict[str, int] = {}
last_probe_fail: dict[str, float] = {}

def should_skip_probe(endpoint_id: str) -> bool:
    fails = probe_failures.get(endpoint_id, 0)
    last_fail = last_probe_fail.get(endpoint_id, 0)
    if fails >= 3 and (time.monotonic() - last_fail) < 300:  # 5 min
        return True
    return False
```

---

## Context Management

```mermaid
flowchart TD
    subgraph Budget["context_budget.py"]
        B1["Track token usage\nper round"]
        B2{"Approaching\nbudget limit?"]
    end

    subgraph Compactor["context_compactor.py"]
        COMP["Self-summary compaction"]
        SUM2["Summarize old messages"] --> KEEP["Keep recent\n8 messages verbatim"]
        COMB["Merge summary +\nrecent → new history"]
    end

    subgraph Preface["chat_processor.py\nContext Preface Layers"]
        L1["1. Preset system prompt"]
        L2["2. Prompt safety policy"]
        L3["3. Pinned memories +\nvector/search memories"]
        L4["4. RAG results"]
        L5["5. Web search results"]
        L6["6. URL content"]
        L7["7. Skills index\n(agent mode only)"]
    end

    B1 --> B2
    B2 -->|Yes| COMP
    B2 -->|No| PREFACE
    COMP --> SUMM
    SUM --> KEEP
    KEEP --> COMB

    L1 --> L2 --> L3 --> L4 --> L5 --> L6 --> L7
```

### Context Budget

`src/context_budget.py:21` exposes a pure function `compute_input_token_budget(configured, context_length, explicit, ...)` that returns the effective soft input-token budget:

- Explicit user budget → honoured exactly (clamped to the model's window when known)
- Otherwise → `headroom` (0.85) of the model's discovered context window, capped at `DEFAULT_HARD_MAX = 200_000`
- Unknown window → fall back to the configured/default value (`DEFAULT_BUDGET = 6000`)

```python
# src/context_budget.py
DEFAULT_HARD_MAX = 200_000
DEFAULT_BUDGET = 6000
DEFAULT_HEADROOM = 0.85

def compute_input_token_budget(configured, context_length, explicit, *,
                                default=DEFAULT_BUDGET,
                                headroom=DEFAULT_HEADROOM,
                                hard_max=DEFAULT_HARD_MAX) -> int:
    if explicit and configured > 0:
        return min(configured, context_length) if context_length > 0 else configured
    if context_length > 0:
        return max(1, min(int(context_length * headroom), hard_max))
    return configured if configured > 0 else default
```

### Context Compactor

`src/context_compactor.py` summarizes older conversation history when usage crosses `COMPACT_THRESHOLD = 0.85` (85% of the model's context window). The summary is produced via the same LLM using `SELF_SUMMARY_SYSTEM_PROMPT`, which yields a Cursor-style structured summary: **User Goal**, **What Was Done**, **Current State**, **Pending / Next Steps**, **Key Context**.

```python
# src/context_compactor.py
COMPACT_THRESHOLD = 0.85
SELF_SUMMARY_SYSTEM_PROMPT = """You are summarizing a conversation to preserve context after compaction. ..."""

async def maybe_compact(session, endpoint_url, model, messages, headers=None):
    context_length = get_context_length(endpoint_url, model)
    used = estimate_tokens(messages)
    pct = (used / context_length) * 100 if context_length else 0
    if pct < COMPACT_THRESHOLD * 100:
        return messages, context_length, False
    # split into older / recent halves, summarize older, splice summary into session.history
```

---

## Stream Safety (Partial Save)

```mermaid
sequenceDiagram
    participant CLIENT as Client
    participant ROUTE as route handler
    participant STREAM as _active_streams dict
    participant DB as Database

    ROUTE->>STREAM: Register session\nstatus="streaming"

    loop Stream tokens
        ROUTE->>CLIENT: SSE delta event
        ROUTE->>STREAM: _stream_set(partial=text)
    end

    alt Client disconnect
        CLIENT-x>ROUTE: Connection lost
        ROUTE->>STREAM: Check partial text
        ROUTE->>DB: Save partial response
        ROUTE->>STREAM: Remove session entry
    end

    end

    ROUTE->>STREAM: Remove on [DONE]
```

```python
# Active stream tracking
_active_streams: dict[str, dict] = {}

def _stream_set(sid: str, **kwargs):
    if sid in _active_streams:
        _active_streams[sid].update(kwargs)

def _stream_get(sid: str) -> dict | None:
    return _active_streams.get(sid)

async def on_disconnect(sid: str):
    stream = _stream_get(sid)
    if stream and stream.get("partial"):
        await save_partial_message(sid, stream["partial"])
    _active_streams.pop(sid, None)
```

---

## Provider-Specific Normalization

```mermaid
flowchart TD
    subgraph Input["Raw Messages"]
        MSG["Chat Messages"]
    end

    subgraph Detect["Provider Detection"]
        D{"From URL"}
    end

    subgraph Formats["Normalized Formats"]
        OA["OpenAI\nStandard chat format"]
        AN["Anthropic\nSystem msg extraction\ntool_use/tool_result"]
        OL["Ollama\nNative format\ntool schema adaptation"]
        OR2["OpenRouter\nOpenAI format\nprefix handling"]
        GR["Groq\nOpenAI format\nspecific capabilities"]
    end

    subgraph Output["HTTP Request"]
        OUT["Provider-specific HTTP call"]
    end

    MSG --> D
    D --> OA
    D --> AN
    D --> OL
    D --> OR2
    D --> GR

    OA --> OUT
    AN --> OUT
    OL --> OUT
    OR2 --> OUT
    GR --> OUT

    classDef input fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef format fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef output fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px

    class MSG input
    class OA,AN,OL,OR2,GR format
    class OUT output
```

```python
# endpoint_resolver.py — provider detection
def detect_provider(url: str) -> str:
    url_lower = url.lower()
    if "anthropic" in url_lower:
        return "anthropic"
    if "ollama" in url_lower:
        return "ollama"
    if "openrouter" in url_lower:
        return "openrouter"
    if "groq" in url_lower:
        return "groq"
    return "openai"  # default / OpenAI-compatible
```

Each provider has a normalization function in `llm_core.py` that converts the internal message format to the provider's expected wire format.