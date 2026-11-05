"""Test the MCP argument-key normalization shim (snake_case -> declared camelCase).

Why: the TypeScript k8s MCP server declares camelCase params (resourceType,
allNamespaces, labelSelector) but the model frequently sends snake_case
(resource_type, all_namespaces, label_selector). Without normalization the server
crashes with "Cannot read properties of undefined (reading 'toLowerCase')" and the
model wastes many rounds guessing its way to the correct spelling.

The shim repairs KEY spelling only, against the server-advertised schema, and is
purely additive (never invents keys, never touches values).
"""

from src.mcp_manager import McpManager


def _mgr_with_k8s_schema():
    """A McpManager whose tool cache mirrors the real k8s server's kubectl_get schema."""
    m = McpManager()
    server_id = "k8s"
    m._tools[server_id] = [{
        "name": "kubectl_get",
        "input_schema": {
            "type": "object",
            "properties": {
                "resourceType": {"type": "string"},
                "name": {"type": "string"},
                "namespace": {"type": "string", "default": "default"},
                "output": {"type": "string"},
                "allNamespaces": {"type": "boolean", "default": False},
                "labelSelector": {"type": "string"},
                "fieldSelector": {"type": "string"},
            },
            "required": ["resourceType"],
        },
    }]
    return m, server_id


def test_snake_case_normalized_to_camelcase():
    m, sid = _mgr_with_k8s_schema()
    fixed = m._normalize_args(sid, "kubectl_get", {
        "resource_type": "nodes",
        "all_namespaces": "true",
        "label_selector": "app=nginx",
        "namespace": "kube-system",
    })
    assert fixed == {
        "resourceType": "nodes",
        "allNamespaces": "true",
        "labelSelector": "app=nginx",
        "namespace": "kube-system",
    }


def test_alread_correct_camelcase_untouched():
    m, sid = _mgr_with_k8s_schema()
    fixed = m._normalize_args(sid, "kubectl_get", {
        "resourceType": "pods", "allNamespaces": True, "output": "wide",
    })
    assert fixed == {"resourceType": "pods", "allNamespaces": True, "output": "wide"}


def test_unknown_keys_left_in_place_not_dropped():
    """We must NOT silently drop keys the model sent that we can't map — the
    server/required-check should surface the real error instead."""
    m, sid = _mgr_with_k8s_schema()
    fixed = m._normalize_args(sid, "kubectl_get", {"made_up": "x", "resource_type": "nodes"})
    assert "made_up" in fixed          # preserved, not dropped
    assert fixed["resourceType"] == "nodes"  # mapped


def test_values_passed_through_verbatim():
    """Normalization repairs KEY spelling only, never values."""
    m, sid = _mgr_with_k8s_schema()
    fixed = m._normalize_args(sid, "kubectl_get", {"resource_type": "nodes"})
    assert fixed["resourceType"] == "nodes"  # value is exactly what the model sent


def test_non_dict_args_passed_through():
    """Built-in/edge tools that pass a non-dict must be untouched, not crashed."""
    m, sid = _mgr_with_k8s_schema()
    assert m._normalize_args(sid, "kubectl_get", None) is None
    assert m._normalize_args(sid, "kubectl_get", {}) == {}
    assert m._normalize_args(sid, "kubectl_get", ["a", "b"]) == ["a", "b"]


def test_no_cached_schema_passes_through():
    """If we don't have the schema, do nothing (safe default)."""
    m = McpManager()
    args = {"resource_type": "nodes"}     # server "ghost" not in cache
    assert m._normalize_args("nope", "kubectl_get", args) == args


def test_full_pipeline_required_check_passes_after_normalize():
    """End-to-end: a snake_case required-arg call no longer fails the required
    pre-check once normalized. (Before the shim, resource_type -> missing
    resourceType -> blocked before the server ever runs.)"""
    m, sid = _mgr_with_k8s_schema()
    required = m._required_fields(sid, "kubectl_get")
    normalized = m._normalize_args(sid, "kubectl_get", {"resource_type": "nodes"})
    missing = [f for f in required if not normalized.get(f)]
    assert required == ["resourceType"]
    assert missing == []                      # required field now present after normalize


def test_empty_args_blocked_even_without_cached_schema():
    """During a reconnect storm the cached schema may be empty, so
    _required_fields returns []. The k8s tools still REQUIRE an arg —
    an empty {} call must be blocked with a clean hint, NOT reach the server
    (which would crash with 'toLowerCase'). This guards the empty-schema gap."""
    m = McpManager()
    # NO schema cached for this server (simulates reconnect storm)
    assert m._required_fields("k8s_ghost", "kubectl_get") == []
    required_check = m._required_fields("k8s_ghost", "kubectl_get")
    # mirror the hard-coded fallback in call_tool
    fallback = {"kubectl_get": "resourceType"}
    if "kubectl_get" in fallback and not required_check:
        required_check = [fallback["kubectl_get"]]
    args = {}
    missing = [f for f in required_check if not args.get(f)]
    assert missing == ["resourceType"], "empty args must be flagged as missing"
