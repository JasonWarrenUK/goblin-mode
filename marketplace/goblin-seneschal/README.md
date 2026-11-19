# goblin-seneschal

*Your grievance has been noted and filed with the others, my liege. The underlings are mustered and the chambers stand inspected.*

> [!NOTE]
> A Claude Code plugin from [goblin-mode](https://github.com/JasonWarrenUK/goblin-mode) for the machine you run sessions on: two mods and six skills. The mods are immediate commands: they work while Claude is busy, and neither starts a turn. The seneschal's words: a grievance is a complaint about Claude Code itself, an underling is a Claude Code session, a chamber is a worktree.

---

## 1. Install

```sh
claude plugin marketplace add JasonWarrenUK/goblin-mode
claude plugin install goblin-seneschal@goblin-mode
```

Needs Claude Code 2.1.287 or later. The panes draw in the terminal; the heartbeat and `/log-grievance <text>` work everywhere. Renamed from `goblin-util` at 1.0.0: an existing install moves to the new name by itself, and `/plugin install goblin-seneschal@goblin-mode` once in a session fetches the new copy if Claude Code reports it not cached. The file of grievances moves too (section 2.1).

---

## 2. `/log-grievance`

Logs a grievance with Claude Code itself (the tool, never your project) into the grievances file, `~/.claude/library/state/grievances.json` unless the `grievances_file` option says otherwise. `proclaim-releases` reads the same file to recognise a fix in the changelog later. The `overhear-grievance` skill does the same by inferring your mood mid-turn; this is the direct channel.

| Form | What happens |
|---|---|
| `/log-grievance the status line ate my prompt` | Appends the entry at once and prints `logged the-status-line-ate-my-prompt`. |
| `/log-grievance` | Opens a small pane with the context line and an input. Enter logs it and closes the pane. Esc closes it. |

Each entry has `id`, `description`, `logged`, `sourceSession`, `resolvedIn` and `resolvedNoted`. `sourceSession` is pre-filled with the repo, the branch and the last failed tool call's first line, so the record says where it bit. An open entry with the same description is not duplicated; you are told its id instead. Marking an entry resolved stays with the skills.

### 2.1. The file it replaces

Before 1.0.0 the plugin kept the same entries in `~/.claude/library/state/cc-pain-points.json`. At every session start, and again before each grievance is logged, the mod checks that old file. When the grievances file is missing, the old file's text is written to it unchanged (every entry and every field as it was). When both exist, each old entry the grievances file lacks is appended after the entries already there, which keep their place and fields. An entry is matched on its `id` and description together, since both plugins make an id from the first 48 characters; an old entry whose id another grievance already uses arrives under the next free suffix (`-2`, `-3`), as `/log-grievance` would have named it. Either way a toast says how many came over. That second case is for a session still running the old plugin: anything it logs to the old file arrives at the next start. An entry is carried once only, so one you delete from the grievances file stays deleted. The record of what was carried starts with this version and lives in the plugin's store, which an update or a reinstall leaves in place. So the first start after an upgrade from 1.0.0 has no record, and matches on `id` alone: an id both files hold is the 1.0.0 copy, its description edited or not. Every other old entry is appended, one you had deleted since included. An old entry with no `id` comes back as a twin if any field of it was changed. Bringing back a deleted entry once is a cheaper mistake than stranding a logged one. No key in an entry ever carried the old word, so nothing inside is rewritten.

The old file is left where it is (a mod can write files but not delete them); delete it once no session still runs goblin-util, as the toast says. Pointing `grievances_file` somewhere new starts that file without the entries already carried, and anything logged to the old file since still arrives there. An old file that will not parse is left alone and named in a toast at session start. While there is no grievances file, `/log-grievance` refuses until it is fixed, so its entries are never stranded behind a new file; once it parses, the next session or grievance carries it over. A grievances file that will not parse is never overwritten: fix it, or, while `grievances_file` still names the path first carried into, delete it and the old file is carried over afresh, losing whatever was logged since the first carry-over.

---

## 3. `/muster-underlings`

Every underling (session) on this machine writes a heartbeat row to the plugin's shared store: repo, branch, whether a turn is running, the last tool it called and when. `/muster-underlings` opens a pane listing them, this session first.

| Key | Does |
|---|---|
| `1` to `9` | Picks an underling. A picked underling that is not this one gets an input under the list. |
| Enter in the input | Sends the line to that underling as a message, the same delivery as the SendMessage tool. The toast says whether it landed. |
| Esc | Closes the pane. |

An underling that has not written for a minute reads `quiet`. Opening the muster never writes: a row past the stale limit is dropped by the next heartbeat any running underling writes, within `heartbeat_seconds` (15 by default). An underling that ends cleanly removes its own row.

---

## 4. The skills

Each is invoked as `/goblin-seneschal:<name>`, or picked up by Claude when the moment fits.

| Skill | Does |
|---|---|
| `overhear-grievance` | Logs a grievance silently the moment Claude Code bites, and marks one resolved when `proclaim-releases` asks |
| `proclaim-releases` | Summarises Claude Code's changelog for a range, filtered by your own setup and matched against your open grievances |
| `proclaim-changes` | Says what you can now see or do after a unit of work lands |
| `inspect-chambers` | Maps every chamber (worktree) in the repo and says which are safe to touch; needs `jq` |
| `audit-prose` | Checks every layer of a prose-gating suite is wired and reports the trend in Claude's own output; needs the suite (section 6's options) |
| `consult-dossiers` | Reads the dossier and persona profile stores; needs the stores and PyYAML |

