#!/bin/sh
# PreToolUse hook (Bash, filtered by `if` to gh api, gh pr comment, gh pr
# review, gh issue comment, gh release create and gh release edit).
# Pipes the payload to library/scripts/gh-guard.py --hook, which exits 2 with
# the reason on stderr when a body is given inline instead of from a file, or
# when a release has no notes source or an empty notes file, blocking the call
# so Claude writes the text to a file first.
# Fail-open: a missing script or python3 never blocks a command.
guard="${0%/*}/../library/scripts/gh-guard.py"
[ -f "$guard" ] || guard="$HOME/.claude/library/scripts/gh-guard.py"
[ -f "$guard" ] && command -v python3 >/dev/null 2>&1 || exit 0
exec python3 "$guard" --hook
