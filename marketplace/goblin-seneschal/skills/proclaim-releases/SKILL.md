---
name: "Proclaim Releases"
description: "Summarise Claude Code's own CHANGELOG.md, filtered and grouped for what actually matters to the user"
when_to_use: "When the user asks what's new in Claude Code, whether to update or what changed since a given point."
model: sonnet
effort: medium
metadata:
  glyph: ᛊ
  family: hud
  goblin-spinner: reading the decrees|filtering the noise|proclaiming
disable-model-invocation: false # read-only viewer, no gate needed
disallowed-tools: ["Edit", "Write", "NotebookEdit"]
allowed-tools: ["Bash(curl:*)", "Bash(awk:*)", "Bash(grep:*)", "Bash(npm view:*)", "Bash(claude --version)", "Read", "AskUserQuestion", "Skill(goblin-seneschal:overhear-grievance)"]
arguments: ["number", "unit"]
argument-hint: "[<n> <d|w|m|v>] e.g. \"1 w\", \"3 d\", \"10 v\" (default: since your installed version)"
---

# Proclaim Releases

Claude Code's real `CHANGELOG.md` lives at the root of `anthropics/claude-code` on GitHub, one flat bullet list per version, no subsections. It is long (thousands of lines) and mostly noise for any one person: platforms they don't run, providers they don't use, admin features for plans they aren't on. This skill fetches it, slices the requested range and reports only what earns a look, grouped by subsystem.

## Step 1: Resolve the range

Two positional args, `<number> <unit>`. Unit is one of:

| Unit | Meaning |
|---|---|
| `d` | days |
| `w` | weeks |
| `m` | months |
| `v` | versions back from latest |

Examples: `1 w` (last week), `3 d` (last three days), `10 v` (last ten versions).

**No arguments**: default to `claude --version` (installed version) as the floor; range is `installed..latest`. This is the actual question most of the time: "what have I missed."

**`v` unit**: that many versions back from latest, no date lookup needed.

**`d`/`w`/`m` units**: version headings (`## 2.1.238`) carry no dates, so resolve via the npm publish-time map:

```bash
npm view @anthropic-ai/claude-code time --json
```

Take that map's own most recent timestamp as "now" (no other clock is available to the script), compute `now - (number × unit)`, and use the first version published on or after that point as the floor.

If the npm time map and the changelog's version set diverge (a version in one but not the other), say so once and fall back to the nearest available version rather than guessing.

A single token with no unit ("1w", "3d") or a unit spelled out ("week", "days") should still resolve sensibly, don't reject on formatting when the intent is obvious; but the canonical form given to the user is always the two-token one above.

## Step 2: Fetch and slice, never load the whole file

```bash
curl -s https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md -o /tmp/cc-changelog.md
```

Use the session scratchpad, not `/tmp`, for the actual output file. Then slice with `awk` on `^## ` boundaries to pull only the resolved range into a second file. Read that slice, not the source file: at ~5,700 lines the full changelog blows the context budget for zero benefit, and pre-summarising it with WebFetch is worse, since WebFetch runs content through a small model that will chew the exact bullets this skill needs to judge verbatim.

## Step 3: Split every bullet into capability or fix

