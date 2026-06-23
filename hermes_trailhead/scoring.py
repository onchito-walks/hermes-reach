"""Hermes Trailhead source-quality scoring — rank search hits by likely usefulness.

After ``search --execute`` returns hits, this module classifies each hit by source
quality and assigns a score.  Higher scores go to maintainer/official/canonical
sources, practitioner firsthand reports, current discussion, and GitHub issues/PRs.
Lower scores go to SEO farms, listicles, empty platform shells, and dead links.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import re
from urllib.parse import urlparse

from .extract import ExtractedHit


class SourceQuality(str, Enum):
    CANONICAL = "canonical"       # Official docs, repos, maintainer statements
    PRACTITIONER = "practitioner" # Reddit threads, forums, firsthand reports
    CURRENT = "current"           # Recent maintainer posts, X/Twitter, active issues
    TECHNICAL = "technical"       # GitHub issues/PRs, changelogs, release notes
    COMMUNITY = "community"       # YouTube, TikTok demos, visual evidence
    GENERIC = "generic"           # Blog, article, general web page
    SEO = "seo"                   # SEO farm, listicle, content mill
    PLATFORM_SHELL = "platform_shell"  # TikTok/Instagram link with no readable content
    DEAD = "dead"                 # Unreachable, blocked, empty
    UNKNOWN = "unknown"


# Domain/pattern scoring rules: (regex, quality, base_score, label)
DOMAIN_RULES: list[tuple[str, SourceQuality, int, str]] = [
    # Canonical — official docs, repos
    (r"github\.com/[^/]+/[^/]+/(issues|pull)/\d+", SourceQuality.TECHNICAL, 85, "GitHub issue/PR"),
    (r"github\.com/[^/]+/[^/]+/releases/tag/", SourceQuality.TECHNICAL, 80, "GitHub release"),
    (r"github\.com/[^/]+/[^/]+/commit/", SourceQuality.TECHNICAL, 75, "GitHub commit"),
    (r"github\.com/[^/]+/[^/]+$", SourceQuality.CANONICAL, 70, "GitHub repo root"),
    (r"github\.com/[^/]+/[^/]+/", SourceQuality.CANONICAL, 68, "GitHub repo page"),
    (r"docs\.", SourceQuality.CANONICAL, 75, "Documentation site"),
    (r"readthedocs\.io", SourceQuality.CANONICAL, 75, "ReadTheDocs"),
    (r"help\.[^/]+/", SourceQuality.CANONICAL, 72, "Official help docs"),
    (r"arxiv\.org", SourceQuality.CANONICAL, 80, "arXiv paper"),
    (r"doi\.org", SourceQuality.CANONICAL, 80, "DOI reference"),
    (r"\.pdf($|[?#])", SourceQuality.CANONICAL, 70, "PDF/whitepaper"),
    (r"/docs/", SourceQuality.CANONICAL, 72, "Documentation path"),
    (r"documentation", SourceQuality.CANONICAL, 70, "Documentation"),

    # Practitioner — firsthand experience
    (r"reddit\.com/r/", SourceQuality.PRACTITIONER, 65, "Reddit community"),
    (r"stackoverflow\.com/questions/", SourceQuality.PRACTITIONER, 68, "StackOverflow question"),
    (r"stackexchange\.com/questions/", SourceQuality.PRACTITIONER, 65, "StackExchange question"),
    (r"discourse\.", SourceQuality.PRACTITIONER, 60, "Discourse forum"),
    (r"forum\.", SourceQuality.PRACTITIONER, 58, "Forum"),
    (r"openrouter\.ai/blog", SourceQuality.PRACTITIONER, 55, "OpenRouter blog"),
    (r"nousresearch\.com", SourceQuality.CANONICAL, 75, "Nous Research"),
    (r"hermes-agent\.nousresearch\.com", SourceQuality.CANONICAL, 78, "Hermes Agent docs"),

    # Current — X/Twitter, maintainer activity
    (r"x\.com/[^/]+/status/", SourceQuality.CURRENT, 55, "X/Twitter post"),
    (r"twitter\.com/[^/]+/status/", SourceQuality.CURRENT, 55, "Twitter post"),
    (r"x\.com/i/communities/", SourceQuality.CURRENT, 50, "X community"),

    # Community — video demos, visual evidence
    (r"youtube\.com/watch", SourceQuality.COMMUNITY, 45, "YouTube video"),
    (r"youtu\.be/", SourceQuality.COMMUNITY, 45, "YouTube short link"),
    (r"tiktok\.com/@", SourceQuality.COMMUNITY, 30, "TikTok video (discovery only)"),
    (r"instagram\.com/(p|reel)/", SourceQuality.COMMUNITY, 25, "Instagram post (discovery only)"),

    # SEO / content-mill signals
    (r"medium\.com/", SourceQuality.SEO, 20, "Medium (often SEO)"),
    (r"towardsdatascience\.com", SourceQuality.SEO, 15, "TDS (SEO risk)"),
    (r"dev\.to/", SourceQuality.SEO, 25, "dev.to (mixed quality)"),
    (r"\.blogspot\.", SourceQuality.SEO, 10, "Blogspot"),
    (r"hubspot\.com", SourceQuality.SEO, 10, "HubSpot content"),
]

# URL keywords that signal high quality regardless of domain
HIGH_SIGNAL_KEYWORDS = [
    "changelog", "release", "migration", "breaking", "deprecated",
    "security", "advisory", "cve", "vulnerability", "fix", "patch",
    "benchmark", "comparison", "vs", "alternative",
]

# URL keywords that signal low quality
LOW_SIGNAL_KEYWORDS = [
    "top-10", "best-of", "ultimate-guide", "definitive-guide",
    "you-wont-believe", "shocking", "viral",
]


@dataclass(frozen=True)
class SourceScore:
    quality: SourceQuality
    score: int  # 0-100
    reasons: tuple[str, ...]
    label: str = ""

    def to_dict(self) -> dict:
        return {
            "quality": self.quality.value,
            "score": self.score,
            "reasons": list(self.reasons),
            "label": self.label,
        }


@dataclass(frozen=True)
class ScoredHit:
    title: str
    url: str
    snippet: str = ""
    extraction_status: str = ""
    extraction_length: int = 0
    scoring: SourceScore = field(default_factory=lambda: SourceScore(
        quality=SourceQuality.UNKNOWN, score=0, reasons=tuple(), label=""
    ))

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "extraction_status": self.extraction_status,
            "extraction_length": self.extraction_length,
            "scoring": self.scoring.to_dict(),
        }

    @classmethod
    def from_extracted_hit(cls, eh: ExtractedHit) -> ScoredHit:
        return cls(
            title=eh.title,
            url=eh.url,
            snippet=eh.snippet,
            extraction_status=eh.extraction.status,
            extraction_length=eh.extraction.content_length,
        )


def _parse_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def score_hit(hit: ScoredHit) -> ScoredHit:
    """Score a single hit based on URL patterns and extraction state."""
    reasons: list[str] = []
    url_lower = hit.url.lower()

    # Check extraction state first
    if hit.extraction_status == "blocked":
        return ScoredHit(
            title=hit.title,
            url=hit.url,
            snippet=hit.snippet,
            extraction_status=hit.extraction_status,
            extraction_length=hit.extraction_length,
            scoring=SourceScore(
                quality=SourceQuality.PLATFORM_SHELL,
                score=0,
                reasons=("Content blocked — requires browser or account session",),
                label="Platform shell (discovery only)",
            ),
        )

    if hit.extraction_status == "error" and hit.extraction_length < 50:
        return ScoredHit(
            title=hit.title,
            url=hit.url,
            snippet=hit.snippet,
            extraction_status=hit.extraction_status,
            extraction_length=hit.extraction_length,
            scoring=SourceScore(
                quality=SourceQuality.DEAD,
                score=0,
                reasons=("Content unreachable or empty",),
                label="Dead link",
            ),
        )

    # Apply domain rules
    matched = False
    for pattern, quality, base_score, label in DOMAIN_RULES:
        if re.search(pattern, url_lower):
            reasons.append(label)
            score = base_score
            matched = True
            break
    else:
        quality = SourceQuality.GENERIC
        score = 35
        reasons.append("Generic web page")

    # Boost for high-signal keywords in URL
    keyword_boost = 0
    for kw in HIGH_SIGNAL_KEYWORDS:
        if kw in url_lower:
            keyword_boost += 3
            reasons.append(f"High-signal keyword: {kw}")

    # Penalize low-signal keywords
    for kw in LOW_SIGNAL_KEYWORDS:
        if kw in url_lower:
            score -= 10
            reasons.append(f"Low-signal keyword: {kw}")

    # Extraction bonus: successfully extracted pages get a modest boost
    if hit.extraction_status == "ok" and hit.extraction_length > 500:
        score += 5
        reasons.append("Successfully extracted (long content)")

    score = max(0, min(100, score + keyword_boost))

    quality_label = reasons[0] if reasons else "Unknown"

    return ScoredHit(
        title=hit.title,
        url=hit.url,
        snippet=hit.snippet,
        extraction_status=hit.extraction_status,
        extraction_length=hit.extraction_length,
        scoring=SourceScore(
            quality=quality,
            score=score,
            reasons=tuple(reasons),
            label=quality_label,
        ),
    )


def score_hits(hits: list[ScoredHit]) -> list[ScoredHit]:
    """Score a list of hits."""
    return [score_hit(hit) for hit in hits]


def rank_hits(scored: list[ScoredHit]) -> list[ScoredHit]:
    """Sort scored hits by score descending."""
    return sorted(scored, key=lambda h: h.scoring.score, reverse=True)
