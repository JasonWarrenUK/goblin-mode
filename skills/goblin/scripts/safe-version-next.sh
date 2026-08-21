#!/bin/zsh
# safe-version-next.sh — `svu next` with a hard guard on the 0.x -> 1.x boundary.
#
# Prints the tag to create. Identical to `svu next` except when the current
# version is 0.x and svu proposes 1.0.0: crossing into 1.x is a human decision
# (it declares the public API stable), so the script emits a minor bump within
# 0.x instead — semver's own convention for breaking changes pre-1.0. Later
# major bumps (1 -> 2, 2 -> 3, ...) pass through untouched.
#
# usage: safe-version-next.sh
# exit codes: 0 ok (tag on stdout; guard note on stderr when it fired),
#             2 environment error,
#             3 nothing to release (no version-bumping commits since the
#               current tag — creating a tag would fail on a duplicate)
set -u

command -v svu >/dev/null 2>&1 || { print -u2 "svu not installed"; exit 2 }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { print -u2 "not inside a git repository"; exit 2 }

current=$(svu current 2>/dev/null) || current="v0.0.0"
next=$(svu next) || { print -u2 "svu next failed"; exit 2 }

if [[ "$next" == "$current" ]]; then
	print -u2 "nothing to release: no version-bumping commits since $current"
	exit 3
fi

cur_major=${${current#v}%%.*}
next_major=${${next#v}%%.*}

if [[ "$cur_major" == "0" && "$next_major" != "0" ]]; then
	minor=${${${current#v}#*.}%%.*}
	print -u2 "guard: svu proposed $next, but the first 1.x tag is a human decision — emitting a 0.x minor bump instead. Tag v1.0.0 manually when the API is ready to be called stable."
	print "v0.$((minor + 1)).0"
else
	print -r -- "$next"
fi
