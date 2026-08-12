---
name: "Skill: Conventions"
description: "{{ 𝚫𝚫𝚫 }} Jason's placement and model-tag conventions for creating or editing skills"
when_to_use: "Before creating or editing a skill — checking where it should live and how to tag its model in frontmatter."
model: haiku
effort: low
disable-model-invocation: true
---

# Skill creation conventions

- All skills live in `~/.claude/skills/` as `SKILL.md` files.
- Command skills (invoked explicitly) get `disable-model-invocation: true`; knowledge skills (always available for reference, never directly invoked) get `user-invocable: false`.
- Exception: a command skill may set `disable-model-invocation: false` when its `when_to_use` describes a moment Claude recognises before the user does (stale PR description, post-merge status drift, "add this to the roadmap" phrasing) **and** the skill contains its own approval gate before anything irreversible. The gate is the safety net; without one, keep it `true`.

## Where to create a skill

1. Always create in the project-local `.claude/skills/` directory unless explicitly told to create it globally.
2. Check for naming conflicts with personal-level skills (`~/.claude/skills/`) — personal scope shadows project scope.
3. Use the new frontmatter convention below when creating or editing skills; recognise the old convention when reading existing skills.

## Model-tag convention (new)

Runic letters in the YAML frontmatter `description` field signal which model the command uses:

| Runes | Model |
|---|---|
| `𝚫𝚫𝚫` | haiku |
| `ƔƔƔ` | sonnet |
| `𝛀𝛀𝛀` | opus |

Format: `description: "{{ ƔƔƔ }} Command description here"`

## Model-tag convention (old — recognise, don't write)

| Runes | Model |
|---|---|
| `ᚻᛕ` | haiku |
| `ᛇᚤ` | sonnet |
| `ᛜᚹ` | opus |
| `ᚨᛔ` | fable |

Format: `description: "{{ ᛇᚤ }} Command description here"`
