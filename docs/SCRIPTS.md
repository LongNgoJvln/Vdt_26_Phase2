# Scripts Reference

Operations / migration / one-shot utilities live under `scripts/`. All are
run from the project root, almost all are idempotent (safe to re-run), and
almost every migration / backfill ships with a dry-run default — pass
`--apply` (or sometimes `--force`) to make changes.

Conventions:
- Scripts that need project imports insert the parent dir on `sys.path` at
  the top, so you can run them with `python scripts/foo.py` or
  `python -m scripts.foo` interchangeably.
- They load `.env` (with `utf-8-sig`) themselves so you don't need to
  `export` first.
- Logs go to stderr; structured summary line at the end with counts.

## Quick reference

| Script | One-liner | Default mode | Write flag |
|---|---|---|---|
| `setup.py` | First-time setup: dirs + DB + admin user | applies | (always) |
| `scripts/backfill_minio_documents.py` | Push lib docs missing from MinIO | dry-run | `--apply` |
| `scripts/backfill_rag_documents.py` | Ingest lib docs missing from Qdrant | dry-run | `--apply` |
| `scripts/ingest_network_knowledge.py` | Ingest bundled 4G/EPC knowledge + instructions into Qdrant | dry-run | `--apply` |
| `scripts/migrate_chroma_to_qdrant.py` | Move Chroma → Qdrant (per-user collections) | dry-run | `--apply` |
| `scripts/migrate_sqlite_to_postgres.py` | Copy SQLite → Postgres | dry-run | `--apply` |
| `scripts/migrate_minio_paths.py` | Re-key MinIO objects to session/library layout | dry-run | `--force` |
| `scripts/migrate_deep_research_to_minio.py` | Re-emit deep-research reports into `userdata/<owner>/research/` | dry-run | (omits `--dry-run`) |
| `scripts/migrate_scheduled_emails_to_pg.py` | Move scheduled-emails SQLite → Postgres | applies | — |
| `scripts/migrate_uploads_to_pg.py` | Move `uploads.json` → Postgres | applies | — |
| `scripts/migrate_user_prefs_to_pg.py` | Move `user_prefs.json` → Postgres | applies | — |
| `scripts/index_documents.py` | Index `personal_docs/` files into RAG | applies | — |
| `scripts/claim_ownerless.py` | Re-assign `owner=NULL` rows to a user | asks for confirmation | — |
| `scripts/update_database.py` | One-shot column backfill (legacy SQLite) | applies | — |
| `scripts/hf_download.py` | HuggingFace model downloader (pipe-friendly) | applies | — |
| `scripts/add_hwfit_models.py` | Seed Cookbook-supported model catalog | applies | — |
| `scripts/check-docker-gpu.sh` | NVIDIA Docker GPU diagnostic + optional fix | read-only | `--install-nvidia-toolkit`, `--enable-nvidia-overlay` |
| `scripts/check-docker-amd-gpu.sh` | AMD Docker GPU diagnostic | read-only | — |
| `scripts/diffusion_server.py` | Standalone diffusion image server (self-contained) | runs | — |
| `scripts/encode_previews.sh` | Re-encode gallery preview clip variants | applies | — |
| `scripts/fix_paths.py` | One-shot filesystem path migrator | applies | — |
| `scripts/odysseus*` (many) | CLI wrappers for per-feature operations | varies | — |

## Categories

### First-time setup

#### `setup.py`
```bash
python setup.py
```
Creates data dirs (`data/`, `data/uploads/`, `data/personal_docs/`,
`data/chroma/`, `logs/`, …), initializes the database schema, and creates the
admin user.

Env knobs:
- `ODYSSEUS_ADMIN_USER` — admin username (default `admin`).
- `ODYSSEUS_ADMIN_PASSWORD` — admin password (default: auto-generated + printed).
- `ODYSSEUS_SKIP_ADMIN_PROMPT=1` — go non-interactive, accept defaults.

### Backfills (wiring previously-missing writes)

