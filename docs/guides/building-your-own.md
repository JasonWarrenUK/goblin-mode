← [Wiki home](../README.md)

# Building Your Own

This setup is specific to one developer's workflow and brain — the ADHD-shaped executive-function scaffolding in [CLAUDE.md](../../CLAUDE.md) won't fit everyone. What's transferable is the *process*, not the specifics. This guide is that process.

## Respect the context window

Every customisation competes for space in Claude's context window. Space spent on configuration is space unavailable for your actual code and conversation. See [Architecture → Context-window cost](../architecture.md#context-window-cost) for the concrete numbers this repo works within.

## Start with friction, not speculation

Don't configure ahead of a problem. Wait until something annoys you more than once, then fix it.

**Exercise:** over your next few sessions, keep a list of moments where Claude does something you immediately correct. Each repeated correction is a candidate for `CLAUDE.md`. Each repeated multi-step instruction is a candidate for a command skill.

## Encode decisions, not preferences

"I prefer tabs" is cosmetic. "Use tabs because the team standard is tabs" prevents a real problem. Configuration noise accumulates fast; each rule should earn its place.

**Exercise:** for each rule you want to add, ask "what goes wrong if Claude ignores this?" If the answer is "nothing, I just prefer it," think twice before adding it.

## Layer your configuration

Three layers, most-general to most-specific:

1. **Global** (`CLAUDE.md` at `~/.claude/`) — true for every project.
2. **Project-level** (`project/CLAUDE.md`) — overrides global for one repository.
3. **Subsystem-level** (`project/frontend/CLAUDE.md`) — overrides project for one area.

Start global. Add project layers only when a project genuinely diverges — not pre-emptively.

## Use model tiers deliberately

This repo's tiers ([full detail](../reference/skills.md#the-runic-glyph-convention)):

- **Haiku** — fast, cheap: commit messages, permission grants, status reports.
- **Sonnet** — balanced: ADRs, doc updates, branch assessment.
- **Opus** — thorough: architectural critique, implementation planning, roadmaps.

Not every task needs your most expensive model. Matching tier to task is a small habit with a real cost payoff at scale.

## Skills, agents, or hooks?

The three mechanisms solve different problems — picking the wrong one either limits what Claude can do or over-engineers something simple.

| If the problem is… | Reach for… |
|---|---|
| Claude's default advice is generically wrong for your stack | A role skill (knowledge, loads automatically) |
| You keep typing the same multi-step instruction | A command skill (workflow, invoked explicitly) |
| A workflow needs investigation across multiple steps, not a fixed template | An agent (autonomous, own context window) |
| A check keeps getting skipped even though you know you should run it | A hook (automatic, tied to a git/session event) |

Full comparison: [Skills vs Agents](../reference/skills.md#skills-vs-agents).

## Version control everything

The whole directory is a git repository. That gets you: reversible configuration changes, a commit history explaining *when* and *why* a rule was added, and a setup that survives moving to a new machine via one `git clone`.

## Let it grow organically

A reasonable progression, not a target to rush toward:

1. **First session:** `CLAUDE.md` with spelling, tone, and code-style preferences.
2. **First month:** your first role skill, when Claude gives generic advice in an area you need opinionated guidance on.
3. **When you notice repetition:** your first command skill, extracted from a workflow you've typed out three times.
4. **When workflows get complex:** your first agent, for a multi-step process you keep doing inconsistently.
5. **When discipline slips:** your first hook, for the check you know you should run but don't.

The goal isn't a comprehensive system. It's a system that solves *your* actual problems, one friction point at a time — this repo's own [design history](../design-history/agent-workflow-design.md) is a worked example of exactly that progression.

---
← [Wiki home](../README.md) · [Architecture](../architecture.md)
