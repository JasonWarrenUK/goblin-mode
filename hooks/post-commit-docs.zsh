#!/bin/bash

# Documentation Sync Hook
# Trigger: post-commit
# Checks if documentation needs updating

set -e

NOTES_PATH="$HOME/Code/notes"
REMINDERS_FILE="$HOME/.claude/doc-reminders.txt"
PROJECT_ROOT=$(git rev-parse --show-toplevel)
PROJECT_NAME=$(basename "$PROJECT_ROOT")

# Colors
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m'

# Get last commit info
COMMIT_HASH=$(git rev-parse HEAD)
COMMIT_SHORT=$(git rev-parse --short HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B | head -n1)
COMMIT_DATE=$(date "+%Y-%m-%d %H:%M")
COMMIT_FILES=$(git diff-tree --no-commit-id --name-only -r HEAD)

# Documentation mappings (using arrays instead of associative arrays for bash 3 compatibility)
map_file_to_doc() {
  local file="$1"

  case "$file" in
    src/routes/api/*|src/lib/api/*) echo "api.md" ;;
    src/lib/components/*|src/components/*) echo "components.md" ;;
    src/lib/db/*|src/lib/server/database/*|src/**/*schema*|src/**/*migration*|*migration*) echo "database.md" ;;
    src/**/auth*|src/**/session*) echo "security.md" ;;
    *.config.ts|*.config.js|package.json) echo "README.md" ;;
    src/routes/**/+page.svelte|src/routes/**/+layout.svelte) echo "routing.md" ;;
    src/lib/utils/*|src/lib/services/*) echo "architecture.md" ;;
    src/styles/*|*.css) echo "styling.md" ;;
    *) echo "" ;;
  esac
}

# Find relevant docs and track files
declare -a RELEVANT_DOCS=()
TEMP_DIR=$(mktemp -d)

while IFS= read -r file; do
  [ -z "$file" ] && continue

  doc=$(map_file_to_doc "$file")
  if [ -n "$doc" ]; then
    RELEVANT_DOCS+=("$doc")

    # Track which files trigger which docs (using temp files)
    echo "$file" >> "$TEMP_DIR/$doc"
  fi
done <<< "$COMMIT_FILES"

# Remove duplicates
RELEVANT_DOCS=($(printf "%s\n" "${RELEVANT_DOCS[@]}" | sort -u))

# Check if docs were also updated in commit
DOCS_UPDATED=()
for doc in "${RELEVANT_DOCS[@]}"; do
  if echo "$COMMIT_FILES" | grep -q "$doc"; then
    DOCS_UPDATED+=("$doc")
  fi
done

# Remove updated docs from relevant list
NEEDS_UPDATE=()
for doc in "${RELEVANT_DOCS[@]}"; do
  if [[ ! " ${DOCS_UPDATED[@]} " =~ " ${doc} " ]]; then
    NEEDS_UPDATE+=("$doc")
  fi
done

# If no docs need updates, exit
if [ ${#NEEDS_UPDATE[@]} -eq 0 ]; then
  if [ ${#DOCS_UPDATED[@]} -gt 0 ]; then
    echo -e "${GREEN}✅ Documentation updated${NC}"
  fi
  exit 0
fi

# Show which docs may need updates
echo ""
echo -e "${BLUE}📝 Documentation check:${NC}"
echo ""
echo -e "${YELLOW}⚠️  The following docs may need updates:${NC}"
echo ""

for doc in "${NEEDS_UPDATE[@]}"; do
  doc_path="$NOTES_PATH/$doc"
  echo -e "  ${BLUE}📄 $doc${NC}"

  # Show affected files
  if [ -f "$TEMP_DIR/$doc" ]; then
    while IFS= read -r file; do
      [ -z "$file" ] && continue
      echo "     • $file"
    done < "$TEMP_DIR/$doc"
  fi

  # Show doc location and age
  if [ -f "$doc_path" ]; then
    last_modified=$(stat -f "%Sm" -t "%Y-%m-%d" "$doc_path" 2>/dev/null || stat -c "%y" "$doc_path" 2>/dev/null | cut -d' ' -f1)
    echo "     Existing: $doc_path"
    echo "     Last updated: $last_modified"
  else
    echo "     ${YELLOW}Not found: $doc_path${NC}"
  fi

  echo ""
done

# Prompt user
if [[ ! -t 0 ]]; then exit 0; fi
read -p "? Update documentation? (y/n/later) " -r
echo ""

case "$REPLY" in
  y|Y)
    # Open docs in editor
    EDITOR="${EDITOR:-vim}"
    for doc in "${NEEDS_UPDATE[@]}"; do
      doc_path="$NOTES_PATH/$doc"

      # Create if doesn't exist
      if [ ! -f "$doc_path" ]; then
        mkdir -p "$(dirname "$doc_path")"
        echo "# $(basename "$doc" .md | tr '[:lower:]' '[:upper:]')" > "$doc_path"
        echo "" >> "$doc_path"
        echo "Created: $(date)" >> "$doc_path"
        echo "" >> "$doc_path"
      fi

      $EDITOR "$doc_path"
    done

    echo -e "${GREEN}✓${NC} Documentation updated"
    ;;

  n|N)
    echo -e "${BLUE}⊘${NC} Skipped documentation updates"
    ;;

  *)
    # Add to reminders
    mkdir -p "$(dirname "$REMINDERS_FILE")"

    # Initialize file if doesn't exist
    if [ ! -f "$REMINDERS_FILE" ]; then
      echo "# Documentation Reminders" > "$REMINDERS_FILE"
      echo "" >> "$REMINDERS_FILE"
    fi

    # Add new reminder
    {
      echo ""
      echo "## $COMMIT_DATE - $COMMIT_MSG ($COMMIT_SHORT)"
      echo "**Project**: $PROJECT_NAME"

      for doc in "${NEEDS_UPDATE[@]}"; do
        echo "- [ ] $doc"
        while IFS= read -r file; do
          [ -z "$file" ] && continue
          echo "  - $file"
        done < "$TEMP_DIR/$doc"
      done
    } >> "$REMINDERS_FILE"

    echo -e "${GREEN}✓${NC} Reminders saved to $REMINDERS_FILE"
    echo "  Run 'claude docs' to see pending updates"
    ;;
esac

# Cleanup temp files
rm -rf "$TEMP_DIR"
