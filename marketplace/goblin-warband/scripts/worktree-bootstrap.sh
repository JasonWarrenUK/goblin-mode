#!/bin/zsh
# worktree-bootstrap.sh: makes a fresh git worktree usable. Symlinks the main
# checkout's git-ignored .env* files into the worktree at the same relative
# paths, then installs dependencies for every tracked lockfile.
#
# Idempotent: an existing file or link is never overwritten, and a rerun only
# repeats the installs. A failed step is reported and the rest still run.
#
# usage: worktree-bootstrap.sh <worktree-path>
# output: one line per action: `linked <path>`, `installed <dir> (<tool>)`,
#         `failed <dir> (<tool>): <reason>`
# exit codes: 0 every step ok, 1 at least one step failed, 2 usage error
set -u

worktree=${1:-}
[[ -n "$worktree" && -d "$worktree" ]] || { print -u2 -- "usage: worktree-bootstrap.sh <worktree-path>"; exit 2 }
worktree=$(git -C "$worktree" rev-parse --show-toplevel 2>/dev/null) \
	|| { print -u2 -- "$1: not inside a git repository"; exit 2 }
common_dir=$(git -C "$worktree" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) \
	|| { print -u2 -- "$worktree: cannot resolve the main checkout"; exit 2 }
main=${common_dir:h}

exit_status=0

# Env files: git-ignored .env* in the main checkout, minus examples. Entries
# with a trailing slash are ignored directories that --directory collapsed.
if [[ "$main" != "$worktree" ]]; then
	for relative in ${(f)"$(git -C "$main" ls-files -o -i --exclude-standard --directory -- ':(glob)**/.env*' 2>/dev/null)"}; do
		[[ "$relative" == */ || "$relative" == *.example ]] && continue
		[[ -f "$main/$relative" ]] || continue
		[[ -e "$worktree/$relative" || -L "$worktree/$relative" ]] && continue
		mkdir -p "$worktree/${relative:h}"
		if ln -s "$main/$relative" "$worktree/$relative"; then
			print -- "linked $relative"
		else
			print -- "failed $relative (link): ln exited $?"
			exit_status=1
		fi
	done
fi

# Dependencies: one install per tracked lockfile, run in its directory. A JS
# lockfile below a directory that already ran a JS install is a workspace
# member, so it is skipped.
typeset -A install_command=(
	bun.lock "bun install"
	bun.lockb "bun install"
	pnpm-lock.yaml "pnpm install --frozen-lockfile"
	package-lock.json "npm ci"
	poetry.lock "poetry install"
	uv.lock "uv sync"
)
js_lockfiles=(bun.lock bun.lockb pnpm-lock.yaml package-lock.json)
js_dirs=()

lockfiles=(${(f)"$(git -C "$worktree" ls-files -- ${(k)install_command/#/:(glob)**/} 2>/dev/null | sort)"})
# Shallowest first, so a workspace root claims its members.
lockfiles=(${(f)"$(print -rl -- $lockfiles | awk -F/ '{print NF, $0}' | sort -n | cut -d' ' -f2-)"})

for lockfile in $lockfiles; do
	name=${lockfile:t}
	directory=${lockfile:h}
	command_line=${install_command[$name]:-}
	[[ -n "$command_line" ]] || continue
	tool=${command_line%% *}

	if (( ${js_lockfiles[(Ie)$name]} )); then
		skip=0
		for claimed in $js_dirs; do
			if [[ "$claimed" == . || "$directory" == "$claimed"/* ]]; then skip=1; break; fi
		done
		(( skip )) && continue
		js_dirs+=($directory)
	fi

	if ! command -v "$tool" >/dev/null 2>&1; then
		print -- "failed $directory ($tool): $tool is not installed"
		exit_status=1
		continue
	fi

	log=$(mktemp)
	if (cd "$worktree/$directory" && ${=command_line}) >"$log" 2>&1; then
		print -- "installed $directory ($tool)"
	else
		print -- "failed $directory ($tool): $(tail -n 1 "$log")"
		exit_status=1
	fi
	rm -f "$log"
done

exit $exit_status
