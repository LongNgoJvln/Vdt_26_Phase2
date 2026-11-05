# Validation status

Prepared on 2026-09-11.

## Passed

- Standalone package verifier: PASS.
- Python syntax: 475 source/test Python files parsed successfully.
- Targeted domain and tool-selection regression suite: 36 passed.
- Migration `0006_network_change_records` exercised against a clean SQLite
  database and both domain tables were created.
- Docker Compose/Kubernetes/config YAML parsed successfully.
- All five network-change tools were found in tool tags, native schemas,
  descriptions, dispatcher routing, and English/Vietnamese keyword selection.
- Runtime databases, sessions, logs, bytecode, virtualenvs, `.env`, and
  Kubernetes Secret manifests were removed from the standalone package.
- Known plaintext credentials found in the old deployment manifest were not
  copied into this package.
- Mermaid/Markdown regression checks: 5 passed, including self-hosted bundle,
  service-worker precache, fenced-block conversion, and document-preview render
  invocation. Frontend JavaScript syntax checks also passed.

Targeted test command:

```sh
pytest -q tests/test_network_change_tools.py tests/test_action_intents.py \
  tests/test_tool_index_keyword_boundaries.py tests/test_tool_parsing_nonstring.py \
  tests/test_unknown_tool_calls.py tests/test_tool_support_heuristic.py
```

## Not yet verified on the target server

- Full dependency installation and the full inherited regression suite.
- Docker image build; Docker was unavailable on the preparation workstation.
- Live startup against the internal PostgreSQL, Qdrant, MinIO, embedding, model,
  and SearXNG endpoints.
- Connection to the server's externally configured read-only Kubernetes MCP.
- `/api/health`, `/api/ready`, login, model picker, MCP discovery, and end-to-end
  network-change smoke tests on the deployed image.

Operators should complete the checklist in `docs/INTERNAL_SERVER_DEPLOYMENT.md`
and append environment-specific results here or in their deployment ticket.

## Multi-agent policy refactor — 2026-09-24

Implemented and checked locally:

- Python AST/bytecode compilation passed for `src/multiagent.py`,
  `src/network_change_tools.py`, `src/mcp_manager.py`, `routes/chat_routes.py`,
  `src/settings.py`, and the new tests.
- `node --check static/js/settings.js` passed.
- Intent tests cover mutating English/Vietnamese network requests and confirm
  that read-only Kubernetes reports do not trigger the pipeline.
- Role-policy tests assert that Generator can only use
  `prepare_network_change`, while Retriever rejects mutating MCP tools.
- MCP schema discovery now accepts both `inputSchema` and `input_schema` SDK
  representations before snake_case/camelCase argument normalization.
- Artifact creation is deferred until the deterministic Critic passes; blocked
  proposal bytes are redacted and transient child sessions are cleaned up.

The workstation's checked-in `venv` points to a removed Python 3.11 Windows
runtime, so the new pytest suite could not be executed in that stale environment.
Run the following after creating a fresh Python 3.11+ virtual environment:

```sh
pytest -q tests/test_multiagent.py tests/test_multiagent_lifecycle.py \
  tests/test_network_change_tools.py tests/test_mcp_manager.py \
  tests/test_action_intents.py \
  tests/test_tool_index_keyword_boundaries.py tests/test_tool_parsing_nonstring.py \
  tests/test_unknown_tool_calls.py tests/test_tool_support_heuristic.py
```

Still requires target-server smoke testing: enable the toggle, configure the
role endpoints, verify a safe scale proposal, verify a rejected `sudo`/chained
or namespace-delete command, and confirm no artifact file exists after block.

## Multi-agent completion — 2026-09-24 (this workstation)

Merged the v2 runtime state (fixed mcp schema mapping, qdrant URL, agent tool
timeout) with the multi-agent additions, then completed the unfinished wiring:

- `v2/data/app.db`, `v2/data/logs/app.log`, and `v2/.env` (QDRANT_URL=
  `http://172.20.1.109:30633`) copied in; `.env`'s docker-internal
  `qdrant:6333` value replaced.
- `run_network_change_pipeline` is now dispatched from `routes/chat_routes.py`
  agent mode when `should_use_network_change_pipeline` matches; all other
  traffic still uses `stream_agent_loop`.
- `materialize_network_change_artifact` + `redact_blocked_proposal_artifact`
  implemented in `src/network_change_tools.py` (were referenced but missing).
- The `_DEFER_ARTIFACT_DOCUMENT` ContextVar is now consumed inside
  `do_prepare_network_change`, so deferred (Generator) runs mint no document
  before the Critic gate.
- Settings UI card "Network Change Multi-Agent" (toggle + per-role
  Coordinator/Retriever/Generator/Critic endpoint+model pickers) added to the
  AI tab in `static/index.html` + `static/js/settings.js`; keys already
  allow-listed in `src/settings.py` `_PER_USER_KEYS`.
- `tests/test_multiagent.py` (intent gate + role policy, order-safe) and
  `tests/test_multiagent_lifecycle.py` (defer/materialize/redact with real DB
  rows; module save/restore pattern) added: suite above passes 56/56 on this
  workstation (Python 3.10 venv).

Known test-suite caveat (pre-existing): `tests/conftest.py` and several sibling
test modules (e.g. `test_companion_pairing.py`, `test_companion_readonly.py`)
mutate `sys.modules` at import/collection time without restoring. Full
alphabetical `pytest tests/` runs therefore have order-dependent collection
errors even on the unmodified v2 baseline (`test_chat_image_routing.py`,
`test_webhook_ssrf_resilience.py`). Use the targeted file list above; a
full-suite run excluding the two new test files reproduces exactly the v2
baseline failure set (no regressions introduced).
