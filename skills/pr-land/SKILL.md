---
name: "PR: Land"
description: "{{ ƔƔƔ }} Land an approved PR — merge to main, delete the branch, tag the version, sync the roadmap, clean up"
when_to_use: "When a PR is approved with checks green and the user wants it merged and the aftermath handled — including after hud-pr_wall shows a PR in the approved bucket."
model: sonnet
effort: medium
disable-model-invocation: true
allowed-tools: ["Read", "Bash(git:*)", "Bash(gh:*)", "Bash(~/.claude/library/scripts/safe-version-next.sh:*)", "Bash(python3:*)"]
arguments: ["pr"]
argument-hint: "[PR number | URL]"
---

# PR: Land

The post-approval sequence as one skill: verify the PR is genuinely ready, merge with a merge commit (granular commits are documentation — they belong on main), then handle everything a merge leaves behind: branch, worktree, version tag, roadmap.

## Hard rule — the version guard

**The 0.x → 1.x boundary is never crossed by this skill, under any circumstances.** Tagging v1.0.0 declares the API stable and only a human does that. The guard is programmatic: the tag always comes from `safe-version-next.sh`, which emits a 0.x minor bump when svu proposes 1.0.0 and passes every other bump through (2.x, 3.x major bumps are fine). Never call `svu next` directly here, and never hand-compute a tag.

## Step 1 — Verify readiness

Resolve the PR from `$ARGUMENTS`, then `gh pr view --json state,reviewDecision,mergeable,mergeStateStatus,statusCheckRollup,headRefName,baseRefName,title`.

Proceed only when: state `OPEN`, `reviewDecision` is `APPROVED`, no failing checks in `statusCheckRollup`, and `mergeable` isn't `CONFLICTING`. Anything short of that: report exactly what's unmet and stop — this skill lands ready PRs; it doesn't chase approvals (`pr-handle_review`) or fix branches.

## Step 2 — Confirm and merge

Show a one-line summary (title, head → base, review state, checks) and **await approval** — merging is irreversible in practice. Then:

```bash
gh pr merge {number} --merge --delete-branch
```

Merge commit, never squash or rebase: the branch's atomic commits are the history. `--delete-branch` removes the remote branch and, where the local branch isn't checked out elsewhere, the local one too.

## Step 3 — Tag the version

From the main checkout: `git checkout main && git pull`, then:

```bash
TAG="$("$HOME"/.claude/library/scripts/safe-version-next.sh)" && git tag "$TAG" && git push origin "$TAG"
```

Push the single tag, never `git push --tags` (that publishes every local tag, strays included). Script exit **3** means nothing to release — no version-bumping commits since the current tag (a docs-only or chore-only PR); say so and skip to Step 4. If the script printed its 0.x guard note to stderr, relay it: the user should know a major bump was requested and deliberately held at 0.x.

## Step 4 — Clean up the checkout

1. If a worktree held this branch (`git worktree list`), remove it — from **outside** it, never while the shell is inside; `cd` to the main checkout first, and return there after.
2. If the local branch survived (it was checked out somewhere), `git branch -d {branch}` — only `-d`; a refusal means unmerged commits and stops the line, not `-D`.
3. `git worktree prune`.

## Step 5 — Roadmap sync

If the repo has a rich roadmap (`python3 "$HOME"/.claude/library/scripts/roadmap.py detect` exits 0), offer to run the `roadmap-maintain` skill so the merged work's task lands as `done` and the projections refresh. Offer, don't assume — the PR may not map to a roadmap task.

## Step 6 — Report

PR merged (URL), tag created, branch/worktree state after cleanup, roadmap synced or skipped. If the changelog matters for this project, note that `doc-changelog` picks up from exactly this moment: new tag, fresh commits.

## Red flags

**Never:** cross 0.x → 1.x (the guard script is the only tag source); squash or rebase-merge; merge with failing or pending checks "because they'll pass"; remove a worktree from inside it; use `git branch -D`; tag before the merge has actually landed on main.

<raw-arguments value="$ARGUMENTS" />
