# Hermes Trailhead Product + Guardrail Audit — 2026-06-15

## Verdict

Hermes Trailhead is on the right track, but only if it keeps treating search results as leads and not proof. The project has the right center of gravity: it is not trying to become a crawler, browser automation framework, credential broker, or generic tool registry. It is trying to make Hermes better at research by choosing the right source terrain, taking safe/free-first routes, returning evidence, and reporting blocked or weak lanes honestly.

The most important risk is coverage theater. A command that returns one TikTok or Instagram URL through generic search has not “searched TikTok” in the product sense. It has discovered a public link. The product only earns the stronger claim after it can read or inspect the content, count what was checked, and explain what could not be reached. This audit turned that into an enforceable output guardrail: execution results now preserve the original lane status, approval requirement, evidence state, and caveat.

## What Agent-Reach teaches us

Primary source reviewed: https://github.com/Panniantong/Agent-Reach and its raw README/install/update docs.

Agent-Reach’s useful doctrine is not “build a mega scraper.” It is scaffolding realism: identify mature upstream tools, install/configure them in isolated places, run doctor checks, document what works, and teach agents how to use the underlying tools directly. The project explicitly describes itself as scaffolding rather than a framework. It routes through tools like `yt-dlp`, `gh`, `twitter-cli`, `rdt-cli`, `mcporter`, and platform-specific CLIs rather than pretending one codebase owns the whole internet.

Trailhead should keep borrowing that doctrine: channel registry, doctor checks, setup plans, safe/dry-run thinking, upstream-tool realism, and a bias toward proven tools. Trailhead should not borrow Agent-Reach’s broad “full internet access” posture wholesale. Hermes Trailhead has a narrower and better product: Hermes research quality. The user does not need every action surface; the user needs better evidence from the right terrain with boundaries stated clearly.

## What is strong now

The README is correctly product-first. It starts with the user promise: Hermes should know where the good internet lives. It defines commitments around terrain, routes, evidence, signal ranking, and blocked-lane honesty. That is the correct north star and it prevents the repo from collapsing into a bag of commands.

The architecture is appropriately boring. The current code uses dataclasses, deterministic JSON, explicit route objects, channel checks, and tests. This is right. The project should not invent hidden daemons, browser-scraping magic, or a custom crawler when Hermes already has web tools and mature upstream projects exist.

The safety boundaries are present and machine-readable in the right places. `SECURITY.md` says Trailhead must not automatically read cookies, print secrets, dump env vars, write credentials, post, buy credits, install global packages, or mutate Hermes config. Tests cover secret non-echoing, approval-required sensitive channels, and route decisions for social/browser surfaces.

The route model is conceptually strong. `router.py` separates known URL reads, broad discovery, structured extraction, interactive browser work, social/current signal, and external tool enablement. That is the right division because each route has different risk, cost, evidence needs, and approval boundaries.

## What is weak or unfinished

The central gap is still evidence follow-through. `search --execute` can return real links across source families, but it does not yet extract/read/rank the returned pages. The README already says this; the code confirms it. Search hits are leads, not evidence. Until Trailhead can read top hits, measure extraction success, and score source quality, it remains a terrain scout rather than the full field-report product.

The second gap is source-quality scoring. Right now, a result list can include useful sources and sludge with equal weight. The project needs first-class ranking features: canonical docs, maintainer posts, GitHub issues/PRs, practitioner threads, firsthand reports, recency when relevant, and penalties for SEO/listicles/empty platform shells/dead links/duplicates.

The third gap is live route scoring. `doctor --live` exists, and route objects describe health/risk conceptually, but route selection itself is still mostly keyword matching. If Redlib is down, Jina is failing, X search is credit-limited, or YouTube tooling is missing, the route should know that before promising a path.

The fourth gap is benchmark pressure. The project has good contract tests, but it needs outcome tests: real research tasks scored by link validity, extraction success, answer usefulness, caveat honesty, and whether Trailhead improved the final Hermes answer.

## Guardrails that must stay non-negotiable

1. Search result does not equal evidence. Every executed result should carry `evidence_state`. Discovery-only lanes must say so.
2. Weak lane honesty beats fake coverage. TikTok, Instagram, and X must distinguish public link discovery from readable platform content.
3. Approval boundaries are data, not prose. Cookies, account sessions, paid APIs, posting, global installs, credential writes, and Hermes config mutation must be marked approval-required in machine-readable output.
4. Upstream tools first. Trailhead routes to mature tools; it does not build bespoke scrapers unless no proven route exists and the reason is documented.
5. Free-first, not free-only. Paid APIs and account sessions are allowed only as explicit escalations, never the default promise.
6. Product mission filters features. If a feature does not improve source terrain choice, route choice, evidence retrieval, source-quality judgment, or blind-spot reporting, it does not belong.
7. No workspace pollution. Agent-Reach’s install docs are right here: external capability tools need sandbox/venv/tmp/home-owned locations, not random project-directory installs.
8. No public action surfaces by default. Trailhead is read-only; posting/commenting/liking/following is out of scope unless a human explicitly approves a separate workflow.

## Immediate build direction

P0 should be evidence follow-through and source-quality scoring together, not separately. The product wants a field report, so the next command should look like:

```bash
python3 -m hermes_trailhead search all "query" --execute --extract --limit 3 --format json
```

The output should include per-hit extraction attempted/succeeded/failed, usable text length, source type, source-quality score, why it was ranked, and a caveat when only discovery was possible.

P1 should be live route scoring: `route` and `search` should optionally consume live channel health and change recommendations accordingly.

P2 should be benchmarks: a fixed set of real research tasks with expected evidence classes and scoring for link validity, extraction success, ranking quality, and caveat honesty.

## Audit accounting

Local sources read:

- `README.md`
- `NOTICE.md`
- `SECURITY.md`
- `docs/boss-architecture.md`
- `hermes_trailhead/search.py`
- `hermes_trailhead/router.py`
- `hermes_trailhead/channels.py`
- `hermes_trailhead/cli.py`
- `hermes_trailhead/formatters.py`
- `tests/test_search.py`
- `tests/test_contracts.py`

Primary external sources extracted:

- `https://github.com/Panniantong/Agent-Reach`
- `https://raw.githubusercontent.com/Panniantong/Agent-Reach/main/README.md`
- `https://raw.githubusercontent.com/Panniantong/Agent-Reach/main/docs/install.md`
- `https://raw.githubusercontent.com/Panniantong/Agent-Reach/main/docs/update.md`

Commands run:

```bash
python3 -m py_compile hermes_trailhead/*.py
python3 -m pytest -q
python3 -m hermes_trailhead route 'current maintainer discussion on x reddit github about Hermes Agent' --format json
python3 -m hermes_trailhead search all 'Hermes Agent discussion' --execute --limit 1 --format json
```

Verification before this audit patch: 46 tests passed. The live search smoke showed the coverage-theater risk directly: TikTok/Instagram returned public links and `status=ok`, but those lanes are still discovery-only and approval-sensitive. The code now preserves that distinction in execution output.
