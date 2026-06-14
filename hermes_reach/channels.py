from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import subprocess
from typing import Callable


ROOT = Path.home()
HERMES_HOME = ROOT / ".hermes"
HERMES_AGENT_REPO = HERMES_HOME / "hermes-agent"
CONFIG = HERMES_HOME / "config.yaml"
CRON = HERMES_HOME / "cron" / "jobs.json"
NEWSLETTER = HERMES_HOME / "scripts" / "hermes-morning-brief-v3.py"
WATCHER = HERMES_HOME / "scripts" / "hermes-upstream-opportunity-watch.py"
VALIDATOR = HERMES_HOME / "scripts" / "validate-hermes-newsletter.py"


@dataclass(frozen=True)
class CheckResult:
    status: str  # ok | warn | off
    detail: str
    action: str = ""


@dataclass(frozen=True)
class Channel:
    key: str
    title: str
    purpose: str
    default_path: str
    risk: str
    check: Callable[[], CheckResult]
    setup_plan: tuple[str, ...]


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 15) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as e:
        return 127, str(e)
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def _file(path: Path) -> bool:
    return path.exists() and path.is_file()


def _cmd(name: str) -> bool:
    return shutil.which(name) is not None


def _contains(path: Path, needle: str) -> bool:
    try:
        return needle in path.read_text(errors="replace")
    except Exception:
        return False


def check_web_search() -> CheckResult:
    if CONFIG.exists():
        return CheckResult("ok", "Hermes config present; use native web_search tool when available.")
    return CheckResult("warn", "Hermes config missing; web_search availability depends on active toolset.")


def check_web_extract() -> CheckResult:
    return CheckResult("ok", "Use native web_extract; fallback recipe is Jina Reader: https://r.jina.ai/http://example.com")


def check_github() -> CheckResult:
    if _cmd("gh"):
        rc, out = _run(["gh", "auth", "status"], timeout=10)
        if rc == 0:
            return CheckResult("ok", "gh authenticated; GitHub MCP also configured in Hermes gateway on this host.")
        return CheckResult("warn", "gh installed but auth status is not clean.", "Run `gh auth status`; authenticate only if needed.")
    return CheckResult("warn", "gh CLI not installed or not on PATH.", "Use GitHub MCP first; install gh only if terminal workflow needs it.")


def check_x_search() -> CheckResult:
    if os.environ.get("XAI_API_KEY"):
        return CheckResult("ok", "XAI_API_KEY present; prefer Hermes x_search for current X discussion.")
    nitter_hint = "local Nitter expected at localhost:8788 per Hermes memory; use fallback extraction if reachable."
    return CheckResult("warn", "No XAI_API_KEY in environment; x_search may be unavailable or credit-limited. " + nitter_hint, "Do not scrape cookies automatically; ask before configuring X auth.")


def check_reddit() -> CheckResult:
    redlib = "https://redlib.perennialte.ch"
    return CheckResult("ok", f"Prefer Redlib/privacy frontend or existing reddit-search tooling. Known Redlib: {redlib}")


def check_youtube() -> CheckResult:
    if _cmd("yt-dlp"):
        return CheckResult("ok", "yt-dlp installed; use for transcripts/metadata when native media tools are not enough.")
    return CheckResult("off", "yt-dlp not installed globally.", "Install in a project venv only when a YouTube task needs it.")


def check_hermes_upstream() -> CheckResult:
    if not HERMES_AGENT_REPO.exists():
        return CheckResult("off", f"Hermes repo missing at {HERMES_AGENT_REPO}")
    rc, out = _run(["git", "rev-list", "--left-right", "--count", "HEAD...origin/main"], cwd=HERMES_AGENT_REPO)
    if rc != 0:
        return CheckResult("warn", "Could not compare Hermes repo to origin/main.", "Run git fetch in the Hermes repo.")
    ahead, behind = out.split()[:2]
    if behind == "0":
        return CheckResult("ok", f"Hermes repo current with origin/main (ahead {ahead}, behind {behind}).")
    return CheckResult("warn", f"Hermes repo is {behind} commits behind origin/main.", "Run `hermes update` after checking local changes.")


