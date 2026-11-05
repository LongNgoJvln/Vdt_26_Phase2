# Network Change

> **Standalone Network Change monolith.** Coding agents should begin with
> [`AGENTS.md`](AGENTS.md). Internal operators should use
> [`docs/INTERNAL_SERVER_DEPLOYMENT.md`](docs/INTERNAL_SERVER_DEPLOYMENT.md).
> Run `python scripts/verify_monolith_source.py` before creating or deploying an
> archive. Package provenance is recorded in [`SOURCE_MANIFEST.md`](SOURCE_MANIFEST.md).

![Network Change](docs/odysseus.jpg)

A self-hosted, multi-tenant AI workspace — the self-hosted equivalent of the
ChatGPT/Claude UI, running on your own hardware, with your own data. Local-first,
privacy-first, and built around an agent loop with RAG over your own document
library.

This `nc_v7_monolith` build provides a review-first network-change workflow. The
normal chat/agent loop remains available, while an opt-in in-process
Coordinator–Retriever–Generator–Critic pipeline handles mutating network-change
requests. See [`docs/NETWORK_CHANGE_MONOLITH.md`](docs/NETWORK_CHANGE_MONOLITH.md)
for its evidence, proposal, safety boundaries, and deployment model.

The bundled 4G/EPC reference documents live under [`knowledge_base/`](knowledge_base/README.md).
After first-time setup, ingest them for the application user that will query
them:

```bash
python -m scripts.ingest_network_knowledge --owner <username> --apply
```

This writes searchable vectors to Qdrant; live Kubernetes/network state still
comes from the configured read-only MCP server.

The default `APP_PROFILE=network_change` keeps chat, the normal agent loop,
sessions, model endpoints, MCP, documents, RAG/knowledge, memory and skills. It
does not register legacy email/calendar/task/cookbook/gallery/host-shell routes.
Set `APP_PROFILE=legacy` only as a temporary compatibility rollback.

Generated session documents are stored in SQL as before and mirrored to
`data/generated/<owner>/<session-id>/`. Network CLI files use `.cli`; intent,
risk and validation evidence remain in the chat/proposal rather than being
mixed into the command file.

### Tool modes before sending a prompt

Open **Tools** below the composer. Every built-in and MCP tool has one mode:

- `Tắt` (`disabled`): never offered and rejected if a model tries to call it.
- `Tự động` (`auto`): selected by the shared semantic/keyword filter.
- `Ghim` (`pinned`): always included for that session.

The MCP settings page still exposes the discovered tool list for each server;
that server-level switch is the global upper bound for session preferences.

### Guarded multi-agent network changes (opt-in)

In **Settings → AI → Network Change Multi-Agent**, enable the pipeline and
optionally select endpoints/models for Coordinator, Retriever, Generator and
Critic. Empty role selections inherit the active chat model. The pipeline runs
only in Agent mode for mutating network/Kubernetes requests; read-only queries
and report generation keep the normal loop. The deterministic validator—not
the Critic model—owns the pass/block verdict, and production execution remains
disabled.

### Kubernetes sandbox (optional)

Production MCP remains read-only. To validate against a disposable lab, add a
separate stdio MCP server with command:

```bash
python -m mcp_servers.k8s_sandbox_server
```

Give only that MCP process `K8S_SANDBOX_KUBECONFIG`. It supports server-side
dry-run by default. Isolated namespace apply/observe/rollback/cleanup additionally
requires `K8S_SANDBOX_ENABLE_APPLY=true`. It rejects cluster-scoped manifests
and never uses `/api/shell/exec`. Vendor EMS/MME CLI remains static/grounding
validation unless a real vendor emulator or test node is configured.
The namespace configured by `K8S_SANDBOX_NAMESPACE` must already exist for the
read-only server-side dry-run; the apply tool creates and removes its own
ephemeral namespace.

