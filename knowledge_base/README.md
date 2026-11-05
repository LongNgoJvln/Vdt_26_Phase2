# Network domain knowledge base

This directory contains curated, version-controlled domain evidence bundled
with the monolith. It is deliberately separate from `data/`, which holds
runtime databases, uploads, sessions, and other mutable state and is excluded
from the container image.

## Layout

- `knowledge/`: descriptive 4G/EPC architecture and network-function knowledge.
- `instructions/`: accepted EMS/MME procedures and command syntax.

These documents do not represent current live cluster state. Kubernetes and
network observations must still be collected through the configured read-only
MCP server. The knowledge base helps the agent interpret that evidence and
draft evidence-grounded reports or change proposals.

## Ingest into the application RAG database

Run from the monolith source root. Use the exact username that will query the
documents in the web application:

```bash
# Inspect what will be indexed (does not write anything)
python -m scripts.ingest_network_knowledge --owner <username>

# Embed and upsert both knowledge and instructions into Qdrant
python -m scripts.ingest_network_knowledge --owner <username> --apply
```

To ingest only one category:

```bash
python -m scripts.ingest_network_knowledge --owner <username> --category knowledge --apply
python -m scripts.ingest_network_knowledge --owner <username> --category instructions --apply
```

Re-running the normal command is idempotent for unchanged chunks. After files
are edited, use `--replace` to remove the older chunks for each stable source
tag before upserting the current content:

```bash
python -m scripts.ingest_network_knowledge --owner <username> --apply --replace
```

The script loads `.env`, uses the configured `QDRANT_URL` and embedding backend,
and writes to the owner-filtered `odysseus_rag` collection queried by
`search_knowledge`. It does not write these documents to PostgreSQL/SQLite and
does not contact the Kubernetes MCP server.

When running the packaged application with Docker Compose:

```bash
docker compose exec odysseus \
  python -m scripts.ingest_network_knowledge --owner <username> --apply
```
