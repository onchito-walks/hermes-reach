# Notices

Hermes Reach is inspired by Agent-Reach:

- Repository: https://github.com/Panniantong/Agent-Reach
- License: MIT
- Copyright notice in upstream license: Copyright (c) 2025 Agent Eyes
- Upstream commit inspected during creation: `71b85f8 docs(readme): clarify browser action boundary`

Agent-Reach's useful architectural pattern is:

1. Maintain a registry of internet channels.
2. Prefer existing mature CLIs/MCP servers over custom scraping.
3. Provide a doctor command that tells the agent what works and what does not.
4. Provide agent-facing instructions so future agents use the right tool path.

Hermes Reach reimplements that pattern for this Hermes installation with a stricter safety posture: diagnostics and setup plans first; no automatic global installs, cookie extraction, credential writes, or posting.
