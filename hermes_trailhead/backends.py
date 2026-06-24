"""Hermes Trailhead multi-backend search engine.

Each source family gets its own ranked chain of search backends.
No single backend failure can crater all results — each lane has
independent fallback paths.  The engine tries backends in order;
first success wins.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import quote_plus, urlparse
import urllib.request


FetchFn = Callable[[str, int], str]


@dataclass
class Backend:
    """One search backend in a platform's ranked chain."""
    name: str
    description: str
    build_url: Callable[[str], str]
    parser: Callable  # (str, int) -> tuple; resolved via _get_parsers()
    timeout: int = 20
    needs_approval: bool = False
    paid: bool = False
    accept_url: Callable[[str], bool] | None = None


# ── Lazy parser resolution (avoids circular import search ↔ backends) ─────

_parsers = None

def _get_parsers():
    global _parsers
    if _parsers is None:
        from .search import (
            _parse_markdown_search_results,
            _parse_html_search_results,
        )
        _parsers = (_parse_markdown_search_results, _parse_html_search_results)
    return _parsers


def _mk() -> Callable:
    """Return markdown parser."""
    return _get_parsers()[0]


def _hp() -> Callable:
    """Return HTML parser."""
    return _get_parsers()[1]


# ── URL builders ──────────────────────────────────────────────────────────


def _ddg_lite_url(query: str) -> str:
    return f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"


def _ddg_html_url(query: str) -> str:
    return f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"


def _jina_ddg_url(query: str) -> str:
    return f"https://r.jina.ai/http://duckduckgo.com/html/?q={quote_plus(query)}"


def _github_search_url(query: str) -> str:
    return f"https://github.com/search?q={quote_plus(query)}&type=issues"


def _youtube_search_url(query: str) -> str:
    return f"https://www.youtube.com/results?search_query={quote_plus(query)}"


def _redlib_search_url(query: str) -> str:
    return f"https://redlib.perennialte.ch/search?q={quote_plus(query)}"


def _nitter_search_url(query: str) -> str:
    return f"http://localhost:8788/search?f=tweets&q={quote_plus(query)}"


def _youtube_result_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    return (
        "youtu.be" in host
        or ("youtube.com" in host and (path == "/watch" or path.startswith("/shorts/") or path.startswith("/@")))
    )


# ── HTTP fetch ────────────────────────────────────────────────────────────


def _fetch(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 Hermes Trailhead/0.3 (multi-backend)",
            "Accept": "text/html,text/plain,text/markdown,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


# ── Platform backend chains ───────────────────────────────────────────────


BACKENDS: dict[str, list[Backend]] = {
    "github": [
        Backend("github_search", "GitHub issue search", _github_search_url, _hp),
        Backend("jina_duckduckgo_site_github", "Jina Reader over DuckDuckGo site:github.com",
                lambda q: _jina_ddg_url(f"site:github.com {q}"), _mk),
        Backend("ddg_lite_site_github", "DuckDuckGo Lite site:github.com",
                lambda q: _ddg_lite_url(f"site:github.com {q}"), _hp),
    ],
    "reddit": [
        Backend("redlib_search", "Redlib privacy frontend", _redlib_search_url, _hp),
        Backend("jina_duckduckgo_site_reddit", "Jina Reader over DuckDuckGo site:reddit.com",
                lambda q: _jina_ddg_url(f"site:reddit.com {q}"), _mk),
        Backend("ddg_lite_site_reddit", "DuckDuckGo Lite site:reddit.com",
                lambda q: _ddg_lite_url(f"site:reddit.com {q}"), _hp),
    ],
    "youtube": [
        Backend("jina_duckduckgo_site_youtube", "Jina Reader over DuckDuckGo site:youtube.com",
                lambda q: _jina_ddg_url(f"site:youtube.com/watch OR site:youtu.be {q}"), _mk, accept_url=_youtube_result_url),
        Backend("ddg_lite_site_youtube", "DuckDuckGo Lite site:youtube.com",
                lambda q: _ddg_lite_url(f"site:youtube.com/watch OR site:youtu.be {q}"), _hp, accept_url=_youtube_result_url),
        Backend("youtube_search", "YouTube search results", _youtube_search_url, _hp, accept_url=_youtube_result_url),
    ],
    "x": [
        Backend("nitter_search", "Nitter privacy frontend", _nitter_search_url, _hp),
        Backend("jina_duckduckgo_site_x", "Jina Reader over DuckDuckGo site:x.com",
                lambda q: _jina_ddg_url(f"site:x.com {q}"), _mk),
        Backend("ddg_lite_site_x", "DuckDuckGo Lite site:x.com",
                lambda q: _ddg_lite_url(f"site:x.com {q}"), _hp),
    ],
    "web": [
        Backend("jina_duckduckgo", "Jina Reader over DuckDuckGo", _jina_ddg_url, _mk),
        Backend("ddg_html", "DuckDuckGo HTML", _ddg_html_url, _hp),
        Backend("ddg_lite", "DuckDuckGo Lite", _ddg_lite_url, _hp),
    ],
    "tiktok": [
        Backend("jina_duckduckgo_site_tiktok", "Jina Reader over DDG site:tiktok.com (discovery only)",
                lambda q: _jina_ddg_url(f"site:tiktok.com {q}"), _mk),
        Backend("ddg_lite_site_tiktok", "DuckDuckGo Lite site:tiktok.com (discovery only)",
                lambda q: _ddg_lite_url(f"site:tiktok.com {q}"), _hp),
    ],
    "instagram": [
        Backend("jina_duckduckgo_site_instagram", "Jina Reader over DDG site:instagram.com (discovery only)",
                lambda q: _jina_ddg_url(f"site:instagram.com {q}"), _mk),
        Backend("ddg_lite_site_instagram", "DuckDuckGo Lite site:instagram.com (discovery only)",
                lambda q: _ddg_lite_url(f"site:instagram.com {q}"), _hp),
    ],
}


# ── Chain executor ────────────────────────────────────────────────────────


@dataclass
class BackendResult:
    hits: tuple  # tuple[SearchHit, ...] — lazy type to avoid circular import
    engine: str
    backend_name: str
    attempts: list[str] = field(default_factory=list)
    saw_response: bool = False
    error: str = ""


def execute_backend_chain(
    platform: str,
    query: str,
    *,
    limit: int = 5,
    fetch: FetchFn | None = None,
) -> BackendResult:
    """Try each backend in the platform's chain. First success wins."""
    chain = BACKENDS.get(platform, [])
    if not chain:
        return BackendResult(hits=(), engine="none", backend_name="", attempts=[])

    fetcher = fetch or _fetch
    attempts: list[str] = []
    saw_response = False
    last_error = ""

    for backend in chain:
        attempts.append(backend.name)
        try:
            url = backend.build_url(query)
            page = fetcher(url, backend.timeout)
            saw_response = True
            parse_markdown, parse_html = _get_parsers()
            parser = backend.parser()
            parsed_hits = parser(page, limit * 3 if backend.accept_url else limit)
            hits = tuple(hit for hit in parsed_hits if backend.accept_url is None or backend.accept_url(hit.url))[:limit]
            if hits:
                return BackendResult(
                    hits=hits,
                    engine=backend.name,
                    backend_name=backend.name,
                    attempts=attempts,
                    saw_response=True,
                    error="",
                )
            last_error = f"{backend.name} returned no parseable search results."
        except Exception:
            last_error = f"{backend.name} failed."
            continue

    return BackendResult(hits=(), engine=attempts[-1] if attempts else "none", backend_name=attempts[-1] if attempts else "", attempts=attempts, saw_response=saw_response, error=last_error)
