"""Tests for the RAG admin tools (rag_list / rag_add_directory /
rag_remove_directory) and their admin/non-admin visibility gate.

Replaces the old MCP-RAG-server tests deleted in Step 1.6 of the migration
plan. Three concerns exercised here:
  1. `do_rag_list` filters index entries by owner for non-admins.
  2. `do_rag_add_directory` threads `owner` through to the RAG manager
     (the bug fix for the ownerless MCP path).
  3. `NON_ADMIN_BLOCKED_TOOLS` in `src/tool_security.py` actually hides
     all three tools from non-admins (visibility-gate regression).
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from src import tool_security
from src.tool_implementations import (
    _file_owner,
    do_rag_add_directory,
    do_rag_list,
    do_rag_remove_directory,
)


@pytest.fixture
def rag_managers(monkeypatch):
    """Inject fake RAG + personal_docs managers into ai_interaction.

    The admin tools read these globals via `_get_rag_admin_managers()`, so
    patching them at the source module is enough.
    """
    rag = MagicMock()
    rag.index_personal_documents.return_value = {"indexed_count": 4}
    rag.remove_directory.return_value = {"removed": 2}

    personal_docs = MagicMock()
    personal_docs.get_indexed_directories.return_value = ["/data/alice/notes"]
    personal_docs.add_directory.return_value = True
    personal_docs.remove_directory.return_value = True

    # The index is a list of dicts shaped like PersonalDocsManager emits:
    # {"name": ..., "path": "/data/personal_uploads/{owner}/..."}.
    personal_docs.index = [
        {"name": "a.txt", "path": "/data/personal_uploads/alice/a.txt"},
        {"name": "b.txt", "path": "/data/personal_uploads/alice/b.txt"},
        {"name": "c.txt", "path": "/data/personal_uploads/bob/c.txt"},
        {"name": "library.md", "path": "/data/library/library.md"},
    ]

    import src.ai_interaction as ai_interaction
    monkeypatch.setattr(ai_interaction, "_rag_manager", rag, raising=False)
    monkeypatch.setattr(ai_interaction, "_personal_docs_manager", personal_docs, raising=False)
    return rag, personal_docs


# -----------------------------------------------------------------------------
# Visibility gate (NON_ADMIN_BLOCKED_TOOLS)
# -----------------------------------------------------------------------------

def test_admin_tools_listed_in_visibility_gate():
    """All three admin tools MUST be in NON_ADMIN_BLOCKED_TOOLS — this is
    the only thing that makes them invisible to public users."""
    blocked = tool_security.NON_ADMIN_BLOCKED_TOOLS
    assert "rag_list" in blocked
    assert "rag_add_directory" in blocked
    assert "rag_remove_directory" in blocked


def test_blocked_tools_for_owner_admin_returns_empty(monkeypatch):
    # Admin owner sees no blockset — admin tools pass through.
    monkeypatch.setattr(
        tool_security, "owner_is_admin_or_single_user", lambda owner: True
    )
    assert tool_security.blocked_tools_for_owner("admin") == set()


def test_blocked_tools_for_owner_non_admin_includes_rag_tools():
    blocked = tool_security.blocked_tools_for_owner("alice")
    assert "rag_list" in blocked
    assert "rag_add_directory" in blocked
    assert "rag_remove_directory" in blocked


def test_is_public_blocked_tool_rag_admin_tools():
    for t in ("rag_list", "rag_add_directory", "rag_remove_directory"):
        assert tool_security.is_public_blocked_tool(t) is True


# -----------------------------------------------------------------------------
# _file_owner path-prefix extraction
# -----------------------------------------------------------------------------

def test_file_owner_extracts_from_personal_uploads_prefix():
    entry = {"path": "/data/personal_uploads/alice/notes.txt"}
    assert _file_owner(entry, "alice") == "alice"


def test_file_owner_lowercases_owner_segment():
    entry = {"path": "/data/personal_uploads/Alice/notes.txt"}
    assert _file_owner(entry, "alice") == "alice"


def test_file_owner_unknown_returns_empty():
    # Library uploads lack an owner prefix in path — surfaced as shared to admins only.
    entry = {"path": "/data/library/notes.txt"}
    assert _file_owner(entry, "alice") == ""


def test_file_owner_handles_non_dict():
    assert _file_owner("not a dict", "alice") == ""


# -----------------------------------------------------------------------------
# do_rag_list owner filter
# -----------------------------------------------------------------------------

async def test_rag_list_no_owner_returns_all_entries(rag_managers):
    # No owner set (admin path): every entry is visible.
    result = await do_rag_list("", owner=None)
    blob = result["results"]
    # 4 entries in the mocked index; we don't truncate.
    assert "a.txt" in blob
    assert "b.txt" in blob
    assert "c.txt" in blob
    assert "library.md" in blob


async def test_rag_list_filters_by_owner_alice(rag_managers):
    result = await do_rag_list("", owner="alice")
    blob = result["results"]
    assert "a.txt" in blob
    assert "b.txt" in blob
    # Bob's file filtered out for alice.
    assert "c.txt" not in blob
    # Legacy ownerless library uploads also filtered out.
    assert "library.md" not in blob


async def test_rag_list_filters_by_owner_bob(rag_managers):
    result = await do_rag_list("", owner="bob")
    blob = result["results"]
    assert "c.txt" in blob
    assert "a.txt" not in blob
    assert "b.txt" not in blob


async def test_rag_list_owner_case_insensitive(rag_managers):
    # Owner comparison is case-insensitive — "Alice" matches "alice" paths.
    result = await do_rag_list("", owner="Alice")
    blob = result["results"]
    assert "a.txt" in blob
    assert "c.txt" not in blob


async def test_rag_list_no_managers_configured(monkeypatch):
    import src.ai_interaction as ai_interaction
    monkeypatch.setattr(ai_interaction, "_rag_manager", None, raising=False)
    monkeypatch.setattr(ai_interaction, "_personal_docs_manager", None, raising=False)
    result = await do_rag_list("", owner=None)
    assert result.get("exit_code") == 1


# -----------------------------------------------------------------------------
# do_rag_add_directory owner propagation
# -----------------------------------------------------------------------------

async def test_rag_add_directory_threads_owner_to_rag_manager(tmp_path, rag_managers):
    rag, personal_docs = rag_managers
    directory = tmp_path / "lib"
    directory.mkdir()
    (directory / "f.txt").write_text("hello")

    content = f'{{"directory": "{directory}"}}'
    result = await do_rag_add_directory(content, owner="alice")

    assert result["action"] == "add_directory"
    assert result["owner"] == "alice"
    rag.index_personal_documents.assert_called_once_with(str(directory), owner="alice")
    personal_docs.add_directory.assert_called_once_with(str(directory), index=False, owner="alice")


async def test_rag_add_directory_admin_can_override_owner(tmp_path, rag_managers):
    """Admin passes owner= in the JSON to act on a user's behalf."""
    rag, personal_docs = rag_managers
    directory = tmp_path / "lib"
    directory.mkdir()
    (directory / "f.txt").write_text("hello")

    content = f'{{"directory": "{directory}", "owner": "charlie"}}'
    result = await do_rag_add_directory(content, owner="admin")

    assert result["owner"] == "charlie"
    rag.index_personal_documents.assert_called_once_with(str(directory), owner="charlie")


