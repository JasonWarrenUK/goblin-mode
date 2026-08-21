← [Wiki home](../../README.md) · [Configuration](../configuration.md)

# Task Trackers

`~/.claude` is tracker-agnostic — it makes no assumption about which project-management tool (if any) a given project uses. `task-sync` and the agents that depend on it (`session-orchestrator`, `session-closer`, `ship-checker`) detect whichever source is available and adapt, rather than hardcoding one vendor.

This directory holds the tool-specific detail each source needs — status-transition mapping, issue-matching rules, orphan detection — kept out of the agent files themselves so those stay readable and portable regardless of which tool a project actually uses.

## The shared convention

Whichever source is active, the same status-transition shape applies:

| Git event | Task status |
|---|---|
| Branch checked out matching a task | **In Progress** |
| PR created referencing the task | **In Review** |
| PR merged to main | **Done** (with confirmation — never automatic) |
| Branch with no recent commits | **Stale** (flagged, not changed) |

Never mark a task "Done" without explicit confirmation, even when running as a subagent. Never create tasks automatically — only suggest creation. See [CLAUDE.md §6.1](../../../CLAUDE.md) for how this is declared at the project level.

## Sources

| Source | Detection | Doc |
|---|---|---|
| **Linear** | Explicit `taskSource: linear` config, Linear CLI present, or Linear issue IDs in branch names/commits | [linear.md](linear.md) |
| **GitHub Issues** | Explicit `taskSource: github` config, or a GitHub remote with issues | [github-issues.md](github-issues.md) |
| **git-native** | Always available — the fallback when no external tracker is configured or detected | [git-native.md](git-native.md) |

## Detection order

1. **Explicit config** — a project's `CLAUDE.md` can declare `taskSource: linear` / `taskSource: github` / `taskSource: git` to skip auto-detection entirely.
2. **Auto-detection** — checked in the order above (Linear → GitHub Issues → git-native) when no explicit config exists. The first available source wins; git-native is always available as the final fallback since it needs no external tool.

`task-sync` reports which source is active at the start of every output, so it's never ambiguous which convention is in play.

---
← [Wiki home](../../README.md) · [Agents](../agents.md)
