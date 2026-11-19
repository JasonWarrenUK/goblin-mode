# goblin-archivist

*Goblin keeps everything. Goblin knows where everything is. Goblin has not decided yet whether to tell you.*

> [!NOTE]
> A Claude Code plugin from [goblin-mode](https://github.com/JasonWarrenUK/goblin-mode) that connects every session on one Mac to one local Obsidian vault. This first release does one thing: it sniffs the vault, read-only, and tells you what is in it.

---

## 1. Install

```sh
claude plugin marketplace add JasonWarrenUK/goblin-mode
claude plugin install goblin-archivist@goblin-mode
```

Needs Claude Code 2.1.287 or later and `python3` on the path. Works only where the vault is: one machine, never a cloud session.

---

## 2. Options

Set in `/config` under goblin-archivist.

| Option | What it is |
|---|---|
| Archivist on | The one switch. Off, the mod registers nothing and every archivist skill stops before reading anything |
| Vault | The vault folder. Left empty, `sniff-vault` lists the vaults Obsidian knows and asks |
| Archivist folder | Where the archivist keeps its own files, outside the vault: a subfolder per project and `vault/` for vault-wide reports. Required; nothing runs without it. Point it somewhere no repository will commit |

---

## 3. `/goblin-archivist:sniff-vault`

Surveys the whole vault and writes nothing in it. A fixed script, with no model in it, reads every note and writes three files to `<Archivist folder>/vault/sniff/`:

| File | Holds |
|---|---|
| `report.md` | Folder layout, note types, every property with its value shapes, tags, templates, Tasks line formats, plugins, published notes, Linter rules and frontmatter that will not parse, with the draft schema in brief |
| `survey.json` | The same counts, whole |
| `schema.draft.json` | A schema drafted from the counts by fixed thresholds |

Claude then writes `schema.notes.md` beside them, proposing where the draft should change and asking you about each point. Run it twice over an unchanged vault and the three script files come out byte for byte the same; your annotations are never overwritten.

---

## 4. Files

| Path | Role |
|---|---|
| `skills/sniff-vault/SKILL.md` | The skill |
| `scripts/archivist.py` | Command line: `vaults`, `sniff` |
| `scripts/_frontmatter.py` | Frontmatter reader for the YAML subset Obsidian uses, standard library only |
| `scripts/_sniff.py` | The survey, the draft schema and the report |
| `scripts/fixtures/vault/` | An invented vault the tests run against |
| `hooks/register.tsx` | The mod; registers nothing yet |
| `SPEC.md` | The living spec: vocabulary, surfaces, decisions and what is still open |
