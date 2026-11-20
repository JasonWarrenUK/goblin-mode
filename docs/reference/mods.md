← [Wiki home](../README.md)

# Mods

Mods are plugins whose code runs inside Claude Code: TypeScript event handlers the engine calls on a tool call, a prompt, a turn or a part of the interface being drawn. They can draw panes, bands and toasts and redraw what Claude Code draws itself, which no settings hook, skill or MCP server can. They need Claude Code 2.1.287 or later, and they draw only in the terminal and the desktop Code tab; in a cloud session or `claude -p` the hooks run and nothing draws. Anthropic's reference: [mods overview](https://code.claude.com/docs/en/plugins/mods/overview).

This config's mods live under `marketplace/<name>/` and are served from the repo's own marketplace (`.claude-plugin/marketplace.json`). Every plugin there is hand-maintained: the directory is the source of truth, nothing generates it. Since the installed copy comes from the GitHub clone under `plugins/marketplaces/goblin-mode/`, an edit is live only after it is pushed and the marketplace updates; to run the working tree instead, start a session with `claude --plugin-dir ~/.claude/marketplace/<name>`.

| Mod | What it does | Draws |
|---|---|---|
| [`goblin-jester`](../../marketplace/goblin-jester/README.md) | Goblin-mode's face in the terminal: a goblin in the band that reacts to the session, the hint line in its voice, a mask over every question, frames by model tier, a day cycle and the project theme's colours. Pure chrome; it changes nothing Claude does. | Band, `TurnDuration`, `PromptHint`, `AskUserQuestion` |
| [`goblin-seneschal`](../../marketplace/goblin-seneschal/README.md) | `/log-grievance` logs a grievance with Claude Code itself into `library/state/grievances.json` without a turn, the repo, branch and last failed tool pre-filled; `/muster-underlings` lists every underling (session) on the machine from a shared heartbeat and sends one a message. Ships six skills beside the mod. | Two panes, toasts |
| [`goblin-scout`](../../marketplace/goblin-scout/README.md) | `/scout-waypoints` opens the roadbook's ready waypoints in a pane with the trails in play and milestone progress by release tier; a digit picks, `c` starts a trail after asking which scout, `r` refreshes, `/scout-waypoints` again closes. The mod ships inside the goblin-scout plugin beside its skills and CLI, so one install gives both. | One pane, toasts |
| [`goblin-warband`](../../marketplace/goblin-warband/README.md) | `/show-slate` opens the slate for a raid of several sessions on one repository: raiders with liveness, who holds the dibs on which shared resource, dibs called, the tribute owed with complete commands and, once a PR is recorded, a PRs group listing only the PRs where the user moves next; `g` grants, `d` marks paid, `x` releases, `o` opens the raid's local spoils page. Thirteen more commands act as the person (`/start-raid`, `/grant-dibs`, `/pay-tribute` and the rest). The mod also registers the `warband_*` tools, adds the raid section to each session's system prompt, marks the chief's messages verified by socket and answers a project hook's `ask` with `allow` under held dibs. Ships beside the ledger CLI, three command hooks and six skills. | One pane, toasts |

## How a mod is laid out

```
marketplace/<name>/
	.claude-plugin/plugin.json   manifest: name, version, userConfig, "types"
	hooks/hooks.json             {"modules": ["./register.tsx"]}
	hooks/register.tsx           the hooks module: export const register: Register
	hooks/*.ts, *.tsx            modules it imports; a Client surface module for animation
	hooks/*.test.ts(x)           tests `claude plugin test` runs without a session
	types/index.d.ts             the `$.state` contract, declared per value
	README.md                    install, what it draws, options, files
```

The engine writes its own declarations beside the manifest (`.claude-plugin/types/`) when a session loads the mod from a folder; that folder is gitignored.

## Checking a mod

| Check | Command |
|---|---|
| The manifest, and what the module hooks and calls | `claude plugin validate marketplace/<name> --strict` |
| Its tests, in an environment like the one hooks run in (no fs, no network, no process) | `claude plugin test marketplace/<name>` |
| Types, once a session has laid the engine's declarations | `tsc -p marketplace/<name>` |

Bare `bun test` cannot run a mod's tests: `claude-code/testing` comes from the plugin runner, so bun fails with `Cannot find module` before a single test loads. That failure says nothing about the mod; use `claude plugin test`.

Two rules the validator holds a module to that are easy to trip: `$` may be passed only to a function declared at the top of the file, never to a closure made inside `register`; and a `Client` element's `module` is a string literal path.

## Conventions

- One `userConfig` switch per mod that turns all of it off, so a demo to someone serious is one toggle.
- Everything rendered takes its colours from the project theme per [CLAUDE.md §7.5](../../CLAUDE.md), through the mod's own resolution of `.claude/themes/` with the `clod` family as the fallback.
- State a drawing depends on lives in `$.state`, declared in the contract, never in a module variable: a hot reload loses those.
- A mod that publishes something other mods read (goblin-jester's `frame` and `palette`) declares it in its contract; a reader lists the mod under `dependencies` and reads the typed reference.

---
← [Wiki home](../README.md) · [Hooks](hooks.md) · [Configuration](configuration.md)
