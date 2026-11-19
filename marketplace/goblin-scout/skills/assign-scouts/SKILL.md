---
name: "Assign Scouts"
description: "Interview-led assignment of roadbook waypoints (tasks) to scouts (the people doing them): collect the team roster, walk the chosen waypoints in batches, write the approved assignee changes to roadbook.json"
when_to_use: "When roadbook waypoints need owners: a fresh roadbook with nobody assigned, a new scout joining, one scout's load to hand over or a rebalance before a sprint. For setting the assignee on a single waypoint as it is added, goblin-scout:add-waypoints already asks."
model: sonnet
effort: medium
metadata:
  glyph: ᛊ
  family: scout
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Edit", "Bash(python3:*)"]
arguments: ["horizon", "scope", "where", "roadbook"]
argument-hint: "[ready|open] [free|taken|all|<scout>] [<phase>|current[:project|focus|<tiers>|<milestones>]] (defaults: ready free current:project)"
---

# Roadbook Scout Assigner

Sets the `assignee` field on many waypoints in one sitting. The user decides every assignment; this skill supplies the structure: which waypoints are in play, what each scout already carries and a reply grammar short enough that 30 waypoints take a few lines of typing.

Shared conventions: `${CLAUDE_PLUGIN_ROOT}/references/roadbook-conventions.md`. The CLI is `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py`.

**Hard rule, inherited from the conventions:** an assignee is never inferred. Never propose, pre-fill or hint at a scout for a waypoint, whether from its description, category, milestone, git history or who owns the waypoints around it. Show facts; the user picks.

---

## Step 0: Parse the arguments

Every argument is optional, but they are positional: passing argument N requires arguments 1 to N-1. Defaults are `ready free current:project`.

| #   | Argument    | Value                   | Meaning |
|-----|-------------|-------------------------|---------|
| 1   | `$horizon`  | `ready` (default)       | only waypoints that are currently unblocked (effective status `todo`) and not on a trail |
| 1   | `$horizon`  | `open`                  | every unfinished waypoint: any status except `done` and `out_of_scope` |
| 2   | `$scope`    | `free` (default)        | only waypoints with no `assignee` |
| 2   | `$scope`    | `taken`                 | only waypoints with an `assignee` |
| 2   | `$scope`    | `all`                   | every waypoint inside the horizon, assigned or unassigned |
| 2   | `$scope`    | `<scout>`               | only waypoints assigned to that scout (case-insensitive match) |
| 3   | `$where`    | `<roadbook>[:<filter>]` | which phase, and which slice of it (below) |
| 4   | `$roadbook` | a path                  | the `roadbook.json` to use; recognised by ending in `.json` or containing a `/`, so it never collides with `$where` |

**`$where`** is `<roadbook>:<filter>`, split on the **last** `:`. When passed, `<roadbook>` is required and `<filter>` is optional.

| Part         | Value               | Meaning |
|--------------|---------------------|---------|
| `<roadbook>` | `current` (default) | the only active phase, or the one the user picks in Step 1 when several are active |
| `<roadbook>` | a phase name        | that phase, matched case-insensitively against the active phases |
| `<filter>`   | `project` (default) | the whole phase |
| `<filter>`   | `focus`             | waypoints in the tier now underway (the lowest tier with unfinished work) |
| `<filter>`   | `<tiers>`           | comma-separated tier words: `core`, `secondary`, `tertiary`, … (waypoints in milestones of those tiers) |
| `<filter>`   | `<milestones>`      | comma-separated milestone ids: `M2,M4` |

Tiers and milestones are mutually exclusive in one call. `M2,secondary` is a hard stop.

Matching is case-insensitive. A multi-word scout name or phase name arrives quoted (`"Mary Ann"`); take the quoted string whole. `free`, `taken` and `all` are reserved words in the scope slot, so a scout with one of those names needs the roadbook edited by hand.

Hard stop (print the usage line, run nothing, never guess) when: argument 1 is passed and is not `ready` or `open`; the phase name matches no active phase (list the active names); the filter mixes tiers and milestones; a tier word or milestone id is unknown for the phase, or `focus` has no tier underway (the CLI says which and exits 2; relay its message).

```text
Usage: /goblin-scout:assign-scouts [ready|open] [free|taken|all|<scout>] [<phase>|current[:project|focus|<tiers>|<milestones>]]
Defaults: ready free current:project
```

Before doing anything else, echo the resolved form so a defaulted argument is never a surprise: `→ ready free MVP:focus` (the phase name once Step 1 has resolved it).

**Output layout.** Every block this skill prints is a markdown heading plus plain text or a markdown table, never a `text` fence. The headings nest as follows; the step templates below show each block's content.

```md
# Roadbook: Assign Scouts      ← printed once, above the echo
## Preparation
### Roster
### Working Set
### Reply Grammar
## Batch 2 of 5 · M2: Search (40% Done) · 4 Waypoints   ← one per batch
## Proposal
## Result
```

Title Case on headings and column headers; the data (`todo`, `none`, waypoint descriptions) is printed as found.

---

## Step 1: Locate the roadbook and check the format

