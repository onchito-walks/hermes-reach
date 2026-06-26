"""Hermes Trailhead evidence extraction — follow-through for search hits.

After ``search --execute`` returns hits, this module extracts actual page content
from URLs and reports what was readable, how much content was retrieved, and
what failed.  The product goal is to turn "5 links found" into "3 pages extracted,
2 blocked — here's what they actually say."
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
import subprocess
import time
import urllib.request
from urllib.parse import parse_qs, urlparse
from typing import Callable, Literal

from .search import SearchHit

ExtractionStatus = Literal["ok", "blocked", "error", "not_attempted"]
TranscriptAttemptStatus = Literal["ok", "blocked", "not_available", "not_attempted"]
SourceType = Literal[
    "web", "x", "reddit", "tiktok", "instagram", "youtube", "github",
    "docs", "forum", "pdf", "unknown",
]

FetchFn = Callable[[str, int], str]


@dataclass(frozen=True)
class VideoEvidence:
    """First-class video-only evidence for sources where page text is not the primary content."""
    caption_transcript_status: TranscriptAttemptStatus = "not_attempted"
    caption_transcript: str = ""
    caption_transcript_length: int = 0
    caption_transcript_error: str = ""
    visual_analysis_status: str = "not_attempted"
    visual_analysis_summary: str = ""
    audio_transcript_status: str = "not_configured"
    audio_transcript: str = ""
    metadata_url: str = ""
    metadata_title: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        if len(d.get("caption_transcript", "")) > 2000:
            d["caption_transcript"] = d["caption_transcript"][:2000] + "..."
        if len(d.get("audio_transcript", "")) > 2000:
            d["audio_transcript"] = d["audio_transcript"][:2000] + "..."
        if len(d.get("visual_analysis_summary", "")) > 2000:
            d["visual_analysis_summary"] = d["visual_analysis_summary"][:2000] + "..."
        return d


@dataclass(frozen=True)
class ExtractionResult:
    status: ExtractionStatus
    content: str = ""
    content_length: int = 0
    source_type: SourceType = "unknown"
    error_message: str = ""
    transcript_attempted: bool = False
    transcript_error: str = ""
    video_evidence: VideoEvidence | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        # Truncate content to a reasonable preview length for JSON output
        if len(d.get("content", "")) > 2000:
            d["content"] = d["content"][:2000] + "..."
        if self.video_evidence is not None:
            d["video_evidence"] = self.video_evidence.to_dict()
        return d

    @property
    def usable(self) -> bool:
        return self.status == "ok" and self.content_length > 50


@dataclass(frozen=True)
class ExtractedHit:
    title: str
    url: str
    snippet: str = ""
    extraction: ExtractionResult = ExtractionResult(status="not_attempted")

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "extraction": self.extraction.to_dict(),
        }

    @classmethod
    def from_search_hit(cls, hit: SearchHit) -> ExtractedHit:
        return cls(title=hit.title, url=hit.url, snippet=hit.snippet)


def _classify_source_type(url: str) -> SourceType:
    """Heuristic URL classification to set source type for extraction context."""
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
    if url_lower.endswith(".pdf"):
        return "pdf"
    if any(d in url_lower for d in ["docs.", "documentation", "readthedocs", "wiki"]):
        return "docs"
    if any(f in url_lower for f in ["forum.", "community.", "discourse", "stackoverflow", "stackexchange"]):
        return "forum"
    return "web"


def _fetch_text(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 Hermes Trailhead/0.2 (extraction)",
            "Accept": "text/plain,text/markdown,text/html,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
        # Try UTF-8, fall back to replacement
        return raw.decode("utf-8", errors="replace")


def _fetch_jina(url: str, timeout: int = 20) -> str:
    """Fetch via Jina Reader for markdown conversion."""
    jina_url = f"https://r.jina.ai/{url}"
    req = urllib.request.Request(
        jina_url,
        headers={
            "User-Agent": "Mozilla/5.0 Hermes Trailhead/0.2 (jina)",
            "Accept": "text/markdown,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _youtube_video_id(url: str) -> str:
    """Extract a YouTube video id from watch, youtu.be, shorts, or embed URLs."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path_parts = [p for p in parsed.path.split("/") if p]
    if "youtu.be" in host and path_parts:
        return path_parts[0]
    if "youtube.com" in host:
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [""])[0]
        if len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed"}:
            return path_parts[1]
    return ""


