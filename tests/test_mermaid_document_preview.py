"""Static regression checks for offline Mermaid document previews."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_mermaid_bundle_is_self_hosted_and_precached():
    index = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    service_worker = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    bundle = ROOT / "static" / "lib" / "mermaid.min.js"

    assert 'src="/static/lib/mermaid.min.js"' in index
    assert "cdn.jsdelivr.net/npm/mermaid" not in index
    assert bundle.is_file()
    assert bundle.stat().st_size > 100_000
    assert "'/static/lib/mermaid.min.js'" in service_worker


def test_markdown_document_preview_invokes_mermaid_renderer_after_showing():
    source = (ROOT / "static" / "js" / "document.js").read_text(encoding="utf-8")
    function_start = source.index("function _setMarkdownPreviewActive")
    function_end = source.index("function toggleMarkdownPreview", function_start)
    function_body = source[function_start:function_end]

    show_at = function_body.index("preview.style.display = ''")
    render_at = function_body.index("markdownModule.renderMermaid(preview)")
    assert show_at < render_at