> 📖 **Full guides live in [`docs/`](docs/).** This README is the short path
> from `git clone` to a running server. For architecture, storage, RAG pipeline,
> configuration reference, and the complete scripts catalog, open:
> - [`docs/SETUP.md`](docs/SETUP.md) — detailed local-dev environment setup
> - [`docs/SCRIPTS.md`](docs/SCRIPTS.md) — every script under `scripts/`
> - [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — layers, middleware, startup flow, agent loop
> - [`docs/ARCHITECTURE_BASELINE_2026-09-14_VI.md`](docs/ARCHITECTURE_BASELINE_2026-09-14_VI.md) — baseline tiếng Việt trước refactor, sequence diagram và gap register
> - [`docs/ARCHITECTURE_POST_REFACTOR_2026-09-14_VI.md`](docs/ARCHITECTURE_POST_REFACTOR_2026-09-14_VI.md) — kiến trúc sau refactor, sequence diagram, mức validation và phần còn thiếu
> - [`docs/ARCHITECTURE_MULTIAGENT_2026-09-24_VI.md`](docs/ARCHITECTURE_MULTIAGENT_2026-09-24_VI.md) — pipeline Coordinator–Retriever–Generator–Critic đã triển khai
> - [`docs/ARCHITECTURE_BASELINE_2026-09-14.md`](docs/ARCHITECTURE_BASELINE_2026-09-14.md) — bản tiếng Anh của baseline
> - [`docs/STORAGE.md`](docs/STORAGE.md) — Postgres / SQLite + Qdrant + MinIO backends
> - [`docs/RAG_PIPELINE.md`](docs/RAG_PIPELINE.md) — ingestion hooks, chunking, hybrid retrieval
> - [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) — full environment-variable and feature-flag reference

## Features
- **Chat + general agent loop** — local/API models, endpoint fallback, Q&A, reports and files.
- **Opt-in guarded pipeline** — Coordinator, read-only Retriever, artifact-only Generator and deterministic Critic for mutating network changes.
- **Network change** — read-only evidence snapshot, drift comparison, staged proposal and audit history.
- **Unified tools** — built-in and MCP discovery with disabled/auto/pinned modes per session.
- **Knowledge base** — separated 4G/EPC knowledge and instructions, owner-scoped Qdrant retrieval.
- **Documents** — editable/versioned Markdown, manifest and command-only network CLI artifacts.
- **Validation** — static checks in the monolith and an optional dedicated Kubernetes sandbox MCP.
- **Storage** — SQLite/PostgreSQL metadata, optional MinIO, plus local generated-file mirrors.
- **Mobile-friendly** — responsive PWA and prompt recall with Arrow Up/Down.

## Quick Start

Run commands from the extracted `nc_v7_monolith` directory. Native deployment is
the simplest path on an internal server; Docker remains optional.

### Docker (recommended)
```bash
cd nc_v7_monolith
cp .env.example .env
docker compose up -d --build
docker compose logs --tail=120 odysseus   # grab the printed admin password
```
Open `http://localhost:7000`. Compose binds the web UI to `127.0.0.1` by default.
If port `7000` is taken, set `APP_PORT=7001` in `.env` and recreate the container.
Set `APP_BIND=0.0.0.0` **only** when you intentionally want LAN / reverse-proxy access.

### Native Linux / macOS
```bash
cd nc_v7_monolith
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python setup.py
python3 -m uvicorn app:app --host 0.0.0.0 --port 7000
```
Requirements: **Python 3.11+**. Run `setup.py` once for directories, schema and
the first admin account; it is not the long-running server process. Subsequent
starts only need the venv activation and Uvicorn command. Change `--port` freely
when `7000` is occupied, and update the reverse proxy/firewall accordingly.

### Native Windows
```powershell
cd nc_v7_monolith
py -3.11 -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python setup.py
python -m uvicorn app:app --host 127.0.0.1 --port 7000
```
Configure an existing local or remote OpenAI-compatible model endpoint from the
Settings UI after login.

## First Login

On first setup, Network Change creates an admin account (`admin` unless
`ODYSSEUS_ADMIN_USER` is set) and prints a temporary password in the terminal.
For Docker installs the same line appears in `docker compose logs odysseus`. The
setup prompt asks you to create these credentials; there is no preset username
or password that must be entered. Use them to log in, then change the password
in **Settings**.

## Local Environment Setup (cheat-sheet)

All runtime config is read from `.env` at startup (BOM-tolerant via `utf-8-sig`).
The bare-minimum `.env` for a local dev instance looks like:

```bash
# Identity / networking
APP_PROFILE=network_change
APP_BIND=127.0.0.1
APP_PORT=7000
AUTH_ENABLED=true
LOCALHOST_BYPASS=false               # set true ONLY for local dev on loopback

# LLM provider (configure others in the UI)
LLM_HOST=localhost                   # e.g. llm-host.local:8000

# Embeddings — prefer a local ONNX model; falls back to HTTP API
LOCAL_EMBEDDING_PATH=/path/to/bge-small-en-v1.5
# EMBEDDING_URL=http://localhost:11434/v1/embeddings   # optional HTTP fallback
# EMBEDDING_MODEL=all-minilm:l6-v2

# Vector DB (Qdrant). Commons used by this project:
QDRANT_URL=http://127.0.0.1:6333
# QDRANT_API_KEY=                      # set only for cloud-hosted instances

# Object storage (MinIO/S3). USD Common cluster:
ODYSSEUS_USE_MINIO=true
MINIO_ENDPOINT=127.0.0.1:9000
MINIO_ACCESS_KEY=change-me
MINIO_SECRET_KEY=change-me
MINIO_BUCKET=networkchange-docs

# Database — SQLite default, flip to Postgres for multi-tenant deployments
DATABASE_URL=sqlite:///./data/app.db
# ODYSSEUS_MULTITENANT_POSTGRES=true
# DATABASE_URL=postgresql+psycopg://user:pass@host:5432/odysseus

# Optional dedicated sandbox MCP; never point this at production
# K8S_SANDBOX_KUBECONFIG=/path/to/sandbox-kubeconfig
```

> 💡 The full variable list (LLM, embeddings, auth, feature flags, GPU overlays,
> web-search keys) is in [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md).

## Scripts Reference (most-used)

All scripts run from the project root and are idempotent (safe to re-run).
Almost every migration / backfill ships with a **dry-run** default — pass
`--apply` to make changes. Full catalog: [`docs/SCRIPTS.md`](docs/SCRIPTS.md).

| Script | What it does | When to run |
|---|---|---|
| `python setup.py` | Create dirs, init DB, create admin user. | First-time setup. |
| `python -m scripts.backfill_minio_documents` | Push lib docs missing from MinIO into `userdata/{owner}/library/`. | After wiring MinIO sync; dry-run default, `--apply` to upload. |
| `python -m scripts.backfill_rag_documents` | Ingest lib docs missing from Qdrant `odysseus_rag`. | After fixing RAG ingestion; dry-run default, `--apply` to write. |
| `python -m scripts.ingest_network_knowledge --owner <u>` | Ingest bundled 4G/EPC knowledge and instructions into Qdrant. | After setup; dry-run default, `--apply` to write. |
| `python -m scripts.migrate_sqlite_to_postgres` | Copy SQLite tables into fresh Postgres. | Moving to multi-tenant Postgres backend. |
| `python -m scripts.migrate_minio_paths` | Re-key MinIO objects to new session/library layout. | After the path-layout refactor. |
| `python scripts/claim_ownerless.py --user <u>` | Assign `owner=NULL` rows to a user. | After enabling auth on an existing install. |

## Application profile

`APP_PROFILE=network_change` is the default and recommended profile. It keeps
chat, the bounded general agent loop, the opt-in guarded network-change pipeline,
sessions, documents/reports, knowledge,
memory/skills, model endpoints, MCP management and network-change validation.
Legacy personal-assistant routes and tools are not registered or are rejected
at runtime.

`APP_PROFILE=legacy` is only a temporary compatibility rollback for upstream
Odysseus behavior; it is not the target production architecture.

Individual features can still be overridden with `ODYSSEUS_FEATURE_<NAME>` env
vars — enable specific ones in minimal mode (e.g. `ODYSSEUS_FEATURE_EMAIL=true`)
or disable specific ones in enterprise mode. The full flag list lives in
[`docs/CONFIGURATION.md`](docs/CONFIGURATION.md).

## Security Notes

Network Change is a self-hosted workspace with access to model endpoints,
uploaded files, owner-scoped data, API tokens, and configured MCP servers.
The default `network_change` profile blocks the legacy shell, web-research,
email/calendar and model-serving surfaces, but it should still be treated like
an internal admin console.

- Keep `AUTH_ENABLED=true` for any network-accessible deployment.
- Keep `LOCALHOST_BYPASS=false` outside local development.
- Set `SECURE_COOKIES=true` when serving through HTTPS at a trusted proxy.
- Do not expose it directly to the public internet without HTTPS + reverse proxy.
- Keep `.env`, `data/`, `logs/`, DBs, uploads, generated media, backups, auth/session files, API keys, and provider tokens **out of Git**. They're gitignored by default.
- Non-admin users do not get shell/Python/file read-write by default; admin-only routes/tools (MCP mgmt, API tokens, webhooks, model/cookbook serving, backup/vault, app settings) are admin-gated. Other features are controlled by per-user privileges — review them before exposing a deployment.
- Rotate any API keys ever pasted into a shared chat, screenshot, demo, or log.



## License

MIT — see [LICENSE](LICENSE) and [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md).
