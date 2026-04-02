#!/bin/zsh

# ~/.claude/hooks/pre-push.zsh

# --- Configuration ---
# Add your repository/directory names to this list
ALLOWED_REPOS=(
  "iris"
)

# --- Logic ---

# Get the name of the current directory
CURRENT_REPO=$(basename "$PWD")

# Check if the current repo is in the allowed list
IS_ALLOWED=false
for repo in "${ALLOWED_REPOS[@]}"; do
  if [[ "$repo" == "$CURRENT_REPO" ]]; then
    IS_ALLOWED=true
    break
  fi
done

# If not allowed, exit silently and let the push happen
if [ "$IS_ALLOWED" = false ]; then
  exit 0
fi

echo "🛡️  Pre-push hook active for: $CURRENT_REPO"

# --- Original Execution ---

# Capture stdin (push info)
PUSH_INFO=$(cat)

# Run tests first
echo "$PUSH_INFO" | ~/.claude/hooks/pre-push-tests "$@"
TEST_EXIT=$?

# If tests failed and user cancelled, stop here
if [ $TEST_EXIT -ne 0 ]; then
  exit $TEST_EXIT
fi

# Run evidence extraction
echo "$PUSH_INFO" | ~/.claude/hooks/pre-push-evidence "$@"
