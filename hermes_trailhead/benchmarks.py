"""Hermes Trailhead benchmark harness.

Defines benchmark task classes that test Trailhead against real research
scenarios.  Scores answer quality, link validity, extraction success,
source diversity, and caveat honesty — not just command exit codes.

Benchmark tasks represent the product promise: ask Hermes something and
Trailhead returns better evidence from better terrain.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Callable

from .search import execute_search, Platform


# ── Benchmark task classes ────────────────────────────────────────────────


@dataclass(frozen=True)
class BenchmarkTask:
    """A single benchmark scenario — one research question with scoring criteria."""
    id: str
    name: str
    description: str
    query: str
    platforms: tuple[str, ...]  # Source families to search
    category: str  # "practitioner", "comparison", "diagnosis", "trend", "docs"
    # Scoring criteria — what the benchmark expects
    min_hits: int = 3          # Minimum expected search hits
    min_platforms_with_hits: int = 2  # At least N platforms should return results
    expected_source_types: tuple[str, ...] = ()  # Expected source families in results
    expected_domains: tuple[str, ...] = ()  # Domains that SHOULD appear (canonical sources)
    reject_source_types: tuple[str, ...] = ()  # Source types that should NOT dominate


# ── Benchmark result types ────────────────────────────────────────────────


@dataclass
class BenchmarkRun:
    task: BenchmarkTask
    total_hits: int = 0
    platforms_with_hits: int = 0
    platforms_checked: list[str] = field(default_factory=list)
    extracted_count: int = 0
    extracted_ok_count: int = 0
    source_types_found: list[str] = field(default_factory=list)
    domains_found: list[str] = field(default_factory=list)
    caveats_triggered: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class BenchmarkScore:
    task_id: str
    task_name: str
    coverage_score: int = 0     # 0-100: did we find results across platforms?
    extraction_score: int = 0   # 0-100: did we successfully extract content?
    source_quality_score: int = 0  # 0-100: did we find the right source types?
    caveat_honesty_score: int = 0  # 0-100: did we report weak lanes honestly?
    total_score: int = 0        # 0-100: weighted aggregate
    verdict: str = ""           # "pass", "fail", "partial"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ── Benchmark task definitions ────────────────────────────────────────────


BENCHMARK_TASKS: tuple[BenchmarkTask, ...] = (
    BenchmarkTask(
        id="practitioner-3d-print",
        name="Practitioner: 3D printing material issue",
        description="User asks why matte PLA prints cleaner than regular PLA. Expect Reddit, forums, manufacturer docs.",
        query="why does matte PLA print more cleanly than cheap regular PLA",
        platforms=("all",),
        category="practitioner",
        min_hits=5,
        min_platforms_with_hits=3,
        expected_source_types=("reddit", "docs", "forum"),
        expected_domains=("reddit.com", "prusa3d.com", "forum"),
        reject_source_types=(),
    ),
    BenchmarkTask(
        id="diagnosis-github-issue",
        name="Diagnosis: GitHub issue discovery",
        description="User hits a bug with Hermes Agent skill loading. Expect GitHub issues, PRs, docs.",
        query="Hermes Agent skill loading error SKILL.md not found",
        platforms=("all",),
        category="diagnosis",
        min_hits=3,
        min_platforms_with_hits=2,
        expected_source_types=("github", "docs", "reddit"),
        expected_domains=("github.com",),
        reject_source_types=(),
    ),
    BenchmarkTask(
        id="comparison-ai-tools",
        name="Comparison: AI agent tools",
        description="User comparing AI coding agents. Expect GitHub, Reddit, X, docs — practitioner signal.",
        query="Hermes Agent vs Claude Code vs Codex comparison 2026",
        platforms=("all",),
        category="comparison",
        min_hits=3,
        min_platforms_with_hits=2,
        expected_source_types=("github", "reddit", "x"),
        expected_domains=(),
        reject_source_types=("seo",),
    ),
    BenchmarkTask(
        id="docs-config-search",
        name="Docs: Configuration search",
        description="User needs to configure Hermes model routing. Expect official docs, GitHub.",
        query="Hermes Agent config.yaml model routing provider setup",
        platforms=("all",),
        category="docs",
        min_hits=2,
        min_platforms_with_hits=1,
        expected_source_types=("docs", "github"),
        expected_domains=("github.com",),
        reject_source_types=("seo",),
    ),
    BenchmarkTask(
        id="trend-scan-ai-agents",
        name="Trend scan: AI agent ecosystem",
        description="What's current in AI agent development. Expect X, Reddit, GitHub — current signal.",
        query="AI agent development latest breakthroughs June 2026",
        platforms=("all",),
        category="trend",
        min_hits=3,
        min_platforms_with_hits=2,
        expected_source_types=("x", "reddit", "github"),
        expected_domains=(),
        reject_source_types=("seo",),
    ),
    BenchmarkTask(
        id="social-video-evidence",
        name="Social: Video/visual evidence search",
        description="Find demos or tutorials for a tool. Expect YouTube, TikTok (discovery), Reddit.",
        query="Hermes Agent setup tutorial demo",
        platforms=("all",),
        category="trend",
        min_hits=2,
        min_platforms_with_hits=1,
        expected_source_types=("youtube", "reddit"),
        expected_domains=("youtube.com",),
        reject_source_types=(),
    ),
)


# ── Scoring functions ─────────────────────────────────────────────────────


def _coverage_score(run: BenchmarkRun, task: BenchmarkTask) -> int:
    """Score hit breadth: did we find results across enough platforms?"""
    if run.total_hits == 0:
        return 0
    hit_score = min(100, int((run.total_hits / max(task.min_hits, 1)) * 50))
    plat_score = min(50, int((run.platforms_with_hits / max(task.min_platforms_with_hits, 1)) * 50))
    return min(100, hit_score + plat_score)


def _extraction_score(run: BenchmarkRun) -> int:
    """Score extraction success: what fraction of attempts succeeded?"""
    if run.extracted_count == 0:
        return 0
    return int((run.extracted_ok_count / run.extracted_count) * 100)


def _source_quality_score(run: BenchmarkRun, task: BenchmarkTask) -> int:
    """Score source type diversity: did we find the expected source families?"""
    if not task.expected_source_types:
        return 50  # No expectations → neutral score
    found_expected = sum(
        1 for st in task.expected_source_types if st in run.source_types_found
    )
    return int((found_expected / len(task.expected_source_types)) * 100)


def _caveat_honesty_score(run: BenchmarkRun) -> int:
    """Score caveat honesty: did we report weak lanes? More caveats = more honest."""
    if run.platforms_checked and run.caveats_triggered > 0:
        return min(100, run.caveats_triggered * 20)
    # No caveats on a search that found everything = suspicious, penalize
    if run.platforms_with_hits >= 6 and run.caveats_triggered == 0:
        return 50  # Probably overclaiming
    return 70  # Neutral — small searches might legitimately have zero caveats


def score_benchmark_run(run: BenchmarkRun, task: BenchmarkTask) -> BenchmarkScore:
    """Score a single benchmark run against its task criteria."""
    coverage = _coverage_score(run, task)
    extraction = _extraction_score(run)
    quality = _source_quality_score(run, task)
    honesty = _caveat_honesty_score(run)

    # Weighted aggregate: coverage 30%, extraction 25%, quality 25%, honesty 20%
    total = int(coverage * 0.30 + extraction * 0.25 + quality * 0.25 + honesty * 0.20)

    if total >= 70:
        verdict = "pass"
    elif total >= 40:
        verdict = "partial"
    else:
        verdict = "fail"

    notes = []
    if run.errors:
        notes.append(f"{len(run.errors)} search errors occurred")
    if run.platforms_with_hits < task.min_platforms_with_hits:
        notes.append(f"Only {run.platforms_with_hits}/{task.min_platforms_with_hits} platforms returned hits")
    if run.total_hits < task.min_hits:
        notes.append(f"Only {run.total_hits}/{task.min_hits} total hits found")

    return BenchmarkScore(
        task_id=task.id,
        task_name=task.name,
        coverage_score=coverage,
        extraction_score=extraction,
        source_quality_score=quality,
        caveat_honesty_score=honesty,
        total_score=total,
        verdict=verdict,
        notes=notes,
    )


# ── Benchmark runner ──────────────────────────────────────────────────────


def run_benchmark(
    task: BenchmarkTask,
    *,
    limit: int = 3,
    extract: bool = True,
    fetch: Callable | None = None,
) -> tuple[BenchmarkRun, BenchmarkScore]:
    """Run a single benchmark task and score the result."""
    run = BenchmarkRun(task=task)

    for platform in task.platforms:
        try:
            executed = execute_search(platform, task.query, limit=limit)  # type: ignore[arg-type]
            for execution in executed.executions:
                run.platforms_checked.append(execution.platform)
                run.total_hits += execution.result_count
                if execution.result_count > 0:
                    run.platforms_with_hits += 1
                # Count caveats
                if execution.caveat:
                    run.caveats_triggered += 1
                if execution.error:
                    run.errors.append(execution.error)
                if execution.evidence_state == "discovered_links_only":
                    run.caveats_triggered += 1

                # Classify source types from hit URLs
                for hit in execution.hits:
                    st = _classify_hit_url(hit.url)
                    if st not in run.source_types_found:
                        run.source_types_found.append(st)
                    domain = _extract_domain(hit.url)
                    if domain and domain not in run.domains_found:
                        run.domains_found.append(domain)

                # Extraction follow-through if requested
                if extract and execution.hits:
                    from .extract import extract_hits
                    extracted = extract_hits(execution.hits, limit=min(2, len(execution.hits)))
                    run.extracted_count += len(extracted)
                    run.extracted_ok_count += sum(1 for eh in extracted if eh.extraction.status == "ok")
                    for eh in extracted:
                        if eh.extraction.status == "blocked":
                            run.caveats_triggered += 1
        except Exception as exc:
            run.errors.append(f"{platform}: {exc}")

    score = score_benchmark_run(run, task)
    return run, score


def _classify_hit_url(url: str) -> str:
    """Quick URL-based source type classification."""
    url_lower = url.lower()
    if "github.com" in url_lower:
        return "github"
    if "x.com" in url_lower or "twitter.com" in url_lower:
        return "x"
    if "reddit.com" in url_lower:
        return "reddit"
    if "tiktok.com" in url_lower:
        return "tiktok"
    if "instagram.com" in url_lower:
        return "instagram"
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    if any(d in url_lower for d in ["docs.", "/docs/", "documentation", "readthedocs", "wiki"]):
        return "docs"
    if "openrouter.ai/blog" in url_lower or "nousresearch.com" in url_lower:
        return "docs"
    if any(f in url_lower for f in ["forum.", "community.", "discourse", "stackoverflow", "stackexchange"]):
        return "forum"
    if any(s in url_lower for s in ["medium.com", "towardsdatascience", "dev.to", "blogspot"]):
        return "seo"
    return "web"


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def run_all_benchmarks(
    *,
    tasks: tuple[BenchmarkTask, ...] | None = None,
    limit: int = 3,
) -> dict:
    """Run all benchmark tasks and return aggregate results."""
    tasks = tasks or BENCHMARK_TASKS
    results = []
    for task in tasks:
        run, score = run_benchmark(task, limit=limit)
        results.append({
            "task": task.name,
            "run": asdict(run),
            "score": score.to_dict(),
        })

    scores = [r["score"]["total_score"] for r in results]
    avg_score = int(sum(scores) / len(scores)) if scores else 0
    passes = sum(1 for r in results if r["score"]["verdict"] == "pass")
    partials = sum(1 for r in results if r["score"]["verdict"] == "partial")
    fails = sum(1 for r in results if r["score"]["verdict"] == "fail")

    return {
        "benchmark_version": "0.1.0",
        "task_count": len(tasks),
        "results": results,
        "aggregate": {
            "average_score": avg_score,
            "passes": passes,
            "partials": partials,
            "fails": fails,
        },
    }
