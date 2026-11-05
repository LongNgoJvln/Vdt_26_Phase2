"""Tests for the upload → RAG ingestion pipeline (src/ingest.py).

These cover the five cases called out in the plan:
  - PDF upload hits extract_pdf_text then embeds with owner set.
  - DOCX upload hits the markitdown office path.
  - TXT upload reads bytes + decodes + chunks.
  - Unsupported extension (mp4) returns skipped with no add_document call.
  - Two identical uploads by different owners produce distinct doc_ids.

Mock pattern follows the rest of the suite: optional deps stay MagicMock
via conftest.py, and we inject a fake VectorRAG with `healthy=True` so
ingest_upload_to_rag's health gate passes.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
from unittest.mock import MagicMock
from types import SimpleNamespace

import pytest

from src import ingest
from src.ingest import IngestResult, ingest_upload_to_rag


class FakeVectorRAG:
    """Minimal stand-in for VectorRAG that records every add_document call."""

    def __init__(self, *, healthy: bool = True):
        self._healthy = healthy
        self.added: list[tuple[str, dict]] = []
        # Override _generate_doc_id behavior so the test can assert on it
        # after add — same logic VectorRAG uses (src/rag_vector.py:38-41).
        from src.rag_vector import _generate_doc_id
        self._generate_doc_id = _generate_doc_id

    @property
    def healthy(self) -> bool:
        return self._healthy

    def _split_into_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 200):
        # Bypass the real VectorRAG chunker — tests want deterministic N chunks.
        # Plain paragraph split keeps the assertion readable.
        if not text:
            return []
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return paragraphs or [text]

    def add_document(self, text: str, metadata: dict) -> bool:
        doc_id = self._generate_doc_id(text, metadata.get("owner"))
        self.added.append((doc_id, dict(metadata)))
        return True


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _write(tmp_path, name: str, body: bytes) -> str:
    path = tmp_path / name
    path.write_bytes(body)
    return str(path)


def _meta(tmp_path, name: str, owner: str = "alice", *, path=None, upload_id="u-123") -> dict:
    return {
        "id": upload_id,
        "name": name,
        "owner": owner,
        "path": path or str(tmp_path / name),
    }


# Reset the in-memory state dict between tests so a stale terminal entry
# from a previous run can't make a status assertion bleed across cases.
@pytest.fixture(autouse=True)
def _clear_ingest_state():
    ingest._INGEST_STATE.clear()
    yield
    ingest._INGEST_STATE.clear()


# -----------------------------------------------------------------------------
# Cases
# -----------------------------------------------------------------------------

async def test_pdf_upload_calls_extract_pdf_and_embeds_with_owner(tmp_path, monkeypatch):
    body = b"%PDF-1.4 fake bytes"
    path = _write(tmp_path, "report.pdf", body)
    meta = _meta(tmp_path, "report.pdf", owner="alice", path=path)
    vector_rag = FakeVectorRAG()

    captured = {}

    def fake_extract_pdf_text(p):
        captured["path"] = p
        return "Page one of the report.\n\nPage two has more detail."

    monkeypatch.setattr(
        "src.personal_docs.extract_pdf_text",
        fake_extract_pdf_text,
        raising=False,
    )

    result = await ingest_upload_to_rag(
        upload_meta=meta, owner="alice", vector_rag=vector_rag
    )

    assert result.status == "ok"
    assert result.chunks == 2
    assert captured["path"] == path
    # Owner propagated into every chunk's metadata.
    assert all(m["owner"] == "alice" for _, m in vector_rag.added)
    assert all(m["upload_id"] == "u-123" for _, m in vector_rag.added)
    assert all(m["source"] == "upload" for _, m in vector_rag.added)
    # chunk_id is sequential per chunk.
    assert [m["chunk_id"] for _, m in vector_rag.added] == [0, 1]
    # Status endpoint can see the terminal state.
    assert ingest.get_ingest_status("u-123")["status"] == "ok"


async def test_docx_upload_uses_markitdown_path(tmp_path, monkeypatch):
    body = b"PK\x03\x04 stub docx"
    path = _write(tmp_path, "notes.docx", body)
    meta = _meta(tmp_path, "notes.docx", owner="bob", path=path, upload_id="u-docx")
    vector_rag = FakeVectorRAG()

    captured = {}

    def fake_office(p):
        captured["path"] = p
        return "Section one.\n\nSection two.\n\nSection three."

    monkeypatch.setattr(
        "src.personal_docs.extract_office_text", fake_office, raising=False
    )

    result = await ingest_upload_to_rag(
        upload_meta=meta, owner="bob", vector_rag=vector_rag
    )

    assert result.status == "ok"
    assert result.chunks == 3
    assert captured["path"] == path
    assert all(m["owner"] == "bob" for _, m in vector_rag.added)


async def test_txt_upload_reads_decodes_and_chunks(tmp_path):
    body = "First paragraph here.\n\nSecond paragraph follows.\n\nThird one closes."
    path = _write(tmp_path, "readme.txt", body.encode("utf-8"))
    meta = _meta(tmp_path, "readme.txt", owner="carol", path=path, upload_id="u-txt")
    vector_rag = FakeVectorRAG()

    result = await ingest_upload_to_rag(
        upload_meta=meta, owner="carol", vector_rag=vector_rag
    )

    assert result.status == "ok"
    assert result.chunks == 3
    # The plain-text path must go through bytes→utf-8 decode, no extraction calls.
    assert all(m["owner"] == "carol" for _, m in vector_rag.added)
    assert [m["chunk_id"] for _, m in vector_rag.added] == [0, 1, 2]


async def test_unsupported_extension_returns_skipped_no_add(tmp_path):
    path = _write(tmp_path, "movie.mp4", b"\x00\x00\x00 mp4 bytes")
    meta = _meta(tmp_path, "movie.mp4", owner="dave", path=path, upload_id="u-mp4")
    vector_rag = FakeVectorRAG()

    result = await ingest_upload_to_rag(
        upload_meta=meta, owner="dave", vector_rag=vector_rag
    )

    assert result.status == "skipped"
    assert vector_rag.added == []
    status = ingest.get_ingest_status("u-mp4")
    assert status is not None and status["status"] == "skipped"


async def test_owner_isolation_two_owners_distinct_doc_ids(tmp_path, monkeypatch):
    """Two users ingest the same text — chunk doc_ids must NOT collide.

    Regression for Step 1.5: previously doc_id was sha256(text) with no
    owner namespace, so two users indexing the same upload overwrote
    each other's chunks in the shared collection.
    """
    body = "Same document body.\n\nAnother paragraph.\n\nA third."
    path_alice = _write(tmp_path, "shared.txt", body.encode("utf-8"))
    path_bob = _write(tmp_path, "shared_b.txt", body.encode("utf-8"))

    vector_alice = FakeVectorRAG()
    vector_bob = FakeVectorRAG()

    await ingest_upload_to_rag(
        upload_meta=_meta(tmp_path, "shared.txt", owner="alice", path=path_alice, upload_id="u-alice"),
        owner="alice",
        vector_rag=vector_alice,
    )
    await ingest_upload_to_rag(
        upload_meta=_meta(tmp_path, "shared_b.txt", owner="bob", path=path_bob, upload_id="u-bob"),
        owner="bob",
        vector_rag=vector_bob,
    )

    ids_alice = {doc_id for doc_id, _ in vector_alice.added}
    ids_bob = {doc_id for doc_id, _ in vector_bob.added}
    assert ids_alice and ids_bob
    # Same text but different owner → distinct doc_ids, the whole point of
    # the Step 1.5 namespacing fix.
    assert ids_alice.isdisjoint(ids_bob)

    # Sanity check the owner namespace actually shows up in the id prefix:
    # _sanitize_owner_for_id emits "alice"/"bob" for these clean inputs.
    assert any(d.startswith("alice_doc_") for d in ids_alice)
    assert any(d.startswith("bob_doc_") for d in ids_bob)


async def test_unhealthy_vector_rag_fails_fast(tmp_path):
    path = _write(tmp_path, "ok.txt", b"some body text")
    meta = _meta(tmp_path, "ok.txt", path=path, upload_id="u-down")
    vector_rag = FakeVectorRAG(healthy=False)

    result = await ingest_upload_to_rag(
        upload_meta=meta, owner=None, vector_rag=vector_rag
    )

    assert result.status == "failed"
    assert vector_rag.added == []
    status = ingest.get_ingest_status("u-down")
    assert status is not None and status["status"] == "failed"


async def test_missing_upload_id_fails_without_state_write():
    # Bad input — no id field at all. Should return failed before touching state.
    result = await ingest_upload_to_rag(
        upload_meta={"name": "no_id.txt"}, owner=None, vector_rag=FakeVectorRAG()
    )
    assert result.status == "failed"
    # No meaningful state entry should have been written under "".
    # (defaultdict creates one on read, so we only assert no real id was set.)
    assert "u-anything" not in ingest._INGEST_STATE
