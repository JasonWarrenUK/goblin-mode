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
| `/artefact-audit` | opus | Audit a topic and render an actionable, status-grouped HTML findings artefact. |
| `/artefact-introduction` | opus | Render a visual HTML introduction to this codebase for a newly-joined developer |
| `/artefact-roadmap` | haiku | Generate the HTML roadmap dashboard deterministically via roadmap.py render. |
| `/config-permit` | haiku | Grant a permission rule globally or for the current project |
| `/doc-adr-create` | sonnet | Create an Architecture Decision Record (ADR) for a significant technical decision |
| `/doc-misc-update` | sonnet | Update an existing documentation file to reflect recent code changes |
| `/doc-readme` | sonnet | Create or update a README — project root or any directory |
| `/doc-status_report-create` | haiku | Create a status report that knows what you've done since the last one |
| `/git-branch-rename` | sonnet | Check the current branch name against convention (type/short-description) and rename it if it drifte… |
| `/git-branch-review` | opus | Assess branch readiness for PR submission |
| `/git-commit-batch` | haiku | Split uncommitted changes into granular commits. |
| `/git-commit-one` | haiku | Generate a commit message. If nothing staged, stage all changes. |
| `/git-integrate` | haiku | Integrate a target branch into the current one by merge, rebase or squash |
| `/pr-create` | sonnet | Create a pull request to main — wordy or shiny (with screenshots), ready-for-review or draft |
| `/pr-review-comment` | opus | Review a pull request and post it as a GitHub review |
| `/pr-update` | sonnet | Update a PR description to account for commits made since it was last written |
| `/project-analyse-critique` | opus | Probe the project for architectural weaknesses, technical debt, and risk — a deliberately critical r… |
| `/project-investigate-concept` | opus | Investigate a codebase in detail and write findings to a document, for a named concept, subsystem, o… |
| `/project-investigate-deps` | opus | Investigate this repo's dependencies in detail |
| `/project-scaffold-from_artefact` | opus | Convert an exported Claude artefact (HTML or JSX) into a working Svelte 5 / SvelteKit 2 project |
| `/roadmap-create` | opus | Create a project roadmap in the rich phase-array format — roadmaps.json as source of truth plus a PH… |
| `/roadmap-maintain` | opus | Recompute and synchronise roadmap task statuses across roadmaps.json and its projections |
| `/roadmap-migrate` | opus | Convert an old simple-style roadmap (single Markdown, four statuses, <a name> anchors, roadmaps.json… |
| `/roadmap-update-tasks` | opus | Add a task to a rich-format project roadmap with correct ID, dependency wiring, and graph integrity… |
| `/task-execute-minima` | haiku | Achieve what I say with a minimalist approach |
| `/task-execute-stud` | sonnet | Plan a non-trivial feature by interviewing to resolve unknowns, then studding every function as a ru… |
| `/task-suggest` | haiku | Suggest the next logical task — grounded in the roadmap's pre-vetted ready-set when one exists, code… |

---

## Model-Invocable Skills

Claude can load these automatically when relevant.

| Skill | Model | Description |
|-------|-------|-------------|
| `/help-whats_new` | sonnet | Summarise what the user can now see or do that they couldn't before this unit of work |
| `/pr-review` | opus | Review a pull request |
| `/roadmap-create-interview` | opus | Run a structured interview to discover new features and produce a batch roadmap proposal. Produces a… |

---

## Role Skills

Ambient knowledge roles (`role-*`), loaded by Claude when relevant.

| Skill | Description | When to use |
|-------|-------------|-------------|
| `role-approach-stud` | Use when about to build a non-trivial feature and you want the shape reviewable before the logic. St… | >=1 of the following are true: (a) spans several functions/files; (b) touches existing code in more than one place; (c)… |
| `role-expert-api_designer` | Type-safe API design: Zod validation, Result types, SvelteKit endpoints, middleware patterns. | When designing or reviewing an API endpoint, request/response contract, or validation layer — auto-loads on files under… |
| `role-expert-data_ontologist` | Polyglot persistence: when to use relational, graph, or document databases; integration patterns. | When choosing a data store or storage pattern for new data, or reviewing a schema/migration — auto-loads on schema or mi… |
| `role-expert-debug_dervish` | Systematic debugging methodology — runtime errors, test failures, logic bugs, performance issues, pr… | When something is broken and the cause isn't obvious yet — an error, a failing test, unexpected behaviour, or a performa… |
| `role-expert-domain_modeller` | Model-first design: map entities, relationships, and boundaries before writing code. | Before writing code for a new feature that introduces new entities or relationships — when the shape of the data model i… |
| `role-expert-frontend_styler` | Frontend styling: layout debugging, style consistency, CSS best practices for Svelte/SvelteKit. | When a layout is broken, styles are inconsistent across components, or CSS needs a best-practice review — auto-loads on… |
| `role-expert-testing_obsessive` | Pragmatic testing with Vitest: risk-based strategy, Svelte component testing, test-after development… | When writing or reviewing tests, or deciding what's worth testing at all — auto-loads on test/spec files, or when the co… |
| `role-linguist-cypher` | Neo4j and Cypher: graph schema design, query patterns, performance optimisation, PostgreSQL integrat… | When writing or reviewing Cypher queries, designing a graph schema, or bridging Neo4j with a relational store — auto-loa… |
| `role-linguist-opentui` | OpenTUI terminal UI library reference. Use when working with @opentui/core, terminal UIs, renderable… | When building or debugging a terminal UI with @opentui/core — renderable composition, Yoga layout issues, or anything to… |
| `role-linguist-svelte` | Svelte 5 and SvelteKit: runes reactivity, component composition, routing, data loading, form handlin… | When writing or reviewing Svelte 5 / SvelteKit code — auto-loads on .svelte files or +page/+layout files, or when runes… |
| `role-manager-git` | Git workflow: branch management, commit conventions, PR patterns, conflict resolution. | When a git operation needs judgement beyond a single command — resolving a conflict, deciding a branch/commit strategy,… |
| `role-viewpoint-ethics` | Passive ethical review: manipulation, accessibility, privacy, sustainability in user-facing features… | When designing or reviewing a user-facing feature — dark patterns, accessibility gaps, privacy overreach, or sustainabil… |
| `role-viewpoint-scope_coach` | Anti-scope-creep. Forces the question: what is the smallest thing that delivers value? | When a plan is quietly growing beyond the original ask, or the user sounds overwhelmed by scope — before committing to a… |
| `role-viewpoint-user_empathy-lens` | Empathy-driven design: think through how real people experience the software; surface and challenge… | When designing a user-facing flow and it's worth pausing to ask how it actually feels to a real person using it — especi… |
| `role-viewpoint-writing_style` | Writing style guide for Jason Warren. Applies whenever writing or editing substantive prose for Jaso… | Any request involving writing, drafting, editing, or composing text that isn't purely code — including GitHub PR descrip… |
