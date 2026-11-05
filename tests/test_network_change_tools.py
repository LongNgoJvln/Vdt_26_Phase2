import json
import importlib.util
from pathlib import Path
import uuid

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from core.database import NetworkChangeProposal, NetworkSnapshotRecord, get_db_session
from src.action_intents import message_needs_tools
from src.network_change_tools import (
    do_collect_network_snapshot,
    do_compare_network_snapshots,
    do_get_network_change_history,
    do_prepare_network_change,
    do_validate_change_artifact,
)
from src.agent_tools import function_call_to_tool_block


def payload(result):
    return json.loads(result.get("output") or result.get("error"))


@pytest.fixture
def owner():
    value = f"network-change-test-{uuid.uuid4()}"
    yield value
    with get_db_session() as db:
        db.query(NetworkChangeProposal).filter(NetworkChangeProposal.owner == value).delete()
        db.query(NetworkSnapshotRecord).filter(NetworkSnapshotRecord.owner == value).delete()


@pytest.mark.asyncio
async def test_snapshot_redacts_secrets_and_removes_volatile_metadata(owner):
    result = await do_collect_network_snapshot(json.dumps({
        "cluster": "lab-a",
        "namespace": "default",
        "observations": [{
            "source": "mcp__k8s__get_resources",
            "kind": "Deployment",
            "data": {
                "metadata": {"name": "api", "resourceVersion": "42", "managedFields": [1]},
                "token": "do-not-store",
                "spec": {"replicas": 2},
            },
        }, {
            "source": "mcp__k8s__get_resources",
            "kind": "Secret",
            "data": {"tls.crt": "certificate bytes"},
        }],
    }), owner=owner)

    assert result["exit_code"] == 0
    snapshot = payload(result)["snapshot"]
    stored = await do_get_network_change_history(
        json.dumps({"record_type": "snapshot", "action": "get", "id": snapshot["id"]}),
        owner=owner,
    )
    data = payload(stored)["snapshot"]["observations"][0]["data"]
    assert data["token"] == "[REDACTED]"
    assert data["metadata"] == {"name": "api"}
    assert payload(stored)["snapshot"]["observations"][1]["data"] == "[REDACTED KUBERNETES SECRET]"
    assert len(snapshot["content_hash"]) == 64

    other_history = await do_get_network_change_history(
        json.dumps({"record_type": "snapshot", "action": "get", "id": snapshot["id"]}),
        owner="someone-else",
    )
    assert other_history["exit_code"] == 1


@pytest.mark.asyncio
async def test_compare_inline_snapshots_returns_field_paths():
    result = await do_compare_network_snapshots(json.dumps({
        "baseline": {"observations": [{"replicas": 2}]},
        "current": {"observations": [{"replicas": 3}]},
    }))
    result_data = payload(result)
    assert result_data["changed"] is True
    assert result_data["diffs"] == [{
        "path": "$[0].replicas",
        "change": "changed",
        "before": 2,
        "after": 3,
    }]


@pytest.mark.asyncio
async def test_validation_is_static_and_flags_mutating_artifact():
    result = await do_validate_change_artifact(json.dumps({
        "artifact": {"format": "cli", "content": "kubectl delete deployment api"},
    }))
    assert result["exit_code"] == 0
    result_data = payload(result)
    assert result_data["risk"] == "high"
    assert result_data["execution_allowed"] is False
    assert any("never run" in warning for warning in result_data["warnings"])
    assert any("rollback" in warning for warning in result_data["warnings"])

    invalid = await do_validate_change_artifact(json.dumps({
        "artifact": {"format": "yaml", "content": "image: ${IMAGE_TAG}"},
    }))
    assert invalid["exit_code"] == 1
    assert payload(invalid)["passed"] is False


@pytest.mark.asyncio
async def test_prepare_proposal_requires_evidence_and_never_executes(owner):
    snapshot_result = await do_collect_network_snapshot(json.dumps({
        "cluster": "lab-a",
        "observations": [{"source": "mcp__k8s__get", "data": {"healthy": True}}],
    }), owner=owner)

    result = await do_prepare_network_change(json.dumps({
        "objective": "Scale the API deployment from two to three replicas",
        "target": {"cluster": "lab-a", "namespace": "default", "kind": "Deployment", "name": "api"},
        "snapshot_id": payload(snapshot_result)["snapshot"]["id"],
        "plan": {"stages": [
            {"name": "observe", "outcome": "baseline captured"},
            {"name": "draft", "outcome": "review manifest"},
        ]},
        "artifact": {"format": "yaml", "content": "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: api\nspec:\n  replicas: 3\n"},
        "rollback": {"artifact": "restore replicas: 2"},
    }), owner=owner)

    assert result["exit_code"] == 0
    result_data = payload(result)
    assert result_data["execution_allowed"] is False
    assert result_data["proposal"]["status"] == "ready_for_review"
    assert result_data["proposal"]["validation"]["passed"] is True


def test_network_change_intents_and_native_schema_conversion():
    assert message_needs_tools("prepare a Kubernetes change proposal for deployment api")
    assert message_needs_tools("lập kế hoạch thay đổi network cho deployment api")
    assert message_needs_tools("so sánh network snapshot trước và sau")
    assert not message_needs_tools("explain what a Kubernetes change proposal is")
    assert not message_needs_tools("giải thích network change là gì")

    block = function_call_to_tool_block(
        "collect_network_snapshot",
        json.dumps({"observations": [{"source": "mcp", "data": {"ok": True}}]}),
    )
    assert block.tool_type == "collect_network_snapshot"
    assert json.loads(block.content)["observations"][0]["data"]["ok"] is True


def test_network_change_migration_creates_both_tables(tmp_path):
    migration_path = Path(__file__).parents[1] / "alembic" / "versions" / "0006_network_change_records.py"
    spec = importlib.util.spec_from_file_location("migration_0006", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = sa.create_engine(f"sqlite:///{tmp_path / 'migration.db'}")
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE sessions (id VARCHAR PRIMARY KEY)"))
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        inspector = sa.inspect(connection)
        assert "network_snapshots" in inspector.get_table_names()
        assert "network_change_proposals" in inspector.get_table_names()
        proposal_columns = {column["name"] for column in inspector.get_columns("network_change_proposals")}
        assert {"snapshot_id", "plan_json", "validation_json", "risk", "status"} <= proposal_columns
