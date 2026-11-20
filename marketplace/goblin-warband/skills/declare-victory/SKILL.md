---
name: "Goblin Warband: Declare Victory"
description: "Close a raid: link the PRs into a stack once they exist, prune each worktree after its session has closed, keep one stack worktree, run the project's checks on the top layer, offer the roadbook follow-ups, archive the ledger"
when_to_use: "From the chief's session when every task has its PR, or the user says the raid is over. Not for landing PRs (pr-land) and not while a raider is still working."
model: opus
effort: medium
metadata:
  glyph: ᛟ
  family: warband
  goblin-spinner: linking the stack|dismissing raiders|archiving the ledger
disable-model-invocation: true
allowed-tools: ["Read", "Bash(python3:*)", "Bash(git:*)", "Bash(gh:*)", "Bash(sh:*)", "Bash(zsh:*)", "CronList", "CronDelete", "AskUserQuestion", "mcp__goblin-warband__warband_slate", "mcp__goblin-warband__warband_send"]
argument-hint: "(no arguments)"
---

# Goblin Warband: Declare Victory

The aftermath, in the order that avoids losing anyone's work. Landing is `pr-land`'s and happens later, at the user's pace; nothing here merges.

## Step 1: Where things stand

`warband_slate`, then the config's `stack_status` command (`warband.py --json status` has `config_path`; read `commands.stack_status`). For each raider's row: the PR number, its base, whether it is linked, chained or independent and whether the session is still live.

## Step 2: Link the stack

Only when every PR that belongs in it exists and each base is the branch below it. Order bottom to top by PR number and show the command before running it: `gh stack link <bottom> ... <top>`; a bottom PR not based on trunk needs `--base <parent>`. A PR that is independent stays off. The project's stacked-PR rules (the config's `conventions` list names them) win over anything here. Ask once with AskUserQuestion; the approval covers one command. Afterwards, re-run the stack status and relay it.

## Step 3: Worktrees

Most worktrees are already gone by now: a merged task's raider is dismissed mid-raid with `warband.py retire <task>`, and a row the slate reads as dismissed (stored as `retired`) is skipped here. For each closed session whose worktree remains, the slate's `live` flag is the test and a live session's worktree is never touched. A merged or closed PR's worktree goes through `warband.py retire <task>` (it removes, prunes and deletes the branch with `-d`, refusing a dirty tree or a running process). An open PR's worktree, from the main checkout: `git worktree remove <path>`, keeping the branch (the PR needs it), then `git worktree prune`. A dirty worktree is shown and left.

When a stack exists, one worktree holds it: `git worktree add <main>/<worktrees.dir>/stack-<n> <top branch>` (or keep one of the pruned ones and rename it on the user's say-so), then `gh stack checkout <top pr>` inside it. Say which worktree is the stack's and that `gh stack up`/`down` move between layers there.

## Step 4: Sync and check

From the stack worktree: `gh stack sync` when trunk moved (show the layers it will force-push first and ask), then the config's `commands.test`, `commands.lint` and `commands.contract` on the top layer. A failure is reported with its output; nothing is pushed over it.

## Step 5: Follow-ups

Everything the raid found and did not do (the orders' "out of scope" lines, the chief's notes, a measurement that was inconclusive, a scope the user withdrew) is offered to the roadbook: read the rulings record first (`python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/warband.py decide list`), since what the user decided to defer is written there in their words, then list the items and say `/goblin-scout:add-waypoints` adds them as a batch of waypoints. A task planned `--unlisted` has no waypoint to update; name it as a candidate for one. Offer, do not run.

## Step 6: Archive

First the scheduled work this session still holds, so nothing fires against a raid that no longer exists: `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/warband.py jobs list` names each job this session recorded (kept on the raid for the chief, which has no row: the `wake` cron from the lead-raid skill, any other cron or Monitor it recorded); delete each cron with CronDelete (CronList shows the ids) and mark each `jobs done <id>`. A wake left running would prompt an empty session every half hour.

Then `warband.py end` from this session (it refuses while dibs are held; `/release-dibs <resource>` first, after asking the holder). The ledger moves to `~/.claude/goblin-warband/runs/<date>-<name>/`, orders and log included. Then one closing paragraph for the user: the PRs and their stack, the worktree that remains, what `pr-land` will land in which order, the rulings the raid recorded (from `decide list`, numbered, in the user's words) and the waypoints offered.

## Never

Merge anything; prune a worktree whose session is live or whose tree is dirty; `git merge` trunk into a layer; link PRs out of base order; end the raid with dibs held without asking their holder.
