# Stud handoff: {{ feature }}

Stage 1 (stud) is complete. This is the review gate; Stage 2 (fill) does not start until the shape below is approved.

## What ran

{{ How the skeleton was driven and the flow it exercised. Paste the log lines / entry-point output from the Verify step that prove the plumbing walks on fake data. }}

## Carried assumptions

{{ Every `$questions` item that could not be resolved in the interview, stated as the assumption taken so it can be corrected before real logic locks it in. Write "None" if the interview resolved everything. }}

- …

## Seam inventory

{{ Output of `scripts/find-scaffold.sh --seams <path>`. Each line is a point where the feature touches existing/external code the reviewer should sign off. }}

- `SEAM:` …
- `HOOKS INTO:` …
- `SCHEMA CHANGE:` …

## Proposed fill order

Pure/leaf first, then outward. Map each studded function to its slot:

1. **Pure/leaf helpers** — {{ functions }} (their `should` bullets become the tests)
2. **I/O** — {{ functions }}
3. **Timing / orchestration** — {{ functions }}
4. **State + UI** — {{ functions }}

Removing the `&&&&`/`!!!!` scaffold markers happens as each chunk is filled in Stage 2.

---

**STOP.** Awaiting review of the shape above before any real logic is written.
