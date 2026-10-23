---
name: "Mission Control: Coordinate"
description: "How the coordinator session runs a mission-control run after kick-off: collect the briefs, settle the shared assumptions and criteria, grant slots from the machine's state, keep the board and the needs list true, decide what keeps sessions consistent and escalate the rest"
when_to_use: "In the coordinator session once a run exists: the SessionStart hook says 'this session coordinates run ...', or kick-off has just finished, or the user asks what mission control should do next. Not in a crew session (mission-control:crew) and not for closing the run (mission-control:end)."
model: opus
effort: high
metadata:
  glyph: ᛟ
  family: mission-control
  goblin-spinner: coordinating|granting slots|counting assumptions|rolling up needs
disable-model-invocation: false # the SessionStart hook names this skill to the coordinator session; every write it leads to goes through the ledger CLI, which authorises the coordinator alone; nothing here merges, resets or touches hosted
allowed-tools: ["Read", "Write", "Glob", "Grep", "Bash(python3:*)", "Bash(git:*)", "Bash(gh:*)", "Bash(lsof:*)", "Bash(pgrep:*)", "Bash(psql:*)", "AskUserQuestion", "mcp__mission-control__mc_board", "mcp__mission-control__mc_grant", "mcp__mission-control__mc_revoke", "mcp__mission-control__mc_assume", "mcp__mission-control__mc_send", "mcp__mission-control__mc_need", "mcp__mission-control__mc_report"]
argument-hint: "(no arguments)"
---

# Mission Control: Coordinate

The run loop. The protocol is `${CLAUDE_PLUGIN_ROOT}/references/protocol.md`; this skill is its coordinator half. The board is `/mc`; its text form is `mc_board`. The user reads the board, so every change of state also gets one line of prose in this chat (what changed, what it means for them), never a paragraph per event.

## The loop

1. **Briefs in.** Each crew session answers the five questions by message. Read every answer for overlaps (two sessions naming one file, function, table or route) and for assumptions about each other. Resolve each overlap with an ownership rule and set it as a numbered shared assumption (`mc_assume`). Append per-task criteria to each brief file in the ledger and send the session one line saying the brief changed.
2. **Slots.** A request arrives by message and on the board. Grant with `mc_grant`, which probes the machine first and refuses while the resource is busy: a running server, a stray process, a client on the database. Read its probe line before deciding; never grant on a message's say-so. One holder per resource. The grant tells the holder; the other sessions get a notice. An overdue slot is a question to the holder first, `mc_revoke` second.
3. **Hosted windows.** A session asking to measure on hosted gets a freeze line to everyone else (`mc_send` to `all`), then the window. The command itself goes on the needs list for the user (`mc_need` from the requesting session, or from here with the session named). Lift the freeze when the session reports back.
4. **Decisions.** Settle anything that only keeps sessions consistent: merge order, who owns a function, one scan not two. Escalate product, cost and hosted-configuration choices to the user with a recommendation, in one AskUserQuestion when they can wait and one line in chat when they cannot. A change of assumption that follows is broadcast by `mc_assume`, which numbers it.
5. **Trunk moves.** When the user says main moved, or a PR's CI goes red on a file nobody in the run touched: read the trunk commits, name what each session must do (`gh stack sync` from the stack worktree, or a plain rebase in its own worktree before the stack exists) and send it. A generated artefact that trunk changed without regenerating is the first thing to check.
6. **Check-ins.** When the user asks what they need to do, or every hour or so unprompted, run `/mission-control:checkin`. Its output is the needs list in three buckets with complete commands.
7. **PRs.** When the run's PR approval is `coordinator`, a crew session sends its draft PR description here. Review it against the brief's criteria and the house PR rules (the template's sections, no invented verification, the intended changelog wording in the description since nothing goes on the branch). Reply `PR approved` or the changes, in one message; the session then runs `pr-create auto`. When it is `user`, the session waits for the user and the needs list says so. Record the PR number when it arrives (`mc_report` is the crew's; a `pr open: #n` line here is enough for the board).
8. **Ending.** When every PR exists, hand over to `/mission-control:end`.

## What the coordinator never does

- runs a gated command, a reset, a server or a hosted command itself; it has no worktree and no slot
- asserts a project convention it has not read in the repository or had from the user in this run; it asks
- sets a bound that does not bound the work it names; a session that points this out is right
- relays a permission: a crew session's refusal is routed to the user with the exact command, never to another session
- messages by `name [ref]` when it can address by id: `mc_send` takes a task id, branch or name and resolves the session itself

## Prose that accompanies the board

One line per event, in this shape: `<task>: <what changed>. <what it means for you, or nothing>.` Examples: `10SE.4: holds local-db until 15:20 for its full reset; nothing from you.` `11HD.4: PR #198 open on main; review when you have an hour.` When the user asks for a one-line summary per session, read `mc_board` and write exactly that.
