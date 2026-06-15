# Hermes Trailhead

**Hermes Trailhead makes the hard-to-reach, high-signal internet part of Hermes' normal research plane.**

Ask Hermes a research question. Trailhead maps the likely source terrain, takes the best free-first routes into the places where frontier/practitioner signal actually lives — X/Twitter, Reddit, TikTok, Instagram, YouTube, GitHub, forums, docs, PDFs, and niche communities — then returns with real links, useful evidence, source-quality caveats, and the blind spots it could not close.

Trailhead exists because generic web search is not enough. It overweights SEO pages, stale summaries, and easy-to-index content. The useful answer is often somewhere messier: a maintainer post, a Reddit thread, a creator demo, a GitHub issue, a forum reply, a changelog, a video transcript, or a platform-native conversation that normal search misses or ranks poorly.

## Mission

Hermes Trailhead should make Hermes feel like it knows where the good internet lives.

That means five product commitments:

1. **Find the terrain** — decide which source families matter for the question instead of defaulting to generic web search.
2. **Take working routes** — use free/open/loginless paths first; treat paid APIs and account sessions as optional escalations, not the default product.
3. **Bring back evidence** — return links, snippets, comments, transcripts, issues, docs, and source metadata where reachable.
4. **Rank signal over sludge** — prefer practitioner, maintainer, firsthand, current, and technical sources over SEO filler.
5. **Be honest about blocked paths** — report weak, blocked, shallow, or unconfigured coverage instead of pretending every platform was deeply searched.

Everything in this repo should support that mission. If a feature does not help Hermes reach better sources, choose better routes, retrieve evidence, judge source quality, or report blind spots, it does not belong here.

## The user experience

The desired experience is not “run a scraper.” It is:

> I ask Hermes something. Hermes Trailhead decides where good evidence is likely to live, checks those places, and comes back with a field report: what it found, why it matters, what links work, what is weak, and what could not be reached.

Example output shape for a real research task:

```text
Question: Why does matte PLA sometimes print more cleanly than cheap regular PLA?

Checked:
- Reddit printer communities
- YouTube demos/transcripts
- manufacturer docs
- GitHub/slicer issues
- general web
- TikTok/Instagram/X via site-search fallback

Strong signal:
- Reddit users consistently report that matte finish hides layer-line defects.
- Manufacturer/material docs point to additives/fillers that change surface finish and flow.
- YouTube demos visually support the surface-finish claim.

Weak or blocked:
- Instagram links were discoverable but not deeply readable without a browser/session path.
- X signal was low for this query.

Evidence:
- real URLs
- result counts by source family
- extraction attempts and failures
- caveats for each weak lane
```

That is the product: not search for its own sake, but Hermes returning with better evidence from better terrain.

## Launchpad and attribution

Hermes Trailhead was launched from an earlier project named SourceScout, which began as a Hermes-specific response to **[Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach)**.

Agent-Reach is the honest launchpad. It showed the access doctrine worth keeping: use mature upstream tools, probe what is actually installed, keep fallback routes, and teach agents which path to take instead of pretending one scraper can own the internet.

Hermes Trailhead gives that doctrine a narrower product mission. Agent-Reach is a broad capability bootstrapper for many agents. Trailhead is a Hermes-native research trailhead: it exists to make Hermes' answers better by making hard-to-reach, high-signal sources part of the research experience.

Trailhead does not vendor Agent-Reach code and does not imply upstream endorsement. See [`NOTICE.md`](NOTICE.md) for attribution and adjacent prior art.

## Source terrain

Trailhead focuses on source families that general search and basic page fetchers often miss, block, truncate, or rank badly:

| Terrain | Why Hermes should care | Current default route |
|---|---|---|
| X/Twitter | maintainer posts, frontier builder discussion, breaking changes | `x_search` when configured; Nitter/site-search fallback; no cookie auth without approval |
| Reddit | practitioner debugging, buying/usage experience, long-tail failure modes | Redlib/reddit-search/site-search, then extraction |
| TikTok / Instagram | early demos, visual examples, creator-side observations | site-search/loginless discovery first; browser/session only with approval |
| YouTube | demos, reviews, lectures, tutorials, transcripts | YouTube search + transcript/media tools when available |
| GitHub | issues, PRs, releases, maintainer decisions, real bugs | GitHub MCP/`gh`/site-search |
| Forums / docs / PDFs | canonical docs plus obscure expert threads | `web_search`, `web_extract`, Jina Reader fallback |
| Dynamic/account sites | pages that require interaction or session state | Hermes browser tools with explicit approval boundaries |

