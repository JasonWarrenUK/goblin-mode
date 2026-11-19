---
name: "Consult Dossiers"
description: "Show the profiles stored in the dossier and persona stores"
when_to_use: "When the user wants to see who's recorded in the dossier or persona stores, look up a specific person or persona or check whether a real colleague has a derived persona linked to them."
model: sonnet
effort: low
metadata:
  glyph: ᛊ
  family: hud
  goblin-spinner: consulting the dossiers|leafing through files|opening the store
disable-model-invocation: false # read-only viewer, no gate needed
disallowed-tools: ["Edit", "Write", "NotebookEdit"]
allowed-tools: ["Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/profiles.py *)"]
arguments: ["action", "store", "modifier"]
argument-hint: "[list [dossier|personas] [full|short] | count [dossier|personas] | show <name>] (no args = usage)"
---

# Consult Dossiers

Two stores, one schema, one viewer: the dossier store (real colleagues, never committed anywhere public) and the personas store (invented or persona-derived adversarial readers). Where each lives comes from the plugin's `dossier_dir` and `personas_dir` options, defaulting to goblin-mode's `~/.claude/library/profiles/dossier/` and `~/.claude/library/profiles/personas/`. No profile ships with the plugin. This skill never writes to either store: it prints to the terminal and stops.

Every command below is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/profiles.py --dossier-dir "${user_config.dossier_dir}" --personas-dir "${user_config.personas_dir}"` followed by the action (the quotes keep a path with a space whole; the script expands a leading `~/` itself); written below as `profiles.py <action>` for short, but always run in full.

**Exit 2 means a store or PyYAML is missing.** The script prints one `missing:` line naming it and the option that set it. Relay the line, say which option in `/config` points elsewhere, and stop.

## Parsing `$ARGUMENTS`

- **No arguments**: go to "No arguments" below.
- **First token is `list` or `count`**: that action. An optional second token `dossier` or `personas` scopes the store (default both). `list` takes an optional third token `full` or `short` (default `short`).
- **First token is `show`**: `show <name>` (name is the next token).
- **Anything else** (one bare token, no recognised verb, e.g. `/goblin-seneschal:consult-dossiers tam`): treat it as `show <that token>`. A bare name defaults to showing that profile; this is the only implicit default this skill takes, and it exists because "look someone up" is the common case.

## No arguments

Do not run anything. Print tersely and stop:

```
Usage: /goblin-seneschal:consult-dossiers list [dossier|personas] [full|short]
       /goblin-seneschal:consult-dossiers count [dossier|personas]
       /goblin-seneschal:consult-dossiers show <name>
```

No script call, no counts, no listing. If the user wants counts they'll ask for `count`; printing a full listing on a bare invocation spends tokens on output that might not be wanted.

## Action: `count`

```bash
profiles.py count --store <dossier|personas|both>
```

Bare `count` (no store token) requests both and is fine to run directly: it's cheap, two lines of output. Print the result as-is.

## Action: `list`

```bash
profiles.py list --store <dossier|personas|both> --format <short|full>
```

Default store is `both`, default format is `short` (slugs only, one per line, no description). `full` adds `id`, `description`, `quickFacts`, `isRealPerson`, `pronouns`, `linkedProfileIds`, `scope` per profile, never the nine stance fields (`needs` through `verdict_style`); those stay reserved for `show`. Print the output under headed sections per store when both are shown.

## Action: `show <name>`

```bash
profiles.py get <name> --store both
```

`<name>` resolves as a slug or an `id` (`profiles.py get` tries both). This call checks both stores at once, so a name present in both prints both sections it returns.

Otherwise:

- **Found in dossier only**: print the profile. If `linkedProfileIds` names a persona (by `id`), follow it: run `get <id> --store personas` and print that too, dossier first, so the source and its derived reader model sit together. Flag if the linked persona's own `updated` is newer than the timestamp recorded in the dossier's `linkedProfileIds` entry (a drift the derivation hasn't caught up with yet).
- **Found in personas only**: print the profile. If `linkedProfileIds` names a dossier entry (by `id`, e.g. `DOS000`), that id alone carries no name: do not attempt to resolve it to "complete the picture"; that is exactly the identity resolution the id and the dossier's separate store exist to prevent. Note the link exists (`derived from a real colleague's review pattern`) without resolving or printing the dossier side unless that same id was already the direct subject of this same `show` call.
- **Found in neither**: say so plainly. If the CLI's own "not found" message came back, relay it; do not guess at a near match: that's the recording skill's job for the dossier side, not this one's.

## Red flags

**Never** print `linkedProfileIds` from a persona file and then separately fetch and print the dossier entry it names, unless that dossier entry was already the direct subject of this same `show` call. Chaining persona → dossier automatically is exactly the identity resolution the separate stores exist to prevent. Chaining dossier → persona is fine and intended: the dossier already names the persona's id, nothing new is revealed by following the link forward.

**Never** write anything. Recording a fact about a person is goblin-mode's `/dossier-record`; deriving a persona is the `red-doc`/`red-branch` methodology. On a machine without those, say so rather than editing a store by hand.

<raw-arguments value="$ARGUMENTS" />
