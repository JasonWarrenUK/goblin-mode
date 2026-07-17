← [Wiki home](../README.md)

# Configuration

Three layers govern behaviour, in ascending order of specificity: [`CLAUDE.md`](../../CLAUDE.md) (what to *do*), `settings.json` (what's *allowed*, and harness options), and skill/agent frontmatter (per-invocation overrides). This page covers `settings.json`; for `CLAUDE.md`'s role see [Architecture](../architecture.md).

## `settings.json` vs `settings.local.jsonc`

There are two permission files, deliberately:

- **`settings.json`** — the file Claude Code actually reads. Committed, shared, the one described below.
- **`settings.local.jsonc`** — a JSONC (JSON-with-comments) *source of truth* for `settings.local.json`, which Claude Code also reads but which isn't valid JSON if hand-annotated. The [`settings-sync.sh`](hooks.md) hook strips comments and trailing commas from the `.jsonc` and writes `.json` at every session start. **Edit the `.jsonc`, never the `.json` directly** — it gets overwritten.

## Model

```json
"model": "fable"
```

The default session model is **Fable 5**, not Sonnet or Opus. Skills and agents override this per-invocation via their own `model:` frontmatter field (see [Skills](skills.md#the-runic-glyph-convention)) — the session default only applies to the main conversation loop.

## Permissions

```json
"permissions": { "allow": [...60 rules...], "deny": [], "ask": [], "defaultMode": "auto" }
```

`defaultMode: auto` means tool calls not covered by an explicit rule prompt for confirmation rather than blocking outright. The 60 `allow` rules pre-approve routine read operations (`cat`, `grep`, `find`, `git log/status/diff/show`, `gh pr/issue view`), common git write operations (`add`, `commit`, `push`, `fetch`), and a handful of project-specific one-offs. Use the `config-permit` skill to add a rule rather than hand-editing this array — see [Skills](skills.md).

## Worktree

```json
"worktree": { "baseRef": "fresh" }
```

Controls what a new worktree branches from — `fresh` rather than the currently checked-out branch, so worktrees don't inadvertently carry uncommitted context from wherever the main tree happened to be. See [CLAUDE.md §8.7](../../CLAUDE.md) for worktree workflow rules.

## Status line

```json
"statusLine": { "type": "command", "command": "bunx -y ccstatusline@latest", ... }
```

Delegates to the [ccstatusline](https://www.npmjs.com/package/ccstatusline) package, refreshed via the two `PreToolUse`/`UserPromptSubmit` hooks documented in [Hooks](hooks.md).

## Enabled plugins

`enabledPlugins` lists installed marketplace plugins and whether each is active. Currently on: `frontend-design`, `feature-dev`, `typescript-lsp`, `plugin-dev`, `hookify`, `claude-md-management`, `claude-code-setup`, `playwright`, `context7`, `visual-explainer`, `understand-anything`, `skill-creator`, `playground`, `vhs-recorder`, `copywriter`. Off: `code-simplifier`, `pyright-lsp`, `discord`.

`extraKnownMarketplaces` registers three non-default marketplace sources (`visual-explainer-marketplace`, `understand-anything`, `foundry`) that some of the above plugins are installed from.

## Personality knobs

A few settings exist purely for tone, matching the [goblin-mode](../../README.md) identity:

- `spinnerVerbs` — replaces the default "thinking…" spinner text with a 20-item rotation (`sKiTtErInG`, `hOaRdInG`, `pIlFeRiNg`, …) in alternating-caps.
- `skillListingBudgetFraction: 0.03` — caps how much of the context window skill descriptions can occupy at session start (3%), keeping the [context-window discipline](../architecture.md#context-window-cost) actually enforced rather than aspirational.

## Everything else

`syntaxHighlightingDisabled`, `alwaysThinkingEnabled`, `autoUpdatesChannel`, `tui`, `showThinkingSummaries`, `theme`, `verbose`, `preferredNotifChannel`, `autoCompactEnabled`, `inputNeededNotifEnabled`, `agentPushNotifEnabled`, and the `skip*PermissionPrompt`/`skipWorkflowUsageWarning` flags are standard Claude Code harness options — see the [Claude Code docs](https://docs.anthropic.com/en/docs/claude-code) for current semantics rather than trusting this page to stay in sync with them.

---
← [Wiki home](../README.md) · [Hooks](hooks.md) · [Skills](skills.md) · [Architecture](../architecture.md)
