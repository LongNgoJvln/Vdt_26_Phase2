# Network-change monolith

This build keeps the original single FastAPI application, frontend, model
endpoint picker, MCP administration, tool index, agent loop, document/RAG
features, and owner-scoped storage. Ordinary work uses the same general-purpose
agent. Mutating network-change requests can be routed through an opt-in,
in-process Coordinator–Retriever–Generator–Critic pipeline.

## Deliberate boundaries

- Kubernetes and network state are read through MCP servers configured in the
  existing Admin UI. The domain layer has no kubeconfig and does not run
  `kubectl`.
- MCP access and tool discovery remain generic. A read-only Kubernetes MCP can
  be added, disabled, or replaced without changing this source.
- This version creates evidence snapshots, diffs, validations, reports, and
  change proposals. It has no approval or execution endpoint.
- Optional Kubernetes execution testing is isolated in
  `mcp_servers/k8s_sandbox_server.py`. It requires a different sandbox
  kubeconfig, rejects cluster-scoped resources, uses server-side dry-run first,
  and cleans up its disposable namespace. It never grants the monolith a
  production write path.
- ACE, self-evolution, free-form A2A orchestration, Batfish, digital-twin
  simulation, automatic rollback, and repair execution are not included. The
  fixed role pipeline may regenerate a rejected draft up to two times.

## Agent workflow

The normal agent loop is still dynamic: it retrieves a small relevant tool set,
calls tools, inspects results, and continues until the task is complete.
Ordinary queries, document creation, report generation, and MCP administration
do not fit a global policy pipeline.

When `network_change_multiagent=true` and the intent gate detects a mutating
network/Kubernetes request, `src/multiagent.py` runs a fixed directed pipeline:

1. **Coordinator** decomposes the request without producing commands.
2. **Retriever** runs in a child session with `search_knowledge`, snapshot tools,
   and dynamically discovered read-only MCP tools only.
3. **Generator** runs in another child session. Its only artifact-producing tool
   is `prepare_network_change`; document, file, shell, Python, lateral dispatch,
   and MCP tools are blocked at execution.
4. **Critic gate** calls `do_validate_change_artifact` directly on the exact
   artifact bytes. This deterministic result—not an LLM opinion—decides pass or
   block. A configured Critic model may only summarize the safe metadata.
5. A valid artifact document is materialized in the parent chat only after the
   gate passes. Failed CLI bytes are removed from stored invalid audit records.
6. Failed drafts can be regenerated twice. Exhaustion returns `BLOCKED` and
   creates no command/manifest file.

The toggle defaults to off. Requests such as “get the Kubernetes system and
create a report” remain on the existing loop even when the toggle is enabled.

For a change proposal on the ordinary loop (toggle off), the intended sequence
remains:

1. Call one or more externally configured read-only MCP tools.
2. Call `collect_network_snapshot` with those returned observations.
3. Optionally call `compare_network_snapshots` for baseline/current drift.
4. Call `validate_change_artifact` while drafting the manifest/config/CLI text.
   Static-only output is `partially_verified`.
5. If a dedicated sandbox MCP is configured, call its dry-run/apply tool and
   pass the unmodified result back as `sandbox_result` for deterministic status.
6. Call `prepare_network_change` to save the evidence-linked proposal and its
   command-only editable artifact.
7. Use `create_document` for other readable reports or exportable files.

The bounded retries, stall detection, verifier, fallback models, and per-run
tool budgets already implemented by `src/agent_loop.py` apply to these tools in
the same way as all other built-ins.

The guarded pipeline uses separate low ceilings (`8` rounds and `12` tool calls
per worker), creates transient owner-scoped child sessions, and deletes them at
the end. A single application image is still deployed; roles are not services.

## Stored records

Postgres (or SQLite for local development) stores two new owner-scoped tables:

- `network_snapshots`: target, sanitized observations, warnings, capture time,
  and a canonical SHA-256 content hash.
- `network_change_proposals`: objective, target, staged plan, artifact,
  validation result, evidence, risk, and review status.

Credential-like fields are redacted from packaged observations, volatile
Kubernetes metadata (`managedFields`, `resourceVersion`, `selfLink`) is removed,
snapshot payloads are capped at 5 MiB, and comparisons are capped at 500 diffs.
These operational records are not written into agent memory or used for
self-evolution.

## Deployment

Build one application image from this directory:

```sh
docker build -t nc-v7-monolith:latest .
docker compose up -d
```

The Kubernetes manifests expect an `app-env` Secret to be created out of band;
secrets are intentionally not stored in the repository:

```sh
cp .env.example .env.k8s
# Set real values in .env.k8s, then:
kubectl -n hw5gai create secret generic app-env \
  --from-env-file=.env.k8s --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -k k8s/
```

Postgres migrations run automatically at startup. Migration
`0006_network_change_records` creates the domain tables.
