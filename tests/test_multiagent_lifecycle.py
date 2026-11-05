"""DB-lifecycle tests for the multi-agent policy pipeline — defer, materialize,
redact around prepare_network_change.

These tests need the REAL core.database (actual FK constraints and rows), so the
conftest/sibling-test module stubs are swapped out at import time and RESTORED
afterward. Bindings made below stay real for this module regardless of what a
later-collected sibling test does to sys.modules (mirrors the isolation approach
of test_webhook_ssrf_resilience.py, plus restore so sibling collection order
never breaks either direction)."""

import sys

_STUBBED = ("src.multiagent", "src.network_change_tools", "src.endpoint_resolver",
            "src.tool_implementations", "src.llm_core", "src.database", "core.database")
_SAVED = {name: sys.modules.pop(name) for name in _STUBBED if name in sys.modules}

import json
import uuid

import pytest

from core.database import (
    NetworkChangeProposal,
    NetworkSnapshotRecord,
    Session,
    get_db_session,
)
from src.network_change_tools import (
    defer_artifact_document_creation,
    do_collect_network_snapshot,
    do_prepare_network_change,
    materialize_network_change_artifact,
    redact_blocked_proposal_artifact,
)

import src.database as _real_src_database
import core.database as _real_core_database

# Put sibling tests' stubs back so their lazy imports still see them.
for _name, _mod in _SAVED.items():
    sys.modules[_name] = _mod


@pytest.fixture(autouse=True)
def _real_database_modules():
    """Swap the real DB modules in for this test's duration.

    do_create_document imports from src.database lazily at call time, so a
    conftest/sibling stub still installed in sys.modules would break document
    creation even though this file's own bindings are real."""
    prior = {name: sys.modules.get(name) for name in ("src.database", "core.database")}
    sys.modules["src.database"] = _real_src_database
    sys.modules["core.database"] = _real_core_database
    try:
        yield
    finally:
        for name, module in prior.items():
            if module is not None:
                sys.modules[name] = module


def payload(result):
    return json.loads(result.get("output") or result.get("error"))


@pytest.fixture
def owner():
    value = f"multiagent-test-{uuid.uuid4()}"
    yield value
    # Proposals FK-reference the parent session; clean both up. All models are
    # module-level bindings — a sibling test may have replaced sys.modules by
    # teardown time, and lazy imports would re-resolve to its stub.
    with get_db_session() as db:
        db.query(NetworkChangeProposal).filter(NetworkChangeProposal.owner == value).delete()
        db.query(NetworkSnapshotRecord).filter(NetworkSnapshotRecord.owner == value).delete()
        db.query(Session).filter(Session.owner == value).delete()


@pytest.fixture
def parent_session(owner):
    """A real parent chat session row (proposals FK-reference sessions.id)."""
    session_id = f"nc-parent-{uuid.uuid4()}"
    with get_db_session() as db:
        db.add(Session(id=session_id, name="[test] multiagent parent",
                       endpoint_url="http://localhost:1", model="test", owner=owner))
    yield session_id


async def _seed_proposal(owner, session_id, *, valid=True):
    snapshot = await do_collect_network_snapshot(json.dumps({
        "cluster": "lab-a",
        "observations": [{"source": "mcp__k8s__list_pods", "data": {"healthy": True}}],
    }), owner=owner)
    artifact = (
        {"format": "yaml", "content": "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: api\nspec:\n  replicas: 3\n"}
        if valid
        else {"format": "yaml", "content": "image: ${PLACEHOLDER}"}
    )
    return await do_prepare_network_change(json.dumps({
        "objective": "Scale the API deployment from two to three replicas",
        "target": {"cluster": "lab-a", "kind": "Deployment", "name": "api"},
        "snapshot_id": payload(snapshot)["snapshot"]["id"],
        "plan": {"stages": [{"name": "scale", "outcome": "replicas 3"}]},
        "artifact": artifact,
        "rollback": {"artifact": "restore replicas: 2"},
    }), session_id=session_id, owner=owner)


