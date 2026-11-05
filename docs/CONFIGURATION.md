# Configuration Reference

All runtime config is read from `.env` at app startup
(`app.py::load_dotenv(encoding="utf-8-sig")`). The `utf-8-sig` codec tolerates
a UTF-8 BOM — a common Windows/Notepad gotcha that would otherwise silently
ignore the first key.

Settings you can change from the **UI** (admin → Settings) later: LLM
providers, email accounts, calendar sources, MCP servers, webhooks, API
tokens, per-user privileges. Everything else is `.env`-only.

> For **install steps**, see [`SETUP.md`](SETUP.md).
> For **what each script does**, see [`SCRIPTS.md`](SCRIPTS.md).

## Networking

| Variable | Default | Purpose |
|---|---|---|
| `APP_BIND` | `127.0.0.1` | Host bind for the web UI. Set `0.0.0.0` only when intentionally exposing to LAN or reverse proxy. |
| `APP_PORT` | `7000` | Host port for the web UI. |
| `ALLOWED_ORIGINS` | `http://localhost,http://127.0.0.1` | Comma-separated CORS allow-list. Add origins when serving from a non-loopback host. |
| `ODYSSEUS_HOST` | — | Used by `start-macos.sh`; overrides bind when running the macOS launcher. |
| `REQUEST_TIMEOUT_SECONDS` | `120` | Hard timeout per request (middleware). |

## Authentication & sessions

| Variable | Default | Purpose |
|---|---|---|
| `AUTH_ENABLED` | `true` | Master switch for login. Keep `true` for any network-accessible deployment. |
| `LOCALHOST_BYPASS` | `false` | If `true`, loopback requests get admin auto-login. **Local dev only** — guard against `X-Forwarded-For` spoofing. |
| `SECURE_COOKIES` | `false` | Set `true` when the app is served through HTTPS at a trusted proxy / private gateway. |
| `ODYSSEUS_ADMIN_USER` | `admin` | First-boot admin username. |
| `ODYSSEUS_ADMIN_PASSWORD` | (random) | First-boot admin password; printed if not set. |
| `ODYSSEUS_SKIP_ADMIN_PROMPT` | `0` | Set `1` to suppress the interactive admin-password prompt at `setup.py`. |
| `SESSION_COOKIE_AGE` | (long-lived) | Session lifetime in seconds. |

> Rotate any API keys ever pasted into a shared chat, demo, screenshot, or log.

## LLM providers

| Variable | Default | Purpose |
|---|---|---|
| `LLM_HOST` | `localhost` | Default LLM server `host[:port]`. |
| `LLM_HOSTS` | — | Comma-separated list for model discovery across multiple servers. |
| `OPENAI_API_KEY` | — | Optional OpenAI key. Prefer adding providers in the UI rather than pre-seeding. |
| `OLLAMA_BASE_URL` | — | Convenience alias for Ollama on host. |
| `RESEARCH_LLM_ENDPOINT` | — | Override the LLM endpoint used for deep-research runs. |
| `LLM_TIMEOUT` | (app default) | HTTP timeout for LLM calls. |
| `LLM_CACHE_TTL` | (app default) | Optional response cache TTL. |

Add providers in **Settings → Models** after first login. The runtime
supports vLLM / SGLang / llama.cpp server / Ollama / OpenAI / OpenRouter —
all OpenAI-compatible.

## Embeddings

