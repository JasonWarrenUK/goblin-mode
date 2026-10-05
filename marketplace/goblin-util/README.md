# goblin-util

> [!NOTE]
> Two Claude Code mods from [goblin-mode](https://github.com/JasonWarrenUK/goblin-mode) for the machine you run sessions on. Both are immediate commands: they work while Claude is busy, and neither starts a turn.

---

## 1. Install

```sh
claude plugin marketplace add JasonWarrenUK/goblin-mode
claude plugin install goblin-util@goblin-mode
```

Needs Claude Code 2.1.287 or later. The panes draw in the terminal; the heartbeat and `/pain <text>` work everywhere.

---

## 2. `/pain`

Logs friction with Claude Code itself (the tool, never your project) into `~/.claude/library/state/cc-pain-points.json`, the file `hud-cc_releases` reads to recognise a fix in the changelog later. The `track-cc_pain` skill does the same by inferring your mood mid-turn; this is the direct channel.

| Form | What happens |
|---|---|
| `/pain the status line ate my prompt` | Appends the entry at once and prints `logged the-status-line-ate-my-prompt`. |
| `/pain` | Opens a small pane with the context line and an input. Enter logs it and closes the pane. Esc closes it. |

The entry carries the schema `library/state/README.md` documents. `sourceSession` is pre-filled with the repo, the branch and the last failed tool call's first line, so the record says where it bit. An open entry with the same description is not duplicated; you are told its id instead. Marking an entry resolved stays with the skill.

---

## 3. `/fleet`

Every session on this machine writes a heartbeat row to the plugin's shared store: repo, branch, whether a turn is running, the last tool it called and when. `/fleet` opens a pane listing them, this session first.

| Key | Does |
|---|---|
| `1` to `9` | Picks a row. A picked session that is not this one gets an input under the table. |
| Enter in the input | Sends the line to that session as a message, the same delivery as the SendMessage tool. The toast says whether it landed. |
| Esc | Closes the pane. |

A row that has not written for a minute reads `quiet`; one past the stale limit is dropped from the store by whichever session draws the pane next. A session that ends cleanly removes its own row.

---

## 4. Options

| Option | Default | What it does |
|---|---|---|
| `enabled` | true | The one switch for all of it. Off, the heartbeat stops and `/pain` and `/fleet` are not registered. |
| `heartbeat_seconds` | 15 | How often this session writes its row. |
| `stale_minutes` | 10 | A session silent for this long is forgotten. |

---

## 5. Files

| File | Holds |
|---|---|
| `hooks/register.tsx` | Both commands, the heartbeat, the two panes |
| `hooks/util.test.tsx` | Tests for the helpers, both forms of `/pain`, the fleet pane and the heartbeat |
| `types/index.d.ts` | The `$.state` contract: the picked session, the last failed tool, the branch |

Check it with `claude plugin validate marketplace/goblin-util --strict` and `claude plugin test marketplace/goblin-util`.
