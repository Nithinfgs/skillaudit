# Research notes (observed 2026-10-21)

Sources were fetched live on the date above. Star counts move quickly; treat them as snapshots.

## Signals

| Source | Observation |
|---|---|
| [GitHub Trending, weekly](https://github.com/trending?since=weekly) | Agent-skill and agent-tooling repos dominate: `anthropics/claude-plugins-official` (+5,650 stars that week), `K-Dense-AI/scientific-agent-skills` (+4,549), `mksglu/context-mode` (+3,556), `HKUDS/CLI-Anything` (+3,587), `android/skills` (+1,255), `cursor/plugins` (+2,040), `ruvnet/ruflo`, `wshobson/agents`, `stablyai/orca`, `akitaonrails/ai-memory`, `anomalyco/opencode`. |
| GitHub Search API, repos created 2026-10-07..21 sorted by stars | `wheresryan22/anatomy` (agent skill, ~18k), `Leonxlnx/earshot`, `Oldcircle/geo-sleuth`, `kajisho5/ffmpeg-skill`, `tigerless-labs/agent-memory`, `lemomo-ai/lemo-opuscar`, `Ryze-AI-Adgent/open-seo-mcp-skills`: newly created skills repos reach thousands of stars within days. |
| [Hacker News](https://hn.algolia.com/api/v1/search?tags=story&query=skills) | "Agent Skills" (agentskills.io, 544 pts), "AGENTS.md outperforms skills in our agent evals" (524), "I still prefer MCP over skills" (460), "SkillsBench" (364), "Show HN: Cq, Stack Overflow for AI coding agents" (225). |
| [agentskills.io specification](https://agentskills.io/specification) | An open format with hard limits (name <= 64 chars, description <= 1024, body < 500 lines / ~5000 tokens recommended). |
| [OWASP Agentic Skills Top 10, AST01](https://owasp.org/www-project-agentic-skills-top-10/ast01.html), [Akamai](https://www.akamai.com/blog/security/top-10-threats-related-agent-skills), [Snyk](https://snyk.io/articles/skill-md-shell-access/) | Malicious skills, hidden prompt injection and skill-selection manipulation are documented threat classes. |
| [arXiv 2607.01456](https://arxiv.org/pdf/2607.01456) | Empirical study of SKILL.md "smells", including context bloat. |

## Repositories examined (17)

anthropics/claude-plugins-official, K-Dense-AI/scientific-agent-skills, ruvnet/ruflo, android/skills, mksglu/context-mode,
heygen-com/hyperframes, cursor/plugins, HKUDS/CLI-Anything, akitaonrails/ai-memory, anomalyco/opencode, wshobson/agents,
stablyai/orca, tigerless-labs/agent-memory, Leonxlnx/earshot, kajisho5/ffmpeg-skill, wheresryan22/anatomy, Louis-CFM/coucou.

## Competitors in the linter niche

- `skills-ref` (reference validator from the agentskills project): frontmatter/naming checks only.
- [`skills_lint`](https://pub.dev/packages/skills_lint) (Dart): spec, structure and path-integrity checks; no security or token-budget analysis found.
- Smithery-listed `skill-linter` / `skill-validator`: skill-based or spec-only checkers.

None found combining spec checks with security heuristics, token budgets and cross-skill trigger-collision detection in a dependency-free CLI with SARIF output. This is based on a limited search, not an exhaustive survey.

## Opportunities scored (weights: demand 25, differentiation 20, feasibility 20, usefulness 20, maintainability 15; each 1-5)

| Idea | Demand | Diff. | Feas. | Useful | Maint. | Weighted /5 |
|---|---|---|---|---|---|---|
| **skillaudit**: lint + security audit for SKILL.md libraries | 5 | 4 | 5 | 4 | 5 | **4.60** |
| Cross-vendor agent-memory handoff format converter | 4 | 3 | 4 | 4 | 4 | 3.80 |
| Agent session cost/context profiler | 4 | 4 | 3 | 4 | 3 | 3.65 |
| CLI-to-agent-tool wrapper generator (CLI-Anything-style) | 4 | 2 | 3 | 3 | 3 | 3.05 |
| Local MCP server permission scanner | 3 | 4 | 3 | 4 | 3 | 3.40 |

Weighted = sum(score x weight) / 100. Scores are the author's judgement, not measurements.
