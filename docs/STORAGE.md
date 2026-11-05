# Storage Architecture

VHT Network Automation uses **three** storage backends per deployment:

1. **Relational DB** — sessions, documents, chat history, all the metadata (`PostgreSQL` multi-tenant, or `SQLite` legacy).
2. **Vector DB** — RAG document vectors and agent tool index (`Qdrant`).
3. **Object storage** — uploads, exports, deep-research reports, library document bodies (`MinIO` / S3-compatible).

This document covers the schema layout, the migration path between backends,
multi-tenant ownership rules (which are enforced at **all three** layers, not
just the DB), and how to operate backfills.

> For the ingestion hooks that *write* into these backends, see
> [`RAG_PIPELINE.md`](RAG_PIPELINE.md). For env vars to point at the backends,
> see [`CONFIGURATION.md`](CONFIGURATION.md).

## Backend selection at a glance

| Component | Default (single-user) | Multi-tenant / prod | Config toggle |
|---|---|---|---|
| Relational DB | `data/app.db` (SQLite) | external PostgreSQL | `DATABASE_URL`, `ODYSSEUS_MULTITENANT_POSTGRES=true` |
| Vector DB | Qdrant (`QDRANT_URL`) | Qdrant + per-user collections | `QDRANT_URL`, `QDRANT_API_KEY` |
| Object storage | local `data/uploads/` | MinIO / S3 | `ODYSSEUS_USE_MINIO=true`, `MINIO_*` |

The two paths the operators most often flip are:

