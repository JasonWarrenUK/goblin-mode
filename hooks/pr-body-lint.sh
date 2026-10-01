#!/bin/sh
# PreToolUse hook (Bash, filtered by `if` to gh pr create / gh pr edit).
# Pipes the payload to library/scripts/md-lint.py --hook, which lints the PR
# body the command carries and exits 2 with the hits on stderr, blocking the
# call so Claude fixes the typography first.
# Fail-open: a missing linter or python3 never blocks a command.
lint="${0%/*}/../library/scripts/md-lint.py"
[ -f "$lint" ] || lint="$HOME/.claude/library/scripts/md-lint.py"
[ -f "$lint" ] && command -v python3 >/dev/null 2>&1 || exit 0
exec python3 "$lint" --hook