#### `backfill_minio_documents.py`
```bash
python -m scripts.backfill_minio_documents                 # dry-run
python -m scripts.backfill_minio_documents --apply         # upload missing
python -m scripts.backfill_minio_documents --apply --owner vht   # one user
python -m scripts.backfill_minio_documents --apply --resync      # re-upload all
```
Walks `documents`, skips any already in MinIO (`stat_object` on the expected
key), uploads the rest via `_sync_document_to_minio` from
`routes/document_routes.py`. Updates `Document.storage_path` to match.

Suffix picked from `Document.language`: `.eml` for email, `.html`/`.xml`,
`.py`/`.js`/`.json`, plain otherwise.

Idempotent. Re-running without `--resync` after a successful `--apply`
should show `skipped_present=<total>` and `uploaded=0`.

#### `backfill_rag_documents.py`
```bash
python -m scripts.backfill_rag_documents                   # dry-run
python -m scripts.backfill_rag_documents --apply           # ingest missing
python -m scripts.backfill_rag_documents --apply --resync  # full re-ingest
```
Same shape as the MinIO backfill but for the Qdrant `odysseus_rag`
collection. Skips docs whose `source` tag is already present in the
collection; ingests the rest via `_ingest_document_to_rag`.

Success criterion: `curl $QDRANT_URL/collections/odysseus_rag` shows
`points_count` increasing by ~total_chunks_added after the run.

### Vector DB migrations

#### `migrate_chroma_to_qdrant.py`
```bash
python -m scripts.migrate_chroma_to_qdrant                 # dry-run
python -m scripts.migrate_chroma_to_qdrant --apply
```
Three Chroma collections → Qdrant targets:

| From (Chroma) | To (Qdrant) |
|---|---|
| `odysseus_rag` | per-user `ody-rag-{sanitize(owner)}` (ownerless lands on `ody-rag-admin`) |
| `vhtna_memories` | shared `vhtna_memories` (owner-tagged payload) |
| `vhtna_tool_index` | shared `vhtna_tool_index` (direct copy) |

Idempotent (`upsert`). Exit codes: 0 success; 1 fatal (Chroma missing /
Qdrant unreachable / embedding init failed).

### Relational DB migrations

#### `migrate_sqlite_to_postgres.py`
```bash
python -m scripts.migrate_sqlite_to_postgres               # dry-run summary
python -m scripts.migrate_sqlite_to_postgres --apply
```
Copies every table from the legacy SQLite DB into a fresh Postgres target.
Run after `ODYSSEUS_MULTITENANT_POSTGRES=true` + a fresh `init_db()`.

#### `migrate_scheduled_emails_to_pg.py`
```bash
DATABASE_URL=postgresql+psycopg://user:pass@host/odysseus \
  python scripts/migrate_scheduled_emails_to_pg.py [--sqlite data/scheduled_emails.db] [--batch 1000]
```
Moves scheduled-emails SQLite into the email-related Postgres tables.
Old ISO datetime strings are parsed into tz-naive UTC.

#### `migrate_uploads_to_pg.py`
```bash
DATABASE_URL=postgresql+psycopg://user:pass@host/5432/odysseus \
  python scripts/migrate_uploads_to_pg.py [--json data/uploads/uploads.json] [--batch 500]
```
Reads `uploads.json` (the legacy index), upserts into `Upload`. NULL owners
remain NULL; the `(owner, sha256)` unique constraint treats NULL as distinct,
so no duplicate collisions on legacy data.

#### `migrate_user_prefs_to_pg.py`
```bash
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/odysseus \
  python scripts/migrate_user_prefs_to_pg.py [--json data/user_prefs.json] [--batch 500]
```
Reads `user_prefs.json`, upserts into `user_settings(owner, key, value_json)`
with `ON CONFLICT DO NOTHING` so re-runs pick up where a partial failure left off.

### Object storage migrations

#### `migrate_minio_paths.py`
```bash
python scripts/migrate_minio_paths.py [--dry-run] [--force]
```
Re-keys objects under the old flat layout to the new session/library split:
- Session files: `userdata/{owner}/sessions/{session_id}/uploads/{upload_id}`
- Library files: `userdata/{owner}/library/{doc_id}`