def check_newsletter() -> CheckResult:
    missing = [str(p) for p in (NEWSLETTER, VALIDATOR) if not p.exists()]
    if missing:
        return CheckResult("warn", "Newsletter gate files missing: " + ", ".join(missing))
    if _contains(NEWSLETTER, "HERMES CAPABILITY RADAR") and _contains(NEWSLETTER, "VALIDATOR"):
        return CheckResult("ok", "Daily briefing has acceptance gate and Hermes Capability Radar.")
    return CheckResult("warn", "Daily briefing exists but capability radar/gate is not verified.")


def check_docs_watcher() -> CheckResult:
    if not WATCHER.exists():
        return CheckResult("off", "Upstream docs/opportunity watcher script missing.")
    if not CRON.exists():
        return CheckResult("warn", "Cron registry missing; watcher may not be scheduled.")
    text = CRON.read_text(errors="replace")
    if "hermes-upstream-opportunity-watch" in text and "hermes-upstream-opportunity-watch.py" in text:
        return CheckResult("ok", "Docs opportunity watcher scheduled in Hermes cron.")
    return CheckResult("warn", "Watcher script exists but cron registration not found.")


def check_agent_reach_upstream() -> CheckResult:
    return CheckResult(
        "warn",
        "Agent-Reach is a plausible MIT scaffold, but cookie/global-install flows should stay sandboxed.",
        "Use Hermes Reach first; sandbox Agent-Reach separately before installing anything into main Hermes.",
    )


CHANNELS: tuple[Channel, ...] = (
    Channel("web-search", "Web search", "Current broad discovery", "Hermes web_search", "low", check_web_search, ("Use native web_search.", "For deep research, triangulate primary sources and social sources.",)),
    Channel("web-extract", "Web/page extraction", "Read pages/PDFs as markdown", "Hermes web_extract", "low", check_web_extract, ("Use native web_extract first.", "Fallback to Jina Reader only for raw URL conversion.",)),
    Channel("github", "GitHub", "Repos, issues, PRs", "GitHub MCP / gh", "medium", check_github, ("Use GitHub MCP tools first.", "Use gh CLI for workflows that need terminal/git integration.",)),
    Channel("x-search", "X/Twitter", "Current maintainer/community signal", "x_search / Nitter", "high", check_x_search, ("Use x_search if credentialed.", "Fallback to Nitter extraction.", "Do not configure cookies or posting without explicit approval.",)),
    Channel("reddit", "Reddit", "Practitioner threads", "Redlib / reddit-search", "medium", check_reddit, ("Use Redlib/privacy frontend.", "Avoid brittle anonymous scraping; browser/cookie auth requires approval.",)),
    Channel("youtube", "YouTube", "Video metadata/transcripts", "yt-dlp / media tools", "medium", check_youtube, ("Install yt-dlp only in a project venv when needed.", "Prefer transcript APIs/tools when already available.",)),
    Channel("hermes-upstream", "Hermes upstream", "Docs/commit capability drift", "git fetch/log/diff", "low", check_hermes_upstream, ("Use git fetch/log/diff in /home/hermes/.hermes/hermes-agent.", "Feed actionable deltas to newsletter capability radar.",)),
    Channel("newsletter", "Daily newsletter", "AI/Hermes intelligence report", "morning brief v3", "low", check_newsletter, ("Keep acceptance gate mandatory.", "Keep Capability Radar frontloaded.",)),
    Channel("docs-watcher", "Docs watcher", "Silent upstream opportunity alerts", "no-agent cron", "low", check_docs_watcher, ("Keep no_agent=true.", "Silent stdout means healthy/no-change.",)),
    Channel("agent-reach", "Agent-Reach upstream", "External broad internet scaffold", "sandbox only", "high", check_agent_reach_upstream, ("Do not install into main Hermes by default.", "Clone/test in /tmp or a venv.", "Adopt individual safe backends only after doctor proof.",)),
)


def get_channel(key: str) -> Channel:
    for channel in CHANNELS:
        if channel.key == key:
            return channel
    raise KeyError(key)
