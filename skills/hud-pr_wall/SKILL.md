---
name: "HUD: PR Wall"
description: "Show every open PR that involves you, bucketed by what each one is waiting on"
when_to_use: "When the user asks what PRs are open, what's awaiting review, what needs their review, where their PRs stand, or wants a cross-project pull-request overview — also the natural first step before picking a target for pr-handle_review or pr-land."
model: haiku
effort: low
metadata:
  glyph: ᚺ
  family: hud
disable-model-invocation: false # "where do my PRs stand?" should load this; it's read-only
allowed-tools: ["Bash(~/.claude/library/scripts/pr-wall.sh:*)"]
arguments: ["scope", "root"]
argument-hint: "[this|all] [code root, default ~/code]"
---

# HUD: PR Wall

One view of every open PR you're involved in, bucketed by whose move it is. Read-only: this skill queries and formats; it never merges, comments or closes anything.

## Step 1 — Gather

```bash
"$HOME"/.claude/library/scripts/pr-wall.sh $scope $root
```

Pass the arguments through verbatim (`$scope` empty means the script auto-detects: `this` inside a GitHub repo, `all` otherwise). The script does everything in one call — two GraphQL searches plus a local-clone scan — and returns one JSON object with four buckets. Do not supplement it with extra `gh` calls; if a bucket looks wrong, say so rather than re-deriving it.

## Step 2 — Render

Four sections, in this order (whose-move-is-it, most actionable first). Omit empty sections; if everything is empty, one line: nothing open involves you.

```markdown
## 🟢 Approved — ready to land ({n})
- **repo#123** — title · updated {relative} · clone: {localPath or "not cloned"}

## 🟠 Changes requested — your move ({n})
...

## ⚪ Awaiting review — reviewer's move ({n})
...

## 🔵 Your review requested ({n})
...
```

- `mineApproved` → **Approved**: suggest `pr-land` for any with a local clone.
- `mineChangesRequested` → **Changes requested**: suggest `pr-handle_review`.
- `mineAwaiting` → **Awaiting review**: nothing to do but chase; note any PR untouched for over a week.
- `reviewRequested` → **Your review requested**: suggest `pr-review` (posted) or `pr-review-dry_run` (read-only).
- Mark drafts with `(draft)` after the title. Keep each PR to one line.

<raw-arguments value="$ARGUMENTS" />
