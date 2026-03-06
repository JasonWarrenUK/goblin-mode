![Goblin Mode](D6C1BA70-D6CD-40A0-8134-1DFED56D5A4D.png)

This repo is what happens when you stop correcting Claude about the same things and start encoding your entire brain into configuration files instead.

**Goblin Mode** is a working configuration system — 50+ slash commands, 12 passive skills, 3 autonomous agents, git hooks — built by one developer to solve problems they actually had. Nothing here was designed speculatively. Every command traces back to a specific friction point. Every hook enforces a habit that was being skipped. The apprenticeship evidence extraction exists because retrospective portfolio building is miserable and nobody does it voluntarily.

What makes this different:

- **Weakness-aware design** — Testing is a known weakness, so a dedicated skill encodes the discipline. ADHD makes executive function unreliable, so hooks enforce it instead of relying on willpower.
- **Context window discipline** — CLAUDE.md loads every session. Skill descriptions load at start; bodies lazy-load on trigger. Commands load on invocation. Agents run in sub-processes. Every layer has a deliberate cost.
- **Model tier thinking** — Commands specify whether they need Haiku (fast, cheap), Sonnet (balanced), or Opus (thorough). Not every task needs the biggest model.
- **Friction-driven, not architecture-driven** — This grew organically from actual work. The process of building it is what's transferable, not the specifics.

> [!NOTE]
> This setup is specific to one developer's workflow (and brain). It's shared as a working example, not a template to copy wholesale. If you're building your own, the **process** is what's transferable — the specifics should be yours.
>
> For the full story on how and why this was built, see [How to Use This Repo](docs/guides/HOW-TO-USE-THIS-REPO.md).

---

## Table of Contents

