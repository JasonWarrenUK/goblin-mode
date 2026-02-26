# CLI Tools Usage Guide
> **Created:** 2026-01-08  
> **For:** Jason Warren - Level 4 Software Developer Apprentice  
> **Purpose:** Comprehensive guide to using installed CLI tools in powerful combinations

---

## Philosophy: Tools Work Together

The real power isn't individual tools - it's **combinations**. Each tool does one thing well, and they pipe together into workflows that are greater than the sum of their parts.

**Installed tools:**
1. fzf - Fuzzy finder (foundation for interactive selection)
2. ripgrep (rg) - Fast search (replaces grep, also handles TODOs)
3. bat - Better cat (syntax highlighting)
4. jq - JSON processor
5. fd - Modern find (respects .gitignore)
6. tokei - Code statistics
7. axe-cli - Accessibility testing
8. svu - Semantic version utility
9. vacuum - OpenAPI linter
10. pake - Web→desktop app wrapper
11. degit - Project scaffolding
12. go - Go language (for other tools)

---

## Part 1: The Core Quartet (fzf + fd + ripgrep + bat)

These four tools form the foundation of everything else.

### 1.1: Interactive File Finder (fzf + fd + bat)

**The Pattern:** Find files interactively with live preview.

```bash
# Basic: Find and preview any file
fd --type f | fzf --preview 'bat --color=always {}'

# Press Ctrl-/ to toggle preview on/off
# Arrow keys to navigate
# Enter to select (prints filename)
```

**Permanent aliases (see zshrc additions file):**
- `preview` - Interactive file finder with preview
- `fe` - Find and edit
- `fts` - Find TypeScript/Svelte files only
- `fdir <directory>` - Find in specific directory

**Real usage in YOUR projects:**

```bash
# Find any file in Rhea
cd ~/Code/rhea
preview

# Find only Svelte components
fts

# Find in src/ directory only
fdir src/
```

---

### 1.2: Content Search (ripgrep + fzf + bat)

**The Pattern:** Search code, fuzzy-select result, view in context.

```bash
# Search for pattern, interactively select result
rg "useState" --line-number --no-heading --color=always | \
  fzf --ansi --preview 'bat --color=always {1} --highlight-line {2}' --delimiter=:

# Breaking down the command:
# rg "pattern" --line-number    # Search with line numbers
# --no-heading                   # Don't group by file
# --color=always                 # Keep syntax colors
# | fzf --ansi                   # Fuzzy select (preserve colors)
# --preview 'bat {1} --highlight-line {2}'  # Preview file, highlight match line
# --delimiter=:                  # Split on : to get file and line number
```

**Permanent aliases:**
- `rgi <pattern>` - Interactive ripgrep (search and preview)
- `rgts <pattern>` - Search TypeScript/Svelte only
- `rge <pattern>` - Search and edit

**Real usage:**

```bash
cd ~/Code/rhea

# Find all uses of "useState"
rgi "useState"

# Find all imports from Supabase
rgi "from.*supabase"

# Find and edit a TODO
rge "TODO"

# Search only in TypeScript
rgts "interface Course"
```

---

### 1.3: TODO Tracking (ripgrep)

Since we replaced tickgit with ripgrep, here's the complete TODO workflow:

**Permanent aliases:**
- `todos` - Find all TODOs with context
- `todosCount` - Count TODOs
- `todosByType` - TODOs sorted by type
- `todosIn <path>` - TODOs in specific files
- `todosi` - Interactive TODO finder

**Real usage:**

```bash
cd ~/Code/rhea

# See all TODOs
todos

# Count them
todosCount

# Interactive - find and view TODOs
todosi

# TODOs in components only
todosIn src/lib/components/

# Export TODOs to file for tracking
todos > ~/portfolio-evidence/rhea-todos-$(date +%Y-%m-%d).txt
```

---

## Part 2: Git Workflow Integration (svu + LazyGit)

### 2.1: Semantic Versioning with svu

**The Pattern:** Let git commits determine version numbers automatically.

**Setup conventional commits:**

