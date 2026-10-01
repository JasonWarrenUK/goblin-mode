# Stacked Pull Requests

Shared reference for every skill that touches branch topology (`next-task-ship`,
`pr-create`, `pr-land`, `pr-handle_review`, `hud-worktrees`,
`clod-role-git_manager`). Skills point here instead of restating the mechanics.

GitHub's native stacked PRs entered public preview on 2026-07-30 and are
subject to change; when a command here misbehaves, verify against
<https://docs.github.com/en/pull-requests/how-tos/stacked-pull-requests>
before working around it.

## The model

A **stack** is an ordered chain of PRs in one repository. The bottom PR targets
the trunk (`main`); every PR above targets the branch of the PR below it. Each
PR shows only its own layer's diff, with a stack map at the top of the PR page.
Branch protection, CODEOWNERS and required checks are enforced on **every**
layer, including mid-stack PRs that don't target `main`.

**Merging is bottom-up and contiguous.** Merging any PR also merges every
unmerged PR below it, as one all-or-nothing operation; a mid-stack PR can never
merge in isolation. The PRs above stay open and automatically retarget the trunk
via a server-side cascading rebase. Once every layer has merged the stack is
closed; a later `gh stack submit` on new branches above it starts a new stack.

**Claude's shell has no terminal, and that changes what a command does.** In a
non-interactive terminal `gh stack merge` merges everything it names *without
prompting*. So `gh stack merge` with no argument lands the whole stack. The only
safe merge form is `gh stack merge <pr#> --merge` with the PR's own number. The
chirpdb project enforces this with a hook; other repos rely on this page.

## When to stack

Stack when new work **builds on a branch whose PR is still open**: the code
dependency is real and the parent hasn't merged. The alternative (branching
from `main`) produces a branch missing its prerequisite; the other alternative
(waiting) serialises work that reviews fine in parallel.

Don't stack when the branches are independent (parallel branches off `main`
remain the default; CLAUDE.md §8.6's "go smaller" means more independent
branches, not deeper stacks), and don't stack past **3 layers**: review burden
compounds and a conflict at the bottom cascades through everything above.

A stack is linear. Work depending on two unmerged parents on *different*
chains cannot be expressed as a stack; that's a genuine block, not a stacking
case.

## CLI: `gh stack`

Installed with `gh extension install github/gh-stack` (v0.1.0; gh ≥ 2.90 per
the quickstart). Verified against `gh stack <command> --help`.

| Command | Does |
|---|---|
| `gh stack init [-b <trunk>] [branches...]` | start a stack; existing branches become layers, missing ones are created |
| `gh stack add [branch] [-m <msg>]` | new branch on top of the current stack; with `-m` and no name the name comes from the message. **`-A`/`-u` without `-m` opens an editor: never.** |
| `gh stack submit [--auto] [--open]` | push all layers, create missing PRs, update bases, link the stack. Non-interactive implies `--auto`, and **new PRs are drafts unless `--open`** |
| `gh stack link <stack#\|branch-or-pr> <branch-or-pr>...` | build or extend a stack on GitHub from PRs and/or branches given bottom-to-top, no local tracking needed. A **stack number** first argument appends the rest to the top of that stack |
| `gh stack view [--json]` | layers, order, PR links (✓ merged, ◎ queued, ○ open, ⚠ needs rebase). Needs local tracking: exits 2 in a checkout that does not track the stack |
| `gh stack checkout <stack# \| pr# \| url \| branch>` | check a stack out; given a PR it can find the stack on GitHub and set up tracking |
| `gh stack rebase [--upstack\|--downstack] [--continue\|--abort]` | cascading rebase, each layer onto the one below |
| `gh stack push` | push all active layers (`--force-with-lease` per branch, not atomic); merged and queued layers are skipped |
| `gh stack sync [--prune]` | fetch, fast-forward trunk, cascade-rebase, push atomically, sync PR state. Aborts on divergence when non-interactive; never opens PRs. `--prune` deletes local branches whose PRs merged |
| `gh stack merge <pr#> --merge` | **the only safe merge form.** Merges that PR and every unmerged layer below it, all or nothing. Takes a stack number or a PR number (never a URL); a bare number is tried as a stack number first. **With no argument, a stack number, or in a shell with no terminal, it merges the whole named set without prompting.** A merge queue on the base branch takes the stack instead |
| `gh stack modify [--continue\|--abort]` | **full-screen interactive editor: Claude cannot drive it.** To restructure, unstack and `init` again, or ask the user |
| `gh stack unstack [--local]` | dissolve the stack (alias `delete`); queued or auto-merge PRs stay stacked |
| `gh stack up / down / top / bottom / trunk` | navigate layers (`switch` is interactive: never) |

