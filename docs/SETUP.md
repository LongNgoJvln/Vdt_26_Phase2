# Local Environment Setup

This is the detailed companion to the README's "Quick Start" — prerequisites,
step-by-step install, troubleshooting, and private/proxied deployment notes.

For the full env-var reference, see [`CONFIGURATION.md`](CONFIGURATION.md).
For what each script does, see [`SCRIPTS.md`](SCRIPTS.md).

## Prerequisites

| Tool | Min version | Why | Notes |
|---|---|---|---|
| Python | 3.11 | Async syntax, `typing` features | 3.12 also tested; 3.13 should work |
| pip | latest | Install deps | — |
| git | any | Clone, version pinning | — |
| tmux | any | Cookbook background model downloads/serves | Optional; only for Cookbook |
| Docker + compose | recent | If using the Docker path | Podman also works with `podman-compose` |

Optional / situational:

- **Local model server**: Ollama, llama.cpp, vLLM, SGLang — only if you want
  local model *serving* (Cookbook can install these for you after first boot).
- **NVIDIA Container Toolkit** (Docker GPU): for Cookbook GPU serving. Run
  `scripts/check-docker-gpu.sh` to diagnose / install / enable the compose
  overlay.
- **SearXNG**: web search. Compose bundles one at `searxng:8080`.
- **MinIO / S3-compatible bucket**: object storage. Optional — without it the
  app falls back to local `data/uploads/`.
- **Qdrant**: vector DB for RAG. The current project default is
  `http://172.20.1.109:30633`; point at your own with `QDRANT_URL`.

## Step-by-step — Native Linux / macOS

### 1. Clone and enter the repo

```bash
git clone <repo-url> 5g-agentic-ai
cd 5g-agentic-ai
```

### 2. Create and activate a virtualenv

```bash
python3 -m venv venv
source venv/bin/activate
```

On macOS with multiple Homebrew Pythons, be explicit:
```bash
/opt/homebrew/bin/python3.12 -m venv venv
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-optional.txt   # faster-whisper, PyMuPDF, duckduckgo-search
```

The `-optional` file pulls in extras for STT, PDF text extraction, and a
DuckDuckGo search fallback. Skip it for a minimal install.

### 4. Create your `.env`

```bash
cp .env.example .env   # if .env.example exists; otherwise use the cheat-sheet below
$EDITOR .env
```

Minimal `.env` for a local dev instance:

```bash
APP_BIND=127.0.0.1
APP_PORT=7000
AUTH_ENABLED=true
LOCALHOST_BYPASS=false               # or true, ONLY for loopback dev

LLM_HOST=localhost                   # primary LLM server (host[:port])

# Embeddings — local ONNX model strongly recommended
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
# DATABASE_URL=postgresql+psycopg://user:pass@host:5432/odysseus

SEARXNG_INSTANCE=http://localhost:8080
ODYSSEUS_DEPLOY_MODE=enterprise
```

> The app reads `.env` with `utf-8-sig` so a Windows-Notepad BOM is fine.

### 5. Initialize the database and admin user

```bash
python setup.py
```

This:
- Creates `data/`, `data/uploads/`, `data/personal_docs/`, `data/chroma/`,
  `logs/`, etc.
- Initializes the DB schema (`Base.metadata.create_all` for SQLite; `alembic
  upgrade head` for Postgres with `ODYSSEUS_MULTITENANT_POSTGRES=true`).
- Creates the admin user. The username defaults to `admin` (override with
  `ODYSSEUS_ADMIN_USER`); the password is auto-generated and printed unless
  `ODYSSEUS_ADMIN_PASSWORD` is set, or you can pass `ODYSSEUS_SKIP_ADMIN_PROMPT=1`
  to go non-interactive.

### 6. Start the server

```bash
python -m uvicorn app:app --host 127.0.0.1 --port 7000
```

Open `http://localhost:7000` in your browser. Log in with the admin password
printed by `setup.py`.

### 7. Configure providers in the UI

_after first login_, go to **Settings** and add:
- LLM providers (under **Models**) — chat completion endpoints.
- Email accounts (IMAP/SMTP) — credentials are Fernet-encrypted at rest.
- Calendar (CalDAV) — sync to Radicale / Nextcloud / Apple / Fastmail.
- MCP servers — local or remote stdio/SSE/HTTP MCP servers.

## Step-by-step — Docker

### 1. Clone

```bash
git clone <repo-url> 5g-agentic-ai
cd 5g-agentic-ai
```

### 2. Create `.env`