def _fetch_youtube_transcript(url: str, timeout: int = 20) -> str:
    """Fetch YouTube captions/transcript using the mature youtube-transcript-api package."""
    video_id = _youtube_video_id(url)
    if not video_id:
        raise RuntimeError("Could not parse YouTube video id")

    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - depends on optional install
        raise RuntimeError("youtube-transcript-api is not installed") from exc

    api = YouTubeTranscriptApi()
    fetched = api.fetch(video_id, languages=("en", "en-US", "en-GB"))
    snippets = getattr(fetched, "snippets", fetched)
    lines: list[str] = []
    for item in snippets:
        if isinstance(item, dict):
            text = item.get("text", "")
            start = item.get("start")
        else:
            text = getattr(item, "text", "")
            start = getattr(item, "start", None)
        text = " ".join(str(text).split())
        if not text:
            continue
        if start is None:
            lines.append(text)
        else:
            lines.append(f"[{float(start):.1f}s] {text}")
    content = "\n".join(lines).strip()
    if not content:
        raise RuntimeError("YouTube transcript was empty")
    return f"YouTube transcript for {video_id}\n\n{content}"


def _reddit_frontend_url(url: str) -> str:
    """Convert Reddit URLs to the configured Redlib privacy frontend."""
    parsed = urlparse(url)
    if "reddit.com" not in parsed.netloc.lower():
        return url
    return f"https://redlib.perennialte.ch{parsed.path}"


def _strip_hermes_web_extract_output(output: str) -> str:
    """Normalize Hermes CLI output down to extracted markdown content."""
    lines = output.splitlines()

    if lines and lines[0].startswith("session_id:"):
        lines = lines[1:]

    if lines and re.match(r"^Readable markdown content from .+:$", lines[0].strip()):
        lines = lines[1:]

    while lines and not lines[0].strip():
        lines = lines[1:]

    return "\n".join(lines).strip()


def _fetch_hermes_web_extract(url: str, timeout: int = 30) -> str:
    """Fetch readable markdown using Hermes' native web_extract tool path."""
    prompt = (
        "Use the native web_extract tool on the URL below and return only the "
        "extracted markdown content, with no explanation, no preamble, and no "
        "code fencing.\n\n"
        f"URL: {json.dumps(url)}"
    )
    cmd = [
        "hermes",
        "chat",
        "-q",
        prompt,
        "-t",
        "web",
        "-Q",
        "--ignore-rules",
        "--ignore-user-config",
        "--safe-mode",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=max(timeout, 30))
    if proc.returncode != 0:
        stderr = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(stderr or f"hermes chat failed with exit code {proc.returncode}")

    content = _strip_hermes_web_extract_output(proc.stdout)
    if not content:
        raise RuntimeError("hermes web_extract returned empty content")
    return content


def _exception_summary(exc: Exception) -> str:
    """Return a compact human-readable summary of an exception."""
    msg = str(exc)
    if len(msg) > 200:
        msg = msg[:200] + "..."
    return f"{type(exc).__name__}: {msg}"

# ── Stealth Chrome backend (primary) ──────────────────────────────────

_STEALTH_EXTRACT_SCRIPT = str(
    __import__("pathlib").Path(__file__).resolve().parent.parent / "stealth-extract.js"
)

