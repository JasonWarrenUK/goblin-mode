#!/bin/sh
# SessionStart hook: one-line nudge when the cwd's roadbook has drifted.
# Silent unless a rich roadbook exists AND validate reports discrepancies.
root="${CLAUDE_PLUGIN_ROOT:-$(dirname "$0")/..}"
python3 "$root/scripts/roadbook.py" detect >/dev/null 2>&1 || exit 0
python3 "$root/scripts/roadbook.py" validate >/dev/null 2>&1 && exit 0
printf '%s\n' "Roadbook drift: roadbook.py validate reports discrepancies; consider running /goblin-scout:tend-roadbook"
exit 0
