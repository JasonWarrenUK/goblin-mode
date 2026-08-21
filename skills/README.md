# Skills

Slash commands and knowledge skills for Claude Code. Regenerate this index from frontmatter when skills change; do not hand-edit rows.

Run `python3 ~/.claude/library/scripts/gen-skills-index.py` after adding, renaming, or re-describing a skill.

| Tier glyph | Model |
|------|-------|
| `ᚺ` | Haiku (fast) |
| `ᛊ` | Sonnet (balanced) |
| `ᛟ` | Opus (thorough) |
| `ᚠ` | Fable (frontier) |

---

## Command Skills

User-invocable slash commands (`disable-model-invocation: true`).

| Command | Model | Description |
|---------|-------|-------------|
| `/artefact-audit` | ᛊ sonnet | Render verified findings as an actionable, status-grouped HTML artefact. |
| `/artefact-intro` | ᛊ sonnet | Render a visual HTML introduction to this codebase for a newly-joined developer |
| `/artefact-playground` | ᛊ sonnet | Creates interactive HTML playgrounds — self-contained single-file explorers that let users configure… |
| `/artefact-roadmap` | ᚺ haiku | Generate the HTML roadmap dashboard deterministically via roadmap.py render. |
| `/branch-integrate` | ᛊ sonnet | Integrate a target branch into the current one by merge, rebase or squash |
| `/branch-qa_review` | ᛟ opus | Assess branch readiness for PR submission: full review methodology plus the checks only a local chec… |
| `/do-minima` |  | Achieve the stated outcome with the smallest change that satisfies it |
| `/do-stud` | ᛊ sonnet | Plan a non-trivial feature by interviewing to resolve unknowns, then studding every function as a ru… |
| `/import-scaffold_artefact` | ᛊ sonnet | Convert an exported Claude artefact (HTML or JSX) into a working Svelte 5 / SvelteKit 2 project |
| `/next-task-group` | ᚺ haiku | Show every currently unblocked roadmap task, grouped by milestone or topic |
| `/next-task-ship` | ᚠ fable | Autonomously run the full delivery loop for the next roadmap task: suggest, worktree, implement, roa… |
| `/pr-handle_review` | ᛟ opus | Work through a PR's change requests: verify each independently, fix what holds up, reply to every th… |
| `/pr-land` | ᛊ sonnet | Land an approved PR: merge to main, delete the branch, tag the version, sync the roadmap, clean up |
| `/project-audit_deps` | ᛊ sonnet | Investigate this repo's dependencies in detail |
| `/project-tag_version` | ᚺ haiku | Tag the release after a merge to main, computing the next semver tag with svu |
| `/red-branch` | ᛟ opus | Adversarial review of a branch diff written as the colleague trying to get it rejected, aimed at one… |
| `/red-doc` | ᛟ opus | Adversarial review of a document written as the colleague trying to kill it, aimed at one or two nam… |
| `/roadmap-create` | ᛟ opus | Create a project roadmap in the rich phase-array format: roadmaps.json as source of truth plus a PHA… |
| `/roadmap-migrate` | ᛊ sonnet | Convert an old simple-style roadmap (single Markdown, four statuses, <a name> anchors, roadmaps.json… |
| `/skill-creator` | ᛟ opus | Create new skills, modify and improve existing skills, and measure skill performance. Use when users… |

---

## Model-Invocable Skills

Claude can load these automatically when relevant.

| Skill | Model | Description |
|-------|-------|-------------|
| `/artefact-conventions` |  | Jason's structural and epistemic-honesty conventions for every artefact Claude creates |
| `/branch-rename` | ᚺ haiku | Check the current branch name against convention (type/short-description) and rename it if it drifte… |
| `/clod-config-skill_conventions` |  | Jason's placement, invocation and metadata conventions for creating or editing skills |
| `/commit-batch` | ᚺ haiku | Split uncommitted changes into granular commits. |
| `/commit-one` | ᚺ haiku | Generate a commit message. If nothing staged, stage all changes. |
| `/doc-changelog` | ᚺ haiku | Build or update the changelog from conventional commits and project it to every surface the project… |
| `/doc-readme` | ᛊ sonnet | Create or update a README for the project root or any directory |
| `/dossier-record` |  | Record a durable fact about a person Jason works with, in their own dossier file |
| `/hud-cc_releases` | ᛊ sonnet | Summarise Claude Code's own CHANGELOG.md, filtered and grouped for what actually matters to Jason |
| `/hud-profiles` | ᛊ sonnet | Show the profiles stored in the dossier and persona stores |
| `/hud-whats_new` | ᛊ sonnet | Summarise what the user can now see or do that they couldn't before this unit of work |
| `/hud-worktrees` | ᛊ sonnet | Map every worktree in this repo in plain language and shepherd safe create/remove actions |
| `/next-task-suggest` | ᚺ haiku | Suggest the next logical task from the roadmap's pre-vetted ready-set, driven by its leverage signal… |
| `/pr-create` | ᛊ sonnet | Create a pull request to main, or a stacked PR onto a parent branch: wordy or shiny (with screenshot… |
| `/pr-review` | ᛟ opus | Review a pull request and post it as a GitHub review |
| `/pr-review-dry_run` | ᛟ opus | Review a pull request's diff and print structured findings to the terminal. Holds the canonical revi… |
| `/pr-update` | ᛊ sonnet | Update a PR description to account for commits made since it was last written |
| `/roadmap-create-interview` | ᛟ opus | Interview the user to turn half-formed ideas into a reviewed batch of roadmap-ready tasks. Read-only… |
| `/roadmap-maintain` | ᛊ sonnet | Sync roadmap statuses after work lands: recompute from the dependency graph and refresh every projec… |
| `/roadmap-review` | ᛟ opus | Interview-led review of the roadmap: strategic health (freshness, priorities, milestone integrity) a… |
| `/roadmap-update-tasks` | ᛊ sonnet | Add a well-formed task, or a reviewed batch of them, to a rich-format roadmap: ID assignment, depend… |
| `/track-cc_pain` |  | Silently log friction with Claude Code itself (bugs, missing features, annoying limitations) for hud… |

---

## Role Skills

Ambient knowledge roles (`user-invocable: false`), loaded by Claude when relevant.

| Skill | Description | When to use |
|-------|-------------|-------------|
| `clod-approach-stud` | Studs every function of a planned feature in its real file as a runnable walking-skeleton (fake data… | >=1 of the following are true: (a) spans several functions/files; (b) touches existing code in more than one place; (c)… |
| `clod-approach-writing_style` | Writing style guide for Jason Warren. Applies whenever writing or editing substantive prose for Jaso… | Any request involving writing, drafting, editing or composing text that isn't purely code (including GitHub PR descripti… |
| `clod-lens-empathy` | Empathy-driven design: think through how real people experience the software; surface and challenge… | When designing a user-facing flow and it's worth pausing to ask how it actually feels to a real person using it; especia… |
| `clod-lens-ethics` | Passive ethical review: manipulation, accessibility, privacy, sustainability in user-facing features… | When designing or reviewing a user-facing feature: dark patterns, accessibility gaps, privacy overreach or sustainabilit… |
| `clod-lens-scope` | Anti-scope-creep. Forces the question: what is the smallest thing that delivers value? | When a plan is quietly growing beyond the original ask, or the user sounds overwhelmed by scope; before committing to a… |
| `clod-role-api_designer` | Type-safe API design: Zod validation, Result types, SvelteKit endpoints, middleware patterns. | When designing or reviewing an API endpoint, request/response contract or validation layer; fires for API design, Zod sc… |
| `clod-role-data_ontologist` | Polyglot persistence: when to use relational, graph or document databases; integration patterns. | When choosing a data store or storage pattern for new data, or reviewing a schema or migration; fires on 'which database… |
| `clod-role-domain_modeller` | Model-first design: map entities, relationships and boundaries before writing code. | Before writing code for a new feature that introduces new entities or relationships: when the shape of the data model is… |
| `clod-role-frontend_styler` | Frontend styling: layout debugging, style consistency, CSS best practices for Svelte/SvelteKit. | When a layout is broken, styles are inconsistent across components or CSS needs a best-practice review; auto-loads only… |
| `clod-role-git_manager` | Git workflow: branch management, commit conventions, PR patterns, conflict resolution. | When a git operation needs judgement beyond a single command: resolving a conflict, deciding a branch/commit strategy or… |
| `clod-role-testing_obsessive` | Pragmatic testing with Vitest: risk-based strategy, Svelte component testing, test-after development… | When writing or reviewing tests, or deciding what's worth testing at all; fires on test coverage, Vitest setup and 'shou… |
| `clod-stack-cypher` | Neo4j and Cypher: graph schema design, query patterns, performance optimisation, PostgreSQL integrat… | When writing or reviewing Cypher queries, designing a graph schema or bridging Neo4j with a relational store; the Cypher… |
| `clod-stack-opentui` | OpenTUI terminal UI library reference: @opentui/core, terminal UIs, renderables, Yoga layouts, Zig-n… | When building or debugging a terminal UI with @opentui/core: renderable composition, Yoga layout issues or anything touc… |
| `clod-stack-svelte` | Svelte 5 and SvelteKit: runes reactivity, component composition, routing, data loading, form handlin… | When writing or reviewing Svelte 5 / SvelteKit code: runes ($state, $derived, $effect), routing and data loading. Auto-l… |
