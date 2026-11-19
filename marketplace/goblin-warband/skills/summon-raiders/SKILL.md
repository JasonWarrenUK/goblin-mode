---
name: "Goblin Warband: Summon Raiders"
description: "Ask every raider the three check-in questions, wait for the replies, and give the user one list of the tribute they owe, in three buckets, every command complete with its directory"
when_to_use: "From the chief's session when the user asks what they need to do, 'anything needed from me?', 'check in with each session', or when the chief has not heard from a raider in a while."
model: opus
effort: medium
metadata:
  glyph: ᛟ
  family: warband
  goblin-spinner: summoning raiders|waiting for replies|tallying tribute
disable-model-invocation: false # the trigger is the user asking what they need to do, which the chief sees first; the skill only sends messages and edits the tribute list
allowed-tools: ["Read", "Bash(python3:*)", "mcp__goblin-warband__warband_slate", "mcp__goblin-warband__warband_send", "mcp__goblin-warband__warband_tribute", "mcp__goblin-warband__warband_report"]
argument-hint: "(no arguments)"
---

# Goblin Warband: Summon Raiders

Three questions out, one list back. The list is the whole output; the user asked for it twice on the first raid because prose updates scrolled away.

## Step 1: Ask

`warband_slate` first, so the list starts from what the ledger already knows (states, dibs, owed tribute), then `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/warband.py reconcile`. Fix what it prints before asking anyone: a merged PR's row to `done` with `warband_report`, a tribute the user has plainly paid marked paid, so the questions go to sessions that are still working and the list does not repeat an item already handled. Drift that cannot be fixed from here (a raider's task never joined, a trail the roadbook on main lacks) opens the list as its own bucket; an `unlisted` line is not drift and stays off the list. A raider's row that reads `waiting on you` is skipped: that session sits on a permission prompt or a question in its own window and cannot answer, so the list opens with its window, the way lead-raid step 0a says, rather than waiting on a reply that arrives only after the user has been there. Then one message to every live raider (`warband_send` to `all`); its reply names any session that is waiting on the user, and that session's SendMessage call is dropped, since the question would sit unread behind the prompt:

```text
Check-in from the chief; reply in three lines. (1) Current state of your branch and anything uncommitted. (2) Exactly what you need from the user right now, as the commands they would type, or "nothing". (3) Anything blocking you that is not the user.
```

## Step 2: Wait

Replies arrive as messages over the next minutes. A session that is mid-tool answers when its turn ends. Wait for every live session except one whose row reads `waiting on you` (it was not asked, and its window is already the first line of the list), up to a few minutes; a silent one is reported as `no reply; last report <summary> at <time>`, never guessed at.

## Step 3: The list

Record every item from a reply's answer 2 with `warband_tribute` (why, the exact command, the absolute directory, `pr` when it blocks one; kind `question` for a question with no command), so the slate and the spoils page carry it too. Then write the list in this chat, in three buckets, nothing else above it:

```markdown
## Tribute

### Drift

- <task>: <what reconcile found and the one command or action that fixes it>.

### Now

1. **<task>: <one line>.** `cd <absolute worktree>/<run_from> && <command>`: <what it unblocks>.

### Right after <the thing it queues behind>

2. ...

### Agreed

- <task>: tribute <n>, <what it is>, since <start time>; <where it is watched>. Paste the result with `/pay-tribute <n>` when it finishes.

### Nothing from you

- <task>: <state, one line>.
```

Rules for the list: every command is complete, with its `cd`, because the user's `!` shell may be standing in another checkout; a hosted command says `read-only` or `writes` in the line; an approval names the session to visit; dibs that the chief will grant on a release are stated as such, with who they wait on; a PR waits on the reviewer `reconcile` names, never on "the user" unless the user is that reviewer or the merge is theirs. A tribute whose status is `started` (agreed on the slate: the user typed it and it runs on; the slate's `Tribute agreed` group) goes under `Agreed` and never under `Now`: it needs nothing typed until its result is in. A bucket with nothing in it is left out, `Drift` and `Agreed` included.

## Step 4: Keep it true

When the user does an item, they press `d` on it in the slate or run `/pay-tribute <n>`; the session that asked can also clear it with the next `warband_report`. When the user says they have typed one that runs on (a backfill, a long hosted measurement), mark it agreed on their word: `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/warband.py needs start <n> --note "<the background task id, or the session watching it>"` from here, or the user's own `s` on the slate or `/agree-tribute <n> [note]`. It then leaves the `Now` bucket and the tribute count and closes as every tribute does, with `/pay-tribute <n>` and the result. An open item that stays past the next check-in is repeated at the top of the new list, marked `still open`.