A weak lane is still useful if it is labeled honestly. “Found public links but could not deeply read Instagram” is a better result than silent omission or fake confidence.

## Product principles

### Free-first, not free-only

The default product should work without paid APIs. Paid APIs can be excellent accelerators when approved, but they are not the core promise. A user should be able to ask Hermes for a high-signal research pass and get something useful from public/search/loginless paths.

### Evidence beats coverage theater

Trailhead should not say “searched TikTok” if it only ran a generic query and found two dead links. It should say exactly what happened: platform checked, query used, result count, working links, extraction status, and caveat.

### Routes are product decisions

A route is not just plumbing. Choosing Reddit over generic web, GitHub issues over blog posts, or a browser session over static extraction changes the answer Hermes gives. Routes should encode source quality, risk, cost, freshness, and evidence requirements.

### Safety is an operating constraint, not the headline

Trailhead is read-only by default. It does not automatically read cookies, post to social platforms, buy API credits, write credentials, or mutate Hermes config. That matters, but safety is not the product. The product is better research with clear approval boundaries.

### Boring implementation is a feature

The implementation should stay plain and inspectable: Python dataclasses, deterministic JSON, explicit routes, concrete evidence fields, and tests. No custom daemon, no hidden browser scraping, no mystical agent autonomy. Use mature upstream tools when they are better.

## How the current code supports the mission

| Command / module | Product job |
|---|---|
| `hermes-trailhead search all "query" --execute` | Breadth pass across high-signal source families, returning real links through loginless public search paths. |
| `hermes-trailhead search <platform> "query"` | Emits a structured action plan for one source family: tool, query, approval boundary, evidence needed, caveat. |
| `hermes-trailhead route "task"` | Chooses the best research route for a natural-language task: known URL, broad discovery, social/current signal, browser/session work, structured extraction, or external tool enablement. |
| `hermes-trailhead doctor` | Reports which routes and source lanes are actually available on this Hermes install. |
| `hermes-trailhead queue` | Prioritizes missing/weak lanes that would most improve source reach. |
| `hermes_trailhead/search.py` | Builds and executes source-family search plans. |
| `hermes_trailhead/router.py` | Encodes task-to-terrain decisions and evidence requirements. |
| `hermes_trailhead/channels.py` | Probes local capability, risk, setup gaps, and approval boundaries. |
| `hermes_trailhead/formatters.py` | Keeps human and JSON output stable enough for Hermes to consume. |

The command names are intentionally practical. `doctor` and `queue` exist because the mission fails if Hermes claims source coverage it does not actually have.

## Install

From a checkout:

```bash
python3 -m pytest -q
python3 -m hermes_trailhead doctor
```

Editable install:

```bash
uv venv .venv
. .venv/bin/activate
uv pip install -e .
hermes-trailhead doctor
```

## Core commands

```bash
# Execute a free-first breadth pass and return real links
python3 -m hermes_trailhead search all "Hermes Agent discussion" --execute --limit 3 --format json

# Plan source-family searches without executing them
python3 -m hermes_trailhead search reddit "Hermes Agent" --format json
python3 -m hermes_trailhead search tiktok "Hermes Agent" --format json

# Choose a route for the task
python3 -m hermes_trailhead route "search X, TikTok, Instagram, Reddit, and YouTube for Hermes Agent discussion"
python3 -m hermes_trailhead route "read this known url as markdown"
python3 -m hermes_trailhead route "extract schema from website"

# Inspect local coverage and gaps
python3 -m hermes_trailhead doctor --format json
python3 -m hermes_trailhead queue --risk high --top 3
python3 -m hermes_trailhead agent-brief
python3 -m hermes_trailhead plan x-search
```

## Search contract

`hermes-trailhead search` is the agent-facing command. In plan mode, it tells Hermes what to do next. In execution mode, it retrieves real links through loginless public search pages rendered by Jina Reader + DuckDuckGo HTML.

```bash
python3 -m hermes_trailhead search all "Prusa XL PLA curling edges" --execute --limit 3 --format json
```

Output shape:

```json
{
  "plan": {
    "query": "Prusa XL PLA curling edges",
    "platform": "all",
    "mode": "hermes_trailhead_action_plan",
    "paid_api_required": false,
    "actions": []
  },
  "executions": [
    {
      "platform": "reddit",
      "status": "ok",
      "executed_query": "site:reddit.com Prusa XL PLA curling edges",
      "engine": "jina_duckduckgo",
      "result_count": 3,
      "hits": [{"title": "...", "url": "...", "snippet": "..."}]
    }
  ]
}
```

