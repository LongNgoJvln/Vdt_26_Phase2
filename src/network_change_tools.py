"""Deterministic, read-only network-change domain tools.

The general agent remains responsible for calling externally configured MCP
tools.  These helpers only package evidence, compare snapshots, and create or
validate a proposal.  They deliberately contain no cluster client and no
execution path, so adding them cannot mutate a managed network or Kubernetes
cluster.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from core.time_utils import iso_utc
from typing import Any, Dict, Iterable, List, Optional, Tuple

from core.database import (
    NetworkChangeProposal,
    NetworkSnapshotRecord,
    get_db_session,
)


# The multi-agent pipeline validates the exact artifact bytes a second time
# before making a file visible in the parent chat.  ContextVar keeps this
# request-local even when several chat streams run concurrently.
_DEFER_ARTIFACT_DOCUMENT: ContextVar[bool] = ContextVar(
    "network_change_defer_artifact_document", default=False
)


@contextmanager
def defer_artifact_document_creation():
    """Defer document creation until the independent policy gate passes."""
    token = _DEFER_ARTIFACT_DOCUMENT.set(True)
    try:
        yield
    finally:
        _DEFER_ARTIFACT_DOCUMENT.reset(token)


MAX_SNAPSHOT_BYTES = 5 * 1024 * 1024
MAX_ARTIFACT_BYTES = 1024 * 1024
MAX_TOOL_OUTPUT_CHARS = 20_000
MAX_DIFFS = 500
RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
VOLATILE_KEYS = {"managedFields", "resourceVersion", "selfLink"}
SENSITIVE_KEY = re.compile(
    r"(?:password|passwd|token|api[_-]?key|secret|private[_-]?key|client[_-]?secret|authorization)",
    re.I,
)
PLACEHOLDER_PATTERNS = (
    re.compile(r"\$\{[^}]+}"),
    re.compile(r"<(?:TODO|TBD|REPLACE|CHANGE|YOUR)[^>]*>", re.I),
    re.compile(r"\b(?:TODO|TBD)\b", re.I),
)


def _parse_args(content: Any) -> Dict[str, Any]:
    if isinstance(content, dict):
        return content
    if not isinstance(content, str) or not content.strip():
        return {}
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("tool input must be a JSON object")
    return parsed


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=iso_utc)


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=iso_utc)


def _loads(value: Optional[str], fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


_ARTIFACT_FORMAT_ALIASES = {
    # Shell CLI artifacts. LLMs often answer a MIME type or a bare shell
    # name; all of these are the same "network-cli" editable artifact.
    "shell": "cli", "sh": "cli", "bash": "cli", "shellscript": "cli",
    "text/x-shellscript": "cli", "text/x-sh": "cli", "application/x-sh": "cli",
    "application/x-shellscript": "cli", "text/shellscript": "cli",
    # Kubernetes/YAML manifests.
    "application/yaml": "kubernetes", "text/yaml": "kubernetes",
    "text/x-yaml": "kubernetes", "application/x-yaml": "kubernetes",
    "manifest": "kubernetes", "k8s": "kubernetes", "kustomization": "kubernetes",
}
_MATERIALIZABLE_FORMATS = {"cli", "network-cli", "yaml", "yml", "kubernetes"}


def _normalize_artifact_format(raw: Any) -> str:
    """Map an LLM-supplied artifact format onto the canonical materializable set.

    Validation is deliberately lenient about the format string, but artifact
    document creation can only mint the editor's CLI/kubernetes languages.
    Unknown formats normalize to "" (not materializable)."""
    fmt = str(raw or "").lower().strip()
    fmt = _ARTIFACT_FORMAT_ALIASES.get(fmt, fmt)
    return fmt if fmt in _MATERIALIZABLE_FORMATS else ""


def _result(payload: Dict[str, Any], *, error: bool = False) -> Dict[str, Any]:
    serialized = _json_text(payload)
    if len(serialized) > MAX_TOOL_OUTPUT_CHARS:
        serialized = _json_text({
            "truncated": True,
            "original_chars": len(serialized),
            "preview": serialized[: MAX_TOOL_OUTPUT_CHARS - 200],
            "hint": "Request a narrower record or scope to retrieve the omitted evidence.",
        })
    key = "error" if error else "output"
    return {key: serialized, "exit_code": 1 if error else 0}


def _owner_filter(query: Any, column: Any, owner: Optional[str]) -> Any:
    # New domain rows are never shared implicitly.  In no-auth mode owner is
    # NULL, so NULL is still an explicit scope rather than "all owners".
    return query.filter(column.is_(None)) if owner is None else query.filter(column == owner)


def _sanitize(value: Any, parent_key: str = "") -> Any:
    """Remove high-noise K8s metadata and redact likely credentials."""
    if SENSITIVE_KEY.search(parent_key):
        return "[REDACTED]"
    if isinstance(value, dict):
        cleaned = {}
        resource_kind = str(value.get("kind") or "").lower()
        for key in sorted(value, key=str):
            key_text = str(key)
            if key_text in VOLATILE_KEYS:
                continue
            # Read-only access can still expose Kubernetes Secret payloads.
            # Redact the whole payload even when its individual keys have
            # harmless-looking names such as tls.crt or username.
            if resource_kind in {"secret", "secrets", "secretlist"} and key_text in {"data", "stringData"}:
                cleaned[key_text] = "[REDACTED KUBERNETES SECRET]"
                continue
            cleaned[key_text] = _sanitize(value[key], key_text)
        return cleaned
    if isinstance(value, list):
        return [_sanitize(item, parent_key) for item in value]
    return value


def _snapshot_dict(row: NetworkSnapshotRecord, *, include_observations: bool = True) -> Dict[str, Any]:
    result = {
        "id": row.id,
        "cluster": row.cluster,
        "namespace": row.namespace,
        "target": _loads(row.target_json, {}),
        "warnings": _loads(row.warnings_json, []),
        "captured_at": row.captured_at.isoformat() if row.captured_at else None,
        "content_hash": row.content_hash,
    }
    if include_observations:
        result["observations"] = _loads(row.observations_json, [])
    return result


def _proposal_dict(row: NetworkChangeProposal, *, detail: bool = True) -> Dict[str, Any]:
    result = {
        "id": row.id,
        "session_id": row.session_id,
        "snapshot_id": row.snapshot_id,
        "objective": row.objective,
        "target": _loads(row.target_json, {}),
        "risk": row.risk,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
    if detail:
        result.update({
            "plan": _loads(row.plan_json, {}),
            "artifact": _loads(row.artifact_json, {}),
            "validation": _loads(row.validation_json, {}),
            "evidence": _loads(row.evidence_json, []),
        })
    return result


def _load_snapshot(snapshot_id: str, owner: Optional[str]) -> Optional[NetworkSnapshotRecord]:
    with get_db_session() as db:
        query = db.query(NetworkSnapshotRecord).filter(NetworkSnapshotRecord.id == snapshot_id)
        row = _owner_filter(query, NetworkSnapshotRecord.owner, owner).first()
        if row is not None:
            db.expunge(row)
        return row


def _risk_from_text(*values: Any) -> str:
    text = " ".join(_canonical(value) for value in values).lower()
    if any(term in text for term in (
        "delete namespace", "drop database", "wipe", "all namespaces", "--all", "production-wide",
    )):
        return "critical"
    if any(term in text for term in (
        "delete", "drain", "reboot", "restart", "replace", "firewall", "route", "bgp", "networkpolicy",
    )):
        return "high"
    if any(term in text for term in (
        "apply", "patch", "scale", "rollout", "upgrade", "config", "manifest", "deployment", "service",
    )):
        return "medium"
    return "low"


def _max_risk(*risks: str) -> str:
    valid = [risk.lower() for risk in risks if isinstance(risk, str) and risk.lower() in RISK_ORDER]
    return max(valid or ["low"], key=RISK_ORDER.get)


def _validate_artifact_data(artifact: Any, rollback: Any = None, requested_risk: str = "") -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    if isinstance(artifact, str):
        artifact = {"format": "text", "content": artifact}
    if not isinstance(artifact, dict):
        artifact = {}

    fmt = str(artifact.get("format") or "text").lower().strip()
    content = artifact.get("content")
    if isinstance(content, (dict, list)):
        content_text = _json_text(content)
    else:
        content_text = str(content or "").strip()

    if not content_text:
        errors.append("artifact.content is required")
    else:
        if len(content_text.encode("utf-8")) > MAX_ARTIFACT_BYTES:
            errors.append(f"artifact exceeds the {MAX_ARTIFACT_BYTES}-byte limit")
        for pattern in PLACEHOLDER_PATTERNS:
            if pattern.search(content_text):
                errors.append("artifact contains unresolved TODO/TBD/placeholder values")
                break

    if content_text and fmt == "json":
        try:
            json.loads(content_text)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON artifact: {exc.msg} at line {exc.lineno}")
    elif content_text and fmt in {"yaml", "yml", "kubernetes"}:
        try:
            import yaml  # type: ignore
            documents = list(yaml.safe_load_all(content_text))
            if not documents or all(document is None for document in documents):
                errors.append("YAML artifact has no documents")
        except ImportError:
            warnings.append("PyYAML is unavailable; YAML syntax was not parsed")
        except Exception as exc:
            errors.append(f"invalid YAML artifact: {exc}")

    inferred_risk = _risk_from_text(artifact, rollback)
    risk = _max_risk(requested_risk, inferred_risk)
    if risk in {"high", "critical"} and not rollback:
        warnings.append("high-risk proposal has no rollback procedure")
    if re.search(r"\bkubectl\s+(?:apply|patch|delete|scale|rollout|replace)\b", content_text, re.I):
        warnings.append("artifact contains a mutating kubectl command; this build will only review it, never run it")

    cli_commands: List[str] = []
    if fmt in {"cli", "network-cli", "bash", "shell"} and content_text:
        for line_number, raw_line in enumerate(content_text.splitlines(), 1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            cli_commands.append(line)
            if re.search(r"(?:^|\s)(?:sudo|su)\s", line, re.I):
                errors.append(f"line {line_number}: privilege escalation is not allowed")
            if re.search(r"(?:&&|\|\||[;`]|\$\(|>\s*/|<\s*/)", line):
                errors.append(f"line {line_number}: shell chaining/redirection is not allowed in a network CLI artifact")
            if re.search(r"\bkubectl\s+delete\s+(?:namespace|ns)\b", line, re.I):
                errors.append(f"line {line_number}: deleting a namespace is outside the review-only change policy")
            if re.search(r"\bkubectl\s+delete\b.*(?:--all(?:\s|$)|--all-namespaces\b|(?:^|\s)-A(?:\s|$))", line, re.I):
                errors.append(f"line {line_number}: broad delete scope is outside the review-only change policy")
            if re.search(r"\brm\s+-[^\n]*r[^\n]*f\b", line, re.I):
                errors.append(f"line {line_number}: recursive force deletion is not allowed")
        if not cli_commands:
            errors.append("CLI artifact contains no executable command lines")

    static_passed = not errors
    artifact_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest() if content_text else None
    supplied_sandbox = artifact.get("sandbox_result") if isinstance(artifact, dict) else None
    sandbox_status = "not_run"
    sandbox_evidence: Dict[str, Any] = {}
    sandbox_stages: Dict[str, str] = {}
    if isinstance(supplied_sandbox, dict):
        sandbox_evidence = {
            key: supplied_sandbox.get(key)
            for key in ("sandbox_id", "artifact_hash", "checks", "errors", "warnings", "cleanup")
            if key in supplied_sandbox
        }
        supplied_hash = supplied_sandbox.get("artifact_hash")
        if not supplied_hash:
            sandbox_status = "failed"
            errors.append("sandbox result is missing artifact_hash")
        elif supplied_hash != artifact_hash:
            sandbox_status = "failed"
            errors.append("sandbox result does not match the current artifact hash")
        else:
            for check in supplied_sandbox.get("checks") or []:
                if not isinstance(check, dict) or not check.get("stage"):
                    continue
                sandbox_stages[str(check["stage"])] = (
                    "passed" if check.get("exit_code") == 0 else "failed"
                )
            sandbox_status = (
                "passed"
                if supplied_sandbox.get("passed") is True
                and sandbox_stages.get("api_dry_run") == "passed"
                else "failed"
            )
            if "api_dry_run" not in sandbox_stages:
                errors.append("sandbox result has no api_dry_run check")
        if sandbox_status == "failed":
            errors.append("sandbox validation reported failure")

    verification = {
        "static": {"status": "passed" if static_passed else "failed"},
        "instruction_grounding": {"status": "not_run", "reason": "requires retrieved instruction evidence"},
        "live_preconditions": {"status": "not_run", "reason": "requires a fresh read-only MCP snapshot"},
        "api_dry_run": {"status": sandbox_stages.get("api_dry_run", "failed" if sandbox_status == "failed" else "not_run"), "evidence": sandbox_evidence},
        "sandbox_apply": {"status": sandbox_stages.get("sandbox_apply", "failed" if sandbox_status == "failed" else "not_run"), "evidence": sandbox_evidence},
        "runtime_probes": {"status": sandbox_stages.get("runtime_observation", "not_run")},
        "rollback_test": {"status": sandbox_stages.get("rollback_test", "not_run")},
        "vendor_runtime": {"status": "not_supported", "reason": "vendor emulator/test node not configured"},
    }
    overall = "failed" if errors else ("passed" if sandbox_status == "passed" else "partially_verified")

    return {
        "passed": not errors,
        "status": overall,
        "format": fmt,
        "risk": risk,
        "errors": errors,
        "warnings": warnings,
        "artifact_hash": artifact_hash,
        "command_count": len(cli_commands),
        "verification": verification,
        "execution_allowed": False,
    }


async def do_collect_network_snapshot(content: Any, owner: Optional[str] = None) -> Dict[str, Any]:
    """Persist observations that the agent already collected via read-only MCP."""
    try:
        args = _parse_args(content)
        observations = args.get("observations")
        if not isinstance(observations, list) or not observations:
            return _result({
                "message": "observations must be a non-empty array of outputs already collected via read-only MCP tools",
            }, error=True)

        normalized = _sanitize(observations)
        target = _sanitize(args.get("target") or {})
        warnings = args.get("warnings") or []
        if not isinstance(warnings, list):
            warnings = [str(warnings)]
        payload_for_hash = {"target": target, "observations": normalized}
        encoded = _canonical(payload_for_hash).encode("utf-8")
        if len(encoded) > MAX_SNAPSHOT_BYTES:
            return _result({
                "message": f"normalized snapshot is {len(encoded)} bytes; maximum is {MAX_SNAPSHOT_BYTES}",
                "hint": "collect a narrower namespace/resource scope or summarize large logs before packaging",
            }, error=True)

        captured_at_raw = args.get("captured_at")
        try:
            if captured_at_raw:
                captured_at = datetime.fromisoformat(str(captured_at_raw).replace("Z", "+00:00"))
                if captured_at.tzinfo is not None:
                    captured_at = captured_at.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                captured_at = datetime.now(timezone.utc).replace(tzinfo=None)
        except ValueError:
            return _result({"message": "captured_at must be an ISO-8601 datetime"}, error=True)

        row = NetworkSnapshotRecord(
            id=str(uuid.uuid4()),
            owner=owner,
            cluster=str(args.get("cluster") or target.get("cluster") or "").strip() or None,
            namespace=str(args.get("namespace") or target.get("namespace") or "").strip() or None,
            target_json=_json_text(target),
            observations_json=_json_text(normalized),
            warnings_json=_json_text(warnings),
            captured_at=captured_at,
            content_hash=hashlib.sha256(encoded).hexdigest(),
        )
        with get_db_session() as db:
            db.add(row)
            db.flush()
            snapshot_payload = _snapshot_dict(row, include_observations=False)
        return _result({
            "snapshot": snapshot_payload,
            "observation_count": len(normalized),
            "normalized_bytes": len(encoded),
            "redaction": "credential-like fields were replaced with [REDACTED]",
            "next": "Use compare_network_snapshots or prepare_network_change with snapshot.id.",
        })
    except (ValueError, json.JSONDecodeError) as exc:
        return _result({"message": str(exc)}, error=True)
    except Exception as exc:
        return _result({"message": f"failed to store network snapshot: {exc}"}, error=True)


def _diff_values(before: Any, after: Any, path: str = "$", diffs: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    diffs = diffs if diffs is not None else []
    if len(diffs) >= MAX_DIFFS:
        return diffs
    if type(before) is not type(after):
        diffs.append({"path": path, "change": "type_changed", "before": before, "after": after})
    elif isinstance(before, dict):
        for key in sorted(set(before) | set(after), key=str):
            child = f"{path}.{key}"
            if key not in before:
                diffs.append({"path": child, "change": "added", "after": after[key]})
            elif key not in after:
                diffs.append({"path": child, "change": "removed", "before": before[key]})
            else:
                _diff_values(before[key], after[key], child, diffs)
            if len(diffs) >= MAX_DIFFS:
                break
    elif isinstance(before, list):
        for index in range(max(len(before), len(after))):
            child = f"{path}[{index}]"
            if index >= len(before):
                diffs.append({"path": child, "change": "added", "after": after[index]})
            elif index >= len(after):
                diffs.append({"path": child, "change": "removed", "before": before[index]})
            else:
                _diff_values(before[index], after[index], child, diffs)
            if len(diffs) >= MAX_DIFFS:
                break
    elif before != after:
        diffs.append({"path": path, "change": "changed", "before": before, "after": after})
    return diffs


async def do_compare_network_snapshots(content: Any, owner: Optional[str] = None) -> Dict[str, Any]:
    try:
        args = _parse_args(content)
        snapshots: List[Tuple[str, Dict[str, Any]]] = []
        for label, id_key, value_key in (
            ("baseline", "baseline_snapshot_id", "baseline"),
            ("current", "current_snapshot_id", "current"),
        ):
            snapshot_id = str(args.get(id_key) or "").strip()
            if snapshot_id:
                row = _load_snapshot(snapshot_id, owner)
                if not row:
                    return _result({"message": f"{label} snapshot not found in caller scope: {snapshot_id}"}, error=True)
                snapshots.append((row.id, _snapshot_dict(row)))
            elif isinstance(args.get(value_key), dict):
                snapshots.append(("inline", _sanitize(args[value_key])))
            else:
                return _result({"message": f"provide {id_key} or inline {value_key}"}, error=True)

        before_id, before = snapshots[0]
        after_id, after = snapshots[1]
        comparable_before = before.get("observations", before)
        comparable_after = after.get("observations", after)
        diffs = _diff_values(comparable_before, comparable_after)
        return _result({
            "baseline": before_id,
            "current": after_id,
            "changed": bool(diffs),
            "diff_count": len(diffs),
            "truncated": len(diffs) >= MAX_DIFFS,
            "diffs": diffs,
        })
    except (ValueError, json.JSONDecodeError) as exc:
        return _result({"message": str(exc)}, error=True)
    except Exception as exc:
        return _result({"message": f"snapshot comparison failed: {exc}"}, error=True)


async def do_validate_change_artifact(content: Any, owner: Optional[str] = None) -> Dict[str, Any]:
    del owner  # Validation is pure and does not access tenant data.
    try:
        args = _parse_args(content)
        artifact = args.get("artifact", args)
        if isinstance(artifact, dict) and isinstance(args.get("sandbox_result"), dict):
            artifact = {**artifact, "sandbox_result": args["sandbox_result"]}
        validation = _validate_artifact_data(
            artifact,
            rollback=args.get("rollback"),
            requested_risk=str(args.get("risk") or ""),
        )
        return _result(validation, error=not validation["passed"])
    except (ValueError, json.JSONDecodeError) as exc:
        return _result({"message": str(exc)}, error=True)


async def do_prepare_network_change(
    content: Any,
    session_id: Optional[str] = None,
    owner: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a structured proposal for human review, never an execution job."""
    try:
        args = _parse_args(content)
        objective = str(args.get("objective") or "").strip()
        plan = args.get("plan") or {}
        artifact = args.get("artifact") or {}
        rollback = args.get("rollback")
        evidence = args.get("evidence") or []
        target = _sanitize(args.get("target") or {})
        snapshot_id = str(args.get("snapshot_id") or "").strip() or None

        errors: List[str] = []
        if not objective:
            errors.append("objective is required")
        stages = plan.get("stages") if isinstance(plan, dict) else None
        if not isinstance(stages, list) or not stages:
            errors.append("plan.stages must be a non-empty array")
        if not snapshot_id and not evidence:
            errors.append("snapshot_id or evidence is required")
        if snapshot_id and not _load_snapshot(snapshot_id, owner):
            errors.append("snapshot_id was not found in the caller's scope")

        artifact_for_validation = artifact
        if isinstance(artifact, dict) and isinstance(args.get("sandbox_result"), dict):
            artifact_for_validation = {**artifact, "sandbox_result": args["sandbox_result"]}
        validation = _validate_artifact_data(
            artifact_for_validation,
            rollback=rollback,
            requested_risk=str(args.get("risk") or ""),
        )
        errors.extend(validation["errors"])
        validation = {
            **validation,
            "errors": errors,
            "passed": not errors,
            "status": "failed" if errors else validation["status"],
        }
        risk = _max_risk(validation["risk"], _risk_from_text(objective, plan, target))
        validation["risk"] = risk

        proposal = NetworkChangeProposal(
            id=str(uuid.uuid4()),
            owner=owner,
            session_id=session_id,
            snapshot_id=snapshot_id,
            objective=objective or "Invalid proposal",
            target_json=_json_text(target),
            plan_json=_json_text(plan),
            artifact_json=_json_text(artifact),
            validation_json=_json_text(validation),
            evidence_json=_json_text(evidence),
            risk=risk,
            status="ready_for_review" if validation["passed"] else "invalid",
        )
        with get_db_session() as db:
            db.add(proposal)
            db.flush()
            proposal_payload = _proposal_dict(proposal)

        artifact_document = None
        if _DEFER_ARTIFACT_DOCUMENT.get():
            # A supervised pipeline (Generator worker) is producing this
            # proposal.  The document is withheld now and only materialized
            # after the independent Critic gate re-validates the exact bytes.
            artifact_document = None
        elif validation["passed"] and session_id and isinstance(artifact, dict):
            artifact_content = artifact.get("content")
            artifact_format = _normalize_artifact_format(artifact.get("format"))
            if isinstance(artifact_content, str) and artifact_content.strip() and artifact_format:
                # The editable artifact contains only executable CLI/manifest
                # bytes. Intent, risk and validation evidence stay in the
                # proposal/response instead of being mixed into the file.
                clean_content = re.sub(r"^```[^\n]*\n|\n```$", "", artifact_content.strip())
                language = "network-cli" if artifact_format in {"cli", "network-cli"} else "kubernetes"
                from src.tool_implementations import do_create_document
                document_result = await do_create_document(
                    f"<title>{objective} — artifact</title><language>{language}</language><content>{clean_content}</content>",
                    session_id=session_id,
                    owner=owner,
                )
                if not document_result.get("error"):
                    artifact_document = {
                        "doc_id": document_result.get("doc_id"),
                        "title": document_result.get("title"),
                        "language": document_result.get("language"),
                    }
        return _result({
            "proposal": proposal_payload,
            "artifact_document": artifact_document,
            "execution_allowed": False,
            "next": "Review/edit the command-only artifact. Use Validate for static checks, then the dedicated k8s-sandbox MCP for API dry-run and isolated apply tests.",
        }, error=not validation["passed"])
    except (ValueError, json.JSONDecodeError) as exc:
        return _result({"message": str(exc)}, error=True)
    except Exception as exc:
        return _result({"message": f"failed to prepare change proposal: {exc}"}, error=True)