@pytest.mark.asyncio
async def test_deferred_generation_creates_no_document(owner, parent_session):
    with defer_artifact_document_creation():
        # valid=True normally mints a doc immediately when a parent session
        # is set; inside the defer context it must not.
        result = await _seed_proposal(owner, parent_session, valid=True)
    assert result["exit_code"] == 0
    assert payload(result)["artifact_document"] is None


@pytest.mark.asyncio
async def test_materialize_creates_document_after_gate(owner, parent_session):
    result = await _seed_proposal(owner, parent_session, valid=True)
    assert result["exit_code"] == 0
    proposal_id = payload(result)["proposal"]["id"]

    materialized = await materialize_network_change_artifact(proposal_id, parent_session, owner=owner)
    assert not materialized.get("error"), materialized
    assert materialized["doc_id"]
    assert materialized["language"] == "kubernetes"
    assert "replicas: 3" in materialized["content"]


@pytest.mark.asyncio
async def test_materialize_rejects_non_ready_proposal(owner, parent_session):
    result = await _seed_proposal(owner, parent_session, valid=False)
    assert result["exit_code"] == 1
    proposal_id = payload(result)["proposal"]["id"]

    materialized = await materialize_network_change_artifact(proposal_id, parent_session, owner=owner)
    assert materialized.get("error")


@pytest.mark.asyncio
async def test_redact_blocked_proposal_removes_bytes(owner, parent_session):
    result = await _seed_proposal(owner, parent_session, valid=False)
    proposal_id = payload(result)["proposal"]["id"]

    redact_blocked_proposal_artifact(proposal_id, parent_session, owner=owner)
    with get_db_session() as db:
        row = db.query(NetworkChangeProposal).filter(NetworkChangeProposal.id == proposal_id).first()
        assert row.status == "redacted"
        assert "${PLACEHOLDER}" not in (row.artifact_json or "")
        assert "REDACTED" in (row.artifact_json or "")

    # Redaction is idempotent.
    redact_blocked_proposal_artifact(proposal_id, parent_session, owner=owner)


@pytest.mark.asyncio
async def test_redact_ignores_other_owners(owner, parent_session):
    result = await _seed_proposal(owner, parent_session, valid=False)
    proposal_id = payload(result)["proposal"]["id"]
    # A different owner's redaction call must not touch this row.
    redact_blocked_proposal_artifact(proposal_id, parent_session, owner="someone-else")
    with get_db_session() as db:
        row = db.query(NetworkChangeProposal).filter(NetworkChangeProposal.id == proposal_id).first()
        assert row.status == "invalid"  # untouched


@pytest.mark.asyncio
async def test_materialize_normalizes_mime_format_alias(owner, parent_session):
    from core.database import NetworkChangeProposal
    import src.network_change_tools as nct

    snapshot = await do_collect_network_snapshot(json.dumps({
        "cluster": "lab-a",
        "observations": [{"source": "mcp__k8s__list_pods", "data": {"healthy": True}}],
    }), owner=owner)
    # Generator LLMs often declare a MIME type; the gate must still accept it.
    result = await do_prepare_network_change(json.dumps({
        "objective": "Scale the API deployment",
        "target": {"cluster": "lab-a", "kind": "Deployment", "name": "api"},
        "snapshot_id": payload(snapshot)["snapshot"]["id"],
        "plan": {"stages": [{"name": "scale", "outcome": "replicas 3"}]},
        "artifact": {"format": "text/x-shellscript", "content": "kubectl scale deployment api --replicas=3\n"},
        "rollback": {"command": "kubectl scale deployment api --replicas=2"},
    }), session_id=parent_session, owner=owner)
    assert result["exit_code"] == 0
    proposal_id = payload(result)["proposal"]["id"]

    materialized = await materialize_network_change_artifact(proposal_id, parent_session, owner=owner)
    assert not materialized.get("error"), materialized
    assert materialized["language"] == "network-cli"
    assert "--replicas=3" in materialized["content"]
