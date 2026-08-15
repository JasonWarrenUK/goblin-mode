#!/usr/bin/env bash
# settings-backup.sh — snapshot ~/.claude/settings.json before it can be lost.
#
# Two callers, wired in settings.json itself:
#   PreToolUse (matcher: Edit|Write, no `if` narrowing — this script reads
#     stdin itself and no-ops for any file that isn't settings.json) —
#     always snapshot the pre-edit state before the change lands, so a bad
#     edit is recoverable.
#   SessionStart — snapshot only `--if-changed`: settings.json got silently
#     truncated once already by something that wasn't a normal Edit/Write
#     call, so this catches drift from outside Claude's own tool calls too.
#
# Backups land in ~/.claude/backups/settings.json.backup.<epoch-ms>, matching
# the naming convention that directory already uses for .claude.json backups.
# Rotates to the most recent 20 snapshots.

set -euo pipefail

CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SRC="$CLAUDE_DIR/settings.json"
BACKUP_DIR="$CLAUDE_DIR/backups"
KEEP=20
MODE="${1:-}"

# When invoked as a PreToolUse hook (no --if-changed arg), stdin carries the
# tool-call JSON. Read it and no-op for anything that isn't settings.json,
# so this stays cheap and silent on the happy path for every other edit.
if [[ "$MODE" != "--if-changed" ]] && [[ ! -t 0 ]]; then
  HOOK_INPUT=$(cat)
  TARGET=$(python3 -c "
import json, sys
try:
    d = json.loads(sys.argv[1])
    print(d.get('tool_input', {}).get('file_path', ''))
except Exception:
    print('')
" "$HOOK_INPUT" 2>/dev/null || true)
  case "$TARGET" in
    *settings.local.json) exit 0 ;;
    *settings.json) ;;
    *) exit 0 ;;
  esac
fi

# Nothing to back up if the file doesn't exist yet.
[[ -f "$SRC" ]] || exit 0

mkdir -p "$BACKUP_DIR"

if [[ "$MODE" == "--if-changed" ]]; then
  LATEST=$(ls -t "$BACKUP_DIR"/settings.json.backup.* 2>/dev/null | head -1 || true)
  if [[ -n "$LATEST" ]] && cmp -s "$SRC" "$LATEST"; then
    exit 0
  fi
fi

STAMP=$(python3 -c "import time; print(int(time.time()*1000))")
cp "$SRC" "$BACKUP_DIR/settings.json.backup.$STAMP"

# Rotate: keep only the most recent $KEEP snapshots.
ls -t "$BACKUP_DIR"/settings.json.backup.* 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -I{} rm -f {}

exit 0
