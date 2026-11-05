# Standalone source manifest

## Provenance

- Package name: `nc_v7_monolith`
- Prepared: 2026-09-24
- Base source: `network-change`
- Base Git commit: `b192a4086929b64f36e0ba693d5d6e6c273fc794`
- Base commit date: 2026-08-24T16:44:03+07:00
- Base commit subject: `update first network-change project`

The base was copied from committed source rather than the runtime working tree.
Runtime databases, logs, sessions, uploads, bytecode, local virtualenvs, IDE
metadata, generated metrics, `.env`, and plaintext Kubernetes Secrets were not
carried into this package.

## Monolith additions

- `src/network_change_tools.py`: snapshot packaging, comparison, static
  validation, proposal persistence, deferred artifact materialization, and history.
- `src/multiagent.py`: opt-in Coordinator–Retriever–Generator–Critic pipeline,
  mutating intent gate, role tool isolation, bounded draft repair, and child
  session cleanup.
- `core/database.py`: `NetworkSnapshotRecord` and `NetworkChangeProposal`.
- `alembic/versions/0006_network_change_records.py`: owner-scoped domain tables.
- Tool registration in `src/agent_tools.py`, `src/tool_schemas.py`,
  `src/tool_parsing.py`, `src/tool_execution.py`, and `src/tool_index.py`.
- English and Vietnamese network-change intent promotion in
  `src/action_intents.py`.
- Domain/regression tests in `tests/test_network_change_tools.py`.
- Multi-agent intent/tool-isolation regressions in `tests/test_multiagent.py`.
- Deployment fixes for the services-cache mount, non-root Kubernetes startup,
  image naming, and out-of-band Secrets.
- Self-hosted Mermaid 11.16.1 frontend bundle and document-preview rendering,
  so fenced `mermaid` diagrams work without public CDN access. The upstream
  MIT license is retained at `static/lib/mermaid.LICENSE.txt`.
- Version-controlled 4G/EPC reference data under `knowledge_base/`, plus
  `scripts/ingest_network_knowledge.py` for owner-scoped Qdrant ingestion.
- `core/app_profile.py`: Network Change route/tool allow-list with a legacy
  rollback profile.
- `src/tool_registry.py` and `routes/tool_registry_routes.py`: canonical
  built-in/MCP registry and per-session disabled/auto/pinned preferences.
- `routes/knowledge_routes.py`: bundled and UI-upload knowledge ingestion.
- `src/generated_file_store.py`: local `data/generated/` document mirror.
- `mcp_servers/k8s_sandbox_server.py`: optional lab-only Kubernetes dry-run and
  disposable namespace adapter; no credentials are bundled.
- Prompt history/tool palette/knowledge/validation UI modules under `static/`.
- `.env.example`, `.gitignore`, `.dockerignore`, agent handoff, deployment
  documentation, and a standard-library package verifier.
- `docs/ARCHITECTURE_MULTIAGENT_2026-09-24_VI.md`: Vietnamese implemented-state
  report and sequence diagram for the guarded role pipeline.

## Explicitly absent

- Production change execution and approval APIs.
- ACE or other self-evolving memory/training loops.
- Separate multi-agent/A2A services and per-agent ModelRouter instances. The
  guarded roles run inside the monolith and reuse the generic endpoint resolver.
- Batfish and digital-twin simulation.
- Bundled Kubernetes client, kubeconfig, or cluster credentials. The optional
  sandbox adapter invokes an installed `kubectl` binary with an operator-set
  sandbox-only kubeconfig.
- Real internal passwords, tokens, API keys, or registry credentials.

## Expected top-level entry points

- Application: `app.py`
- Container: `Dockerfile`
- Local composition: `docker-compose.yml`
- Kubernetes: `k8s/kustomization.yaml`
- Dependencies: `requirements.txt`
- Database migrations: `alembic.ini` and `alembic/versions/`
- Agent instructions: `AGENTS.md`
- Package verifier: `scripts/verify_monolith_source.py`
