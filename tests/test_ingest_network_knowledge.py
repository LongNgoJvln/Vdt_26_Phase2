from pathlib import Path

import pytest

from scripts.ingest_network_knowledge import build_chunks, discover_documents, parse_args


class FakeRag:
    @staticmethod
    def _split_into_chunks(content):
        return [content]


def test_discover_documents_keeps_categories_and_skips_placeholders(tmp_path: Path):
    knowledge = tmp_path / "knowledge"
    instructions = tmp_path / "instructions"
    knowledge.mkdir()
    instructions.mkdir()
    (knowledge / "overview.md").write_text("EPC overview", encoding="utf-8")
    (knowledge / "PUT_MORE_HERE.txt").write_text("placeholder", encoding="utf-8")
    (instructions / "procedure.md").write_text("set something", encoding="utf-8")

    documents = discover_documents(tmp_path, ("knowledge", "instructions"))

    assert [(item.category, item.relative_path) for item in documents] == [
        ("knowledge", "overview.md"),
        ("instructions", "procedure.md"),
    ]


def test_build_chunks_adds_owner_role_and_stable_source(tmp_path: Path):
    path = tmp_path / "MME.md"
    path.write_text("MME procedure", encoding="utf-8")
    document = discover_documents_from_file(path)

    records = build_chunks(FakeRag(), document, "operator")

    assert records[0][0] == "MME procedure"
    metadata = records[0][1]
    assert metadata["owner"] == "operator"
    assert metadata["knowledge_role"] == "instructions"
    assert metadata["source"] == "network-kb:instructions:MME.md"


def discover_documents_from_file(path: Path):
    from scripts.ingest_network_knowledge import SourceDocument

    return SourceDocument("instructions", path, path.name)


def test_owner_is_required():
    with pytest.raises(SystemExit):
        parse_args([])
