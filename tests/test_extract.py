import json

from hermes_trailhead.search import SearchHit
from hermes_trailhead.extract import (
    ExtractionResult,
    ExtractedHit,
    _classify_source_type,
    extract_one,
    extract_hits,
)


def test_classify_source_type_github():
    assert _classify_source_type("https://github.com/NousResearch/hermes-agent/issues/42") == "github"


def test_classify_source_type_reddit():
    assert _classify_source_type("https://www.reddit.com/r/hermesagent/comments/abc123/") == "reddit"


def test_classify_source_type_x():
    assert _classify_source_type("https://x.com/nousresearch/status/123") == "x"


def test_classify_source_type_tiktok():
    assert _classify_source_type("https://www.tiktok.com/@user/video/123") == "tiktok"


def test_classify_source_type_youtube():
    assert _classify_source_type("https://www.youtube.com/watch?v=abc123") == "youtube"


def test_classify_source_type_docs():
    assert _classify_source_type("https://docs.hermes-agent.nousresearch.com/config") == "docs"


def test_classify_source_type_forum():
    assert _classify_source_type("https://stackoverflow.com/questions/123") == "forum"


def test_classify_source_type_generic():
    assert _classify_source_type("https://example.com/blog/post") == "web"


def test_classify_source_type_pdf():
    assert _classify_source_type("https://example.com/report.pdf") == "pdf"


def test_tiktok_extraction_is_blocked_not_error():
    result = extract_one("https://www.tiktok.com/@user/video/123", fetch=lambda u, t: "fake content")
    assert result.status == "blocked"
    assert result.source_type == "tiktok"
    assert "browser" in result.error_message.lower()


def test_instagram_extraction_is_blocked():
    result = extract_one("https://www.instagram.com/p/abc123/", fetch=lambda u, t: "fake content")
    assert result.status == "blocked"
    assert result.source_type == "instagram"


def test_extraction_success():
    def fake_fetch(url, timeout):
        return "This is real content from a web page. " * 10

    result = extract_one("https://example.com/article", fetch=fake_fetch)
    assert result.status == "ok"
    assert result.content_length > 100
    assert result.source_type == "web"
    assert result.usable is True


def test_extraction_too_short_is_not_usable():
    def fake_fetch(url, timeout):
        return "short"

    result = extract_one("https://example.com/empty", fetch=fake_fetch)
    assert result.status == "error"
    assert not result.usable


def test_extraction_network_error_falls_to_error():
    def fake_fetch(url, timeout):
        raise OSError("Connection refused")

    result = extract_one("https://example.com/dead", fetch=fake_fetch)
    assert result.status == "error"
    assert "Could not extract" in result.error_message


def test_extraction_result_to_dict():
    result = ExtractionResult(status="ok", content="hello world", content_length=11, source_type="web")
    d = result.to_dict()
    assert d["status"] == "ok"
    assert d["content_length"] == 11
    assert d["source_type"] == "web"


def test_extracted_hit_from_search_hit():
    hit = SearchHit(title="Test", url="https://example.com", snippet="A test")
    eh = ExtractedHit.from_search_hit(hit)
    assert eh.title == "Test"
    assert eh.url == "https://example.com"
    assert eh.extraction.status == "not_attempted"


def test_extracted_hit_to_dict():
    eh = ExtractedHit(
        title="Test",
        url="https://example.com",
        snippet="Snippet",
        extraction=ExtractionResult(status="ok", content="hello", content_length=5, source_type="web"),
    )
    d = eh.to_dict()
    assert set(d) == {"title", "url", "snippet", "extraction"}
    assert d["extraction"]["status"] == "ok"


def test_extract_hits_respects_limit():
    def fake_fetch(url, timeout):
        return "Real content from a webpage that is long enough to pass. " * 5

    hits = tuple(
        SearchHit(title=f"Hit {i}", url=f"https://example.com/{i}", snippet=f"Snippet {i}")
        for i in range(10)
    )
    results = extract_hits(hits, limit=3, fetch=fake_fetch)
    assert len(results) == 3


def test_extract_hits_empty_input():
    results = extract_hits((), limit=5)
    assert len(results) == 0
