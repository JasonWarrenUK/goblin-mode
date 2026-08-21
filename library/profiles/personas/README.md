# Red personas

One file per persona, read and written by `library/scripts/red-personas.py` and by
the `red` skills' persona-resolution steps (see `../../references/red/methodology.md`). Each one is a
specific reader whose motive, reach and attention pattern decide what kills a target
in their hands. A persona is only useful if it makes different evidence lethal; two
personas that reject a target for the same reason are one persona — `red-personas.py
audit` checks for exactly that.

Sibling of [../dossier/](../dossier/) under `library/profiles/`; the two share
one schema, split by what is safe to track. See [../README.md](../README.md)
for how the two halves fit together.

## File contract

```markdown
---
id: PER002
slug: bob
description: <one line>
quickFacts: <short search surface>
isRealPerson: false
updated: <YYYY-MM-DD-hhmm>
pronouns: <the persona's own, as written in the prose body>
linkedProfileIds: []
scope: [doc]
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

- `id` is a stable identifier assigned once by `library/scripts/assign_profile_ids.py`
  — three-letter store prefix (`PER` here, `DOS` for a dossier entry) plus a
  three-digit number, highest-existing-plus-one, never reused or renumbered. This is
  what `linkedProfileIds` references, precisely so a persona can be renamed (its
  `slug` changed) without orphaning every link pointing at it.
- `slug` matches the filename (`{slug}.md`). **Always a name** — invented for a
  persona with no real-world source (`bob`), or the invented name given to a persona
  derived from a real dossier entry (`cedric`, derived from Max). See the privacy
  section below for why an invented name is itself the anonymisation.
- `isRealPerson`: always `false` here. A persona is a reader model, never a person.
- `linkedProfileIds`: `[]` for an invented persona with no real source. For a persona
  derived from a dossier entry, a list of `["<dossier id>", false, "<updated at
  link time>", "<linkDescription>"]` quadruples — `isSource: false` because the
  dossier entry is the origin, this file the derivation. The dossier `id` this
  references (e.g. `"DOS005"`) carries no name and no slug on its own — see the
  privacy section for what `linkDescription` may and may not add on top.
- `scope` is a list: `[doc]`, `[branch]`, or `[doc, branch]` for a persona that reads
  both the same way. This is the field that lets one persona serve more than one
  `red-*` skill without being duplicated.

## The privacy boundary: an invented name, and an opaque id, are the anonymisation

`library/profiles/dossier/` is entirely gitignored except its README; this directory is
**tracked**, and reports built from it can be read by other people. A persona
derived from a real person carries an **invented** name, never the real one — Cedric
is Max's persona, and that substitution is what keeps this directory safe to track:

- **The persona's name is never the real person's name.** `cedric.md`, not `max.md`.
  Nobody reading this tracked directory can tell Cedric was modelled on anyone in
  particular; the name itself is the anonymisation, not a number standing in for one.
- **`quickFacts` on a persona is not automatically identical to `quickFacts` on its
  source dossier entry.** The persona's version describes the reader stance
  (`"fully fluent, no charity, forensic numbered dossiers"`); the dossier's describes
  the real relationship (`"regular collaborator"`). Copying the dossier's `quickFacts`
  onto the persona verbatim would reattach identifying content to a tracked file —
  write the persona's own, generalised past identifiability.
- **`linkedProfileIds` here names an opaque `id`, never a slug or a name.** `["DOS005",
  false, ...]` carries no more information than "some dossier entry, unspecified,
  links here" — resolving it back to Max requires reading the gitignored dossier
  directory and finding whichever file's `id` matches, which only works on the
  machine that has that directory. The dossier side (gitignored, so safe to be
  specific) can say `"derived persona: fully fluent, no charity, blocks by
  attrition"` in its own `linkDescription`; the persona side keeps its
  `linkDescription` generic — never a project name, a file path, or a quote
  attributable to one person — the same generalisation discipline methodology.md's
  Step 1c always required, now backed by an id that carries nothing identifying
  even before the description discipline is applied.
- The nine frontmatter summaries are a compressed index into the body, not a
  competing copy: written at the same time as the prose, by whichever step drafts the
  persona, so they start in sync. `red-personas.py audit` catches drift or
  near-duplication after the fact; it does not enforce sync at write time.

**The one exception: `goblin.md`.** The generalisation discipline above exists
to protect other people from having their identity reattached to a tracked
file. Goblin is derived from Jason's own dossier entry (`jason.md`), and
Jason's conventions are already published in this same tracked config
(`CLAUDE.md`, this output style) — there is no third party to protect by
generalising his stated preferences into vaguer language. `goblin.md`
distils rather than generalises: it states his actual conventions directly
(no em dashes, cite sources, no sycophancy) rather than the behavioural
pattern those conventions imply. The distinction that still holds: it still
does not point back at his file the way `jason.md` points outward at
`CLAUDE.md` — a persona's job is to carry its own stance, not defer to
another file's, even when that file is safe to name.

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
