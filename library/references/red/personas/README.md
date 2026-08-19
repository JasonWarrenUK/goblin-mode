# Red personas

One file per persona, read and written by `library/scripts/red-personas.py` and by
the `red` skills' persona-resolution steps (see `../methodology.md`). Each one is a
specific reader whose motive, reach and attention pattern decide what kills a target
in their hands. A persona is only useful if it makes different evidence lethal; two
personas that reject a target for the same reason are one persona — `red-personas.py
audit` checks for exactly that.

## File contract

```markdown
---
slug: bob
scope: [doc]
dossier_id: null
derived_from_updated: null
needs: <one clause>
stake: <one clause>
power: <one clause, or a stable token like "veto" / "no veto">
fluency: <one clause>
reads: <one clause>
skips: <one clause>
trigger: <one clause>
charity: <one clause>
verdict_style: <one clause>
---

**Needs:** <full paragraph>
...all nine fields, full prose, exactly as the frontmatter summarises them...
```

- `slug` matches the filename (`{slug}.md`). For an invented persona (`bob`, `cedric`)
  this is a name. **For a persona derived from a real dossier entry, this is the
  dossier's `metadata.personaId` as a number** (`personas/7.md`, `slug: 7`) — never the
  person's name. See the privacy section below for why.
- `scope` is a list: `[doc]`, `[branch]`, or `[doc, branch]` for a persona that reads
  both the same way. This is the field that lets one persona serve more than one
  `red-*` skill without being duplicated.
- `dossier_id`: `null`, or the numeric `metadata.personaId` this persona was derived
  from — the same number as `slug`, when derived. Redundant with `slug` on purpose:
  `slug` is what the resolution flow looks up by, `dossier_id` is what states the
  provenance explicitly for a reader of the file, in case a future convention ever
  gives derived personas a different slug scheme.
- `derived_from_updated`: `null`, or the dossier entry's `metadata.updated` value at
  the moment of derivation. Compared against the live dossier file's current
  `metadata.updated` at Step 1's resolution time (methodology.md) to detect drift: if
  the dossier has newer facts than the persona was derived from, the run offers a
  refresh before proceeding rather than reviewing on a stale model.

## The privacy boundary: numbers, not names, in this tracked directory

`library/dossier/` is entirely gitignored except its README; this directory is
**tracked**, and reports built from it can be read by other people. A persona
derived from a real person must therefore carry nothing that identifies them:

- **No name in the filename or `slug`.** The dossier's `metadata.personaId` (a small
  integer, allocated once by `dossier-record` on first derivation — see its Step 2a)
  is what stands in for the person everywhere in this directory.
- **No paraphrase of their dossier entry.** Facts get generalised to the behavioural
  pattern they imply, never lifted close enough to be traceable back (no project
  names, file paths, or quotes attributable to one person). See methodology.md's Step
  1c for the full derivation discipline this directory depends on.
- **The link is one-directional and machine-readable, not memorable.** Given a
  `personas/{n}.md` file, nothing in this directory says whose dossier entry it came
  from beyond the number itself; going from number back to name means reading the
  gitignored `library/dossier/` directory and checking each file's `personaId`, which
  is exactly the point — that lookup only works on the machine that has the dossier.
- The nine frontmatter summaries are a compressed index into the body, not a
  competing copy: written at the same time as the prose, by whichever step drafts the
  persona, so they start in sync. `red-personas.py audit` catches drift or
  near-duplication after the fact; it does not enforce sync at write time.

## Field purposes

| Field | What it does |
|---|---|
| Needs | The decision they opened the target to make. Generates the "left without what they came for" findings |
| Stake | What they are protecting: turf, budget, a prior decision, their own record. Aims the search at content rather than form |
| Power | What they can actually do to the target. Ranks the order of fire across personas |
| Fluency | How much domain vocabulary they carry. Decides whether an undefined term is a nitpick or a wall |
| Reads | Which parts they actually consume, in order |
| Skips | What they will not open, and whether that is principle or habit |
| Trigger | The specific thing that makes them reject the target |
| Charity | How much benefit of the doubt they extend. Decides whether the small stuff counts at all |
| Verdict style | What their rejection looks like: a sentence, a dossier, silence |

## A doc-only persona's Reads/Skips rarely transfer to code as-is

`bob`'s Reads/Skips describe how someone moves through prose (TLDR-first, Deep-Dive
skipping). A code reviewer's Reads/Skips describe how they move through a diff
instead: whether they open the tests, whether they follow a changed signature out to
its callers, whether they read the whole file or just the highlighted lines. Porting
a persona across that boundary means rewriting Reads/Skips/Stake/Trigger for the new
domain while keeping Needs/Power/Charity/Verdict style unchanged — same stance,
different material. `cedric` (`scope: [doc, branch]`) is the worked example: one
person, one nine-field stance, with the domain-specific fields spelling out both
readings explicitly rather than being duplicated into two files. `red-personas.py
audit` is what catches it if a "ported" persona drifts far enough from the original
to actually be two people, or close enough that it should have been merged like this
one was — the schema and the resolution logic are shared regardless; whether a given
persona is one entry or two is a judgement call the audit surfaces, not a rule.

## Suggested pair

`bob`, `cedric` for `/red-doc`. A run that names no persona shows the scoped roster
and asks; it never picks for you. A run that names a persona missing from this
directory interviews for the nine fields and writes a new file here before the
report starts.
