#!/bin/zsh
# pr-wall.sh — one-call data gather for the hud-pr_wall skill. Buckets open
# PRs by their relationship to the authenticated user and cross-references
# each against local clones, so the skill formats a single JSON dump instead
# of orchestrating gh calls and directory walks itself.
#
# usage: pr-wall.sh [this|all] [code-root]
#   scope defaults to `this` inside a git repo with a GitHub remote, else `all`
#   code-root defaults to ~/code (searched 3 levels deep for clones)
#
# output: one JSON object:
#   { scope, buckets: { mineAwaiting, mineChangesRequested, mineApproved,
#     reviewRequested } } — each entry: { repo, number, title, url, isDraft,
#     reviewDecision, updatedAt, localPath|null }
# exit codes: 0 ok, 2 environment/usage error
set -u

command -v gh >/dev/null 2>&1 || { print -u2 "gh not installed"; exit 2 }
command -v jq >/dev/null 2>&1 || { print -u2 "jq not installed"; exit 2 }

scope=${1:-}
root=${2:-$HOME/code}

if [[ -z "$scope" ]]; then
	if gh repo view --json nameWithOwner >/dev/null 2>&1; then scope=this; else scope=all; fi
fi

repo_filter=""
if [[ "$scope" == "this" ]]; then
	nwo=$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null) \
		|| { print -u2 "scope 'this' needs a GitHub repository in the current directory"; exit 2 }
	repo_filter=" repo:$nwo"
elif [[ "$scope" != "all" ]]; then
	print -u2 "usage: pr-wall.sh [this|all] [code-root]"; exit 2
fi

search() {
	gh api graphql -f query='
query($q: String!) {
	search(query: $q, type: ISSUE, first: 50) {
		nodes {
			... on PullRequest {
				repository { nameWithOwner }
				number title url isDraft reviewDecision updatedAt
			}
		}
	}
}' -f q="$1" --jq '[.data.search.nodes[] | select(.number != null) | {repo: .repository.nameWithOwner, number, title, url, isDraft, reviewDecision, updatedAt}]'
}

mine=$(search "is:pr is:open author:@me archived:false$repo_filter") || exit 2
requested=$(search "is:pr is:open review-requested:@me archived:false$repo_filter") || exit 2

# nameWithOwner -> local clone path (first match wins; worktrees excluded by
# matching only real .git directories, not .git files)
clones="{}"
if [[ -d "$root" ]]; then
	while IFS= read -r gitdir; do
		dir=${gitdir:h}
		url=$(git -C "$dir" remote get-url origin 2>/dev/null) || continue
		nwo=$(print -r -- "$url" | sed -E 's#^(git@github\.com:|https://github\.com/)##; s#\.git$##')
		[[ -n "$nwo" ]] && clones=$(print -r -- "$clones" | jq --arg k "$nwo" --arg v "$dir" 'if has($k) then . else . + {($k): $v} end')
	done < <(find "$root" -maxdepth 3 -type d -name .git 2>/dev/null)
fi

jq -n --argjson mine "$mine" --argjson req "$requested" --argjson clones "$clones" --arg scope "$scope" '
	def local: . + {localPath: ($clones[.repo] // null)};
	{
		scope: $scope,
		buckets: {
			mineAwaiting:         [$mine[] | select(.reviewDecision == "REVIEW_REQUIRED" or .reviewDecision == null) | local],
			mineChangesRequested: [$mine[] | select(.reviewDecision == "CHANGES_REQUESTED") | local],
			mineApproved:         [$mine[] | select(.reviewDecision == "APPROVED") | local],
			reviewRequested:      [$req[] | local]
		}
	}'
