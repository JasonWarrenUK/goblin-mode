#!/bin/zsh
# SessionStart hook: one-line nudge when the cwd's roadmap has drifted.
# Silent (exit 0, no output) unless a rich roadmap exists AND validate
# reports discrepancies. Fast in non-roadmap repos: detect walks up from
# the cwd and exits non-zero immediately when nothing is found.

python3 "$HOME"/.claude/library/scripts/roadmap.py detect >/dev/null 2>&1 || exit 0
python3 "$HOME"/.claude/library/scripts/roadmap.py validate >/dev/null 2>&1 && exit 0
print "⚠ Roadmap drift: roadmap.py validate reports discrepancies; consider running /roadmap-maintain"
exit 0
