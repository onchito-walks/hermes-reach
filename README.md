# Hermes Reach

Hermes Reach is a Hermes-native replication of the useful Agent-Reach pattern: give the agent a durable, diagnosable map of internet-reading/searching channels without blindly installing global tools or touching browser cookies.

It is **inspired by** [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach), which is MIT licensed. This project does not vendor Agent-Reach code; it borrows the scaffold idea: channel registry, doctor checks, and agent-facing usage recipes.

## Why this exists

Hermes already has many internet surfaces:

- `web_search`
- `web_extract`
- browser tools
- GitHub MCP
- X search when xAI credits are available
- local Nitter/Redlib privacy frontends
- cron/newsletter delivery
- GBrain/session recall

The gap is not raw access. The gap is **operator clarity**: which channel should the agent use, what is currently working, and what setup is missing?

Hermes Reach answers that with:

- `hermes-reach doctor` — check configured/readable channels
- `hermes-reach queue` — show prioritized channel/setup gaps
- `hermes-reach plan <channel>` — print a safe setup plan, not execute it blindly
- `hermes-reach capability-radar` — summarize Hermes-install-vs-current-capability gaps

## Safety policy

By default Hermes Reach is read-only and diagnostic.

It does **not**:

- install global npm/pip packages automatically
- read browser cookies automatically
- write credentials
- post to social platforms
- mutate Hermes routing/config

Any setup involving cookies, credentials, paid services, or posting requires explicit human approval and should be done as a separate task.

## Quick start

```bash
cd /home/hermes/src/hermes-reach
python3 -m hermes_reach doctor
python3 -m hermes_reach queue
python3 -m hermes_reach capability-radar
python3 -m hermes_reach plan x-search
```

Optional console script after editable install:

```bash
uv venv .venv
. .venv/bin/activate
uv pip install -e .
hermes-reach doctor
```

## Channels

| Channel | Status check | Hermes-native default | Notes |
|---|---|---|---|
| Web search | Hermes tool availability / config hints | `web_search` | Current facts and broad discovery |
| Web extract | Hermes tool availability / Jina fallback | `web_extract` | Page/PDF extraction |
| GitHub | `gh auth status` and MCP presence | GitHub MCP / `gh` | Public and private repo operations |
| X/Twitter | xAI key, Nitter fallback | `x_search` then Nitter | Avoid cookie scraping unless explicitly approved |
| Reddit | Redlib/local CLI presence | Redlib / reddit-search | Avoid brittle anonymous scraping |
| YouTube | `yt-dlp` availability | install only when needed | Transcripts/media metadata |
| Hermes upstream | local Hermes git repo | `git fetch/log/diff` | Docs/opportunity watcher |
| Newsletter | cron + validator | morning brief v3 | Must include social/news + capability radar |

## Relationship to Agent-Reach

Agent-Reach is broader and more aggressive: it can install/configure many upstream CLIs and cookie-based channels. Hermes Reach is narrower and safer: it documents and diagnoses our Hermes-native stack first, then proposes setup steps for missing channels.

If we later decide to install Agent-Reach itself, do it in a sandbox first and audit the exact tools/cookie flows. Do not put cookie-heavy installers into the main Hermes profile without approval.

## License / attribution

Hermes Reach is MIT licensed. Agent-Reach is MIT licensed, Copyright (c) 2025 Agent Eyes. See `NOTICE.md`.