| Variable | Default | Purpose |
|---|---|---|
| `LOCAL_EMBEDDING_PATH` | — | **Preferred** — local ONNX model directory (e.g. `bge-small-en-v1.5`). No network at runtime. |
| `EMBEDDING_URL` | — | OpenAI-compatible embeddings endpoint, used when no local model. |
| `EMBEDDING_MODEL` | — | Model name to pass to the HTTP API (e.g. `all-minilm:l6-v2`). |
| `FASTEMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | fastembed fallback model id. |
| `FASTEMBED_CACHE_PATH` | `~/.cache/fastembed` | fastembed cache location. |
| `HF_HUB_DISABLE_SYMLINKS` | `1` on Windows | Forces HF hub to copy (not symlink) model files — UNC shares can't follow symlinks. |

Init order in `src/embeddings.py`:
1. Local ONNX from `LOCAL_EMBEDDING_PATH` (if set and loadable).
2. HTTP API from `EMBEDDING_URL` + `EMBEDDING_MODEL`.
3. fastembed / sentence-transformers (downloads from HF hub on first use).
4. Keyword-only retrieval (degrade mode).

## Vector DB (Qdrant)

| Variable | Default | Purpose |
|---|---|---|
| `QDRANT_URL` | `http://172.20.1.109:30633` | Qdrant server URL. Point at your own for non-default deploys. |
| `QDRANT_API_KEY` | — | Set only for cloud-hosted Qdrant. |
| `QDRANT_TIMEOUT` | `30.0` | Per-request timeout (seconds). |
| `QDRANT_CONNECT_TIMEOUT` | `2.0` | TCP probe timeout (seconds). |

Collections used:
- `odysseus_rag` — legacy single-collection RAG (per-owner payload tag).
- `ody-rag-{sanitize(owner)}` — per-user RAG collection.
- `vhtna_memories` — persistent vector memory (shared, owner-tagged).
- `vhtna_tool_index` — agent tool index (shared).

