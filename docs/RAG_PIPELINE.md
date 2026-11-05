# RAG Pipeline

How documents flow from upload to searchable vector, and how the agent (and
chat) retrieves them.

```
                ┌── DB row (documents.current_content)
                │
upload / edit ──┼── MinIO sync ──→ userdata/{owner}/library/{object_name}
                │
                └── RAG ingest ──→ Qdrant collection ──→ points (UUID5 id, 384-dim)
                                      │
                                      └── chunk → embed → upsert
                                      │
search ─────────────────────────────────► Qdrant search (70% vector, 30% keyword)
                                      │
                                      └── top-k hits → agent / chat context
```

> For how the storage backends are wired, see [`STORAGE.md`](STORAGE.md).
> For the database models involved, see [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Ingestion write sites

The function that does the actual chunking + Qdrant put is
`routes/document_routes.py::_ingest_document_to_rag`. It is called from
these sites:

| Caller | Code path | Called? |
|---|---|---|
| `create_document` (POST `/documents`) | `routes/document_routes.py` | ✅ |
| `import_pdf` (POST `/documents/import-pdf`) | `routes/document_routes.py` | ✅ (via PDF form/plain creators) |
| `do_create_document` (AI tool) | `src/tool_implementations.py` | ✅ |
| `do_update_document` (AI tool) | `src/tool_implementations.py` | ✅ |
| `create_form_markdown_document` (PDF form doc) | `src/pdf_form_doc.py` | ✅ |
| `create_plain_pdf_document` (PDF plain doc) | `src/pdf_form_doc.py` | ✅ |
| **`update_document` (PUT `/documents/{id}`)** | `routes/document_routes.py` | ❌ — only `_sync_document_to_minio` |
| **`patch_document` (PATCH `/documents/{id}`)** | `routes/document_routes.py` | ❌ — only `_sync_document_to_minio` |

### ⚠️ The update caveat

**Content updates made via the web UI's PUT/PATCH do NOT re-index into
Qdrant.** The action only calls `_sync_document_to_minio`, so:

- MinIO has the new body.
- The DB row has the new body.
- The Qdrant collection **still has the old body.** Search will return
  outdated text until the doc is re-ingested.

Three workarounds:

1. **Force a re-ingest per doc**: `python -m scripts.backfill_rag_documents --apply --resync`.
2. **Use the agent's `update_document` tool**: that path (in
   `src/tool_implementations.py::do_update_document`) does call
   `_ingest_document_to_rag`.
3. **Delete + recreate**: from the editor, delete the doc and re-upload.
   Both DELETE and POST trigger the correct lifecycle.

This asymmetry is a known gap; the agent-tool path is correct because the
agent has no other way to know it should re-ingest. The route handlers were
left alone to avoid re-embedding on every keystroke-level save.

## Chunking

`_ingest_document_to_rag` chunks the document body before embedding:

- **Size**: 1000 chars (~200 tokens) per chunk.
- **Overlap**: 200 chars between consecutive chunks.
- **Source tag**: stored in Qdrant payload as `source = "doc:{owner}:{doc_id}"`
  so the backfill / delete paths can find every chunk from one doc.

Each chunk's payload carries:
- `document` — the doc title.
- `owner` — for per-user filtering at search time.
- `source` — the dedupe / delete key above.
- `chunk_index` — 0-based, for ordering.
- `text` — the chunk body (returned in search hits).

## Point IDs

Qdrant 1.18 only accepts **UUID or unsigned-int** point ids. The function
`src/rag_vector.py::_generate_doc_id` generates a deterministic `uuid5`:

```python
namespace = uuid.uuid5(uuid.NAMESPACE_DNS, sha256(owner.encode())[:16].hex())
point_id  = uuid.uuid5(namespace, sha256(text.encode()).hexdigest())
```

Why deterministic? Two reasons:
1. **Dedupe** — re-ingesting the same chunk is an idempotent upsert.
2. **Targeted delete** — `_remove_document_from_rag` can compute the same IDs
   and delete just those points, no Qdrant scroll needed.

Memory: [Qdrant Point ID Format](../project_qdrant_point_id_format.md) — if
you ever see `Format error in JSON body: value … is not a valid point ID`,
you sent a string slug by mistake.

## Embeddings

Embeddings are 384-dimensional (`bge-small-en-v1.5` ONNX by default). Two
init paths in `src/embeddings.py`:

1. **Local ONNX** (preferred): `LOCAL_EMBEDDING_PATH` points at a local copy
   of the model directory. No network at runtime, ~120 MB, fast on CPU.
