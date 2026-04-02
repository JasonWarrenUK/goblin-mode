#!/bin/zsh

# Portfolio Evidence Extraction Hook - Batched Pre-Push
# Trigger: pre-push
# Analyzes ALL commits being pushed in a SINGLE Claude call

set -e

EVIDENCE_LOG="$HOME/.claude/docs/evidence-tracker.md"
PROJECT_ROOT=$(git rev-parse --show-toplevel)
PROJECT_NAME=$(basename "$PROJECT_ROOT")

# Read push info from stdin
while read local_ref local_sha remote_ref remote_sha; do
  # Skip deletes
  if [ "$local_sha" = "0000000000000000000000000000000000000000" ]; then
    continue
  fi

  # Determine commit range
  if [ "$remote_sha" = "0000000000000000000000000000000000000000" ]; then
    # New branch - get all commits not on remote
    COMMIT_RANGE="$local_sha --not --remotes"
  else
    COMMIT_RANGE="$remote_sha..$local_sha"
  fi

  # Get all commits being pushed
  COMMITS=$(git rev-list $COMMIT_RANGE 2>/dev/null || echo "")

  if [ -z "$COMMITS" ]; then
    echo "📝 No new commits to analyze"
    exit 0
  fi

  COMMIT_COUNT=$(echo "$COMMITS" | wc -l | tr -d ' ')
  echo "🔍 Scanning $COMMIT_COUNT commit(s) for KSB evidence..."

  # Gather all commit data
  ALL_DIFFS=""
  ALL_MESSAGES=""
  ALL_FILES=""
  COMMIT_SUMMARIES=""

  for commit in $COMMITS; do
    COMMIT_SHORT=$(git rev-parse --short $commit)
    COMMIT_MSG=$(git log -1 --pretty=%B $commit)
    COMMIT_MSG_FIRST=$(echo "$COMMIT_MSG" | head -n1)
    COMMIT_FILES=$(git diff-tree --no-commit-id --name-only -r $commit)
    COMMIT_DIFF=$(git show $commit --stat)

    ALL_MESSAGES="$ALL_MESSAGES
$COMMIT_MSG"
    ALL_FILES="$ALL_FILES
$COMMIT_FILES"
    ALL_DIFFS="$ALL_DIFFS

--- Commit $COMMIT_SHORT: $COMMIT_MSG_FIRST ---
$COMMIT_DIFF"

    COMMIT_SUMMARIES="$COMMIT_SUMMARIES
- $COMMIT_SHORT: $COMMIT_MSG_FIRST"
  done

  # Get full diff for the entire range (more useful for analysis)
  if [ "$remote_sha" != "0000000000000000000000000000000000000000" ]; then
    FULL_DIFF=$(git diff $remote_sha..$local_sha)
  else
    FULL_DIFF=$(git show $local_sha)
  fi

  # Initialize evidence log if needed
  if [ ! -f "$EVIDENCE_LOG" ]; then
    mkdir -p "$(dirname "$EVIDENCE_LOG")"
    cat > "$EVIDENCE_LOG" << 'EOF'
# Project Evidence Tracker

## KSB Index

### Knowledge

### Skills

### Behaviours

---

## Evidence Journal