def _fetch_stealth_chrome(url: str, timeout: int = 30, cookies: str | None = None) -> str:
    """Fetch page content through puppeteer-extra + stealth plugin Chrome.

    Stealth-patched Chrome passes bot detection on YouTube, Instagram, and
    TikTok.  Returns clean page text.  For YouTube URLs, also attempts to
    extract auto-generated captions from the DOM.

    Requires: node, puppeteer-extra, puppeteer-extra-plugin-stealth
    """
    cmd = [
        "node", _STEALTH_EXTRACT_SCRIPT, url,
        "--timeout", str(max(timeout, 15) * 1000),
    ]
    if cookies and __import__("os").path.exists(cookies):
        cmd.extend(["--cookies", cookies])
    if "youtube.com" in url or "youtu.be" in url:
        cmd.append("--transcript")

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 15)
    if proc.returncode != 0:
        stderr = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(stderr or f"stealth-extract failed with exit {proc.returncode}")

    try:
        result = __import__("json").loads(proc.stdout)
    except Exception:
        raise RuntimeError(f"stealth-extract returned invalid JSON: {proc.stdout[:200]}")

    if not result.get("ok"):
        raise RuntimeError(result.get("error", "stealth-extract failed"))

    text = result.get("text", "")
    if not text or len(text) < 20:
        raise RuntimeError("stealth-extract returned empty page content")

    # For YouTube, prefix transcript if available
    transcript = result.get("transcript")
    if transcript:
        text = f"YouTube transcript:\n\n{transcript}\n\n---\n\nPage text:\n\n{text}"

    return text


# ── yt-dlp transcript backend ────────────────────────────────────────

