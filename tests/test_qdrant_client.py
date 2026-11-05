"""Regression tests for src/qdrant_client.py — singleton lifecycle and
``healthy()`` semantics.

Three behaviors covered:
  - First call creates a QdrantClient; second call returns the same instance.
  - ``reset_client()`` drops the singleton so the next call reconnects.
  - ``healthy()`` reflects actual reachability without raising.

Network is replaced with MagicMock + monkeypatch on ``_port_open``; tests do
not need a live Qdrant.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import src.qdrant_client as qc


@pytest.fixture(autouse=True)
def _reset_singleton():
    qc.reset_client()
    yield
    qc.reset_client()


def _fake_qdrant_client_class():
    class _FakeQdrantClient:
        instances = []

        def __init__(self, url=None, api_key=None, timeout=None, **kw):
            self.url = url
            self.api_key = api_key
            self.timeout = timeout
            self.get_collections = MagicMock(return_value=MagicMock(collections=[]))
            type(self).instances.append(self)

    return _FakeQdrantClient


def test_get_qdrant_client_returns_singleton(monkeypatch):
    FakeCls = _fake_qdrant_client_class()
    monkeypatch.setattr(qc, "_port_open", lambda *a, **k: True)
    fake_module = MagicMock()
    fake_module.QdrantClient = FakeCls
    monkeypatch.setitem(__import__("sys").modules, "qdrant_client", fake_module)

    first = qc.get_qdrant_client()
    second = qc.get_qdrant_client()
    assert first is second
    assert len(FakeCls.instances) == 1


def test_reset_client_drops_singleton(monkeypatch):
    FakeCls = _fake_qdrant_client_class()
    monkeypatch.setattr(qc, "_port_open", lambda *a, **k: True)
    fake_module = MagicMock()
    fake_module.QdrantClient = FakeCls
    monkeypatch.setitem(__import__("sys").modules, "qdrant_client", fake_module)

    first = qc.get_qdrant_client()
    qc.reset_client()
    second = qc.get_qdrant_client()

    assert first is not second
    assert len(FakeCls.instances) == 2


def test_get_qdrant_client_raises_when_unreachable(monkeypatch):
    # Force probe + smoke to fail: preflight port closed AND constructor blows up.
    monkeypatch.setattr(qc, "_port_open", lambda *a, **k: False)

    fake_module = MagicMock()
    fake_module.QdrantClient.side_effect = RuntimeError("boom")
    monkeypatch.setitem(__import__("sys").modules, "qdrant_client", fake_module)

    with pytest.raises(RuntimeError):
        qc.get_qdrant_client()
    # Singleton must not cache a failed connection.
    assert qc._client is None


def test_healthy_false_when_client_unreachable(monkeypatch):
    # get_qdrant_client() raises → healthy() must return False (not propagate).
    def _raise():
        raise RuntimeError("nope")

    monkeypatch.setattr(qc, "get_qdrant_client", _raise)
    assert qc.healthy() is False


def test_healthy_true_when_query_succeeds(monkeypatch):
    client = MagicMock()
    client.get_collections.return_value = MagicMock(collections=[])
    monkeypatch.setattr(qc, "get_qdrant_client", lambda: client)
    assert qc.healthy() is True
