---
name: "HUD: Profiles"
description: "Show the profiles stored in the dossier and persona stores"
when_to_use: "When Jason wants to see who's recorded in the dossier or persona stores, look up a specific person or persona, or check whether a real colleague has a derived persona linked to them."
model: sonnet
effort: low
metadata:
  glyph: ᛊ
  family: hud
disable-model-invocation: false # read-only viewer, no gate needed
disallowed-tools: ["Edit", "Write", "NotebookEdit"]
allowed-tools: ["Bash(python3 \"$HOME\"/.claude/library/scripts/profiles.py:*)"]
arguments: ["action", "target"]
argument-hint: "[list [dossier|personas] | show <name>] (no args = usage)"
---

# HUD: Profiles

Two stores, one schema, one viewer: `library/profiles/dossier/` (real colleagues, gitignored) and `library/profiles/personas/` (invented or persona-derived adversarial readers, tracked). See `library/profiles/README.md` for how they relate. This skill never writes to either — it prints to the terminal and stops.

## No arguments

```
Usage: /hud-profiles list [dossier|personas]
       /hud-profiles show <name>

dossier: N profiles   personas: N profiles
```

Run `python3 ~/.claude/library/scripts/profiles.py list --store both` to get the counts, then print the usage block above with those numbers filled in. Stop here.

## Action: `list`

```bash
python3 ~/.claude/library/scripts/profiles.py list --store both
```

Print the output under two headed sections, **Dossier** and **Personas**, each row as `slug — description`. If a dossier entry's `linkedProfileIds` names a persona, note it inline: `dan — Jason's manager; software developer`; `max — Works with Jason and Jaz, nothing else recorded yet (→ cedric)`.

## Action: `list dossier`

```bash
python3 ~/.claude/library/scripts/profiles.py list --store dossier
```

Dossier section only.

## Action: `list personas`

```bash
python3 ~/.claude/library/scripts/profiles.py list --store personas
```

Personas section only.

## Action: `show <name>`

```bash
python3 ~/.claude/library/scripts/profiles.py get <name> --store both
```

This resolves across both stores at once, so a name present in both (a real person whose derived persona happens to share a slug — not possible today, since personas always take an invented name, but the script doesn't assume that will always hold) prints both sections it returns.

Otherwise:

- **Found in dossier only**: print the profile. If `linkedProfileIds` names a persona, follow it — run `get <linked-slug> --store personas` and print that too, dossier first, so the source and its derived reader model sit together. Flag if the linked persona's own `updated` is newer than the timestamp recorded in the dossier's `linkedProfileIds` entry (a drift the derivation hasn't caught up with yet).
- **Found in personas only**: print the profile. If `linkedProfileIds` names a dossier entry, this is a tracked file pointing at a gitignored one — do not attempt to read the dossier entry to "complete the picture" beyond what the persona's own `linkedProfileIds.linkDescription` already says; that description is deliberately generalised and is the whole point of the boundary. Note the link exists (`derived from a real colleague's review pattern`) without trying to resolve or print the dossier side unless the name matches something already found in this same `show` call.
- **Found in neither**: say so plainly. If the CLI's own "not found" message came back, relay it; do not guess at a near match — that's `/dossier-record`'s job for the dossier side, not this skill's.

## Red flags

**Never** print `linkedProfileIds` from a persona file and then separately fetch and print the dossier entry it names, unless that dossier entry was already the direct subject of this same `show` call. Chaining persona → dossier automatically is exactly the identity resolution the tracked/gitignored split exists to prevent. Chaining dossier → persona is fine and intended: the dossier already has the name, nothing new is revealed by following the link forward.

**Never** write anything. If Jason wants to record a fact, that's `/dossier-record`. If a persona needs deriving, that's `red-doc`/`red-branch`'s Step 1c in `library/references/red/methodology.md`.

<raw-arguments value="$ARGUMENTS" />
