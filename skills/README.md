# Skills

Slash commands and ambient knowledge skills for Claude Code.

| Tier | Model |
|------|-------|
| `𝚫𝚫𝚫` | Haiku — fast |
| `ƔƔƔ` | Sonnet — balanced |
| `𝛀𝛀𝛀` | Opus — thorough |

---

## Knowledge Skills

These skills are loaded automatically by Claude when relevant. Not user-invocable (`user-invocable: false`).

| Skill | Description |
|-------|-------------|
| `api-designer` | This skill should be used when the user mentions "API design", "TypeScript API", "type-safe API", "endpoint design", "API validation", "Zod", discusses creating APIs, type safety, error handling, or API architecture. Addresses designing clean, type-safe APIs with validation, error handling, and documentation. |
| `cypher-linguist` | This skill should be used when the user mentions "Neo4j", "Cypher", "graph database", "graph query", discusses graph relationships, traversals, path finding, or needs help with Cypher syntax. Addresses Neo4j fundamentals, query patterns, performance optimization, and integration with relational databases. |
| `data-ontologist` | This skill should be used when the user mentions "database design", "schema design", "graph database", "document database", "polyglot persistence", "data modeling", "Neo4j", "Supabase", "PostgreSQL", "MongoDB", discusses database architecture, choosing databases, or integrating multiple databases. Addresses when to use relational vs graph vs document databases and integration patterns. |
| `debugging` | Systematic debugging methodology — runtime errors, test failures, logic bugs, performance issues, production incidents. Five-step framework, root-cause analysis, browser/Node/Svelte tooling, and common bug patterns. |
| `domain-modeller` | This skill should be used when the user mentions "domain model", "entity relationships", "data model", "system model", "map the domain", "what are the entities", "how does this connect", discusses designing a new feature or system, plans architecture, or needs to understand the shape of a problem before coding. Addresses model-first thinking — understanding the domain before writing solutions. |
| `ethics-reviewer` | This skill should be used when the user mentions "dark patterns", "accessibility", "a11y", "privacy", "tracking", "analytics", "notifications", "user data", "GDPR", "consent", "manipulation", "sustainability", "performance budget", or when building user-facing features that collect data, send notifications, display urgency, or gate access. Addresses ethical constraints in software design — manipulation, accessibility, privacy, and sustainability. |
| `frontend-styler` | This skill should be used when the user mentions "layout issues", "styling problems", "CSS fixes", "style consistency", "unify styles", "visual bugs", discusses frontend styling, works on UI components, or asks about component styling approaches. Applies to Svelte/SvelteKit projects primarily, with general frontend principles. |
| `git-manager` | This skill should be used when the user mentions "git", "branch", "commit", "merge", "pull request", "PR", "version control", discusses branching strategy, commit conventions, collaboration workflows, or needs help with git operations. Addresses git best practices, branch management, commit messages, and LazyGit integration. |
| `opentui-operative` | OpenTUI terminal UI library reference. Use when working with @opentui/core, terminal UIs, renderables, Yoga layouts, or Zig-native rendering. |
| `roadmap-interviewer` | Run a structured interview to discover new features and produce a batch roadmap proposal. Use this skill when the user wants to explore what to build next, brainstorm features, expand the roadmap, plan a new phase, or says things like 'what should we add', 'help me think through features', 'let's plan the next milestone', or 'interview me about what to build'. Produces a structured proposal for review — nothing is written to the roadmap until the user approves. |
| `roadmap-task-adder` | Add a task to a project roadmap with correct ID, dependency wiring, and graph integrity. Use this skill whenever the user wants to add a task, feature, or work item to a roadmap — even if they just say 'add this to the roadmap', 'put this in the plan', or 'track this as a task'. Handles task ID assignment, section placement, dependency edges in both directions, and ensures no task is left as an unconnected island. |
| `scope-coach` | This skill should be used when the user mentions "scope", "MVP", "minimum viable", "too much", "overwhelmed", "where do I start", "feature creep", "simplify", "cut scope", "what's essential", or when a conversation reveals expanding complexity, multiple possible approaches, or analysis paralysis. Counterbalances the tendency to over-analyse and over-build. |
| `svelte-ninja` | This skill should be used when the user mentions "Svelte", "SvelteKit", "runes", "$state", "$derived", "$effect", "$props", discusses component patterns, reactive state, routing, load functions, form actions, or needs help with Svelte/SvelteKit code. Addresses Svelte 5 patterns using runes, SvelteKit conventions, and best practices. |
| `testing-obsessive` | This skill should be used when the user mentions "write tests", "test coverage", "testing strategy", "unit tests", "integration tests", "e2e tests", "vitest", "jest", discusses testing approaches, asks about test patterns, or works on test files. Addresses testing fundamentals with emphasis on Vitest and Svelte component testing using pragmatic, risk-based approaches. |
| `user-empathy-lens` | This skill should be used when the user mentions "user experience", "UX", "how would someone use this", "user flow", "onboarding", "confusing", "intuitive", "user needs", "persona", "user story", or when designing features that end-users interact with directly. Addresses understanding users through empathy and inference rather than formal research. |
| `whats-new` | Summarise what the user can now see or do that they couldn't before this unit of work |
| `writing-style` | Writing style guide for Jason Warren. Use this skill whenever writing prose, reports, documentation, or any substantive text for Jason — including drafting sections, editing existing content, or rewriting passages. Also use when Jason asks you to review or improve writing. Trigger on any request involving writing, drafting, editing, or composing text that isn't purely code. This includes github Pull Requests & Linear tasks |