async def do_get_network_change_history(content: Any, owner: Optional[str] = None) -> Dict[str, Any]:
    try:
        args = _parse_args(content)
        action = str(args.get("action") or "list").lower()
        record_id = str(args.get("id") or "").strip()
        record_type = str(args.get("record_type") or "proposal").lower()
        limit = min(max(int(args.get("limit") or 20), 1), 100)

        with get_db_session() as db:
            if record_type in {"snapshot", "snapshots"}:
                query = _owner_filter(db.query(NetworkSnapshotRecord), NetworkSnapshotRecord.owner, owner)
                if action in {"get", "read", "view"}:
                    row = query.filter(NetworkSnapshotRecord.id == record_id).first()
                    if not row:
                        return _result({"message": "snapshot not found in caller scope"}, error=True)
                    payload = {"snapshot": _snapshot_dict(row)}
                else:
                    rows = query.order_by(NetworkSnapshotRecord.captured_at.desc()).limit(limit).all()
                    payload = {"snapshots": [_snapshot_dict(row, include_observations=False) for row in rows]}
            else:
                query = _owner_filter(db.query(NetworkChangeProposal), NetworkChangeProposal.owner, owner)
                if action in {"get", "read", "view"}:
                    row = query.filter(NetworkChangeProposal.id == record_id).first()
                    if not row:
                        return _result({"message": "proposal not found in caller scope"}, error=True)
                    payload = {"proposal": _proposal_dict(row)}
                else:
                    status = str(args.get("status") or "").strip()
                    if status:
                        query = query.filter(NetworkChangeProposal.status == status)
                    rows = query.order_by(NetworkChangeProposal.created_at.desc()).limit(limit).all()
                    payload = {"proposals": [_proposal_dict(row, detail=False) for row in rows]}
        return _result(payload)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return _result({"message": str(exc)}, error=True)
    except Exception as exc:
        return _result({"message": f"failed to read network-change history: {exc}"}, error=True)


