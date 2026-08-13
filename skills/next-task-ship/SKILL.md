---
name: "Ship: Next"
description: "Autonomously run the full delivery loop for the next roadmap task — suggest, worktree, implement, roadmap-sync, PR, self-review"
when_to_use: "When you want to hand over a whole task cycle unattended: pick the next unblocked roadmap task, build it in an isolated worktree with tests green, keep roadmaps.json and its projections coherent, open a PR, and have it self-reviewed and fixed before handing back control."
model: fable
effort: high
metadata:
  glyph: ᚠ
  family: next-task
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Edit", "Write", "Bash(git:*)", "Bash(gh:*)", "Bash(python3:*)", "Bash(node:*)", "Bash(jq:*)", "Bash(npm:*)", "Bash(bun:*)", "Bash(pnpm:*)", "Bash(deno:*)"]
argument-hint: "[assignee] [focus area] (both optional, forwarded to next-task-suggest)"
---

# Ship: Next — the full delivery loop, unattended

Orchestrates four existing skills (`next-task-suggest`, `roadmap-maintain`, `pr-create`, `pr-review`) plus the mechanical git/test/lint work between them into one autonomous cycle: pick a task, build it in isolation, keep the roadmap coherent, open a PR, self-review it, fix what's actionable.

This skill does not reimplement any of those four skills' methodology — it invokes them and carries their outputs forward. Where this file's instructions and a called skill's own instructions conflict on *how* to do that skill's job, the called skill wins; this file only owns sequencing, the git/test/lint mechanics between them, and the hard rules below.

## Hard rules (never break these)

1. **Roadmap files are never hand-edited.** `.claude/roadmaps.json` is the only source of truth. Never directly edit the PHASE file's task list, the Mermaid block, `ROADMAP_OVERVIEW.md`, or the HTML artefact — those are `roadmap-maintain`'s job, driven off `roadmaps.json`. If something about the roadmap looks wrong, fix `roadmaps.json` (or flag it) and let `roadmap-maintain` propagate it.
2. **Never run `git stash` blind.** Before any stash, run `git status` and `git stash list` first, and only stash what those show is genuinely in the way. Prefer not stashing at all when a worktree already isolates the work.
3. **Unmet dependencies → stop and write `BLOCKED.md`, never guess.** If the suggested task turns out to have an unmet dependency, an ambiguous requirement no reasonable default resolves, or a blocker `roadmap-maintain`/`next-task-suggest` didn't already surface, stop the loop at that point and write a `BLOCKED.md` report (template in Step 8) instead of improvising a workaround.
4. **The gate loop is capped at 6 rounds.** Step 3's implement/test/typecheck/lint cycle gets at most 6 fix-and-rerun rounds. If the gate still isn't green after the sixth, stop and write `BLOCKED.md` with the failing output — a gate that won't converge means the task is misunderstood or the ground is broken, and grinding on it unattended burns usage without progress. The same cap applies to Step 7's post-review fix gate.

## Step 0 — Parse arguments

