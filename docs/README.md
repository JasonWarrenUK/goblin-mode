# Documentation

The wiki for `~/.claude` — Jason's [goblin-mode](../README.md) Claude Code config. Everything here should be usable both by a human skimming for context and by an agent grepping for a fact — no page assumes you've read the others first, but they link where it helps.

## Start here

New to this repo? Read in this order:

1. [Root README](../README.md) — the pitch and the top-level map.
2. [Architecture](architecture.md) — how the layers (CLAUDE.md, skills, agents, hooks) fit together and what each costs to load.
3. Pick a reference page below for the subsystem you're touching.

Already familiar? Jump straight to a reference page — they're written to stand alone.

## Reference

Factual, per-subsystem pages. These describe what exists, not why it was built.

| Page | Covers |
|---|---|
| [Skills](reference/skills.md) | Command vs. role skills, the runic model-tier convention, `when_to_use`, the generated index |
| [Agents](reference/agents.md) | The 10 autonomous agents, the session and shipping loops |
| [Hooks](reference/hooks.md) | Global and project-level Claude Code hooks, plus the unrelated git `pre-commit` dispatcher |
| [Library](reference/library.md) | `references/`, `templates/`, `configs/examples/`, `scripts/` — the deterministic halves |
| [Task Trackers](reference/task-trackers/README.md) | Tracker-agnostic status-transition convention, plus tool-specific detail for Linear, GitHub Issues, and git-native |
| [Configuration](reference/configuration.md) | `settings.json` — model, permissions, worktree, plugins, personality knobs |

For the full generated skill list (not duplicated here), see **[skills/README.md](../skills/README.md)**.

## Guides

Discursive material — the *why*, and how to build your own version of this.

| Page | Covers |
|---|---|
| [Building Your Own](guides/building-your-own.md) | The transferable process: start with friction, layer configuration, use model tiers, grow organically |

## Design history

Provenance documents — proposals and the reasoning behind decisions, kept even after the proposal shipped.

| Page | Covers |
|---|---|
| [Agent & Workflow Design](design-history/agent-workflow-design.md) | The original case for all 10 agents; all six *new* ones proposed there have since shipped |

## Archive

Stale content kept for reference, explicitly not current.

| Page | Covers |
|---|---|
| [Iris Development Tracker](archive/iris-development-tracker.md) | Task tracker for the Iris project, last touched January 2026 |

## Reference material outside this wiki

Other top-level artefacts this wiki links out to rather than duplicates:

- [`CLAUDE.md`](../CLAUDE.md) — the behaviour file, loaded every session.
- [`skills/README.md`](../skills/README.md) — the generated skill index.
- [`output-styles/british-dev-goblin.md`](../output-styles/british-dev-goblin.md) — the tone definition.
- [`docs/glossary.md`](glossary.md) — vocabulary specific to this config.
- [`docs/personal/`](personal/) — portfolio evidence, kept separate from the technical wiki.

## Keeping this wiki honest

The last version of this documentation drifted from reality for months — README claimed 66 skills against an actual 45, pointed at directories that no longer existed, and listed a hook that had been deleted. Two things make that less likely this time:

- **Generated content stays generated.** `skills/README.md` is rebuilt from frontmatter (`python3 ~/.claude/library/scripts/gen-skills-index.py`), not hand-maintained. Counts quoted elsewhere in this wiki should match its output — if they don't, the wiki is stale, not the generator.
- **Reference pages describe current state only.** Anything speculative or historical lives under [Design history](design-history/agent-workflow-design.md) or [Archive](archive/), clearly labelled, rather than blended into the reference pages as if it were still true.

---
[Glossary](glossary.md) · [Architecture](architecture.md)
