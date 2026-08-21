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
unmerged PR below it, as one operation; a mid-stack PR can never merge in
isolation. After a partial merge, the PRs above automatically retarget the
trunk via a server-side cascading rebase.

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

Installed with `gh extension install github/gh-stack` (needs gh ≥ 2.0).

| Command | Does |
|---|---|
| `gh stack init [-b <trunk>] [branches...]` | start a stack; existing branches become layers |
| `gh stack add <branch>` | new branch at HEAD, added as the top layer |
| `gh stack submit` | push all layers, open one PR per layer with correct bases |
| `gh stack link <stack\|branch-or-pr> <branch-or-pr>...` | build a stack on GitHub from PRs and/or branches given bottom-to-top, no local tracking needed; existing PRs are used, bare branches get PRs created with correct base chaining |
| `gh stack view [--json]` | layers, order, PR links |
| `gh stack checkout <stack# \| pr# \| url \| branch>` | check a stack out |
| `gh stack rebase [--upstack\|--downstack] [--continue\|--abort]` | cascading rebase, each layer onto the one below |
| `gh stack push` | push all active layers (`--force-with-lease` per branch) |
| `gh stack sync [--prune]` | fetch, fast-forward trunk, rebase remaining layers onto it, push, sync PR state; `--prune` also deletes local branches whose PRs merged |
| `gh stack merge <pr#> [--merge\|--squash\|--rebase]` | merge a layer and everything below it, atomically (all or none). A bare number resolves as a *stack* number first, PR number second; when they could collide, `gh stack checkout <pr-url>` then a bare `gh stack merge` |
| `gh stack modify [--continue\|--abort]` | interactive restructure: drop, fold, insert, reorder, rename |
| `gh stack unstack [--local]` | dissolve the stack (open/draft/closed PRs leave it; merged ones stay) |
| `gh stack up / down / top / bottom / trunk` | navigate layers |

For PRs created by other means (e.g. `pr-create`), `gh stack link` is the
lightest path: create the child PR with `--base <parent-branch>`, then link it
to the parent's PR or stack.

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

- **Plain `gh pr merge` fails on a stacked PR**: the legacy merge endpoint
  can't merge stacks. Use `gh stack merge <pr#> --merge` (or the web UI).
- **Auto-merge is not supported** on stacked PRs.
- **Same repository only**; cross-fork stacks don't exist. GitHub Desktop has
  no support.
- **Server-side rebases produce unsigned commits.** A repo requiring signed
  commits must rebase locally via `gh stack rebase` and `gh stack push`
  instead of the PR page's Rebase button.
- **Closing a mid-stack PR blocks everything above it**; dissolve or
  restructure with `gh stack modify` rather than closing layers casually.
- **Never rename or delete a branch that is the base of an open PR** (check
  `gh pr list --base <branch>`); rename inside a stack only via
  `gh stack modify`.
- Merge queues are supported (layers queue in order; an ejected layer ejects
  everything above it). One quirk: the merge group may exceed the queue's
  size limit by up to 50% to keep a stack together.

## Interaction with this config's conventions

- **Merge commits survive**: `gh stack merge --merge` gives each layer its own
  merge commit on `main`, bottom-up, so `doc-changelog`'s `--first-parent`
  one-entry-per-PR view and `pr-land`'s merge-commit rule both hold.
- **One landing, one tag**: a multi-layer merge is a single landing event;
  `pr-land` tags once afterwards, not once per layer.
- **Roadmap linkage**: a task's optional `pr` field in `roadmaps.json`
  (see the `scheme` plugin's `references/roadmap-conventions.md`) records the PR that ships
  it. `next-task-ship` uses it to detect that a `done` dependency is still
  unmerged and stack on its branch rather than branching from `main`.
- **`svu` on a child layer** counts the parent's unmerged commits too; a
  pending-bump report on a stacked branch describes the stack, not the layer.