Updates database records with the new `storage_path` values.

#### `migrate_deep_research_to_minio.py`
```bash
python scripts/migrate_deep_research_to_minio.py --default-owner admin@example.com [--dry-run]
```
Re-emits every deep-research report to `userdata/<owner>/research/<id>.json`
via the dual-write path. Legacy flat files in `data/deep_research/` stay in
place so flipping the flag back rolls back cleanly.

Ownerless legacy rows (pre-D.5 exports) are attributed to `--default-owner`
(typically the admin).

### Library / doc indexing

#### `ingest_network_knowledge.py`
```bash
python -m scripts.ingest_network_knowledge --owner <username>
python -m scripts.ingest_network_knowledge --owner <username> --apply
python -m scripts.ingest_network_knowledge --owner <username> --apply --replace
```
Indexes the version-controlled files under `knowledge_base/knowledge` and
`knowledge_base/instructions` into the `odysseus_rag` Qdrant collection. The
owner is mandatory because `search_knowledge` filters results by the logged-in
username. The default is a dry run; `--replace` is intended for re-indexing
after source documents change.

This is domain reference data, not live NetConfig. Live state continues to come
from the configured read-only MCP server and is saved separately as network
snapshots.

#### `index_documents.py`
```bash
python scripts/index_documents.py
```
Walks `personal_docs/` for `.txt` / `.md` / `.json`, chunks each (1000 chars,
200 overlap), and adds to the RAG vector DB. Per-file progress logging + a
final stats summary.

#### `hf_download.py`
```bash
python scripts/hf_download.py --repo <repo-id> [--dest <path>]
```
HuggingFace model downloader with pipe-friendly progress output (no ANSI bar
spamming logs). Used by the Cookbook flow when wiring pre-downloaded models
into a remote serve script.

### Owner attribution

#### `claim_ownerless.py`
```bash
python scripts/claim_ownerless.py --user <username>
```
Walks the owner-carrying tables and assigns every `owner IS NULL` row to the
given user. Useful when enabling auth on an install where rows were created
before the `owner` column was enforced.

There's a complementary startup hook in `core/database.py::_migrate_assign_legacy_owner`
that does the same job automatically (assigns orphans to the admin user) —
use this CLI when you want non-admin ownership or want to see the per-table
progress.

### Legacy column updates

#### `update_database.py`
```bash
python scripts/update_database.py
```
One-shot: adds `last_accessed`, `is_important`, `message_count` to legacy
SQLite sessions. For each existing row, `last_accessed` defaults to
`created_at`, `is_important` to False, `message_count` to the count of
related chat messages. Idempotent (checks column existence before adding).

> Only relevant for installs that pre-date the columns. New installs create
> the columns on first boot via `Base.metadata.create_all`.

### GPU / Docker helpers

#### `check-docker-gpu.sh` (NVIDIA)
```bash
scripts/check-docker-gpu.sh                             # read-only diagnostic
scripts/check-docker-gpu.sh --print-install-commands    # OS-specific commands
scripts/check-docker-gpu.sh --install-nvidia-toolkit    # sudo; Ubuntu/Debian
scripts/check-docker-gpu.sh --enable-nvidia-overlay     # edit .env after GPU passes
scripts/check-docker-gpu.sh --install-nvidia-toolkit --enable-nvidia-overlay   # full
```
Diagnoses NVIDIA Docker passthrough and optionally installs the toolkit +
edits `.env` to enable the `gpu.nvidia.yml` compose overlay.

Safety: `.env` is only modified with `--enable-nvidia-overlay`, and only
after GPU passthrough succeeds. `--yes` skips prompts but does not bypass
the passthrough gate.

#### `check-docker-amd-gpu.sh` (AMD / ROCm)
```bash
scripts/check-docker-amd-gpu.sh
```
Read-only diagnostic. Reports what to add to `.env` (e.g. `RENDER_GID=989`
and `COMPOSE_FILE=docker-compose.yml:docker/gpu.amd.yml`).

### Cookbook model catalog

