#!/bin/sh
# SessionStart hook: one-line nudge when the cwd's roadmap has drifted.
# Silent unless a rich roadmap exists AND validate reports discrepancies.
root="${CLAUDE_PLUGIN_ROOT:-$(dirname "$0")/..}"
python3 "$root/scripts/roadmap.py" detect >/dev/null 2>&1 || exit 0
python3 "$root/scripts/roadmap.py" validate >/dev/null 2>&1 && exit 0
printf '%s\n' "Roadmap drift: roadmap.py validate reports discrepancies; consider running /roadmap:maintain"
exit 0
