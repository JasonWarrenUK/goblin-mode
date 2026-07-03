# Stud conventions (mechanical reference)

Agent-reference material shared by the stud skills (`task-execute-stud`, `role-approach-stud`). Loaded at runtime; not written for a human reader. The skill bodies carry the *why*; this file carries the mechanical *how* so the two lineages can't drift on the mechanics.

## Scaffold banners: new vs edited

Every marker is a **comment** (the skeleton must still run and lint) and is labelled scaffold so it's obviously temporary.

- **`&` = new code** (didn't exist before): new files, new functions/sections, new config blocks.
- **`!` = edited code** (existing code being changed): a new line *inside* an existing function counts as editing that function.

**Multi-line chunk → full banner box:**

```python
# &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
# new chunk, scaffold, remove on implementation
# &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
<code>
# &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
```

Use `!` and `chunk being edited, scaffold, remove on implementation` for edits.

**Single-line addition → short inline tag** (a full box would be more banner than code):

```python
# &&&& new (scaffold)
FETCH = "..."

# !!!! edit (scaffold)
poll_task = start(...)
```

Keep the box symbols consistent so a plain-text search (`&&&&`, `!!!!`) finds every scaffold marker for removal in Stage 2. The `find-scaffold.sh --markers` script does exactly this search.

## Seam markers

Mark the points where a stud touches things outside itself:

- `SEAM:` — touches external/existing logic (I/O, subprocess, another subsystem).
- `HOOKS INTO:` — wires into a specific existing call site.
- `SCHEMA CHANGE:` — a DB/interface change.

`find-scaffold.sh --seams` inventories these for the handoff/checkpoint summary.

## Comment prefix by language

Every marker above is a comment, so use the target language's own comment syntax:

| Prefix | Languages |
|--------|-----------|
| `#`    | Python, shell, YAML |
| `//`   | JS/TS, Go, Rust, C |
| `--`   | SQL, Lua |

## Fill order (Stage 2)

Replace fakes with real logic **pure/leaf functions first**:

1. Pure, unit-testable helpers (calculations, transforms, get-or-create); their `should` bullets become the tests.
2. I/O (network, subprocess, DB reads/writes).
3. Timing / orchestration.
4. State + UI.

Removing the `&&&&`/`!!!!` scaffold markers is part of filling each chunk.
