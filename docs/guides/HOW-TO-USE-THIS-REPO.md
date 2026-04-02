# Claude Code Config

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) is Anthropic's command-line tool for working with Claude. Out of the box it's useful, but you can customise how it behaves — what it knows about your tech stack, how it writes commit messages, what checks it runs before pushing code.

If you're new to Claude Code, [this cheat sheet](https://medium.com/@tonimaxx/the-ultimate-claude-code-cheat-sheet-your-complete-command-reference-f9796013ea50) is a good starting point. This README assumes you've used it at least a few times and are wondering how to make it work better for you.

> [!IMPORTANT]
> The specific choices here reflect my particular workflow, and a lot of my approach is shaped by <strike><i>being three goblins stood on each other's shoulders in a man suit</i></strike> having ADHD... but the process of building it is completely transferable. Your setup should look nothing like this one.

<details>
<summary><h2>Table of Contents</h2></summary>

- [Repository Structure](#repository-structure)
- [Directory Guide](#directory-guide)
  - [CLAUDE.md](#claudemd)
  - [.claude/](#claude)
  - [skills/](#skills)
  - [agents/](#agents)
  - [hooks/](#hooks)
  - [output-styles/](#output-styles)
  - [library/](#library)
- [Skills vs Agents](#skills-vs-agents)
- [How This Setup Was Built](#how-this-setup-was-built)
- [Building Your Own](#building-your-own)
  - [Respect the Context Window](#respect-the-context-window)
  - [Start With Friction](#start-with-friction)
  - [Encode Decisions, Not Preferences](#encode-decisions-not-preferences)
  - [Layer Your Configuration](#layer-your-configuration)
  - [Use Model Tiers Deliberately](#use-model-tiers-deliberately)
  - [Version Control Everything](#version-control-everything)
  - [Let It Grow Organically](#let-it-grow-organically)
</details>

<details>
<summary><h2>Repository Structure</h2></summary>

```
claude-code-config/
├── CLAUDE.md                     # Global behaviour & conventions
├── .claude/
│   ├── settings.local.jsonc      # Tool permissions source of truth (JSONC)
│   └── hooks/
│       ├── session-start.sh      # Project context detection (remote sessions)
│       └── session-start-local.sh
├── agents/                       # Autonomous multi-step workflows (10)
│   ├── design-reviewer.md
│   ├── implementation-planner.md
│   ├── project-context-loader.md
│   ├── roadmap-maintainer.md
│   ├── scope-guard.md
│   ├── session-closer.md
│   ├── session-orchestrator.md
│   ├── ship-checker.md
│   ├── task-sync.md
│   └── test-gap-scanner.md
├── skills/                       # Domain knowledge + invocable commands (66)
│   ├── svelte-ninja/             # Knowledge skill (passive)
│   ├── git-manager/              # Knowledge skill (passive)
│   ├── testing-obsessive/        # Knowledge skill (passive)
│   ├── git-commit-one-delta/     # Command skill (invocable)
│   ├── pr-shiny-main-gamma/      # Command skill (invocable)
│   ├── doc-create-roadmap-omega/ # Command skill (invocable)
│   └── ...                       # 60 more
├── hooks/                        # Shell scripts triggered by git/session events
│   ├── pre-push.zsh
│   ├── pre-push-tests.zsh
│   ├── pre-push-evidence.zsh
│   ├── post-commit-docs.zsh
│   ├── settings-sync.sh
│   ├── session-start-worktree.sh
│   └── stop-uncommitted-check.sh
├── output-styles/                # Personality and tone definitions
│   └── british-dev-goblin.md
└── library/                      # Shared templates, examples, and references
    ├── configs/examples/
    │   └── roadmaps.jsonc
    ├── docs/
    │   ├── reasonable-colors-reference.md
    │   ├── examples/
    │   │   └── mvp.md
    │   └── templates/
    │       ├── ADR.md
    │       ├── api-reference.md
    │       ├── feature-spec.md
    │       ├── roadmap.md
    │       ├── status-report.md
    │       ├── technical-overview.md
    │       └── work-record.md
```
</details>

---

## Directory Guide

### CLAUDE.md

The root configuration file. Claude reads this at the start of every session. It defines:

- **Technical profile** — languages, frameworks, databases, testing preferences
- **Communication rules** — tone, spelling conventions, when to ask vs. proceed
- **Code standards** — naming, TypeScript strictness, paradigm choices
- **Git workflow** — commit format, branch naming, breaking change detection
- **Security defaults** — no secrets in code, RLS, input validation

<details>
    <summary><strong>How I use it</strong></summary>
    This file encodes the things I got tired of repeating. British spelling corrections, the instruction not to edit files without asking, the reminder that testing is a known weakness rather than something to pretend doesn't exist. It's accumulated over time — each section exists because its absence caused a problem at least once.
</details>

<details>
    <summary><strong>The pattern</strong></summary>
    CLAUDE.md is where you put the things that should be true across every project. If you find yourself correcting Claude about the same thing in different repositories, that correction belongs here.
</details>

---

### .claude/

Contains `settings.local.jsonc` (the source of truth for tool permissions) and `hooks/` (project-level hook scripts). The `settings-sync.sh` hook strips JSONC comments and writes `settings.local.json` at session start — edit the `.jsonc`, not the `.json`.

<details>
    <summary><strong>How I use it</strong></summary>
    Enables the sequential thinking MCP tool and pre-approves common git commands, read operations, and package manager commands so I'm not confirming every routine operation. The project-level hooks detect framework, package manager, and test runner at session start in remote (web) sessions.
</details>

<details>
    <summary><strong>The pattern</strong></summary>
    This is Claude Code's permission system. Anything Claude does that requires tool access gets gated here. Start restrictive and open permissions as you build trust with specific workflows.
</details>

---

### skills/

Skills serve two distinct roles. The architecture has evolved: what were formerly slash commands in a separate `commands/` directory have been merged into skills. All 66 skills live in `skills/<name>/SKILL.md`.

**Context cost:** At session start, only each skill's description (from the YAML frontmatter) loads into context. The full skill body loads only when triggered or invoked. The idle cost of 66 skills is modest; the active cost can be significant if multiple knowledge skills trigger simultaneously.

#### Knowledge Skills (17 — passive)

These load automatically when Claude detects relevant keywords in conversation. You don't invoke them.

| Skill | Triggers on | Purpose |
|---|---|---|
| `api-designer` | API design, Zod, validation | Type-safe API contracts and error handling |
| `cypher-linguist` | Neo4j, Cypher, graph queries | Cypher query language and graph patterns |
| `data-ontologist` | database design, schema, polyglot | When to use relational vs. graph vs. document |
| `debugging` | debugging mentions | Five-step debugging framework |
| `domain-modeller` | domain model, entities, DDD | Model-first design before writing code |
| `ethics-reviewer` | user-facing features, manipulation, privacy | Passive ethical review |
| `frontend-styler` | layout issues, CSS, styling | Debugging layout and style consistency |
| `git-manager` | git, branch, commit, PR | Branch naming, commit conventions, conflict resolution |
| `opentui-operative` | @opentui/core, terminal UI, Yoga | OpenTUI terminal UI library reference |
| `roadmap-interviewer` | interview, roadmap planning | Structured interview to discover new features |
| `roadmap-task-adder` | add task, roadmap task | Add tasks to roadmaps with correct ID and dependency wiring |
| `scope-coach` | scope, requirements | Anti-scope-creep questioning |
| `svelte-ninja` | Svelte, SvelteKit, runes, $state | Svelte 5 patterns and SvelteKit conventions |
| `testing-obsessive` | write tests, Vitest, coverage | Risk-based testing strategy and Vitest setup |
| `user-empathy-lens` | user experience, empathy, design | Empathy-driven design thinking |
| `whats-new` | summary, what changed | Summarise what the user can now do that they couldn't before |
| `writing-style` | prose, documentation, report | Writing style guide for Jason Warren |

#### Command Skills (49 — invocable)

You invoke these by typing `/skill-name` in Claude Code. Each name encodes a model tier:

| Tier suffix | Model | Best for |
|---|---|---|
| `delta` | Haiku | Fast, routine tasks |
| `gamma` | Sonnet | Balanced reasoning |
| `omega` | Opus | Complex analysis |

**Categories:** `git`, `pr`, `doc`, `linear`, `merge`, `repo`, `review`, `suggest-task`, `wip`, `config`, `do`

Some categories offer multiple tiers for the same operation (`suggest-task-delta/gamma/omega`). Others are fixed to one model — `git-commit-one-delta` is always Haiku (commit messages don't need deep reasoning); `repo-critique` is always Opus (shallow critiques aren't useful).

<details>
    <summary><strong>How I use it</strong></summary>
    The `doc-create-roadmap-omega` skill generates structured roadmaps with Mermaid dependency graphs. The `pr-shiny-main-gamma` skill creates PRs with a non-technical absurd metaphor in the summary (deliberate — makes PR reviews less tedious). The `suggest-task-omega` skill analyses the codebase against the roadmap and recommends what to work on next. The `wip-roadmap` skill gives a quick digest of development status without writing anything.
</details>

<details>
    <summary><strong>The pattern</strong></summary>
    Skills formalise the workflows you repeat. If you find yourself giving Claude the same multi-step instruction more than twice, extract it into a command skill. The model tier system is worth adopting — not every task needs your most expensive model. Status reports work fine with Haiku; architectural analysis benefits from Opus.
</details>

---

### agents/

Agents are autonomous multi-step workflows that Claude delegates to. Each agent runs in its own context window with a designated model.

**Context cost:** Agent definitions are loaded so Claude knows when to delegate, but the agent itself runs as a separate sub-process. The cost to your main session is just the description in the frontmatter — a few lines. The actual instruction set only loads into the agent's own context when it's spawned.

| Agent | Model | Purpose |
|---|---|---|
| `design-reviewer` | Opus | Review proposed features against design values before implementing |
| `implementation-planner` | Opus | Break vague feature requests into actionable implementation plans |
| `project-context-loader` | Sonnet | Rebuild mental context when switching between projects |
| `roadmap-maintainer` | Opus | Keep documentation and roadmaps in sync with actual code |
| `scope-guard` | Sonnet | Monitor scope during planning and implementation, intervene early |
| `session-closer` | Haiku | Capture session state for next time; update Linear; write handoff note |
| `session-orchestrator` | Sonnet | Build a ranked work plan at session start from git state and priorities |
| `ship-checker` | Opus | Multi-dimensional quality check before shipping: tests, docs, breaking changes |
| `task-sync` | Sonnet | Keep Linear/GitHub Issues consistent with git and branch state |
| `test-gap-scanner` | Sonnet | Identify untested code using risk-based prioritisation |

<details>
    <summary><strong>How I use it</strong></summary>
    I work across multiple projects (Iris, Rhea, Theia). The context loader exists because switching between them was painful — with ADHD, context-switching costs are steep. The session orchestrator and session closer create a session loop: start with a ranked work plan, end with a handoff note. The scope guard and design reviewer are proactive checks that fire before I've committed to an approach.
</details>

<details>
    <summary><strong>The pattern</strong></summary>
    Agents solve *process* problems, not *knowledge* problems. If you notice a recurring multi-step workflow where you keep forgetting steps or doing them inconsistently, that's an agent. Skills tell Claude what to know; agents tell Claude what to *do*. Think about the workflows you dread or skip — those are your agent candidates.
</details>

---

### hooks/

Claude Code supports hooks that trigger on a range of events — `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `SessionStart`, `Stop`, and more. Hooks can be shell commands, single-prompt LLM calls, or full sub-agents.

All seven hooks in this repository:

| Hook | Event | Purpose |
|---|---|---|
| `pre-push.zsh` | Before push | Orchestrator — routes to other hooks; guards with repo allowlist |
| `pre-push-tests.zsh` | Before push | Detects untested files, runs test suite, warns on gaps |
| `pre-push-evidence.zsh` | Before push | AI-driven extraction of apprenticeship portfolio evidence from commits |
| `post-commit-docs.zsh` | After commit | Checks if documentation needs updating based on changed files |
| `settings-sync.sh` | SessionStart | Strips JSONC comments from `settings.local.jsonc` → `settings.local.json` |
| `session-start-worktree.sh` | SessionStart | Injects git worktree context into the session environment |
| `stop-uncommitted-check.sh` | Stop | Warns about uncommitted changes when Claude finishes responding |

There are also two project-level hooks in `.claude/hooks/`: `session-start.sh` detects project framework, package manager, and test runner in remote (web) sessions; `session-start-local.sh` runs local-specific initialisation.

<details>
    <summary><strong>How I use it</strong></summary>
    <p>The hooks enforce discipline I wouldn't maintain manually. The test hook catches untested code before it reaches the remote. The evidence hook is specific to my situation — I'm on a Software Development Apprenticeship (Level 4) and need to collect KSB evidence from my work. Rather than retrospectively hunting for evidence, the hook analyses each push and extracts it automatically. The stop hook is a lightweight prompt: "you've been in this session a while, there are uncommitted changes — should you commit before finishing?"</p>
    <p>The `pre-push.zsh` orchestrator has an allowlist — only specified repositories run the full hook chain. This prevents the heavier hooks (especially the AI evidence extraction) from running on every casual project.</p>
    <p>The `settings-sync.sh` hook solves a specific problem: Claude Code reads `settings.local.json` but comments aren't valid JSON. The hook lets me maintain a `.jsonc` source of truth and generates the `.json` file on every session start.</p>
</details>

<details>
    <summary><strong>The pattern</strong></summary>
    Hooks have different uses depending on what you need. Enforcing personal discipline (my main use) is one. Others include: automating tedious bookkeeping, enforcing team standards, integrating with external tools, or augmenting Claude's behaviour (injecting context at session start, validating output before it's finalised). The key insight is the allowlist approach: not every project needs every hook.
</details>

---

### output-styles/

Defines how Claude communicates — tone, verbosity, explanation strategy. The style file loads for the entire session, so keep it concise.

<details>
    <summary><strong>How I use it</strong></summary>
    The `british-dev-goblin.md` style sets a collaborative, understated tone. It tells Claude to lead with solutions, skip obvious explanations, and only go deep when there's genuine learning value. It also encodes writing discipline rules: no em dashes, no contrastive couplets, no parade of examples.
</details>

<details>
    <summary><strong>The pattern</strong></summary>
    Without a style, Claude defaults to explaining things you already know. A style that says "skip obvious explanations" and "lead with the solution" cuts that padding. Someone who learns best from detailed explanations would configure the opposite of what's here.
</details>

---

### library/

Shared resources, templates, and reference material used by skills and agents.

<details>
    <summary><strong>How I use it</strong></summary>
    <p>`library/configs/examples/roadmaps.jsonc` defines the expected shape of a project's `.claude/roadmaps.json` registry — the roadmap creation skill uses this format when registering a new roadmap.</p>
    <p>`library/docs/reasonable-colors-reference.md` is a quick-reference for the [Reasonable Colors](https://www.reasonable.work/colors/) palette, which is the default for all frontend/styling work. It covers all 24 colour sets, the shade system, and WCAG contrast ratios. The full palette is also available via `npm install reasonable-colors` or the CDN at `unpkg.com/reasonable-colors@0.4.0/reasonable-colors.css`.</p>
    <p>`library/docs/examples/mvp.md` is a complete worked example of a roadmap in the `{Milestone}{Category}.{Seq}` format — the canonical reference for what `doc-create-roadmap-omega` produces.</p>
    <p>`library/docs/templates/` has blank templates for ADRs, API references, feature specs, roadmaps, status reports, technical overviews, and work records.</p>
</details>

<details>
    <summary><strong>The pattern</strong></summary>
    As your setup grows, you'll accumulate reusable fragments — data structures, template formats, reference material. Rather than duplicating these across skills, centralise them. The library is the "shared code" of your configuration.
</details>

---

## Skills vs Agents

These two systems do different jobs. Understanding the distinction matters because choosing the wrong one either limits what Claude can do or over-engineers something simple.

### Skills: Knowledge and Repeatable Workflows

A skill is either a knowledge pack (passive, loads on keywords) or a structured workflow (active, invoked with a slash command).

<details>
  <summary><strong>Knowledge skills: how they work</strong></summary>
  Each knowledge skill lives in `skills/<name>/SKILL.md`. The YAML frontmatter declares trigger keywords. When you mention "Svelte" or "$state", the `svelte-ninja` skill loads into Claude's context. You never asked for it — Claude just becomes more knowledgeable about Svelte for the duration of that conversation.
</details>

<details>
  <summary><strong>Command skills: how they work</strong></summary>
  Each command skill has `disable-model-invocation: true` in its frontmatter. When you type `/skill-name`, Claude follows the skill's defined workflow: a sequence of steps, a specified model tier, input handling, and output format.
</details>

<details>
  <summary><strong>What they're for</strong></summary>
  Knowledge skills tell Claude *how to think* about a subject. The `testing-obsessive` skill doesn't just list Vitest commands — it encodes a risk-based testing philosophy and priority matrices. Command skills formalise repeatable workflows. The `doc-create-status-report-delta` skill defines a filename convention, audience guidelines, and the instruction to read the previous report before writing the new one. These details accumulated because early status reports were inconsistent.
</details>

<details>
  <summary><strong>When to create one</strong></summary>
  Knowledge skill: when Claude gives you generic advice in an area where you need opinionated guidance. Command skill: when you've given Claude the same multi-step instruction more than twice.
</details>

### Agents: Autonomous Processes

An agent is a multi-step workflow that Claude delegates to a sub-process. Agents run autonomously, use their own model, and some have persistent memory across sessions.

<details>
  <summary><strong>How they work</strong></summary>
  Each agent lives in `agents/<name>.md`. The frontmatter sets the model and a description that tells Claude *when* to delegate to the agent. When Claude recognises a matching situation, it spawns the agent as a separate process with its own context window.
</details>

<details>
  <summary><strong>What they're for</strong></summary>
  Complex workflows that require judgement, multiple tool calls, and potentially their own accumulated context. The `project-context-loader` doesn't just read a README — it analyses git history, scans for ADRs, checks active branches, identifies technical debt, and synthesises everything into a 60-second context reload. That's too much orchestration for a skill.
</details>

<details>
  <summary><strong>When to create one</strong></summary>
  When a workflow requires autonomous decision-making across multiple steps. If the process needs Claude to *investigate* before acting (rather than following a fixed template), that's an agent.
</details>

### Quick Reference

| | Knowledge Skills | Command Skills | Agents |
|---|---|---|---|
| **Triggered by** | Keywords (automatic) | Slash command (explicit) | Claude's judgement (delegated) |
| **Purpose** | Domain knowledge | Repeatable workflows | Autonomous multi-step processes |
| **Complexity** | Static reference | Structured steps | Dynamic investigation |
| **Model** | Inherits session model | Specifies own model | Specifies own model |
| **User action** | None — loads silently | You invoke it | Claude delegates to it |
| **Memory** | None | None | Can persist across sessions |
| **Context cost** | Description at start; full file on trigger | Full file on invoke | Description only (runs in sub-process) |

---

## How This Setup Was Built

This didn't start as a comprehensive system. It started with a `CLAUDE.md` that said "use British spelling" and a `.gitignore`. Every addition traces back to a specific problem.

<details>
<summary><strong>CLAUDE.md Grew From Repeated Corrections</strong></summary>

The "Spelling (Non-Negotiable)" section exists because Claude kept writing "organization" and "initialize." Rather than correcting it every session, the config now lists explicit rules (`-ise` not `-ize`, `-our` not `-or`, `-re` not `-er`) and links to the Oxford Learner's Dictionary as the authority. The "Code Editing" section — "Do not edit files directly unless explicitly asked" — exists because Claude would make changes without showing them first. Each rule in CLAUDE.md is a correction that happened often enough to formalise.
</details>

<details>
<summary><strong>Knowledge Skills Addressed Gaps in Claude's Default Advice</strong></summary>

The `svelte-ninja` skill was created because Claude's generic Svelte knowledge didn't cover Svelte 5's runes system well enough — it would suggest Svelte 4 patterns (`$:` reactive statements, stores) when the project had moved to `$state`, `$derived`, and `$effect`. The skill encodes the specific patterns, anti-patterns, and SvelteKit conventions that matter for this stack.
</details>

<details>
<summary><strong>Some Skills Exist to Compensate for Known Weaknesses</strong></summary>

The CLAUDE.md states plainly: "Testing is a known weakness. No systematic TDD, no comprehensive coverage culture." The `testing-obsessive` skill was built as a counterweight — it encodes the testing approach the developer *wants* to follow (risk-based, test-after, 80% coverage target, not 100%) even when the instinct is to skip writing tests entirely. The skill doesn't pretend the weakness doesn't exist; it builds scaffolding around it.
</details>

<details>
<summary><strong>Command Skills Were Extracted From Repeated Instructions</strong></summary>

The `wip-version` skill updates version numbers across multiple files simultaneously — README, package.json, tauri.conf.json, Cargo.toml. It exists because those numbers kept drifting out of sync during manual updates. The `doc-create-status-report-delta` skill has a specific filename format, audience guidelines ("one dev, one non-dev — explain capabilities, not implementation"), and the instruction to read the previous report before writing the new one. These details accumulated because early status reports were inconsistent.

What were formerly slash commands in a `commands/` directory have been merged into command skills — same workflows, same model tier conventions, now living alongside knowledge skills in `skills/`.
</details>

<details>
<summary><strong>Agents Were Added When Skills Weren't Enough</strong></summary>

The `project-context-loader` agent exists because switching between projects (Iris, Rhea, Theia) meant losing track of branches, recent decisions, and work in progress. A skill could provide a template for context-loading, but the agent needs to *investigate* — scan git history, read ADRs, check for uncommitted changes, identify patterns, and synthesise a briefing. That requires autonomy.

The session orchestrator and session closer form a loop: start each session with a ranked work plan based on git state and Linear priorities; end with a handoff note for the next session. This compensates for the ADHD-driven tendency to start sessions without context and end them without recording what was done.
</details>

<details>
<summary><strong>Hooks Were Written When Discipline Failed</strong></summary>

The pre-push test hook exists because untested code kept reaching the remote. The post-commit documentation hook exists because the mapping between source files and their documentation was clear (API files should trigger `api.md` updates, auth files should trigger `security.md`) but wasn't being acted on consistently. The evidence extraction hook exists because retrospectively hunting for apprenticeship portfolio evidence was miserable — automating it at push time turned a dreaded chore into a background process.
</details>

The through-line is externalised executive function. Working memory (knowledge skills), task initiation (`suggest-task` command skills), sustained process discipline (hooks), context switching (`project-context-loader` agent) — each addresses something that ADHD makes unreliable by offloading it to a system that doesn't forget, doesn't get distracted, and doesn't need motivation to follow through.

---

## Building Your Own

### Respect the Context Window

Every customisation competes for space in Claude's context window. Space consumed by configuration is space unavailable for your code and conversation.

| Type | When it loads | Typical size | Cost when idle |
|---|---|---|---|
| **CLAUDE.md** | Every session | 50–200 lines | Always present |
| **Output style** | Every session (when active) | 20–40 lines | Always present |
| **Knowledge skill** | Description at start; body on trigger | 180–1,400 lines | Minimal (description only) |
| **Command skill** | On slash-command invoke | 30–240 lines | Zero until invoked |
| **Agent description** | Every session | 5–10 lines (frontmatter only) | Minimal |

The ones to watch are knowledge skills. Their descriptions load at session start (cheap), but when triggered, the full body loads — and they trigger automatically on keywords. Multiple skills triggering simultaneously is realistic.

**Practical guidance:**
- **Start with command skills** — they're free until invoked
- **Keep CLAUDE.md lean** — it loads every session
- **Create knowledge skills deliberately** — only when Claude's default advice is genuinely inadequate for your domain
- **Don't duplicate** — if it's in CLAUDE.md, don't repeat it in a skill

### Start With Friction

Don't configure speculatively. Wait until something annoys you, then fix it.

**Exercise:** Over your next few sessions, keep a list of moments where Claude does something you immediately correct. Each correction is a candidate for `CLAUDE.md`.

### Encode Decisions, Not Preferences

There's a difference between "I prefer tabs" and "use tabs because the team standard is tabs." The first is cosmetic; the second prevents real problems.

**Exercise:** For each rule you want to add, ask: "What goes wrong if Claude ignores this?" If the answer is "nothing, I just prefer it," consider whether it's worth the configuration noise.

### Layer Your Configuration

This setup uses three layers:

1. **Global** (`CLAUDE.md` at root) — true for every project
2. **Project-level** (`project/CLAUDE.md`) — overrides global for specific repositories
3. **Subsystem-level** (`project/frontend/CLAUDE.md`) — overrides project for specific areas

Start with global. Add project layers only when a project genuinely diverges.

### Use Model Tiers Deliberately

Command skills in this repo use three tiers:

- **Haiku** (`delta`) — fast, cheap: version bumps, work records, simple suggestions
- **Sonnet** (`gamma`) — balanced: ADRs, documentation updates, code analysis
- **Opus** (`omega`) — thorough: architectural critiques, implementation planning, roadmaps

Not every task needs Opus. If you're generating a commit message, Haiku is fine. If you're planning a database migration, you probably want Opus.

### Version Control Everything

This entire directory is a git repository. That means:

- Changes to configuration are tracked and reversible
- You can see *when* a rule was added and *why* (through commit messages)
- The setup can be shared, forked, or referenced by others
- Moving to a new machine means cloning one repository

### Let It Grow Organically

**A reasonable progression:**

1. **Week 1:** Create `CLAUDE.md` with your spelling, tone, and code style preferences
2. **First month:** Add your first knowledge skill when Claude gives generic advice in your specialist area
3. **When you notice repetition:** Extract your first command skill from a workflow you've typed out three times
4. **When workflows get complex:** Create your first agent for a multi-step process you keep doing inconsistently
5. **When discipline slips:** Add your first hook for the check you know you should run but don't

The goal isn't a comprehensive system. The goal is a system that solves *your* actual problems, one friction point at a time.