def _fetch_ytdlp_transcript(url: str, timeout: int = 30) -> str:
    """Fetch YouTube auto-generated subtitles using yt-dlp.

    yt-dlp is battle-tested and uses multiple extraction methods to bypass
    YouTube restrictions.  Downloads English auto-subs as SRT, converts to
    plain text.  This is the PRIMARY YouTube transcript path since
    youtube-transcript-api is IP-blocked on datacenter IPs.
    """
    video_id = _youtube_video_id(url)
    if not video_id:
        raise RuntimeError("Could not parse YouTube video id")

    out_path = f"/tmp/yt-trailhead-{video_id}"
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-auto-subs",
        "--sub-lang", "en",
        "--convert-subs", "srt",
        "-o", out_path,
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        if "Video unavailable" in stderr or "Private video" in stderr:
            raise RuntimeError(f"YouTube: Video unavailable or private")
        raise RuntimeError(f"yt-dlp failed: {stderr[:200]}")

    # Read the downloaded SRT file
    import glob as _glob
    srt_files = _glob.glob(f"{out_path}.en.srt")
    if not srt_files:
        raise RuntimeError("yt-dlp: no subtitle file produced (video may lack auto-captions)")

    with open(srt_files[0], "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    # Clean up temp file
    try:
        __import__("os").remove(srt_files[0])
    except Exception:
        pass

    # Strip SRT timestamps and sequence numbers, keep only text
    lines: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.isdigit():
            continue  # sequence number
        if "-->" in line:
            continue  # timestamp
        if line.startswith("[") and line.endswith("]"):
            continue  # music/sound effect tags
        lines.append(line)

    content = " ".join(lines).strip()
    if not content or len(content) < 30:
        raise RuntimeError("yt-dlp: subtitle content too short or empty")

    return f"YouTube auto-captions for {video_id}\n\n{content}"


# ── Browser Harness backend (legacy fallback) ─────────────────────────

def _fetch_browser_harness(url: str, timeout: int = 30) -> str:
    """Fetch page content through the local browser-harness daemon (Chrome CDP).

    Uses the running Chrome instance on CDP port 9222.  Navigates to the URL,
    waits for page settle, then extracts visible text.  Kept as fallback for
    platforms where stealth Chrome is unavailable.
    """
    script = _BROWSER_EXTRACT_SCRIPT.replace("{url}", url).replace("{timeout}", str(timeout))
    proc = subprocess.run(
        ["browser-harness"],
        input=script,
        capture_output=True,
        text=True,
        timeout=timeout + 10,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(stderr or f"browser-harness failed with exit {proc.returncode}")
    out = proc.stdout.strip()
    if not out or len(out) < 20:
        raise RuntimeError("browser-harness returned empty page content")
    return out


# ── Apify backend (primary for Instagram / TikTok) ─────────────────────

_ApifyClient = None  # lazy import


def _get_apify_token() -> str | None:
    """Read Apify API token from secrets file or environment."""
    import os as _os
    token = _os.environ.get("APIFY_API_KEY")
    if token:
        return token
    token_path = _os.path.expanduser("~/.hermes/secrets/apify-api-key.txt")
    try:
        with open(token_path) as f:
            token = f.read().strip()
            if token:
                return token
    except Exception:
        pass
    return None


def _get_apify_client():
    """Lazy-init Apify client. Returns None if no API key configured."""
    global _ApifyClient
    token = _get_apify_token()
    if not token:
        return None
    if _ApifyClient is None:
        from apify_client import ApifyClient as _AC
        _ApifyClient = _AC
    return _ApifyClient(token)


def _instagram_shortcode(url: str) -> str:
    """Extract shortcode from Instagram URL like /p/DDaO4kPyB7W/."""
    import re as _re
    m = _re.search(r'instagram\.com/(?:p|reel)/([A-Za-z0-9_-]+)', url)
    return m.group(1) if m else ""


def _fetch_apify_instagram(url: str, timeout: int = 60) -> str:
    """Extract Instagram post/profile content via Apify Instagram Scraper.

    Uses Apify's managed cloud service — no accounts, no proxies, no browser
    management needed.  Returns structured text with captions, comments, and
    metadata.
    """
    client = _get_apify_client()
    if not client:
        raise RuntimeError("Apify API key not configured")

    shortcode = _instagram_shortcode(url)
    if shortcode:
        # Specific post — use direct URL
        run_input = {
            "directUrls": [f"https://www.instagram.com/p/{shortcode}/"],
            "resultsLimit": 1,
        }
    else:
        # Profile URL — extract username
        import re as _re
        m = _re.search(r'instagram\.com/([A-Za-z0-9_.]+)', url)
        username = m.group(1) if m else ""
        if not username:
            raise RuntimeError(f"Could not parse Instagram URL: {url}")
        run_input = {
            "username": [username],
            "resultsLimit": 5,
        }

    run = client.actor("apify/instagram-scraper").call(
        run_input=run_input,
        memory_mbytes=256,
        timeout_secs=timeout,
    )

    # Extract meaningful text from results
    items = _extract_apify_dataset(run, client)
    if not items:
        raise RuntimeError("Apify Instagram scraper returned no results")

    lines: list[str] = []
    for item in items:
        caption = item.get("caption", "") or item.get("description", "") or ""
        if caption:
            lines.append(caption)
        # Add comments if available
        comments = item.get("latestComments", []) or item.get("comments", []) or []
        for c in comments[:5]:
            text = c.get("text", "") if isinstance(c, dict) else str(c)
            if text:
                lines.append(f"[comment] {text}")

    content = "\n\n".join(lines).strip()
    if not content or len(content) < 20:
        raise RuntimeError("Apify Instagram scraper: content too short or empty")
    return content


def _fetch_apify_tiktok(url: str, timeout: int = 60) -> str:
    """Extract TikTok video/profile content via Apify TikTok Scraper.

    Uses Apify's managed cloud service.  Returns video descriptions,
    metadata, and stats.
    """
    client = _get_apify_client()
    if not client:
        raise RuntimeError("Apify API key not configured")

    import re as _re
    # Extract username from URL
    m = _re.search(r'tiktok\.com/@([A-Za-z0-9_.]+)', url)
    username = m.group(1) if m else ""
    if not username:
        raise RuntimeError(f"Could not parse TikTok URL: {url}")

    run_input = {
        "username": [username],
        "postsCount": 5,
    }

    run = client.actor("clockworks/tiktok-scraper").call(
        run_input=run_input,
        memory_mbytes=256,
        timeout_secs=timeout,
    )

    items = _extract_apify_dataset(run, client)
    if not items:
        raise RuntimeError("Apify TikTok scraper returned no results")

    lines: list[str] = []
    for item in items:
        desc = item.get("text", "") or item.get("description", "") or ""
        if desc:
            lines.append(f"TikTok: {desc}")
        # Add stats for context
        plays = item.get("playCount", "") or item.get("diggCount", "")
        if plays:
            lines.append(f"  [plays: {plays}]")

    content = "\n".join(lines).strip()
    if not content or len(content) < 20:
        raise RuntimeError("Apify TikTok scraper: content too short or empty")
    return content


def _extract_apify_dataset(run_result, client) -> list[dict]:
    """Pull items from Apify run result (handles both sync call and async)."""
    import json as _json
    # If run_result is already a list, return it
    if isinstance(run_result, list):
        return run_result
    # If it's a dict with items, return items
    if isinstance(run_result, dict):
        items = run_result.get("items") or run_result.get("data") or []
        if items:
            return items
        # Try getting dataset
        dataset_id = run_result.get("defaultDatasetId") or run_result.get("datasetId")
        if dataset_id:
            items = client.dataset(dataset_id).list_items().items
            return items or []
    return []


# ── Instagram / TikTok cookie paths ───────────────────────────────────

def _get_platform_cookies(platform: str) -> str | None:
    """Return path to burner-account cookies file if it exists."""
    cookie_path = __import__("os").path.expanduser(
        f"~/.hermes/state/{platform}-cookies.json"
    )
    return cookie_path if __import__("os").path.exists(cookie_path) else None


_BROWSER_EXTRACT_SCRIPT = """
import time as _t

ensure_real_tab()
result = goto_url("{url}")
if not result or not result.get('loaderId'):
    print("NAVIGATE_FAILED")
    exit(1)

# Wait for dynamic content to settle (TikTok/Instagram JS hydration, YouTube page load)
body_text = ""
for attempt in range(1, 15):
    _t.sleep(0.8)
    body_text = js("(document.body && document.body.innerText) || ''")
    if body_text and len(body_text) > 50:
        break

if not body_text or len(body_text) < 10:
    print("NO_VISIBLE_TEXT")
    exit(2)

# Truncate to reasonable extract size
if len(body_text) > 8000:
    body_text = body_text[:8000] + "..."

# Include page title for context
title_text = js("document.title || ''")
if title_text:
    print(f"TITLE: {title_text}")
print(body_text)
"""


def extract_one(url: str, *, extract: FetchFn | None = None, fetch: FetchFn | None = None, timeout: int = 15, title: str = "") -> ExtractionResult:
    """Extract content from a single URL. Tries Hermes web_extract first, then direct fetch, then Jina Reader.

    For video-only sources (TikTok, YouTube, Instagram), returns structured
    video_evidence alongside any plain-text content that was retrievable.
    """
    fetcher = fetch or _fetch_text
    source_type = _classify_source_type(url)

    # TikTok / Instagram: Apify first (primary), then oEmbed, stealth Chrome,
    # then browser-harness fallback.
    if source_type in ("tiktok", "instagram"):

        # Primary: Apify cloud scraping (no accounts, no proxies, no browser)
        try:
            if source_type == "instagram":
                content = _fetch_apify_instagram(url, timeout=max(timeout, 30))
            else:
                content = _fetch_apify_tiktok(url, timeout=max(timeout, 30))
            if content and len(content) > 50:
                return ExtractionResult(
                    status="ok",
                    content=content[:8000],
                    content_length=len(content),
                    source_type=source_type,
                    video_evidence=VideoEvidence(
                        caption_transcript_status="ok" if source_type == "instagram" else "not_attempted",
                        visual_analysis_status="available",
                        visual_analysis_summary=content[:2000],
                        metadata_url=url,
                        metadata_title=title,
                    ),
                )
        except Exception:
            pass  # Apify failed or not configured → fall through

        # TikTok oEmbed: try metadata extraction without rendering the full page.
        if source_type == "tiktok":
            try:
                oembed_url = f"https://www.tiktok.com/oembed?url={url}"
                content = fetcher(oembed_url, timeout=timeout)
                if content and len(content) > 50:
                    import json as _json
                    try:
                        data = _json.loads(content)
                        title_text = data.get("title", "")
                        author = data.get("author_name", "")
                        desc = f"TikTok by @{author}: {title_text}" if author else title_text
                        if desc and len(desc) > 30:
                            return ExtractionResult(
                                status="ok",
                                content=desc[:2000],
                                content_length=len(desc),
                                source_type=source_type,
                                video_evidence=VideoEvidence(
                                    caption_transcript_status="not_attempted",
                                    visual_analysis_status="available",
                                    metadata_url=url,
                                    metadata_title=desc[:200],
                                ),
                            )
                    except Exception:
                        pass
            except Exception:
                pass

        # Stealth Chrome: primary browser extraction for Instagram/TikTok.
        cookies = _get_platform_cookies(source_type)
        try:
            content = _fetch_stealth_chrome(url, timeout=timeout, cookies=cookies)
            if content and len(content) > 50:
                return ExtractionResult(
                    status="ok",
                    content=content[:8000],
                    content_length=len(content),
                    source_type=source_type,
                    video_evidence=VideoEvidence(
                        caption_transcript_status="not_available",
                        visual_analysis_status="available",
                        visual_analysis_summary=content[:2000],
                        metadata_url=url,
                        metadata_title=title,
                    ),
                )
        except Exception:
            pass

        # Browser-harness: legacy fallback for platforms without stealth Chrome.
        if source_type == "instagram":
            try:
                content = _fetch_browser_harness(url, timeout=timeout)
                if content and len(content) > 50:
                    return ExtractionResult(
                        status="ok",
                        content=content[:5000],
                        content_length=len(content),
                        source_type=source_type,
                        video_evidence=VideoEvidence(
                            caption_transcript_status="not_available",
                            visual_analysis_status="available",
                            visual_analysis_summary=content[:2000],
                            metadata_url=url,
                            metadata_title=title,
                        ),
                    )
            except Exception:
                pass

        return ExtractionResult(
            status="blocked",
            source_type=source_type,
            error_message=(
                f"{source_type} content requires browser/session for full extraction; "
                "stealth Chrome and browser-harness both failed; "
                f"cookies {'available' if cookies else 'not configured'}"
            ),
            video_evidence=VideoEvidence(
                caption_transcript_status="not_attempted" if source_type == "tiktok" else "not_available",
                visual_analysis_status="available",
                visual_analysis_summary="Title, snippet, and video URL preserved as discovery evidence; call video_analyze() for visual summary.",
                audio_transcript_status="not_configured",
                metadata_url=url,
                metadata_title=title,
            ),
        )

    # YouTube: try yt-dlp captions first (primary transcript path), fall
    # back to youtube-transcript-api, then stealth Chrome for page content.
    if source_type == "youtube":
        transcript_attempted = True
        transcript_error = ""
        video_ev = VideoEvidence(
            metadata_url=url,
            metadata_title=title,
            visual_analysis_status="available",
            visual_analysis_summary="Title, snippet, and video URL preserved; call video_analyze() for visual summary.",
        )

        # Primary: yt-dlp auto-generated subtitles
        ytdlp_exc = None
        try:
            content = _fetch_ytdlp_transcript(url, timeout=timeout)
            if content and len(content) > 50:
                return ExtractionResult(
                    status="ok",
                    content=content,
                    content_length=len(content),
                    source_type=source_type,
                    transcript_attempted=True,
                    video_evidence=VideoEvidence(
                        caption_transcript_status="ok",
                        caption_transcript=content,
                        caption_transcript_length=len(content),
                        visual_analysis_status="available",
                        audio_transcript_status="ok",
                        metadata_url=url,
                        metadata_title=title,
                    ),
                )
        except Exception as exc:
            ytdlp_exc = exc
            transcript_error = f"yt-dlp transcript failed: {_exception_summary(exc)}"

        # Fallback 1: youtube-transcript-api (legacy, may be IP-blocked)
        if transcript_error:
            try:
                content = _fetch_youtube_transcript(url, timeout=timeout)
                if content and len(content) > 50:
                    return ExtractionResult(
                        status="ok",
                        content=content,
                        content_length=len(content),
                        source_type=source_type,
                        transcript_attempted=True,
                        video_evidence=VideoEvidence(
                            caption_transcript_status="ok",
                            caption_transcript=content,
                            caption_transcript_length=len(content),
                            visual_analysis_status="available",
                            audio_transcript_status="ok",
                            metadata_url=url,
                            metadata_title=title,
                        ),
                    )
            except Exception as exc2:
                transcript_error = f"All transcript methods failed: yt-dlp: {_exception_summary(ytdlp_exc or exc2)}, api: {_exception_summary(exc2)}"

        # Fallback 2: stealth Chrome for page content + captions
        if transcript_error:
            try:
                content = _fetch_stealth_chrome(url, timeout=timeout)
                if content and len(content) > 50:
                    return ExtractionResult(
                        status="ok",
                        content=content[:8000],
                        content_length=len(content),
                        source_type=source_type,
                        transcript_attempted=True,
                        transcript_error=transcript_error,
                        video_evidence=VideoEvidence(
                            caption_transcript_status="blocked",
                            caption_transcript_error=transcript_error,
                            visual_analysis_status="available",
                            audio_transcript_status="not_configured",
                            metadata_url=url,
                            metadata_title=title,
                        ),
                    )
            except Exception:
                pass

        # Fallback 3: direct page fetch for metadata/title/description
        try:
            content = fetcher(url, timeout)
            if content and len(content) > 50:
                return ExtractionResult(
                    status="ok",
                    content=content[:5000],
                    content_length=len(content),
                    source_type=source_type,
                    transcript_attempted=transcript_attempted,
                    transcript_error=transcript_error,
                    video_evidence=video_ev,
                )
        except Exception:
            pass

        # No page content either
        return ExtractionResult(
            status="blocked",
            source_type=source_type,
            error_message=f"YouTube page and transcript both unreachable: {transcript_error or 'IP blocked or video unavailable'}",
            transcript_attempted=transcript_attempted,
            transcript_error=transcript_error,
            video_evidence=video_ev,
        )

    # Reddit often blocks direct fetches; try Redlib before generic page extraction.
    if source_type == "reddit":
        try:
            content = fetcher(_reddit_frontend_url(url), timeout)
            if content and len(content) > 50:
                return ExtractionResult(
                    status="ok",
                    content=content,
                    content_length=len(content),
                    source_type=source_type,
                )
        except Exception:
            pass  # Fall through to Hermes/Jina/direct fetch

    # Try direct fetch first (fast, no subprocess).
    try:
        content = fetcher(url, timeout)
        if content and len(content) > 50:
            return ExtractionResult(
                status="ok",
                content=content,
                content_length=len(content),
                source_type=source_type,
            )
    except Exception:
        pass  # Fall through to Jina

    # Try Jina Reader for markdown.
    if fetch is None:  # Only try Jina when not testing
        try:
            content = _fetch_jina(url, timeout=timeout)
            if content and len(content) > 50:
                return ExtractionResult(
                    status="ok",
                    content=content,
                    content_length=len(content),
                    source_type=source_type,
                )
        except Exception:
            pass

    # Try Hermes native web_extract last (slow subprocess).
    try:
        content = (extract or _fetch_hermes_web_extract)(url, timeout)
        if content and len(content) > 50:
            return ExtractionResult(
                status="ok",
                content=content,
                content_length=len(content),
                source_type=source_type,
            )
    except Exception:
        pass  # Fall through to error

    return ExtractionResult(
        status="error",
        source_type=source_type,
        error_message=f"Could not extract content from {url} via Hermes web_extract, direct fetch, or Jina fetch",
    )


def extract_hits(
    hits: tuple[SearchHit, ...],
    *,
    limit: int = 5,
    extract: FetchFn | None = None,
    fetch: FetchFn | None = None,
    timeout: int = 15,
) -> tuple[ExtractedHit, ...]:
    """Extract content from search hits. Returns ExtractedHit objects with extraction results."""
    extracted: list[ExtractedHit] = []
    for hit in hits[:limit]:
        result = extract_one(hit.url, extract=extract, fetch=fetch, timeout=timeout, title=hit.title)
        eh = ExtractedHit(
            title=hit.title,
            url=hit.url,
            snippet=hit.snippet,
            extraction=result,
        )
        extracted.append(eh)
    return tuple(extracted)
