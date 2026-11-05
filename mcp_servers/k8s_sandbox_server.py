"""Dedicated Kubernetes sandbox MCP server.

This process is intentionally separate from the Network Change web app.  It
refuses to start without an explicit sandbox kubeconfig, never uses a shell,
rejects cluster-scoped objects, and confines all apply tests to an ephemeral
namespace.  Do not point ``K8S_SANDBOX_KUBECONFIG`` at a production cluster.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
import tempfile
import uuid
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool


server = Server("k8s-sandbox")
KUBECTL = os.getenv("KUBECTL_PATH", "kubectl")
KUBECONFIG = Path(os.getenv("K8S_SANDBOX_KUBECONFIG", "")).expanduser()
BASE_NAMESPACE = os.getenv("K8S_SANDBOX_NAMESPACE", "network-change-sandbox")
ENABLE_APPLY = os.getenv("K8S_SANDBOX_ENABLE_APPLY", "false").lower() in {"1", "true", "yes"}
MAX_BYTES = 1024 * 1024
CLUSTER_SCOPED_KINDS = {
    "namespace", "node", "clusterrole", "clusterrolebinding",
    "customresourcedefinition", "storageclass", "persistentvolume",
    "mutatingwebhookconfiguration", "validatingwebhookconfiguration",
}


def _ensure_config() -> None:
    if not str(KUBECONFIG) or not KUBECONFIG.is_file():
        raise RuntimeError("K8S_SANDBOX_KUBECONFIG must point to a dedicated sandbox kubeconfig")
    production = os.getenv("KUBECONFIG")
    if production and Path(production).expanduser().resolve() == KUBECONFIG.resolve():
        raise RuntimeError("sandbox kubeconfig must not be the same path as KUBECONFIG")


def _validate_manifest(manifest: str) -> None:
    if not manifest.strip():
        raise ValueError("manifest is required")
    if len(manifest.encode("utf-8")) > MAX_BYTES:
        raise ValueError("manifest exceeds 1 MiB")
    kinds = {match.lower() for match in re.findall(r"(?mi)^\s*kind\s*:\s*([\w.-]+)\s*$", manifest)}
    blocked = sorted(kinds & CLUSTER_SCOPED_KINDS)
    if blocked:
        raise ValueError(f"cluster-scoped kinds are forbidden in the sandbox: {blocked}")


def _cmd(*args: str, timeout: int = 60) -> dict:
    command = [KUBECTL, "--kubeconfig", str(KUBECONFIG), *args]
    completed = subprocess.run(
        command, capture_output=True, text=True, timeout=timeout,
        encoding="utf-8", errors="replace", shell=False,
    )
    return {
        "command": [KUBECTL, "--kubeconfig", "[SANDBOX_KUBECONFIG]", *args],
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-12000:],
        "stderr": completed.stderr[-12000:],
    }


def _write_manifest(directory: str, name: str, content: str) -> str:
    path = Path(directory) / name
    path.write_text(content, encoding="utf-8")
    return str(path)


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="sandbox_server_dry_run",
            description="Validate a Kubernetes manifest against the dedicated sandbox API server using kubectl apply --dry-run=server. Never touches the production kubeconfig.",
            inputSchema={
                "type": "object",
                "properties": {"manifest": {"type": "string"}},
                "required": ["manifest"],
            },
        ),
        Tool(
            name="sandbox_exercise_manifest",
            description="Apply a manifest in a disposable namespace on the dedicated sandbox cluster, inspect resources, optionally apply rollback, then always clean up. Requires K8S_SANDBOX_ENABLE_APPLY=true.",
            inputSchema={
                "type": "object",
                "properties": {
                    "manifest": {"type": "string"},
                    "rollback_manifest": {"type": "string"},
                    "timeout_seconds": {"type": "integer", "minimum": 10, "maximum": 180},
                },
                "required": ["manifest"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    sandbox_id = f"nc-sandbox-{uuid.uuid4().hex[:10]}"
    checks: list[dict] = []
    cleanup = {"attempted": False, "passed": None}
    try:
        _ensure_config()
        manifest = str(arguments.get("manifest") or "")
        _validate_manifest(manifest)
        artifact_hash = hashlib.sha256(manifest.strip().encode("utf-8")).hexdigest()
        timeout = min(max(int(arguments.get("timeout_seconds") or 60), 10), 180)
        with tempfile.TemporaryDirectory(prefix="network-change-sandbox-") as temp_dir:
            manifest_path = _write_manifest(temp_dir, "candidate.yaml", manifest)
            if name == "sandbox_server_dry_run":
                namespace_check = await asyncio.to_thread(
                    _cmd, "get", "namespace", BASE_NAMESPACE, timeout=timeout,
                )
                checks.append({"stage": "sandbox_namespace_preflight", **namespace_check})
                if namespace_check["exit_code"] != 0:
                    raise RuntimeError(
                        f"sandbox namespace {BASE_NAMESPACE!r} does not exist or is not accessible: "
                        f"{namespace_check['stderr'] or namespace_check['stdout']}"
                    )
                result = await asyncio.to_thread(
                    _cmd, "apply", "--dry-run=server", "-o", "yaml", "-n", BASE_NAMESPACE,
                    "-f", manifest_path, timeout=timeout,
                )
                checks.append({"stage": "api_dry_run", **result})
                payload = {
                    "passed": result["exit_code"] == 0,
                    "sandbox_id": sandbox_id,
                    "artifact_hash": artifact_hash,
                    "checks": checks,
                    "cleanup": cleanup,
                }
            elif name == "sandbox_exercise_manifest":
                if not ENABLE_APPLY:
                    raise RuntimeError("sandbox apply is disabled; set K8S_SANDBOX_ENABLE_APPLY=true on this dedicated server")
                create = await asyncio.to_thread(_cmd, "create", "namespace", sandbox_id, timeout=timeout)
                checks.append({"stage": "create_namespace", **create})
                if create["exit_code"] != 0:
                    raise RuntimeError(create["stderr"] or "failed to create sandbox namespace")
                cleanup["attempted"] = True
                dry = await asyncio.to_thread(
                    _cmd, "apply", "--dry-run=server", "-o", "yaml", "-n", sandbox_id,
                    "-f", manifest_path, timeout=timeout,
                )
                checks.append({"stage": "api_dry_run", **dry})
                if dry["exit_code"] == 0:
                    applied = await asyncio.to_thread(_cmd, "apply", "-n", sandbox_id, "-f", manifest_path, timeout=timeout)
                    checks.append({"stage": "sandbox_apply", **applied})
                    observed = await asyncio.to_thread(_cmd, "get", "all", "-n", sandbox_id, "-o", "wide", timeout=timeout)
                    checks.append({"stage": "runtime_observation", **observed})
                    rollback = str(arguments.get("rollback_manifest") or "")
                    if rollback.strip():
                        _validate_manifest(rollback)
                        rollback_path = _write_manifest(temp_dir, "rollback.yaml", rollback)
                        rolled_back = await asyncio.to_thread(_cmd, "apply", "-n", sandbox_id, "-f", rollback_path, timeout=timeout)
                        checks.append({"stage": "rollback_test", **rolled_back})
                payload = {
                    "passed": bool(checks) and all(check["exit_code"] == 0 for check in checks),
                    "sandbox_id": sandbox_id,
                    "artifact_hash": artifact_hash,
                    "checks": checks,
                    "cleanup": cleanup,
                }
            else:
                raise ValueError(f"Unknown tool: {name}")
    except Exception as exc:
        payload = {"passed": False, "sandbox_id": sandbox_id, "checks": checks, "errors": [str(exc)], "cleanup": cleanup}
    finally:
        if cleanup["attempted"]:
            try:
                removed = await asyncio.to_thread(_cmd, "delete", "namespace", sandbox_id, "--wait=false", timeout=30)
                cleanup["passed"] = removed["exit_code"] == 0
                cleanup["result"] = removed
            except Exception as exc:
                cleanup["passed"] = False
                cleanup["error"] = str(exc)
    return [TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))]


async def run() -> None:
    _ensure_config()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(run())
