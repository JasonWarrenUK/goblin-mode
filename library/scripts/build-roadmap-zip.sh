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

cd "$repo_root"

# Non-skill files ship from this fixed list.
local -a files=(
	"library/scripts/_roadmap_core.py"
	"library/scripts/roadmap.py"
	"library/scripts/test_roadmap.py"
	"library/templates/roadmap-artefact.html"
	"library/references/roadmap-conventions.md"
	"library/configs/examples/roadmaps.json"
)

# Skill membership is discovered from frontmatter: any SKILL.md declaring
# `bundle: roadmap-system` in its metadata ships in the zip. A new
# roadmap-touching skill opts in by adding that line — no edit here needed.
local skill
for skill in skills/*/SKILL.md(N); do
	grep -q "bundle: roadmap-system" "$skill" && files+=("$skill")
done

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
