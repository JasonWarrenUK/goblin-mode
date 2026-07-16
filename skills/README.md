# Skills

Slash commands and knowledge skills for Claude Code. Regenerate this index from frontmatter when skills change; do not hand-edit rows.

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
| `/git-branch-rename` | sonnet | Rename branch if needed |
| `/git-branch-review` | opus | Assess branch readiness for PR submission |
| `/git-commit-batch` | haiku | Split uncommitted changes into granular commits. |
| `/git-commit-one` | haiku | Generate a commit message. If nothing staged, stage all changes. |
| `/git-integrate` | haiku | Integrate a target branch into the current one by merge, rebase or squash |
| `/pr-create` | sonnet | Create a pull request to main — wordy or shiny (with screenshots), ready-for-review or draft |
| `/pr-review-comment` | opus | Review a pull request and post it as a GitHub review |
| `/pr-update` | sonnet | Update a PR description to account for commits made since it was last written |
| `/project-analyse-critique` | opus | Probe the project for weaknesses |
| `/project-investigate-concept` | opus | Investigate a codebase in detail |
| `/project-investigate-deps` | opus | Investigate this repo's dependencies in detail |
| `/project-scaffold-from_artefact` | opus | Convert an exported Claude artefact (HTML or JSX) into a working Svelte 5 / SvelteKit 2 project |
| `/roadmap-create` | opus | Create a project roadmap in the rich phase-array format — roadmaps.json as source of truth plus a PHASE tas… |
| `/roadmap-maintain` | opus | Recompute and synchronise roadmap task statuses across roadmaps.json and its projections |
| `/roadmap-migrate` | opus | Convert an old simple-style roadmap (single Markdown, four statuses, <a name> anchors, roadmaps.json pointe… |
| `/roadmap-update-tasks` | opus | Add a task to a rich-format project roadmap with correct ID, dependency wiring, and graph integrity — ID as… |
| `/task-execute-minima` | haiku | Achieve what I say with a minimalist approach |
| `/task-execute-stud` | sonnet | Plan a non-trivial feature by interviewing to resolve unknowns, then studding every function as a runnable… |
| `/task-suggest` | haiku | Suggest the next logical task — grounded in the roadmap's pre-vetted ready-set when one exists, codebase an… |

---

## Model-Invocable Skills

Claude can load these automatically when relevant.

| Skill | Model | Description |
|-------|-------|-------------|
| `/help-whats_new` | sonnet | Summarise what the user can now see or do that they couldn't before this unit of work |
| `/pr-review` | opus | Review a pull request |
| `/roadmap-create-interview` | opus | Run a structured interview to discover new features and produce a batch roadmap proposal. Produces a struct… |

---

## Role Skills

Ambient knowledge roles (`role-*`), loaded by Claude when relevant.

| Skill | Description |
|-------|-------------|
| `role-approach-stud` | Use when about to build a non-trivial feature and you want the shape reviewable before the logic. Studs eve… |
| `role-expert-api_designer` | Type-safe API design: Zod validation, Result types, SvelteKit endpoints, middleware patterns. |
| `role-expert-data_ontologist` | Polyglot persistence: when to use relational, graph, or document databases; integration patterns. |
| `role-expert-debug_dervish` | Systematic debugging methodology — runtime errors, test failures, logic bugs, performance issues, productio… |
| `role-expert-domain_modeller` |  |
| `role-expert-frontend_styler` |  |
| `role-expert-testing_obsessive` |  |
| `role-linguist-cypher` |  |
| `role-linguist-opentui` | OpenTUI terminal UI library reference. Use when working with @opentui/core, terminal UIs, renderables, Yoga… |
| `role-linguist-svelte` |  |
| `role-manager-git` |  |
| `role-viewpoint-ethics` |  |
| `role-viewpoint-scope_coach` |  |
| `role-viewpoint-user_empathy-lens` |  |
| `role-viewpoint-writing_style` | Writing style guide for Jason Warren. Use this skill whenever writing prose, reports, documentation, or any… |
