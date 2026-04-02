# ~~Claude Code~~ <sup><ins>`goblin mode`</ins></sup>

![Goblin Mode](D6C1BA70-D6CD-40A0-8134-1DFED56D5A4D.png)

> [!CAUTION]
> 50% useful tool/teaching resource for agentic coding, 50% externalised temper tantrum.

**Goblin Mode** is a permanently-in-flux configuration system (skills[^1], agents, hooks) built by one developer to solve problems they actually had. Every skill traces back to a specific friction point. Hooks enforce habits that were being skipped.

[^1]: Skills replaced slash commands after Anthropic merged the two systems.

- **Weakness-aware design:** Testing is a known weakness, so a dedicated skill encodes the discipline. ADHD makes executive function unreliable, so hooks enforce it instead of relying on willpower.
- **Context window discipline:** CLAUDE.md loads every session. Skill descriptions load at start; bodies lazy-load on trigger. Agents run in sub-processes. Every layer has a deliberate cost.
- **Model tier thinking:** Skills specify whether they need Haiku (fast, cheap), Sonnet (balanced), or Opus (thorough). Not every task needs the biggest model.
- **Friction-driven, not architecture-driven:** This grew organically from actual work. The process of building it is what's transferable, not the specifics.

> [!NOTE]
> This setup is specific to one developer's workflow (and brain). If you're building your own, the **process** is what's transferable; the specifics should be yours.
>
> For the full story on how and why this was built, see [How to Use This Repo](docs/guides/HOW-TO-USE-THIS-REPO.md).

---

## Table of Contents

