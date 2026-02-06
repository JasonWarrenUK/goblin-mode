# Claude Code Config

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) is Anthropic's command-line tool for working with Claude. Out of the box it's useful, but you can customise how it behaves — what it knows about your tech stack, how it writes commit messages, what checks it runs before pushing code. That's what this repository does: it stores those customisations in one place so they're version-controlled and portable.

If you're new to Claude Code, [this cheat sheet](https://medium.com/@tonimaxx/the-ultimate-claude-code-cheat-sheet-your-complete-command-reference-f9796013ea50) is a good starting point. This README assumes you've used it at least a few times and are wondering how to make it work better for you.

The specific choices here reflect one developer's workflow — many of them shaped by ADHD — but the patterns are transferable. Your setup should look nothing like this one.

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
- [Commands vs Skills vs Agents](#commands-vs-skills-vs-agents)
- [How This Setup Was Built](#how-this-setup-was-built)
- [Building Your Own](#building-your-own)
  - [Respect the Context Window](#respect-the-context-window)
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

**Context cost:** Skills don't load into context when triggered — they're loaded at session start so Claude can scan their trigger keywords. The ten skills in this repo total ~7,300 lines. That's context window space consumed in every session, whether or not a skill is ever relevant. When a skill *does* trigger, the cost has already been paid; but every skill you add raises the baseline cost of every session. The `api-designer` alone is 1,374 lines. If your session never touches API design, those 1,374 lines are pure overhead.

| Skill | Triggers on | Purpose | Impact Example |
|---|---|---|---|
| `svelte-ninja` | Svelte, SvelteKit, runes, $state | Svelte 5 patterns and SvelteKit conventions | Uses `$state` runes instead of suggesting Svelte 4 stores |
| `git-manager` | git, branch, commit, PR | Branch naming, commit conventions, conflict resolution | Generates `feat(auth):` commits instead of generic messages |
| `api-designer` | API design, Zod, validation | Type-safe API contracts and error handling | Adds Zod validation schemas instead of bare `req.body` access |
| `frontend-styler` | layout issues, CSS, styling | Debugging layout problems and style consistency | Checks computed styles systematically instead of guessing at CSS |
| `debugging` | debugging mentions | Basic five-step debugging framework | Asks "can you reproduce it?" before suggesting fixes |
| `systematic-debugger` | bug, error, broken, DevTools | Methodical browser and Node.js debugging | Walks through DevTools Network tab instead of adding `console.log` everywhere |
| `data-ontologist` | database design, schema, polyglot | When to use relational vs. graph vs. document databases | Recommends Neo4j for relationship-heavy data instead of forcing everything into PostgreSQL |
| `cypher-linguist` | Neo4j, Cypher, graph queries | Cypher query language and graph patterns | Writes `MATCH (n)-[:KNOWS]->(m)` patterns instead of suggesting SQL joins |
| `remember` | "remember that", "note this" | Stores preferences in CLAUDE.md files | Writes "Omit semicolons" to CLAUDE.md instead of just acknowledging the preference |
| `testing-obsessive` | write tests, Vitest, coverage | Risk-based testing strategy and Vitest setup | Prioritises testing payment logic over styling, targets 80% coverage not 100% |

**How I use it:** The skills reflect what I actually work with. There's a Svelte skill because that's my primary framework. There's a Neo4j/Cypher skill because I work with graph databases. There are *two* debugging skills because the first one (`debugging`, 180 lines) is a quick five-step framework for when I roughly know where the problem is and just need a structured process. The second (`systematic-debugger`, 880 lines) is for when I'm genuinely stuck — it has DevTools walkthroughs, Svelte-specific reactive debugging, common bug pattern catalogues and performance profiling guides. The `testing-obsessive` skill exists precisely because testing is a weakness; it encodes the approach I want to follow even when my instinct is to skip it.

**The pattern:** Skills should encode expertise you need but don't always have at your fingertips. They're not documentation — they're opinionated guides that tell Claude *how* to approach a domain, not just what the domain contains. A React developer would have entirely different skills here. A Python data scientist would have different skills again. The question to ask: "When I'm working in this area, what do I wish I always remembered?"

---

### agents/

Agents are autonomous multi-step workflows that Claude can delegate to. Each agent has a designated model (Sonnet for speed, Opus for depth) and a specific job.

**Context cost:** Agent definitions (the `.md` files) are loaded so Claude knows *when* to delegate, but the agent itself runs as a separate sub-process with its own context window. The cost to your main session is just the description in the frontmatter — typically a few lines. The actual 100+ line instruction set only loads into the agent's own context when it's spawned.

| Agent | Model | Purpose |
|---|---|---|
| `project-context-loader` | Sonnet | Rebuild mental context when switching between projects |
| `implementation-planner` | Opus | Break vague feature requests into actionable implementation plans |
| `roadmap-maintainer` | Opus | Keep documentation and roadmaps in sync with actual code |

**How I use it:** I work across multiple projects (Iris, Rhea, Theia). The context loader exists because switching between them was painful — with ADHD, context-switching costs are steep, and I'd lose track of what branch I was on, what I'd been working on, what architectural decisions I'd made. Twenty minutes of reading git logs before writing a line of code, every time. The implementation planner exists because I tend to start coding the interesting bit before thinking through the full scope of a feature. The roadmap maintainer exists because my roadmap format is complex — milestones with numbered task IDs, dependency tracking via Mermaid diagrams, status tables and per-milestone sections that all need to agree with each other. Updating that by hand invites inconsistency.

**The pattern:** Agents solve *process* problems, not *knowledge* problems. If you notice a recurring multi-step workflow where you keep forgetting steps or doing them inconsistently, that's an agent. Skills tell Claude what to know; agents tell Claude what to *do*. Think about the workflows you dread or skip — those are your agent candidates.

---

### commands/

Invocable templates triggered with slash commands (e.g., `/doc/create/adr`). Each command specifies a model tier, accepts arguments and defines a structured workflow.

**Context cost:** Commands only load into context when you invoke them. Until you type the slash command, they consume nothing. This makes them the cheapest customisation — you can have dozens of commands with zero impact on your day-to-day context budget.

**Categories:**

- **analyse/** — Codebase introspection: critiques, overviews, roadmap-vs-reality comparisons
- **chore/** — Maintenance tasks like version number updates across files
- **doc/create/** — Generate new documentation: ADRs, READMEs, roadmaps, work records, status reports
- **doc/update/** — Update existing docs to reflect code changes
- **git/** — Commit message generation and pull request creation
- **project/** — Initialise new projects from a template (Kamino)
- **task/** — Suggest next logical tasks or execute with minimal approach

Some commands offer model tiers so the same operation can run at different levels of sophistication. The `task/suggest` command comes in three variants: `delta` (Haiku — quick suggestion when you just need momentum), `gamma` (Sonnet — balanced analysis) and `omega` (Opus — thorough codebase-vs-roadmap comparison). The `task/minima` command offers `delta` and `gamma` only — Opus would be overkill for "do this with minimal approach." Other commands don't tier at all: `git/commit` is always Haiku (commit messages don't need deep reasoning), `analyse/critique` is always Opus (shallow critiques aren't useful) and `doc/create/status-report` is always Haiku (structured enough that the template does the heavy lifting).

**How I use it:** The `analyse/critique` command points Opus at my codebase and probes for weaknesses in implemented code — not missing features, just problems in what's actually there. The `doc/create/work-record` command generates session summaries from git history — useful for apprenticeship portfolio evidence. The `task/suggest` commands analyse my codebase against my roadmap and suggest what to work on next, which helps when I'm stuck or scattered. The `git/pull-request` command has an unusual rule: the summary must be a "non-technical, absurd metaphor." That's a deliberate choice to make PR reviews less tedious.

**The pattern:** Commands formalise the workflows you repeat. If you find yourself giving Claude the same multi-step instruction more than twice, extract it into a command. The model tier system is worth adopting — not every task needs your most expensive model. Status reports and version bumps work fine with Haiku; architectural analysis benefits from Opus.

---

### hooks/

Claude Code supports hooks that trigger on a range of events — not just git operations. The full list includes `PreToolUse` and `PostToolUse` (before/after Claude runs a tool), `UserPromptSubmit` (when you send a message), `SessionStart` and `SessionEnd`, `Stop` (when Claude finishes responding), `Notification` and more. Hooks can be shell commands, single-prompt LLM calls or full sub-agents with tool access.

All the hooks in *this* repository happen to be git hooks (shell scripts symlinked into `.git/hooks/` directories), but that's a reflection of where my friction was, not a limitation of the system. A `PreToolUse` hook could lint every file before Claude writes it. A `SessionStart` hook could load environment-specific context. A `Stop` hook could verify that tests pass before Claude considers itself done.

| Hook | Event | Purpose |
|---|---|---|
| `pre-push.zsh` | Before push | Orchestrator — routes to other hooks, guards with repo allowlist |
| `pre-push-tests.zsh` | Before push | Detects untested files, runs test suite, warns on gaps |
| `pre-push-evidence.zsh` | Before push | AI-driven extraction of apprenticeship portfolio evidence from commits |
| `post-commit-docs.zsh` | After commit | Checks if documentation needs updating based on changed files |

**How I use it:** The hooks enforce discipline I wouldn't maintain manually — and that's the primary reason *I* reach for them. The test hook catches untested code before it reaches the remote. The evidence hook is specific to my situation — I'm on a Software Development Apprenticeship (Level 4) and need to collect evidence of Knowledge, Skills, and Behaviours (KSBs) from my work. Rather than retrospectively hunting for evidence, the hook analyses each push and extracts it automatically. The documentation hook maps changed source files to their relevant docs (API files trigger `api.md`, auth files trigger `security.md`, config changes trigger `README.md`) and prompts me to update them.

The `pre-push.zsh` orchestrator has an allowlist — only specified repositories run the full hook chain. This prevents the heavier hooks (especially the AI evidence extraction) from running on every casual project.

**The pattern:** Hooks have different uses depending on what you need. Enforcing personal discipline (my main use) is one. Others include: automating tedious bookkeeping (logging, data collection), enforcing team standards across contributors, integrating with external tools (CI, linters, notification services) or augmenting Claude's behaviour (injecting context at session start, validating output before it's finalised). The key insight is the allowlist approach: not every project needs every hook. Start with the trigger point that matches your actual friction.

---

### output-styles/

Defines how Claude communicates — tone, verbosity, explanation strategy. The style file is loaded when active and stays in context for the entire session, so keep it concise.

**How I use it:** The `british-dev-goblin.md` style sets a collaborative, understated tone. It tells Claude to lead with solutions, skip obvious explanations and only go deep when there's genuine learning value. "Casual but not cringe-inducing" and "English sensibility (avoid American over-enthusiasm)" are the operative instructions.

**The pattern:** Without a style, Claude defaults to explaining things you already know — prefacing a database migration with what a migration is, or walking through how `async/await` works before answering your actual question. A style that says "skip obvious explanations" and "lead with the solution" cuts that padding and gets to the answer faster. Someone who learns best from detailed explanations would configure the opposite of what's here. Someone working in a team might want a more formal, documentation-oriented style.

---

### library/

Shared resources, templates and example configurations used by commands and agents.

**How I use it:** Currently holds example config structures that commands reference as templates. For instance, `library/configs/examples/roadmaps.jsonc` defines the expected shape of a project's `.claude/roadmaps.json` file — the `doc/create/roadmap` command uses this format when generating a new roadmap and registering it in the project config.

**The pattern:** As your setup grows, you'll accumulate reusable fragments — data structures, template formats, example configs. Rather than duplicating these across commands, centralise them. The library is the "shared code" of your configuration.

---

## Commands vs Skills vs Agents

These three systems do different jobs. Understanding the distinction matters because choosing the wrong one for a task either limits what Claude can do or over-engineers something simple.

### Skills: Passive Knowledge

A skill is a knowledge pack that Claude loads automatically when it detects relevant keywords in conversation. You don't invoke skills — they activate on their own.

**How they work:** Each skill lives in `skills/<name>/SKILL.md`. The YAML frontmatter declares trigger keywords. When you mention "Svelte" or "$state", the `svelte-ninja` skill loads its 900 lines of Svelte 5 patterns, runes conventions and SvelteKit routing guidance into Claude's context. You never asked for it — Claude just becomes more knowledgeable about Svelte for the duration of that conversation.

**What they're for:** Domain expertise. A skill tells Claude *how to think* about a subject. The `testing-obsessive` skill doesn't just list Vitest commands — it encodes a risk-based testing philosophy ("Not for 100% coverage"), a specific workflow (test-after development) and priority matrices for deciding what to test. The `data-ontologist` skill doesn't just describe databases — it provides decision frameworks for when to use relational vs. graph vs. document storage.

**When to create one:** When Claude gives you generic advice in an area where you need opinionated guidance. If Claude suggests class components when you've standardised on Svelte 5 runes, that's a skill gap.

### Commands: Explicit Workflows

A command is a structured template you invoke deliberately with a slash command (e.g., `/doc/create/status-report`). Commands define a step-by-step workflow, specify which model to use and often accept arguments.

**How they work:** Each command lives in `commands/<category>/<name>.md`. The YAML frontmatter sets the model and description. The body defines ordered steps, input handling, output format and rules. When you type `/git/commit`, Claude follows the commit command's specific workflow: check staging, generate a conventional commit message, show it for approval, then push.

**What they're for:** Repeatable processes with defined structure. The `doc/create/status-report` command doesn't just say "write a status report" — it specifies a filename convention (`003_26-01-13-1545_xml-validation-added.md`), requires reading the previous report and the roadmap first, defines an audience ("one dev, one non-dev") and forbids nested bullet lists. The `chore/version` command updates five specific files (README, package.json, tauri.conf.json, Cargo.toml, a UI layout file) in lockstep — a task that's easy to get wrong manually.

**When to create one:** When you've given Claude the same multi-step instruction more than twice. If you keep typing "look at my git history, compare it to the roadmap, and write a status report in this format," that's a command.

### Agents: Autonomous Processes

An agent is a multi-step workflow that Claude delegates to a sub-process. Agents run autonomously, use their own model and can have persistent memory across sessions.

**How they work:** Each agent lives in `agents/<name>.md`. The frontmatter sets the model and a description that tells Claude *when* to delegate to the agent. When Claude recognises a matching situation, it spawns the agent as a separate process. The `roadmap-maintainer` agent, for example, runs on Opus, has its own persistent memory directory and follows a six-step workflow: read relevant command files, assess current state, identify gaps, apply patterns, validate accuracy and suggest updates.

**What they're for:** Complex workflows that require judgement, multiple tool calls and potentially their own accumulated context. The `project-context-loader` agent doesn't just read a README — it analyses git history, scans for ADRs, checks active branches, identifies technical debt and synthesises everything into a 60-second context reload. That's too much orchestration for a command and too process-oriented for a skill.

**When to create one:** When a workflow requires autonomous decision-making across multiple steps. If the process needs Claude to *investigate* before acting (rather than following a fixed template), that's an agent.

### Quick Reference

| | Skills | Commands | Agents |
|---|---|---|---|
| **Triggered by** | Keywords (automatic) | Slash command (explicit) | Claude's judgement (delegated) |
| **Purpose** | Domain knowledge | Repeatable workflows | Autonomous multi-step processes |
| **Complexity** | Static reference | Structured steps | Dynamic investigation |
| **Model** | Inherits session model | Specifies own model | Specifies own model |
| **User action** | None — loads silently | You invoke it | Claude delegates to it |
| **Memory** | None | None | Can persist across sessions |
| **Context cost** | Full file on trigger | Full file on invoke | Description only (runs in sub-process) |
| **Example** | "How to write Svelte 5 runes" | "Generate a status report" | "Rebuild project context" |

---

## How This Setup Was Built

This didn't start as a comprehensive system. It started with a `CLAUDE.md` that said "use British spelling" and a `.gitignore`. Every addition traces back to a specific problem.

<details>
<summary><strong>CLAUDE.md Grew From Repeated Corrections</strong></summary>

The "Spelling (Non-Negotiable)" section exists because Claude kept writing "organization" and "initialize." Rather than correcting it every session, the config now lists explicit rules (`-ise` not `-ize`, `-our` not `-or`, `-re` not `-er`) and links to the Oxford Learner's Dictionary as the authority. The "Code Editing" section — "Do not edit files directly unless explicitly asked" — exists because Claude would make changes without showing them first. Each rule in CLAUDE.md is a correction that happened often enough to formalise.
</details>

<details>
<summary><strong>The First Skills Addressed Gaps in Claude's Default Advice</strong></summary>

The `svelte-ninja` skill (900+ lines) was created because Claude's generic Svelte knowledge didn't cover Svelte 5's runes system well enough — it would suggest Svelte 4 patterns (`$:` reactive statements, stores) when the project had moved to `$state`, `$derived` and `$effect`. The skill encodes the specific patterns, anti-patterns and SvelteKit conventions that matter for this developer's stack.
</details>

<details>
<summary><strong>Some Skills Exist to Compensate for Known Weaknesses</strong></summary>

The CLAUDE.md states plainly: "Testing is a known weakness. No systematic TDD, no comprehensive coverage culture." The `testing-obsessive` skill was built as a counterweight — it encodes the testing approach the developer *wants* to follow (risk-based, test-after, 80% coverage target, not 100%) even when the instinct is to skip writing tests entirely. It includes specific priority matrices, Vitest configurations and a section on portfolio evidence for KSB documentation. The skill doesn't pretend the weakness doesn't exist; it builds scaffolding around it.
</details>

<details>
<summary><strong>Iteration Is Visible in the Skill Set</strong></summary>

There are two debugging skills. The first (`debugging`) is a concise five-step framework: reproduce, isolate, diagnose, fix, verify. It's 180 lines and covers the basics. The second (`systematic-debugger`) is 880 lines and adds browser DevTools workflows, Node.js debugging, Svelte-specific patterns (reactive statement logging, store debugging, component lifecycle tracing), performance profiling and common bug pattern catalogues (race conditions, stale closures, memory leaks). The first skill wasn't deleted because it serves a different moment — `debugging` is for when you roughly know where the problem is and need a structured process to work through it; `systematic-debugger` is for when you're genuinely stuck and need the DevTools walkthrough or the bug pattern catalogue to jog your thinking.
</details>

<details>
<summary><strong>The <code>remember</code> Skill Is a Meta-Tool</strong></summary>

It exists because preferences kept getting lost between sessions. When you say "remember that the API uses snake_case," it parses the instruction, locates the appropriate CLAUDE.md file, determines the right section, transforms casual language into an imperative instruction ("API responses use snake_case — convert to camelCase in frontend code") and writes it. It's a skill whose job is to grow the configuration itself.
</details>

<details>
<summary><strong>Commands Were Extracted From Repeated Instructions</strong></summary>

The `chore/version` command updates version numbers across five files simultaneously — README, package.json, tauri.conf.json, Cargo.toml and a UI layout file. It exists because those numbers kept drifting out of sync during manual updates. The `doc/create/status-report` command has a specific filename format (`003_26-01-13-1545_xml-validation-added.md`), audience guidelines ("one dev, one non-dev — explain capabilities, not implementation") and the instruction to read the previous report before writing the new one. These details accumulated because early status reports were inconsistent — different formats, missing context, jargon that non-technical readers couldn't parse.
</details>

<details>
<summary><strong>Agents Were Added When Commands Weren't Enough</strong></summary>

The `project-context-loader` agent exists because switching between projects (Iris, Rhea, Theia) meant losing track of branches, recent decisions and work in progress. A command could list files, but the context loader needs to *investigate* — scan git history, read ADRs, check for uncommitted changes, identify patterns and synthesise a 60-second briefing. That requires autonomy, not a fixed template. The `roadmap-maintainer` agent was given persistent memory (`agent-memory/roadmap-maintainer/`) because documentation context was being lost between sessions — it needed to remember what it had found before.
</details>

<details>
<summary><strong>Hooks Were Written When Discipline Failed</strong></summary>

The pre-push test hook exists because untested code kept reaching the remote. The post-commit documentation hook exists because the mapping between source files and their documentation was clear (API files should trigger `api.md` updates, auth files should trigger `security.md`) but the developer wasn't making those updates consistently. The evidence extraction hook exists because retrospectively hunting for apprenticeship portfolio evidence was miserable — automating it at push time turned a dreaded chore into a background process.
</details>

The through-line, if there is one, is externalised executive function. Working memory (`remember` skill), task initiation (`task/suggest` commands), sustained process discipline (hooks), context switching (`project-context-loader` agent) — each addresses something that ADHD makes unreliable by offloading it to a system that doesn't forget, doesn't get distracted and doesn't need motivation to follow through. That's the shape of *this* setup. Yours will have a different shape, driven by whatever your brain is worst at maintaining on its own.

Each layer built on the one before it, and each addition solved a problem that was already causing friction — not one that might cause friction someday.

---

## Building Your Own

### Respect the Context Window

Every customisation competes for space in Claude's context window — the total amount of text it can "see" at once. Space consumed by configuration is space unavailable for your code and conversation.

The costs vary dramatically by type:

| Type | When it loads | Typical size | Cost when idle |
|---|---|---|---|
| **CLAUDE.md** | Every session | 50–200 lines | Always present |
| **Output style** | Every session (when active) | 20–40 lines | Always present |
| **Skill** | On keyword trigger | 180–1,400 lines | Zero until triggered |
| **Agent description** | Every session | 5–10 lines (frontmatter only) | Minimal |
| **Command** | On slash-command invoke | 30–240 lines | Zero until invoked |

The dangerous ones are skills. They trigger automatically on keywords, they can stack (mentioning "Svelte" and "testing" loads ~1,800 lines) and you don't always know it's happened. Ten skills totalling 7,300 lines won't all load at once, but three or four triggering simultaneously is realistic.

**Practical guidance:**

- **Start with commands** — they're free until invoked
- **Keep CLAUDE.md lean** — it loads every session, so every line has a recurring cost
- **Create skills deliberately** — only when Claude's default advice is genuinely inadequate for your domain, and keep them as focused as possible
- **Don't duplicate** — if it's in CLAUDE.md, don't repeat it in a skill

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
- The setup can be shared, forked or referenced by others
- Moving to a new machine means cloning one repository

The `.gitignore` here uses an inverted pattern — it ignores everything by default and explicitly includes what should be tracked. This prevents accidentally committing Claude's cache, task history or other ephemeral data.

### Let It Grow Organically

This repository has ten skills, three agents and over a dozen commands. It didn't start that way, and yours shouldn't either.

**A reasonable progression:**

1. **Week 1:** Create `CLAUDE.md` with your spelling, tone and code style preferences
2. **First month:** Add your first skill when Claude gives generic advice in your specialist area
3. **When you notice repetition:** Extract your first command from a workflow you've typed out three times
4. **When workflows get complex:** Create your first agent for a multi-step process you keep doing inconsistently
5. **When discipline slips:** Add your first hook for the check you know you should run but don't

The goal isn't a comprehensive system. The goal is a system that solves *your* actual problems, one friction point at a time.
