#!/usr/bin/env bash
# session-start-worktree.sh — detects git worktrees and injects context about node_modules
# Run as a SessionStart hook.

git_dir=$(git rev-parse --git-dir 2>/dev/null)

# Not a git repo at all — nothing to do
if [[ -z "$git_dir" ]]; then
  exit 0
fi

# Worktree git dirs look like: /path/to/repo/.git/worktrees/<name>
# The main working tree's git dir is just: /path/to/repo/.git (or .git itself)
if [[ "$git_dir" =~ \.git/worktrees/[^/]+$ ]]; then
  main_root=$(git worktree list 2>/dev/null | head -1 | awk '{print $1}')

  cat <<EOF
[Session context — git worktree detected]

This session is running inside a git worktree, not the main working tree.

IMPORTANT: node_modules is NOT installed in this worktree directory. This means
npm/bun scripts, test runners, build tools, and any other node_modules-dependent
commands will fail if run from the worktree path directly.

Options:
1. Run commands from the main repo root instead:
   Main repo root: ${main_root:-$(git worktree list 2>/dev/null | head -1 | awk '{print $1}')}
   Find it at runtime with: git worktree list | head -1 | awk '{print \$1}'
   Example: cd <main-repo-root> && npm test -- --filter <path>

2. Symlink node_modules into this worktree:
   ln -s ${main_root:-<main-repo-root>}/node_modules ./node_modules

When referencing the worktree path in commands, always qualify them with the
main repo root context (e.g. bun run --cwd <main-root> or cd <main-root> first).
EOF
fi