These two kinds clear the relevance bar in different ways and get filtered separately. A bullet is a **fix** if its changelog wording is fundamentally "X was broken, now it isn't" (the file's own `Fixed`/`Hardened` prefixes, and any `Changed`/`Improved` bullet that's really a bug being quietly corrected). Everything else (genuinely new capability, a behaviour change you'd choose to use, a setting worth knowing exists) is a **capability**.

### Capabilities: filter by "would the user recognise the use, unprompted"

Source the relevance signal live from the user's own setup; never hardcode a stack list that will drift:

- The user's CLAUDE.md files and any profile they reference (already in context every session): their languages, runtimes, frameworks, editor and operating system.
- The skills and plugins they keep (`~/.claude/skills/`, the project's `.claude/skills/`, `~/.claude/plugins/installed_plugins.json`): someone who authors skills or plugins cares about `SKILL.md` parsing, `claude plugin validate`, marketplaces and frontmatter even if they wouldn't describe themselves as "into plugin infrastructure."
- This session's own environment: the features demonstrably in use here (worktrees, output styles, hooks, MCP servers, cross-session `SendMessage`/`ListAgents`, subagent forking), not ones inferred from the changelog talking about them.

**Drop on sight:** anything for a platform, provider or deployment the user's setup shows no sign of. That is usually an operating system other than theirs (Windows/WSL, Cygwin, PowerShell on a Mac), a model provider they don't use (Bedrock, Vertex AI, Foundry, apps gateway internals), self-hosted-runner fleet operations, Team/Enterprise admin policy and managed-settings schema when nothing shows they are on such a plan, mTLS/cert rotation for gateway deployments and items for an IDE their config never mentions.

**Keep even when small:** anything touching a subsystem this session shows in active use. For most users of this plugin that means skills/plugins/marketplaces, subagents/Agent tool semantics, git/worktree behaviour, terminal/keybinding UX, cross-session messaging, MCP client-side behaviour and model/effort selection; check before assuming any one of them.

A capability only earns its place if the bullet is self-evidently actionable as written: the reader gets from the description to "oh, I'd use that" without help. If it takes an explained "why this matters" clause bolted on to justify itself, it isn't self-evident: cut it, don't prop it up with an explanation. Prefer three sharp keeps over five that need footnotes.

### Fixes: filter by logged grievances only, not by subsystem match

The grievances file is `${user_config.grievances_file}` (a leading `~/` is the user's home; a value that is neither absolute nor under `~/` means the default, `~/.claude/library/state/grievances.json`, as the mod reads it). A fix bullet earns a place only if it plausibly resolves an entry there with `resolvedIn: null`. Subsystem relevance (worktrees, skills, MCP) is not sufficient on its own: a fix for a bug the user never hit is not news, however on-brand the subsystem is. Two narrow exceptions that surface regardless of the grievances: a fix for a genuine security/data-loss issue (framed as risk removed, not bug re-lived) and a fix explicitly requested this same run ("did they fix X" prompted the check).

If the grievances file is missing, say so in one line and report capabilities and the two exceptions only; never create it here. When `~/.claude/library/state/cc-pain-points.json` exists in its place, the plugin kept its grievances there before 1.0.0 and has not carried them over (its mod is off): read the open entries from that file instead, and say once that it should be carried over.

Read the open entries and the fix bullets from this range, and match by meaning: the grievance's description and the changelog's eventual phrasing will rarely share vocabulary (worktree isolation blocking a safe git command vs. "worktree-isolated sessions... running destructive git commands" describe the same friction from opposite ends). Judge the underlying cause, not keyword overlap.

For each candidate match, do not resolve it silently. Ask first:

> `AskUserQuestion`: "This looks like it might fix a logged grievance: '{{entry.description}}'. {{version}}: {{bullet text}}. Does this address it?"

If confirmed, call `Skill(goblin-seneschal:overhear-grievance)` with an instruction to mark that entry's `resolvedIn`/`resolvedNoted` (do not write to the JSON directly: this skill stays read-only; the write is `overhear-grievance`'s job). If not confirmed, leave the entry open and don't surface the bullet as a "this is fixed now" item.

## Step 4: Group thematically and report

Group by subsystem, not by the changelog's own `Added`/`Fixed`/`Improved`/`Changed` prefixes: those are change types, not themes, and grouping on them just yields a shorter copy of the same document. Useful groups tend to be: skills & plugins, agents & subagents, git & worktrees, MCP, terminal & rendering, models & effort, cross-session messaging. Cap at ~5 groups, ~5 items per group, drop empty groups silently. If the filtered set is genuinely small (a quiet week), say so in one line rather than padding.

Each item: one line, plain language, what changed, in the reader's own vocabulary where the changelog's wording buries the point. Name the version it landed in. State the change directly; don't append a justifying clause explaining why it matters: if it needs that explanation to land, it belongs in the drop pile, not on the page with a crutch attached.

If items were dropped for being out of scope, don't list them individually; a single closing line ("N other changes this range, all Windows/Enterprise/Bedrock: skipped") is enough so the omission reads as deliberate rather than incomplete. Fixes dropped for having no matching open grievance don't need their own tally; they were never candidates.

## Red flags

**Never** paste the raw changelog slice back as the answer, that isn't a summary. **Never** run this through WebFetch. **Never** report on the full file when a range was requested; scope discipline is the entire value of this skill over just reading the changelog directly. **Never** surface a fix bullet on subsystem relevance alone; it needs a matched, confirmed grievance (or the security/data-loss exception). **Never** write to the grievances file directly; that's `overhear-grievance`'s job, called only after explicit confirmation.

<raw-arguments value="$ARGUMENTS" />