```bash
# Your commit messages should follow this format:
# - fix: ...        → patch bump (0.1.0 → 0.1.1)
# - feat: ...       → minor bump (0.1.0 → 0.2.0)  
# - feat!: ...      → major bump (0.1.0 → 1.0.0)
# - BREAKING CHANGE → major bump (0.1.0 → 1.0.0)
```

**Permanent aliases:**
- `vnext` - Show next version
- `vcurrent` - Show current version
- `gtag` - Create tag with next version
- `vhistory` - Show version history

**Workflow example:**

```bash
cd ~/Code/rhea

# Check current version
vcurrent
# Output: v0.2.3

# See what next version will be
vnext
# Output: v0.2.4 (if last commit was "fix: ...")
# Output: v0.3.0 (if last commit was "feat: ...")

# Make changes
git add .
git commit -m "feat: add course difficulty levels"

# Check next version (should be minor bump)
vnext
# Output: v0.3.0

# Create and push tag
gtag
# Creates v0.3.0, pushes to origin

# See version history
vhistory
```

---

### 2.2: LazyGit + svu Integration

**Add custom command to LazyGit:**

```yaml
# ~/.config/lazygit/config.yml

customCommands:
  - key: 'T'
    description: 'Create next semantic version tag'
    command: 'git tag $(svu next) && git push --tags'
    context: 'global'
    loadingText: 'Creating tag...'
    
  - key: 'V'
    description: 'Show next version'
    command: 'svu next'
    context: 'global'
    subprocess: true
    
  - key: 'shift+V'
    description: 'Show current version'
    command: 'svu current'
    context: 'global'
    subprocess: true
```

**LazyGit workflow:**

1. Open LazyGit: `lazygit`
2. Stage changes, commit with conventional format
3. Press `V` to see what next version will be
4. Press `T` to create and push tag
5. Press `Shift+V` to confirm current version

---

## Part 3: Project Intelligence (tokei + jq)

### 3.1: Code Statistics (tokei)

**The Pattern:** Gather metrics for portfolio evidence.

**Permanent aliases:**
- `stats` - Quick stats
- `statsJson <project>` - Detailed stats with JSON output
- `statsAll` - Compare project sizes
- `statsPortfolio` - Portfolio evidence stats

**Real usage:**

```bash
# Quick stats for current project
cd ~/Code/rhea
stats

# Get JSON for processing
statsJson | jq '.TypeScript.code'

# Compare all your projects
statsAll

# Generate portfolio evidence
statsPortfolio
```

**For AM2 Portfolio:**

```bash
# Generate comprehensive evidence
cd ~/Code/rhea
tokei --output json > ~/portfolio-evidence/rhea-metrics.json

# Extract specific metrics with jq
cat ~/portfolio-evidence/rhea-metrics.json | jq '{
  total_lines: .Total.code,
  typescript_lines: .TypeScript.code,
  svelte_lines: .Svelte.code,
  files: .Total.inaccurate
}'
```

---

### 3.2: Package Dependencies (jq)

**The Pattern:** Analyze and compare dependencies across projects.

**Permanent aliases:**
- `deps` - List all dependencies
- `devdeps` - List dev dependencies
- `depVersion <dep>` - Check specific dependency version
- `depsCompare <proj1> <proj2>` - Compare dependencies between projects
- `findPackageUsage <package>` - Find which projects use a specific package

**Real usage:**

```bash
cd ~/Code/rhea

# See all dependencies
deps

# Check SvelteKit version
depVersion "@sveltejs/kit"

# Compare Rhea and Iris dependencies
depsCompare ~/Code/rhea ~/Code/iris

# Find which projects use Supabase
findPackageUsage "@supabase/supabase-js"

# Extract TypeScript config
jq '.compilerOptions' tsconfig.json

# See all scripts
jq '.scripts' package.json
```

---

## Part 4: Accessibility Testing (axe-cli)

### 4.1: Local Development Testing

**The Pattern:** Test accessibility during development, before deployment.

**Permanent aliases:**
- `axeLocal <port>` - Test local dev server
- `axeRoute <port> <route>` - Test specific routes
- `axeRoutes <port>` - Test all major routes

**Real workflow:**

```bash
cd ~/Code/rhea

# Start dev server
npm run dev &  # or bun dev &

# Wait for server to start
sleep 3

# Test accessibility
axeLocal

# Test specific page
axeRoute 5173 /courses

# Test all routes
axeRoutes 5173

# Kill dev server
kill %1
```

