"""Behaviour tests for the context-engineering RAG loop in ChatProcessor.

Two regression points locked in here:
  - short follow-up messages inherit the previous user turns via
    ``_recent_user_text`` so RAG retrieval keeps surfacing the same chunks
    across a multi-turn conversation.
  - the threshold consumes ``vector_similarity`` (pure cosine), not the
    hybrid ``similarity``, so the cutoff stays stable regardless of how the
    keyword leg is weighted.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.chat_processor import ChatProcessor, _recent_user_text


# ── helpers ──────────────────────────────────────────────────────────────

class _MemoryManager:
    def load(self, owner=None):
        return []

    def increment_uses(self, _ids):
        pass


class _FakeRagManager:
    """Records the search() query and returns canned hits."""

    def __init__(self, hits):
        self._hits = hits
        self.queries: list[str] = []

    def search(self, query, k=5, owner=None):
        self.queries.append(query)
        return list(self._hits)


def _build_processor(rag_hits=None) -> tuple[ChatProcessor, _FakeRagManager]:
    personal_docs = SimpleNamespace(rag_manager=None)
    cp = ChatProcessor(
        memory_manager=_MemoryManager(),
        personal_docs_manager=personal_docs,
    )
    rag = _FakeRagManager(rag_hits or [])
    personal_docs.rag_manager = rag
    return cp, rag


# ── _recent_user_text ─────────────────────────────────────────────────────

def test_recent_user_text_concatenates_recent_user_turns():
    msgs = [
        {"role": "user", "content": "tell me about reports"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "yes do it in november"},
    ]
    out = _recent_user_text(msgs)
    assert "tell me about reports" in out
    assert "yes do it in november" in out


def test_recent_user_text_skips_tool_result_envelopes():
    msgs = [
        {"role": "user", "content": "[Tool execution results] blah"},
        {"role": "user", "content": "the real follow-up"},
    ]
    out = _recent_user_text(msgs)
    assert out == "the real follow-up"


def test_recent_user_text_respects_max_window():
    msgs = [{"role": "user", "content": f"msg number {i}"} for i in range(10)]
    out = _recent_user_text(msgs, max_user=3, max_chars=100)
    assert "msg number 9" in out
    assert "msg number 0" not in out
    assert len(out) <= 100


# ── behaviour through build_context_preface ──────────────────────────────

def test_rag_retrieval_folds_in_recent_user_history():
    cp, rag = _build_processor(rag_hits=[{
        "id": "x1",
        "document": "Quarterly revenue was $5M in Q3.",
        "metadata": {"filename": "q3-report.pdf"},
        "similarity": 0.9,
        "vector_similarity": 0.9,
    }])

    history = [
        {"role": "user", "content": "summarize the Q3 revenue report"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "yes"},  # contextless follow-up
    ]
    cp.build_context_preface(
        message="yes",
        session=MagicMock(),
        use_rag=True,
        use_memory=False,
        owner="alice",
        history=history,
    )

    assert len(rag.queries) == 1
    # The query must include the original rich turn, not just "yes".
    assert "Q3 revenue" in rag.queries[0]
    assert rag.queries[0] != "yes"


def test_rag_retrieval_without_history_uses_message_only():
    cp, rag = _build_processor(rag_hits=[])
    cp.build_context_preface(
        message="standalone question about the report",
        session=MagicMock(),
        use_rag=True,
        use_memory=False,
        owner="alice",
        history=None,
    )
    assert rag.queries == ["standalone question about the report"]


# ── threshold semantics ───────────────────────────────────────────────────

def test_threshold_uses_vector_similarity_not_hybrid():
    """A hit with strong vector match but zero keyword overlap must clear the
    threshold. Hybrid ``similarity`` would land at ~0.7*vector and likely
    drop under the cliff; ``vector_similarity`` keeps it deterministic."""
    cp, rag = _build_processor(rag_hits=[{
        "id": "x",
        "document": "irrelevant kw body",
        "metadata": {"filename": "a.pdf"},
        # Strong vector, deliberately low hybrid score.
        "similarity": 0.30,        # below old 0.35 if compared naively
        "vector_similarity": 0.55, # well above 0.35 on pure cosine
        "keyword_score": 0.0,
    }])
    preface, rag_sources, _ = cp.build_context_preface(
        message="some query",
        session=MagicMock(),
        use_rag=True,
        use_memory=False,
        owner="alice",
        history=None,
    )
    assert rag_sources, "vector_similarity 0.55 must clear threshold 0.35"


def test_threshold_drops_weak_vector_hit():
    cp, rag = _build_processor(rag_hits=[{
        "id": "x",
        "document": "body",
        "metadata": {"filename": "a.pdf"},
        "similarity": 0.30,
        "vector_similarity": 0.20,  # too weak even on pure cosine
    }])
    _preface, rag_sources, _ = cp.build_context_preface(
        message="q",
        session=MagicMock(),
        use_rag=True,
        use_memory=False,
        owner="alice",
        history=None,
    )
    assert rag_sources == []
