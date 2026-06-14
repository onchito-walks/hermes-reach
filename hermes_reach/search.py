"""Hermes-usable search routing for hard-to-reach internet sources.

The CLI cannot call Hermes tools directly when it runs as a subprocess, so this module
emits structured, machine-readable search actions that Hermes can execute with its own
`web_search`, `web_extract`, `x_search`, GitHub MCP, browser, or media tools.

Default paths avoid paid API dependencies. Paid/API-backed tools may appear only as
optional accelerators or when already configured by the user's Hermes environment.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal
from urllib.parse import quote_plus

from .channels import CheckResult, check_reddit, check_x_search

Platform = Literal["all", "web", "x", "reddit", "tiktok", "instagram", "youtube", "github"]
SearchStatus = Literal["ready", "planned", "gap", "approval_required"]


@dataclass(frozen=True)
class SearchAction:
    platform: str
    status: SearchStatus
    query: str
    recommended_tool: str
    direct_url: str = ""
    site_query: str = ""
    frontend_url: str = ""
    approval_required: bool = False
    paid_api_required: bool = False
    evidence_needed: tuple[str, ...] = ()
    caveat: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["evidence_needed"] = list(self.evidence_needed)
        return data


@dataclass(frozen=True)
class SearchRun:
    query: str
    platform: str
    mode: str
    paid_api_required: bool
    actions: tuple[SearchAction, ...]

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "platform": self.platform,
            "mode": self.mode,
            "paid_api_required": self.paid_api_required,
            "actions": [action.to_dict() for action in self.actions],
        }


PLATFORMS: tuple[str, ...] = ("web", "x", "reddit", "tiktok", "instagram", "youtube", "github")


def _site_query(site: str, query: str) -> str:
    return f"site:{site} {query}"


def _search_url(engine: str, query: str) -> str:
    if engine == "redlib":
        return f"https://redlib.perennialte.ch/search?q={quote_plus(query)}"
    if engine == "nitter":
        return f"http://localhost:8788/search?f=tweets&q={quote_plus(query)}"
    if engine == "github":
        return f"https://github.com/search?q={quote_plus(query)}"
    if engine == "youtube":
        return f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    return ""


def action_for(platform: str, query: str, *, live: bool = False) -> SearchAction:
    if platform == "web":
        return SearchAction(
            platform="web",
            status="ready",
            query=query,
            recommended_tool="web_search",
            site_query=query,
            paid_api_required=False,
            evidence_needed=("query", "result_count", "extracted_source_count", "source URLs"),
            caveat="Use web_extract on promising URLs; search results are leads, not evidence.",
        )

    if platform == "x":
        status: SearchStatus = "planned"
        caveat = "Use x_search if Hermes has it configured; otherwise use Nitter or site:x.com search. Do not use cookie auth without approval."
        if live:
            res = check_x_search(live=True)
            if res.status == "ok":
                status = "ready"
                caveat = res.detail
            else:
                status = "gap"
                caveat = res.detail
        return SearchAction(
            platform="x",
            status=status,
            query=query,
            recommended_tool="x_search or web_search",
            direct_url=_search_url("nitter", query),
            site_query=_site_query("x.com", query),
            frontend_url="http://localhost:8788",
            approval_required=True,
            paid_api_required=False,
            evidence_needed=("query", "handles checked", "post count", "working links", "coverage caveat"),
            caveat=caveat,
        )

    if platform == "reddit":
        status = "ready"
        caveat = "Prefer Redlib/reddit-search first; browser/cookie auth requires approval."
        if live:
            res = check_reddit(live=True)
            if res.status != "ok":
                status = "gap"
                caveat = res.detail
            else:
                caveat = res.detail
        return SearchAction(
            platform="reddit",
            status=status,
            query=query,
            recommended_tool="web_search or reddit-search",
            direct_url=_search_url("redlib", query),
            site_query=_site_query("reddit.com", query),
            frontend_url="https://redlib.perennialte.ch",
            paid_api_required=False,
            evidence_needed=("query/subreddits", "post count", "comment/thread links", "working Redlib or Reddit links"),
            caveat=caveat,
        )

    if platform == "tiktok":
        return SearchAction(
            platform="tiktok",
            status="gap",
            query=query,
            recommended_tool="web_search then supervised browser/media tool if needed",
            site_query=_site_query("tiktok.com", query),
            approval_required=True,
            paid_api_required=False,
            evidence_needed=("site query", "video/profile URLs", "retrieved count", "reader/browser caveat"),
            caveat="No dedicated TikTok reader is configured by default. Use site:tiktok.com search first; account/session browser work needs approval.",
        )

    if platform == "instagram":
        return SearchAction(
            platform="instagram",
            status="gap",
            query=query,
            recommended_tool="web_search then supervised browser if needed",
            site_query=_site_query("instagram.com", query),
            approval_required=True,
            paid_api_required=False,
            evidence_needed=("site query", "profile/post URLs", "retrieved count", "reader/browser caveat"),
            caveat="No dedicated Instagram reader is configured by default. Use site:instagram.com search first; account/session browser work needs approval.",
        )

    if platform == "youtube":
        return SearchAction(
            platform="youtube",
            status="planned",
            query=query,
            recommended_tool="web_search, media tools, or yt-dlp if installed",
            direct_url=_search_url("youtube", query),
            site_query=_site_query("youtube.com", query),
            paid_api_required=False,
            evidence_needed=("video URLs", "metadata/transcript availability", "retrieved count"),
            caveat="Use media/transcript tools when available; install yt-dlp only in a project venv when needed.",
        )

    if platform == "github":
        return SearchAction(
            platform="github",
            status="ready",
            query=query,
            recommended_tool="GitHub MCP, gh CLI, or web_search site:github.com",
            direct_url=_search_url("github", query),
            site_query=_site_query("github.com", query),
            paid_api_required=False,
            evidence_needed=("repo/issue/PR URLs", "auth boundary", "retrieved count"),
            caveat="Use GitHub MCP first when available; gh CLI for terminal/git workflows.",
        )

    raise ValueError(f"Unknown platform: {platform}")


def search_run(platform: Platform, query: str, *, live: bool = False) -> SearchRun:
    if platform == "all":
        actions = tuple(action_for(p, query, live=live) for p in PLATFORMS)
    else:
        actions = (action_for(platform, query, live=live),)
    return SearchRun(
        query=query,
        platform=platform,
        mode="hermes_action_plan",
        paid_api_required=any(action.paid_api_required for action in actions),
        actions=actions,
    )
