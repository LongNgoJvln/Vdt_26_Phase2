"""Ingest the bundled network-domain knowledge base into Qdrant.

Run from the monolith source root::

    python -m scripts.ingest_network_knowledge --owner admin
    python -m scripts.ingest_network_knowledge --owner admin --apply

The default invocation is a dry run.  ``--apply`` embeds and upserts the
documents into the same owner-filtered ``odysseus_rag`` collection queried by
the agent's ``search_knowledge`` tool.  ``--replace`` additionally removes old
chunks for each stable source tag before ingesting its current contents.
"""
from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KNOWLEDGE_ROOT = ROOT / "knowledge_base"
CATEGORIES = ("knowledge", "instructions")
SUPPORTED_EXTENSIONS = {".md", ".txt", ".json"}

sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest_network_knowledge")

try:
    from dotenv import load_dotenv  # noqa: E402

    load_dotenv(dotenv_path=ROOT / ".env", encoding="utf-8-sig")
except Exception as exc:  # pragma: no cover - dependency/runtime specific
    logger.warning(".env not loaded: %s", exc)


@dataclass(frozen=True)
class SourceDocument:
    category: str
    path: Path
    relative_path: str

    @property
    def source_tag(self) -> str:
        return f"network-kb:{self.category}:{self.relative_path}"


def discover_documents(root: Path, categories: Iterable[str]) -> list[SourceDocument]:
    """Return deterministic, supported source files from selected categories."""
    documents: list[SourceDocument] = []
    for category in categories:
        category_dir = root / category
        if not category_dir.is_dir():
            raise FileNotFoundError(f"Knowledge category directory not found: {category_dir}")
        for path in sorted(category_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            if path.name.startswith("PUT_") or path.name.casefold() == "readme.md":
                continue
            documents.append(SourceDocument(
                category=category,
                path=path,
                relative_path=path.relative_to(category_dir).as_posix(),
            ))
    return documents


def build_chunks(rag, document: SourceDocument, owner: str) -> list[tuple[str, dict]]:
    """Read one source document and create owner-scoped RAG chunk records."""
    content = document.path.read_text(encoding="utf-8-sig", errors="replace").strip()
    if not content:
        return []
    chunks = rag._split_into_chunks(content)  # Same chunker used by directory ingestion.
    return [
        (
            chunk,
            {
                "owner": owner,
                "source": document.source_tag,
                "filename": document.path.name,
                "relative_path": document.relative_path,
                "directory": document.category,
                "type": document.path.suffix.lower(),
                "knowledge_role": document.category,
                "domain": "4g_epc",
                "managed_by": "ingest_network_knowledge",
                "chunk_id": index,
            },
        )
        for index, chunk in enumerate(chunks)
        if chunk.strip()
    ]


def ingest_documents(rag, documents: Iterable[SourceDocument], owner: str, replace: bool = False) -> dict:
    """Reusable ingestion core for the CLI and authenticated UI route."""
    files_ok = files_failed = chunks_upserted = chunks_removed = 0
    errors: list[str] = []
    for document in documents:
        try:
            records = build_chunks(rag, document, owner)
            if not records:
                continue
            if replace:
                chunks_removed += int(rag.delete_by_source(document.source_tag) or 0)
            result = rag.add_documents_batch(records)
            if not result.get("success"):
                raise RuntimeError(result.get("message") or "Qdrant batch upsert failed")
            upserted = int(result.get("added_count") or 0)
            failed = int(result.get("failed_count") or 0)
            chunks_upserted += upserted
            files_failed += int(failed > 0)
            files_ok += int(failed == 0)
        except Exception as exc:
            files_failed += 1
            errors.append(f"{document.relative_path}: {exc}")
            logger.exception("Failed to ingest %s: %s", document.path, exc)
    return {
        "files_ok": files_ok,
        "files_failed": files_failed,
        "chunks_upserted": chunks_upserted,
        "chunks_removed": chunks_removed,
        "errors": errors,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest bundled 4G/EPC knowledge and instructions into Qdrant."
    )
    parser.add_argument(
        "--owner",
        required=True,
        help="Exact application username that should be able to retrieve these documents.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_KNOWLEDGE_ROOT,
        help="Knowledge root containing knowledge/ and instructions/.",
    )
    parser.add_argument(
        "--category",
        choices=(*CATEGORIES, "all"),
        default="all",
        help="Ingest one category or both (default: all).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write vectors to Qdrant; without this flag the command is a dry run.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="With --apply, remove existing chunks for each source before re-ingesting it.",
    )
    args = parser.parse_args(argv)
    args.owner = args.owner.strip()
    if not args.owner:
        parser.error("--owner must not be empty")
    if args.replace and not args.apply:
        parser.error("--replace requires --apply")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.expanduser().resolve()
    categories = CATEGORIES if args.category == "all" else (args.category,)

    try:
        documents = discover_documents(root, categories)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 1

    category_counts = {
        category: sum(document.category == category for document in documents)
        for category in categories
    }
    logger.info(
        "Discovered %d files under %s for owner=%s (%s)",
        len(documents),
        root,
        args.owner,
        ", ".join(f"{key}={value}" for key, value in category_counts.items()),
    )
    if not documents:
        logger.error("No supported knowledge documents found")
        return 1
    if not args.apply:
        for document in documents:
            logger.info("[dry-run] %s <- %s", document.source_tag, document.path)
        logger.info("Dry run complete; rerun with --apply to write to Qdrant")
        return 0

    from src.rag_singleton import get_rag_manager  # noqa: E402

    rag = get_rag_manager()
    if not rag or not getattr(rag, "healthy", False):
        logger.error(
            "RAG manager unavailable. Check QDRANT_URL and the local/HTTP embedding configuration."
        )
        return 1

    result = ingest_documents(rag, documents, args.owner, replace=args.replace)

    logger.info(
        "Done: files_ok=%d files_failed=%d chunks_upserted=%d chunks_removed=%d "
        "owner=%s collection=odysseus_rag",
        result["files_ok"],
        result["files_failed"],
        result["chunks_upserted"],
        result["chunks_removed"],
        args.owner,
    )
    return 0 if result["files_failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
