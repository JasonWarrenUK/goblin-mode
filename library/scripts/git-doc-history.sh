#!/bin/zsh
# git-doc-history.sh — the "what changed since this doc was last touched"
# gathering step for doc-update skills, so the model analyses one structured
# dump instead of orchestrating several exploratory git calls.
#
# usage: git-doc-history.sh <doc-path> [scope-dir]
#   scope-dir defaults to the doc's own directory.
#
# exit codes: 0 ok (including "no changes"), 2 usage/repository error
set -u

doc=${1:-}
[[ -n "$doc" ]] || { print -u2 "usage: git-doc-history.sh <doc-path> [scope-dir]"; exit 2 }
scope=${2:-$(dirname "$doc")}

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { print -u2 "not inside a git repository"; exit 2 }

last=$(git log -1 --format=%H -- "$doc" 2>/dev/null)
if [[ -n "$last" ]]; then
	range="$last..HEAD"
	print "== commits touching '$scope' since '$doc' last changed ($last) =="
else
	range="HEAD~15..HEAD"
	print "== '$doc' has no git history; last 15 commits touching '$scope' =="
fi

commits=$(git log --oneline "$range" -- "$scope" 2>/dev/null)
if [[ -z "$commits" ]]; then
	print "(no changes — the doc is up to date with '$scope')"
	exit 0
fi
print "$commits"
print ""
print "== file changes in that range =="
git diff --name-status "$range" -- "$scope"
print ""
print "== diff stat =="
git diff --stat "$range" -- "$scope"