`$ARGUMENTS` forwards verbatim to `next-task-suggest` (assignee and/or focus area, same parsing rules as that skill's Step 0). No arguments is the common case — just "give me the next thing".

## Step 1 — Suggest the next task

Invoke the `next-task-suggest` skill with `$ARGUMENTS`. Take its chosen task (roadmap ID, description, dependencies) as this run's target. If `next-task-suggest` reports no ready candidate (empty candidate set, or an assignee filter matched nothing and the fallback pick also looks wrong for this loop), stop here — write `BLOCKED.md` (Step 8) rather than picking arbitrarily.

Cross-check the chosen task's `dependsOn` against `roadmaps.json` directly: every dependency must show `status: done`. `next-task-suggest`'s `ready` set should already guarantee this, but this is the hard-rule-3 checkpoint — if anything is unmet, stop and write `BLOCKED.md` now, before touching git.

## Step 2 — Worktree and branch

1. `git status` on the main checkout — confirm it's clean enough to branch from (uncommitted work here is the user's, not this task's; if present, stop and ask rather than assuming it's abandoned).
2. Derive a branch name from the task: `<prefix>/<short-description>` per the branch-naming convention (`feat/`, `fix/`, `enhance/`, `refactor/`, `test/`, `docs/`, `config/` — pick the prefix from the task's nature). Check it doesn't already exist (`git branch --list`, `git worktree list`) before creating — reuse rather than duplicate if it does.
3. Create the worktree: `git worktree add <path> -b <branch-name>` (path convention: sibling directory, e.g. `../<repo>-worktrees/<branch-name>`, or the project's existing worktree convention if `git worktree list` shows one already).
4. Install dependencies inside the new worktree before doing anything else there — `git worktree add` never carries over `node_modules` (it's gitignored), so skipping this produces confusing false-positive failures (missing-module errors, generated-config-dependent path aliases like SvelteKit's `$lib` failing to resolve) that look like real bugs but are just a bare worktree. Use the project's package manager (`bun install` / `npm install` / etc, per the ecosystem preference order) and, if the project has a codegen step its own tooling depends on (e.g. `svelte-kit sync`), run that too before trusting any test/typecheck output from this worktree.
5. All subsequent steps operate inside this worktree, not the main checkout.

## Step 3 — Implement with tests

1. Implement the task as described in `roadmaps.json` / the PHASE file entry. Follow the project's existing conventions (read nearby code before writing) rather than this file's general style defaults where the two differ.
2. Write tests alongside the implementation — this is in-scope by default per testing convention, not an optional extra.
3. Discover the project's test, typecheck, and lint commands from `package.json` scripts (or the equivalent for the project's ecosystem) rather than guessing flags.
4. Run all three — full test suite, typecheck, lint — and iterate until every one is green. Do not silence or skip a failing check; fix the underlying issue. If a failure traces back to something outside this task's scope (pre-existing breakage unrelated to the change), stop and report it rather than expanding scope to fix it unasked — this is a "flag assumptions" moment, not a "guess and proceed" one.
5. Re-run all three together once more after the last fix, to catch cross-check regressions (a lint fix that breaks a test, etc).

## Step 4 — Roadmap sync

Invoke the `roadmap-maintain` skill (plain status-sync run, not `reconcile` — this task's completion is already known and explicit, not something to infer from a codebase scan) to mark the shipped task `done` in `roadmaps.json` and propagate to the PHASE file, the Mermaid diagram, `ROADMAP_OVERVIEW.md`, and the HTML artefact. This is the only sanctioned way any of those projected files change — never hand-edit them in this step or any other.

Confirm its Step 7 validation report comes back clean before continuing.

## Step 5 — Commit

Commit the implementation and the `roadmaps.json` change (plus its synced projections) using Conventional Commits (`type(scope): description`), split into granular thematic commits rather than one giant commit — typically: one or more commits for the implementation/tests, one for the roadmap sync. Flag any breaking-change signal (removed/renamed exports, changed signatures, schema/API/env changes) with a `BREAKING CHANGE:` footer or `!` per the breaking-change convention — do not silently omit it.

## Step 6 — Open the PR

Invoke the `pr-create` skill from this branch. Let it draft the description from the commits and stop for its own approval step — this orchestrator does not bypass that; show the draft and wait before it creates the PR. Once approved and created, capture the PR URL/number.

## Step 7 — Self-review and fix

1. Invoke `pr-review` against the PR just opened. It posts a real GitHub review (inline comments + verdict) — let it run its full methodology (via `pr-review` underneath) rather than re-deriving findings here.
2. Read back the posted findings. Anything marked actionable and correctness/quality-bearing (not stylistic bikeshedding, not a finding the review itself flags as low-confidence) gets fixed in a **follow-up commit** on the same branch — never amend the commits already reviewed.
3. Re-run the full test/typecheck/lint gate (Step 3.4) after the fix commit, same bar: all green.
4. Push the follow-up commit. Do not re-invoke `pr-review` again automatically after fixing — one self-review cycle per run. If the findings warrant a second look, say so and let the user decide whether to loop again.

## Step 8 — BLOCKED.md (only if a hard rule triggers a stop)

Written to the repo root (main checkout, not the worktree, so it survives worktree cleanup) when Step 1's dependency check, Step 2's dirty-tree check, or any other genuinely unresolved ambiguity stops the loop. Never write this file speculatively — only on an actual stop.

```markdown
# BLOCKED — <task ID>: <short description>

**Stopped at:** Step <N> — <step name>
**Reason:** <what's unmet — a specific dependsOn ID not done, an ambiguous requirement, a pre-existing test failure unrelated to this task, etc.>

## What was checked
<the specific evidence — dependsOn IDs and their actual status from roadmaps.json, the git status output, the failing check output, etc.>

## What would unblock this
<the concrete next action — "mark TASK-4 done first", "resolve the ambiguity in roadmaps.json's notes field for this task", "a human decision on X">
```

Report the file's location and a one-line summary; do not attempt to guess past the blocker.

## Red flags

**Never:** hand-edit the PHASE file, Mermaid block, `ROADMAP_OVERVIEW.md`, or HTML artefact directly: `roadmap-maintain` only. **Never:** `git stash` without checking `git status` and `git stash list` first. **Never:** invent a resolution to an unmet dependency or genuine ambiguity: write `BLOCKED.md` instead. **Never:** push with a red test/typecheck/lint gate. **Never:** amend a commit `pr-review` already reviewed — fix findings in a new commit. **Never:** skip `pr-create`'s own approval pause for the PR description.

<raw-arguments value="$ARGUMENTS" />