2. **HTTP API** (fallback): `EMBEDDING_URL` + `EMBEDDING_MODEL`. Talks to an
   OpenAI-compatible `/v1/embeddings` endpoint (Ollama, vLLM, …).

When the HTTP endpoint is unreachable, the system falls back to
`fastembed` / `sentence-transformers` and ultimately to keyword-only
retrieval. Logs surface the degrade.

## Collections

| Collection | Holds | Owner filter |
|---|---|---|
| `odysseus_rag` (legacy) | All lib docs in one collection | `owner` in payload |
| `ody-rag-{sanitize(owner)}` (per-user) | One collection per owner | per-collection isolation |
| `vhtna_memories` | Persistent vector memory | `owner` in payload |
| `vhtna_tool_index` | Agent tool index (retrieved per turn) | shared |

The legacy `odysseus_rag` is still the default for the global RAG manager
(`get_rag_manager()`). Per-user collections (`get_rag_manager_for_user(owner)`)
are populated by the Chroma→Qdrant migration:

```bash
python -m scripts.migrate_chroma_to_qdrant --apply
```

## Retrieval

`do_search_knowledge` (`src/tool_implementations.py`) is the agent-facing
entrypoint. For chat, `src/chat_processor.py` calls the same
`rag_manager.search(...)` under the hood.

Hybrid retrieval — **70% vector similarity, 30% keyword overlap**:

```python
final_score = 0.70 * vector_similarity + 0.30 * keyword_score
```

- **Vector similarity**: cosine distance between the query embedding and the
  chunk's vector, returned by Qdrant.
- **Keyword score**: normalized count of query terms appearing in the chunk
  text (case-insensitive; stop-words removed).

Both per-owner scoping and the dedupe-tag filter are applied at Qdrant
search time, so cross-user hits come back empty by construction.

## `read_file` over library documents

The `read_file` tool (agent-facing) is wired to fall back to MinIO for
library documents. In `src/tool_execution.py`:

- If the path resolves to `userdata/{owner}/library/{object_name}`, the tool
  calls `store.get_library_file(owner, object_name)` instead of opening a
  local file.
- The agent never sees the difference — the return is the file body as text.

This is why MinIO sync matters for the agent's behavior: without the
`userdata/{owner}/library/...` key, `read_file` would silently fail or
return stale local-disk data.

## Backfilling

After fixing `_ingest_document_to_rag` (chunking + owner scope + non-silent
errors) several legacy rows predated the fix. Backfill with:

```bash
python -m scripts.backfill_rag_documents              # dry-run
python -m scripts.backfill_rag_documents --apply      # ingest missing
python -m scripts.backfill_rag_documents --apply --resync  # full re-ingest
```

The dry-run queries Qdrant by the `source` tag; any doc whose tag is absent
gets re-ingested. `--resync` ignores presence and re-ingests everything
(useful when the chunking logic itself changed).

Success check:
```bash
curl "$QDRANT_URL/collections/odysseus_rag" | jq '.result.points_count'
```

## End-to-end verification

To confirm a single doc is searchable after ingest:

```python
from src.rag_singleton import get_rag_manager
rag = get_rag_manager()
hits = rag.search("distinctive phrase from the doc", top_k=5, owner="vht")
for h in hits:
    print(h["metadata"].get("source"), h["similarity"], h["document"])
```

Each hit is a dict with `id`, `document`, `metadata`, `distance`,
`similarity`, `vector_similarity`, `keyword_score`. The doc you just
ingested should be rank-1 for a query that uses its distinctive terms.

To delete the probe:
```python
rag.delete_by_source("doc:vht:<doc_id>")   # or per-tag for your collection
```

## Per-component deep dive

| File | Responsibility |
|---|---|
| `routes/document_routes.py::_ingest_document_to_rag` | The one-shot ingest entry: chunks + embeds + upserts. |
| `routes/document_routes.py::_sync_document_to_minio` | The sibling helper that uploads the body to MinIO. |
| `src/rag_vector.py` | Qdrant client wrapper — collections, point ids, upsert scroll. |
| `src/rag_manager.py::RAGManager` | Higher-level wrapper that VectorRAG uses; skills + per-user. |
| `src/rag_singleton.py` | Lazy global RAG manager (legacy `odysseus_rag`). |
| `src/embeddings.py` | Embedding model init (local ONNX / HTTP API / fallback chain). |
| `src/tool_implementations.py::do_search_knowledge` | Agent-facing search tool. |
| `src/tool_execution.py` (around line 181/198/667) | `read_file` MinIO fallback for library docs. |
| `scripts/backfill_rag_documents.py` | Operator backfill CLI. |
| `scripts/migrate_chroma_to_qdrant.py` | One-shot Chroma→Qdrant migration. |
