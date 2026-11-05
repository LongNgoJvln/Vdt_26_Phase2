"""Regression tests for ``MemoryVectorStore`` against the Qdrant backend.

Locks three promises of the post-Chroma memory store:
  - ``add`` writes a PointStruct whose payload contains ``text``, ``owner``,
    and ``source="memory"``, with the memory_id used as the point id.
  - ``search(query, k, owner=...)`` routes through ``query_points`` with an
    owner-scoped Filter (multi-tenant isolation via payload, not collection).
  - ``find_similar`` is owner-scoped as well — duplicate detection does not
    leak across users.

Plus a rebuild test: when ``rebuild(memories)`` is called, the dropped-and-
recreated collection continues to record each point's ``owner`` payload, and
identical memory_ids across owners stay distinct only when their payload
owner differs.

The Qdrant client and embedder are both fakes — no live network or model.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.memory_vector import MemoryVectorStore


# -----------------------------------------------------------------------------
# Fakes
# -----------------------------------------------------------------------------

class _FakeEmbedder:
    """Deterministic 384-d embeddings keyed on the input string."""

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
    """Owner-aware fake that records every interaction VectorStore makes."""

    def __init__(self):
        self.upserts: list[dict] = []
        self.deletes: list[dict] = []
        self.collection_drops: list[str] = []
        self.collection_creates: list[str] = []
        self._points_by_owner: dict[str | None, list[_FakeHit]] = {}
        self._owner_filter_seen = None
        self.get_collection = MagicMock()
        self.get_collections = MagicMock(return_value=MagicMock(collections=[]))
        self.create_payload_index = MagicMock()

    def create_collection(self, *, collection_name, vectors_config, **kw):
        self.collection_creates.append(collection_name)

    def delete_collection(self, *, collection_name):
        self.collection_drops.append(collection_name)

    def query_points(self, *, collection_name, query, using=None,
                     query_filter=None, limit=None, with_payload=True):
        self._owner_filter_seen = query_filter
        owner_val = _extract_filter_value(query_filter, "owner")
        hits = self._points_by_owner.get(owner_val, [])
        return SimpleNamespace(points=hits[:limit] if limit else hits)

    def search(self, **kw):  # legacy fallback for older qdrant-client
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
                _FakeHit(p.id, score=0.95, payload=dict(p.payload))
            )
        self.upserts.append({"collection": collection_name, "points": points})
        return MagicMock()

    def delete(self, *, collection_name, points_selector, wait=True):
        self.deletes.append({"collection": collection_name, "ids": points_selector})

    def count(self, *, collection_name, count_filter=None, exact=True):
        if count_filter is None:
            # Admin / global view — sum every owner bucket.
            n = sum(len(v) for v in self._points_by_owner.values())
        else:
            owner_val = _extract_filter_value(count_filter, "owner")
            n = len(self._points_by_owner.get(owner_val, []))
        return SimpleNamespace(count=n)


def _extract_filter_value(filter_obj, key):
    if filter_obj is None or not getattr(filter_obj, "must", None):
        return None
    for cond in filter_obj.must:
        if getattr(cond, "key", None) == key:
            match = getattr(cond, "match", None)
            return getattr(match, "value", None)
    return None


@pytest.fixture
def store():
    """Build a MemoryVectorStore without running the real init path."""
    client = _FakeQdrantClient()
    instance = MemoryVectorStore.__new__(MemoryVectorStore)
    instance._data_dir = "data/legacy"
    instance._model = _FakeEmbedder()
    instance._client = client
    instance._dim = 384
    instance._healthy = True
    return instance, client


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

def test_add_writes_owner_tagged_payload_with_memory_id(store):
    inst, client = store
    inst.add("mem-1", "preferred tab width is 2", owner="alice")

    assert len(client.upserts) == 1
    call = client.upserts[0]
    assert call["collection"] == MemoryVectorStore.COLLECTION_NAME

    point = call["points"][0]
    assert point.id == "mem-1"
    assert point.payload["text"] == "preferred tab width is 2"
    assert point.payload["owner"] == "alice"
    assert point.payload["source"] == "memory"
    assert point.payload["id"] == "mem-1"


def test_add_without_owner_omits_owner_field(store):
    """Legacy / admin path: no owner means no owner key in the payload at all.

    A ``None`` value would silently index and force admin lookups through an
    owner-is-null filter — we want the field absent instead.
    """
    inst, _ = store
    inst.add("mem-2", "system-wide note", owner=None)

    # Re-fetch by inspecting the client's upsert log via the same fixture.
    inst2, client2 = store
    inst2.add("mem-3", "another note", owner=None)
    payloads = [p.payload for c in client2.upserts for p in c["points"]]
    assert all("owner" not in p for p in payloads)


def test_search_routes_through_query_points_with_owner_filter(store):
    inst, client = store
    # Same text, two owners — must stay isolated.
    inst.add("mem-a", "shared concern", owner="alice")
    inst.add("mem-b", "shared concern", owner="bob")

    results = inst.search("shared concern", k=5, owner="alice")
    assert client._owner_filter_seen is not None
    assert _extract_filter_value(client._owner_filter_seen, "owner") == "alice"
    for r in results:
        # Every hit must belong to alice — owner field absent or == alice is
        # NOT acceptable under the owner-scoped contract.
        assert r["memory_id"] == "mem-a"


def test_search_unfiltered_for_admin_path(store):
    """When owner is None we skip the filter (admin / global lookup)."""
    inst, client = store
    inst.add("mem-x", "everyone's note", owner="alice")
    inst.add("mem-y", "everyone's note", owner="bob")

    inst.search("everyone", k=10, owner=None)
    assert client._owner_filter_seen is None


def test_find_similar_is_owner_scoped(store):
    """Duplicate detection within one owner — not across all owners."""
    inst, client = store
    inst.add("dup-1", "I prefer tabs over spaces", owner="alice")
    inst.add("dup-2", "I prefer tabs over spaces", owner="bob")

    # Alice searching for a similar memory must only see her own entry.
    hit = inst.find_similar("tabs vs spaces", threshold=0.0, owner="alice")
    assert hit == "dup-1"

    # Owner filter must have been passed — not a global scan.
    assert _extract_filter_value(client._owner_filter_seen, "owner") == "alice"


def test_find_similar_returns_none_when_no_owner_match(store):
    inst, _ = store
    inst.add("dup-1", "shared text", owner="alice")

    # Bob has no memories — must return None, not alice's near-match.
    assert inst.find_similar("shared text", threshold=0.0, owner="bob") is None


def test_rebuild_preserves_owner_payload(store):
    inst, client = store
    memories = [
        {"id": "m1", "text": "alice's note", "owner": "alice"},
        {"id": "m2", "text": "bob's note", "owner": "bob"},
        {"id": "m3", "text": "legacy note"},  # owner intentionally missing
    ]
    inst.rebuild(memories)

    # Collection was dropped before re-creating — the wipe semantics that
    # the admin Danger-Zone relies on.
    assert MemoryVectorStore.COLLECTION_NAME in client.collection_drops

    payloads = {p.id: p.payload for c in client.upserts for p in c["points"]}
    assert payloads["m1"]["owner"] == "alice"
    assert payloads["m2"]["owner"] == "bob"
    # Legacy entry has no owner field — admin/global fallback.
    assert "owner" not in payloads["m3"]


def test_count_filters_by_owner(store):
    inst, _ = store
    inst.add("m1", "a", owner="alice")
    inst.add("m2", "b", owner="alice")
    inst.add("m3", "c", owner="bob")

    assert inst.count(owner="alice") == 2
    assert inst.count(owner="bob") == 1
    # No filter → total across every owner (admin view).
    assert inst.count() == 3


def test_remove_uses_point_selector(store):
    inst, client = store
    inst.add("m1", "doomed", owner="alice")
    inst.remove("m1")
    assert client.deletes == [
        {"collection": MemoryVectorStore.COLLECTION_NAME, "ids": ["m1"]}
    ]