async def materialize_network_change_artifact(
    proposal_id: str,
    parent_session_id: str,
    owner: Optional[str] = None,
) -> Dict[str, Any]:
    """Create the artifact document for an accepted proposal, after the Critic gate.

    Mirrors the document path of do_prepare_network_change: the file holds only
    cleaned CLI/manifest bytes, while intent, risk, and validation evidence stay
    on the proposal. Returns {doc_id,title,language,version,content} on success
    or {error: "..."} when no acceptable artifact exists.
    """
    try:
        proposal_id = str(proposal_id or "").strip()
        if not proposal_id or not parent_session_id:
            return {"error": "proposal_id and parent session are required"}

        with get_db_session() as db:
            row = (
                _owner_filter(db.query(NetworkChangeProposal), NetworkChangeProposal.owner, owner)
                .filter(NetworkChangeProposal.id == proposal_id)
                .first()
            )
            if row is None:
                return {"error": "proposal not found in caller scope"}
            if row.status != "ready_for_review":
                return {"error": f"proposal status is {row.status}, not ready_for_review"}
            artifact = _loads(row.artifact_json, {})
            objective = row.objective

        if not isinstance(artifact, dict):
            return {"error": "proposal artifact is not a structured object"}

        artifact_content = artifact.get("content")
        artifact_format = _normalize_artifact_format(artifact.get("format"))
        if not isinstance(artifact_content, str) or not artifact_content.strip():
            return {"error": "proposal artifact has no content bytes"}
        if not artifact_format:
            return {"error": f"unsupported artifact format: {str(artifact.get('format') or 'none')!r}"}

        clean_content = re.sub(r"^```[^\n]*\n|\n```$", "", artifact_content.strip())
        language = "network-cli" if artifact_format in {"cli", "network-cli"} else "kubernetes"
        from src.tool_implementations import do_create_document
        document_result = await do_create_document(
            f"<title>{objective} — artifact</title><language>{language}</language><content>{clean_content}</content>",
            session_id=parent_session_id,
            owner=owner,
        )
        if document_result.get("error"):
            return {"error": f"document creation failed: {document_result.get('message') or document_result.get('error')}"}
        # Defensive: do_create_document sets is_active=True, but a long detached
        # run can race with other document/tool calls that flip the active-doc
        # pointer. Force the surfaced artifact visible so it is never hidden
        # from the chat link or the document library.
        from core.database import Document as _Document
        doc_id = document_result.get("doc_id")
        if doc_id:
            with get_db_session() as db:
                d = _owner_filter(db.query(_Document), _Document.owner, owner).filter(_Document.id == doc_id).first()
                if d is not None and not d.is_active:
                    d.is_active = True
        return {
            "doc_id": document_result.get("doc_id"),
            "title": document_result.get("title"),
            "language": document_result.get("language", language),
            "version": document_result.get("version", 1),
            "content": clean_content,
        }
    except Exception as exc:
        return {"error": f"failed to materialize artifact: {exc}"}


def redact_blocked_proposal_artifact(
    proposal_id: str,
    parent_session_id: Optional[str] = None,
    owner: Optional[str] = None,
) -> None:
    """Keep a rejected/cancelled proposal row for audit, but never keep its bytes.

    The artifact content is replaced with a placeholder so a failed pipeline run
    leaves no rejected command/manifest text retrievable from chat or file.
    """
    try:
        proposal_id = str(proposal_id or "").strip()
        if not proposal_id:
            return
        with get_db_session() as db:
            row = (
                _owner_filter(db.query(NetworkChangeProposal), NetworkChangeProposal.owner, owner)
                .filter(NetworkChangeProposal.id == proposal_id)
                .first()
            )
            if row is None:
                return
            if row.status in {"ready_for_review", "redacted"}:
                # Accepted proposals keep their bytes (they are already
                # surfaced documents); redaction is idempotent.
                return
            row.artifact_json = _json_text({
                "format": "redacted",
                "content": "[REDACTED — artifact rejected by the deterministic policy gate]",
                "reason": f"blocked in session {parent_session_id or 'unknown'}",
            })
            row.status = "redacted"
    except Exception:
        # Redaction is a safety fallback, never a crash path for the pipeline.
        return
