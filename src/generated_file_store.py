"""Durable, human-readable mirror for documents created in chat sessions."""

from __future__ import annotations

import os
import re
from pathlib import Path


ROOT = Path(os.getenv("GENERATED_FILES_DIR", "data/generated"))
EXTENSIONS = {
    "markdown": ".md", "text": ".txt", "plain": ".txt",
    "network-cli": ".cli", "cli": ".cli", "bash": ".sh",
    "kubernetes": ".yaml", "yaml": ".yaml", "json": ".json",
    "python": ".py", "javascript": ".js", "typescript": ".ts",
    "html": ".html", "css": ".css", "csv": ".csv", "xml": ".xml",
}


def _safe(value: str | None, fallback: str) -> str:
    value = re.sub(r"[^\w.-]+", "-", (value or "").strip(), flags=re.UNICODE).strip(".-")
    return (value[:80] or fallback)


def mirror_document(doc) -> str | None:
    """Atomically mirror a session document and return its relative path."""
    if doc is None or not getattr(doc, "session_id", None):
        return None
    owner = _safe(getattr(doc, "owner", None), "local")
    session = _safe(getattr(doc, "session_id", None), "session")
    doc_id = _safe(getattr(doc, "id", None), "document")
    title = _safe(getattr(doc, "title", None), "untitled")
    language = str(getattr(doc, "language", None) or "text").lower()
    suffix = EXTENSIONS.get(language, ".txt")
    directory = ROOT / owner / session
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{doc_id}--{title}{suffix}"
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(str(getattr(doc, "current_content", "") or ""), encoding="utf-8")
    os.replace(tmp, target)
    for stale in directory.glob(f"{doc_id}--*"):
        if stale != target and stale.is_file():
            try:
                stale.unlink()
            except OSError:
                pass
    return target.as_posix()