**For portfolio evidence:**

```bash
# Generate accessibility report for AM2
cd ~/Code/rhea
npm run dev &
sleep 5
axe http://localhost:5173 --save ~/portfolio-evidence/rhea-accessibility-$(date +%Y-%m-%d).json
kill %1

# Include in work record or ADR
echo "## Accessibility Testing" >> docs/work-record.md
echo "Tested with axe-cli on $(date +%Y-%m-%d)" >> docs/work-record.md
echo "Results: ~/portfolio-evidence/rhea-accessibility-$(date +%Y-%m-%d).json" >> docs/work-record.md
```

---

## Part 5: Project Scaffolding (degit + pake)

### 5.1: Quick Experiments (degit)

**The Pattern:** Start experiments fast with templates, no git history bloat.

**Permanent aliases:**
- `svelteStart <name>` - Quick Svelte starter
- `svelteKitStart <name>` - SvelteKit starter
- `myTemplate <name> <template>` - Clone from your own template

**Real usage:**

```bash
# Quick Svelte experiment
svelteStart test-idea
cd test-idea
npm run dev

# Try SvelteKit
svelteKitStart test-kit

# Use official templates
degit sveltejs/template#typescript my-ts-app
```

---

### 5.2: Web to Desktop (pake)

**The Pattern:** Wrap web apps as native desktop apps for testing/learning.

**Permanent aliases:**
- `desktop <url> <name>` - Quick desktop wrapper
- `desktopLocal <name> <port>` - Wrap local dev server

**Real usage for Iris learning:**

```bash
# Wrap a web app to see how desktop versions work
desktop https://claude.ai Claude

# Test Rhea as desktop app
cd ~/Code/rhea
npm run dev &
sleep 3
desktopLocal Rhea 5173

# This creates Rhea.app
# Open it, explore how it feels as desktop app
# Learn from this for Iris (Tauri) project

kill %1
```

---

## Part 6: Daily Workflows

### 6.1: Morning Standup

**Complete status check across all projects.**

**Permanent alias:**
- `standup` - Morning standup check

**Usage:**

```bash
# Every morning
standup

# Output shows:
# - Current branch for each project
# - Uncommitted changes count  
# - Last commit info
# - TODO count
```

---

### 6.2: End of Day Cleanup

**Ensure everything is committed and pushed.**

**Permanent alias:**
- `eod` - End of day check

**Usage:**

```bash
# Before logging off
eod

# Shows any:
# - Uncommitted changes
# - Unpushed commits
# - Projects needing attention
```

---

### 6.3: Weekly Portfolio Evidence

**Generate comprehensive portfolio stats weekly.**

**Permanent alias:**
- `portfolioWeekly` - Weekly portfolio report

**Usage:**

```bash
# Every Friday
portfolioWeekly

# Generates markdown report with:
# - Code stats per project
# - Git activity last 7 days
# - TODO counts
# - Saves to ~/portfolio-evidence/weekly/
```

---

## Part 7: Project-Specific Workflows

### 7.1: Rhea (Svelte/LangChain Curriculum Generator)

**Complete development workflow:**

```bash
cd ~/Code/rhea

# Morning: Check status
git status
vcurrent           # Current version
todos              # Any TODOs

# Development: Find and edit
rgi "CourseGenerator"     # Find usage
fe                        # Find and edit component

# Testing: Accessibility
npm run dev &
sleep 3
axeLocal
kill %1

# Commit: Conventional commit
git add .
git commit -m "feat: add course difficulty selection"

# Version: Check and tag
vnext              # See next version
gtag               # Create and push tag

# Or use LazyGit:
lazygit
# Press V to see next version
# Press T to create tag
```

---

### 7.2: Iris (Tauri ILR File Creator Replacement)

**Project setup and development:**

```bash
cd ~/Code/iris

# Morning: Status check
standup            # Full project status

# Research: Compare with old implementation
cd ~/Code/ilr-file-creator
rgi "semantic validation"
cd ~/Code/iris

# Development: Find Tauri patterns
rgi "tauri::"
rgi "invoke"

# Learning: Try pake for desktop feel
desktop http://localhost:1420 IrisTest

# Stats: Track progress
stats
statsJson | jq '.Rust.code'  # Rust lines
statsJson | jq '.TypeScript.code'  # TypeScript lines

# Portfolio evidence
statsPortfolio
```

