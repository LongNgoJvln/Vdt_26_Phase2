#!/usr/bin/env python3
"""Verify that a source package is complete, clean, and safe to archive.

Uses only the Python standard library so it can run before dependencies are
installed. It does not connect to any service and does not modify files.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOMAIN_TOOLS = {
    "collect_network_snapshot",
    "compare_network_snapshots",
    "validate_change_artifact",
    "prepare_network_change",
    "get_network_change_history",
}
REQUIRED = {
    "AGENTS.md",
    "agent.md",
    "README.md",
    "SOURCE_MANIFEST.md",
    ".env.example",
    ".gitignore",
    ".dockerignore",
    "app.py",
    "Dockerfile",
    "docker-compose.yml",
    "requirements.txt",
    "alembic.ini",
    "alembic/versions/0006_network_change_records.py",
    "docs/AGENT_HANDOFF.md",
    "docs/ARCHITECTURE_MULTIAGENT_2026-09-24_VI.md",
    "docs/INTERNAL_SERVER_DEPLOYMENT.md",
    "docs/NETWORK_CHANGE_MONOLITH.md",
    "docs/VALIDATION_STATUS.md",
    "knowledge_base/README.md",
    "knowledge_base/knowledge/4G_EPC_Overview.md",
    "knowledge_base/instructions/MME_Configuration.md",
    "scripts/ingest_network_knowledge.py",
    "static/lib/mermaid.min.js",
    "static/lib/mermaid.LICENSE.txt",
    "src/network_change_tools.py",
    "src/multiagent.py",
    "tests/test_mermaid_document_preview.py",
    "tests/test_network_change_tools.py",
    "tests/test_multiagent.py",
}
REGISTRATION_FILES = {
    "src/agent_tools.py",
    "src/tool_schemas.py",
    "src/tool_execution.py",
    "src/tool_index.py",
}
FORBIDDEN_NAMES = {".git", ".venv", ".venv-test", "__pycache__", ".pytest_cache", ".test-artifacts"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".log"}
SECRET_PATTERNS = {
    "private key": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    "OpenAI-style key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "known removed lab credential": re.compile(r"vht123456|123456@Epc|admin@vht", re.I),
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for item in sorted(REQUIRED):
        if not (ROOT / item).is_file():
            errors.append(f"missing required file: {item}")

    for path in ROOT.rglob("*"):
        if any(part in FORBIDDEN_NAMES for part in path.relative_to(ROOT).parts):
            errors.append(f"forbidden runtime/cache path: {rel(path)}")
            continue
        if path.is_file() and path.suffix.lower() in FORBIDDEN_SUFFIXES:
            errors.append(f"forbidden runtime file: {rel(path)}")

    for forbidden in (ROOT / ".env", ROOT / "k8s" / "secret-app.yaml", ROOT / "k8s" / "secret-harbor.yaml"):
        if forbidden.exists():
            errors.append(f"secret-bearing file must not be packaged: {rel(forbidden)}")

    data_dir = ROOT / "data"
    if data_dir.exists():
        unexpected = [path for path in data_dir.rglob("*") if path.is_file() and path.name != ".gitkeep"]
        errors.extend(f"runtime data must not be packaged: {rel(path)}" for path in unexpected)

    python_count = 0
    for path in ROOT.rglob("*.py"):
        if any(part in FORBIDDEN_NAMES for part in path.relative_to(ROOT).parts):
            continue
        python_count += 1
        try:
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except Exception as exc:
            errors.append(f"Python syntax error in {rel(path)}: {exc}")

    for item in sorted(REGISTRATION_FILES):
        path = ROOT / item
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        missing = sorted(tool for tool in DOMAIN_TOOLS if tool not in text)
        if missing:
            errors.append(f"{item} is missing domain tool registrations: {', '.join(missing)}")

    migration = ROOT / "alembic" / "versions" / "0006_network_change_records.py"
    if migration.is_file():
        text = migration.read_text(encoding="utf-8-sig")
        for table in ("network_snapshots", "network_change_proposals"):
            if table not in text:
                errors.append(f"migration 0006 is missing table {table}")

    kustomization = ROOT / "k8s" / "kustomization.yaml"
    if kustomization.is_file():
        text = kustomization.read_text(encoding="utf-8-sig")
        for match in re.finditer(r"^\s*-\s+([^#\s]+\.yaml)\s*$", text, re.M):
            resource = ROOT / "k8s" / match.group(1)
            if not resource.is_file():
                errors.append(f"kustomization references missing resource: k8s/{match.group(1)}")

    scan_extensions = {".py", ".md", ".yaml", ".yml", ".json", ".toml", ".ini", ".sh", ".ps1"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in scan_extensions:
            continue
        if path.resolve() == Path(__file__).resolve():
            # This verifier necessarily contains the detection signatures.
            continue
        if any(part in FORBIDDEN_NAMES for part in path.relative_to(ROOT).parts):
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"possible {label} in {rel(path)}")

    if not (ROOT / "data" / ".gitkeep").is_file():
        warnings.append("data/.gitkeep is absent; startup will create data/, but keeping it is clearer")

    print(f"root: {ROOT}")
    print(f"python files parsed: {python_count}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in sorted(set(errors)):
            print(f"ERROR: {error}")
        print(f"FAIL: {len(set(errors))} issue(s)")
        return 1
    print("PASS: standalone monolith source is complete and archive-safe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
