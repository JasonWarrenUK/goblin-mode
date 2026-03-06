#!/bin/bash
set -euo pipefail

# Only run in local (terminal) sessions
if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then
	exit 0
fi

ENV="$CLAUDE_ENV_FILE"
PROJECT="$CLAUDE_PROJECT_DIR"

# ─── Git Worktree Awareness ─────────────────────────────────────────

if git -C "$PROJECT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
	# Detect if we're inside a worktree (not the main working tree)
	GIT_COMMON=$(git -C "$PROJECT" rev-parse --git-common-dir 2>/dev/null)
	GIT_DIR=$(git -C "$PROJECT" rev-parse --git-dir 2>/dev/null)

	if [ "$GIT_DIR" != "$GIT_COMMON" ]; then
		echo 'export GIT_IS_WORKTREE="true"' >> "$ENV"
		echo "export GIT_MAIN_WORKTREE=\"$(git -C "$PROJECT" worktree list --porcelain | head -1 | sed 's/^worktree //')\"" >> "$ENV"
	fi

	# List all active worktrees and their branches (prevents duplicate branch creation)
	WORKTREES=$(git -C "$PROJECT" worktree list --porcelain 2>/dev/null | grep -E '^(worktree |branch )' | paste - - 2>/dev/null | sed 's/worktree //;s/\tbranch refs\/heads\// /' | tr '\n' '|' | sed 's/|$//')
	if [ -n "$WORKTREES" ]; then
		echo "export GIT_WORKTREES=\"$WORKTREES\"" >> "$ENV"
	fi

	# ─── Stale Branch Detection ──────────────────────────────────────

	DEFAULT_BRANCH=$(git -C "$PROJECT" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
	BEHIND=$(git -C "$PROJECT" rev-list --count "HEAD..origin/$DEFAULT_BRANCH" 2>/dev/null || echo "0")
	if [ "$BEHIND" -gt 20 ]; then
		echo "export GIT_BRANCH_STALE=\"true\"" >> "$ENV"
		echo "export GIT_COMMITS_BEHIND=\"$BEHIND\"" >> "$ENV"
	fi

	# ─── Conflict / Rebase Detection ─────────────────────────────────

	GIT_DIR_ABS=$(git -C "$PROJECT" rev-parse --absolute-git-dir 2>/dev/null)
	if [ -d "$GIT_DIR_ABS/rebase-merge" ] || [ -d "$GIT_DIR_ABS/rebase-apply" ]; then
		echo 'export GIT_REBASE_IN_PROGRESS="true"' >> "$ENV"
	elif [ -f "$GIT_DIR_ABS/MERGE_HEAD" ]; then
		echo 'export GIT_MERGE_IN_PROGRESS="true"' >> "$ENV"
	elif [ -f "$GIT_DIR_ABS/CHERRY_PICK_HEAD" ]; then
		echo 'export GIT_CHERRY_PICK_IN_PROGRESS="true"' >> "$ENV"
	fi
fi

# ─── Local Toolchain Verification ────────────────────────────────────

MISSING_TOOLS=""
for tool in zed bun gh; do
	if ! command -v "$tool" >/dev/null 2>&1; then
		MISSING_TOOLS="${MISSING_TOOLS}${tool},"
	fi
done
if [ -n "$MISSING_TOOLS" ]; then
	MISSING_TOOLS=$(echo "$MISSING_TOOLS" | sed 's/,$//')
	echo "export MISSING_TOOLS=\"$MISSING_TOOLS\"" >> "$ENV"
fi

# Detect preferred editor
if command -v zed >/dev/null 2>&1; then
	echo 'export EDITOR_AVAILABLE="zed"' >> "$ENV"
elif [ -n "${VISUAL:-}" ]; then
	echo "export EDITOR_AVAILABLE=\"$VISUAL\"" >> "$ENV"
elif [ -n "${EDITOR:-}" ]; then
	echo "export EDITOR_AVAILABLE=\"$EDITOR\"" >> "$ENV"
fi