async def test_rag_add_directory_missing_dir_returns_error(rag_managers):
    result = await do_rag_add_directory('{"directory": "/nope/not/here"}', owner="alice")
    assert result.get("exit_code") == 1
    assert "not found" in result.get("error", "").lower()


async def test_rag_add_directory_no_directory_arg(rag_managers):
    result = await do_rag_add_directory('{}', owner="alice")
    assert result.get("exit_code") == 1
    assert "directory" in result.get("error", "").lower()


# -----------------------------------------------------------------------------
# do_rag_remove_directory
# -----------------------------------------------------------------------------

async def test_rag_remove_directory_calls_both_managers(rag_managers):
    rag, personal_docs = rag_managers
    result = await do_rag_remove_directory('{"directory": "/data/alice/notes"}', owner="alice")

    assert result["action"] == "remove_directory"
    assert result["removed_from_index"] is True
    personal_docs.remove_directory.assert_called_once_with("/data/alice/notes")
    rag.remove_directory.assert_called_once_with("/data/alice/notes")


async def test_rag_remove_directory_missing_directory_arg(rag_managers):
    result = await do_rag_remove_directory('{}', owner="alice")
    assert result.get("exit_code") == 1
    assert "directory" in result.get("error", "").lower()


async def test_rag_remove_directory_resilient_to_personal_docs_failure(rag_managers):
    rag, personal_docs = rag_managers
    personal_docs.remove_directory.side_effect = RuntimeError("boom")
    # Must not raise — best-effort cascade.
    result = await do_rag_remove_directory('{"directory": "/data/x"}', owner="alice")
    assert result["action"] == "remove_directory"
    assert result["removed_from_index"] is False
    rag.remove_directory.assert_called_once_with("/data/x")
