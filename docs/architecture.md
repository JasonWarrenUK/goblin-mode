← [Wiki home](README.md)

# Architecture

How the layers of this config fit together, what each costs to load, and one pattern worth understanding on its own: pairing a skill with a deterministic script.

## The layers

```text
You type something in Claude Code
        │
        ├─ Keywords or file paths match? ──→ Role skill loads automatically
        │
        ├─ You type /skill-name? ──→ Command skill runs its defined workflow
        │
        ├─ Skill or Claude spawns an agent? ──→ Agent works autonomously, own context window
        │
        └─ Git/session event fires? ──→ Hooks run checks and injections

Meanwhile, CLAUDE.md shapes every response throughout.
```

Each layer has a different trigger and a different cost:

| Layer | Loads | Typical size | Idle cost |
|---|---|---|---|
| [`CLAUDE.md`](../CLAUDE.md) | Every session | ~500 lines | Always present |
| Output style | Every session (when active) | 20–40 lines | Always present |
| Role skill | Description at start; body on trigger | 50–300 lines | Description only |
| Command skill | On slash-command invoke | 10–100 lines | Zero until invoked |
| Agent description | Every session | 5–10 lines (frontmatter only) | Minimal |
| Agent body | On delegation | Full instruction set | Zero until spawned |

`CLAUDE.md` is the one layer that's always fully loaded, which is why [CLAUDE.md §11](../CLAUDE.md) and the general house style favour brevity there over comprehensiveness — anything that only matters sometimes belongs in a skill instead.

## Context-window cost

Role-skill descriptions are the ones to watch: cheap individually, but they all load at session start and *several can trigger in the same turn* if a message touches multiple domains (e.g. editing a `.svelte` file that's also a test file triggers both `role-linguist-svelte` and `role-expert-testing_obsessive`). `skillListingBudgetFraction` in [`settings.json`](reference/configuration.md) caps how much of the context window the startup listing can occupy — currently 3%.

**Practical guidance if extending this setup:**
- Start with command skills — free until invoked.
- Keep `CLAUDE.md` lean — it loads every session, unconditionally.
- Create a role skill only when Claude's default advice is genuinely wrong for your stack, not just generic.
- Don't duplicate — if it's in `CLAUDE.md`, don't restate it in a skill.

## The deterministic-half pattern

Several command skills pair a **shell/Python script** (in `library/scripts/`) with a **model-driven skill body**. The script does the part of the job that has one correct answer — parsing `git status`, diffing a lockfile against the registry, validating a JSON schema — and the model's job is judgement on the script's structured output, not re-deriving those facts by orchestrating a chain of exploratory tool calls itself.

```
git-branch-review skill  ──runs──→  branch-facts.sh  ──emits──→  structured JSON
                                                                       │
                                                          model reads exact numbers,
                                                          judges readiness — doesn't
                                                          re-derive them from raw git output
```

Concrete pairs: `branch-facts.sh` → `git-branch-review`, `deps-dump.sh` → `project-investigate-deps`, `git-doc-history.sh` → the `doc-*` update skills, `roadmap.py` → the whole `roadmap-*` family, `config_permit.py` → `config-permit`, `validate_audit_findings.py` → `artefact-audit`. Full list at [Library → scripts](reference/library.md#scripts--the-deterministic-halves).

The benefit compounds: a script is testable in isolation (`test_roadmap.py` exists precisely because `roadmap.py` is complex enough to warrant it), its output is the same for the same input (so regenerated artefacts diff cleanly instead of drifting on each run), and the model spends its reasoning budget on the part that actually needs judgement.

## The two agent loops

[Agents](reference/agents.md) form a session loop (orchestrate → implement → ship → close → repeat) and a shipping loop (readiness check fanning out to test-gap, task-sync, and doc-staleness checks). Full diagrams on the [agents reference page](reference/agents.md#the-two-loops).

## Model tiers

Command skills specify one of three tiers via the [runic glyph convention](reference/skills.md#the-runic-glyph-convention): Haiku for mechanical work, Sonnet for balanced reasoning, Opus for work that needs to hold a lot of context or make a judgement call. The session default (in [`settings.json`](reference/configuration.md)) is currently Fable, overridden per-invocation by whichever skill or agent is running.

## Design principles this repo follows

- **Friction-driven, not architecture-driven.** Every skill, hook, and agent traces to a specific problem that came up during real work — see [Design history](design-history/agent-workflow-design.md) for a worked example of a whole agent generation proposed, prioritised, and shipped this way.
- **Weakness-aware.** `role-expert-testing_obsessive` exists because testing discipline doesn't come naturally; the `stop-uncommitted-check.sh` hook exists because remembering to commit doesn't either. The config compensates for known gaps rather than pretending they don't exist.
- **Context window discipline.** Every layer above is deliberately costed. If you're extending this setup, that discipline is the part worth keeping even if nothing else transfers.

---
← [Wiki home](README.md) · [Skills](reference/skills.md) · [Agents](reference/agents.md) · [Glossary](glossary.md)
