# Red personas

One file per persona, read and written by `${CLAUDE_PLUGIN_ROOT}/scripts/red-personas.py`
and by the `red` skills' persona-resolution steps (see `${CLAUDE_PLUGIN_ROOT}/references/methodology.md`).
Each one is a specific reader whose motive, reach and attention pattern decide
what kills a target in their hands. A persona is only useful if it makes
different evidence lethal; two personas that reject a target for the same
reason are one persona — `red-personas.py audit` checks for exactly that.

Sibling of the dossier store in spirit, not in directory: the shipped
personas this file describes live at `${CLAUDE_PLUGIN_ROOT}/personas/`,
while `~/.claude/library/profiles/dossier/` (never shipped) is the real-people
half of the same schema. See [profiles-README.md](profiles-README.md) for
how the two halves fit together, and `personas_dirs()` in `_profiles_core.py`
for how a user's own local personas (`~/.claude/library/profiles/personas/`)
are searched alongside the shipped pair described here.

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

- `id` is a stable identifier assigned once by `${CLAUDE_PLUGIN_ROOT}/scripts/assign_profile_ids.py`
  — three-letter store prefix (`PER` here, `DOS` for a dossier entry) plus a
  three-digit number, highest-existing-plus-one, never reused or renumbered. This is
  what `linkedProfileIds` references, precisely so a persona can be renamed (its
  `slug` changed) without orphaning every link pointing at it.
- `slug` matches the filename (`{slug}.md`). **Always a name** — invented for a
  persona with no real-world source (`bob`), or the invented name given to a persona
  derived from a real dossier entry (`cedric`, derived from a real colleague's
  dossier file). See the privacy section below for why an invented name is
  itself the anonymisation.
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

`~/.claude/library/profiles/dossier/` is entirely gitignored except its README; this directory is
**tracked**, and reports built from it can be read by other people. A persona
derived from a real person carries an **invented** name, never the real one —
`cedric.md` is derived from a real colleague's dossier entry, and that
substitution is what keeps this directory safe to track:

- **The persona's name is never the real person's name.** `cedric.md` names no
  dossier file. Nobody reading this tracked directory can tell who, if anyone,
  a given persona was modelled on; the invented name itself is the
  anonymisation, not a number standing in for one.
- **`quickFacts` on a persona is not automatically identical to `quickFacts` on its
  source dossier entry.** The persona's version describes the reader stance
  (`"fully fluent, no charity, forensic numbered dossiers"`); the dossier's describes
  the real relationship (`"regular collaborator"`). Copying the dossier's `quickFacts`
  onto the persona verbatim would reattach identifying content to a tracked file —
  write the persona's own, generalised past identifiability.
- **`linkedProfileIds` here names an opaque `id`, never a slug or a name.** `["DOS005",
  false, ...]` carries no more information than "some dossier entry, unspecified,
  links here" — resolving it back to the real person requires reading the
  gitignored dossier directory and finding whichever file's `id` matches,
  which only works on the machine that has that directory. The dossier side
  (gitignored, so safe to be specific) can say `"derived persona: fully
  fluent, no charity, blocks by attrition"` in its own `linkDescription`; the
  persona side keeps its
  `linkDescription` generic — never a project name, a file path, or a quote
  attributable to one person — the same generalisation discipline methodology.md's
  Step 1c always required, now backed by an id that carries nothing identifying
  even before the description discipline is applied.
- The nine frontmatter summaries are a compressed index into the body, not a
  competing copy: written at the same time as the prose, by whichever step drafts the
  persona, so they start in sync. `red-personas.py audit` catches drift or
  near-duplication after the fact; it does not enforce sync at write time.

**A persona derived from the operator's own dossier entry is still subject
to the discipline above.** Deriving a persona from your own dossier file
(rather than a colleague's) doesn't relax the generalisation rule: the
persona still carries an invented name and a generalised stance, never a
direct restatement of your own file's contents, and it never points back at
your dossier entry the way that entry might point outward at your own
config. A persona's job is to carry its own stance, not defer to another
file's, even your own.

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

## A doc persona's Reads/Skips rarely transfer to code unmodified

A persona's prose-side Reads/Skips describe how someone moves through prose
(TLDR-first, Deep-Dive skipping, say). A code reviewer's Reads/Skips describe
how they move through a diff instead: whether they open the tests, whether
they follow a changed signature out to its callers, whether they read the
whole file or just the highlighted lines. Porting a persona across that
boundary means rewriting Reads/Skips/Stake/Trigger for the new domain while
keeping Needs/Power/Charity/Verdict style unchanged — same stance, different
material. `bob` and `cedric` (both `scope: [doc, branch]`) are the worked
examples: one person, one nine-field stance each, with the domain-specific
fields spelling out both readings explicitly rather than being duplicated
into two files. `red-personas.py audit` is what catches it if a "ported"
persona drifts far enough from the original
to actually be two people, or close enough that it should have been merged like this
one was — the schema and the resolution logic are shared regardless; whether a given
persona is one entry or two is a judgement call the audit surfaces, not a rule.

## Default and suggested pair

A run naming no persona defaults to `bob` (`scope: [doc, branch]`, the
lightweight of the two shipped dual-scope personas) rather than asking — see
`methodology.md`'s Step 1. `cedric` is the heavier alternative, also
`scope: [doc, branch]`, for when a forensic pass is wanted deliberately. The
explicit roster lookup (`/red-doc personas` or `/red-branch personas`, with
no other arguments) still shows every scoped persona and picks nothing. A
run that names a persona missing from this directory interviews for the nine
fields and writes a new file here before the report starts.