Run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py detect`, appending `$roadbook` (argument 4) as the PATH argument when one was given. Exit **3** = old simple format: stop and tell the user to run `goblin-scout:rebind-roadbook` first. Exit **2** = could not locate or parse: ask the user for the path. Proceed only on exit 0. Every later CLI call in this skill carries the same PATH.

**Phase selection.** Read `roadbook.json` and list the phases without `archived: true`. A named `<roadbook>` in `$where` selects that phase (hard stop if it matches none). `current`: one active phase, use it; several, ask with AskUserQuestion which to work on, listing the last active phase in the array first and marking it recommended (the array is appended to, so last is most recent). Pass the choice as `--phase "{name}"` on every later CLI call. Never pick silently between active phases.

---

## Step 2: Collect the roster

The interview opens here, before any waypoint is shown.

1. Gather the distinct `assignee` strings already present anywhere in the chosen phase, finished waypoints included. These are names the roadbook knows; they are context for the question and carry no weight as assignments.
2. Ask in plain text (names are free text, so AskUserQuestion's fixed options do not fit):

   ```text
   Who are the scouts on this team? Give me the names, comma-separated.
   Already in this roadbook: {existing names, or "nobody yet"}.
   ```

3. Build the roster from the answer. The user's spelling is canonical. Where a roster name matches an existing assignee case-insensitively but the spelling differs (`jaz` in the roadbook, `Jaz` in the answer), say so and offer to normalise every occurrence to the roster spelling as part of this run's write; `goblin-scout:suggest-waypoint` filters on the string, so two spellings split one scout's waypoints in two.
4. Give each roster member a short handle for the reply grammar: the shortest unique case-insensitive prefix of the name (`j` for Jaz and `m` for Max; `ja` and `jo` for Jaz and Jo). Print the roster with handles once, under `### Roster` (inside `## Preparation`), as one plain line: `Jason (jas), Jaz (jaz)`.
5. An existing assignee the user left off the roster stays on their waypoints untouched. Mention each such name once; the user may have left the team member out on purpose.

**Named-scout scope check.** When `$scope` is a scout's name and no waypoint in the phase carries it (case-insensitive), say `No waypoint in {phase} is assigned to {name}.`, list the assignees that do exist and stop.

---

## Step 3: Build the working set

Both horizons come from the CLI, so status, trails and tiers are never re-derived. Pass the `$where` filter through: `--milestones M2,M4` for a milestone list, `--tiers core,secondary` for a tier list, `--tiers focus` for `focus` and nothing for `project`.

- `$horizon` = `ready`: run `roadbook.py ready --json {filter flags}`. The `candidates` array is the complete unblocked set inside the filter with no trail on it, already ordered by leverage, each with `assignee` (empty string when unassigned). Waypoints on a trail sit apart in its `claimed` list: a scout is already working on them, so they are not up for assignment here.
- `$horizon` = `open`: run `roadbook.py open --json {filter flags}`. `candidates` holds every waypoint inside the filter that is not `done` or `out_of_scope`, each with `status`, `display` and `started`. A waypoint with a `started` date is on a trail: show it, but flag any proposal to move it to someone else, since that hands over live work. If `roadbook.py validate` reports status discrepancies, tell the user and suggest `goblin-scout:tend-roadbook` first; carry on if they say so, since assignment does not depend on status being fresh.

Filter by `$scope` (`free`: empty `assignee`; `taken`: non-empty; `all`: no filter; `<scout>`: case-insensitive match). An empty working set is a result: report it (`Every ready waypoint in M2 already has a scout.`) and stop.

Compute the **load table**, which the interview reprints as it changes: for each roster member, the count of unfinished waypoints they hold across the whole phase, split into in progress (on a trail), ready and not-yet-ready, plus one row for unassigned.

```md
### Working Set
{N} waypoints ({horizon}, {scope}) in {phase} · {filter}

| Load Now   | In Progress | Ready | Later | Total |
|------------|------------:|------:|------:|------:|
| Jaz (j)    |           1 |     2 |     4 |     7 |
| Max (m)    |           0 |     0 |     1 |     1 |
| Unassigned |           0 |     6 |    11 |    17 |
```

---

## Step 4: Assign in batches

Split the working set into batches by milestone, in milestone order. A milestone with more than 10 waypoints in the working set splits again by topic (the letters between the milestone number and the sequence in the waypoint ID: `2TI.3` → `TI`); a topic still over 10 splits into runs of 10. Keep the Step 3 ordering inside each batch.

Show one batch at a time, numbered from 1 within the batch:

```md
## Batch 2 of 5 · M2: Search ({milestoneDonePct}% Done) · 4 Waypoints

| # | ID    | Status  | Now  | Upstream Owners | Waypoint             |
|--:|-------|---------|------|-----------------|----------------------|
| 1 | 2SE.1 | todo    | none | none            | {full description}   |
| 2 | 2SE.2 | blocked | none | 2SE.1 (none)    | {full description}   |
| 3 | 2SE.4 | blocked | Max  | 2SE.2 (none)    | {full description}   |
| 4 | 2TI.3 | todo    | none | 1IN.2 (Jaz)     | {full description}   |

Assign: "<rows> <scout>" clauses split by ";". Example: 1-2 j; 4 m
```

