---
name: "Plan Expedition"
description: "Interview the user to turn half-formed ideas into an expedition (a reviewed batch of new work) of roadbook-ready waypoints (tasks). Read-only; goblin-scout:add-waypoints writes the approved expedition."
when_to_use: "When the user wants to explore what to build next, brainstorm features, expand the roadbook (or 'the roadmap'), plan a new phase or says things like 'what should we add', 'help me think through features', 'let's plan the next milestone' or 'interview me about what to build'. Not for adding a single already-specified waypoint; that's goblin-scout:add-waypoints."
model: fable
effort: high
metadata:
  glyph: ᚠ
  family: scout
disable-model-invocation: false # explicit: read-only interview, so "help me think through features" phrasing can load it
allowed-tools: ["Read", "Glob", "Grep", "Bash(python3:*)"]
disallowed-tools: ["Edit", "Write", "NotebookEdit"] # read-only by contract; goblin-scout:add-waypoints writes the approved expedition
arguments: ["focus"]
argument-hint: "[milestone, theme or focus (optional)]"
---

# Roadbook Expedition Planner

A structured interview that turns half-formed ideas into an expedition: a coherent batch of roadbook-ready waypoints. The goal is to make the user think clearly about what they want to build, then produce a proposal they can review before anything touches the roadbook.

---

## Philosophy

Good features don't usually arrive fully formed. They start as vague intentions ("we need better search", "users keep asking for X") and need interrogation to become waypoints. This skill does that interrogation: it asks focused questions in small batches, listens for dependencies and scope and organises the output into something the roadbook can absorb cleanly.

The interview is a thinking tool as much as a discovery one. Sometimes the most valuable outcome is realising a "feature" is actually three separate concerns, or that what feels new is actually an extension of something already tracked.

---

## Step 1: Orient to the roadbook

This is a read-only skill: it writes nothing; it produces a proposal that `goblin-scout:add-waypoints` later writes.

Locate and read the rich-format roadbook: user-specified path → `.claude/roadbook.json` (the source of truth, an array of phase objects; the active phase is the non-`archived` entry; `.claude/roadmaps.json` in a project that predates 3.0.0) → a scan of `docs/roadbook/` (or `docs/roadmaps/`). Check the format with `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py detect`; exit **3** (old simple format): tell the user to run `goblin-scout:rebind-roadbook` first, since the proposal must speak the rich vocabulary; exit **2**: ask for the path.

From the active phase, extract:

- All milestones (names, goals) and their per-status waypoint counts (`python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py stats` gives these)
- The actionable frontier: `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py ready` lists the unblocked `todo` waypoints with leverage signals; what the project can start now shapes what is worth proposing next
- `blocked`/`paused`/`deferred` waypoints (potential unlock targets)
- The external gates (a proposed waypoint may depend on a gate) and existing category prefixes per milestone

Shared conventions (status vocabulary, graph rules): `${CLAUDE_PLUGIN_ROOT}/references/roadbook-conventions.md`; in progress is a trail on an existing waypoint, never a status; a new waypoint never starts on a trail. This context informs the interview: connect what the user describes to what's already tracked, and avoid proposing duplicates.

---

## Step 2: Set the interview scope

Before asking anything about features, clarify:

- **Which milestone or area** does the user want to focus on? Or are they open to anything?
- **Is there a theme?** (e.g. "we want to improve onboarding", "tightening the auth flow", "M2 planning")
- **Rough quantity**: a handful of waypoints, or a full milestone's worth?

Keep this brief: one or two questions at most. If `$focus` was passed or the user's opening message already answers these, take that as the scope and skip straight to Step 3.

---

## Step 3: The interview loop

Ask 2–4 questions per round. Never dump a long list of questions at once; it reads as homework. The questions should feel like a conversation, not a form.

### Question types

**Discovery questions**: what does the user want to build?

- "What's been frustrating you or your users about the current state of X?"
- "What would make Y feel complete?"
- "Is there anything you keep meaning to add but haven't prioritised yet?"

**Clarification questions**: sharpen something vague

- "When you say 'better X', what would that look like in practice?"
- "Is this a new screen/flow, or a change to something that already exists?"
- "Who triggers this: the user, a system event, an admin?"

**Dependency questions**: surface connections

- "Does this require anything that isn't built yet?"
- "Would this unlock anything else on the roadbook?"
- "Is this blocked by anything currently `todo` or `blocked` on the roadbook?"

**Scope questions**: keep things honest

- "Is this one waypoint, or does it break into distinct pieces?"
- "Is this MVP, or nice-to-have?"
- "Could a simpler version of this ship sooner?"

### Round discipline

After each round of answers:

