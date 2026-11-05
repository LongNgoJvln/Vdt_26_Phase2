"""Tests for VectorRAG's Qdrant-backed implementation.

Covers three regression points from the Chroma→Qdrant migration:
  - add_document writes a single upsert with owner-namespaced id and a payload
    that contains ``text`` and ``owner``.
  - search() routes through ``query_points`` with an owner-scoped Filter when
    owner is supplied.
  - Owner-determinism: identical text uploaded by two different owners
    produces distinct doc_ids ( regression for the legacy
    ``sha256(text)`` global doc-id ).

No live Qdrant or embedding endpoint — embedder and client are both fakes.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.rag_vector import VectorRAG, _generate_doc_id


# -----------------------------------------------------------------------------
# Fake dependencies
# -----------------------------------------------------------------------------

class _FakeEmbedder:
    """Returns a deterministic 384-d vector per input string."""

    def __init__(self):
        self.url = "fake://embedder"
        self.model = "fake-embed"

    def encode(self, texts, normalize_embeddings=True):
        import numpy as np
        return np.array([[float((hash(t) & 0xFF) + i) / 255.0
                          for i in range(384)] for t in texts])


class _FakeHit:
    def __init__(self, point_id, score, payload):
        self.id = point_id
        self.score = score
        self.payload = payload


class _FakeQdrantClient:
    """Records every call VectorRAG makes so tests can assert on them."""

    def __init__(self):
        self.upserts: list[dict] = []
        self._points_by_owner: dict[str, list[_FakeHit]] = {}
        self._owner_filter_seen: dict = None
        from unittest.mock import MagicMock
        self.get_collection = MagicMock()
        self.get_collections = MagicMock(return_value=MagicMock(collections=[]))
        self.create_collection = MagicMock()
        self.create_payload_index = MagicMock()

    def query_points(self, *, collection_name, query, using=None,
                     query_filter=None, limit=None, with_payload=True):
        self._owner_filter_seen = query_filter
        owner_val = _extract_filter_value(query_filter, "owner")
        hits = self._points_by_owner.get(owner_val, [])
        return SimpleNamespace(points=hits[:limit] if limit else hits)

    def search(self, **kw):  # legacy path
        return self.query_points(**{
            "collection_name": kw["collection_name"],
            "query": kw["query_vector"],
            "query_filter": kw.get("query_filter"),
            "limit": kw.get("limit"),
            "with_payload": kw.get("with_payload", True),
        }).points

    def upsert(self, *, collection_name, points, wait=True):
        for p in points:
            owner = p.payload.get("owner") if hasattr(p, "payload") else None
            self._points_by_owner.setdefault(owner, []).append(
                _FakeHit(p.id, score=0.9, payload=dict(p.payload))
            )
        self.upserts.append({"collection": collection_name, "points": points})
        return MagicMock()

    def count(self, *, collection_name, count_filter=None, exact=True):
        owner_val = _extract_filter_value(count_filter, "owner")
        n = len(self._points_by_owner.get(owner_val, []))
        return SimpleNamespace(count=n)

    def delete(self, **kw):
        pass


def _extract_filter_value(filter_obj, key):
    """Return the MatchValue bound to ``key`` in a Filter (or None)."""
    if filter_obj is None or not getattr(filter_obj, "must", None):
        return None
    for cond in filter_obj.must:
        if getattr(cond, "key", None) == key:
            match = getattr(cond, "match", None)
            return getattr(match, "value", None)
    return None


@pytest.fixture
def rag(monkeypatch):
    client = _FakeQdrantClient()

    def _fake_get_qdrant_client():
        return client

    def _fake_get_embedding_client():
        return _FakeEmbedder()

    monkeypatch.setattr(
        "src.rag_vector.get_qdrant_client" if "get_qdrant_client" in dir(__import__("src.rag_vector", fromlist=["x"]))
        else "src.qdrant_client.get_qdrant_client",
        _fake_get_qdrant_client,
    )
    # Import paths used by VectorRAG (lazy imports inside _initialize_system).
    import src.rag_vector as rv
    monkeypatch.setattr(rv, "_ensure_collection", lambda *a, **k: None)

    # The lazy imports in rag_vector point at src.qdrant_client.get_qdrant_client.
    import src.qdrant_client as qc
    monkeypatch.setattr(qc, "get_qdrant_client", _fake_get_qdrant_client)

    import src.embeddings as emb
    monkeypatch.setattr(emb, "get_embedding_client", _fake_get_embedding_client)

    # Construct a VectorRAG and manually attach the fake client (bypassing init).
    instance = VectorRAG.__new__(VectorRAG)
    instance.collection_name = "ody-rag-alice"
    instance._client = client
    instance._model = _FakeEmbedder()
    instance._healthy = True
    instance._dim = 384
    instance.persist_directory = "data/chroma"  # back-compat arg
    return instance, client


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

def test_add_document_writes_owner_namespaced_id_and_payload(rag):
    instance, client = rag
    ok = instance.add_document(
        "The quick brown fox",
        {"owner": "alice", "source": "upload", "upload_id": "u1",
         "filename": "fox.txt", "type": ".txt"},
    )
    assert ok is True
    assert len(client.upserts) == 1
    call = client.upserts[0]
    assert call["collection"] == "ody-rag-alice"

    point = call["points"][0]
    assert point.payload["text"] == "The quick brown fox"
    assert point.payload["owner"] == "alice"
    assert point.payload["source"] == "upload"
    assert point.payload["upload_id"] == "u1"
    # id must be namespaced by owner — _generate_doc_id puts owner_ prefix.
    assert point.id.startswith("alice"), point.id


def test_search_routes_through_query_points_with_owner_filter(rag):
    instance, client = rag
    # Seed two different owners.
    instance.collection_name = "shared"
    instance.add_document("alice secret", {"owner": "alice"})
    instance.add_document("bob secret", {"owner": "bob"})

    # Query as alice.
    results = instance.search("secret", k=5, owner="alice")
    assert client._owner_filter_seen is not None
    assert _extract_filter_value(client._owner_filter_seen, "owner") == "alice"
    # Only alice's payload should be returned.
    for r in results:
        assert r["metadata"]["owner"] == "alice"


def test_two_owners_same_text_produce_distinct_doc_ids():
    """The legacy ``sha256(text)`` doc-id collided two owners; the new
    namespaced form must keep them distinct."""
    text = "duplicate content"
    id_a = _generate_doc_id(text, owner="alice")
    id_b = _generate_doc_id(text, owner="bob")
    assert id_a != id_b


def test_add_document_returns_false_when_unhealthy(monkeypatch):
    unhealthy = VectorRAG.__new__(VectorRAG)
    unhealthy._client = None
    unhealthy._model = None
    unhealthy._healthy = False
    unhealthy._dim = None
    unhealthy.collection_name = "x"
    unhealthy.persist_directory = "data/chroma"
    assert unhealthy.add_document("x", {"owner": "y"}) is False
