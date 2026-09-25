#!/bin/zsh
# safe-version-next.sh: `svu next` with a hard guard on the 0.x -> 1.x boundary.
#
# Prints the tag to create. Identical to `svu next` except when the current
# version is 0.x and svu proposes 1.0.0: crossing into 1.x is a human decision
# (it declares the public API stable), so the script emits a minor bump within
# 0.x instead: semver's own convention for breaking changes pre-1.0. Later
# major bumps (1 -> 2, 2 -> 3, ...) pass through untouched.
#
# usage: safe-version-next.sh [--plugin NAME --dir PATH]
#   no flags        root repo: tag prefix "v", history from the whole repo
#   --plugin --dir  scope to one plugin subtree: tag prefix "NAME-v",
#                    history and svu's commit scan both limited to PATH, so a
#                    plugin only bumps on commits that actually touched it
# exit codes: 0 ok (tag on stdout; guard note on stderr when it fired),
#             2 environment error,
#             3 nothing to release (no version-bumping commits since the
#               current tag: creating a tag would fail on a duplicate)
set -u

plugin=""
dir=""
while (( $# > 0 )); do
	case "$1" in
	--plugin) [[ $# -ge 2 ]] || { print -u2 -- "--plugin needs a value"; exit 2 }
		plugin="$2"; shift 2 ;;
	--dir) [[ $# -ge 2 ]] || { print -u2 -- "--dir needs a value"; exit 2 }
		dir="$2"; shift 2 ;;
	*) print -u2 -- "unknown argument: $1"; exit 2 ;;
	esac
done
if [[ -n "$plugin" && -z "$dir" ]] || [[ -z "$plugin" && -n "$dir" ]]; then
	print -u2 -- "--plugin and --dir must be given together"
	exit 2
fi

command -v svu >/dev/null 2>&1 || { print -u2 -- "svu not installed"; exit 2 }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { print -u2 -- "not inside a git repository"; exit 2 }

# svu current has no --log.directory (it only needs the latest matching tag,
# not a commit scan); svu next needs it to limit which commits count towards
# a bump. Passing --log.directory to `current` fails with "Unknown flag" and
# would otherwise be swallowed by the 2>/dev/null fallback below, so the two
# commands get their own argument lists rather than one shared array.
current_args=()
next_args=()
prefix="v"
if [[ -n "$plugin" ]]; then
	[[ -d "$dir" ]] || { print -u2 -- "$dir: not a directory"; exit 2 }
	prefix="${plugin}-v"
	current_args=(--tag.prefix "$prefix" --tag.pattern "${prefix}*")
	next_args=("${current_args[@]}" --log.directory "$dir")
fi

current=$(svu current "${current_args[@]}" 2>/dev/null) || current="${prefix}0.0.0"
if [[ "$current" == "${prefix}0.0.0" ]]; then
	# svu current tolerates zero matching tags (falls back above); svu next
	# does not, it hard-errors "no tags match" instead of treating an empty
	# series as a first release. A fresh series starts at whatever the
	# plugin's already-built plugin.json declares (so a plugin authored at
	# 0.3.0 before its first tag doesn't get written back down to 0.1.0),
	# or 0.1.0 when no built plugin.json exists yet either.
	declared=""
	if [[ -n "$plugin" && -f "$dir/.claude-plugin/plugin.json" ]]; then
		declared=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([0-9][0-9.]*\)".*/\1/p' "$dir/.claude-plugin/plugin.json" | head -1)
	fi
	next="${prefix}${declared:-0.1.0}"
else
	next=$(svu next "${next_args[@]}") || { print -u2 -- "svu next failed"; exit 2 }
fi

if [[ "$next" == "$current" ]]; then
	print -u2 -- "nothing to release: no version-bumping commits since $current"
	exit 3
fi

cur_major=${${current#$prefix}%%.*}
next_major=${${next#$prefix}%%.*}

if [[ "$cur_major" == "0" && "$next_major" != "0" ]]; then
	minor=${${${current#$prefix}#*.}%%.*}
	print -u2 -- "guard: svu proposed $next, but the first 1.x tag is a human decision: emitting a 0.x minor bump instead. Tag ${prefix}1.0.0 manually when the API is ready to be called stable."
	print "${prefix}0.$((minor + 1)).0"
else
	print -r -- "$next"
fi
