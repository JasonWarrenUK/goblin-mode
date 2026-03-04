#!/bin/bash
set -euo pipefail

# Only run in remote (web) sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
	exit 0
fi

# Ensure all hook scripts are executable
if [ -d "$CLAUDE_PROJECT_DIR/hooks" ]; then
	chmod +x "$CLAUDE_PROJECT_DIR/hooks/"*.zsh 2>/dev/null || true
fi

# Ensure the session-start hook itself stays executable
chmod +x "$CLAUDE_PROJECT_DIR/.claude/hooks/session-start.sh" 2>/dev/null || true