`audit-prose` and `consult-dossiers` audit and read things the plugin does not ship: the prose suite, the commit-msg hook, the output style and the two profile stores. On a machine without them, each says what is missing and stops.

---

## 5. The commands you have, the workflow and what not to do

| Command | Where | Does |
|---|---|---|
| `/log-grievance <text>` | any underling, any time, even mid-turn | logs the grievance at once, with the repo, branch and last failed tool call attached |
| `/log-grievance` | any underling | opens the small pane: type, Enter logs, Esc closes |
| `/muster-underlings` | any underling | opens the pane of every live underling on this machine; `1` to `9` picks one, Enter in the input messages it, Esc closes |

The workflow is short. Something in Claude Code itself bites: `/log-grievance <what happened>` the moment it does, before the detail fades; `proclaim-releases` reads the grievances against each release's changelog and tells you when one is fixed. You want to know what another session on this machine is doing, or to tell it something: `/muster-underlings`, pick the row, type the line. Neither command starts a turn, so both work while Claude is busy.

Do not:

- **Do not log a bug in your project with `/log-grievance`.** It is for Claude Code, the tool, only; a project bug goes on the project's tracker or roadbook, and an entry about one is noise the release check cannot match.
- **Do not use `/muster-underlings` to get another underling to do what yours was refused.** A message arrives as a peer message and is read as a teammate's, and a peer cannot grant a permission; the receiving session is told to refuse and surface it. Route the blocked thing to yourself.
- **Do not treat a `quiet` underling as gone.** It has not written for a minute; it is dropped only after `stale_minutes` by the next heartbeat another underling writes. Opening the muster writes nothing.
- **Do not mark an entry resolved from here.** `/log-grievance` only adds; resolving stays with `overhear-grievance` and `proclaim-releases`, which know what fixed it.
- **Do not duplicate an open entry.** The same description is refused with the existing id; add to that one through the skill instead.

---

## 6. Options

Set in `/config` or under `pluginConfigs` in `settings.json`. Every path takes a leading `~/` for your home.

| Option | Default | What it does |
|---|---|---|
| `enabled` | true | The one switch for the mod. Off, the heartbeat stops, the old file is not carried over and `/log-grievance` and `/muster-underlings` are not registered. |
| `heartbeat_seconds` | 15 | How often this underling writes its row. |
| `stale_minutes` | 10 | An underling silent for this long is forgotten. |
| `grievances_file` | `~/.claude/library/state/grievances.json` | Where grievances are kept, for the mod and both grievance skills. Only an absolute path or one under `~/` is taken; anything else would land in every project a session opens, so it is named in a toast and the default is used. |
| `prose_scripts_dir` | `~/.claude/library/scripts` | The prose suite `audit-prose` checks: `slop-scan.py`, `gen-skills-index.py` and the prose tests. |
| `commit_msg_hook` | `~/.claude/hooks/commit-msg` | The commit-msg hook `audit-prose` checks. |
| `commit_msg_log` | `~/.claude/library/state/commit-msg-log.jsonl` | The hook's log, for the rejection rate. |
| `output_style` | `~/.claude/output-styles/british-dev-goblin.md` | The output style `audit-prose` scans and expects `settings.json` to name. |
| `prose_metrics_store` | `~/.claude/library/state/prose-metrics.json` | Where `audit-prose` records the daily output metrics. |
| `dossier_dir` | `~/.claude/library/profiles/dossier` | The dossier store `consult-dossiers` reads. |
| `personas_dir` | `~/.claude/library/profiles/personas` | The persona store `consult-dossiers` reads. |

---

## 7. Files

| File | Holds |
|---|---|
| `hooks/register.tsx` | Both commands, the heartbeat, the two panes and the carry-over of the old file |
| `hooks/seneschal.test.tsx` | Tests for the helpers, the carry-over, both forms of `/log-grievance`, the underlings pane and the heartbeat |
| `types/index.d.ts` | The `$.state` contract: the picked underling, the last failed tool, the branch |
| `skills/*/SKILL.md` | The six skills |
| `scripts/` | The scripts the skills run: `worktree-state.sh` and `stack-status.py` for `inspect-chambers`, `prose-health.py` and `prose-metrics.py` for `audit-prose`, `profiles.py` and `_profiles_core.py` for `consult-dossiers`. Copies of goblin-mode's `library/scripts`, with every audited or read location taken from a flag |

Check it with `claude plugin validate marketplace/goblin-seneschal --strict` and `claude plugin test marketplace/goblin-seneschal`.