- Acknowledge what you've captured (briefly; don't repeat it back verbatim)
- Ask the next 2–4 questions, either deepening existing threads or opening new ones
- **End each round** with: *"Anything else you want to explore, or shall I write up what we have?"*

Continue until the user says they're done or stops introducing new ideas.

---

## Step 4: Synthesise

Once the interview is complete, synthesise everything into a structured proposal. Do not write to the roadbook yet.

### For each proposed waypoint

Assign:

- **Proposed ID**: follow the existing `{Milestone}{Category}.{Seq}` convention. Use `?` for the seq number if the milestone/category is new and you can't determine the next number without the user confirming placement (e.g. `2TI.?`)
- **Description**: clear, imperative, task-like (not "we need to...", just "Build X" or "Add Y")
- **Proposed milestone**: which milestone this belongs to, and why
- **Proposed status**, computed mechanically: `todo` if it has no incomplete dependencies, `blocked` if it depends on anything not yet `done`, `paused`/`deferred` if it sits behind a gate that imposes those
- **Incoming dependencies**: existing waypoint IDs, a milestone ID or a gate ID that must resolve first
- **Tier gate**, when the proposed milestone is in tier 1 or above (a `(Secondary)`/`(Tertiary)` suffix on its name): the lower-tier milestones its existing waypoints carry, copied as given. A tier reaches a lower tier by milestone, never by waypoint (conventions, Tiers): a prerequisite in a lower tier that the gate already covers is noted as `Extends {ID}` and left out of the dependency list; one the gate does not cover adds its milestone to the gate (say so, since the waypoint's gate then differs from its siblings') unless the waypoint is meant to escape its tier. A `softMilestone` member of a lower-tier milestone is not covered by membership alone, so it stays in the dependency list as a waypoint edge unless a hard member of that milestone, or anything else the gate requires, depends on it, directly or through other waypoints, which covers it like any other prerequisite. `goblin-scout:add-waypoints` applies the same rule when it writes, and `validate` refuses a covered edge.
- **Outgoing dependencies**: existing waypoints this would unblock, or new waypoints in this expedition that depend on it
- **Scout**: only if the user names one during the interview. Ask, don't infer; unlike status, this is never computed. Leave unset if nobody said who owns it.

### Cross-waypoint dependencies within the expedition

If proposed waypoints depend on each other, make that explicit. Show the internal dependency chain.

### Orphan and childless flags

Apply the same checks as `goblin-scout:add-waypoints`:

- Flag any proposed waypoint with no connections as a potential orphan
- For childless waypoints that clearly enable further work, propose a placeholder child

---

## Step 5: Present the proposal

Format the proposal clearly. Group waypoints by milestone. For each waypoint:

```text
{ID}. {Description}
  Milestone: {N} ({Name})
  Status: {todo / blocked / paused / deferred}
  Scout: {name, or "unassigned"}
  Depends on: {waypoint/milestone/gate IDs or "nothing"}
  Tier gate: {lower-tier milestone IDs and the sibling they came from, or "n/a"} (tiered phases only)
  Extends: {lower-tier waypoint IDs noted rather than wired, or "nothing"} (tiered phases only)
  Enables: {IDs (existing or new) or "nothing yet"}
  [⚠ Orphan: no connections found] (if applicable)
  [+ Placeholder child proposed: {ID}. {Description}] (if applicable)
```

After the full list, include a **Dependency map**: a compact text representation of how the expedition connects internally and to existing waypoints:

```text
Existing waypoint A → New waypoint B → New waypoint C
                                     ↘ Existing waypoint D (now unblocked)
New waypoint E (standalone, orphan warning)
```

Then ask: *"Does this look right? Any waypoints to cut, rename or move? Once you're happy I'll hand this expedition to the waypoint adder."*

---

## Step 6: Hand off

Once the user approves (or approves with amendments), this skill's job is done. The output is a clean batch specification ready for `goblin-scout:add-waypoints` to process in its batch mode: all IDs assigned and edges wired in one pass, one consolidated proposal, one write.

Tell the user which mode to reach for: *"Approved. Use `/goblin-scout:add-waypoints c \"...\"` to write these to the roadbook in dependency order"* when the expedition has an asserted internal chain, or *`t`* when the waypoints are independent of each other. Pass the proposal above as context either way.

---

## What to avoid

- **Asking too many questions at once**: 2–4 per round, no more
- **Proposing things already tracked**: check the roadbook first; if something close exists, flag it rather than duplicating
- **Over-engineering the proposal**: waypoints should be concrete enough to action; design documents belong elsewhere
- **Writing to the roadbook during the interview**: the proposal is the output; the user approves before anything is written
- **Scope creep in the interview itself**: if the user's ideas balloon into a full new milestone, note it and suggest a separate planning session rather than trying to capture everything at once
