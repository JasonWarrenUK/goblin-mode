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

## Who reads it

- `dossier-record` writes and updates these files.
- `red-sabotage` reads them when a persona slug is not in
  `library/references/sabotage-personas.md`, deriving a review profile from the
  entry and interviewing for the gaps. It writes the review profile to the
  persona store, never back into a person file: how someone reviews a document
  is inference about them, and it belongs in a file labelled as such.
- `MEMORY.md` carries a one-line pointer per person, so recall finds them.
