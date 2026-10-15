#!/bin/sh
# PreToolUse hook (Bash, filtered by `if` to gh pr create).
# Pipes the payload to library/scripts/web/observations.py guard, which finds
# every docs/artefacts/*/observations.json this branch changed and runs the
# sign-off status on each: an open entry or an unwaived principles finding
# exits 2 with the list on stderr, blocking the call so the review is closed
# before the PR exists.
# Fail-open: a missing script or python3, or no export on the branch, never
# blocks a command.
guard="${0%/*}/../library/scripts/web/observations.py"
[ -f "$guard" ] || guard="$HOME/.claude/library/scripts/web/observations.py"
[ -f "$guard" ] && command -v python3 >/dev/null 2>&1 || exit 0
exec python3 "$guard" guard