```bash
cp .env.example .env
$EDITOR .env
```

Docker-specific overrides applied by `docker-compose.yml`:
- `SEARXNG_INSTANCE` is forced to `http://searxng:8080` (the compose service).
- `QDRANT_URL` defaults to `http://172.20.1.109:30633` (override if you run
  your own).
- The web port comes from `APP_PORT` (default `7000`); the bind from
  `APP_BIND` (default `127.0.0.1`).

### 3. Build and start

```bash
docker compose up -d --build
docker compose logs --tail=120 odysseus     # grab the admin password
```

Open `http://localhost:7000`.

### 4. Enable GPU (Cookbook serving) — optional

Cookbook can only detect GPUs that Docker exposes to the container. Run the
diagnostic:

```bash
scripts/check-docker-gpu.sh          # read-only
scripts/check-docker-gpu.sh --install-nvidia-toolkit   # sudo; Ubuntu/Debian
scripts/check-docker-gpu.sh --enable-nvidia-overlay    # edits .env after GPU passes
```

Manual alternative: add this to `.env`:

```bash
COMPOSE_FILE=docker-compose.yml:docker/gpu.nvidia.yml
```

For AMD/ROCm:

```bash
scripts/check-docker-amd-gpu.sh
# then add the reported values to .env:
COMPOSE_FILE=docker-compose.yml:docker/gpu.amd.yml
RENDER_GID=989    # your host's numeric render group id
```

> **GPU passthrough ≠ llama.cpp CUDA.** `nvidia-smi` passing inside the
> container confirms Docker GPU access, but llama.cpp also needs `cudart` at
> runtime. If Cookbook logs show `Unable to find cudart library`, that is a
> Cookbook/llama.cpp build issue — re-install the serve engine via
> **Cookbook → Dependencies** to get a CUDA-enabled build. Same split applies
> to AMD/ROCm.

See the comments in `docker/gpu.nvidia.yml` or `docker/gpu.amd.yml` for the
full per-overlay notes.

## Step-by-step — Apple Silicon

Docker on macOS cannot use the Metal GPU. For GPU-accelerated Cookbook on an
M-series Mac, run natively:

```bash
./start-macos.sh
```

Launches at `http://127.0.0.1:7860` (AirPlay often holds `7000`). To expose
over a trusted LAN/VPN (e.g. Tailscale):

```bash
ODYSSEUS_HOST=0.0.0.0 ./start-macos.sh
# then open http://<tailscale-ip>:7860
```

Keep `AUTH_ENABLED=true` before binding outside loopback.

To build a clickable app wrapper:
```bash
./build-macos-app.sh
```

## Step-by-step — Native Windows

One-command launcher (creates venv, installs deps, runs setup, starts server):

```powershell
powershell -ExecutionPolicy Bypass -File .\launch-windows.ps1
```

Or manually:
```powershell
py -3.11 -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python setup.py
python -m uvicorn app:app --host 127.0.0.1 --port 7000
```