Search results are leads, not proof. The research loop still needs extraction and synthesis. Trailhead's job is to send Hermes into better terrain and make the retrieval state explicit.

Supported source families:

```text
all, web, x, reddit, tiktok, instagram, youtube, github
```

## Safety and approval boundaries

Hermes Trailhead is read-only by default. It does **not** automatically:

- install global packages
- read browser cookies
- dump environment variables
- write credentials
- post to social platforms
- mutate Hermes config
- buy API credits

High-risk routes and channels are marked `approval_required` in machine-readable output. Examples include browser sessions tied to real accounts, cookie extraction, paid API setup, posting, global installer scripts, and credential storage.

## Prior art landscape

Hermes Trailhead is not claiming to be first. It is a focused Hermes product built from several proven ideas:

- **[Agent-Reach](https://github.com/Panniantong/Agent-Reach)** — the direct launchpad for the access doctrine: channel registry, probes, setup guidance, upstream-tool realism.
- **Composio / Pipedream / Arcade / Zapier MCP** — show the value of tool catalogs, authorization, and managed integrations.
- **MCP Registry / Glama / PulseMCP** — show the scale and noise of capability discovery.
- **Firecrawl / Crawl4AI / Jina Reader / Exa** — show mature crawl/search/extract primitives Trailhead should route to, not replace.
- **Browserbase / Stagehand / browser-use / Playwright MCP** — show browser execution layers Trailhead should gate and choose among.
- **Nitter / Redlib / yt-dlp / platform CLIs** — show the pragmatic access paths needed for current social/practitioner signal.

The lesson is not “copy all of them.” The lesson is: Hermes needs a local product layer that knows which route fits the question, what is available right now, what risk it carries, and what evidence must come back.

## What Hermes Trailhead is not

Hermes Trailhead is not:

- a public MCP registry
- a SaaS integration marketplace
- a browser automation framework
- a crawler
- a scraping toolkit
- a social bot
- a credential manager

It is the local Hermes research trailhead: source terrain, route choice, free-first retrieval, evidence requirements, and honest blind spots.

## Roadmap judged by the mission

The next work should be prioritized by whether it improves Hermes' real research output.

1. **Source-quality scoring** — rank hits by likely usefulness: maintainer/practitioner/firsthand/current/canonical beats SEO filler.
2. **Extraction follow-through** — after `--execute`, optionally extract/read top hits and report which pages were actually usable.
3. **Better weak-lane reporting** — make TikTok/Instagram/X caveats sharper: discovered links vs readable content vs account-required pages.
4. **Route scoring from live state** — route decisions should consider current channel health, credentials, cost, latency, and risk.
5. **State/history** — track which lanes repeatedly work or fail, then feed that into GBrain or the morning briefing.
6. **Capability imports** — import candidate tools from MCP/catalog ecosystems, but keep them untrusted until locally validated.
7. **Benchmarks** — test against real research tasks and score answer quality, link validity, extraction success, and caveat honesty.

If a roadmap item cannot explain how it makes Hermes return better evidence, it should not be a priority.

## Tests

```bash
python3 -m py_compile hermes_trailhead/*.py
python3 -m pytest -q
python3 -m hermes_trailhead search all "Hermes Agent discussion" --execute --limit 1 --format json
```

The test suite covers CLI JSON contract stability, approval gates, no-secret-output regressions, route decision quality, queue/filter behavior, search plan contracts, and README positioning constraints.

## Weekly company loop

A healthy Trailhead needs maintenance because the internet terrain changes. The weekly loop should ask:

1. Did the product still return useful evidence on real research tasks?
2. Which source lanes were weak, blocked, or noisy?
3. Did any upstream tool make a route safer, cheaper, or more reliable?
4. Did any platform become more login-heavy or brittle?
5. Does the README still lead with mission and user experience before implementation?
6. What is the one highest-leverage improvement to Hermes' research quality?

Low-noise rule: if nothing actionable changed, say that and stop.

## License

Hermes Trailhead is open source under the BSD 3-Clause License. You may use, modify, and redistribute it, but you must preserve the copyright notice and license text.

See [`NOTICE.md`](NOTICE.md) for prior-art acknowledgments.
