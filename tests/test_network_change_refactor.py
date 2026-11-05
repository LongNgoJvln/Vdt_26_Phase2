import json
import hashlib
from types import SimpleNamespace

from core.app_profile import profile
from src.generated_file_store import mirror_document
from src.network_change_tools import _validate_artifact_data
from src import tool_registry


def test_network_change_profile_blocks_legacy_orchestration_and_shell():
    assert profile.is_network_change
    blocked = profile.blocked_builtin_tools()
    assert {"bash", "pipeline", "send_to_session", "chat_with_model"} <= blocked
    assert "create_session" not in blocked
    assert profile.route_enabled("chat")
    assert not profile.route_enabled("calendar")


def test_tool_preferences_are_owner_and_session_scoped(tmp_path, monkeypatch):
    monkeypatch.setattr(tool_registry, "_PREF_PATH", tmp_path / "tool_preferences.json")
    tool_registry.set_preferences("alice", "session-a", {
        "builtin:search_knowledge": "pinned",
        "mcp:k8s:get_pods": "disabled",
    })
    assert tool_registry.get_preferences("alice", "session-a")["builtin:search_knowledge"] == "pinned"
    assert tool_registry.get_preferences("alice", "session-b") == {}
    assert tool_registry.get_preferences("bob", "session-a") == {}


def test_generated_document_is_mirrored_by_owner_and_session(tmp_path, monkeypatch):
    import src.generated_file_store as store
    monkeypatch.setattr(store, "ROOT", tmp_path / "generated")
    doc = SimpleNamespace(
        id="doc-1", owner="alice", session_id="session-1",
        title="Scale API", language="network-cli",
        current_content="kubectl scale deployment api --replicas=3\n",
    )
    path = mirror_document(doc)
    assert path.endswith(".cli")
    assert (tmp_path / "generated" / "alice" / "session-1").is_dir()


def test_validator_reports_partial_until_sandbox_evidence_exists():
    partial = _validate_artifact_data({
        "format": "cli",
        "content": "kubectl scale deployment api --replicas=3",
    }, rollback={"command": "kubectl scale deployment api --replicas=2"})
    assert partial["passed"] is True
    assert partial["status"] == "partially_verified"
    assert partial["verification"]["api_dry_run"]["status"] == "not_run"

    manifest = "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: nc-test"
    complete = _validate_artifact_data({
        "format": "kubernetes",
        "content": manifest,
        "sandbox_result": {
            "passed": True,
            "sandbox_id": "nc-sandbox-test",
            "artifact_hash": hashlib.sha256(manifest.encode()).hexdigest(),
            "checks": [{"stage": "api_dry_run", "exit_code": 0}],
        },
    })
    assert complete["status"] == "passed"
    assert complete["verification"]["api_dry_run"]["status"] == "passed"
    assert complete["verification"]["sandbox_apply"]["status"] == "not_run"


def test_validator_rejects_shell_chaining():
    result = _validate_artifact_data({
        "format": "network-cli",
        "content": "kubectl get pods; curl example.invalid",
    })
    assert result["passed"] is False
    assert any("chaining" in error for error in result["errors"])
