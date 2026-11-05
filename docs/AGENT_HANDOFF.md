# Agent handoff

## Architecture baseline before refactor

Báo cáo tiếng Việt
[`ARCHITECTURE_BASELINE_2026-09-14_VI.md`](ARCHITECTURE_BASELINE_2026-09-14_VI.md)
là mốc hiện trạng được bảo toàn trước đợt refactor network-focused. Bản tiếng
Anh tương ứng nằm tại
[`ARCHITECTURE_BASELINE_2026-09-14.md`](ARCHITECTURE_BASELINE_2026-09-14.md).
Không sửa hai baseline để mô tả hành vi tương lai. Khi refactor hoàn tất, tạo
`ARCHITECTURE_POST_REFACTOR_<YYYY-MM-DD>.md` riêng và đối chiếu với baseline.

Báo cáo hậu refactor hiện tại là
[`ARCHITECTURE_POST_REFACTOR_2026-09-14_VI.md`](ARCHITECTURE_POST_REFACTOR_2026-09-14_VI.md).

## Current implementation

This directory is a standalone continuation source. It does not depend on the
old `nc_v7/app`, `nc_v7/frontend`, or sibling `network-change` directory at
runtime. The frontend is served by the same FastAPI process from `static/`, and
the domain functions run inside the same agent tool dispatcher.

The effective request flow is:

```text
user message
  -> action_intents: decide chat vs agent mode
  -> mutating intent + network_change_multiagent toggle?
       -> yes: multiagent directed policy pipeline
       -> no: agent_loop bounded reasoning/tool loop
  -> tool_registry: global/profile + per-session disabled/auto/pinned
  -> tool_index: semantic retrieval + keyword hints cho built-in và MCP
  -> model endpoint selected for the current session
  -> MCP tool calls for live read-only observations
  -> network_change_tools for snapshot/diff/validation/proposal/history
  -> PostgreSQL/SQLite domain records
  -> create_document + data/generated mirror for reports/files
```

There is no separate lead-agent service. `src/multiagent.py` coordinates four
in-process roles for mutating changes only; each role inherits the chat endpoint
unless configured otherwise. Endpoint fallback remains a reliability feature;
cross-model tools and the teacher-escalation/self-writing skill hook are disabled
by the Network Change profile.

## What was preserved from the deployed source

- Full static frontend and authentication/settings surfaces.
- Offline Mermaid rendering for fenced `mermaid` blocks in chat and Markdown
  document preview; the pinned browser bundle lives in `static/lib/`.
- Model endpoint registration, model picker, endpoint discovery, session model,
  utility/teacher selection, and fallback behavior.
- MCP server add/update/delete/reconnect, discovered schemas, disabled tools,
  owner visibility, quarantine, timeout, and reconnect behavior.
- Intent promotion, Qdrant-backed tool index, keyword fallback, and bounded
  number of schemas sent to the model.
- Multi-round agent loop, tool budget, stall detection, verifier, background
  runs, SSE events, and result formatting.
- Documents, files, RAG, memory, MinIO, Qdrant, and Postgres/SQLite support.
  Tasks, notes, calendar, research and integrations remain physically present
  only for compatibility rollback and are not registered in the default profile.

## What was added

### Evidence snapshot

`collect_network_snapshot` receives observations already produced by read-only
MCP calls. It normalizes dictionaries, removes `managedFields`,
`resourceVersion`, and `selfLink`, redacts credential-like keys and Kubernetes
Secret payloads, calculates a canonical SHA-256 hash, and stores an owner-scoped
record.

Snapshot is an evidence package, not merely `kubectl get`. Depending on the MCP
tools selected by the agent it can contain inventory, object specs/status,
events, metrics, logs, configuration facts, and other read-only observations.

### Drift comparison

`compare_network_snapshots` accepts two saved snapshot IDs or inline snapshots.
It produces deterministic field paths and caps output at 500 differences.

### Artifact validation and proposal

`validate_change_artifact` checks empty content, unresolved placeholders,
JSON/YAML syntax, mutating `kubectl` text, shell chaining, inferred risk,
rollback guidance, and size. It returns explicit verification levels. It does
not execute commands.

`prepare_network_change` requires an objective, staged plan, artifact, and
either a snapshot ID or other evidence. Valid proposals become
`ready_for_review`; failed attempts are saved as `invalid` for audit and repair
by a later bounded agent round.

### Guarded role pipeline

`src/multiagent.py` closes the free-document bypass for mutating network-change
requests. The Retriever can only use knowledge, snapshots, and dynamically
identified read-only MCP tools. The Generator can only call
`prepare_network_change`; `disabled_tools` blocks all document/file/shell/MCP
alternatives at execution. Artifact document creation is deferred with a
request-local `ContextVar` (consumed inside `do_prepare_network_change`). The
Critic calls the deterministic validator on the exact bytes, after which a
passing artifact is materialized into the parent session via
`materialize_network_change_artifact`; rejected attempts are scrubbed by
`redact_blocked_proposal_artifact` (status `redacted`, bytes replaced). Failed
bytes are never emitted to chat/file. Maximum repair is two regeneration
rounds.

Dispatch: `routes/chat_routes.py` agent mode routes the request to
`run_network_change_pipeline` when `should_use_network_change_pipeline`
matches (toggle + mutating-network intent, with explanation questions
excluded); all other traffic still uses `stream_agent_loop`.

The feature is disabled by default and controlled in Settings → AI
("Network Change Multi-Agent": toggle + optional per-role endpoint/model
overrides for Coordinator/Retriever/Generator/Critic; blank inherits the chat
model). Read-only network inspection and report requests deliberately remain
on the normal loop.

## Known limitations

- The app is intentionally single-replica. MCP sessions, detached run replay,
  and scheduler/poller coordination remain process-local.
- Snapshot comparison is structural; list reordering may appear as drift.
- Static validation is not a full vendor/Kubernetes semantic validator.
- A separate opt-in `k8s_sandbox_server.py` can perform API dry-run and
  disposable-namespace tests using a dedicated sandbox kubeconfig. Production
  MCP access remains read-only; this is not a digital twin.
- No approval, execution, rollback, or live-system repair executor is wired.
- `agent_runs.py` replay is not restart-durable.
- Some base documentation notes a known document PUT/PATCH-to-Qdrant resync
  caveat; see `docs/STORAGE.md` before changing document persistence.

## Safe next milestones

1. Add API/UI views for saved snapshots and proposals without adding execution.
2. Add schema-aware Kubernetes manifest validation using offline schemas.
3. Improve list-aware diffing with stable resource identity keys.
4. Persist detached agent-run events if restart durability becomes necessary.
5. Add an isolated test/sandbox adapter only after its trust boundary is agreed.
6. Evaluate Batfish only for supported traditional network-device configs; do
   not keep it merely as an unused dependency.
7. Research self-evolving behavior separately before enabling any automatic
   memory/policy updates.

Any move toward live writes requires a new explicit design covering credentials,
scope, authorization, dry-run, approval, idempotency, evidence, rollback, audit,
and failure recovery. Do not infer that authority from the current proposal
tools.
