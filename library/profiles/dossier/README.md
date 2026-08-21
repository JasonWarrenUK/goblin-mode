# Dossier

One file per person Jason works with regularly. Written and maintained by the
`dossier-record` skill, read by anything that needs to know who someone is.
Sibling of [../personas/](../personas/) under `library/profiles/`; the two
share one schema, split by what is safe to track. See
[../README.md](../README.md) for how the two halves fit together.

**Everything in this directory except this README is gitignored.** These are
notes about real people; they stay on the machine. The schema is tracked so the
convention survives; the contents are not.

## File shape

`{slug}.md`, slug lowercase, matching the name they are called by.

```markdown
---
slug: jaz
description: One line, used to decide relevance during recall
quickFacts: friend, close collaborator
isRealPerson: true
updated: 2026-08-21-1212
pronouns: unstated
linkedProfileIds: []
scope: []
needs: null
stake: null
power: null
fluency: null
reads: null
skips: null
trigger: null
charity: null
verdict_style: null
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

## Frontmatter, shared with the persona store

The full field list (see [../personas/README.md](../personas/README.md) for
the persona-side reading of the same schema):

| Field | On a dossier entry |
|---|---|
| `slug` | The filename, lowercase, matching the name they are called by |
| `description` | One line, used to decide relevance during recall |
| `quickFacts` | A short search surface: role, relationship. Not automatically identical to a linked persona's `quickFacts` — see below |
| `isRealPerson` | Always `true` here |
| `updated` | `YYYY-MM-DD-hhmm`, bumped whenever the file changes |
| `pronouns` | `unstated` until Jason says otherwise; they/them in the meantime |
| `linkedProfileIds` | See "Linking to a persona" below |
| `scope`, `needs`…`verdict_style` | The nine reader-behaviour fields, `null` here. A real person is not modelled as a reviewer; they are only linked to a persona that is |

## Linking to a persona

`linkedProfileIds` is a list of `["<slug>", <isSource>, "<updated at link time>",
"<linkDescription>"]` quadruples, many-to-many. On the dossier side this can
name the linked persona directly and describe the link in specific terms,
because **this directory never leaves the machine**: `isSource: true` marks
this entry as the origin of that persona.

```yaml
linkedProfileIds:
  - ["cedric", true, "2026-08-21-1212", "derived persona: fully fluent, no charity, blocks by attrition on unreconciled claims"]
```

The persona side of the same link is deliberately less specific — see
[../personas/README.md](../personas/README.md)'s privacy section. A stale link
(the linked persona's own `updated` now newer than the timestamp recorded
here) means the persona was drafted from an older version of this entry and a
refresh is worth offering.

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
- **A persona derived from this entry gets an invented name, never a number.**
  See [../personas/README.md](../personas/README.md) for why an invented name
  is itself the anonymisation. `linkedProfileIds` is written on both sides at
  derivation time.

## Who reads it

- `dossier-record` writes and updates these files, including writing
  `linkedProfileIds` on first derivation (see `red-doc`/`red-branch` below).
- `red-doc` and `red-branch` read them when a persona slug is not found by
  `library/scripts/red-personas.py` in `library/profiles/personas/`,
  deriving a review profile from the entry and interviewing for the gaps. The
  derived persona is written to the persona store under an invented name,
  never back into this person's file: how someone reviews a target is
  inference about them, and it belongs in a file labelled as such.
- `MEMORY.md` carries a one-line pointer per person, so recall finds them.
