← [Wiki home](README.md)

# Glossary

Vocabulary specific to this config. General Claude Code terms (session, context window, tool use) aren't repeated here — see the [Claude Code docs](https://docs.anthropic.com/en/docs/claude-code) for those.

**Command skill** — A skill invoked explicitly with `/skill-name`. Frontmatter carries `disable-model-invocation: true`. See [Skills](reference/skills.md#command-skills-vs-role-skills).

**Role skill** — A skill Claude loads automatically on keyword or file-path match, never invoked directly. Frontmatter carries `user-invocable: false`. Formerly called a "knowledge skill" in older material.

**Model-invocable command skill** — A command skill Claude *can* also self-invoke (`disable-model-invocation: false`), used when one skill needs to call another (`pr-review-comment` calling `pr-review`) or as an automatic wrap-up (`help-whats_new`).

**Runic glyph** — The `𝚫𝚫𝚫`/`ƔƔƔ`/`𝛀𝛀𝛀` prefix on a command skill's description, signalling Haiku/Sonnet/Opus. Superseded the old Greek-letter convention (`ᚻᛕ`/`ᛇᚤ`/`ᛜᚹ`/`ᚨᛔ`). See [Skills](reference/skills.md#the-runic-glyph-convention).

**Model tier** — Haiku (fast, cheap, mechanical), Sonnet (balanced), Opus (thorough, expensive). Not every task needs the most capable tier.

**`when_to_use`** — The frontmatter field naming the concrete trigger moment for a skill, distinct from `description` (which says what it does). Prescribed by the canonical template at `library/configs/examples/skill-frontmatter.yaml`.

**CLOD TRIGGER** — The comment label in `skill-frontmatter.yaml` marking the `when_to_use` field — a reminder that this is the field the model actually pattern-matches against when deciding whether to load a role skill.

**Deterministic half** — A shell/Python script in `library/scripts/` that does a skill's fact-gathering with one correct answer (parsing git output, validating a schema), so the model's context is spent on judgement rather than orchestration. See [Architecture](architecture.md#the-deterministic-half-pattern).

**`paths:` glob** — A frontmatter field on some role skills (e.g. `role-linguist-svelte`) that auto-triggers the skill when a matching file is read or edited, independent of keyword matching.

**Fork context** (`context: fork`) — A skill frontmatter setting that runs the skill in a separate agent context rather than the main conversation — used when a skill's read footprint would otherwise bloat the main session (`project-analyse-critique`, `project-investigate-concept`).

**Agent** — An autonomous multi-step workflow (`agents/*.md`) Claude delegates to, running in its own context window with its own model. Distinct from a skill: skills tell Claude what to *know* or a fixed sequence to run; agents investigate and decide. See [Agents](reference/agents.md).

**Worktree `baseRef: fresh`** — The `settings.json` setting controlling what a new git worktree branches from: a fresh point, not whatever the main tree happens to be checked out to.

**JSONC source of truth** — The pattern where `settings.local.jsonc` (commented, human-edited) is stripped to `settings.local.json` (uncommented, what Claude Code actually reads) by the `settings-sync.sh` hook on every session start. See [Hooks](reference/hooks.md).

---
← [Wiki home](README.md) · [Skills](reference/skills.md) · [Architecture](architecture.md)
