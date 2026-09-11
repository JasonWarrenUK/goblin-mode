# State

Durable personal usage data, not project config. Files here are gitignored (see root `.gitignore`); this README and any schema docs are tracked so the shape survives even though the data doesn't.

## `cc-pain-points.json`

Logged friction with Claude Code itself (the CLI/harness, not any project it's working in): bugs hit, missing features, annoying limitations. Written by `hud-cc_pain`, read by `hud-cc_releases` to decide which changelog fixes actually clear the "you'd recognise this" bar before surfacing them.

Schema, one entry per pain point:

```json
{
  "id": "kebab-case-slug",
  "description": "free-text account of the friction, in Jason's own words/framing",
  "logged": "YYYY-MM-DD",
  "sourceSession": "optional short context, e.g. project or task at the time",
  "resolvedIn": null,
  "resolvedNoted": null
}
```

- `resolvedIn`: version tag once `hud-cc_releases` finds a matching fix and Jason confirms it addresses the entry. `null` while open.
- `resolvedNoted`: date the confirmation happened. `null` while open.

Resolved entries are kept, not deleted: a quiet log of what's been fixed over time. `hud-cc_releases` only matches against entries where `resolvedIn` is `null`.

## `commit-msg-log.jsonl`

One line per commit that passed through `hooks/commit-msg`, pass or reject, appended by the hook itself. Read by `prose-health.py` (via `hud-prose_health`) to report how often the gate fires.

```json
{"ts": "2026-09-11T09:14:02Z", "repo": "wyrd-tui", "result": "reject", "rules": "em dash|Oxford comma"}
```

`rules` is empty on a pass. Set `SLOP_NO_LOG=1` to skip logging (the health check's self-test does).

## `prose-metrics.json`

Per-day counts of house-rule breaches in Claude's own terminal output, keyed by `YYYY-MM-DD`, written by `prose-metrics.py --record`. Transcripts under `projects/` get pruned; this file keeps the trend. A day's row is replaced whenever a fresh scan of the transcripts covers at least as many words as the recorded row.

```json
{"2026-09-10": {"msgs": 284, "words": 9494, "emdash": 51, "endash": 0, "oxford": 3, "ize": 0, "amer_or": 0, "amer_er": 0, "amer_use": 0}}
```