- **`ODYSSEUS_MULTITENANT_POSTGRES=true`** routes the DB through Alembic and the
  per-user `owner` filter — see [PostgreSQL multi-tenant path](#postgresql-multi-tenant-path).
- **`ODYSSEUS_USE_MINIO=true`** routes file I/O through `src/object_store.py`
  instead of the local filesystem — see [Object storage (MinIO)](#object-storage-minio).

## Relational DB

### Models (core/database.py)

Roughly 24 SQLAlchemy models. **Every user-facing model has an `owner` column**
(`String`, indexed, `nullable=True` for legacy data). Notable ones:

| Model | Holds | Notes |
|---|---|---|
| `Session` | Chat session metadata | `owner`, `title`, `archived`, timestamps |
| `ChatMessage` | Messages | FK to `Session`; `role`, `content`, `tool_calls` |
| `Document` | Document metadata | `current_content` (latest), `language`, `storage_path` (MinIO key), `is_active`, `archived` |
| `DocumentVersion` | Versioned bodies | FK to `Document`; `version_number`, `content`, `summary`, `source` |
| `Memory` | Persistent KV memory | `owner`, `key`, `value`, keywords, embedding (int4 for SQLite) |
| `Note`, `CalendarEvent`, `CalendarCal` | Personal organiser | per-owner scoping |
| `EmailAccount` | IMAP/SMTP creds | Fernet-encrypted (`src/secret_storage.py`) |
| `ModelEndpoint` | LLM server registry | `owner`-aware (users have private providers; admin-shared ones are global) |
| `McpServer` | MCP server config | `owner`-aware |
| `ScheduledTask`, `TaskRun` | Cron / event tasks | per-owner dispatch |
| `GalleryImage`, `GalleryAlbum` | Image gallery | per-owner, albums shared explicitly |
| `Comparison`, `Signature`, `ApiToken`, `Webhook`, `UserTool`, `CrewMember`, `EditorDraft`, `Integration` | Misc | per-owner |

`TimestampMixin` adds `created_at`/`updated_at` to most models.

### SQLite (default)

```bash
DATABASE_URL=sqlite:///./data/app.db
```

- Schema is created idempotently at startup via `Base.metadata.create_all`.
- Legacy column adds (`last_accessed`, `is_important`, `message_count`, …) run
  through `_migrate_*` helpers in `core/database.py`.
- Foreign-key enforcement is enabled globally (`PRAGMA foreign_keys=ON`).
- The connection uses `check_same_thread=False` so background tasks can share it.

### PostgreSQL (multi-tenant path)

```bash
ODYSSEUS_MULTITENANT_POSTGRES=true
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/odysseus
```

- `core/database.py::_init_db_postgres_alembic()` runs `alembic upgrade head`
  under a `pg_advisory_lock`, so concurrent workers converge on a single
  migrator — first worker migrates, others block until it commits.
- The 30+ SQLite-only `_migrate_*` steps are skipped (Alembic is the source of
  truth here).
- Migrations live in `alembic/versions/` (currently `0001`–`0005`).

To migrate an existing SQLite install to Postgres:

```bash
# 1. Bring up an empty Postgres target
createdb -h <host> -U <user> odysseus

# 2. Set the env vars and start the app once soAlembic builds the empty schema
export DATABASE_URL=postgresql+psycopg://user:pass@host:5432/odysseus
export ODYSSEUS_MULTITENANT_POSTGRES=true
python -c "from core.database import init_db; init_db()"

# 3. Copy the data
python -m scripts.migrate_sqlite_to_postgres        # dry-run summary
python -m scripts.migrate_sqlite_to_postgres --apply

# 4. Caveat: vector-related tables (memory, tool_index) live in Qdrant
#    not Postgres — if you still have Chroma data, run migrate_chroma_to_qdrant
#    (see Vector DB section).
```

### Multi-tenant ownership

The `owner` column is enforced at **two layers**:

1. **Route layer** — every query in `routes/*_routes.py` filters by
   `request.state.current_user.username`. Admin users bypass the filter.
2. **Schema layer** — most owner columns are indexed, and several uniqueness
   constraints include owner (e.g. `ApiToken.token`, `Webhook.event_id`).

Two safety valves recover legacy rows where `owner IS NULL`:

- **At startup**: `core/database.py::_migrate_assign_legacy_owner` rewrites
  `owner=NULL` rows to the configured admin user. Idempotent.
- **Operator CLI**: `scripts/claim_ownerless.py --user <username>` does the same
  on demand, with a per-table progress log.

## Vector DB (Qdrant)

| Setting | Value (USD-Common cluster) |
|---|---|
| Endpoint | `http://172.20.1.109:30633` |
| Server version | 1.18 |
| Collection (legacy) | `odysseus_rag` |
| Per-user collections | `ody-rag-{sanitize(owner)}` |
| Shared collection | `vhtna_memories` (per-user tagged) |
| Tool-index collection | `vhtna_tool_index` |
| Point ID format | UUID or unsigned int — **string slugs reject** (see `docs/`/memory: `qdrant-point-id-format`) |
| Embedding dim | 384 (BGE-small-en-v1.5 ONNX) |

Point IDs are `uuid5` — namespace = `sha256(owner)[:16]`, name = `sha256(text)`
(see `src/rag_vector.py::_generate_doc_id`). This gives dedupe-friendly
deterministic IDs.

To migrate from legacy Chroma:

```bash
python -m scripts.migrate_chroma_to_qdrant             # dry-run
python -m scripts.migrate_chroma_to_qdrant --apply     # write per-user ody-rag-{owner}
```

> The migration pulls from Chroma on disk (or HTTP) and writes the same
> embeddings to Qdrant with `upsert`. Re-runs only re-save the same payloads.

For the chunking/retrieval details, see [`RAG_PIPELINE.md`](RAG_PIPELINE.md).

## Object storage (MinIO)

| Setting | Value (USD-Common cluster) |
|---|---|
| Endpoint | `10.55.110.130:32100` |
| Bucket | `networkchange-docs` |
| Library prefix | `userdata/{owner}/library/{object_name}` |
| Session uploads prefix | `userdata/{owner}/sessions/{session_id}/uploads/{upload_id}` |
| Research exports prefix | `userdata/{owner}/research/{id}.json` |
| Credentials | `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` (read from `.env`) |

Toggle with `ODYSSEUS_USE_MINIO=true`. When disabled, the app falls back to
local disk under `data/uploads/`. The wrapper (`src/object_store.py`) exposes:

```python
store.put_library_file(owner, object_name, body, content_type=...)
store.delete_library_file(owner, object_name)
store.get_library_file(owner, object_name) -> bytes
store.put_session_upload(owner, session_id, upload_id, body, ...)
store.put_research_file(owner, research_id, payload, ...)
# ...
```

**Per-user namespace** (`userdata/{owner}/...`) is enforced at the wrapper
layer, not at the bucket policy. The DB `Document.storage_path` column stores
the full key (`userdata/vht/library/abc123.py`) so the app can resolve a doc
back to its object without an extra lookup.

### Document body storage — what gets written when

| Write site | Code path | What lands where |
|---|---|---|
| POST `/documents` | `routes/document_routes.py::create_document` | DB row + `_sync_document_to_minio` + `_ingest_document_to_rag` |
| PUT `/documents/{id}` | `routes/document_routes.py::update_document` | DB row + `_sync_document_to_minio` (**NOT** `_ingest_document_to_rag` — see caveat) |
| PATCH `/documents/{id}` | `routes/document_routes.py::patch_document` | same as PUT |
| POST `/documents/import-pdf` | `routes/document_routes.py::import_pdf` | DB row + MinIO sync + RAG ingest (via PDF form/plain creators) |
| DELETE `/documents/{id}` | `routes/document_routes.py::delete_document` | DB delete + `_remove_document_from_minio` (tries all candidate suffixes) |
| AI tool `create_document` | `src/tool_implementations.py::do_create_document` | DB row + MinIO sync + RAG ingest |
| AI tool `update_document` | `src/tool_implementations.py::do_update_document` | DB row + MinIO sync + RAG ingest |
| PDF form-doc creator | `src/pdf_form_doc.py::create_form_markdown_document` | DB row + RAG ingest + MinIO sync |
| PDF plain-doc creator | `src/pdf_form_doc.py::create_plain_pdf_document` | DB row + RAG ingest + MinIO sync |

**⚠️ Update caveat:** the route PUT/PATCH paths **do not** call
`_ingest_document_to_rag` — only `_sync_document_to_minio`. Content updates
made via the web UI will *not* be re-indexed into Qdrant. The AI-tool update
path (`do_update_document`) does. If you need a UI edit re-indexed, either
re-trigger from an agent call or run `scripts/backfill_rag_documents.py --apply --resync`.

### Backfilling MinIO

If you wired MinIO sync into the create paths *after* documents already existed,
they were never copied to object storage. Backfill with:

```bash
python -m scripts.backfill_minio_documents              # dry-run
python -m scripts.backfill_minio_documents --apply      # upload missing
python -m scripts.backfill_minio_documents --apply --owner vht   # one user
python -m scripts.backfill_minio_documents --apply --resync      # re-upload all
```

The dry-run uses `stat_object` to skip already-present objects. The
`--resync` flag ignores presence and re-uploads every document.

For Qdrant backfill (same pattern for missing RAG points):

```bash
python -m scripts.backfill_rag_documents                # dry-run
python -m scripts.backfill_rag_documents --apply        # ingest missing
python -m scripts.backfill_rag_documents --apply --resync   # full re-ingest
```

## Per-user isolation matrix

The three backends enforce ownership at different layers — same model, three
enforcement points:

| Layer | Enforcement | OOM for mis-attribution |
|---|---|---|
| Relational DB | `WHERE owner = :current_user` in every query; admin bypasses | Route sees no rows from other users |
| Qdrant | Per-user collection `ody-rag-{owner}` (or per-owner `source_tag` filter on shared collections) | Cross-user search returns zero hits |
| MinIO | Per-object key `userdata/{owner}/...`; wrapper enforces owner in the key | Object key doesn't resolve; `get_library_file(other_user, …)` 404s |

Exception: admin accounts (`User.is_admin=True`) bypass the DB filter. Admin
visibility is intentional and audited. Qdrant and MinIO do not have an
admin-bypass path — admins go through the same per-user wrapper.

## Backups

Quick recipe (single host):

```bash
# 1. DB — sqlite or pg_dump
sqlite3 data/app.db ".backup '$(date +data/backups/app-%F.db)'"   # SQLite
pg_dump "$DATABASE_URL" -F c -f data/backups/odysseus-$(date +%F).dump  # Postgres

# 2. MinIO bucket
mc alias set odysseusminio http://10.55.110.130:32100 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY"
mc mirror --overwrite odysseusminio/networkchange-docs backups/minio/$(date +%F)/

# 3. Qdrant snapshots
curl -X POST "$QDRANT_URL/collections/odysseus_rag/snapshots"
# download the snapshot from the link returned in the response

# 4. .env (the secrets!) — separately, encrypted
tar czf backups/secrets-$(date +%F).tgz .env data/auth.json
```

`scripts/odysseus-backup` automates pieces of this.

## Failure modes & observability

| Symptom | Likely cause | Where to look |
|---|---|---|
| "object store not healthy" log + library docs still work | `ODYSSEUS_USE_MINIO=true` but the cluster is down; falls back to local disk | `src/object_store.py::healthy` flag; `docker compose logs odysseus \| grep object_store` |
| `Format error in JSON body: value … is not a valid point ID` (Qdrant 400) | String ID was sent instead of UUID/int | `src/rag_vector.py::_generate_doc_id` — must produce `uuid.uuid4()` or `uuid.uuid5(...)` |
| Document content search returns nothing for a doc that exists | PUT/PATCH path was used; see [Update caveat](#document-body-storage--what-gets-written-when) | `scripts/backfill_rag_documents.py --apply --resync` |
| Non-admin user can't see legacy doc | `owner=NULL` until `_migrate_assign_legacy_owner` runs | `scripts/claim_ownerless.py --user <u>` |
| `mc` shows objects with the old key layout | Pre-refactor MinIO data | `scripts/migrate_minio_paths.py` |
