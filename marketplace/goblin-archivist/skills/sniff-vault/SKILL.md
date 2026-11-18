---
name: "Sniff Vault"
description: "Survey the Obsidian vault read-only: folder layout, note types, every property with its value shapes, tags, templates, Tasks formats, plugins, what is published and what Linter rewrites, plus a drafted schema. Writes nothing in the vault."
when_to_use: "When the vault's shape needs to be known before anything is written to it: the first run of goblin-archivist, or after the vault has been reorganised and the schema needs revisiting."
model: opus
effort: high
metadata:
  glyph: ᛟ
  family: archivist
  goblin-spinner: sniffing|tallying|rummaging|squinting
disable-model-invocation: true # reads every note in the vault; the user starts it
allowed-tools: ["Bash(python3:*)", "Read", "Write"]
---

# Sniff Vault

The archivist noses through the whole vault before it touches anything. A fixed script reads every note and writes three files outside the vault; you then read them, write your annotations to a fourth file and walk the user through what was found. Nothing is written inside the vault, by the script or by you.

## Step 0: The switch

The archivist is on: `${user_config.enabled}`. If that reads `false`, say goblin-archivist is switched off (`/config`, goblin-archivist, Archivist on) and stop.

## Step 1: Where to read and where to write

- Vault: `${user_config.vault}`
- Archivist folder: `${user_config.base_folder}`

A value that is empty or still reads `${user_config...}` is unset.

1. **Archivist folder unset:** stop. Tell the user to set it in `/config` (goblin-archivist, Archivist folder): a folder outside the vault and outside any repository that would commit it, holding one subfolder per project and `vault/` for vault-wide reports. Do not pick one for them.
2. **Vault unset:** run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/archivist.py" vaults`. It lists the vaults Obsidian knows (`path`, `open`, `exists`). Ask which one with AskUserQuestion, then carry on with that path for this run and tell the user to set the Vault option so the question does not come back.

## Step 2: Sniff

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/archivist.py" sniff --vault "<vault>" --base "<archivist folder>"
```

The script reads every Markdown note and the named files in `.obsidian` (plugin manifests and the settings of Tasks, Templater, Periodic Notes, Digital Garden, Share Note and Linter). It never reads `.trash` or any other dot-folder's notes, and it refuses an output folder inside the vault. It prints the three paths as JSON.

| Exit | Meaning | Do |
|---|---|---|
| 0 | Done | Step 3 |
| 2 | Bad path, or the output folder is inside the vault | Report the message; stop |
| 3 | Vault unset | Step 1.2 |
| 4 | Archivist folder unset | Step 1.1 |

Two runs over an unchanged vault give byte-identical files. A rerun overwrites `survey.json`, `report.md` and `schema.draft.json` and nothing else.

## Step 3: Read and annotate

Read `report.md` whole, then `schema.draft.json`. Read individual notes only to settle a question the report raises, and say which you opened.

Write `schema.notes.md` in the same folder. The script never touches that file, so annotations survive a rerun; if it already exists, read it first and add a dated section rather than replacing what is there. Never edit `schema.draft.json` or `report.md`.

The draft is mechanical: a property is required for a type when at least 90% of that type's notes carry it, optional from 10%. Annotate where the mechanism misleads, one entry per point, each with what the draft says, what you propose, why, and the question for the user:

- **Types:** apparent types that are one type under two names (`project` beside `untyped in Projects`), or one name covering two kinds of note.
- **Properties:** case or spelling variants (section 4 lists them), conflicting value shapes, values that are templating code rather than data, properties that look abandoned.
- **Tags:** case variants and near-duplicates; whether a nested family wants a root.
- **Tasks:** the line formats in use against the statuses defined; formats that look like typing slips rather than choices.
- **Publishing:** every note Digital Garden or Share Note would publish, so nothing the archivist writes later lands on the web unasked.
- **Linter:** which enabled rules would rewrite a note the archivist appends to (timestamps, tag formatting, trailing spaces).
- **Problems:** frontmatter that does not parse, with the fix each needs.

## Step 4: Walk the user through it

Lead with the totals and the three findings most likely to change the schema. Then go through `schema.notes.md` a section at a time, putting each question to the user and recording the answer in the file under the question. The schema is a proposal until the user approves it; approving it, and writing it anywhere, belong to a later step of goblin-archivist and not to this skill.