- [What's In Here](#whats-in-here)
- [Quick Start](#quick-start)
- [Directory Guide](#directory-guide)
  - [CLAUDE.md: The Behaviour File](#claudemd-the-behaviour-file)
  - [Skills: Commands and Domain Knowledge](#skills-commands-and-domain-knowledge)
  - [Agents: Autonomous Workflows](#agents-autonomous-workflows)
  - [Hooks: Automation](#hooks-automation)
  - [Docs: Documentation](#docs-documentation)
- [How It All Fits Together](#how-it-all-fits-together)
- [Key Concepts](#key-concepts)
- [Documentation Index](#documentation-index)

---

## What's In Here

| Component | Count | What it does |
|-----------|-------|-------------|
| **Skills (command)** | 49 | Slash commands you invoke (e.g. `/git:commit-one-delta`) |
| **Skills (knowledge)** | 17 | Knowledge packs that load automatically when relevant |
| **Agents** | 10 | Autonomous sub-processes for multi-step work |
| **Hooks** | 7 | Scripts that run on git events and session lifecycle |
| **Docs** | 2 files | Guides for this repo |

---

## Quick Start

If you've cloned this and want to understand what you're looking at:

1. **Read [CLAUDE.md](CLAUDE.md):** the main behaviour file — tells Claude how to write code, format commits, and communicate.
2. **Browse [skills/README.md](skills/README.md):** full index of available commands.
3. **Read [How to Use This Repo](docs/guides/HOW-TO-USE-THIS-REPO.md):** explains every directory and the thinking behind each one.

If you're new to Claude Code customisation entirely, start with the [How to Use This Repo](docs/guides/HOW-TO-USE-THIS-REPO.md) guide.

---

## Directory Guide

### `CLAUDE.md`: The Behaviour File

The single most important file. Loaded into every Claude Code session and defines:

- **Technical profile:** languages, frameworks, preferred tools
- **Communication rules:** British English, no sycophancy, direct answers
- **Code conventions:** tabs for indentation, naming patterns, TypeScript strict mode
- **Git workflow:** conventional commits, branch naming, PR structure
- **Security defaults:** no committed secrets, input validation, RLS

Think of it as "if I had to brief a new developer on how I work, what would I say?"

### `skills/`: Commands and Domain Knowledge

Skills serve two distinct roles:

**Command skills** (49) — you invoke these by typing `/skill-name` in Claude Code. Each has a model tier in its name:

| Tier | Model | Best for |
|------|-------|----------|
| `delta` | Haiku | Fast, routine tasks |
| `gamma` | Sonnet | Balanced reasoning |
| `omega` | Opus | Complex analysis |

Categories: git, PR, doc, linear, merge, repo, review, suggest-task, wip, config, do.

**Knowledge skills** (17) — Claude loads these automatically when it detects relevant keywords in your conversation. Mentioning "Svelte" triggers `svelte-ninja`; mentioning "Neo4j" triggers `cypher-linguist`. You never invoke them directly.

Only the skill's short description loads at session start (cheap on context). The full knowledge pack loads on demand.

### `agents/`: Autonomous Workflows

Agents are **sub-processes** that Claude spawns to handle multi-step work independently:

| Agent | Purpose |
|-------|---------|
| `design-reviewer` | Review proposed features against design values before implementation |
| `implementation-planner` | Break vague development requests into actionable plans |
| `project-context-loader` | Rebuild mental context when switching between projects |
| `roadmap-maintainer` | Keep documentation and roadmaps in sync with code changes |
| `scope-guard` | Detect and flag scope creep before it becomes entrenched |
| `session-closer` | Capture session state, update task tracker, write handoff note |
| `session-orchestrator` | Build a work plan at session start from git history and priorities |
| `ship-checker` | Multi-dimensional quality check before creating a PR |
| `task-sync` | Keep Linear/GitHub Issues consistent with git and branch state |
| `test-gap-scanner` | Identify untested code using risk-based prioritisation |

They run in their own context window, so they don't clutter your main conversation.

### `hooks/`: Automation

Scripts that run automatically on git events and session lifecycle:

| Hook | Trigger | What it does |
|------|---------|-------------|
| `pre-push.zsh` | Before push | Orchestrator; guards which repos run the full chain |
| `pre-push-tests.zsh` | Before push | Detects untested files; runs test suite |
| `pre-push-evidence.zsh` | Before push | Extracts apprenticeship KSB portfolio evidence from commits |
| `post-commit-docs.zsh` | After commit | Checks if changed files need documentation updates |
| `settings-sync.sh` | Session start | Strips JSONC comments from settings source of truth → settings.local.json |
| `session-start-worktree.sh` | Session start | Injects worktree context into the session environment |
| `stop-uncommitted-check.sh` | Stop | Warns about uncommitted changes when Claude finishes responding |

The `pre-push.*` hooks are specific to an apprenticeship workflow; they enforce habits that are easy to forget (running tests, tracking evidence, updating docs). The `settings-sync.sh` hook is what makes the `.jsonc` → `.json` source-of-truth approach work.

### `docs/`: Documentation

Guides for this repo. See the [Documentation Index](#documentation-index) below.

---

## How It All Fits Together

```
You type something in Claude Code
        │
        ├─ Keywords detected? ──→ Knowledge skill loads automatically
        │
        ├─ You type /skill-name? ──→ Command skill runs a defined workflow
        │
        ├─ Skill or Claude spawns agent? ──→ Agent works autonomously
        │
        └─ You push code? ──→ Hooks run checks and extraction

Meanwhile, CLAUDE.md shapes every response throughout.
```

The key insight: **CLAUDE.md is always active**, knowledge skills activate on context, command skills activate on demand, and hooks activate on git and session events. Each layer has a different trigger and a different cost to your context window.

---

## Key Concepts

**Context window cost:** Everything Claude reads uses up its working memory. This setup is designed to be efficient: only descriptions load upfront, full content loads on demand. If you're building your own, this matters more than you'd think.

**Model tiers:** Not every task needs the most powerful model. Haiku is fast and cheap for routine work. Opus is thorough but slower and more expensive. The tier system makes this choice explicit.

**Organic growth:** None of this was planned upfront. Every skill and hook traces back to a specific problem that came up during actual work. If you're building your own setup, start with one friction point and go from there.

For more on these ideas: [How to Use This Repo](docs/guides/HOW-TO-USE-THIS-REPO.md)

---

## Documentation Index

### Guides
| File | Description |
|------|-------------|
| [How to Use This Repo](docs/guides/HOW-TO-USE-THIS-REPO.md) | Comprehensive guide to the entire setup; start here |
| [Agent Workflow Design](docs/guides/agent-workflow-design.md) | Design notes for the agent-based workflow patterns |
