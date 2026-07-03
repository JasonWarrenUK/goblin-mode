---
name: "Stud (approach)"
description: "Use when about to build a non-trivial feature and you want the shape reviewable before the logic. Studs every function in its real file as a runnable walking-skeleton (fake data, real wiring) so names, placement, and contracts are visible before any real logic is written. Lay the skeleton, then checkpoint for review."
when_to_use: ">=1 of the following are true: (a) spans several functions/files; (b) touches existing code in more than one place; (c) user wants to review the approach before implementation; (d) user is learning the codebase"
user-invocable: false
model: sonnet
effort: medium
allowed-tools:
  - "Read"
  - "Glob"
  - "Grep"
  - "Edit"
  - "Write"
  - "Bash(scripts/find-scaffold.sh:*)"
disallowed-tools:
  - "Bash(git:*)"
  - "Bash(gh:*)"
---

# Stud: Part 1, skeleton first (knowledge)

You reached for this skill mid-task because you're about to build something that spans several functions or files, and the shape should be reviewable before the logic. This is a **technique you apply**, not a ceremony you run: lay a runnable skeleton, prove the plumbing, then checkpoint so the shape can be reviewed before you fill it.

There is no interview here. You were triggered mid-flow, and the feature is already in play. If a genuine ambiguity blocks the skeleton, ask a single targeted question and move on; don't turn this into a planning session.

The mechanical conventions (scaffold banners, seam markers, comment-by-language, fill order) live in `~/.claude/library/references/stud/conventions.md`. Read it before writing stubs. A full worked example is in `~/.claude/library/references/stud/worked-example.md`.

## Announce at start

State the mode-switch out loud so whoever's watching knows why the next diff is full of fakes and scaffold banners:

> "I'm laying down a runnable skeleton before filling in the logic (stud skill); I'll checkpoint the shape before writing any real logic."

This line is load-bearing in the knowledge path: the user didn't ask for a skeleton, so tell them they're getting one and why.

## Overview

Build the feature in **two stages** so it can be understood before it hits maximum complexity:

- **Stage 1, stud (this skill):** every function studded in its *real* file/location with real signatures, but bodies return realistic **fake data**. The whole chain runs end-to-end on dummy data. Names, placement, and contracts get reviewed here.
- **Stage 2, fill (separate):** replace the fakes with real logic, pure/leaf functions first. Each `should` bullet becomes a test.

**Core principle:** shape before logic. A stud that *runs* (fake data, real wiring) is worth more than a doc, because you can execute the plumbing and see the flow before writing a line of real logic.

## Steps

### 1. Place each stud in its real home

Do **not** invent locations. If you've already read the relevant files in this task, reuse what you know; otherwise explore now. Place each stud where it will actually live, matching the surrounding patterns (naming, the shape of similar functions, how coroutines/handlers/queries are already written).

- Identify the existing function(s)/file(s) each piece hooks into, and the pattern to mirror.
- Note anything that must change in existing code (schema, wiring, config).

### 2. Declare the shared shapes once

At the top of the relevant module, write the data shapes that flow through the feature **once** (the input shape, the stored/returned shape) and reference them everywhere instead of re-describing them per function. This stops the input/output contracts from drifting apart as you stud.

### 3. Write the stubs

Each stud is a real, named function in its real place, that:

1. **Returns realistic fake data, not null/None.** So the chain runs as a *walking skeleton*. Return a plausible value that matches the documented output shape.
2. **Lists behaviours as `should` bullets.** Short comment lines describing what the real function must do. These are human-readable now and become the literal test cases in Stage 2.
3. **Marks the seams** where it touches things outside itself (`SEAM:` / `HOOKS INTO:` / `SCHEMA CHANGE:`; see the conventions reference).

