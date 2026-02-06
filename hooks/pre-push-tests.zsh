#!/bin/bash

# Test Automation Hook - Simplified
# Trigger: pre-push
# Checks for untested code and runs tests

PROJECT_ROOT=$(git rev-parse --show-toplevel)
cd "$PROJECT_ROOT"

echo "🔍 Checking for untested code..."

# Get files changed since last push (simplified)
REMOTE_BRANCH="origin/main"
CHANGED_FILES=$(git diff --name-only "$REMOTE_BRANCH"...HEAD 2>/dev/null || git diff --name-only HEAD~1 2>/dev/null || git ls-files)

# Filter to only source files (not config/docs/test fixtures/barrel exports/types)
SOURCE_FILES=$(echo "$CHANGED_FILES" | grep -E '\.(ts|js|svelte)$' | grep -v -E '\.(test|spec)\.(ts|js)$' | grep -v -E '\.(config|setup)\.(ts|js)$' | grep -v -E '(^|/)tests?/' | grep -v -E '(^|/)index\.(ts|js)$' | grep -v -E '(^|/)types/' |  | grep -v -E '(^|/)brand?/')

if [ -z "$SOURCE_FILES" ]; then
  echo "✓ No testable source files changed"
  exit 0
fi

# Check each source file for tests
UNTESTED_FILES=()
while IFS= read -r file; do
  [ -z "$file" ] && continue
  [ ! -f "$file" ] && continue

  # Determine test file name (co-located)
  test_file=""
  case "$file" in
    *.ts)    test_file="${file%.ts}.test.ts" ;;
    *.js)    test_file="${file%.js}.test.js" ;;
    *.svelte) test_file="${file%.svelte}.test.ts" ;;
  esac

  # Also check for mirrored tests/ directory pattern
  mirrored_test_file=""
  if [[ "$file" == src/* ]]; then
    # Convert src/lib/parser.ts -> tests/lib/parser.test.ts
    relative_path="${file#src/}"
    case "$file" in
      *.ts)    mirrored_test_file="tests/${relative_path%.ts}.test.ts" ;;
      *.js)    mirrored_test_file="tests/${relative_path%.js}.test.js" ;;
      *.svelte) mirrored_test_file="tests/${relative_path%.svelte}.test.ts" ;;
    esac
  fi

  # Check if file has testable exports (not just types/interfaces)
  # Skip files that only export types, interfaces, or type aliases
  has_runtime_export=false
  if grep -q "export" "$file" 2>/dev/null; then
    # Check for runtime exports (functions, classes, const, let, var, default)
    if grep -E "export\s+(async\s+)?function|export\s+class|export\s+(const|let|var)|export\s+default|export\s*\{" "$file" 2>/dev/null | grep -v -E "export\s+type\s|export\s+interface\s" >/dev/null; then
      has_runtime_export=true
    fi
  fi

  if [ "$has_runtime_export" = true ]; then
    # Check if test file exists in EITHER location
    has_test=false
    [ -n "$test_file" ] && [ -f "$test_file" ] && has_test=true
    [ -n "$mirrored_test_file" ] && [ -f "$mirrored_test_file" ] && has_test=true

    if [ "$has_test" = false ]; then
      UNTESTED_FILES+=("$file")
    fi
  fi
done <<< "$SOURCE_FILES"

# Report untested files
if [ ${#UNTESTED_FILES[@]} -gt 0 ]; then
  echo ""
  echo "⚠️  Found ${#UNTESTED_FILES[@]} file(s) without tests:"
  for file in "${UNTESTED_FILES[@]}"; do
    echo "  • $file"
  done
  echo ""
  echo "Recommendation: Add tests before pushing"
  echo ""

  read -p "Continue anyway? (y/n) " -n 1 -r
  echo ""

  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "✓ Push cancelled"
    exit 1
  fi
  echo ""
fi

# Detect test runner
TEST_CMD=""

# Check for bun (prioritize if available)
if command -v bun &> /dev/null; then
  # Bun is installed, prefer it
  if [ -f "bun.lockb" ] || [ -f "bun.lock" ] || [ -f "bunfig.toml" ]; then
    TEST_CMD="bun test"
  # Also check package.json for bun usage
  elif grep -q '"bun"' package.json 2>/dev/null; then
    TEST_CMD="bun test"
  fi
fi

# Fall back to other package managers if bun not detected
if [ -z "$TEST_CMD" ]; then
  if [ -f "deno.lock" ] || [ -f "deno.json" ]; then
    TEST_CMD="deno test"
  elif [ -f "package.json" ]; then
    if [ -f "package-lock.json" ]; then
      TEST_CMD="npm test"
    elif [ -f "pnpm-lock.yaml" ]; then
      TEST_CMD="pnpm test"
    elif [ -f "yarn.lock" ]; then
      TEST_CMD="yarn test"
    else
      TEST_CMD="npm test"
    fi
  fi
fi

# Run tests if test command exists
if [ -n "$TEST_CMD" ]; then
  echo "🧪 Running tests with: $TEST_CMD"
  echo ""

  if $TEST_CMD; then
    echo ""
    echo "✅ All tests passed"
    exit 0
  else
    echo ""
    echo "❌ Tests failed"
    echo ""

    read -p "Push anyway? (y/n) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
      echo "⚠️  Pushing despite test failures"
      exit 0
    else
      echo "✓ Push cancelled"
      exit 1
    fi
  fi
else
  echo "✓ No test command found, skipping tests"
  exit 0
fi
