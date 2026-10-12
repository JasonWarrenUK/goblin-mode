#!/usr/bin/env bash
# session-start-worktree.sh — detects git worktrees and warns when dependencies are missing
# Run as a SessionStart hook.

git_dir=$(git rev-parse --git-dir 2>/dev/null)

# Not a git repo at all — nothing to do
if [[ -z "$git_dir" ]]; then
  exit 0
fi

# Worktree git dirs look like: /path/to/repo/.git/worktrees/<name>
# The main working tree's git dir is just: /path/to/repo/.git (or .git itself)
if [[ "$git_dir" =~ \.git/worktrees/[^/]+$ ]]; then
  worktree_root=$(git rev-parse --show-toplevel 2>/dev/null)

  # A JS lockfile at the worktree root with no node_modules beside it means
  # nothing has been installed yet. Python venvs live outside the tree, so
  # they are not checked here.
  has_js_lockfile=0
  for lockfile in bun.lock bun.lockb pnpm-lock.yaml package-lock.json; do
    [[ -f "$worktree_root/$lockfile" ]] && has_js_lockfile=1
  done

  if [[ "$has_js_lockfile" == 1 && ! -d "$worktree_root/node_modules" ]]; then
    cat <<EOF
[Session context — git worktree with no installed dependencies]

This session is running inside a git worktree and node_modules is not installed.
Run this before any test, build or script:

  ~/.claude/library/scripts/worktree-bootstrap.sh $worktree_root

It symlinks the main checkout's git-ignored .env* files and installs
dependencies for every tracked lockfile.
EOF
  fi
fi