**Point IDs must be UUID or unsigned int.** See
[`RAG_PIPELINE.md`](RAG_PIPELINE.md#point-ids) and the memory
`qdrant-point-id-format`.

## Object storage (MinIO / S3)

| Variable | Default | Purpose |
|---|---|---|
| `ODYSSEUS_USE_MINIO` | `false` | Master switch. When `false`, falls back to local `data/uploads/`. |
| `MINIO_ENDPOINT` | — | `host:port` of the MinIO / S3 server. Project default: `10.55.110.130:32100`. |
| `MINIO_ACCESS_KEY` | — | Access key. |
| `MINIO_SECRET_KEY` | — | Secret key. |
| `MINIO_BUCKET` | — | Bucket name. Project default: `networkchange-docs`. |
| `MINIO_SECURE` | `true` | Use HTTPS. |
| `MINIO_REGION` | — | Optional region tag. |

Object key layout:
- Library docs: `userdata/{owner}/library/{object_name}`
- Session uploads: `userdata/{owner}/sessions/{session_id}/uploads/{upload_id}`
- Deep-research exports: `userdata/{owner}/research/{id}.json`

See [`STORAGE.md`](STORAGE.md#object-storage-minio) for the wrapper API
and the per-user isolation model.

## Relational DB

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/app.db` | SQLAlchemy connection URL. |
| `ODYSSEUS_MULTITENANT_POSTGRES` | `false` | Switch to the Postgres + Alembic path. Triggers `alembic upgrade head` under advisory lock at startup. |

Postgres example:
```bash
ODYSSEUS_MULTITENANT_POSTGRES=true
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/odysseus
```

Switching an existing SQLite install to Postgres:
1. Bring up an empty Postgres target.
2. Set the env vars above and run `python -c "from core.database import init_db; init_db()"` once to run migrations.
3. `python -m scripts.migrate_sqlite_to_postgres --apply` to copy data.

See [`STORAGE.md`](STORAGE.md#postgresql-multi-tenant-path) for full details.

## Web search

| Variable | Default | Purpose |
|---|---|---|
| `SEARXNG_INSTANCE` | `http://localhost:8080` | SearXNG URL. Docker overrides to `http://searxng:8080`. |
| `SEARXNG_SECRET` | (auto on first Docker boot) | SearXNG cookie/CSRF secret. Leave blank unless you need to pin. |
| `DATA_BRAVE_API_KEY` | — | Optional Brave Search key. |
| `GOOGLE_API_KEY` | — | Optional Google Custom Search key. |
| `GOOGLE_PSE_CX` | — | Google Programmable Search Engine id. |
| `TAVILY_API_KEY` | — | Optional Tavily key. |
| `SERPER_API_KEY` | — | Optional Serper key. |
| `DUCKDUCKGO_SEARCH` | (auto-detected) | Falls back to duckduckgo-search if `requirements-optional.txt` is installed. |

The search dispatcher in `src/search/` tries each enabled source in order
and falls back to the next on failure.

## Background tasks / agents

| Variable | Default | Purpose |
|---|---|---|
| `MAX_AGENT_ROUNDS` | `20` | Hard ceiling on agent continuation steps. |
| `CLEANUP_INTERVAL_HOURS` | `24` | Background session-cleanup cadence. |
| `ODYSSEUS_INPROCESS_POLLERS` | `1` | In-process task-scheduler pollers. |
| `ODYSSEUS_INPROCESS_TASKS` | `1` | In-process task workers. |
| `ODYSSEUS_SCRIPT_HOST` | `localhost` | Host label used by Cookbook when generating serve scripts. |

## HuggingFace / Cookbook

| Variable | Default | Purpose |
|---|---|---|
| `HF_TOKEN` | — | HuggingFace token (gated models, higher rate limits). |
| `HUGGING_FACE_HUB_TOKEN` | — | Alias some libraries check. |

Cookbook-related caches live under `./data/huggingface` (compose-mounted
from `~/.cache/huggingface` inside the container) and `./data/local`
(compose-mounted from `~/.local` inside the container) so a container
recreate doesn't drop installed CLIs / serve engines.

## Feature flags

`core/feature_flags.py::FeatureFlags` is an immutable singleton read at import
time. Two layers of gating:

### Deploy modes

| `ODYSSEUS_DEPLOY_MODE` | Features enabled |
|---|---|
| `enterprise` (default) | All 19 features. |
| `minimal` | Chat, Documents (Library), Research, Settings only. |

```bash
ODYSSEUS_DEPLOY_MODE=minimal
```

### Per-feature overrides

`ODYSSEUS_FEATURE_<NAME>` overrides the deploy-mode default — enables a
feature in `minimal` mode or disables one in `enterprise` mode. Recognized
flags (case-sensitive):

| Flag | Default in enterprise | Controls |
|---|---|---|
| `ODYSSEUS_FEATURE_CHAT` | true | Chat UI / endpoints |
| `ODYSSEUS_FEATURE_AGENT` | true | Agent loop |
| `ODYSSEUS_FEATURE_RESEARCH` | true | Deep research |
| `ODYSSEUS_FEATURE_DOCUMENTS` | true | Document editor + library |
| `ODYSSEUS_FEATURE_MEMORY` | true | Persistent memory + skills |
| `ODYSSEUS_FEATURE_EMAIL` | true | IMAP/SMTP integration |
| `ODYSSEUS_FEATURE_CALENDAR` | true | CalDAV calendar |
| `ODYSSEUS_FEATURE_NOTES` | true | Notes + todos |
| `ODYSSEUS_FEATURE_TASKS` | true | Scheduled tasks |
| `ODYSSEUS_FEATURE_GALLERY` | true | Image gallery |
| `ODYSSEUS_FEATURE_COOKBOOK` | true | Cookbook hardware scan / model serving |
| `ODYSSEUS_FEATURE_COMPARE` | true | Side-by-side model comparison |
| `ODYSSEUS_FEATURE_MCP` | true | External MCP servers |
| `ODYSSEUS_FEATURE_WEBHOOKS` | true | Outbound webhook dispatcher |
| `ODYSSEUS_FEATURE_API_TOKENS` | true | `ody_*` Bearer tokens |
| `ODYSSEUS_FEATURE_SHELL` | false | Agent shell tool (admin-only even when enabled) |
| `ODYSSEUS_FEATURE_SEARCH` | true | Web search (agent + chat) |
| `ODYSSEUS_FEATURE_STT` | true | Speech-to-text (requires faster-whisper) |
| `ODYSSEUS_FEATURE_TTS` | true | Text-to-speech |
| `ODYSSEUS_FILE_UPLOADS` | true | File upload tool |
| `ODYSSEUS_FEATURE_DOCUMENT_RAG` | true | Document RAG (vector search over library) |

Plus infra flags:

| Flag | Default | Controls |
|---|---|---|
| `ODYSSEUS_INFRA_MULTITENANT_POSTGRES` | mirrors `ODYSSEUS_MULTITENANT_POSTGRES` | Routes DB init through Alembic |
| `ODYSSEUS_FEATURE_OFFLINE_MODE` | false | Disables all internet-requiring features |

Example combination: enterprise mode minus shell + email, plus a single
extra feature in minimal:

```bash
ODYSSEUS_DEPLOY_MODE=enterprise
ODYSSEUS_FEATURE_SHELL=false
ODYSSEUS_FEATURE_EMAIL=false
```

## Multi-process invocation quirks

- **BOM on Windows:** `.env` saved from Notepad gets a UTF-8 BOM. The
  app loader handles it; if you write a custom launcher that bypasses
  `app.py`'s `load_dotenv`, the BOM silently breaks parser.
- **HF symlinks on Windows:** `app.py` sets `HF_HUB_DISABLE_SYMLINKS=1`
  automatically on Windows. HuggingFace hub would otherwise symlink model
  files, which fails on UNC/network shares.
- **Same-thread SQLite:** the engine uses `check_same_thread=False` so
  background tasks can share the connection.
- **Postgres advisory lock:** first worker at startup runs `alembic
  upgrade head`; others block until the leader commits. Safe to scale
  horizontally without a manual migrate step.

## Docker-specific compose overrides

These come from `docker-compose.yml`:

| Source | What it does |
|---|---|
| `SEARXNG_INSTANCE=http://searxng:8080` | Routes search to the bundled compose service. |
| `host.docker.internal:host-gateway` | Lets the container reach Ollama on the host. |
| `COMPOSE_FILE=docker-compose.yml:docker/gpu.nvidia.yml` | Adds NVIDIA GPU passthrough. |
| `COMPOSE_FILE=docker-compose.yml:docker/gpu.amd.yml` + `RENDER_GID=<n>` | Adds AMD/ROCm GPU passthrough. |
| `PUID` / `PGID` (default `1000`) | Drops to this user inside the container; entrypoint chowns `data/` and `logs/` to match. |

See the comments in `docker/gpu.nvidia.yml` / `docker/gpu.amd.yml` for the
per-overlay details.

## Secrets hygiene

- `.env`, `data/auth.json`, `data/uploads/`, `data/app.db`,
  `data/personal_docs/`, generated media, backups: **gitignored by default**.
  Confirm with `git status --short` before publishing a fork.
- Fernet-encrypts at rest: email-account credentials, MCP server credentials
  (when marked secret), webhook signatures (when configured).
- API tokens (`ody_*`) are stored hashed (bcrypt) in `ApiToken`. The prefix
  is shown once on creation; the full token is never recoverable.
- Review `data/auth.json` after first boot: disable open signup unless
  intentionally enabled, make only your own account admin, keep demo/test
  accounts non-admin.

Rotate any API keys ever pasted into a shared chat, demo, screenshot, or
log.

## Minimal example `.env`

```bash
# Identity / networking
APP_BIND=127.0.0.1
APP_PORT=7000
AUTH_ENABLED=true
LOCALHOST_BYPASS=false
ALLOWED_ORIGINS=http://localhost,http://127.0.0.1

# LLM
LLM_HOST=localhost
# OPENAI_API_KEY=sk-...

# Embeddings (local ONNX)
LOCAL_EMBEDDING_PATH=/path/to/bge-small-en-v1.5

# Vector DB
QDRANT_URL=http://172.20.1.109:30633

# Object storage
ODYSSEUS_USE_MINIO=true
MINIO_ENDPOINT=10.55.110.130:32100
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=***************
MINIO_BUCKET=networkchange-docs

# Relational DB
DATABASE_URL=sqlite:///./data/app.db
# ODYSSEUS_MULTITENANT_POSTGRES=true

# Search
SEARXNG_INSTANCE=http://localhost:8080

# Feature gating
ODYSSEUS_DEPLOY_MODE=enterprise
```