A run with a single batch drops the `Batch 1 of 1 ·` prefix: `## M5: Filtering & Search (0% Done) · 1 Waypoint`.

- **Status** reads `in progress` for a waypoint on a trail (one with a `started` date) that is `todo` or `blocked`; a paused, deferred or finished status shows as itself.
- **Now** is the current assignee. **Upstream owners** lists the waypoint's direct `dependsOn` waypoints with their assignee in brackets; assignments made earlier in this run show up here, and milestone and gate dependencies are omitted. It is a fact about the graph and never a recommendation.
- Full descriptions always, never truncated; the table wraps them inside the Waypoint cell.
- Print the grammar reference below in full once, under `### Reply Grammar` in `## Preparation` (after the Working Set, before the first batch). Batches then carry only the one-line reminder shown above.

### Reply Grammar

| Reply                | Effect |
|----------------------|--------|
| `1-3 j`              | rows 1 to 3 go to the scout whose handle is `j` |
| `1,4 max`            | rows 1 and 4 to Max (full names and handles both work) |
| `all j` / `rest j`   | every row / every row not named in an earlier clause |
| `2 -`                | clear row 2's assignee |
| `1-2 j; 3 m; rest -` | several clauses, split by `;` or new lines |
| `skip`               | leave the whole batch as it is |
| `back`               | reopen the previous batch |
| `done`               | stop here and go to the proposal with what has been decided |
| `+ Priya`            | add a scout to the roster mid-run; handles are recomputed and reprinted |

Rows a reply does not mention stay unchanged. A row named in two clauses, a row number outside the batch or a handle matching no one (or more than one scout): change nothing, quote the offending clause and ask again for that batch only. Never resolve an ambiguous reply by guessing.

After each batch, confirm in one line what was recorded (`2SE.1, 2SE.2 → Jaz · 2TI.3 → Max · 2SE.4 stays with Max`) and reprint the load table with the pending changes applied. Nothing is written to disk during this step.

---

## Step 5: Prepare the proposal (do not edit yet)

```md
## Proposal
Assignee changes: {N} waypoints in {phase}

### New Assignments
| ID    | Change      | Waypoint      |
|-------|-------------|---------------|
| 2SE.1 | none → Jaz  | {description} |
| 2TI.3 | none → Max  | {description} |

### Reassignments
| ID    | Change      | Waypoint      |
|-------|-------------|---------------|
| 2SE.4 | Max → Jaz   | {description} |

### Cleared
| ID    | Change      | Waypoint      |
|-------|-------------|---------------|
| 3UI.2 | Jaz → none  | {description} |

Spelling normalised: "jaz" → "Jaz" on {n} waypoints

### Load
| Scout      | Before | After |
|------------|-------:|------:|
| Jaz (j)    |      7 |    10 |
| Max (m)    |      1 |     1 |
| Unassigned |     17 |    14 |

Still unassigned in this working set: {n}
```

Omit any section with no rows. Reassignments and clears take a scout's name off a waypoint, so they always get their own sections; never fold them into the new assignments.

Then ask with AskUserQuestion: **Apply** / **Revise a batch** / **Cancel**. Revise returns to Step 4 at the batch the user names and comes back here afterwards. Cancel writes nothing.

---

## Step 6: Write (once approved)

Edit `roadbook.json` only. Assignee has no projection in the PHASE file or the overview (`ROADBOOK_OVERVIEW.md`, or `ROADMAP_OVERVIEW.md` in a project that predates 3.0.0), so neither is touched.

- **Set or replace**: `"assignee": "{roster spelling}"`, placed by the conventions' waypoint field order (after `notes` when present, before `started` and `pr` when present).
- **Clear**: delete the `assignee` line entirely and fix the trailing comma on the line before it. Never write an empty string; the field is omit-when-empty.
- Tabs for indentation; leave every other field, including `status` and `started`, as found.
- One Edit per waypoint, anchored on the waypoint's `"id"` line so the match is unique. Never use `replace_all` for spelling normalisation: similar names can share a prefix, so each occurrence is edited on its own.

---

## Step 7: Validate and report

Run `roadbook.py validate`; it must report clean, and a discrepancy that was present before Step 6 is reported as pre-existing. If the phase's chart exists (its `artefact` path, else `docs/artefacts/chart-*.html`), refresh it with `roadbook.py render`, since its scout chips come from this field.

Print the report under `## Result`: the count of waypoints changed; the final load table (same columns as the Working Set table); how many waypoints in the working set are still unassigned; any roster member who ended with nothing. Close with the one next action that fits, for example `/goblin-scout:suggest-waypoint Jaz` to pull that scout's highest-leverage ready waypoint.

---

## Conventions

- `assignee` is free text with no roster stored in the roadbook. The roster from Step 2 lives only for this run; it is asked for every time.
- `roadbook.json` is the source of truth. Statuses, field order, formatting and everything else: `${CLAUDE_PLUGIN_ROOT}/references/roadbook-conventions.md`.

<raw-arguments value="$ARGUMENTS" />
