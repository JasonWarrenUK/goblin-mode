---
name: "Start Trail"
description: "Start a trail (claim a roadbook waypoint, which is a task) when work on it starts, or release the claim when work stops: asks which scout is doing it, runs the CLI, commits the change"
when_to_use: "When the user says they are starting, taking or working on a roadbook waypoint or task (\"claim 2SE.1\", \"I'm picking up the search task\"), or wants to drop one (\"release 2SE.1\", \"I'm not doing that any more\"), or a goblin-scout hook nudge asks whether the branch is roadbook work. Never for setting an assignee without a start (goblin-scout:assign-scouts, or `roadbook.py assign`) or for marking work done (goblin-scout:tend-roadbook)."
model: sonnet
effort: low
metadata:
  glyph: ᛊ
  family: scout
disable-model-invocation: false # the trigger is the user saying they are starting a waypoint, which Claude sees first; the commit and push each await approval below
allowed-tools: ["Read", "Bash(python3:*)", "Bash(git:*)"]
arguments: ["task", "who"]
argument-hint: "[<waypoint id>] [<scout>|release]"
---

# Roadbook Trail

A trail is a claim: it says a scout has started a waypoint. The waypoint gains a `started` date and an `assignee`, and views show it as in progress. This skill is the one place that procedure lives; the branch-start hook nudge and `goblin-scout:tend-roadbook` both hand over to it.

Shared conventions: `${CLAUDE_PLUGIN_ROOT}/references/roadbook-conventions.md` (Trails section). The CLI is `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py`.

**Hard rule, inherited from the conventions:** an assignee is never inferred. Never propose or pre-fill a name from the waypoint text, git author or who owns neighbouring waypoints. The one name that may be offered is the waypoint's own current `assignee`.

---

## Step 0: Parse the arguments

Both arguments are optional and positional: passing `$who` requires `$task`.

| Call                    | Meaning |
|-------------------------|---------|
| (no arguments)          | pick a ready waypoint from a list, then start a trail on it |
| `<waypoint id>`         | start a trail on that waypoint; ask which scout is doing it |
| `<waypoint id> <scout>` | start it for that scout; nothing to ask |
| `<waypoint id> release` | drop the trail |

`release` is a reserved word in the `$who` slot, so a scout with that name needs `roadbook.py claim` run by hand. A multi-word name arrives quoted (`"Mary Ann"`); take the quoted string whole.

Match `$task` against the phase's waypoint ids exactly, then case-insensitively. No match: hard stop, print the usage line with the three closest ids and run nothing. Never guess a waypoint.

```text
Usage: /goblin-scout:start-trail [<waypoint id>] [<scout>|release]
```

---

## Step 1: Locate the roadbook

Run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py detect`. Exit **3** = old simple format: stop and tell the user to run `goblin-scout:rebind-roadbook` first. Exit **2** = could not locate or parse: ask the user for the path. Proceed only on exit 0.

**Phase selection.** List the phases in `roadbook.json` without `archived: true`. One active phase: use it. Several: ask with AskUserQuestion which to work on, listing the last active phase in the array first and marking it recommended. Pass the choice as `--phase "{name}"` on every later CLI call. Never pick silently between active phases.

---

## Step 2: Choose the waypoint (no `$task` only)

Run `roadbook.py ready --json`. Show the first 5 `candidates` (already in leverage order) as `{id}  {description}  (unblocks {transitiveUnblocks}, {milestoneName})`, and under them one line naming each waypoint in `claimed` as `On a trail: {id} ({assignee}, since {started})`, so nobody picks one twice. Ask which with AskUserQuestion, one option per candidate. An empty candidate list is a result: say `No ready waypoint without a trail.` and stop.

---

## Step 3: Start or release

**Where this runs.** Check this and the file's uncommitted state (Step 4, item 1) before running the CLI. Trails normally live on the branch doing the work (`git branch --show-current`). On the default branch, ask first with AskUserQuestion: **Start the trail here and leave it uncommitted** / **Cancel**. Whichever is chosen, skip the commit and push in Step 4 on the default branch.

**Start.**

1. `$who` given: that is the assignee. Otherwise ask in plain text, `Which scout is doing {id}?`, offering the waypoint's current `assignee` when it has one.
2. Run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py claim {id} --assignee="{name}"` with the Step 1 phase and path. Without an assignee answer, leave `--assignee` off.
3. Relay a refusal word for word. The cases: the waypoint is not ready to start (it reports its effective status; a blocked waypoint is refused only while some blocker has no trail or is a gate, and the refusal names them), it is already on a trail (whose, since when), it is assigned to someone else, or `roadbook.json` is not in canonical form. For the assignee case offer to hand the waypoint over, and rerun with `--reassign` solely when the user agrees. For the format case say that a write would reformat the whole file, and rerun with `--reformat` solely when the user agrees.

**Release.**

1. Run `roadbook.py release {id}` with the Step 1 phase and path. When the waypoint has an `assignee`, first ask once whether to clear it too; add `--unassign` only on yes.
2. A waypoint with no trail is reported as it is; nothing is written.

The CLI writes `roadbook.json` only. A trail has no PHASE file annotation and no overview line, so nothing else is edited here.

---

## Step 4: Commit and offer the push

Skip this step on the default branch and when the CLI refused.

1. Before Step 3 runs the CLI, note whether `roadbook.json` (the path `detect` reported) already has uncommitted changes: `git status --short -- {path}`. If it did, ask before committing: those changes would ride along.
2. Commit that file only: `git commit -m "chore(roadbook): claim {id}" -- {path}` (or `release {id}`).
3. Ask once whether to push the branch so the team sees the trail. Push (`git push -u origin {branch}`) only on yes.

---

## Step 5: Report

One line: `Trail started on 2SE.1 for Jaz (started 2026-10-02) on feat/search, committed, not pushed.` or the release equivalent. A trail needs no follow-up; the next action is the work itself.

---

## Red flags

**Never:** infer an assignee; edit `status` to `in_progress` (a trail is a field, never a status); hand-edit `started` or `assignee` in `roadbook.json` when the CLI can do it; use `--reassign` without the user agreeing to take the waypoint from its current owner; commit anything but `roadbook.json`; push without a yes.

> **Mirrored phases:** a waypoint mirrored from Jira cannot be claimed, released or assigned here; the CLI refuses and says so. Tell the user it is assigned in Jira and offer `roadbook.py pull` to refresh. A waypoint marked `"local": true` starts a trail as usual, with no commit when the roadbook file is `.claude/roadbook.local.json` (it is outside git).

<raw-arguments value="$ARGUMENTS" />
