#!/usr/bin/env bash
# Stop hook: warn about uncommitted/unstaged changes when Claude finishes responding.
# Exits silently when the working tree is clean to avoid noise.

set -euo pipefail

# Only run if we're inside a git repo
if ! git -C "$PWD" rev-parse --git-dir > /dev/null 2>&1; then
  exit 0
fi

# Get porcelain status (empty = clean)
STATUS=$(git -C "$PWD" status --porcelain 2>/dev/null)

if [[ -z "$STATUS" ]]; then
  exit 0
fi

MODIFIED=$(echo "$STATUS" | grep -c '^ M\|^M \|^MM' 2>/dev/null || true)
STAGED=$(echo "$STATUS" | grep -c '^[MADRC]' 2>/dev/null || true)
UNTRACKED=$(echo "$STATUS" | grep -c '^??' 2>/dev/null || true)

PARTS=()
[[ $STAGED -gt 0 ]] && PARTS+=("$STAGED staged")
[[ $MODIFIED -gt 0 ]] && PARTS+=("$MODIFIED unstaged")
[[ $UNTRACKED -gt 0 ]] && PARTS+=("$UNTRACKED untracked")

SUMMARY=$(IFS=', '; echo "${PARTS[*]}")

echo "⚠️  Uncommitted changes in $PWD: $SUMMARY file(s). Consider committing before finishing."