Example (Python; use the language's own comment syntax elsewhere):

```python
def upsert_event(conn, ev):
    # INSERT a new event, or UPDATE times if its id already exists.
    # in: ServerEvent   out: None
    # SEAM: workshop resolved via get_or_create_workshop
    # should INSERT for a new id
    # should UPDATE times when the id exists and they changed
    # should no-op when nothing changed
    return None  # fake
```

Coroutines / handlers / long-lived studs should still **loop and log** so running the skeleton visibly exercises the flow, even though the bodies are empty. See `worked-example.md` for a full three-function feature.

### 4. Mark new vs edited with scaffold banners

So a reviewer can see, at a glance, what is new code versus a change to existing code. Every marker is a comment (the skeleton must still run and lint) and is labelled scaffold so it's obviously temporary. The full banner formats (`&` new, `!` edited; box for chunks, inline tag for single lines) are in `~/.claude/library/references/stud/conventions.md`. Keep the box symbols consistent so a plain-text search (`&&&&`, `!!!!`) finds every scaffold marker for removal in Stage 2.

### 5. Verify the skeleton runs

A stud skeleton that doesn't run is just a doc; the point is that it runs. Before you checkpoint:

- Syntax/lint clean (the banners are comments, so linters must still pass).
- **Run it** on the fake data and show the flow firing, e.g. start the process and watch the log lines, or drive the entry points directly. The point is to prove the plumbing (calls, wiring, shutdown) before any real logic exists.
- Confirm the working tree contains only intended changes.
- `scripts/find-scaffold.sh --markers <studded-path>` should list exactly the banners you placed (expected now; removed in Stage 2). Point it at the files you studded, not the whole repo.

### 6. Checkpoint before filling

You triggered this yourself mid-task, so don't barrel straight into Stage 2. Surface the shape and let it be reviewed **before** any real logic:

- Show what ran and the flow it exercised (Step 5 output).
- List the seams the reviewer must sign off: run `scripts/find-scaffold.sh --seams <path>`.
- State the fill order you'd take next (pure/leaf first; see the conventions reference):

  1. Pure, unit-testable helpers (calculations, transforms, get-or-create); their `should` bullets become the tests.
  2. I/O (network, subprocess, DB reads/writes).
  3. Timing / orchestration.
  4. State + UI.

- Then pause for the shape to be reviewed. Filling is Stage 2; removing the `&&&&`/`!!!!` scaffold markers happens as you fill each chunk, not here.

The whole reason you reached for a skeleton was to make the shape reviewable; skipping the checkpoint throws that away.

---

## Reference

### Quick Reference

| Element     | Rule |
|-------------|------|
|  Announce   | Say you're skeletoning first, and that you'll checkpoint before real logic |
|  Location   | Real file, real signature, mirror the neighbouring pattern (reuse files already read) |
|    Body     | Realistic **fake** return, never null/None |
|   Shapes    | Declared once at top, referenced everywhere |
| Behaviours  | `should …` bullets → Stage 2 tests |
|    Seams    | `SEAM:` / `HOOKS INTO:` / `SCHEMA CHANGE:` |
|  Banners    | `&` new, `!` edited; see conventions reference |
|   Verify    | Skeleton **runs** on fake data + lints clean |
| Checkpoint  | Surface the shape for review before Stage 2 |

### Common Mistakes

- **Skipping the announce.** The user didn't ask for a skeleton; if you don't say why the diff is full of fakes, it reads as broken code.
- **Barrelling into Stage 2.** The point of studding is a reviewable shape; filling without a checkpoint discards it.
- **Turning it into an interview.** You were triggered mid-flow; resolve real blockers with one targeted question, not a planning session.
- **Studs return null.** Then the chain can't run, and the whole value of the walking skeleton is lost. Return fake-but-plausible data.
- **Inventing locations.** Placing studs in made-up files instead of where they'll live. Explore first (Step 1).
- **Re-describing shapes per function.** They drift. Declare once (Step 2).
- **Banner boxes on one-liners.** More banner than code. Inline tag for single lines; box for chunks.
- **Markers that aren't comments.** Breaks the run/lint. Every scaffold marker is a comment.
- **Skipping the run.** "It compiles" is not "it runs". Actually execute the skeleton (Step 5).

### Red Flags

**Never:**

- Silently switch into skeleton mode without announcing it.
- Fill in real logic before the shape has been checkpointed.
- Hand off a skeleton you haven't run.
- Leave `&&&&`/`!!!!` scaffold markers behind as if they were permanent.

**Always:**

- Announce the skeleton pass and the checkpoint up front.
- Return fake data so it runs.
- Declare shapes once; mirror existing patterns.
- Tag every new/edited region so the diff is scannable.
- Prove the plumbing works, then checkpoint the shape for review.
