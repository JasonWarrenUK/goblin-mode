# Dossier

One file per person Jason works with regularly. Written and maintained by the
`dossier-record` skill, read by anything that needs to know who someone is.

**Everything in this directory except this README is gitignored.** These are
notes about real people; they stay on the machine. The schema is tracked so the
convention survives; the contents are not.

## File shape

`{slug}.md`, slug lowercase, matching the name they are called by.

```markdown
---
name: jaz
description: One line, used to decide relevance during recall
metadata:
  type: person
  relationship: friend, close collaborator
  pronouns: unstated
  updated: 2026-08-15
  personaId: null
---

# Jaz

## Facts

- Builds their own Claude Code skills. `2026-08-15`
- Light on advanced skill builds (frontmatter YAML, bundled scripts), fast study. `2026-08-15`
- Shares Jason's instincts on tooling and design. `2026-08-15` *(inferred)*

## Working with them

- Anything about how to pitch, hand off or collaborate.

## Open questions

- What is genuinely unknown, so a future run knows what to listen for.
```

## Rules

- **One fact per bullet, dated.** The date is when it was recorded, not when it
  became true. Staleness has to be visible.
- **Mark inference.** A fact Jason stated stands bare. Anything Claude worked
  out from context carries `*(inferred)*`. The distinction matters when the
  file is used to model how someone will behave.
- **Pronouns are recorded only when stated.** `unstated` means they/them until
  told otherwise, which is the house rule everywhere else too.
- **Durable only.** Roles, expertise, preferences, working relationships, what
  someone cares about. Not "on leave next week", not "asked me about the PR".
- **No overwrite without asking.** New facts append. A fact that contradicts an
  existing line gets raised before either version is kept, because the
  correction is usually the interesting part.
- **`metadata.personaId`: `null` until a `red-*` skill derives a persona from
  this entry, then a small integer.** Allocated once, on first derivation
  (highest existing `personaId` across the directory, plus one; `1` if none
  exist yet), never reused, never assigned speculatively. It is the only link
  between a dossier entry and its derived persona, and it exists precisely so
  that link never has to be the person's name: the persona side stores this
  number, never the slug, in a tracked file. See "Who reads it" below.

## Who reads it

- `dossier-record` writes and updates these files, including allocating
  `metadata.personaId` on first derivation (see `red-doc`/`red-branch` below).
- `red-doc` and `red-branch` read them when a persona slug is not found by
  `library/scripts/red-personas.py` in `library/references/red/personas/`,
  deriving a review profile from the entry and interviewing for the gaps. If
  `metadata.personaId` is still `null`, they ask `dossier-record` to allocate
  one before writing the derived persona; the persona file is then named and
  slugged by that number, never by the person's name, and stores
  `derived_from_updated` alongside it so a later dossier edit can be detected
  as drift (see `library/references/red/personas/README.md`). They write the
  review profile to the persona store, never back into a person file: how
  someone reviews a target is inference about them, and it belongs in a file
  labelled as such.
- `MEMORY.md` carries a one-line pointer per person, so recall finds them.
