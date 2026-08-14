# Stud Methodology

The shared core both stud skills execute: `do-stud` (user-invoked, interviews first) and `clod-approach-stud` (self-triggered mid-build, announces first). Each skill's own file carries only what differs; everything below applies to both. Mechanical conventions (banner formats, seam markers, comment-by-language, fill order detail) stay in [conventions.md](conventions.md); a full three-function example is in [worked-example.md](worked-example.md).

## Contents

- The two stages and the core principle
- Find the real homes
- Declare the shared shapes once
- Write the stubs
- Scaffold banners
- Verify the skeleton runs
- The fill order (Stage 2 preview)
- Shared mistakes and hard rules

## The two stages and the core principle

Build the feature in **two stages** so it can be understood before it hits maximum complexity:

- **Stage 1, stud (this pass):** every function studded in its *real* file/location with real signatures, but bodies return realistic **fake data**. The whole chain runs end-to-end on dummy data. Names, placement and contracts get reviewed here.
- **Stage 2, fill (separate):** replace the fakes with real logic, pure/leaf functions first. Each `should` bullet becomes a test.

**Core principle:** shape before logic. A stud that *runs* (fake data, real wiring) is worth more than a doc, because you can execute the plumbing and see the flow before writing a line of real logic.

## Find the real homes

Do **not** invent locations. Read the code (reusing files already read this task where applicable) and place each stud where it will actually live, matching the surrounding patterns: naming, the shape of similar functions, how coroutines/handlers/queries are already written.

- Identify the existing function(s)/file(s) each piece hooks into, and the pattern to mirror.
- Note anything that must change in existing code (schema, wiring, config).

## Declare the shared shapes once

At the top of the relevant module, write the data shapes that flow through the feature **once** (the input shape, the stored/returned shape) and reference them everywhere instead of re-describing them per function. This stops the input/output contracts from drifting apart as you stud.

## Write the stubs

Each stud is a real, named function in its real place, that:

1. **Returns realistic fake data, not null/None.** So the chain runs as a *walking skeleton*. Return a plausible value that matches the documented output shape.
2. **Lists behaviours as `should` bullets.** Short comment lines describing what the real function must do. These are human-readable now and become the literal test cases in Stage 2.
3. **Marks the seams** where it touches things outside itself (`SEAM:` / `HOOKS INTO:` / `SCHEMA CHANGE:`; see [conventions.md](conventions.md)).

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

Coroutines / handlers / long-lived studs should still **loop and log** so running the skeleton visibly exercises the flow, even though the bodies are empty. See [worked-example.md](worked-example.md) for a full three-function feature.

## Scaffold banners

Mark new vs edited code so a reviewer can see, at a glance, what is new versus a change to existing code. Every marker is a comment (the skeleton must still run and lint) and is labelled scaffold so it's obviously temporary. The full banner formats (`&` new, `!` edited; box for chunks, inline tag for single lines) are in [conventions.md](conventions.md). Keep the box symbols consistent so a plain-text search (`&&&&`, `!!!!`) finds every scaffold marker for removal in Stage 2.

## Verify the skeleton runs

A stud skeleton that doesn't run is just a doc; the point is that it runs. Before the handoff/checkpoint:

- Syntax/lint clean (the banners are comments, so linters must still pass).
- **Run it** on the fake data and show the flow firing: start the process and watch the log lines, or drive the entry points directly. The point is to prove the plumbing (calls, wiring, shutdown) before any real logic exists.
- Confirm the working tree contains only intended changes.
- `"$HOME"/.claude/library/scripts/find-scaffold.sh --markers <studded-path>` should list exactly the banners you placed (expected now; removed in Stage 2). Point it at the files you studded, not the whole repo.

For the seam inventory at handoff: `"$HOME"/.claude/library/scripts/find-scaffold.sh --seams <path>`.

## The fill order (Stage 2 preview)

Stated at handoff, executed in Stage 2, pure/leaf first:

1. Pure, unit-testable helpers (calculations, transforms, get-or-create); their `should` bullets become the tests.
2. I/O (network, subprocess, DB reads/writes).
3. Timing / orchestration.
4. State + UI.

Removing the `&&&&`/`!!!!` scaffold markers is part of filling each chunk in Stage 2, never Stage 1's job.

## Shared mistakes and hard rules

Mistakes:

- **Studs return null.** Then the chain can't run, and the whole value of the walking skeleton is lost. Return fake-but-plausible data.
- **Inventing locations.** Placing studs in made-up files instead of where they'll live. Explore first.
- **Re-describing shapes per function.** They drift. Declare once.
- **Banner boxes on one-liners.** More banner than code. Inline tag for single lines; box for chunks.
- **Markers that aren't comments.** Breaks the run/lint. Every scaffold marker is a comment.
- **Skipping the run.** "It compiles" is not "it runs". Actually execute the skeleton.

**Never:** write real logic in Stage 1; hand off a skeleton you haven't run; leave scaffold markers behind as if they were permanent. **Always:** return fake data so it runs; declare shapes once and mirror existing patterns; tag every new/edited region so the diff is scannable; prove the plumbing works, then stop for review.