Local GPU *serving* of vLLM/SGLang needs Linux/WSL2. For a local model on
Windows, [Ollama](https://ollama.com/download) is the easiest path — point
the app at `http://localhost:11434/v1` in **Settings**.

Windows gotchas:
- `.env` saved from Notepad gets a UTF-8 BOM. The app reads with
  `utf-8-sig` so it's fine; if you ever bypass that loader, strip the BOM.
- HuggingFace symlinks don't work on UNC/network shares. `app.py` sets
  `HF_HUB_DISABLE_SYMLINKS=1` on Windows automatically to force a copy.
- Git for Windows gives you `bash.exe` — needed for Cookbook model downloads
  and the agent shell tool.

## Connecting external services

### LLM provider

Pick one (or several):

| Provider | Endpoint shape |
|---|---|
| Ollama | `http://localhost:11434/v1` |
| vLLM / SGLang / llama.cpp server | `http://<host>:8000/v1` |
| OpenAI / OpenRouter | `https://api.openai.com/v1` (needs `OPENAI_API_KEY`) |

Add in **Settings → Models**. If you only want one default, set `LLM_HOST` in
`.env`.

### Ollama on host, app in Docker

Add the endpoint `http://host.docker.internal:11434/v1` in Settings. Ollama
must listen outside its own loopback:

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

`host.docker.internal` is Docker's hostname for the host machine from inside
the container.

### External Qdrant / MinIO

Point at your instances in `.env` and they're picked up at first boot. The
default project values are the USD-Common cluster
(`QDRANT_URL=http://172.20.1.109:30633`, MinIO at `10.55.110.130:32100`).

### External Postgres (multi-tenant)

```bash
export ODYSSEUS_MULTITENANT_POSTGRES=true
export DATABASE_URL=postgresql+psycopg://user:pass@host:5432/odysseus
python -c "from core.database import init_db; init_db()"   # runs alembic upgrade head
```

Then populate from an existing SQLite install:
```bash
python -m scripts.migrate_sqlite_to_postgres --apply
```

## Built-in MCP servers

The app auto-registers a few MCP servers at startup. The npx-based ones
(currently `@playwright/mcp` for browser control) only start when their npm
package is already cached. To enable:

```bash
npx -y @playwright/mcp@latest --version
```

That installs `@playwright/mcp` + Playwright (~300 MB total). Restart the app
and the server will register at startup.

## Verifying the install

```bash
curl http://localhost:7000/healthz        # app health
curl "$QDRANT_URL/collections/odysseus_rag"   # vector DB reachable
mc ls --recursive odysseusminio/networkchange-docs/userdata/<owner>/library/  # lib docs synced
```

Useful logs to grep:

```bash
docker compose logs odysseus | grep -E 'object_store|RAG|Qdrant|DEGRADED'
```

## Troubleshooting

### First boot forces a login despite `AUTH_ENABLED=false`

Likely cause: `.env` has a UTF-8 BOM and the loader was bypassed. The app's
loader uses `utf-8-sig` to strip it — if you're starting uvicorn with a
custom command that skips `app.py`'s module-level `load_dotenv`, the BOM
makes the parser silently ignore `AUTH_ENABLED`.

Fix: re-save `.env` as plain UTF-8, or always start via `python -m uvicorn
app:app` (which triggers the module import order).

### `could not connect to Qdrant at http://172.20.1.109:30633`

Check that:
- You're on a network that can reach that host (it's not on the public internet).
- `QDRANT_TIMEOUT` and `QDRANT_CONNECT_TIMEOUT` are sensible (defaults `30.0`
  and `2.0` seconds).
- No proxy is intercepting. Try `curl -v "$QDRANT_URL/collections"`.

### `Format error in JSON body: value … is not a valid point ID`

You're writing Qdrant points with a string ID. Qdrant 1.18 only accepts UUID
or unsigned int. The fix is in `src/rag_vector.py::_generate_doc_id` — IDs
must be `uuid.uuid4()` or `uuid.uuid5(...)`. See
[`STORAGE.md`](STORAGE.md#vector-db-qdrant) for details.

### Library docs work but content search returns nothing

You're hitting the **update caveat**: PUT/PATCH paths don't re-index into
RAG. Re-ingest with:

```bash
python -m scripts.backfill_rag_documents --apply --resync
```

### `Auth session expired` loop after restarting

Likely the auth DB was recreated while your browser still had the old
session cookie. Clear cookies for `localhost:7000` and log in fresh.

### Cookbook can't find GPU

Run `scripts/check-docker-gpu.sh`. Common causes:
- NVIDIA Container Toolkit not installed on host.
- Compose overlay not enabled (`COMPOSE_FILE=docker-compose.yml:docker/gpu.nvidia.yml`).
- For AMD: `RENDER_GID` doesn't match your host's render group.

### Reverse proxy returns 401 even with valid session

`SECURE_COOKIES=true` requires HTTPS end-to-end. If your proxy terminates
TLS and proxies to a plain-HTTP app, that's fine; if any hop is HTTP, the
cookie is dropped. Either complete the HTTPS chain or set
`SECURE_COOKIES=false` for the dev path.

## Private or proxied deployments

VHT Network Automation serves plain HTTP on its app port. A typical
production/private deployment:

1. Keep the app on localhost (`127.0.0.1:7000`).
2. Terminate HTTPS at a trusted reverse proxy or private access gateway
   (Cloudflare Access, Tailscale, Caddy, nginx, Traefik).
3. Put the authenticated app entrypoint behind that layer.
4. Keep raw service / model ports internal-only.

Common internal-only ports from the default compose setup:

| Port | Service |
|---|---|
| `7000` | App raw port |
| `8080` | SearXNG |
| `8091` | ntfy |
| `8100` | ChromaDB host port (compose access) |
| `11434` | Ollama |
| `8000-8020` | Common local model/provider APIs |

If your access layer reaches the app on the same host, proxy to
`http://127.0.0.1:7000` and keep `AUTH_ENABLED=true`,
`LOCALHOST_BYPASS=false`, `SECURE_COOKIES=true`.
