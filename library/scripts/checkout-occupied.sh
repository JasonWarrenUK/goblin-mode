#!/bin/zsh
# checkout-occupied.sh: reports whether another live Claude session is working
# in a checkout, so a skill can leave that checkout alone instead of switching
# its branch or committing beside someone else's uncommitted files.
#
# Claude Code keeps one JSON file per live session in ~/.claude/sessions/,
# holding its pid, name, status and cwd. A session occupies a checkout when
# its pid is alive and the worktree containing its cwd is the one asked about.
# The calling session is left out: any session whose pid is an ancestor of
# this script is the caller.
#
# The recorded cwd is where the session started. A session that started in the
# main checkout and moved its work into a worktree still counts against the
# main checkout: over-cautious on purpose.
#
# usage: checkout-occupied.sh [path]   (default: the current directory)
# env:   CLAUDE_SESSIONS_DIR overrides the sessions directory (tests use it)
# exit codes: 0 no other live session in the checkout,
#             1 occupied (sessions listed in the JSON),
#             2 environment or usage error
set -u

target=${1:-$PWD}
sessions_dir=${CLAUDE_SESSIONS_DIR:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sessions}

command -v jq >/dev/null 2>&1 || { print -u2 -- "jq not installed"; exit 2 }
[[ -d "$target" ]] || { print -u2 -- "$target: not a directory"; exit 2 }
checkout=$(git -C "$target" rev-parse --show-toplevel 2>/dev/null) \
	|| { print -u2 -- "$target: not inside a git repository"; exit 2 }

# macOS volumes are case-insensitive by default, and a session's cwd keeps
# whatever case it was started with
normalise() {
	if [[ "$OSTYPE" == darwin* ]]; then print -r -- "${1:l}"; else print -r -- "$1"; fi
}

typeset -A ancestors
pid=$$
while [[ -n "$pid" ]] && (( pid > 1 )); do
	ancestors[$pid]=1
	pid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
done

branch=$(git -C "$checkout" symbolic-ref --short -q HEAD) || branch=""
dirty_files=$(git -C "$checkout" status --porcelain 2>/dev/null | wc -l | tr -d ' ')

occupants=()
for session_file in "$sessions_dir"/*.json(N); do
	session_pid=$(jq -r '.pid // empty' "$session_file" 2>/dev/null)
	session_cwd=$(jq -r '.cwd // empty' "$session_file" 2>/dev/null)
	[[ "$session_pid" == <-> && -n "$session_cwd" ]] || continue
	(( ${+ancestors[$session_pid]} )) && continue
	kill -0 "$session_pid" 2>/dev/null || continue
	session_checkout=$(git -C "$session_cwd" rev-parse --show-toplevel 2>/dev/null) || continue
	[[ "$(normalise "$session_checkout")" == "$(normalise "$checkout")" ]] || continue
	occupants+=("$(jq -c '{name: (.name // ""), pid, status: (.status // ""), cwd, session_id: (.sessionId // "")}' "$session_file")")
done

sessions_json="[]"
(( ${#occupants} )) && sessions_json=$(print -rl -- "${occupants[@]}" | jq -s -c '.')

jq -n \
	--arg checkout "$checkout" \
	--arg branch "$branch" \
	--argjson dirty_files "$dirty_files" \
	--argjson sessions "$sessions_json" \
	'{checkout: $checkout, branch: $branch, dirty_files: $dirty_files, occupied: ($sessions | length > 0), sessions: $sessions}'

(( ${#occupants} )) && exit 1
exit 0