---

### 7.3: Things We Do (Next.js/RxDB)

**Database and state management:**

```bash
cd ~/Code/things-we-do

# Find RxDB patterns
rgi "RxDB"
rgi "collection"

# Check dependencies
deps | jq 'keys'
depVersion "rxdb"

# Find all state management
rgi "useState|useReducer|useStore"

# Compare with Rhea's approach
depsCompare ~/Code/things-we-do ~/Code/rhea
```

---

## Part 8: Advanced Combinations

### 8.1: The Ultimate Search

**Combine everything for maximum power:**

**Permanent aliases:**
- `ultimate <pattern>` - Find anything (name OR content)
- `searchAll <pattern>` - Search across all projects

**Usage:**

```bash
# Find anything containing "supabase"
ultimate supabase

# Search all projects
searchAll "useState"
searchAll "TODO"
```

---

### 8.2: Git History Explorer

**Navigate git history visually:**

**Permanent aliases:**
- `gitLog` - Interactive git log with preview
- `gitBlame <file>` - Find when a line was changed

**Usage:**

```bash
cd ~/Code/rhea

# Browse git history interactively
gitLog

# See when a line was changed
gitBlame src/App.svelte
```

---

## Summary: Your Enhanced Workflow

**Daily routine:**
```bash
# Morning
standup                    # Check all projects
cd ~/Code/rhea
todos                      # Check TODOs

# Development
preview                    # Find files
rgi "pattern"              # Search code
fe                         # Edit quickly

# Committing
git add .
git commit -m "feat: ..."
vnext                      # Check version
gtag                       # Tag and push

# Evening
eod                        # Check uncommitted work
```

**Weekly routine:**
```bash
portfolioWeekly           # Generate evidence
statsAll                   # Compare projects
searchAll "TODO"          # Technical debt review
```

---

## Quick Reference: All Aliases

### File Finding
- `preview` - Interactive file finder with preview
- `fe` - Find and edit
- `fts` - Find TypeScript/Svelte files
- `fdir <dir>` - Find in specific directory

### Code Search
- `rgi <pattern>` - Interactive ripgrep
- `rgts <pattern>` - Search TypeScript/Svelte
- `rge <pattern>` - Search and edit
- `todos` - Find all TODOs
- `todosCount` - Count TODOs
- `todosi` - Interactive TODO finder

### Git & Versioning
- `vcurrent` - Show current version
- `vnext` - Show next version
- `gtag` - Create and push tag
- `vhistory` - Show version history
- `gitLog` - Interactive git log
- `gitBlame <file>` - Interactive git blame

### Project Intelligence
- `stats` - Code statistics
- `statsAll` - Compare all projects
- `statsPortfolio` - Portfolio evidence
- `deps` - List dependencies
- `depVersion <dep>` - Check version
- `depsCompare <p1> <p2>` - Compare dependencies

### Testing
- `axeLocal <port>` - Test accessibility
- `axeRoute <port> <route>` - Test route
- `axeRoutes <port>` - Test all routes

### Scaffolding
- `svelteStart <name>` - Svelte starter
- `svelteKitStart <name>` - SvelteKit starter
- `desktop <url> <name>` - Web→desktop

### Daily Workflows
- `standup` - Morning check
- `eod` - End of day check
- `portfolioWeekly` - Weekly report

### Advanced
- `ultimate <pattern>` - Ultimate search
- `searchAll <pattern>` - Search all projects

---

## Installation

All aliases and functions are in: `~/.claude/docs/cli-tools-zshrc-additions.sh`

To install:
```bash
# Review the file first
bat ~/.claude/docs/cli-tools-zshrc-additions.sh

# Add to your .zshrc
cat ~/.claude/docs/cli-tools-zshrc-additions.sh >> ~/.zshrc

# Reload
source ~/.zshrc
```

---

**Created:** 2026-01-08  
**Last Updated:** 2026-01-08  
**Location:** `~/.claude/docs/cli-tools-usage-guide.md`
