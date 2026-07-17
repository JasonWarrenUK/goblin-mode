← [Wiki home](../README.md)

# Skills

Skills are the largest single category in this repo — 45 of them, living at `skills/<name>/SKILL.md`. They split into two families with different triggers, different frontmatter shapes, and different jobs.

For the full generated list with descriptions, see **[skills/README.md](../../skills/README.md)** — that file is regenerated from frontmatter (see [below](#regenerating-the-index)) and this page deliberately doesn't duplicate its rows.

## Command skills vs. role skills

| | Command skills (27) | Role skills (15) | Model-invocable command skills (3) |
|---|---|---|---|
| **Invoked by** | `/skill-name` — explicit, manual | Claude's judgement, on keywords or file paths | Either — same shape as command skills but Claude can also self-invoke |
| **Frontmatter flag** | `disable-model-invocation: true` | `user-invocable: false` | `disable-model-invocation: false`, with a comment explaining why |
| **Naming** | `Group: Action` Title Case (`"PR: Create"`, `"Roadmap: Maintain"`) | Mixed — kebab-case (`svelte-ninja`), Title Case (`Data Ontologist`), or the `role-<family>-<name>` directory prefix | Same as command skills |
| **Purpose** | Repeatable workflows you consciously reach for | Domain knowledge that should colour every relevant response, whether or not you thought to ask | A workflow another skill needs to call into |
| **Description prefix** | Runic model glyph (see below) | None — no `model:` field to signal | Runic glyph |

The three model-invocable exceptions are `help-whats_new` (useful as an automatic wrap-up), `pr-review` (`disable-model-invocation: false` specifically so `pr-review-comment` can call it internally), and `roadmap-create-interview` (no flag at all, so it defaults to model-invocable).

## The runic glyph convention

Every command skill's description opens with a glyph signalling its model tier, matching the `model:` frontmatter field:

| Glyph | Model | Best for |
|---|---|---|
| `𝚫𝚫𝚫` | Haiku | Fast, mechanical: commit messages, permission grants, status reports |
| `ƔƔƔ` | Sonnet | Balanced: ADRs, doc updates, branch review |
| `𝛀𝛀𝛀` | Opus | Thorough: architectural critique, roadmap creation, planning |

This superseded an older Greek-letter convention (`ᚻᛕ`/`ᛇᚤ`/`ᛜᚹ`/`ᚨᛔ` for haiku/sonnet/opus/fable) — see [CLAUDE.md §4.1.2](../../CLAUDE.md) for the old convention, kept there only for recognising it in older material. Zero skills use it any more.

## Role skill families

The 15 role skills sort into five directory-prefix families, each with a distinct kind of expertise:

| Prefix | Families | Example |
|---|---|---|
| `role-approach-*` | How to structure implementation work | `role-approach-stud` — walking-skeleton scaffolding before real logic |
| `role-expert-*` | Deep domain knowledge | API design, data modelling, debugging, frontend styling, testing |
| `role-linguist-*` | Language/library-specific patterns | Cypher, OpenTUI, Svelte |
| `role-manager-*` | Process ownership | Git workflow |
| `role-viewpoint-*` | A deliberate lens to apply | Ethics, scope discipline, user empathy, writing style |

Most `role-expert-*` and `role-linguist-*` skills also carry a `paths:` glob (e.g. `**/*.svelte`) that auto-triggers them when a matching file is touched, on top of keyword triggering.

## `when_to_use` vs `description`

Every skill's frontmatter carries both a `description` (what it does) and a `when_to_use` (the concrete trigger moment) — the canonical shape is `library/configs/examples/skill-frontmatter.yaml`. Splitting the two serves both readers: `description` answers "what is this" for a human scanning the index; `when_to_use` gives the model (and a human deciding whether to invoke a command skill) a concrete trigger to pattern-match against, in the same spirit as the `argument-hint` field already used across command skills.

> [!NOTE]
> Until this sweep, only 3 of 45 skills actually populated `when_to_use` despite the template prescribing it. The other 42 either crammed WHEN-information into `description`, relied on a `paths:` glob doing the work implicitly, or had no WHEN signal at all. All 45 now carry both fields.

## Regenerating the index

`skills/README.md` is generated, not hand-written — its own header says so. Run this after adding, renaming, or re-describing any skill:

```bash
python3 ~/.claude/library/scripts/gen-skills-index.py
```

Add `--check` to verify the index is current without writing (exits 1 if stale — useful in a pre-commit hook or CI). It reads every `SKILL.md`'s frontmatter, classifies each into command / model-invocable / role by its invocation flags, and rebuilds all three tables — so descriptions, models, and counts can't silently drift the way they had before this sweep (the index previously showed eight role skills with blank description cells).

## Skills vs Agents

| | Command skills | Role skills | [Agents](agents.md) |
|---|---|---|---|
| **Triggered by** | Slash command (explicit) | Keywords / paths (automatic) | Claude's judgement (delegated) |
| **Complexity** | Structured steps | Static reference | Dynamic investigation |
| **Context cost** | Full file on invoke | Description at start; full file on trigger | Description only (runs as sub-process) |
| **User action** | You invoke it | None — loads silently | Claude delegates to it |
| **Memory** | None | None | Can persist across sessions |

Knowledge skill: create one when Claude's default advice is generically wrong for your stack (Svelte 5 runes vs. the Svelte 4 patterns Claude defaults to, say). Command skill: create one when you've given Claude the same multi-step instruction more than twice. Agent: create one when the workflow needs autonomous investigation, not just a fixed template.

---
← [Wiki home](../README.md) · [Agents](agents.md) · [Library](library.md) · [Glossary](../glossary.md)