Useful exit codes: 2 not in a stack, 3 rebase conflict, 6 branch is in more than
one stack, 8 stack locked by another process, 9 stacked PRs not enabled.

For PRs created by other means (e.g. `pr-create`): create the child PR with
`--base <parent-branch>`, then `gh stack link <stack#> <new-pr>` to append it to
the top of an existing stack (the stack number is on the GitHub stack UI), or
`gh stack link <parent-pr> <new-pr>` to start one. Branches built with plain git
and linked this way have no local tracking; run `gh stack checkout <pr#>` before
`rebase`, `sync` or `up`/`down` (inferred from the docs, not tested).

To add a layer to an existing stack from a clean checkout:
`gh stack checkout <pr#>`, `gh stack top`, `gh stack add -m "<message>" <branch>`,
`gh stack submit --auto --open`.

## Maintenance flows

**A lower layer changed** (review fix on the parent): from the parent branch,
commit, then `gh stack rebase --upstack` and `gh stack push`. Reviewed content
on the layers above survives; only parentage (and SHAs) change. GitHub's PR
view handles the force-push sanely because each PR diffs against its own base.

**Trunk moved / a layer merged**: `gh stack sync --prune`. Remaining layers
rebase onto the new trunk state and stale refs are pruned.

**Rebase conflict**: `gh stack rebase` stops and lists the files. Resolve,
`git add`, `gh stack rebase --continue`; or `--abort` to restore the
pre-rebase state.

## Hard caveats

- **Do not run plain `gh pr merge` on a stacked PR.** The docs say the legacy
  merge endpoints cannot merge a stack; what `gh pr merge` does to a stacked PR
  is untested here. Use `gh stack merge <pr#> --merge` (or the web UI).
- **The merge button on a PR lands every layer below it too** (and the top PR's
  button lands the whole stack). Say which layers it will land before anyone
  clicks it.
- **Every layer needs CI.** Required checks and review are judged on each layer
  against the stack's base, so a workflow filtered to `pull_request` on `main`
  leaves upper layers with no checks and unmergeable. Run CI on pull requests into
  any branch.
- **Auto-merge is not supported** on stacked PRs.
- **Same repository only**; cross-fork stacks don't exist. GitHub Desktop has
  no support.
- **Server-side rebases produce unsigned commits**, including the automatic
  retarget of the layers above after a merge. A repo requiring signed commits
  must rebase locally via `gh stack rebase` and `gh stack push` instead of the PR
  page's Rebase button.
- **Never rename or delete a branch that is the base of an open PR** (check
  `gh pr list --base <branch>`). `gh stack modify` can rename inside a stack but
  is interactive; Claude's route is to unstack, rename and `init` again, or to ask
  the user.
- Merge queues are supported, with progressive rollout reported at launch
  (layers queue in order; an ejected layer ejects everything above it). One
  quirk: the merge group may exceed the queue's size limit by up to 50% to keep
  a stack together.
- Everything must be in one repository with a straight chain; branching is not
  allowed.

## Interaction with this config's conventions

- **Merge commits**: `pr-land` and `doc-changelog` assume `gh stack merge --merge`
  leaves one merge commit per layer on `main`, bottom-up. The docs say only that
  the stack merges "in a single operation, ordered from the bottom up", so treat
  that as unverified and check `git log --first-parent` after the first real
  stacked landing.
- **One landing, one tag**: a multi-layer merge is a single landing event;
  `pr-land` tags once afterwards, not once per layer.
- **Roadmap linkage**: a task's optional `pr` field in `roadmaps.json`
  (see `library/references/roadmap-conventions.md`) records the PR that ships
  it. `next-task-ship` uses it to detect that a `done` dependency is still
  unmerged and stack on its branch rather than branching from `main`.
- **`svu` on a child layer** counts the parent's unmerged commits too; a
  pending-bump report on a stacked branch describes the stack, not the layer.