EOF
  fi

  # PHASE 1: Keyword Scan (across ALL commits)
  SEARCH_TEXT="$ALL_DIFFS $ALL_MESSAGES $ALL_FILES"
  POTENTIAL_EVIDENCE=false

  # Knowledge triggers
  echo "$SEARCH_TEXT" | grep -qiE "role\.in|responsibilit|sole\.developer|one\.person|wearing\.multiple|future\.maintainer|bus\.factor" && POTENTIAL_EVIDENCE=true
  echo "$SEARCH_TEXT" | grep -qiE "pair\.programm|code\.review|pull\.request|pr\.review|standup|retrospective|consensus|knowledge\.shar|collaborated|professional\.practice" && POTENTIAL_EVIDENCE=true
  echo "$SEARCH_TEXT" | grep -qiE "algorithm|complexity|big\.o|optimize|array|nested|object\.manipulation|deep\.copy|json|linked\.list|binary\.tree|hash\.table|sorting|dynamic\.programming|memoization|recursion|race\.condition" && POTENTIAL_EVIDENCE=true
  echo "$SEARCH_TEXT" | grep -qiE "design\.document|design\.spec|specification|architecture\.diagram|uml|wireframe|mockup|api\.spec|openapi|swagger|acceptance\.criteria|user\.story|technical\.spec" && POTENTIAL_EVIDENCE=true

  # Skills triggers
  echo "$SEARCH_TEXT" | grep -qiE "refactor|clean\.code|code\.cleanup|readability|self\.document|descriptive|code\.smell|duplicate|magic\.number|dry|single\.responsibility|separation\.of\.concerns|decouple|modular|maintainable|extensible" && POTENTIAL_EVIDENCE=true
  echo "$SEARCH_TEXT" | grep -qiE "unit\.test|test\.spec|\.test\.|\.spec\.|jest|vitest|mocha|assert|expect|describe|mock|coverage|tdd|test\.driven|arrange\.act\.assert|given\.when\.then" && POTENTIAL_EVIDENCE=true
  echo "$SEARCH_TEXT" | grep -qiE "test\.scenario|test\.case|edge\.case|boundary|happy\.path|sad\.path|invalid\.input|integration\.test|e2e|acceptance\.test|regression|exploratory" && POTENTIAL_EVIDENCE=true
  echo "$SEARCH_TEXT" | grep -qiE "debug|debugger|breakpoint|stack\.trace|root\.cause|reproduce|isolate|troubleshoot|hot\.fix|bug\.fix|control\.flow|static\.analysis" && POTENTIAL_EVIDENCE=true
  echo "$SEARCH_TEXT" | grep -qiE "build\.system|build\.pipeline|compile|bundle|deploy|ci\.cd|github\.actions|gitlab\.ci|docker|kubernetes|helm|artifact|npm\.publish|environment\.variable|staging|production|release|version\.bump" && POTENTIAL_EVIDENCE=true
  echo "$SEARCH_TEXT" | grep -qiE "object\.oriented|oop|inheritance|polymorphism|encapsulation|event\.driven|event\.sourcing|reactive|functional\.programming|pure\.function|immutability|design\.pattern|factory|singleton|observer|mvc|mvvm" && POTENTIAL_EVIDENCE=true
  echo "$SEARCH_TEXT" | grep -qiE "implement\.spec|implement\.design|per\.spec|as\.specified|according\.to|follows\.design|adheres\.to|conforms\.to|meets\.requirement|satisfies|matches\.design|acceptance\.criteria\.met|wireframe\.implemented|api\.contract" && POTENTIAL_EVIDENCE=true

  # Behaviours triggers
  echo "$SEARCH_TEXT" | grep -qiE "reasoning|rationale|justification|justify|therefore|trade\.off|pros\.and\.cons|evaluate|compare\.approaches|alternative|better\.than|chosen\.over|decision\.based|logical" && POTENTIAL_EVIDENCE=true
  echo "$SEARCH_TEXT" | grep -qiE "security|encrypt|hash\.password|authentication|authorization|access\.control|csrf|xss|sql\.injection|sanitization|vulnerability|https|secret\.management|gitignore|changelog|licensing|meaningful\.commit|branch\.naming" && POTENTIAL_EVIDENCE=true

  if [ "$POTENTIAL_EVIDENCE" = false ]; then
    echo ""
    echo "✓ Pre-push evidence hook completed"
    echo "  Commits scanned: $COMMIT_COUNT"
    echo "  KSB patterns found: none"
    echo ""
    exit 0
  fi

  # PHASE 2: Single AI Analysis for ALL commits
  echo "🤖 Analyzing $COMMIT_COUNT commit(s) with Claude AI (batched)..."

  PUSH_DATE=$(date +%Y-%m-%d)
  BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)

  PROMPT_FILE=$(mktemp)
  cat > "$PROMPT_FILE" << 'PROMPTEOF'
You are analyzing a BATCH of git commits for Level 4 Software Development Apprenticeship evidence.

**CRITICAL**: Only analyze AM1 KSBs (Assessment Method 1: Project Report). Do NOT analyze AM2 KSBs.

## AM1 KSBs ONLY

### Knowledge
- **K2**: Roles and responsibilities within SDLC
- **K6**: How teams work effectively to produce software
- **K9**: Principles of algorithms, logic, and data structures
- **K11**: Software designs and functional/technical specifications

