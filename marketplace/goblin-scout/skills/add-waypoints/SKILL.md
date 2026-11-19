---
name: "Add Waypoints"
description: "Add a well-formed waypoint (a task), or a reviewed batch of them, to a rich-format roadbook: ID assignment, dependency wiring in both directions, graph integrity"
when_to_use: "Whenever the user wants to add a task, feature or work item to the roadbook, even phrased as 'add this to the roadmap', 'put this in the plan' or 'track this as a task'. For a batch of half-formed ideas, run goblin-scout:plan-expedition first and feed its approved expedition here as one batch."
model: opus
effort: medium
metadata:
  glyph: ᛟ
  family: scout
disable-model-invocation: false # invocable by Claude so "add this to the roadbook" loads this skill instead of hand-editing the JSON; Step 7's approval gate still applies
allowed-tools: ["Read", "Glob", "Grep", "Edit", "Bash(python3:*)"]
arguments: ["mode", "description"]
argument-hint: "[t|c|m] [description]"
---

# Roadbook Waypoint Adder

Adds a well-formed waypoint to an existing rich-format roadbook. The job is placing the waypoint correctly in the dependency graph, wiring its relationships in **both** artefacts (`.claude/roadbook.json` and the PHASE file it names) and leaving the roadbook coherent; appending a line is the least of it.

Shared conventions: `${CLAUDE_PLUGIN_ROOT}/references/roadbook-conventions.md`. The CLI is `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py`.

## Batch mode

