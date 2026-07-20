#!/bin/zsh
# Rebuilds roadmap-system.zip — a distributable snapshot of the roadmap tooling
# (scripts, HTML template, conventions reference, and every skill that touches
# roadmaps). Run from anywhere; paths below are relative to the repo root.
#
# Usage: zsh library/scripts/build-roadmap-zip.sh

set -euo pipefail

local script_dir="${0:A:h}"
local repo_root="${script_dir:h:h}"
local out="$repo_root/roadmap-system.zip"

# Single source of truth for what ships. Add a line here when a new file
# starts touching the roadmap system; remove one when it goes stale.
local -a files=(
	"library/scripts/_roadmap_core.py"
	"library/scripts/roadmap.py"
	"library/scripts/test_roadmap.py"
	"library/templates/roadmap-artefact.html"
	"library/references/roadmap-conventions.md"
	"library/configs/examples/roadmaps.json"
	"skills/roadmap-create/SKILL.md"
	"skills/roadmap-create-interview/SKILL.md"
	"skills/roadmap-maintain/SKILL.md"
	"skills/roadmap-migrate/SKILL.md"
	"skills/roadmap-update-tasks/SKILL.md"
	"skills/artefact-roadmap/SKILL.md"
	"skills/task-suggest/SKILL.md"
	"skills/roadmap-build-zip/SKILL.md"
)

cd "$repo_root"

for f in "${files[@]}"; do
	if [[ ! -f "$f" ]]; then
		print -u2 "✗ missing expected file: $f"
		exit 1
	fi
done

rm -f "$out"
zip -X "$out" "${files[@]}" >/dev/null

print "✓ wrote $out"
unzip -l "$out"
