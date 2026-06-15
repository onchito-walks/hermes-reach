# Hermes Trailhead Product Architecture

Hermes Trailhead is a Hermes-native research trailhead. Its job is to make Hermes' answers better by sending research tasks into the right high-signal source terrain and bringing back usable evidence with honest caveats.

The architecture is intentionally boring because the product is not the infrastructure. The product is the experience: Hermes knows where to look, uses the safest working route first, returns real links and excerpts, and says what it could not reach.

## Product promise

For a given research question, Hermes Trailhead should answer four operational questions:

1. **Where is the good evidence likely to live?** Generic web, X, Reddit, TikTok, Instagram, YouTube, GitHub, docs, forums, PDFs, browser-only pages, or a mix.
2. **Which route works right now?** Native Hermes tools, loginless public search, privacy frontends, GitHub MCP, media tools, browser tools, or an approved external connector.
3. **What evidence must come back?** Working links, counts, extracted text, comments, transcripts, issue threads, source quality notes, and failure/caveat state.
4. **What boundary requires approval?** Cookies, browser sessions, credentials, paid APIs, posting, global installs, account mutation.

Everything else is implementation detail.

## Why Agent-Reach mattered

Agent-Reach was the launchpad because it had the right access realism: do not build bespoke scrapers for everything; identify mature upstream tools, probe what exists, document fallbacks, and give the agent durable instructions.

Hermes Trailhead keeps that doctrine but narrows the product. Agent-Reach is broad capability bootstrap. Trailhead is Hermes research quality: better terrain, better routes, better evidence, better caveats.

## Architecture layers

```text
Research question
   ↓
Source terrain decision
   ↓
Route choice + approval boundary
   ↓
Free-first retrieval / action plan
   ↓
Evidence returned + caveats
   ↓
Hermes synthesis
```

## Current code slice

| Layer | Current implementation | Product role |
|---|---|---|
| Source terrain | `search.py` platform plans: web, X, Reddit, TikTok, Instagram, YouTube, GitHub | Makes source families explicit instead of hiding them behind generic search. |
| Route choice | `router.py` task routes | Chooses known-URL read, discovery, social/current signal, extraction, browser work, or external tool enablement. |
| Capability state | `channels.py` checks | Prevents fake coverage claims by showing what the local Hermes install can actually use. |
| Evidence contract | dataclasses + JSON formatters | Gives Hermes structured fields for links, counts, status, caveats, and approval requirements. |
| Operator UX | CLI commands | Lets humans and agents inspect, execute, and verify source routes. |

## Product principles encoded in the architecture

### Free-first retrieval

The default path should work without paid APIs. `search --execute` uses loginless public search rendered through Jina Reader and DuckDuckGo HTML. That is not the final ideal retrieval system, but it proves the product can return real links across source families without paid API dependence.

### Honest weak lanes

TikTok, Instagram, and X are difficult. The architecture should represent that honestly: discoverable links are not the same as deeply readable posts; configured `x_search` is not the same as a local Nitter fallback; browser/session routes are not the same as accountless access.

### Evidence as data

Every machine-readable path should carry enough data for Hermes to avoid overclaiming: source family, query, route, status, result count, working URL, extraction attempt, caveat, approval requirement.

### Approval boundaries as data

Approval requirements must be fields, not vibes. A route involving account sessions, cookies, paid services, posting, or global installation must be machine-readable as approval-required.

### Upstream tools, not bespoke heroics

Trailhead should route to mature tools — web_extract, GitHub MCP, Jina Reader, Redlib/Nitter-style frontends, yt-dlp/media tools, Firecrawl, Crawl4AI, Stagehand, Browserbase — instead of inventing custom scrapers when established tools exist.

## Current weakness

Hermes Trailhead is not yet fully living up to its mission. It can plan and run a breadth pass, but it does not yet deeply extract and rank the best evidence after retrieval. That is the central product gap.

The old architecture was strong as a doctor/router. The new product lens says that is only the foundation. A diagnostic that says “seven lanes available” is useful, but the user cares whether Hermes came back with better evidence and a better answer.

## Next architecture bets

### P0 — Evidence follow-through

After `search --execute`, add an optional mode that extracts/reads top hits and reports:

- extraction attempted/succeeded/failed
- usable text length
- source type
- source quality signal
- why the hit is or is not worth using

### P0 — Source quality scoring

Add ranking features that favor:

- maintainer/official/canonical sources
- practitioner firsthand reports
- current discussions when recency matters
- GitHub issues/PRs for real implementation bugs
- transcripts/demos for visual/product evidence

And penalize:

- SEO farms
- empty platform shells
- duplicate snippets
- dead links
- generic listicles

### P1 — Live route scoring

Route decisions should consider current channel health, auth availability, cost, latency, and risk. If Redlib is down, the Reddit route should change. If X search is credit-limited, the route should say so before Hermes promises X coverage.

### P1 — Historical reliability

Track which routes work over time. A weekly product loop should know whether TikTok discovery is repeatedly weak, whether GitHub links are reliable, whether Jina is failing, and whether a platform became more login-heavy.

### P1 — Capability import, locally validated

Import candidates from MCP/catalog ecosystems, but keep them untrusted until locally validated. Popularity is not trust. A candidate becomes useful only after it proves it can improve Hermes research output.

### P2 — Benchmarks by user outcome

Benchmarks should measure answer quality and evidence quality, not just command success. Example task classes:

- material/practitioner research
- current tool comparison
- GitHub issue diagnosis
- product trend scan
- forum/docs deep answer
- visual creator evidence search

## Non-goals

Hermes Trailhead should not become:

- a crawler
- a browser automation framework
- a scraping toolkit
- a SaaS connector marketplace
- a credential broker
- a social bot
- a generic MCP registry

It should remain the Hermes layer that knows source terrain, chooses routes, retrieves evidence, and reports blind spots.
