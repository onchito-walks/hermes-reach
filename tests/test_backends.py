from hermes_trailhead.backends import execute_backend_chain, _youtube_result_url


def test_youtube_result_url_rejects_corporate_navigation_pages():
    assert _youtube_result_url("https://www.youtube.com/watch?v=abc123") is True
    assert _youtube_result_url("https://youtu.be/abc123") is True
    assert _youtube_result_url("https://www.youtube.com/shorts/abc123") is True
    assert _youtube_result_url("https://www.youtube.com/@creator") is True
    assert _youtube_result_url("https://www.youtube.com/about/") is False
    assert _youtube_result_url("https://www.youtube.com/about/press/") is False
    assert _youtube_result_url("https://www.youtube.com/about/copyright/") is False


def test_youtube_backend_filters_navigation_and_falls_through_to_video_results():
    calls = []

    def fake_fetch(url, timeout):
        calls.append(url)
        if "r.jina.ai" in url:
            return """
## [About](https://www.youtube.com/about/)
Corporate page.
## [Press](https://www.youtube.com/about/press/)
Corporate page.
"""
        return """
<a href="https://www.youtube.com/about/">About</a>
<a href="https://www.youtube.com/watch?v=abc123">Real demo video</a>
<a href="https://youtu.be/def456">Second real video</a>
"""

    result = execute_backend_chain("youtube", "Claude Code Codex", limit=2, fetch=fake_fetch)

    assert result.engine == "ddg_lite_site_youtube"
    assert len(calls) >= 2
    assert [hit.url for hit in result.hits] == [
        "https://www.youtube.com/watch?v=abc123",
        "https://youtu.be/def456",
    ]
