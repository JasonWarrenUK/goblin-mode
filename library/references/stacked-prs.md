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
the quickstart). Verified against `gh stack <command> --help`, which wins over
any command detail on this page: the extension is pre-1.0 and its flags move.
GitHub also publishes a `gh-stack` agent skill (`github/gh-stack`, `skills/gh-stack`)
covering exit codes and recovery; this page records only what a project decides
on top of the commands and what the script below reads.

| Command | Does |
|---|---|
| `gh stack init [-b <trunk>] [branches...]` | start a stack; existing branches become layers, missing ones are created. **Adopting an existing chain** is `gh stack init <bottom> <middle> <top>`, one shot; it writes local tracking only, and a second run answers `branch "<bottom>" already exists in a stack`, which means the first run worked. Prefer `gh stack link` when the PRs already exist and no local tracking is wanted |
| `gh stack add <branch>` | new branch on top of the current stack; opens no editor and carries uncommitted changes over. **`-m` creates a commit, so on a clean tree `add -m` dies with `nothing to commit`** (verified on v0.1.0). **`-A`/`-u` without `-m` opens an editor: never.** |
| `gh stack submit [--auto] [--open]` | push all layers, create missing PRs, update bases, link the stack. Non-interactive implies `--auto`, and **new PRs are drafts unless `--open`**; `--open` also flips *existing* draft layers to ready, so leave it off when linking PRs that are drafts on purpose. With every layer already a PR it links them and opens no editor (verified on chirpdb #191). Run it from a layer, not the trunk: from `main` it fails with `branch "main" belongs to multiple stacks` whenever a stale stack shares the trunk |
| `gh stack link <stack#\|branch-or-pr> <branch-or-pr>...` | build or extend a stack on GitHub from PRs and/or branches given bottom-to-top, no local tracking needed. A **stack number** first argument appends the rest to the top of that stack |
| `gh stack view [--json]` | layers, order, PR links (✓ merged, ◎ queued, ○ open, ⚠ needs rebase). Needs local tracking: exits 2 in a checkout that does not track the stack |
| `gh stack checkout <stack# \| pr# \| url \| branch>` | check a stack out; given a PR it can find the stack on GitHub and set up tracking. Fails with `pathspec '<branch>' did not match` when a tracked layer's local branch has been deleted (a pruned worktree takes its branch with it) |
| `gh stack rebase [--upstack\|--downstack] [--continue\|--abort]` | cascading rebase, each layer onto the one below |
| `gh stack push` | push all active layers (`--force-with-lease` per branch, not atomic); merged and queued layers are skipped |
| `gh stack sync [--prune]` | fetch, fast-forward trunk, cascade-rebase (only when trunk moved), push with `--force-with-lease`, sync PR state. When local and remote have diverged and the shell is non-interactive it changes nothing and **exits 0 printing `Sync aborted`**, so check the output, never the exit code alone; never opens PRs. `--prune` deletes local branches whose PRs merged, **in the current stack only**; a stale stack elsewhere in tracking is `unstack`'s job |
| `gh stack merge <pr#> --merge` | **the only safe merge form.** Merges that PR and every unmerged layer below it, all or nothing. Takes a stack number or a PR number (never a URL); a bare number is tried as a stack number first. **With no argument, a stack number, or in a shell with no terminal, it merges the whole named set without prompting.** A merge queue on the base branch takes the stack instead. `--yes` is implied without a terminal and `--merge` pins the method (the no-squash rule in `pr-land`); GitHub's own skill shows `merge <pr#> --yes` and so reuses the last-used method |
| `gh stack modify [--continue\|--abort]` | **full-screen interactive editor: Claude cannot drive it.** To restructure, unstack and `init` again, or ask the user |
| `gh stack unstack [<stack#>] [--local]` | dissolve the stack (alias `delete`); queued or auto-merge PRs stay stacked. `unstack <n> --local` drops only the local tracking entry, which is the fix for a stale stack whose PRs have all merged: it needs no checkout, and `checkout <n>` cannot reach a stack whose branches are gone |
| `gh stack up / down / top / bottom / trunk` | navigate layers (`switch` is interactive: never) |

Useful exit codes: 2 not in a stack, 3 rebase conflict, 6 branch is in more than
one stack, 8 stack locked by another process, 9 stacked PRs not enabled. The
multi-stack refusal (usually the checked-out branch being the trunk of several
stacks) is exit 6 from `view` but exit 2 from `sync`, `rebase` and `up` in a
non-interactive shell on v0.1.0, so match the `belongs to multiple stacks` text.
The fix is `gh stack checkout <a branch unique to the intended stack>`.

For PRs created by other means (e.g. `pr-create`): create the child PR with
`--base <parent-branch>`, then `gh stack link <stack#> <new-pr>` to append it to
the top of an existing stack (the stack number is on the GitHub stack UI), or
`gh stack link <bottom...> <parent-pr> <new-pr>` to start one, with every PR of the
parent's chain in order (just `<parent-pr> <new-pr>` when the parent sits alone).
Link by PR number: a branch argument makes `link` push it and open a PR with an
auto-generated title. A parent with two open children cannot be linked as one
line; pick a path. Branches built with plain git
and linked this way have no local tracking; run `gh stack checkout <pr#>` before
`rebase`, `sync` or `up`/`down` (inferred from the docs, not tested; `init` +
`submit` is the tested route, chirpdb #191, 2026-10-21).

To add a layer to an existing stack from a clean checkout:
`gh stack checkout <pr#>`, `gh stack top`, `gh stack add <branch>`, commit the
work, then `gh stack submit --auto --open`.

## Three sources of truth, and the script that reads them

A PR can be **chained** (its base is another open PR's branch) without being
**linked** (GitHub's `stack` field on the PR is null): the chain gives the right
diffs, the link gives the stack map, the retarget after a merge and `gh stack
merge`. Guessing from the base branch gets this wrong in both directions
(chirpdb #139 on 2026-10-01, #187 to #189 on 2026-10-21). The third source is
**local tracking**: the `gh-stack` JSON file listing each stack's trunk,
branches and PR numbers. Where it lives depends on the extension version.
v0.1.0 (installed here) joins it onto `git rev-parse --git-dir`, so the main
checkout's file is `.git/gh-stack` and a linked worktree has its own at
`.git/worktrees/<admin name>/gh-stack`: nothing is shared, and a stack checked
out in a worktree is untracked from every other checkout (chirpdb #200 on
2026-10-26, where the common-dir file held `"stacks": []` while the worktree's
held the stack). v0.2.0 moved it to `<git common dir>/gh-stack`, one catalogue
for every worktree, and migrates the per-worktree files on first run, keeping
each as `gh-stack.pre-worktree-migration`. The script asks `gh stack --version`
and reads both locations, counting only the one that version reads from the
current checkout (`gh_stack_version`, `tracking_files` and a per-stack `active`
in its JSON); the other file's stacks are listed as not read from here. The
extension is installed once per machine, so every repo on it sees the same
version; a project's vendored `gh-stack` skill may pin another.
`sync`, `rebase`, `up`, `down`, `top` and `view` need the current branch in it;
`link` and `merge` do not.

`~/.claude/library/scripts/stack-status.py [--json] [--open] [branch|pr ...]`
reads all three and prints one verdict per target:

| Verdict | Means | Do |
|---|---|---|
| `linked` | GitHub holds the stack | `gh stack` commands apply; `checkout <pr#>` first when the row says the branch is missing or untracked here |
| `chained-unlinked` | bases form a chain, GitHub has no stack | `gh stack link <bottom> ... <top>`, never `init` |
| `independent` | ordinary PR, on the trunk or on a base no open PR owns (`release/1.x`) | nothing |
| `no-pr` | no open PR | nothing to stack yet |

It also lists every tracked stack and marks one stale when every layer has a PR
and GitHub reports each as `MERGED` (`gh stack unstack <n> --local`). The tracking
file's own `merged` flag only refreshes on `gh stack sync`, so the script asks
GitHub; a closed PR, a layer with no PR yet or an unreadable state keeps a stack
live. A branch tracked in several stacks shows all of them (`tracked_in`). Tests:
`test_stack_status.py` beside it.

## Maintenance flows

**A lower layer changed** (review fix on the parent): from the parent branch,
commit, then `gh stack rebase --upstack` and `gh stack push`. Reviewed content
on the layers above survives; only parentage (and SHAs) change. GitHub's PR
view handles the force-push sanely because each PR diffs against its own base.

**Trunk moved / a layer merged**: `gh stack sync --prune`. Remaining layers
rebase onto the new trunk state and stale refs are pruned. **Never `git merge
main` (or the parent) into a layer.** GitHub's model is rebase throughout: the
server-side cascade after a landing is a rebase, `sync` and `rebase` replay only
non-merge commits (so a merge commit on a layer vanishes at the next rebase and
its SHAs move anyway), and `gh stack modify` refuses a stack whose history is
not linear. Merge commits belong at the landing (`--merge`), not inside a layer.
Someone else rebased the stack: `gh stack sync` from your checkout fast-forwards
to the pushed state; a `git pull` would merge the old tip back in.

**Local branches gone** (a pruned worktree deletes its branch): local tracking
still lists them, `up`/`down` and `sync` fail, and `stack-status.py` says
"branch missing". `gh stack checkout <pr#>` fetches the layers back.

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

## Worktrees: one per stack

Git checks a branch out in one place only, and every `gh stack` navigation or
rebase is a `git checkout` of each layer in turn inside one working tree. A
layer checked out in another worktree makes `up`, `down`, `top`, `rebase` and
`sync` fail on it. Claude Code's worktree isolation adds the other half: from
inside a worktree it refuses `git -C <other worktree>` and any command it
cannot verify stays put, so touching a sibling worktree means leaving this one.
Three layers in three worktrees therefore cost three `EnterWorktree` moves and
three hand merges (chirpdb, 2026-10-21).

So: **one worktree per stack**, named for the stack or its bottom branch, and
`gh stack up`/`down` to move between layers inside it. `branch-worktree new` on
a branch that `stack-status.py` reports as `linked` enters that stack's
worktree instead of adding one; bootstrap runs once per stack. A second
worktree on the same stack is for a second session on a different layer, and
two sessions rebasing one chain is the thing to avoid, so it is rare.

## Interaction with this config's conventions

- **Detection comes from `stack-status.py`**, never from the base branch alone:
  `pr-land` reads its verdict before choosing `gh pr merge` or `gh stack merge`,
  `pr-create` reads it before offering `gh stack link`, and `branch-stack` is
  the command skill for everything that changes a stack without opening or
  landing a PR (link, sync, tidy).

- **Merge commits**: `gh stack merge {top-pr} --merge` leaves **one merge commit
  for the whole stack**, titled for the top PR, not one per layer. Verified on
  the-work, 2026-10-15: a two-layer stack (#48 below #49) landed as a single
  commit `6566e9e` with two parents (the old `main` tip and the top layer's
  head). The lower layer's commits are reachable through that second parent, so
  the granular history survives, but `git log --first-parent` shows one line
  for the stack and the lower PR is merged only as far as GitHub's UI is
  concerned. Consequences: `doc-changelog` cannot build one entry per layer from
  first-parent history (read `git log --no-merges previousTag..tag`, or the
  stack's PR titles, instead), and the `pr` fields on the lower layers' roadmap
  tasks still point at the right PR.
- **One landing, one tag**: a multi-layer merge is a single landing event;
  `pr-land` tags once afterwards, not once per layer.
- **Roadmap linkage**: a task's optional `pr` field in `roadmaps.json`
  (see `library/references/roadmap-conventions.md`) records the PR that ships
  it. `next-task-ship` uses it to detect that a `done` dependency is still
  unmerged and stack on its branch rather than branching from `main`.
- **`svu` on a child layer** counts the parent's unmerged commits too; a
  pending-bump report on a stacked branch describes the stack, not the layer.