- [What's In Here](#whats-in-here)
- [Quick Start](#quick-start)
- [Directory Guide](#directory-guide)
  - [CLAUDE.md — The Behaviour File](#claudemd--the-behaviour-file)
  - [Commands — Slash Commands](#commands--slash-commands)
  - [Skills — Domain Knowledge](#skills--domain-knowledge)
  - [Agents — Autonomous Workflows](#agents--autonomous-workflows)
  - [Hooks — Git Automation](#hooks--git-automation)
  - [Docs — Documentation](#docs--documentation)
- [How It All Fits Together](#how-it-all-fits-together)
- [Key Concepts](#key-concepts)
- [Documentation Index](#documentation-index)

---

## What's In Here

At a glance:

| Component | Count | What it does |
|-----------|-------|-------------|
| **Commands** | 50+ | Slash commands you type (e.g. `/git:commit:one:delta`) |
| **Skills** | 12 | Knowledge packs that load automatically when relevant |
| **Agents** | 3 | Autonomous sub-processes for multi-step work |
| **Hooks** | 4 | Shell scripts that run on git events (push, commit) |
| **Docs** | 18 files | Guides, references, and workflow documentation |

---

## Quick Start

If you've cloned this and want to understand what you're looking at:

1. **Read [CLAUDE.md](CLAUDE.md)** — this is the main behaviour file. It tells Claude how to write code, format commits, and communicate.
2. **Browse [commands/README.md](commands/README.md)** — the full index of slash commands, organised by category.
3. **Read [How to Use This Repo](docs/guides/HOW-TO-USE-THIS-REPO.md)** — the comprehensive guide that explains every directory and the thinking behind each one.

If you're new to Claude Code customisation entirely, start with the [How to Use This Repo](docs/guides/HOW-TO-USE-THIS-REPO.md) guide. It assumes no prior knowledge of configuration beyond basic Claude Code usage.

---

## Directory Guide

### `CLAUDE.md` — The Behaviour File

The single most important file. This is loaded into every Claude Code session and defines:

- **Technical profile** — languages, frameworks, preferred tools
- **Communication rules** — British English, no sycophancy, direct answers
- **Code conventions** — tabs for indentation, naming patterns, TypeScript strict mode
- **Git workflow** — conventional commits, branch naming, PR structure
- **Security defaults** — no committed secrets, input validation, RLS

Think of it as "if I had to brief a new developer on how I work, what would I say?"

### `commands/` — Slash Commands

Commands are workflows you invoke explicitly by typing `/command-name` in Claude Code. There are 50+ of them across 8 categories:

- **Codebase** — analyse, critique, investigate a project
- **Documentation** — create READMEs, roadmaps, ADRs, work records
- **Git** — commits, PRs, branch management, rebasing
- **Linear** — issue creation, task management, dependency tracking
- **Suggest** — "what should I work on next?"
- **Do** — "just do this thing, minimally"

Each command filename ends with a **model tier** (`delta`, `gamma`, `omega`) that signals which Claude model it's designed for:

| Tier | Model | Best for |
|------|-------|----------|
| `delta` | Haiku | Fast, routine tasks |
| `gamma` | Sonnet | Balanced reasoning |
| `omega` | Opus | Complex analysis |

Full reference: [commands/README.md](commands/README.md)

### `skills/` — Domain Knowledge

Skills are **passive** — you don't invoke them directly. Claude loads them automatically when it detects relevant keywords in your conversation. For example, mentioning "Svelte" triggers the `svelte-ninja` skill, which loads Svelte 5 patterns and SvelteKit conventions.

Current skills cover: Svelte, Git, API design, CSS/styling, debugging, databases (SQL + graph), testing, and a few others.

Only the skill's short description loads at session start (cheap on context). The full knowledge pack loads on demand.

### `agents/` — Autonomous Workflows

Agents are **sub-processes** that Claude spawns to handle multi-step work independently:

| Agent | Purpose |
|-------|---------|
| `project-context-loader` | Rebuilds mental context when switching between projects |
| `implementation-planner` | Breaks vague feature requests into actionable plans |
| `roadmap-maintainer` | Keeps documentation and roadmaps in sync with code changes |

They run in their own context window, so they don't clutter your main conversation.

### `hooks/` — Git Automation

Shell scripts that run automatically on git events:

| Hook | Trigger | What it does |
|------|---------|-------------|
| `pre-push.zsh` | Before push | Routes to other hooks; guards which repos run the full chain |
| `pre-push-tests.zsh` | Before push | Detects untested files; runs test suite |
| `pre-push-evidence.zsh` | Before push | Extracts apprenticeship portfolio evidence from commits |
| `post-commit-docs.zsh` | After commit | Checks if changed files need documentation updates |

These are specific to an apprenticeship workflow — they enforce habits that are easy to forget (running tests, tracking evidence, updating docs).

### `docs/` — Documentation

Guides, references, and workflow documentation. See the [full index](#documentation-index) below.

---

## How It All Fits Together

```
You type something in Claude Code
        │
        ├─ Keywords detected? ──→ Skill loads automatically
        │
        ├─ You type /command? ──→ Command runs a defined workflow
        │
        ├─ Command spawns agent? ──→ Agent works autonomously
        │
        └─ You push code? ──→ Hooks run checks and extraction

Meanwhile, CLAUDE.md shapes every response throughout.
```

The key insight: **CLAUDE.md is always active**, skills activate on context, commands activate on demand, and hooks activate on git events. Each layer has a different trigger and a different cost to your context window.

---

## Key Concepts

**Context window cost** — Everything Claude reads uses up its working memory. This setup is designed to be efficient: only descriptions load upfront, full content loads on demand. If you're building your own, this matters more than you'd think.

**Model tiers** — Not every task needs the most powerful model. Haiku is fast and cheap for routine work. Opus is thorough but slower and more expensive. The tier system makes this choice explicit.

**Organic growth** — None of this was planned upfront. Every command, skill, and hook traces back to a specific problem that came up during actual work. If you're building your own setup, start with one friction point and go from there.

For more on these ideas: [How to Use This Repo](docs/guides/HOW-TO-USE-THIS-REPO.md)

---

## Documentation Index

### Guides
| File | Description |
|------|-------------|
| [How to Use This Repo](docs/guides/HOW-TO-USE-THIS-REPO.md) | Comprehensive guide to the entire setup — start here |

### Setup & Configuration
| File | Description |
|------|-------------|
| [CLI Tools Quick Reference](docs/setup/cli-tools-quick-reference.md) | Single-page cheat sheet for daily workflows |
| [CLI Tools Usage Guide](docs/setup/cli-tools-usage-guide.md) | Detailed guide for CLI tools |
| [Doc Commands Reference](docs/setup/doc-commands-reference.md) | Quick reference for `/doc/*` commands |
| [Git Branch Naming](docs/setup/git-branch-naming-conventions.md) | Branch naming prefix guide |
| [Git Configuration](docs/setup/git-configuration-documentation.md) | Git setup documentation |
| [Claude Config Analysis](docs/setup/claude-config-analysis.md) | Complete audit of the `~/.claude/` structure |
| [iTerm2 Setup](docs/setup/iterm2-setup-guide.md) | iTerm2 terminal configuration |
| [Terminal Setup](docs/setup/terminal-setup-documentation.md) | Terminal setup and configuration |

### Workflows
| File | Description |
|------|-------------|
| [Debugging Patterns](docs/workflows/debugging-workflow-patterns.md) | Systematic debugging approaches |
| [Documentation Strategy](docs/workflows/documentation-workflow-strategy.md) | Documentation creation and maintenance workflow |

### Portfolio & Apprenticeship
| File | Description |
|------|-------------|
| [Evidence Tracker](docs/portfolio/evidence-tracker.md) | KSB evidence tracking for apprenticeship |
| [Weekly Review Template](docs/portfolio/weekly-portfolio-review-template.md) | Structured weekly portfolio documentation |
| [Dev Environment Audit](docs/portfolio/dev-environment-audit.md) | Systematic review of development environment |
| [Audit Overview](docs/portfolio/audit-overview-for-manager.md) | Environment audit formatted for manager review |
| [Audit Demo Script](docs/portfolio/audit-demo-script.md) | 15-minute demo script for environment audit |

### Projects
| File | Description |
|------|-------------|
| [Iris Development Tracker](docs/projects/iris-development-tracker.md) | Development tasks for the Iris project |
