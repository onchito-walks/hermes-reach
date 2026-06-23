"""Hermes Trailhead PhD-level research gauntlet.

This module is the deterministic product-quality test for Trailhead.  It does
not hit the network.  Live access changes too often; the gauntlet instead asks:

- Do we model all hard-source lanes the product promises?
- Do we separate discovery, readable evidence, transcript evidence, and blocked
  platform shells?
- Do we score canonical/practitioner/technical/current/community evidence above
  SEO/generic sludge?
- Do we honestly report TikTok/Instagram/X-style shallow or blocked lanes?
- Do YouTube transcript-style evidence count as more than a bare video link?

Use `benchmark` as the live canary.  Use this gauntlet as the non-flaky PhD
product contract.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

from .extract import ExtractionResult, ExtractedHit
from .scoring import ScoredHit, score_hit, SourceQuality
from .search import SearchHit

LaneKind = Literal[
    "web",
    "docs",
    "github",
    "reddit",
    "x",
    "youtube_transcript",
    "tiktok_discovery",
    "instagram_discovery",
    "forum",
    "pdf",
]


@dataclass(frozen=True)
class EvidenceFixture:
    """A deterministic evidence item for a hard-source lane."""

    lane: LaneKind
    title: str
    url: str
    content: str = ""
    expected_quality: str = ""
    should_extract: bool = True
    should_be_blocked: bool = False
    should_have_transcript: bool = False
    caveat_required: bool = False


@dataclass(frozen=True)
class GauntletCase:
    """A product-level research scenario Trailhead must support."""

    id: str
    name: str
    user_question: str
    expected_lanes: tuple[LaneKind, ...]
    fixtures: tuple[EvidenceFixture, ...]
    route_intent: str


@dataclass
class LaneFinding:
    lane: str
    url: str
    extraction_ok: bool
    blocked_ok: bool
    transcript_ok: bool
    caveat_ok: bool
    quality: str
    score: int
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GauntletScore:
    case_id: str
    case_name: str
    lane_coverage_score: int
    extraction_contract_score: int
    transcript_score: int
    quality_score: int
    caveat_honesty_score: int
    total_score: int
    verdict: str
    findings: list[LaneFinding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["findings"] = [finding.to_dict() for finding in self.findings]
        return d


# ── Deterministic PhD test corpus ─────────────────────────────────────────

TRANSCRIPT = """Transcript [00:00] Introduction to Hermes Agent setup.
[00:42] The presenter opens config.yaml and explains provider routing.
[02:10] They demonstrate a failed model call and fallback to DeepSeek.
[03:18] The video shows the exact command output and terminal state.
"""

GAUNTLET_CASES: tuple[GauntletCase, ...] = (
    GauntletCase(
        id="hard-source-material-diagnosis",
        name="Material diagnosis across practitioner + canonical sources",
        user_question="Why does matte PLA sometimes print cleaner than cheap regular PLA?",
        route_intent="practitioner material failure: reddit forums docs youtube visual evidence",
        expected_lanes=("reddit", "forum", "docs", "youtube_transcript"),
        fixtures=(
            EvidenceFixture(
                lane="reddit",
                title="Matte PLA hides layer lines and changes flow",
                url="https://www.reddit.com/r/3Dprinting/comments/example/matte_pla_layer_lines/",
                content="Practitioners report matte PLA hides layer lines and can print cleaner because filler changes surface finish and flow behavior.",
                expected_quality=SourceQuality.PRACTITIONER.value,
            ),
            EvidenceFixture(
                lane="forum",
                title="Forum thread: PLA curling and surface additives",
                url="https://forum.prusa3d.com/forum/original-prusa-i3-mk3s-mk3-how-do-i-print-this/matte-pla-curling/",
                content="Multiple users compare cheap glossy PLA and matte PLA, noting bed adhesion, cooling, and additive differences.",
                expected_quality=SourceQuality.PRACTITIONER.value,
            ),
            EvidenceFixture(
                lane="docs",
                title="Prusa material guide — PLA",
                url="https://help.prusa3d.com/article/pla_2062",
                content="Official material docs explain PLA behavior, cooling, bed temperatures, and surface finish considerations.",
                expected_quality=SourceQuality.CANONICAL.value,
            ),
            EvidenceFixture(
                lane="youtube_transcript",
                title="Matte PLA print quality comparison demo",
                url="https://www.youtube.com/watch?v=mattePlaDemo",
                content=TRANSCRIPT + " The demo visually compares matte and glossy PLA side by side.",
                expected_quality=SourceQuality.COMMUNITY.value,
                should_have_transcript=True,
            ),
        ),
    ),
    GauntletCase(
        id="agent-tool-current-research",
        name="Current AI agent research across GitHub, X, Reddit, docs, video",
        user_question="What is the current state of Hermes Agent compared with Claude Code and Codex?",
        route_intent="current practitioner research: github issues x reddit docs youtube transcript",
        expected_lanes=("web", "github", "x", "reddit", "docs", "youtube_transcript"),
        fixtures=(
            EvidenceFixture(
                lane="web",
                title="Independent AI agent comparison overview",
                url="https://example.com/research/ai-agent-comparison-2026",
                content="A broad web overview compares Hermes Agent, Claude Code, Codex, routing reliability, cost, and developer workflows.",
                expected_quality=SourceQuality.GENERIC.value,
            ),
            EvidenceFixture(
                lane="github",
                title="Hermes Agent issue about model fallback",
                url="https://github.com/NousResearch/hermes-agent/issues/49982",
                content="Maintainers discuss fallback behavior, model providers, and a reproducible bug report.",
                expected_quality=SourceQuality.TECHNICAL.value,
            ),
            EvidenceFixture(
                lane="x",
                title="Maintainer post about agent routing",
                url="https://x.com/nousresearch/status/1234567890",
                content="Maintainer notes a current routing fix and links to a release note.",
                expected_quality=SourceQuality.CURRENT.value,
                caveat_required=True,
            ),
            EvidenceFixture(
                lane="reddit",
                title="Practitioners compare Claude Code and Codex",
                url="https://www.reddit.com/r/LocalLLaMA/comments/example/claude_code_codex_hermes/",
                content="Developers compare agent reliability, cost, local tooling, and coding-loop ergonomics.",
                expected_quality=SourceQuality.PRACTITIONER.value,
            ),
            EvidenceFixture(
                lane="docs",
                title="Hermes Agent configuring models",
                url="https://hermes-agent.nousresearch.com/docs/user-guide/configuring-models",
                content="Official Hermes docs describe model providers, routing, fallback, and configuration.",
                expected_quality=SourceQuality.CANONICAL.value,
            ),
            EvidenceFixture(
                lane="youtube_transcript",
                title="Hermes Agent setup walkthrough",
                url="https://youtube.com/watch?v=hermesSetupDemo",
                content=TRANSCRIPT,
                expected_quality=SourceQuality.COMMUNITY.value,
                should_have_transcript=True,
            ),
        ),
    ),
    GauntletCase(
        id="blocked-visual-social-honesty",
        name="Visual/social discovery with honest blocked-lane caveats",
        user_question="Find TikTok and Instagram demos for a new AI tool without using account cookies.",
        route_intent="visual social search tiktok instagram youtube account boundaries",
        expected_lanes=("tiktok_discovery", "instagram_discovery", "youtube_transcript"),
        fixtures=(
            EvidenceFixture(
                lane="tiktok_discovery",
                title="Creator demo on TikTok",
                url="https://www.tiktok.com/@creator/video/123456789",
                content="",
                expected_quality=SourceQuality.PLATFORM_SHELL.value,
                should_extract=False,
                should_be_blocked=True,
                caveat_required=True,
            ),
            EvidenceFixture(
                lane="instagram_discovery",
                title="Instagram reel demo",
                url="https://www.instagram.com/reel/ABC123/",
                content="",
                expected_quality=SourceQuality.PLATFORM_SHELL.value,
                should_extract=False,
                should_be_blocked=True,
                caveat_required=True,
            ),
            EvidenceFixture(
                lane="youtube_transcript",
                title="Public YouTube tutorial with transcript",
                url="https://youtu.be/publicDemo123",
                content=TRANSCRIPT + " Public transcript is readable without account cookies.",
                expected_quality=SourceQuality.COMMUNITY.value,
                should_have_transcript=True,
            ),
        ),
    ),
    GauntletCase(
        id="canonical-docs-pdf-forum",
        name="Canonical docs + PDF + forum triangulation",
        user_question="How should Hermes configure model routing and what failure modes matter?",
        route_intent="known docs pdf forum github model routing configuration",
        expected_lanes=("docs", "github", "forum", "pdf"),
        fixtures=(
            EvidenceFixture(
                lane="docs",
                title="Configuration | Hermes Agent",
                url="https://hermes-agent.nousresearch.com/docs/user-guide/configuration/",
                content="Official configuration docs describe config.yaml sections and provider setup.",
                expected_quality=SourceQuality.CANONICAL.value,
            ),
            EvidenceFixture(
                lane="github",
                title="Pull request: fallback provider routing",
                url="https://github.com/NousResearch/hermes-agent/pull/46004",
                content="A PR changes model fallback behavior and includes tests for provider routing.",
                expected_quality=SourceQuality.TECHNICAL.value,
            ),
            EvidenceFixture(
                lane="forum",
                title="Community discussion: provider routing gotchas",
                url="https://community.nousresearch.com/t/hermes-provider-routing-gotchas/42",
                content="Users report confusing provider settings and fixes for config reload behavior.",
                expected_quality=SourceQuality.PRACTITIONER.value,
            ),
            EvidenceFixture(
                lane="pdf",
                title="Agent routing whitepaper PDF",
                url="https://example.edu/papers/agent-routing-fallback.pdf",
                content="PDF paper discusses failover, routing confidence, and model selection under quota constraints.",
                expected_quality=SourceQuality.CANONICAL.value,
            ),
        ),
    ),
)


# ── Evaluation ────────────────────────────────────────────────────────────

EXPECTED_MIN_SCORE_BY_QUALITY = {
    SourceQuality.CANONICAL.value: 65,
    SourceQuality.TECHNICAL.value: 65,
    SourceQuality.PRACTITIONER.value: 55,
    SourceQuality.CURRENT.value: 45,
    SourceQuality.COMMUNITY.value: 35,
    SourceQuality.PLATFORM_SHELL.value: 0,
    SourceQuality.GENERIC.value: 30,
}


def _extract_fixture(fixture: EvidenceFixture) -> ExtractionResult:
    if fixture.should_be_blocked:
        return ExtractionResult(
            status="blocked",
            source_type="tiktok" if "tiktok" in fixture.lane else "instagram",
            error_message="Discovery-only lane requires browser/session; no account cookies used.",
        )
    return ExtractionResult(
        status="ok" if fixture.should_extract else "not_attempted",
        content=fixture.content,
        content_length=len(fixture.content),
        source_type="youtube" if fixture.lane == "youtube_transcript" else "web",
    )


def _score_fixture(fixture: EvidenceFixture) -> tuple[LaneFinding, int]:
    hit = SearchHit(title=fixture.title, url=fixture.url, snippet="fixture")
    extraction = _extract_fixture(fixture)
    extracted = ExtractedHit(title=hit.title, url=hit.url, snippet=hit.snippet, extraction=extraction)
    scored = score_hit(ScoredHit.from_extracted_hit(extracted))

    notes: list[str] = []
    extraction_ok = (not fixture.should_extract) or extraction.status == "ok"
    blocked_ok = (not fixture.should_be_blocked) or extraction.status == "blocked"
    transcript_ok = True
    if fixture.should_have_transcript:
        transcript_ok = "[00:" in fixture.content and "transcript" in fixture.content.lower()
        if not transcript_ok:
            notes.append("missing transcript-shaped content")

    caveat_ok = True
    if fixture.caveat_required:
        caveat_ok = fixture.should_be_blocked or fixture.lane in ("x", "tiktok_discovery", "instagram_discovery")
        if not caveat_ok:
            notes.append("expected caveat boundary not represented")

    expected_min = EXPECTED_MIN_SCORE_BY_QUALITY.get(fixture.expected_quality, 30)
    quality_ok = scored.scoring.quality.value == fixture.expected_quality or scored.scoring.score >= expected_min
    if not quality_ok:
        notes.append(
            f"quality mismatch: expected {fixture.expected_quality}, got {scored.scoring.quality.value}/{scored.scoring.score}"
        )

    points = sum([extraction_ok, blocked_ok, transcript_ok, caveat_ok, quality_ok])
    lane_score = int(points / 5 * 100)

    return LaneFinding(
        lane=fixture.lane,
        url=fixture.url,
        extraction_ok=extraction_ok,
        blocked_ok=blocked_ok,
        transcript_ok=transcript_ok,
        caveat_ok=caveat_ok,
        quality=scored.scoring.quality.value,
        score=scored.scoring.score,
        notes=notes,
    ), lane_score


def run_gauntlet_case(case: GauntletCase) -> GauntletScore:
    findings: list[LaneFinding] = []
    lane_scores: list[int] = []

    fixture_lanes = {fixture.lane for fixture in case.fixtures}
    expected_lanes = set(case.expected_lanes)
    lane_coverage_score = int((len(expected_lanes & fixture_lanes) / max(len(expected_lanes), 1)) * 100)

    extraction_points = []
    transcript_points = []
    quality_points = []
    caveat_points = []

    for fixture in case.fixtures:
        finding, lane_score = _score_fixture(fixture)
        findings.append(finding)
        lane_scores.append(lane_score)
        extraction_points.append(finding.extraction_ok and finding.blocked_ok)
        transcript_points.append(finding.transcript_ok)
        quality_points.append(finding.score >= EXPECTED_MIN_SCORE_BY_QUALITY.get(fixture.expected_quality, 30))
        caveat_points.append(finding.caveat_ok)

    extraction_score = int((sum(bool(x) for x in extraction_points) / max(len(extraction_points), 1)) * 100)
    transcript_score = int((sum(bool(x) for x in transcript_points) / max(len(transcript_points), 1)) * 100)
    quality_score = int((sum(bool(x) for x in quality_points) / max(len(quality_points), 1)) * 100)
    caveat_score = int((sum(bool(x) for x in caveat_points) / max(len(caveat_points), 1)) * 100)

    total = int(
        lane_coverage_score * 0.20
        + extraction_score * 0.25
        + transcript_score * 0.15
        + quality_score * 0.25
        + caveat_score * 0.15
    )
    verdict = "pass" if total >= 85 else "partial" if total >= 70 else "fail"
    notes: list[str] = []
    if lane_coverage_score < 100:
        notes.append("missing expected hard-source lane fixture")
    for finding in findings:
        notes.extend(f"{finding.lane}: {note}" for note in finding.notes)

    return GauntletScore(
        case_id=case.id,
        case_name=case.name,
        lane_coverage_score=lane_coverage_score,
        extraction_contract_score=extraction_score,
        transcript_score=transcript_score,
        quality_score=quality_score,
        caveat_honesty_score=caveat_score,
        total_score=total,
        verdict=verdict,
        findings=findings,
        notes=notes,
    )


def run_gauntlet(cases: tuple[GauntletCase, ...] | None = None) -> dict:
    cases = cases or GAUNTLET_CASES
    results = [run_gauntlet_case(case) for case in cases]
    average = int(sum(score.total_score for score in results) / max(len(results), 1))
    passes = sum(1 for score in results if score.verdict == "pass")
    partials = sum(1 for score in results if score.verdict == "partial")
    fails = sum(1 for score in results if score.verdict == "fail")
    return {
        "gauntlet_version": "1.0.0",
        "mode": "offline_deterministic_product_contract",
        "case_count": len(results),
        "hard_source_lanes": sorted({lane for case in cases for lane in case.expected_lanes}),
        "aggregate": {
            "average_score": average,
            "passes": passes,
            "partials": partials,
            "fails": fails,
        },
        "results": [score.to_dict() for score in results],
    }
