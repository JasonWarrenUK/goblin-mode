#!/bin/zsh
# git-integrate.sh — mechanical half of the git-integrate skill.
# Fetches the target and integrates it into the current branch by the chosen
# strategy. The model only intervenes on exit 3 (conflicts) and to write the
# squash commit message; tests and the push stay with the caller so nothing
# unverified leaves the machine.
#
# usage: git-integrate.sh <merge|rebase|squash> [target-branch]
#   target defaults to main.
#
# exit codes:
#   0  integration complete (squash: changes staged, awaiting commit message)
#   2  usage or repository-state error (nothing was changed)
#   3  conflicts — left in place for interactive resolution
set -u

strategy=${1:-}
target=${2:-main}

fail() { print -u2 "git-integrate: $1"; exit 2 }

case "$strategy" in
	merge|rebase|squash) ;;
	*) fail "usage: git-integrate.sh <merge|rebase|squash> [target-branch]" ;;
esac

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "not inside a git repository"
branch=$(git symbolic-ref --short -q HEAD) || fail "detached HEAD — check out a branch first"
[[ "$branch" == "$target" ]] && fail "already on '$target' — nothing to integrate"
[[ -n "$(git status --porcelain)" ]] && fail "working tree not clean — commit or stash first"

git fetch origin "$target" || fail "could not fetch origin/$target"

case "$strategy" in
	merge)
		if ! git merge "origin/$target"; then
			print -u2 "CONFLICTS: resolve them, git commit, then run tests and push."
			exit 3
		fi
		print "OK: merged origin/$target into $branch. Run tests, then: git push"
		;;
	rebase|squash)
		if ! git rebase "origin/$target"; then
			print -u2 "CONFLICTS: resolve each, git rebase --continue, then run tests and push with --force-with-lease."
			exit 3
		fi
		if [[ "$strategy" == squash ]]; then
			git reset --soft "origin/$target"
			print "SQUASH-READY: all branch changes staged as one unit on top of origin/$target."
			print "Commit with a descriptive message, run tests, then: git push --force-with-lease"
		else
			print "OK: rebased $branch onto origin/$target. Run tests, then: git push --force-with-lease"
		fi
		;;
esac
exit 0
