#!/bin/zsh
# pr-facts.sh — the "what changed since the description was written" gathering
# step for pr-update: PR metadata, current body, the watermark, and every
# commit since it, in one structured dump instead of several exploratory calls.
#
# usage: pr-facts.sh <pr-number-or-url>
# exit codes: 0 ok, 2 environment/usage error,
#             3 no new commits since the watermark (description is current)
set -u

pr=${1:-}
[[ -n "$pr" ]] || { print -u2 "usage: pr-facts.sh <pr-number-or-url>"; exit 2 }
command -v gh >/dev/null 2>&1 || { print -u2 "gh not installed"; exit 2 }
command -v jq >/dev/null 2>&1 || { print -u2 "jq not installed"; exit 2 }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { print -u2 "not inside a git repository"; exit 2 }

json=$(gh pr view "$pr" --json number,title,body,headRefName,baseRefName) || exit 2
body=$(print -r -- "$json" | jq -r .body)
head_ref=$(print -r -- "$json" | jq -r .headRefName)
base_ref=$(print -r -- "$json" | jq -r .baseRefName)

git fetch origin "$base_ref" "$head_ref" >/dev/null 2>&1 || true
tip="origin/$head_ref"
git rev-parse --verify -q "$tip" >/dev/null || tip="$head_ref"
git rev-parse --verify -q "$tip" >/dev/null || { print -u2 "cannot resolve PR head '$head_ref' locally"; exit 2 }

print "== pr =="
print -r -- "$json" | jq '{number, title, headRefName, baseRefName}'
print "== body =="
print -r -- "$body"

watermark=$(print -r -- "$body" | sed -nE 's/.*<!-- pr-update-watermark: ([0-9a-f]+) -->.*/\1/p' | tail -1)
if [[ -n "$watermark" ]] && git cat-file -e "$watermark^{commit}" 2>/dev/null; then
	range="$watermark..$tip"
	print "== watermark: $watermark =="
else
	base="origin/$base_ref"
	git rev-parse --verify -q "$base" >/dev/null || base="$base_ref"
	range="$base..$tip"
	print "== watermark: none (whole branch is new) =="
fi

commits=$(git log --oneline "$range" 2>/dev/null)
if [[ -z "$commits" ]]; then
	print "(no new commits — the description is already up to date)"
	exit 3
fi

print "== new commits ($range) =="
print -r -- "$commits"
print "== per-commit stat =="
git log --stat "$range"
print "== next watermark sha =="
git rev-parse "$tip"
