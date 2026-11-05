"""Smoke test: generate a network-cli artifact, validate it statically, and
have the validator accept synthetic sandbox evidence.

Why this exists:
  * The static validator (``_validate_artifact_data``) is the source of truth
    and never touches a cluster.
  * The sandbox (``mcp_servers/k8s_sandbox_server.py``) is an OPTIONAL, separate
    process that only *produces evidence*; the validator merely consumes a
    ``sandbox_result`` dict handed to it. There is no coded retry loop.
  * These tests pin both behaviors so a CLI artifact can be generated and
    verified with NO container/cluster available — which matches how this
    deployment runs (no Qdrant, no sandbox cluster today). When a sandbox
    cluster is later wired in, the validator's "partially_verified -> passed"
    promotion still holds.
"""

import hashlib
import json

import pytest

from src.network_change_tools import do_validate_change_artifact


def _payload(result):
    """Unwrap the tool Result envelope the do_* helpers return."""
    if isinstance(result, dict):
        if "output" in result and result["output"]:
            return json.loads(result["output"])
        if "error" in result and result["error"]:
            # ``error`` may be a bool (True => the body lives under a sibling
            # 'output'), not always the body — fall through.
            if result["error"] is not True:
                return json.loads(result["error"])
    return result


def make_cli_artifact() -> dict:
    """A clean, generated network-cli artifact (the kind the agent emits)."""
    return {
        "format": "network-cli",
        "content": (
            "# Gather read-only cluster evidence\n"
            "kubectl get nodes -o wide\n"
            "kubectl get pods -A --field-selector=status.phase!=Running\n"
            "kubectl get events -A --sort-by=.lastTimestamp\n"
        ),
    }


def fake_sandbox_result(artifact: dict, *, passed: bool = True,
                        api_dry_run_ok: bool = True, hash_override: str = None) -> dict:
    """Build a sandbox_result envelope the validator accepts.

    Mirrors what mcp_servers/k8s_sandbox_server.py returns (sandbox_id,
    artifact_hash, checks with `stage`+`exit_code`). We recompute the hash the
    SAME way the validator does (sha256 of stripped content) so the evidence is
    legitimately bound to the artifact.
    """
    content_text = str(artifact.get("content", "")).strip()
    artifact_hash = hash_override if hash_override is not None else hashlib.sha256(
        content_text.encode("utf-8")
    ).hexdigest()
    return {
        "sandbox_id": "nc-sandbox-smoke0001",
        "artifact_hash": artifact_hash,
        "passed": bool(passed and api_dry_run_ok),
        "checks": [
            {"stage": "sandbox_namespace_preflight", "exit_code": 0},
            {"stage": "api_dry_run", "exit_code": 0 if api_dry_run_ok else 1},
        ],
        "errors": [],
        "warnings": [],
        "cleanup": {"attempted": True, "passed": True},
    }


# ── Static layer (no cluster, no sandbox) ──────────────────────────────────

@pytest.mark.asyncio
async def test_generated_cli_artifact_passes_static_validation():
    """Generate a CLI artifact and confirm static validation passes."""
    artifact = make_cli_artifact()

    result = await do_validate_change_artifact(json.dumps({"artifact": artifact}))
    body = _payload(result)

    assert body["passed"] is True, body.get("errors")
    assert body["command_count"] == 3          # 3 kubectl lines, comment stripped
    assert body["format"] == "network-cli"
    assert body["verification"]["static"]["status"] == "passed"
    assert body["verification"]["api_dry_run"]["status"] == "not_run"
    assert body["status"] == "partially_verified"   # static OK, no sandbox yet


@pytest.mark.asyncio
async def test_static_rules_reject_unsafe_cli_constructs():
    """The static validator is the real gate; risky constructs must fail it."""
    cases = {
        "sudo": "sudo kubectl get nodes",
        "shell-chain": "kubectl get nodes && kubectl get pods",
        "redirect": "kubectl get nodes > /tmp/out",
        "placeholder": "kubectl get nodes  # TODO fill me",
    }
    for label, bad_line in cases.items():
        artifact = {"format": "network-cli", "content": bad_line}
        body = _payload(await do_validate_change_artifact(json.dumps({"artifact": artifact})))
        assert body["passed"] is False, f"{label}: expected failure, got {body}"
        assert body["verification"]["static"]["status"] == "failed"
        assert body["errors"], f"{label}: expected an error message"


# ── Sandbox-evidence layer (validator consumes, never runs) ────────────────

@pytest.mark.asyncio
async def test_validator_promotes_to_passed_with_matching_sandbox_hash():
    """A bound, well-formed sandbox_result upgrades fully_verified."""
    artifact = make_cli_artifact()
    sandbox = fake_sandbox_result(artifact, passed=True, api_dry_run_ok=True)

    body = _payload(await do_validate_change_artifact(json.dumps({
        "artifact": artifact,
        "sandbox_result": sandbox,
    })))

    assert body["passed"] is True, body.get("errors")
    assert body["status"] == "passed"
    assert body["verification"]["api_dry_run"]["status"] == "passed"


@pytest.mark.asyncio
async def test_validator_rejects_tampered_sandbox_hash():
    """Sandbox evidence must be bound to THIS artifact via artifact_hash."""
    artifact = make_cli_artifact()
    # Hash does NOT match the artifact content -> evidence is for something else.
    tampered = fake_sandbox_result(artifact, hash_override="0" * 64)

    body = _payload(await do_validate_change_artifact(json.dumps({
        "artifact": artifact,
        "sandbox_result": tampered,
    })))

    assert body["passed"] is False
    assert body["status"] == "failed"
    assert any("artifact" in e and "hash" in e for e in body["errors"])


@pytest.mark.asyncio
async def test_validator_rejects_sandbox_that_failed_dry_run():
    """If the sandbox dry-run itself failed, the artifact is not verified."""
    artifact = make_cli_artifact()
    sandbox = fake_sandbox_result(artifact, passed=False, api_dry_run_ok=False)

    body = _payload(await do_validate_change_artifact(json.dumps({
        "artifact": artifact,
        "sandbox_result": sandbox,
    })))

    assert body["passed"] is False
    assert body["status"] == "failed"
    assert body["verification"]["api_dry_run"]["status"] == "failed"


# ── Verify-loop invariant ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_evidence_means_partially_verified_not_passed():
    """This is the invariant that makes CLI generation safe WITHOUT a cluster.

    A clean static check never auto-promotes to `passed`; without sandbox
    evidence it stops at `partially_verified`. So the absence of any container/
    cluster today cannot be mistaken for a fully verified change. There is no
    hidden retry loop — promotion only happens when matching evidence is supplied.
    """
    for fmt in ("network-cli", "yaml", "kubernetes"):
        content = (
            "kubectl get nodes -o wide\n" if fmt == "network-cli"
            else "apiVersion: v1\nkind: Namespace\nmetadata:\n  name: lab\n"
        )
        body = _payload(await do_validate_change_artifact(json.dumps({
            "artifact": {"format": fmt, "content": content},
        })))
        assert body["passed"] is True, (fmt, body.get("errors"))
        assert body["status"] == "partially_verified", fmt
        assert body["execution_allowed"] is False
