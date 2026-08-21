# Profiles

Two stores of the same kind of thing: a profile of a reader. Split by what is
safe to track, sharing one frontmatter schema so neither is a second-class
citizen of the other. Both are resolved by `_profiles_core.py`
(`DOSSIER_DIR`, `SHIPPED_PERSONAS_DIR`, `USER_PERSONAS_DIR`), not by this
file's own location, so this README can live inside the plugin while
describing directories that mostly don't:

```
${CLAUDE_PLUGIN_ROOT}/personas/          ← tracked; shipped with the plugin (bob, cedric)
~/.claude/library/profiles/dossier/      ← gitignored except its own README; real colleagues
~/.claude/library/profiles/personas/     ← tracked locally; a user's own personas (never shipped)
```

## Why two directories per store

`dossier/` holds real facts about real people Jason works with: role,
expertise, preferences, how they review. It stays off git entirely because a
real colleague's working notes are not something to publish, and it never
travels with the plugin — a fresh install has none of it, correctly.

`personas/` (searched across both locations above, shipped-then-user or
user-then-shipped depending on lookup order — see `personas_dirs()`) holds
nine-field models of how a specific reader attacks a target (a document or a
branch), used by the `goblin:red-doc`/`goblin:red-branch` skills. The shipped pair
(`bob`, `cedric`) is tracked, because the reports they produce are meant to
be read and iterated on, sometimes by other people; a user's own local
additions (a machine-specific persona, kept out of the distributed plugin)
live in the second, user-local location instead.

A persona can be derived from a real dossier entry — for example, `cedric.md`
is derived from a real colleague's dossier file. That link is written on both
sides via `linkedProfileIds`, which references each side's stable `id` rather
than a name or slug, and it is safe on two layers: the persona carries an
**invented name**, never the real one, and the link itself points at an
opaque id, not a name — nobody reading the tracked `personas/` directory can
identify the real person from the persona's file, even by following the
link. See [personas-README.md](personas-README.md)'s privacy section for
the full discipline, and `~/.claude/library/profiles/dossier/README.md` for
the dossier side of the same link (that file stays local; it never ships
with the plugin).

## Shared schema

Both file types use the same frontmatter fields. What differs is which ones
are populated and how specific `linkedProfileIds` is allowed to be:

| Field | Dossier | Personas |
|---|---|---|
| `id` | `DOS001`, `DOS002`… assigned once, never renumbered | `PER001`, `PER002`… same scheme, own prefix |
| `slug` | The person's name | Always invented — a name, never a number |
| `description` | One line | One line |
| `quickFacts` | Role, relationship | Reader stance in short form |
| `isRealPerson` | `true` | `false` |
| `updated` | `YYYY-MM-DD-hhmm` | `YYYY-MM-DD-hhmm` |
| `pronouns` | `unstated` until Jason says otherwise | The persona's own, as written |
| `linkedProfileIds` | May be specific — this directory never leaves the machine | Generalised only — see personas/README.md |
| `scope`, nine stance fields | `null` — a real person is not a reader model | Populated — this is what a persona is |

`id` is assigned by `${CLAUDE_PLUGIN_ROOT}/scripts/assign_profile_ids.py`, run once per new
profile file (idempotent — re-running never renumbers an existing file).

## Who reads what

- `goblin:dossier-record` writes and updates dossier entries.
- `goblin:red-doc` and `goblin:red-branch` read persona files via
  `${CLAUDE_PLUGIN_ROOT}/scripts/red-personas.py`, and derive new personas
  from dossier entries when asked, per `${CLAUDE_PLUGIN_ROOT}/references/methodology.md` Step 1c.
- `goblin:hud-profiles` reads both, read-only, for a human to browse.