### Skills
- **S1**: Create logical and maintainable code
- **S4**: Test code and analyze results using unit testing
- **S6**: Identify and create test scenarios
- **S7**: Apply structured techniques to problem solving, debug code
- **S10**: Build, manage, and deploy code into relevant environment
- **S11**: Apply appropriate software development approach
- **S12**: Follow software designs and functional/technical specifications
- **S16**: Apply algorithms, logic, and data structures

### Behaviours
- **B2**: Applies logical thinking
- **B3**: Maintains productive, professional, and secure working environment

## Commits to Analyze

PROMPTEOF

  cat >> "$PROMPT_FILE" << COMMITEOF
**Project**: $PROJECT_NAME
**Branch**: $BRANCH_NAME
**Date**: $PUSH_DATE
**Commits in this push**:
$COMMIT_SUMMARIES

**Combined Code Changes**:
\`\`\`diff
$FULL_DIFF
\`\`\`

COMMITEOF

  cat >> "$PROMPT_FILE" << 'INSTRUCTEOF'

## Analysis Task

Analyze ALL commits together as a body of work. Return ONLY a valid JSON object:

```json
{
  "detected_ksbs": ["K9", "S1"],
  "confidence": "high",
  "evidence": {
    "K9": "Implements binary search algorithm with O(log n) complexity...",
    "S1": "Refactored code for readability: extracted method, descriptive names..."
  },
  "methodology_notes": "Technical reasoning about approach taken...",
  "commits_analyzed": 5,
  "next_steps": [
    "Add unit tests for edge cases",
    "Document algorithm choice in ADR"
  ]
}
```

## Rules

1. **Only include KSBs with CLEAR, SPECIFIC evidence** across these commits
2. **Be TECHNICAL and SPECIFIC**: Cite specific code changes, patterns, algorithms
3. **Consider the commits as a whole** - look for patterns across the work
4. **Confidence levels**: "high" (explicit), "medium" (reasonable inference), "low" (circumstantial)
5. **Return ONLY valid JSON** - no preamble, no markdown formatting
6. **If NO KSBs demonstrated**: `{"detected_ksbs": [], "confidence": "none", "evidence": {}, "commits_analyzed": N}`

Now analyze the commits above.
INSTRUCTEOF

  ANALYSIS=$(claude --print < "$PROMPT_FILE" 2>/dev/null || echo '{"detected_ksbs": [], "confidence": "error", "evidence": {}}')
  rm "$PROMPT_FILE"

  # Strip markdown code fences if present
  ANALYSIS_CLEAN=$(echo "$ANALYSIS" | sed -n '/^```json$/,/^```$/p' | sed '1d;$d')
  if [ -z "$ANALYSIS_CLEAN" ]; then
    ANALYSIS_CLEAN="$ANALYSIS"
  fi

  DETECTED=$(echo "$ANALYSIS_CLEAN" | grep -o '"detected_ksbs"[^]]*]' | grep -o 'K[0-9]\+\|S[0-9]\+\|B[0-9]\+' | tr '\n' ' ' | xargs)

  if [ -z "$DETECTED" ]; then
    echo "🤖 AI analysis: No clear KSB evidence found in $COMMIT_COUNT commit(s)"
    exit 0
  fi

  CONFIDENCE=$(echo "$ANALYSIS_CLEAN" | grep -o '"confidence"[^"]*"[^"]*"' | cut -d'"' -f4)

  # Create entry
  FIRST_COMMIT=$(echo "$COMMITS" | tail -1 | xargs git rev-parse --short)
  LAST_COMMIT=$(echo "$COMMITS" | head -1 | xargs git rev-parse --short)
  ENTRY_ID="$PUSH_DATE-$FIRST_COMMIT-$LAST_COMMIT"

  cat >> "$EVIDENCE_LOG" << ENTRYEOF

### $PUSH_DATE - Push: $COMMIT_COUNT commits ($FIRST_COMMIT..$LAST_COMMIT)

**Project**: $PROJECT_NAME
**Branch**: \`$BRANCH_NAME\`
**Commits**:
$COMMIT_SUMMARIES

**AI-Detected KSBs** (Confidence: $CONFIDENCE):
ENTRYEOF

  # Extract and add evidence
  echo "$ANALYSIS_CLEAN" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for ksb, evidence in data.get('evidence', {}).items():
        print(f'- **{ksb}**: {evidence}')
except:
    pass
" >> "$EVIDENCE_LOG" 2>/dev/null || {
    for ksb in $DETECTED; do
      echo "- **$ksb**: [Evidence from AI analysis]" >> "$EVIDENCE_LOG"
    done
  }

  METHODOLOGY=$(echo "$ANALYSIS_CLEAN" | grep -o '"methodology_notes"[^"]*"[^"]*"' | sed 's/"methodology_notes"[^"]*"//' | tr -d '"')
  if [ -n "$METHODOLOGY" ]; then
    echo "" >> "$EVIDENCE_LOG"
    echo "**Methodology Notes**: $METHODOLOGY" >> "$EVIDENCE_LOG"
  fi

  echo "" >> "$EVIDENCE_LOG"
  echo "**Next Steps**:" >> "$EVIDENCE_LOG"
  echo "$ANALYSIS_CLEAN" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for step in data.get('next_steps', []):
        print(f'- {step}')
except:
    print('- Review and refine evidence manually')
" >> "$EVIDENCE_LOG" 2>/dev/null || echo "- Review and refine evidence manually" >> "$EVIDENCE_LOG"

  cat >> "$EVIDENCE_LOG" << 'ENTRYEOF'

---
ENTRYEOF

  # Update KSB Index
  for ksb in $DETECTED; do
    case "$ksb" in
      K2) DESC="Roles and Responsibilities within SDLC" ;;
      K6) DESC="How Teams Work Effectively" ;;
      K9) DESC="Algorithms, Logic, and Data Structures" ;;
      K11) DESC="Software Designs and Specifications" ;;
      S1) DESC="Create Logical and Maintainable Code" ;;
      S4) DESC="Test Code Using Unit Testing" ;;
      S6) DESC="Identify and Create Test Scenarios" ;;
      S7) DESC="Problem Solving and Debugging" ;;
      S10) DESC="Build, Manage, and Deploy Code" ;;
      S11) DESC="Apply Software Development Approach" ;;
      S12) DESC="Follow Software Designs and Specifications" ;;
      S16) DESC="Apply Algorithms, Logic, and Data Structures" ;;
      B2) DESC="Applies Logical Thinking" ;;
      B3) DESC="Productive, Professional, and Secure Environment" ;;
      *) DESC="Unknown KSB" ;;
    esac

    case "$ksb" in
      K*) SECTION="### Knowledge" ;;
      S*) SECTION="### Skills" ;;
      B*) SECTION="### Behaviours" ;;
    esac

    if ! grep -q "^#### $ksb - " "$EVIDENCE_LOG"; then
      TMPFILE=$(mktemp)
      added=false
      while IFS= read -r line; do
        echo "$line"
        if [ "$line" = "$SECTION" ] && [ "$added" = false ]; then
          echo ""
          echo "#### $ksb - $DESC"
          echo ""
          added=true
        fi
      done < "$EVIDENCE_LOG" > "$TMPFILE"
      mv "$TMPFILE" "$EVIDENCE_LOG"
    fi

    LINK="- [$PUSH_DATE - $COMMIT_COUNT commits on $BRANCH_NAME](#$ENTRY_ID)"
    TMPFILE=$(mktemp)
    found=false
    while IFS= read -r line; do
      echo "$line"
      if [[ "$line" == "#### $ksb - "* ]] && [ "$found" = false ]; then
        echo "$LINK"
        found=true
      fi
    done < "$EVIDENCE_LOG" > "$TMPFILE"
    mv "$TMPFILE" "$EVIDENCE_LOG"
  done

  echo ""
  echo "✅ Evidence extracted (batched analysis):"
  echo "   Project: $PROJECT_NAME"
  echo "   Commits: $COMMIT_COUNT ($FIRST_COMMIT..$LAST_COMMIT)"
  echo "   KSBs detected: $DETECTED"
  echo "   Confidence: $CONFIDENCE"
  echo ""
  echo "   Saved to: $EVIDENCE_LOG"
  echo ""
  echo "⚠️  Review and refine evidence before using in portfolio"

done

exit 0
