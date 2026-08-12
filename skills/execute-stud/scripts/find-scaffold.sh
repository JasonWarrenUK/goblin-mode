#!/usr/bin/env zsh
# find-scaffold.sh — locate stud scaffold markers or seams in a path.
#
# Usage:
#   find-scaffold.sh --markers <path>   list &&&& / !!!! scaffold banners as file:line
#   find-scaffold.sh --seams   <path>   inventory SEAM: / HOOKS INTO: / SCHEMA CHANGE:
#
# Exit status:
#   --markers : 1 if any scaffold marker is found (so a Stop hook can flag leftovers),
#               0 if the path is clean.
#   --seams   : always 0 (an inventory, not a gate).
#
# macOS-compatible: uses grep -RnE only, no GNU-only flags.

emulate -L zsh
set -u

mode=${1:-}
target=${2:-.}

case "$mode" in
	--markers)
		# Scaffold banners left behind. && and !! runs of 4+ are the box/inline tags.
		if grep -RnE '&{4,}|!{4,}' "$target" 2>/dev/null; then
			print -u2 "find-scaffold: scaffold markers still present in $target"
			exit 1
		fi
		exit 0
		;;
	--seams)
		# Seam inventory for the handoff/checkpoint summary. Never fails.
		grep -RnE 'SEAM:|HOOKS INTO:|SCHEMA CHANGE:' "$target" 2>/dev/null
		exit 0
		;;
	*)
		print -u2 "usage: find-scaffold.sh --markers|--seams <path>"
		exit 2
		;;
esac
