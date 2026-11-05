"""Multi-agent policy pipeline tests — intent gate and role tool policy.

Pure-logic tests only (regexes, policy sets, settings gate): no database rows.
DB-lifecycle tests (defer/materialize/redact) live in
tests/test_multiagent_lifecycle.py."""

import sys

# Importing src.multiagent needs the real src.endpoint_resolver /
# llm_core chain; a sibling test collected earlier (e.g. test_companion_pairing)
# may have replaced those entries with partial stubs. Swap in the real modules
# for the import, then restore whatever was there so sibling lazy imports are
# unaffected (same save/restore approach as test_multiagent_lifecycle.py).
_STUBBED = ("src.multiagent", "src.endpoint_resolver", "src.llm_core",
            "src.database", "core.database")
_SAVED = {name: sys.modules.pop(name) for name in _STUBBED if name in sys.modules}

import json
from unittest.mock import patch

import pytest

from src.multiagent import (
    _is_network_change_request,
    _parse_json_object,
    _read_only_mcp_names,
    _role_tool_policy,
    network_change_multiagent_enabled,
    should_use_network_change_pipeline,
)

for _name, _mod in _SAVED.items():
    sys.modules[_name] = _mod


# ── Intent gate ────────────────────────────────────────────────────────────

def test_mutating_english_network_requests_trigger_pipeline():
    assert _is_network_change_request("scale the api deployment to 3 replicas in kubernetes")
    assert _is_network_change_request("deploy the new manifest to the production namespace")
    assert _is_network_change_request("delete the old ingress route")
    assert _is_network_change_request("rollout restart the api pods across the cluster")


def test_mutating_vietnamese_network_requests_trigger_pipeline():
    assert _is_network_change_request("thay đổi cấu hình mạng cho deployment api")
    assert _is_network_change_request("triển khai manifest mới lên cluster k8s")
    assert _is_network_change_request("khởi động lại các pod trong namespace default")


def test_artifact_requests_trigger_pipeline():
    assert _is_network_change_request("generate the kubectl commands for the 5g upf migration")
    assert _is_network_change_request("draft a manifest yaml for the new networkpolicy")


def test_read_only_and_offtopic_requests_do_not_trigger():
    assert not _is_network_change_request("show me the pods in the default namespace")
    assert not _is_network_change_request("list the deployments and their status")
    assert not _is_network_change_request("explain how kubernetes rollout restart works")
    assert not _is_network_change_request("scale is a word but there is no infrastructure context here")
    assert not _is_network_change_request("")
    assert not _is_network_change_request(None)


def test_pipeline_gate_requires_toggle_and_intent():
    with patch("src.settings.get_user_setting", return_value=False):
        assert not should_use_network_change_pipeline("scale the k8s deployment", "alice")
        assert not should_use_network_change_pipeline("what pods are running", "alice")
    with patch("src.settings.get_user_setting", return_value=True):
        assert should_use_network_change_pipeline("scale the k8s deployment", "alice")
        assert not should_use_network_change_pipeline("what pods are running", "alice")


def test_enabled_parses_string_on_values():
    for raw in ("1", "true", "yes", "on", "On", "TRUE"):
        with patch("src.settings.get_user_setting", return_value=raw):
            assert network_change_multiagent_enabled("alice"), raw
    for raw in ("", "0", "false", "no", "off"):
        with patch("src.settings.get_user_setting", return_value=raw):
            assert not network_change_multiagent_enabled("alice"), raw


def test_parse_json_object_extracts_from_fenced_prose():
    assert _parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert _parse_json_object('Sure! Here it is: {"b": [2]} hope that helps') == {"b": [2]}
    assert _parse_json_object("[1, 2]") is None
    assert _parse_json_object("no json here") is None


# ── Role tool policy ──────────────────────────────────────────────────────

def _mcp_tool(name, server_id="k8s", description=""):
    return {"name": name, "description": description, "server_id": server_id}


def test_generator_policy_only_allows_prepare_network_change():
    allowed, disabled = _role_tool_policy("generator", owner=None)
    assert allowed == {"prepare_network_change"}
    # Every builtin and MCP tool bar the one artifact path is disabled.
    assert "bash" in disabled
    assert "prepare_network_change" not in disabled


def test_retriever_policy_rejects_mutating_mcp_tools():
    mcp_tools = [
        _mcp_tool("list_pods", description="list pods in namespace"),
        _mcp_tool("get_deployment", description="describe one deployment"),
        _mcp_tool("delete_pod", description="delete a pod"),
        _mcp_tool("apply_manifest", description="apply a manifest"),
        _mcp_tool("restart_deployment", description="restart rollout"),
    ]
    allowed_ro = _read_only_mcp_names(mcp_tools)
    assert "mcp__k8s__list_pods" in allowed_ro
    assert "mcp__k8s__get_deployment" in allowed_ro
    assert "mcp__k8s__delete_pod" not in allowed_ro
    assert "mcp__k8s__apply_manifest" not in allowed_ro
    assert "mcp__k8s__restart_deployment" not in allowed_ro


def test_retriever_policy_includes_read_only_builtins():
    allowed, disabled = _role_tool_policy("retriever", owner=None)
    assert {"search_knowledge", "collect_network_snapshot", "compare_network_snapshots"} <= allowed
    assert "prepare_network_change" in disabled
    assert "bash" in disabled