#### `add_hwfit_models.py`
```bash
python scripts/add_hwfit_models.py
```
Seeds the Cookbook-supported model catalog with hwfit's curated models (sizes,
VRAM estimates, format tags). Idempotent on the model id.

### Per-feature CLI wrappers — `scripts/odysseus*`

These are first-class commands for working with the app's data from the
shell. Most are read/inspect or one-shot action CLIs.

| Wrapper | What it does |
|---|---|
| `odysseus` | Top-level dispatcher; run without args for the list. |
| `odysseus-sessions` | List / inspect chat sessions. |
| `odysseus-docs` | Library document utilities. |
| `odysseus-memory` | Memory CRUD / search. |
| `odysseus-notes` | Notes / todos CRUD. |
| `odysseus-tasks` | Scheduled task CRUD / trigger. |
| `odysseus-research` | Deep research start / status / results. |
| `odysseus-mail` | IMAP account / folder ops. |
| `odysseus-calendar` | CalDAV sync / event ops. |
| `odysseus-contacts` | Contact list ops. |
| `odysseus-gallery` | Gallery image / album ops. |
| `odysseus-signature` | Saved signature ops. |
| `odysseus-preset` | Chat preset CRUD. |
| `odysseus-skills` | Skill definition CRUD / audit. |
| `odysseus-webhook` | Webhook CRUD / dispatch. |
| `odysseus-mcp` | MCP server CRUD. |
| `odysseus-personal` | Personal data (account) ops. |
| `odysseus-logs` | Log viewer / grep / tail. |
| `odysseus-theme` | Theme CRUD / preview. |
| `odysseus-backup` | Backup orchestration (DB + MinIO + .env). |
| `odysseus-cookbook` | Cookbook hardware-scan / model download / serve lifecycle. |

Each starts with `--help` for the command list.

### Standalone bits

#### `diffusion_server.py`
A self-contained diffusion image server. Run directly:
```bash
python scripts/diffusion_server.py
```
Not part of the main app; useful for offloading image generation to a separate
process / host.

#### `encode_previews.sh`
```bash
bash scripts/encode_previews.sh
```
Re-encodes gallery preview clip variants (gif/webm) for the docs landing
page / in-app gallery previews.

#### `fix_paths.py`
```bash
python scripts/fix_paths.py
```
One-shot filesystem path migrator. Read the source before running — it's
targeted at a specific historical refactor.

## Convention: dry-run by default

If a migration script you're adding could mutate state, follow the same
pattern:

```python
ap = argparse.ArgumentParser()
ap.add_argument("--apply", action="store_true", help="Actually write (default is dry-run)")
args = ap.parse_args()

# ... compute the change set ...

if not args.apply:
    logger.info("[dry-run] would do X")
    return 0

# ... actually write ...
```

This mirrors the existing backfills and migrations, so operators can run any
script blindly, see what it would do, and then re-run with `--apply` once
they've confirmed.

## Running scripts in Docker

The compose service runs as the `odysseus` user inside the container.
Scripts can `exec` into the running container:

```bash
docker compose exec odysseus python -m scripts.backfill_rag_documents --apply
docker compose exec odysseus python -m scripts.backfill_minio_documents --apply
```

For one-off adhoc scripts that aren't in the image yet, mount them:
```bash
docker compose run --rm -v "$(pwd)/scripts:/app/scripts:z" odysseus \
  python -m scripts.backfill_rag_documents --apply
```

## Safety: backups before migrations

Before any `--apply` migration:

```bash
# 1. DB
sqlite3 data/app.db ".backup 'data/backups/app-$(date +%F).db'"   # SQLite
pg_dump "$DATABASE_URL" -F c -f "data/backups/odysseus-$(date +%F).dump"   # Postgres

# 2. MinIO
mc mirror --overwrite odysseusminio/networkchange-docs "backups/minio/$(date +%F)/"

# 3. Qdrant snapshots
curl -X POST "$QDRANT_URL/collections/odysseus_rag/snapshots"
```

`scripts/odysseus-backup` automates parts of this.
