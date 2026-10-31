#!/bin/sh
# Claude Code hook for clod-approach-types, three callers wired in settings.json:
#   PreToolUse   (matcher: Edit|Write)   type-guard.sh remind
#   PostToolUse  (matcher: Edit|Write)   type-guard.sh scan
#   SessionStart (matcher: compact)      type-guard.sh compact
# Pipes the payload to library/scripts/type-guard.py <mode>. remind and compact
# print the type-intent reminder as additionalContext (remind only when the
# text being written declares a type, at most once per half hour per session);
# scan runs the ast-grep rules in library/ast-grep over the .ts or .py file
# just written and exits 2 with the findings on stderr, so Claude fixes the
# file before moving on.
# Per-repo opt-out: git config typeGuard.enforce false / typeGuard.remind false
# Fail-open: a missing script, python3 or ast-grep never blocks an edit.
guard="${0%/*}/../library/scripts/type-guard.py"
[ -f "$guard" ] || guard="$HOME/.claude/library/scripts/type-guard.py"
[ -f "$guard" ] && command -v python3 >/dev/null 2>&1 || exit 0
exec python3 "$guard" "${1:-scan}"
