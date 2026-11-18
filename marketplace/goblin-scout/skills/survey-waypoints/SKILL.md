---
name: "Survey Waypoints"
description: "Show every currently unblocked roadbook waypoint (a task) as one table per milestone, topic or scout, with similar waypoints adjacent"
when_to_use: "When you want the whole actionable frontier laid out to choose from: goblin-scout:suggest-waypoint picks one; this shows them all."
model: sonnet
effort: low
metadata:
  glyph: ᛊ
  family: next-task
disable-model-invocation: false # read-only display that writes nothing; invocable so a redundant Skill call after the slash command reloads cleanly instead of erroring
allowed-tools: ["Bash(python3:*)"]
arguments: ["pivot"]
argument-hint: "[milestone|topic|scout] (grouping pivot, default milestone)"
---

# Survey: Ready Waypoints

Display the roadbook's complete ready-set (every waypoint with no trail on it whose effective status is `todo`), grouped for the user to choose between. Read-only: this skill writes nothing and picks nothing.

## Step 0: Parse the pivot

The pivot argument as typed: `$pivot` (blank when none was given).

- blank or `milestone` → one table per milestone
- `topic` → one table per topic, with the milestone as a column
- `scout` (or `dev`) → one table per assignee, `Unassigned` last, with the milestone as a column
- anything else → name the three valid pivots, then default to milestone

A **topic** is the category prefix embedded in the waypoint ID: the letters between the milestone number and the sequence (`2TI.3` → `TI`).

## Step 1: Locate the roadbook

Run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py detect`. Exit **3** = old simple format: tell the user to run `goblin-scout:rebind-roadbook` first and stop. Exit **2** = could not locate/parse; ask for the path. Proceed only on exit 0.

## Step 2: Get the data

Run both:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py ready --json
python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py stats
```

The `candidates` array is the complete ready-set: every entry is unblocked by definition; never re-derive or second-guess status here. Each candidate carries `id`, `description`, `milestone`, `milestoneName`, `milestoneDonePct`, `transitiveUnblocks`, `isMilestoneSink`, `assignee` and `notes`.

The `groups` object fixes the membership of every table: `groups.milestone` maps each milestone ID to its candidate IDs, `groups.topic` does the same per topic, `groups.dev` does the same per assignee (`unassigned` for the empty string). Take table membership from it; never work out the groups or their sizes yourself.

If `candidates` is empty: say so, and use the `stats` breakdown to name the cheapest unblock: which blocker or gate, if cleared, frees the most waypoints.

## Step 3: Order the rows

The `ready` command sorts by leverage. Discard that order: here `transitiveUnblocks` is a column, never the sort key. Inside each table, waypoints about the same idea sit next to each other.

1. Give every candidate a **theme**: a label of one to three words for the feature or concept it works on (`search`, `login`, `CSV export`), judged from its description and notes. Two waypoints touching the same feature share one label, whatever their topic prefix: `Show login errors inline on the form` (a `UI` waypoint) and `Rate-limit failed login attempts` (an `AU` waypoint) are both `login`.
2. Check the grain. Too coarse: the label repeats a topic or milestone name (`UI`, `Authentication`), which the ID and heading already say. Too fine: every row has its own label. Most themes should hold two to five waypoints; a theme of one is fine when nothing else touches that idea.
3. Rows sharing a theme are contiguous. Place related themes next to each other (`search index` beside `search UI`, both away from `billing`).
4. Ties inside a theme: milestone number, then waypoint ID in natural order (`2TI.3` before `2TI.10`).

The theme is a reading aid for this display only. It is never written to the roadbook.

Work out every candidate's group, theme and position silently. The reply holds the header line, the tables and the footer, nothing else: no plan, no theme list, no draft, no correction, no second copy of a table.

## Step 4: Render

Open with one header line: phase name, ready count against the total from `stats`.

Then one table per group. Order the groups by milestone number (milestone pivot), alphabetically by topic (topic pivot), or as `groups.dev` lists them (scout pivot: case-insensitive alphabetical, `Unassigned` last).

**Milestone pivot** (default):

```markdown
## M2: {milestoneName} ({milestoneDonePct}% done)

| Theme | ID | Waypoint | Unblocks | Scout |
|---|---|---|---|---|
| {theme} | {id} | {full description} | {transitiveUnblocks} | {assignee} |
```

**Topic pivot:**

```markdown
## {topic}

| Theme | ID | Waypoint | Milestone | Unblocks | Scout |
|---|---|---|---|---|---|
| {theme} | {id} | {full description} | {milestone} ({milestoneDonePct}%) | {transitiveUnblocks} | {assignee} |
```

**Scout pivot:**

```markdown
## {assignee, or "Unassigned"}

| Theme | ID | Waypoint | Milestone | Unblocks |
|---|---|---|---|---|
| {theme} | {id} | {full description} | {milestone} ({milestoneDonePct}%) | {transitiveUnblocks} |
```

No Scout column here; the heading already names the scout.

Cell rules:

- **Theme**: printed on every row, including repeats, so a row still reads on its own.
- **Waypoint**: the full description, always. Never shorten it to tidy the table; escape any `|` in the text as `\|`.
- **Unblocks**: the number, and `0` still prints; a waypoint that frees nothing is worth knowing about. Append `· closes {milestone}` when `isMilestoneSink` is true, in every pivot.
- **Scout**: empty cell when the field is empty. Drop the column from a table where it is empty on every row (milestone and topic pivots only; the scout pivot never has this column).

**Notes never go in the table.** A long note beside a long Waypoint cell is what pushes the table past the terminal's box-table width and drops it into the stacked `Key: value` fallback, so it stays out of every pivot's columns. Directly under each table, one bullet per row that has a non-empty `notes`, in the same row order as the table above it; skip the whole block when no row in that table has notes:

```markdown
- {id}: {notes}
```

**Every candidate gets exactly one row.** A large ready-set produces long tables; that is the point of this skill. Never sample, summarise or close a table with "and N more". Each table holds exactly the IDs `groups` lists for it. That list fixes membership only: row order comes from Step 3, so rows sharing a theme stay contiguous even when their IDs are far apart in the list. Before moving to the next table, check the one you just wrote against that list ID by ID; add any row you missed.

No commentary between tables. After the last table, end with one line giving each table's row count beside the size of its `groups` list:

```text
Shown {total rows in all tables} of {length of candidates} ready waypoints ({group} {rows in its table}/{size of its groups list} · … one entry per table)
```

The groups named there are this run's tables: milestone IDs in the milestone pivot, topics in the topic pivot, scouts (as `groups.dev` names them) in the scout pivot. Any pair that differs means a dropped or duplicated row: fix that table before finishing.

When `ready --json`'s `claimed` list is not empty, follow that line with one more naming each waypoint on a trail, so nobody picks one twice: `On a trail: {id} ({assignee}, since {started}) · …` (drop the assignee when it is empty; add its `status` when that isn't `todo`).

The reply ends there. No recommendation, no highest-leverage pick, no "Next:" line: this skill lays the ready-set out to choose from, it never chooses.

<raw-arguments value="$ARGUMENTS" />
