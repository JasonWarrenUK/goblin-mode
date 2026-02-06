# Claude Code Config

A version-controlled setup for customising [Claude Code](https://docs.anthropic.com/en/docs/claude-code), Anthropic's CLI tool. This repository stores skills, agents, commands, hooks, and preferences that shape how Claude behaves during development sessions.

It's also a teaching resource. The specific choices here reflect one developer's workflow, but the patterns are transferable. Your setup should look nothing like this one — and that's the point.

## Table of Contents

- [Repository Structure](#repository-structure)
- [Directory Guide](#directory-guide)
  - [CLAUDE.md](#claudemd)
  - [.claude/](#claude)
  - [skills/](#skills)
  - [agents/](#agents)
  - [commands/](#commands)
  - [hooks/](#hooks)
  - [output-styles/](#output-styles)
  - [library/](#library)
- [How This Setup Was Built](#how-this-setup-was-built)
- [Building Your Own](#building-your-own)
  - [Start With Friction](#start-with-friction)
  - [Encode Decisions, Not Preferences](#encode-decisions-not-preferences)
  - [Layer Your Configuration](#layer-your-configuration)
  - [Use Model Tiers Deliberately](#use-model-tiers-deliberately)
  - [Version Control Everything](#version-control-everything)
  - [Let It Grow Organically](#let-it-grow-organically)

---

## Repository Structure

```
claude-code-config/
├── CLAUDE.md                     # Global behaviour & conventions
├── .claude/
│   └── settings.local.json       # Tool permissions (MCP, git)
├── agents/                       # Autonomous multi-step workflows
│   ├── project-context-loader.md
│   ├── implementation-planner.md
│   └── roadmap-maintainer.md
├── skills/                       # Domain-specific knowledge packs
│   ├── svelte-ninja/
│   ├── git-manager/
│   ├── api-designer/
│   ├── frontend-styler/
│   ├── debugging/
│   ├── systematic-debugger/
│   ├── data-ontologist/
│   ├── cypher-linguist/
│   ├── remember/
│   └── testing-obsessive/
├── commands/                     # Invocable workflow templates
│   ├── analyse/
│   ├── chore/
│   ├── doc/create/
│   ├── doc/update/
│   ├── git/
│   ├── project/
│   └── task/
├── hooks/                        # Shell scripts triggered by git events
│   ├── pre-push.zsh
│   ├── pre-push-tests.zsh
│   ├── pre-push-evidence.zsh
│   └── post-commit-docs.zsh
├── output-styles/                # Personality and tone definitions
│   └── british-dev-goblin.md
└── library/                      # Shared templates and examples
    └── configs/examples/
```

---

## Directory Guide

### CLAUDE.md

The root configuration file. Claude reads this at the start of every session. It defines:

- **Technical profile** — languages, frameworks, databases, testing preferences
- **Communication rules** — tone, spelling conventions, when to ask vs. proceed
- **Code standards** — naming, TypeScript strictness, paradigm choices
- **Git workflow** — commit format, branch naming, breaking change detection
- **Security defaults** — no secrets in code, RLS, input validation

**How I use it:** This file encodes the things I got tired of repeating. British spelling corrections, the instruction not to edit files without asking, the reminder that testing is a known weakness rather than something to pretend doesn't exist. It's accumulated over time — each section exists because its absence caused a problem at least once.

**The pattern:** CLAUDE.md is where you put the things that should be true across every project. If you find yourself correcting Claude about the same thing in different repositories, that correction belongs here.

---

### .claude/

Contains `settings.local.json`, which manages tool permissions and MCP (Model Context Protocol) server connections.

**How I use it:** Currently enables the sequential thinking MCP tool (which gives Claude a structured internal reasoning step) and pre-approves `git add` and `git commit` commands so I'm not confirming every staging operation.

**The pattern:** This is Claude Code's permission system. Anything Claude does that requires tool access — running shell commands, connecting to external services — gets gated here. Start restrictive and open permissions as you build trust with specific workflows.

---

### skills/

Each subdirectory contains a `SKILL.md` file — a self-contained knowledge pack that Claude loads when it detects relevant context. Skills are triggered automatically by keywords in conversation.

| Skill | Triggers on | Purpose |
|---|---|---|
| `svelte-ninja` | Svelte, SvelteKit, runes, $state | Svelte 5 patterns and SvelteKit conventions |
| `git-manager` | git, branch, commit, PR | Branch naming, commit conventions, conflict resolution |
| `api-designer` | API design, Zod, validation | Type-safe API contracts and error handling |
| `frontend-styler` | layout issues, CSS, styling | Debugging layout problems and style consistency |
| `debugging` | debugging mentions | Basic five-step debugging framework |
| `systematic-debugger` | bug, error, broken, DevTools | Methodical browser and Node.js debugging |
| `data-ontologist` | database design, schema, polyglot | When to use relational vs. graph vs. document databases |
| `cypher-linguist` | Neo4j, Cypher, graph queries | Cypher query language and graph patterns |
| `remember` | "remember that", "note this" | Stores preferences in CLAUDE.md files |
| `testing-obsessive` | write tests, Vitest, coverage | Risk-based testing strategy and Vitest setup |

**How I use it:** The skills reflect what I actually work with. There's a Svelte skill because that's my primary framework. There's a Neo4j/Cypher skill because I work with graph databases. There are *two* debugging skills because the first one was too shallow and I needed a more methodical version — but I kept both because they serve different moments. The `testing-obsessive` skill exists precisely because testing is a weakness; it encodes the approach I want to follow even when my instinct is to skip it.

**The pattern:** Skills should encode expertise you need but don't always have at your fingertips. They're not documentation — they're opinionated guides that tell Claude *how* to approach a domain, not just what the domain contains. A React developer would have entirely different skills here. A Python data scientist would have different skills again. The question to ask: "When I'm working in this area, what do I wish I always remembered?"

---

### agents/

Agents are autonomous multi-step workflows that Claude can delegate to. Each agent has a designated model (Sonnet for speed, Opus for depth) and a specific job.

| Agent | Model | Purpose |
|---|---|---|
| `project-context-loader` | Sonnet | Rebuild mental context when switching between projects |
| `implementation-planner` | Opus | Break vague feature requests into actionable implementation plans |
| `roadmap-maintainer` | Opus | Keep documentation and roadmaps in sync with actual code |

**How I use it:** I work across multiple projects (Iris, Rhea, Theia). The context loader exists because switching between them was painful — I'd lose track of what branch I was on, what I'd been working on, what architectural decisions I'd made. The implementation planner exists because I tend to start coding before I've thought through the full scope of a feature. The roadmap maintainer exists because documentation rots the moment you stop updating it, and I'd rather automate that discipline than rely on willpower.

**The pattern:** Agents solve *process* problems, not *knowledge* problems. If you notice a recurring multi-step workflow where you keep forgetting steps or doing them inconsistently, that's an agent. Skills tell Claude what to know; agents tell Claude what to *do*. Think about the workflows you dread or skip — those are your agent candidates.

---

### commands/

Invocable templates triggered with slash commands (e.g., `/doc/create/adr`). Each command specifies a model tier, accepts arguments, and defines a structured workflow.

**Categories:**

- **analyse/** — Codebase introspection: critiques, overviews, roadmap-vs-reality comparisons
- **chore/** — Maintenance tasks like version number updates across files
- **doc/create/** — Generate new documentation: ADRs, READMEs, roadmaps, work records, status reports
- **doc/update/** — Update existing docs to reflect code changes
- **git/** — Commit message generation and pull request creation
- **project/** — Initialise new projects from a template (Kamino)
- **task/** — Suggest next logical tasks or execute with minimal approach

Commands come in model tiers — `delta` (Haiku, fast/cheap), `gamma` (Sonnet, balanced), `omega` (Opus, thorough) — so the same operation can run at different levels of sophistication depending on need.

**How I use it:** The `doc/create/work-record` command generates session summaries from git history — useful for apprenticeship portfolio evidence. The `task/suggest` commands analyse my codebase against my roadmap and suggest what to work on next, which helps when I'm stuck or scattered. The `git/pull-request` command has an unusual rule: the summary must be a "non-technical, absurd metaphor." That's a deliberate choice to make PR reviews less tedious.

**The pattern:** Commands formalise the workflows you repeat. If you find yourself giving Claude the same multi-step instruction more than twice, extract it into a command. The model tier system is worth adopting — not every task needs your most expensive model. Status reports and version bumps work fine with Haiku; architectural analysis benefits from Opus.

---

### hooks/

Shell scripts (zsh) that run automatically on git events. These are symlinked into individual project `.git/hooks/` directories.

| Hook | Event | Purpose |
|---|---|---|
| `pre-push.zsh` | Before push | Orchestrator — routes to other hooks, guards with repo allowlist |
| `pre-push-tests.zsh` | Before push | Detects untested files, runs test suite, warns on gaps |
| `pre-push-evidence.zsh` | Before push | AI-driven extraction of apprenticeship portfolio evidence from commits |
| `post-commit-docs.zsh` | After commit | Checks if documentation needs updating based on changed files |

**How I use it:** The hooks enforce discipline I wouldn't maintain manually. The test hook catches untested code before it reaches the remote. The evidence hook is specific to my situation — I'm on a Software Development Apprenticeship (Level 4) and need to collect evidence of Knowledge, Skills, and Behaviours (KSBs) from my work. Rather than retrospectively hunting for evidence, the hook analyses each push and extracts it automatically. The documentation hook maps changed files to their relevant docs and prompts me to update them.

The `pre-push.zsh` orchestrator has an allowlist — only specified repositories run the full hook chain. This prevents the heavier hooks (especially the AI evidence extraction) from running on every casual project.

**The pattern:** Hooks are for discipline you know you need but won't consistently apply. The key insight is the allowlist approach: not every project needs every hook. Start with hooks that catch mistakes (tests, linting) and only add heavier automation (AI analysis, documentation checks) to projects that warrant it.

---

### output-styles/

Defines how Claude communicates — tone, verbosity, explanation strategy.

**How I use it:** The `british-dev-goblin.md` style sets a collaborative, understated tone. It tells Claude to lead with solutions, skip obvious explanations, and only go deep when there's genuine learning value. "Casual but not cringe-inducing" and "English sensibility (avoid American over-enthusiasm)" are the operative instructions.

**The pattern:** If Claude's default communication style doesn't match how you think, an output style fixes that. This isn't cosmetic — it affects how useful the responses are. Someone who learns best from detailed explanations would configure the opposite of what's here. Someone working in a team might want a more formal, documentation-oriented style.

---

### library/

Shared resources, templates, and example configurations used by commands and agents.

**How I use it:** Currently holds example config structures (like the roadmap JSON format). It's a reference directory — commands point here when they need to know what shape a configuration should take.

**The pattern:** As your setup grows, you'll accumulate reusable fragments — data structures, template formats, example configs. Rather than duplicating these across commands, centralise them. The library is the "shared code" of your configuration.

---

## How This Setup Was Built

This didn't start as a comprehensive system. It started with a `CLAUDE.md` that said "use British spelling" and a `.gitignore`.

Each addition came from a specific friction point:

1. **CLAUDE.md grew** because I kept correcting the same behaviours
2. **Skills appeared** when I noticed Claude giving generic advice in areas where I needed opinionated guidance
3. **Commands emerged** when I typed the same multi-step instructions for the third time
4. **Agents were added** when I had workflows complex enough that a single prompt couldn't capture them
5. **Hooks were written** when I realised I was forgetting to run tests before pushing (again)
6. **Output styles materialised** when the default tone felt wrong often enough to fix

The order matters. Don't start by building ten skills and five agents. Start with `CLAUDE.md` and let the rest emerge from actual need.

---

## Building Your Own

### Start With Friction

Don't configure speculatively. Wait until something annoys you, then fix it.

This setup has a Svelte skill because the developer uses Svelte. It has a Neo4j skill because the developer uses Neo4j. If you're a Django developer who works with PostgreSQL, your skills directory should reflect *that* — and it should start empty until you notice Claude giving you unhelpful Django advice.

**Exercise:** Over your next few sessions, keep a list of moments where Claude does something you immediately correct. Each correction is a candidate for `CLAUDE.md`.

### Encode Decisions, Not Preferences

There's a difference between "I prefer tabs" and "use tabs because the team standard is tabs." The first is cosmetic; the second prevents real problems.

The CLAUDE.md in this repo doesn't just say "use British spelling" — it links to a dictionary and lists specific rules (`-ise` not `-ize`, `-our` not `-or`). It doesn't just say "write good commits" — it specifies Conventional Commits format and when to flag breaking changes.

**Exercise:** For each rule you want to add, ask: "What goes wrong if Claude ignores this?" If the answer is "nothing, I just prefer it," consider whether it's worth the configuration noise.

### Layer Your Configuration

This setup uses three layers:

1. **Global** (`CLAUDE.md` at root) — true for every project
2. **Project-level** (`project/CLAUDE.md`) — overrides global for specific repositories
3. **Subsystem-level** (`project/frontend/CLAUDE.md`) — overrides project for specific areas

This means the global config can say "prefer Svelte" while a specific project's config says "this one uses React." Start with global. Add project layers only when a project genuinely diverges.

### Use Model Tiers Deliberately

Commands in this repo use three tiers:

- **Haiku** (`delta`) — fast, cheap: version bumps, work records, simple suggestions
- **Sonnet** (`gamma`) — balanced: ADRs, documentation updates, code analysis
- **Opus** (`omega`) — thorough: architectural critiques, implementation planning, roadmaps

Not every task needs Opus. If you're generating a commit message, Haiku is fine. If you're planning a database migration, you probably want Opus. The tiered approach keeps costs proportional to complexity.

### Version Control Everything

This entire directory is a git repository. That means:

- Changes to configuration are tracked and reversible
- You can see *when* a rule was added and *why* (through commit messages)
- The setup can be shared, forked, or referenced by others
- Moving to a new machine means cloning one repository

The `.gitignore` here uses an inverted pattern — it ignores everything by default and explicitly includes what should be tracked. This prevents accidentally committing Claude's cache, task history, or other ephemeral data.

### Let It Grow Organically

This repository has ten skills, three agents, and over a dozen commands. It didn't start that way, and yours shouldn't either.

**A reasonable progression:**

1. **Week 1:** Create `CLAUDE.md` with your spelling, tone, and code style preferences
2. **First month:** Add your first skill when Claude gives generic advice in your specialist area
3. **When you notice repetition:** Extract your first command from a workflow you've typed out three times
4. **When workflows get complex:** Create your first agent for a multi-step process you keep doing inconsistently
5. **When discipline slips:** Add your first hook for the check you know you should run but don't

The goal isn't a comprehensive system. The goal is a system that solves *your* actual problems, one friction point at a time.
