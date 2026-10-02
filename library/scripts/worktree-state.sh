#!/bin/zsh
# worktree-state.sh: reports whether a worktree is dirty and how far its HEAD
# sits ahead of and behind a base, for the read-only worktree map.
#
# It exists so hud-worktrees can allow one script instead of `git -C * ...`
# rules: a `*` before the git subcommand also matches `-c core.fsmonitor=...`,
# which makes git run a program. Here every git flag is fixed, the path is only
# ever the value of `-C` and the base is resolved to a commit id before
# rev-list sees it.
#
# usage: worktree-state.sh <path> [base]
#   base: a ref to count against (origin/main, origin/<PR base>); omitted, the
#         branch's upstream; neither resolving, ahead and behind are null
# prints: {"path", "dirty", "base", "ahead", "behind"} as one JSON object
# exit codes: 0 reported, 2 environment or usage error
set -u

(( $# >= 1 && $# <= 2 )) || { print -u2 -- "usage: worktree-state.sh <path> [base]"; exit 2 }
target=$1
base=${2:-}

command -v jq >/dev/null 2>&1 || { print -u2 -- "jq not installed"; exit 2 }
[[ -d "$target" ]] || { print -u2 -- "$target: not a directory"; exit 2 }
[[ "$(git -C "$target" rev-parse --is-inside-work-tree 2>/dev/null)" == true ]] \
	|| { print -u2 -- "$target: not inside a git work tree"; exit 2 }

dirty=$(git -C "$target" status --porcelain | wc -l | tr -d ' ')

if [[ -n "$base" ]]; then
	base_commit=$(git -C "$target" rev-parse --verify --quiet --end-of-options "$base^{commit}") \
		|| { print -u2 -- "$base: not a commit in $target"; exit 2 }
	base_name=$base
else
	base_commit=$(git -C "$target" rev-parse --verify --quiet "@{upstream}^{commit}" 2>/dev/null) || base_commit=""
	base_name=$(git -C "$target" rev-parse --abbrev-ref --symbolic-full-name "@{upstream}" 2>/dev/null) || base_name=""
fi

if [[ -n "$base_commit" ]]; then
	counts=(${=$(git -C "$target" rev-list --left-right --count "$base_commit...HEAD")})
	jq -n --arg path "$target" --argjson dirty "$dirty" --arg base "$base_name" \
		--argjson behind "${counts[1]}" --argjson ahead "${counts[2]}" \
		'{path: $path, dirty: $dirty, base: $base, ahead: $ahead, behind: $behind}'
else
	jq -n --arg path "$target" --argjson dirty "$dirty" \
		'{path: $path, dirty: $dirty, base: null, ahead: null, behind: null}'
fi
