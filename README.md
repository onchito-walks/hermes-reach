# Hermes Reach

Hermes Reach is a small control plane for agent capabilities.

It answers one question:

> For this task, what should the agent use, what should it avoid, what needs approval, and what evidence proves the job worked?

It is built for [Hermes Agent](https://hermes-agent.nousresearch.com/docs), but the idea is general: agents should not blindly install tools, scrape cookies, post to accounts, or guess which search/browser/crawler path is safe. They should route the task through a simple policy layer first.

## Why it exists

Modern agents have too many ways to touch the internet:

- search APIs
- page readers
- crawlers
- browser automation
- hosted browser sessions
- MCP servers
- SaaS integration platforms
- social frontends
- local CLIs

Raw access is not the hard part anymore. The hard part is **choosing the right surface safely**.

Hermes Reach keeps that choice explicit.

## What it does

Hermes Reach has three jobs:

1. **Diagnose** what capabilities are available.
2. **Route** each task to the safest useful tool path.
3. **State the proof** required before the agent can claim success.

It does not try to be every crawler, browser, or integration platform. It tells the agent when to use one.

## Install

From a checkout:

```bash
python3 -m pytest -q
python3 -m hermes_reach doctor
```

Editable install:

```bash
uv venv .venv
. .venv/bin/activate
uv pip install -e .
hermes-reach doctor
```

## Core commands

```bash
# Check capability health with evidence
python3 -m hermes_reach doctor
python3 -m hermes_reach doctor --format json

# Show prioritized gaps
python3 -m hermes_reach queue
python3 -m hermes_reach queue --risk high --top 3

# Ask the router what path a task should use
python3 -m hermes_reach route "read this known url as markdown"
python3 -m hermes_reach route "login to a site and fill a form"
python3 -m hermes_reach route "extract schema from website"

# List all routing rules
python3 -m hermes_reach routes

# Emit an agent-facing brief
python3 -m hermes_reach agent-brief

# Print a safe setup plan for one channel
python3 -m hermes_reach plan x-search
```

## Example

```bash
python3 -m hermes_reach route "login to a site and fill a form"
```

Output:

```text
# Hermes Reach route: interactive-browser

Task: Login/session/form/visual browser work
Primary: Hermes browser tools for live supervised actions
Fallbacks: Browserbase contexts, Stagehand act/observe/extract/agent, browser-use for autonomous browser tasks
Avoid: headless scraping of logged-in sites without consent, cookie extraction as a default
Approval required: yes

Evidence required before claiming success:
- target site
- account boundary
- allowed actions
- screenshot/log proof
```

That is the product: simple routing, visible boundaries, clear evidence.

## Architecture

Hermes Reach is intentionally boring.

```text
Task intent
   ↓
Router
   ↓
Policy + risk gate
   ↓
Capability channel
   ↓
Evidence required
```

The code is split into three pieces:

| File | Purpose |
|---|---|
| `hermes_reach/router.py` | Task-class routing rules. |
| `hermes_reach/channels.py` | Capability checks and evidence. |
| `hermes_reach/cli.py` | Human and machine-readable commands. |

The main data model is plain Python dataclasses. Output is text, Markdown, or JSON.

## Safety model

Hermes Reach is read-only by default.

It does **not** automatically:

- install global packages
- read browser cookies
- dump environment variables
- write credentials
- post to social platforms
- mutate Hermes config
- buy API credits

High-risk routes and channels are marked `approval_required` in machine-readable output.

Examples of high-risk work:

- browser sessions tied to a real account
- cookie extraction
- paid API setup
- social posting
- global installer scripts
- credential storage

## Loginless-first search

Hermes Reach prefers search paths that do not require personal logins when the task allows it:

1. Search with public or configured search surfaces.
2. Read pages with clean readers like `web_extract` or Jina Reader.
3. Use privacy frontends such as SearXNG, Nitter, Redlib, or Whoogle when appropriate.
4. Use browser automation only when the page truly needs session state or interaction.
5. Require approval before touching cookies, accounts, paid APIs, or posting surfaces.

## Prior art

Hermes Reach is not pretending to be first. It is a local control-plane take on ideas from several strong projects.

### Agent capability and MCP ecosystems

- [Agent-Reach](https://github.com/Panniantong/Agent-Reach) inspired the initial pattern: channel registry, doctor checks, and setup plans.
- [Composio](https://composio.dev/) shows the value of a broad tool catalog, managed auth, and meta-tools.
- [Pipedream Connect / MCP](https://pipedream.com/docs/connect/mcp) shows managed API integration at large scale.
- [Arcade.dev](https://docs.arcade.dev/) shows a clean split between tool catalog, runtime, and authorization.
- [Zapier MCP](https://zapier.com/mcp) shows the value of low-friction SaaS action surfaces.
- The [official MCP Registry](https://modelcontextprotocol.io/registry/about), [Glama](https://glama.ai/mcp/servers), and [PulseMCP](https://www.pulsemcp.com/servers) show the discovery/catalog side of the ecosystem.

### Browser, crawl, and extraction engines

Hermes Reach does not replace these tools. It routes to them when they fit.

- [Firecrawl](https://docs.firecrawl.dev/) for crawl/search/extract APIs.
- [Crawl4AI](https://docs.crawl4ai.com/) for open, deterministic crawl/extract workflows.
- [Browserbase](https://docs.browserbase.com/) for hosted browser infrastructure and persistent contexts.
- [Stagehand](https://docs.stagehand.dev/) for browser primitives like act, observe, and extract.
- [browser-use](https://github.com/browser-use/browser-use) for agentic browser automation.
- [Playwright MCP](https://github.com/microsoft/playwright-mcp) for structured browser control through MCP.
- [Jina Reader](https://jina.ai/reader/) for URL-to-markdown reading.
- [Exa](https://exa.ai/docs/reference/search) for semantic search and extraction.

### Harness and local-agent systems

Hermes Reach is also influenced by harness-first agent systems:

- [OpenClaw](https://github.com/openclaw/openclaw) and Claw-style assistants: local tools, skills, plugins, policy, and MCP boundaries.
- [MCPorter](https://github.com/openclaw/mcporter): bridging MCP servers into usable local tooling.
- [Claude Code skills, subagents, hooks, and MCP](https://docs.anthropic.com/en/docs/claude-code/overview): reusable workflows, isolated agents, and policy hooks.
- [OpenAI Codex CLI](https://github.com/openai/codex): terminal-native coding-agent harnessing.
- [gstack](https://github.com/garrytan/gstack): skill-driven software workflows and review loops.

The lesson from all of them is the same:

> The harness is the product. The model is only useful when the harness gives it tools, policy, memory, tests, and boundaries.

## What Hermes Reach is not

Hermes Reach is not:

- a public MCP registry
- a SaaS integration marketplace
- a browser automation framework
- a crawler
- a scraping toolkit
- a social bot
- a credential manager

It is the small local layer that decides which of those things, if any, should be used.

## Tests

```bash
python3 -m py_compile hermes_reach/*.py
python3 -m pytest -q
```

The test suite covers:

- CLI JSON contract stability
- approval gates
- no-secret-output regressions
- router decision quality
- route serialization
- queue/filter behavior
- public README safety claims

## Weekly company loop

A healthy capability control plane needs maintenance. The intended weekly loop is:

1. Run tests.
2. Check for bugs and security regressions.
3. Review state-of-the-art changes in agent harnesses, MCP registries, crawlers, browser runtimes, and loginless search.
4. Open issues for concrete improvements.
5. Update docs when positioning or prior art changes.

## License and attribution

Hermes Reach is open source under the BSD 3-Clause License. You may use, modify, and redistribute it, but you must preserve the copyright notice and license text.

See `NOTICE.md` for prior-art acknowledgments.
