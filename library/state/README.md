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

Resolved entries are kept, not deleted — a quiet log of what's been fixed over time. `hud-cc_releases` only matches against entries where `resolvedIn` is `null`.
