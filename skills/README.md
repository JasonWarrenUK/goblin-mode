# Skills

Slash commands and knowledge skills for Claude Code. Regenerate this index from frontmatter when skills change; do not hand-edit rows.

Run `python3 ~/.claude/library/scripts/gen-skills-index.py` after adding, renaming, or re-describing a skill.

| Tier glyph | Model |
|------|-------|
| `𝚫𝚫𝚫` | Haiku — fast |
| `ƔƔƔ` | Sonnet — balanced |
| `𝛀𝛀𝛀` | Opus — thorough |

---

## Command Skills

User-invocable slash commands (`disable-model-invocation: true`).

| Command | Model | Description |
|---------|-------|-------------|
| `/analyse-project-concept` | opus | Investigate a codebase in detail and write findings to a document, for a named concept, subsystem, o… |
| `/analyse-project-critique` | opus | Probe the project for architectural weaknesses, technical debt, and risk — a deliberately critical r… |
| `/artefact-introduction` | opus | Render a visual HTML introduction to this codebase for a newly-joined developer |
| `/artefact-roadmap` | haiku | Generate the HTML roadmap dashboard deterministically via roadmap.py render. |
| `/audit-artefact` | opus | Audit a topic and render an actionable, status-grouped HTML findings artefact. |
| `/audit-project-deps` | opus | Investigate this repo's dependencies in detail |
| `/branch-integrate` | haiku | Integrate a target branch into the current one by merge, rebase or squash |
| `/branch-review` | opus | Assess branch readiness for PR submission |
| `/clod-config-permits` | haiku | Grant a permission rule globally or for the current project |
| `/clod-config-skill_conventions` | haiku | Jason's placement and model-tag conventions for creating or editing skills |
| `/commit-batch` | haiku | Split uncommitted changes into granular commits. |
| `/commit-one` | haiku | Generate a commit message. If nothing staged, stage all changes. |
| `/distro-changelog` | sonnet | Build or update the changelog from conventional commits and project it to every surface the project… |
| `/distro-tag_version` | haiku | Compute the next semver tag with svu and push it |
| `/distro-zip_roadmap` | haiku | Rebuild roadmap-system.zip, the distributable snapshot of the roadmap tooling (scripts, HTML templat… |
| `/doc-adr` | sonnet | Create an Architecture Decision Record for a significant technical decision |
| `/doc-misc-update` | sonnet | Update an existing documentation file to reflect recent code changes |
| `/doc-readme` | sonnet | Create or update a README — project root or any directory |
| `/execute-minima` | haiku | Achieve what I say with a minimalist approach |
| `/execute-stud` | sonnet | Plan a non-trivial feature by interviewing to resolve unknowns, then studding every function as a ru… |
| `/next-task-group` | haiku | Show every currently unblocked roadmap task, grouped by milestone or topic |
| `/next-task-ship` | opus | Autonomously run the full delivery loop for the next roadmap task — suggest, worktree, implement, ro… |
| `/next-task-suggest` | haiku | Suggest the next logical task — grounded in the roadmap's pre-vetted ready-set when one exists, code… |
| `/pr-create` | sonnet | Create a pull request to main — wordy or shiny (with screenshots), ready-for-review or draft |
| `/pr-handle_review` | opus | Work through a PR's change requests — verify each independently, fix what holds up, reply to every t… |
| `/pr-land` | sonnet | Land an approved PR — merge to main, delete the branch, tag the version, sync the roadmap, clean up |
| `/pr-review` | opus | Review a pull request and post it as a GitHub review |
| `/roadmap-create` | opus | Create a project roadmap in the rich phase-array format — roadmaps.json as source of truth plus a PH… |
| `/roadmap-migrate` | opus | Convert an old simple-style roadmap (single Markdown, four statuses, <a name> anchors, roadmaps.json… |
| `/scaffold-artefact` | opus | Convert an exported Claude artefact (HTML or JSX) into a working Svelte 5 / SvelteKit 2 project |

---

## Model-Invocable Skills

Claude can load these automatically when relevant.

| Skill | Model | Description |
|-------|-------|-------------|
| `/branch-rename` | sonnet | Check the current branch name against convention (type/short-description) and rename it if it drifte… |
| `/hud-pr_wall` | haiku | Show every open PR that involves you, bucketed by what each one is waiting on |
| `/hud-whats_new` | sonnet | Summarise what the user can now see or do that they couldn't before this unit of work |
| `/hud-worktrees` | sonnet | Map every worktree in this repo in plain language and shepherd safe create/remove actions |
| `/pr-review-dry_run` | opus | Review a pull request |
| `/pr-update` | sonnet | Update a PR description to account for commits made since it was last written |
| `/roadmap-audit-deps` | opus | Interview-led audit of the roadmap's dependency graph — are the edges, gates and milestone boundarie… |
| `/roadmap-create-interview` | opus | Interview the user to turn half-formed ideas into a reviewed batch of roadmap-ready tasks — read-onl… |
| `/roadmap-maintain` | opus | Sync roadmap statuses after work lands — recompute from the dependency graph and refresh every proje… |
| `/roadmap-review` | opus | Interview-led review of the roadmap's health — status freshness, the priorities the graph implies, a… |
| `/roadmap-update-tasks` | opus | Add a single well-formed task to a rich-format roadmap — ID assignment, dependency wiring in both di… |

---

## Role Skills

Ambient knowledge roles (`role-*`), loaded by Claude when relevant.

| Skill | Description | When to use |
|-------|-------------|-------------|
| `clod-approach-stud` | Use when about to build a non-trivial feature and you want the shape reviewable before the logic. St… | >=1 of the following are true: (a) spans several functions/files; (b) touches existing code in more than one place; (c)… |
| `clod-expert-api_designer` | Type-safe API design: Zod validation, Result types, SvelteKit endpoints, middleware patterns. | When designing or reviewing an API endpoint, request/response contract, or validation layer — auto-loads on files under… |
| `clod-expert-data_ontologist` | Polyglot persistence: when to use relational, graph, or document databases; integration patterns. | When choosing a data store or storage pattern for new data, or reviewing a schema/migration — auto-loads on schema or mi… |
| `clod-expert-debug_dervish` | Systematic debugging methodology — runtime errors, test failures, logic bugs, performance issues, pr… | When something is broken and the cause isn't obvious yet — an error, a failing test, unexpected behaviour, or a performa… |
| `clod-expert-domain_modeller` | Model-first design: map entities, relationships, and boundaries before writing code. | Before writing code for a new feature that introduces new entities or relationships — when the shape of the data model i… |
| `clod-expert-frontend_styler` | Frontend styling: layout debugging, style consistency, CSS best practices for Svelte/SvelteKit. | When a layout is broken, styles are inconsistent across components, or CSS needs a best-practice review — auto-loads on… |
| `clod-expert-git_manager` | Git workflow: branch management, commit conventions, PR patterns, conflict resolution. | When a git operation needs judgement beyond a single command — resolving a conflict, deciding a branch/commit strategy,… |
| `clod-expert-testing_obsessive` | Pragmatic testing with Vitest: risk-based strategy, Svelte component testing, test-after development… | When writing or reviewing tests, or deciding what's worth testing at all — auto-loads on test/spec files, or when the co… |
| `clod-lang-cypher` | Neo4j and Cypher: graph schema design, query patterns, performance optimisation, PostgreSQL integrat… | When writing or reviewing Cypher queries, designing a graph schema, or bridging Neo4j with a relational store — auto-loa… |
| `clod-lang-opentui` | OpenTUI terminal UI library reference. Use when working with @opentui/core, terminal UIs, renderable… | When building or debugging a terminal UI with @opentui/core — renderable composition, Yoga layout issues, or anything to… |
| `clod-lang-svelte` | Svelte 5 and SvelteKit: runes reactivity, component composition, routing, data loading, form handlin… | When writing or reviewing Svelte 5 / SvelteKit code — auto-loads on .svelte files or +page/+layout files, or when runes… |
| `clod-lens-empathy` | Empathy-driven design: think through how real people experience the software; surface and challenge… | When designing a user-facing flow and it's worth pausing to ask how it actually feels to a real person using it — especi… |
| `clod-lens-ethics` | Passive ethical review: manipulation, accessibility, privacy, sustainability in user-facing features… | When designing or reviewing a user-facing feature — dark patterns, accessibility gaps, privacy overreach, or sustainabil… |
| `clod-lens-scope` | Anti-scope-creep. Forces the question: what is the smallest thing that delivers value? | When a plan is quietly growing beyond the original ask, or the user sounds overwhelmed by scope — before committing to a… |
| `clod-lens-writing-style` | Writing style guide for Jason Warren. Applies whenever writing or editing substantive prose for Jaso… | Any request involving writing, drafting, editing, or composing text that isn't purely code — including GitHub PR descrip… |
