---
name: "Next: Task Group"
description: "Show every currently unblocked roadmap task, grouped by milestone or topic"
when_to_use: "When you want the whole actionable frontier laid out to choose from — next-task-suggest picks one; this shows them all."
model: haiku
effort: low
metadata:
  glyph: ᚺ
  family: next-task
  bundle: roadmap-system
disable-model-invocation: true
allowed-tools: ["Bash(python3:*)"]
arguments: ["pivot"]
argument-hint: "[milestone|topic] (grouping pivot, default milestone)"
---

# Next: Task Group

Display the roadmap's complete ready-set — every task whose effective status is `todo` — grouped for choosing between, not choosing for you. Read-only: this skill writes nothing and picks nothing.

## Step 0 — Parse the pivot

`$ARGUMENTS` is empty or `milestone` → group by milestone with topic sub-groups. `$ARGUMENTS` is `topic` → pivot: group by topic with the milestone on each task line. Anything else: say the two valid pivots and default to milestone.

A **topic** is the category prefix embedded in the task ID — the letters between the milestone number and the sequence (`2TI.3` → `TI`).

## Step 1 — Locate the roadmap

Run `python3 "$HOME"/.claude/library/scripts/roadmap.py detect`. Exit **3** = old simple format — tell the user to run `roadmap-migrate` first and stop. Exit **2** = could not locate/parse — ask for the path. Proceed only on exit 0.

## Step 2 — Get the data

Run both:

```bash
python3 "$HOME"/.claude/library/scripts/roadmap.py ready --json
python3 "$HOME"/.claude/library/scripts/roadmap.py stats
```

The `candidates` array is the complete ready-set — every entry is unblocked by definition; never re-derive or second-guess status here. Each candidate carries `id`, `description`, `milestone`, `milestoneName`, `milestoneDonePct`, `transitiveUnblocks`, `isMilestoneSink`, `assignee` and `notes`.

If `candidates` is empty: say so, and use the `stats` breakdown to name the cheapest unblock — which blocker or gate, if cleared, frees the most tasks.

## Step 3 — Render

Header: phase name, ready count against the total from `stats`.

**Milestone pivot** (default):

```markdown
## M2 — {milestoneName} ({milestoneDonePct}% done)

### {topic}

- **{id}** — {full description}
  ↳ unblocks {transitiveUnblocks} · completes milestone · {assignee} · {notes}
```

Omit the `### {topic}` line when a milestone's ready tasks all share one topic. On the annotation line, include only what applies: drop `completes milestone` unless `isMilestoneSink`, drop the assignee when empty, drop notes when empty. `unblocks 0` still prints — a task that frees nothing is worth knowing about.

**Topic pivot:**

```markdown
## {topic}

- **{id}** — {full description} _({milestone} · {milestoneDonePct}% done)_
  ↳ unblocks {transitiveUnblocks} · completes milestone · {assignee} · {notes}
```

Both pivots preserve the `ready` command's ordering within each group (it sorts by leverage: `transitiveUnblocks` desc, then `milestoneDonePct` desc). Order the groups themselves by milestone number (milestone pivot) or alphabetically (topic pivot).

Full descriptions always — never truncate them to tidy the layout.

<raw-arguments value="$ARGUMENTS" />
