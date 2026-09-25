---
name: "Next Task: Group"
description: "Show every currently unblocked roadmap task as one table per milestone or topic, with similar tasks adjacent"
when_to_use: "When you want the whole actionable frontier laid out to choose from: next-task-suggest picks one; this shows them all."
model: haiku
effort: low
metadata:
  glyph: ᚺ
  family: next-task
disable-model-invocation: false # read-only display that writes nothing; invocable so a redundant Skill call after the slash command reloads cleanly instead of erroring
allowed-tools: ["Bash(python3:*)"]
arguments: ["pivot"]
argument-hint: "[milestone|topic] (grouping pivot, default milestone)"
---

# Next: Task Group

Display the roadmap's complete ready-set (every unclaimed task whose effective status is `todo`), grouped for choosing between, not choosing for you. Read-only: this skill writes nothing and picks nothing.

## Step 0: Parse the pivot

The pivot argument as typed: `$pivot` (blank when none was given).

- blank or `milestone` → one table per milestone
- `topic` → one table per topic, with the milestone as a column
- anything else → name the two valid pivots, then default to milestone

A **topic** is the category prefix embedded in the task ID: the letters between the milestone number and the sequence (`2TI.3` → `TI`).

## Step 1: Locate the roadmap

Run `python3 "$HOME"/.claude/library/scripts/roadmap.py detect`. Exit **3** = old simple format: tell the user to run `roadmap-migrate` first and stop. Exit **2** = could not locate/parse; ask for the path. Proceed only on exit 0.

## Step 2: Get the data

Run both:

```bash
python3 "$HOME"/.claude/library/scripts/roadmap.py ready --json
python3 "$HOME"/.claude/library/scripts/roadmap.py stats
```

The `candidates` array is the complete ready-set: every entry is unblocked by definition; never re-derive or second-guess status here. Each candidate carries `id`, `description`, `milestone`, `milestoneName`, `milestoneDonePct`, `transitiveUnblocks`, `isMilestoneSink`, `assignee` and `notes`.

The `groups` object fixes the membership of every table: `groups.milestone` maps each milestone ID to its candidate IDs, `groups.topic` does the same per topic. Take table membership from it; never work out the groups or their sizes yourself.

If `candidates` is empty: say so, and use the `stats` breakdown to name the cheapest unblock: which blocker or gate, if cleared, frees the most tasks.

## Step 3: Order the rows

The `ready` command sorts by leverage. Discard that order: here `transitiveUnblocks` is a column, never the sort key. Inside each table, tasks about the same idea sit next to each other.

1. Give every candidate a **theme**: a label of one to three words for the feature or concept it works on (`search`, `login`, `CSV export`), judged from its description and notes. Two tasks touching the same feature share one label, whatever their topic prefix: `Show login errors inline on the form` (a `UI` task) and `Rate-limit failed login attempts` (an `AU` task) are both `login`.
2. Check the grain. Too coarse: the label repeats a topic or milestone name (`UI`, `Authentication`), which the ID and heading already say. Too fine: every row has its own label. Most themes should hold two to five tasks; a theme of one is fine when nothing else touches that idea.
3. Rows sharing a theme are contiguous. Place related themes next to each other (`search index` beside `search UI`, both away from `billing`).
4. Ties inside a theme: milestone number, then task ID in natural order (`2TI.3` before `2TI.10`).

The theme is a reading aid for this display only. It is never written to the roadmap.

Work out every candidate's group, theme and position silently. The reply holds the header line, the tables and the footer, nothing else: no plan, no theme list, no draft, no correction, no second copy of a table.

## Step 4: Render

Open with one header line: phase name, ready count against the total from `stats`.

Then one table per group. Order the groups by milestone number (milestone pivot) or alphabetically by topic (topic pivot).

**Milestone pivot** (default):

```markdown
## M2: {milestoneName} ({milestoneDonePct}% done)

| Theme | ID | Task | Unblocks | Dev | Notes |
|---|---|---|---|---|---|
| {theme} | {id} | {full description} | {transitiveUnblocks} | {assignee} | {notes} |
```

**Topic pivot:**

```markdown
## {topic}

| Theme | ID | Task | Milestone | Unblocks | Dev | Notes |
|---|---|---|---|---|---|---|
| {theme} | {id} | {full description} | {milestone} ({milestoneDonePct}%) | {transitiveUnblocks} | {assignee} | {notes} |
```

Cell rules:

- **Theme**: printed on every row, including repeats, so a row still reads on its own.
- **Task**: the full description, always. Never shorten it to tidy the table; escape any `|` in the text as `\|`.
- **Unblocks**: the number, and `0` still prints; a task that frees nothing is worth knowing about. Append ` · closes {milestone}` when `isMilestoneSink` is true, in both pivots.
- **Dev** and **Notes**: empty cell when the field is empty. Drop either column from a table where it is empty on every row.

**Every candidate gets exactly one row.** A large ready-set produces long tables; that is the point of this skill. Never sample, summarise or close a table with "and N more". Each table holds exactly the IDs `groups` lists for it. That list fixes membership only: row order comes from Step 3, so rows sharing a theme stay contiguous even when their IDs are far apart in the list. Before moving to the next table, check the one you just wrote against that list ID by ID; add any row you missed.

No commentary between tables. After the last table, end with one line giving each table's row count beside the size of its `groups` list:

```text
Shown {total rows in all tables} of {length of candidates} ready tasks ({group} {rows in its table}/{size of its groups list} · … one entry per table)
```

The groups named there are this run's tables: milestone IDs in the milestone pivot, topics in the topic pivot.

When `ready --json`'s `claimed` list is not empty, add one last line naming each claimed task, so nobody picks one twice: `Claimed: {id} ({assignee}, since {started}) · …` (drop the assignee when it is empty; add its `status` when that isn't `todo`).

Any pair that differs means a dropped or duplicated row: fix that table before finishing.

<raw-arguments value="$ARGUMENTS" />