---

## Command Skills

User-invocable slash commands (`disable-model-invocation: true`). All commands have been migrated from `commands/` to `skills/`.

### Config

| Command | Tier | Description |
|---------|------|-------------|
| `/config-permits-global-delta` | Haiku | Grant a permission globally (all projects) via settings.local.jsonc |
| `/config-permits-project-delta` | Haiku | Grant a permission for the current project via .claude/settings.local.json |

### Do

| Command | Tier | Description |
|---------|------|-------------|
| `/do-minima` | Haiku | Achieve what I say with a minimalist approach |

### Doc

| Command | Tier | Description |
|---------|------|-------------|
| `/doc-create-adr-gamma` | Sonnet | Create an Architecture Decision Record (ADR) for a significant technical decision |
| `/doc-create-readme-for-gamma` | Sonnet | Generate a README for a specific directory |
| `/doc-create-readme-omega` | Opus | Generate a comprehensive README.md from project analysis |
| `/doc-create-roadmap-omega` | Opus | Create a project roadmap document in structured milestone format |
| `/doc-create-status-report-delta` | Haiku | Create a status report that knows what you've done since the last one |
| `/doc-create-work-record-delta` | Haiku | Generate a work record summarizing today's development session |
| `/doc-update-readme-gamma` | Sonnet | Update a README to reflect recent changes |
| `/doc-update-roadmap-omega` | Opus | Update project roadmap task organization |
| `/doc-update-target-gamma` | Sonnet | Update existing documentation to reflect recent code changes |
| `/doc-view-roadmap` | Sonnet | Visualise a project roadmap as an interactive HTML dashboard |

### Git

| Command | Tier | Description |
|---------|------|-------------|
| `/git-clone-from-kamino` | Opus | Initialize a new project from the Kamino template |
| `/git-commit-batch-delta` | Haiku | Split uncommitted changes into granular commits. |
| `/git-commit-one-delta` | Haiku | Generate a commit message. If nothing staged, stage all changes. |
| `/git-rename-branch` | Sonnet | Rename branch if needed |

### Linear

| Command | Tier | Description |
|---------|------|-------------|
| `/linear-check-deps-omega` | Opus | Analyse and assign dependency relationships for Linear tasks |
| `/linear-create-issue-in-project` | Opus | Create a new Linear issue with automatic dependency detection |
| `/linear-create-issue-related-to` | Sonnet | Create a new Linear issue with optional relations |
| `/linear-crit-path-to-project` | Opus | Decompose a Linear project into a critical path of granular issues |
| `/linear-crit-path-to-task` | Opus | Decompose a Linear issue into a critical path of granular issues |
| `/linear-hoover-issues` | Opus | Find Linear issues addressed by this branch and inject into PR body |
| `/linear-tackle-issue-delta` | Haiku | Tackle a task from Linear |
| `/linear-tackle-issue-gamma` | Sonnet | Tackle a task from Linear |
| `/linear-tackle-issue-omega` | Opus | Tackle a task from Linear |

### Merge

| Command | Tier | Description |
|---------|------|-------------|
| `/merge-from-main` | Opus | Merge from main |
| `/merge-from-named` | Opus | Merge from branch |
| `/merge-rebase` | Opus | Rebase from main |
| `/merge-squashbase` | Opus | Squash and rebase |

### PR

| Command | Tier | Description |
|---------|------|-------------|
| `/pr-shiny-draft` | Sonnet | Create a draft pull request to main |
| `/pr-shiny-main-gamma` | Sonnet | Create a pull request to main |
| `/pr-shiny-main-omega` | Opus | Create a pull request to main |
| `/pr-update` | Sonnet | Update a PR description to account for commits made since it was last written |
| `/pr-wordy-draft` | Sonnet | Create a draft pull request to main |
| `/pr-wordy-main-gamma` | Sonnet | Create a pull request to main |
| `/pr-wordy-main-omega` | Opus | Create a pull request to main |

### Repo

| Command | Tier | Description |
|---------|------|-------------|
| `/repo-check-deps` | Opus | Investigate this repo's dependencies in detail |
| `/repo-critique` | Opus | Probe the project for weaknesses |
| `/repo-introduce` | Opus | Provide a detailed high-level overview of this codebase |
| `/repo-investigate` | Opus | Investigate a codebase in detail |

### Review

| Command | Tier | Description |
|---------|------|-------------|
| `/review-pr` | Opus | Review a pull request and post a comment |
| `/review-this-branch` | Opus | Assess branch readiness for PR submission |

### Suggest Task

| Command | Tier | Description |
|---------|------|-------------|
| `/suggest-task-delta` | Haiku | Suggest the next logical task based on codebase analysis |
| `/suggest-task-gamma` | Sonnet | Suggest the next logical task based on codebase analysis |
| `/suggest-task-omega` | Opus | Suggest the next logical task based on codebase analysis |

### WIP

| Command | Tier | Description |
|---------|------|-------------|
| `/wip-pr-review` | Opus | Review code changes on the current branch against its open PR |
| `/wip-roadmap` | Opus | Map out project status, direction, and next steps |
| `/wip-version` | Haiku | Check all version number props and update them |
