---
name: "Stud"
description: "{{ ƔƔƔ }} Plan a non-trivial feature by interviewing to resolve unknowns, then studding every function as a runnable walking-skeleton (fake data, real wiring) so names, placement, and contracts can be reviewed before any real logic is written. Stops for review; fill is a separate pass."
arguments: ["outcome", "questions"]
argument-hint: ["desired outcome", "open questions to resolve"]
disable-model-invocation: true
model: sonnet
effort: medium
allowed-tools:
  - "Read"
  - "Glob"
  - "Grep"
  - "Edit"
  - "Write"
  - "AskUserQuestion"
  - "Bash(scripts/find-scaffold.sh:*)"
disallowed-tools:
  - "Bash(git:*)"
  - "Bash(gh:*)"
---

# Stud: Part 1, plan then skeleton (command)

You were invoked deliberately by the user with an outcome in hand. Your job is to turn a decided-upon feature into a **reviewable runnable skeleton**, and to stop there. This is a planning ritual, not an implementation run: interview first, stud second, then hand back for review. Do **not** write real logic in this skill.

**Arguments:** `$outcome` is required; `$questions` is optional (trailing). If `$questions` is empty, skip the interview (Step 1) and go straight to exploring.

## Overview

Deliver **$outcome** in **two stages** so it can be understood before it hits maximum complexity:

- **Stage 1, stud (this skill):** every function studded in its *real* file/location with real signatures, but bodies return realistic **fake data**. The whole chain runs end-to-end on dummy data. Names, placement, and contracts get reviewed here.
- **Stage 2, fill (separate):** replace the fakes with real logic, pure/leaf functions first. Each `should` bullet becomes a test.

**Core principle:** shape before logic. A stud that *runs* (fake data, real wiring) is worth more than a doc, because you can execute the plumbing and see the flow before writing a line of real logic.

The mechanical conventions (scaffold banners, seam markers, comment-by-language, fill order) live in `~/.claude/library/references/stud/conventions.md`. Read it before Step 3. A full worked example is in `~/.claude/library/references/stud/worked-example.md`.

## Steps

### 1. Interview to resolve the unknowns

Before touching code, resolve **$questions** with the user. This is the part a mid-task pass can't do: you have the user's attention, so use it. Resolving `$questions` up front is this skill's whole advantage.

- Use `AskUserQuestion` for each open question; keep going until they're all resolved or explicitly parked.
- Feed the answers back into the outcome so Steps 2 and 3 build the *agreed* shape, not a guessed one.
- If a question can't be resolved now, note it as a **carried assumption** and flag it at handoff rather than silently picking an answer.

Skip this step only if `$questions` is empty. Never invent answers to fill the gap.

### 2. Find the real homes (explore first)

Do **not** invent locations. Read the code and place each stud where it will actually live, matching the surrounding patterns (naming, the shape of similar functions, how coroutines/handlers/queries are already written).

- Identify the existing function(s)/file(s) each piece hooks into, and the pattern to mirror.
- Note anything that must change in existing code (schema, wiring, config).

### 3. Declare the shared shapes once

At the top of the relevant module, write the data shapes that flow through the feature **once** (the input shape, the stored/returned shape) and reference them everywhere instead of re-describing them per function. This stops the input/output contracts from drifting apart as you stud.

### 4. Write the stubs

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

### 5. Mark new vs edited with scaffold banners

So a reviewer can see, at a glance, what is new code versus a change to existing code. Every marker is a comment (the skeleton must still run and lint) and is labelled scaffold so it's obviously temporary. The full banner formats (`&` new, `!` edited; box for chunks, inline tag for single lines) are in `~/.claude/library/references/stud/conventions.md`. Keep the box symbols consistent so a plain-text search (`&&&&`, `!!!!`) finds every scaffold marker for removal in Stage 2.

### 6. Verify the skeleton runs

A stud skeleton that doesn't run is just a doc; the point is that it runs. Before handing off:

- Syntax/lint clean (the banners are comments, so linters must still pass).
- **Run it** on the fake data and show the flow firing, e.g. start the process and watch the log lines, or drive the entry points directly. The point is to prove the plumbing (calls, wiring, shutdown) before any real logic exists.
- Confirm the working tree contains only intended changes.
- Confirm every scaffold marker is intentional: `scripts/find-scaffold.sh --markers <studded-path>` should list exactly the banners you placed (it's expected to find them now; they get removed in Stage 2). Point it at the files you studded, not the whole repo.

### 7. STOP and hand back for review

This skill ends at a reviewable skeleton. **Do not start Stage 2.** Fill in `templates/handoff.md` and wait for the user:

- **What ran:** the flow the skeleton exercised (Step 6 output).
- **Carried assumptions:** every unresolved item from Step 1, flagged.
- **Seam inventory:** run `scripts/find-scaffold.sh --seams <path>`.
- **Proposed fill order** (pure/leaf first; see the conventions reference):
  1. Pure, unit-testable helpers (calculations, transforms, get-or-create); their `should` bullets become the tests.
  2. I/O (network, subprocess, DB reads/writes).
  3. Timing / orchestration.
  4. State + UI.

Removing the `&&&&`/`!!!!` scaffold markers is part of filling each chunk in Stage 2, not this skill's job.

---

## Reference

### Quick Reference

| Element     | Rule |
|-------------|------|
|  Interview  | Resolve `$questions` before any code; carry unresolved ones as flagged assumptions |
|  Location   | Real file, real signature, mirror the neighbouring pattern |
|    Body     | Realistic **fake** return, never null/None |
|   Shapes    | Declared once at top, referenced everywhere |
| Behaviours  | `should …` bullets → Stage 2 tests |
|    Seams    | `SEAM:` / `HOOKS INTO:` / `SCHEMA CHANGE:` |
|  Banners    | `&` new, `!` edited; see conventions reference |
|   Verify    | Skeleton **runs** on fake data + lints clean |
|   Handoff   | STOP after skeleton; user approves fill order before Stage 2 |

### Common Mistakes

- **Skipping the interview.** You have the user in the loop; resolving `$questions` up front is this skill's whole advantage. Don't guess what you could ask.
- **Bleeding into Stage 2.** This skill stops at a reviewable skeleton. Writing real logic here defeats the review gate.
- **Studs return null.** Then the chain can't run, and the whole value of the walking skeleton is lost. Return fake-but-plausible data.
- **Inventing locations.** Placing studs in made-up files instead of where they'll live. Explore first (Step 2).
- **Re-describing shapes per function.** They drift. Declare once (Step 3).
- **Banner boxes on one-liners.** More banner than code. Inline tag for single lines; box for chunks.
- **Markers that aren't comments.** Breaks the run/lint. Every scaffold marker is a comment.
- **Skipping the run.** "It compiles" is not "it runs". Actually execute the skeleton (Step 6).

### Red Flags

**Never:**

- Invent answers to `$questions` instead of asking.
- Start Stage 2 (real logic) inside this skill.
- Hand off a skeleton you haven't run.
- Leave `&&&&`/`!!!!` scaffold markers behind as if they were permanent.

**Always:**

- Interview first; flag carried assumptions at handoff.
- Return fake data so it runs.
- Declare shapes once; mirror existing patterns.
- Tag every new/edited region so the diff is scannable.
- Prove the plumbing works, then STOP for review.
