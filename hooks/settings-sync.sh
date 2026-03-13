#!/usr/bin/env bash
# settings-sync.sh — strips JSONC comments from settings.local.jsonc → settings.local.json
# Run as a SessionStart hook.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$(dirname "$SCRIPT_DIR")"

SRC="$CLAUDE_DIR/settings.local.jsonc"
DST="$CLAUDE_DIR/settings.local.json"

# Source must exist
if [[ ! -f "$SRC" ]]; then
  exit 0
fi

# Strip // line comments and trailing commas before closing braces/brackets
stripped=$(sed \
  -e 's|//.*$||' \
  -e 's|,\s*\([}\]]\)|\1|g' \
  "$SRC")

# Check for keys in .json not present in .jsonc (warn only if .json already exists)
if [[ -f "$DST" ]]; then
  src_keys=$(echo "$stripped" | grep -o '"[^"]*"\s*:' | sed 's/\s*://' | sort -u)
  dst_keys=$(grep -o '"[^"]*"\s*:' "$DST" | sed 's/\s*://' | sort -u)

  missing=$(comm -13 <(echo "$src_keys") <(echo "$dst_keys"))

  if [[ -n "$missing" ]]; then
    echo "{\"type\":\"warning\",\"message\":\"settings-sync: the following keys exist in settings.local.json but not in settings.local.jsonc — they will be discarded: $missing\"}" >&2
  fi
fi

echo "$stripped" > "$DST"