When the input is a multi-waypoint proposal (typically `goblin-scout:plan-expedition`'s approved expedition), run Steps 1–6 for the batch as a whole rather than once per waypoint: assign every ID up front, wire all edges including those between the new waypoints themselves, and run the Step 5 integrity checks across the combined graph. Steps 7–9 stay singular: one consolidated proposal, one approval, one write pass, one validate. Never loop the full skill per waypoint; fifteen approval gates for one already-reviewed expedition is ceremony with no safety in it.

---

## Step 0: Resolve the mode

`$mode` is `t`, `c` or `m` (aliases below), first token of `$ARGUMENTS`, case-insensitive. Remainder is `$description`.

| Token | Aliases                            | Meaning |
|-------|------------------------------------|---------|
| `t`   | `task`, `tasks`                    | One or more waypoints, independence unknown: treat as unrelated unless `$description` says otherwise |
| `c`   | `chain`, `sequence`, `set`         | At least two waypoints with a natural dependency order the user asserts: wire the chain in the order given |
| `m`   | `mile`, `ms`, `miles`, `milestone` | Create at least one new milestone; `$description` may also carry a seed waypoint |

Resolution depends on how this skill was reached:

- **Explicit `/goblin-scout:add-waypoints` invocation with no arguments or with a first token matching none of the aliases**: hard stop. Print `Usage: /goblin-scout:add-waypoints t|c|m "<description>"` and run nothing. Never guess a mode for an explicit invocation with no recognisable token: "improve the CSS" alone is exactly this case.
- **Model-invoked from natural language** ("add this to the roadbook", with no mode token because there's no slash command to carry one): infer the mode from the request shape and say the inference aloud before proceeding: one item → `t`; "X then Y" / "after" / explicit sequential phrasing → `c`; "new milestone" / "new phase of work" → `m`. This is the only path where mode is inferred rather than typed.
- **`m` with a milestone description but no seed waypoint**: not a stop; ask for the seed waypoint via AskUserQuestion, then continue.

`t` and `c` both proceed into Steps 1–9 below, unchanged in step numbering; `c` additionally parses `$description` for its asserted order (the word "then", commas, "after") and wires each waypoint's `dependsOn` to the one before it in that order, then runs the rest identically to `t`. `m` proceeds into "Milestone mode (`m`)" below before continuing into Step 3.

---

## Step 1: Locate the roadbook and check the format

Run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py detect`. Exit **3** = old simple format: **stop and tell the user to run `goblin-scout:rebind-roadbook` first**. Exit **2** = could not locate/parse: ask the user for the path. Only proceed on exit 0.

Read the full `roadbook.json` and the active phase's PHASE file before adding: you need the existing waypoint graph, milestone IDs, gates and categories.

---

## Step 2: Understand what to add

Extract: **description**; **milestone** (which milestone; ask if unclear); **tier** (read from the milestone name's trailing `(Secondary)`/`(Tertiary)` suffix, Core when there is none; see the conventions reference, Tiers. A follow-up to a waypoint in one tier often belongs in a later tier, and that is where the tier gate in Step 4 applies); **category** (2–3 letter prefix, reuse an existing one in that milestone where it fits); **dependencies** (what must be done first; what it unblocks); **scout** (the `assignee`: ask the user directly; never infer it from the description, the git author, the category owner or who is running this skill; leave it unset if the user doesn't say). Ask before proceeding if any is ambiguous: a badly placed waypoint is worse than a delayed one.

**In milestone mode (`m`), do this instead of picking an existing milestone**: see "Milestone mode" below, then continue into Step 3 for the seed waypoint(s).

---

## Milestone mode (`m`)

No existing skill appends a milestone to a *live* phase (`goblin-scout:start-roadbook` builds a whole phase from scratch, including its milestones, in one pass; `goblin-scout:rebind-roadbook` converts an old-format file wholesale). This is that missing procedure. Run it in place of the ordinary "pick an existing milestone" half of Step 2, then continue into Step 3 onward for the seed waypoint(s) that populate the new milestone.

1. **Assign the milestone ID**: `M{max existing milestone number + 1}`. Never reuse a milestone ID, mirroring the waypoint-ID rule below. This numbering rule and the milestone field-order rule both live in `${CLAUDE_PLUGIN_ROOT}/references/roadbook-conventions.md`; read it there rather than re-deriving it.
2. **Milestone object shape**: exactly `{id, name, goal, tasks: []}`; no other fields. Ask the user for `goal` (one sentence) if they haven't given one.
3. **Milestone-to-milestone gating**: milestones have no `dependsOn` field of their own; a "this milestone can't start until X finishes" gate is expressed on the seed waypoint(s) inside it instead. If the user says the new milestone is gated on other milestones, give the seed waypoint `dependsOn: ["M{a}", "M{b}", ...]`; it resolves once every non-`softMilestone` member of each is `done` or `out_of_scope`.
4. **Flag mid-sequence insertion rather than deciding it silently.** `M{N}` numbering is loosely coupled to waypoint-ID category prefixes elsewhere in a roadbook (a category can span several milestones), and nothing documents what happens if a milestone is ever inserted between existing ones rather than appended at the end. Appending (this procedure) is unambiguous; if the user ever wants to insert mid-sequence, say plainly that this is an open question rather than picking a convention on the spot.
5. **Childless-milestone check**, parallel to Step 5's childless-waypoint check below: a milestone with only one seed waypoint is fine on its own. Flag it only if that waypoint's own nature obviously implies more should follow soon.
6. Proceed into Step 3 for the seed waypoint(s), exactly as for any other new waypoint, with the milestone now resolved to the ID just assigned.

---

## Step 3: Assign a waypoint ID

`{MilestoneNum}{Category}.{Seq}`: find the highest sequence in that category and use `next = highest + 1`. Sub-waypoints: alpha suffix (`2TI.15a`). **Never reuse an ID**, even a removed one.

---

## Step 4: Identify dependencies

**Incoming** (`dependsOn`): waypoints this new waypoint requires. An entry may be a **waypoint ID**, a **milestone ID** (`M1`: resolves done only when all its waypoints are done) or an **external gate ID** (from `externalGates`). If a gate is an incoming dependency, the gate's `blocks[]` must gain this waypoint ID (parity).

**Tier gate** (when the target milestone is in tier 1 or above): a tier reaches a lower tier by milestone, never by waypoint (conventions reference, Tiers). Before wiring anything from a lower tier, read what the milestone's existing waypoints carry as lower-tier entries (`["M7", "M8", "M9", "M10", "M11"]`, or `["M1", "M6"]`; with no siblings yet, the gate the tier's other milestones carry): that list is the gate, and the new waypoint copies it. Then, for every lower-tier **waypoint** the user named as a prerequisite: if the gate already covers it (its milestone is in the list, or a listed entry reaches it), it does not go in `dependsOn`; record it in `notes` as `Extends {ID}` instead, and say which sibling the gate was copied from. When the gate does not cover it, the waypoint edge is still wrong; the prerequisite's **milestone** is what joins the gate. By default the waypoint keeps its tier: add that milestone to the copied list (`["M7", "M8", "M9"]` where the siblings carry `["M7", "M8"]`), note `Extends {ID}` as usual and flag in Step 7 that this waypoint's gate now differs from its siblings'. The one exception is a waypoint the user confirms is meant to escape its tier (wanted soon, so it waits on no lower-tier milestone): then the waypoint edge stays, it carries no gate at all and `notes` says so. One prerequisite neither branch covers by itself: a `softMilestone` member of a lower-tier milestone. A soft member never gates its milestone (conventions reference, Soft milestone members), so membership alone does not let `M10` reach a soft `10SE.7`, whether M10 is already in the list or added to it. While nothing the gate requires waits on it, the waypoint edge is the only thing that does, so it stays in `dependsOn` alongside the copied gate, and `validate` accepts that shape. When a hard member of M10, or anything else the gate requires, depends on `10SE.7`, directly or through other waypoints, the gate cannot resolve before it, so it is covered: record `Extends 10SE.7` and leave the edge out. Check the copied gate first: when an entry already in it reaches 10SE.7, such as a hard member of M7 that depends on it, the gate stays as copied. Add M10 only when the sole path to 10SE.7 runs through a hard member of M10 and the copied list lacks M10 (flag the differing gate in Step 7), which is the uncovered-prerequisite rule above applied as usual. `validate` (Step 9) refuses a covered lower-tier waypoint edge, so make the choice here; Step 9 only reports it.

**Outgoing**: existing waypoints that this new waypoint should now block; add the new ID to their `dependsOn` (and mirror any gate parity). Completing this waypoint may change those waypoints' computed status (the recompute handles that). If one of them is on a trail (it has a `started` date), say so before adding the edge: the new dependency blocks work a scout has already started.

**Soft (`softDependsOn`):** an optional, best-effort link worth drawing but not worth blocking on; ask if the relationship is a real dependency or a soft one before defaulting to `dependsOn`. Renders dotted, imposes no status, no cycle constraint (see conventions reference for direction).

---

## Step 5: Graph integrity checks (before writing)

**Orphan check.** A waypoint with no dependency edges in or out is orphaned. Warn (`"This waypoint has no connections to the existing graph. Intentional?"`), suggest the most plausible connection and proceed on the user's call. Some waypoints genuinely stand alone.

**Childless check.** If nothing depends on the new waypoint but its nature clearly unlocks future work, create a placeholder child in the appropriate milestone: `- [ ] **{NewID}**: {unlocked capability} _(blocked: depends on {NewWaypointID})_`, `status: "blocked"`, with the dependency edge. Skip placeholders for obviously terminal waypoints (deploy, final release notes). Tell the user what placeholder was created and why. In milestone mode (`m`), also run the childless-*milestone* check from that section above.

---

## Step 6: Compute the new waypoint's status (mechanical)

The mechanical status rule applies (see conventions reference): empty `dependsOn` → `todo`; any non-`done` dependency → at least `blocked`, escalating under `deferred > paused > blocked > todo`; this covers both a dependency on a gate that `imposes: paused`/`deferred` and a dependency on a waypoint that is itself already `paused`/`deferred`. `softDependsOn` never feeds this rule. After wiring, confirm the new waypoint's status and any downstream changes with `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py recompute --check` (preview, no write).

---

## Step 7: Prepare the proposal (do not edit yet)

In milestone mode (`m`), lead with the milestone block, then the seed waypoint block below it:

```text
New milestone: {ID}, {Name}
Goal: {goal}
Gated on: {milestone IDs, or "nothing"}
```

Waypoint block (always; the only block in `t`/`c` modes):

```text
New waypoint: {ID}, {description}
Milestone: {N} ({Milestone Name})   Status: {todo|blocked|paused|deferred}
Scout: {name, or "unassigned"}
Dependencies (in): {IDs / milestone / gate, or "none"}
Tier gate: {lower-tier milestone IDs copied, and the sibling they came from, e.g. "M7, M8, M9, M10, M11 (from 13SE.1)"; "M7, M8 (from 13SE.1) + M9 for 9AB.2: differs from siblings" when a prerequisite's milestone was added; "n/a: core tier"; or "none: escapes the tier"}
Lower-tier work noted, not wired: {IDs moved into notes as "Extends {ID}", or "none"}
Dependencies (out): {waypoint IDs this gets added to, or "none"}
Placeholder child: {ID and description, or "none"}

Graph changes:
  + roadbook.json: new milestone object (m mode only); new waypoint object; edits to {existing waypoints' dependsOn}; gate blocks[] updates
  + diagram: regenerated from the JSON (node {ID}; edges {list})
```

Then ask: *"Does this look right? I'll write to the roadbook on your say-so."*

---

## Step 8: Write to both artefacts (once approved)

0. **`m` mode only, before anything else**: insert the new milestone object (`{id, name, goal, tasks: []}`) into the phase's `milestones[]` array, after the last existing milestone.
1. **`roadbook.json`**: insert the waypoint object in its milestone's `tasks[]` (field order per the conventions reference; tabs; British spelling). Include `assignee`/`softDependsOn`/`softMilestone` only when the user gave one; omit them entirely otherwise, exactly like `notes`. Update any existing waypoints' `dependsOn`. Update any gate's `blocks[]` for parity. Add the placeholder waypoint if any.
2. **PHASE file**: add the waypoint line under its milestone with the status annotation (`_(blocked: depends on {IDs})_` etc.); update any existing waypoint lines whose dependency clause changed; add the placeholder line. **`m` mode only**: first emit a full new milestone section (`## Milestone {N}: {Name}`, blank line, `**Goal:** {goal}`, blank line) before the waypoint line, matching `goblin-scout:start-roadbook` Step 7's shape. This is new work into an existing milestone; the section doesn't exist yet the way it does for a milestone `goblin-scout:start-roadbook` built from scratch.
3. **Mermaid diagram**: replace the entire fenced `mermaid` block with the output of `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py graph --mermaid --direction LR`. Never hand-edit edges, sinks or class lines; the generator recomputes milestone sinks (including any former sink displaced by the new waypoint) and the canonical colours.
4. **The overview** (`ROADBOOK_OVERVIEW.md`, or `ROADMAP_OVERVIEW.md` in a project that predates 3.0.0): the waypoint total (and, in `m` mode, the milestone total) changed, so update the header `**N waypoints across M milestones.**` (`**N tasks across M milestones.**` in an overview written before 3.0.0; keep whichever word it already uses); pull *both* numbers from `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py stats --json` (`total` and `milestonesTotal`), never just the waypoint count.

---

## Step 9: Validate and confirm

Run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py validate`; it must report clean (parity, acyclicity, status recompute, no lower-tier waypoint edge the waypoint already requires by milestone). A cross-tier discrepancy here means Step 4's tier gate was skipped: drop the edge and move the ID into `notes`, never the reverse. If the phase's chart exists (its `artefact` path, else `docs/artefacts/chart-*.html`), refresh it with `roadbook.py render`. Then report: waypoint added (and milestone, in `m` mode); status; edges added; existing waypoints modified; placeholder created; any orphan warning. If the new waypoint's computed status is `blocked` on a dependency that looks like it should already be `done` in reality, say so explicitly rather than reporting `blocked` as if the wiring itself is uncertain; the roadbook can lag real-world completion.

---

## Conventions

- Waypoint line: `- [ ] **{ID}**: {description}` + annotation. Completed: `- [x] **{ID}**: {description}`.
- Milestone section: `## Milestone {N}: {Name}` + `**Goal:** {goal}`, matching `goblin-scout:start-roadbook` Step 7.
- roadbook.json is the source of truth; the PHASE file and overview are projections.
- Everything else (statuses, colours, graph/edge rules, formatting, milestone-ID assignment and milestone field order): `${CLAUDE_PLUGIN_ROOT}/references/roadbook-conventions.md`.

> **Mirrored phases:** when the active phase has a `source`, every waypoint you add is the user's own: give it `"local": true` and an id that is not a Jira key (`L1`, `L2`…). Never add, edit or remove a mirrored waypoint; those change in Jira and arrive with `roadbook.py pull`. Details: Mirrored phases in the conventions reference.

<raw-arguments value="$ARGUMENTS" />
