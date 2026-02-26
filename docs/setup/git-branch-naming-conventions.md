# Git Branch Naming Conventions

> **Created**: 2026-01-06  
> **Purpose**: Standardized branch naming strategy for consistent, scannable git workflows

---

## Structure

```
<prefix>/<short-description>
```

**Rules**:
- All lowercase
- Hyphens between words (no underscores or spaces)
- Imperative mood: `add-feature`, not `adds-feature` or `adding-feature`
- Descriptive but concise: `feat/calculate-user-stats` not `feat/stats`
- No ticket numbers (not using GitHub issues)

---

## Branch Prefixes

### Core Development

| Prefix | Purpose | Examples |
|--------|---------|----------|
| `feat/` | New features (user-facing or API) | `feat/add-user-dashboard`<br>`feat/implement-search` |
| `enhance/` | Improvements to existing features (not bugs) | `enhance/improve-search-speed`<br>`enhance/add-sorting-options` |
| `fix/` | Bug fixes | `fix/correctly-render-button`<br>`fix/handle-null-user` |
| `hotfix/` | Critical production fixes | `hotfix/patch-security-vulnerability`<br>`hotfix/restore-payment-flow` |

### Code Quality

| Prefix | Purpose | Examples |
|--------|---------|----------|
| `refactor/` | Code restructuring (no behaviour change) | `refactor/extract-auth-logic`<br>`refactor/simplify-validation` |
| `types/` | Type definitions (interfaces, types, contracts) | `types/add-api-response-types`<br>`types/define-user-interfaces` |
| `perf/` | Performance improvements | `perf/optimize-graph-rendering`<br>`perf/lazy-load-images` |
| `test/` | Adding/updating tests | `test/add-auth-integration-tests`<br>`test/increase-coverage` |
| `debug/` | Debugging/investigation branches (temporary) | `debug/investigate-memory-leak`<br>`debug/trace-render-issue` |

### Documentation & Content

| Prefix | Purpose | Examples |
|--------|---------|----------|
| `docs/` | Documentation changes | `docs/update-api-reference`<br>`docs/add-setup-guide` |
| `content/` | Content updates (copy, text, data files) | `content/update-landing-page-copy`<br>`content/add-curriculum-data` |

### Styling & UI

| Prefix | Purpose | Examples |
|--------|---------|----------|
| `styles/` | Visual styling (colors, fonts, spacing) | `styles/update-color-palette`<br>`styles/increase-button-padding` |
| `layout/` | Structural positioning (grid, flexbox, responsive) | `layout/make-sidebar-responsive`<br>`layout/switch-to-grid` |
| `a11y/` | Accessibility improvements | `a11y/add-aria-labels`<br>`a11y/improve-keyboard-navigation` |

### Dependencies & Configuration

| Prefix | Purpose | Examples |
|--------|---------|----------|
| `deps/` | Dependency updates | `deps/upgrade-svelte-5`<br>`deps/update-all-packages` |
| `build/` | Build system, bundler, tooling | `build/configure-vite`<br>`build/add-source-maps` |
| `config/` | Configuration files (non-Claude) | `config/update-prettier-rules`<br>`config/add-eslint-plugin` |
| `agents/` | Claude Code configuration | `agents/add-testing-workflow`<br>`agents/update-global-claude-md` |
| `chore/` | Maintenance tasks (cleanup, file moves) | `chore/remove-unused-files`<br>`chore/organize-imports` |

### CI/CD & DevOps

| Prefix | Purpose | Examples |
|--------|---------|----------|
| `ci/` | CI/CD pipeline changes | `ci/add-deployment-workflow`<br>`ci/configure-github-actions` |
| `deploy/` | Deployment-specific changes | `deploy/add-production-env`<br>`deploy/configure-vercel` |

### Experimental

| Prefix | Purpose | Examples |
|--------|---------|----------|
| `spike/` | Research/proof-of-concept (not intended for merge) | `spike/investigate-rxdb-performance`<br>`spike/test-neo4j-integration` |
| `experiment/` | Experimental features (may be discarded) | `experiment/try-new-auth-flow`<br>`experiment/alternative-ui-layout` |
| `wip/` | Work in progress (explicit "not ready" signal) | `wip/partial-migration`<br>`wip/incomplete-feature` |

---

## Breaking Changes

For breaking changes, prefix the description with `breaking-`:

```
feat/breaking-api-redesign
refactor/breaking-rename-core-types
enhance/breaking-change-auth-flow
```

**Why prefix not suffix**:
- Branch type (`feat/`, `refactor/`) stays in consistent position
- Easy to scan in branch lists
- Easy to grep: `git branch | grep breaking`
- Breaking nature still prominent (first word after `/`)

---

## Decision Tree

Starting a new branch? Ask these questions in order:

```
1. Does it add NEW functionality?
   → YES: feat/

2. Does it fix something BROKEN?
   → YES: fix/ (or hotfix/ if critical)

3. Does it IMPROVE existing functionality (not broken)?
   → YES: enhance/

4. Does it restructure code WITHOUT changing behaviour?
   → YES: refactor/

5. Is it ONLY type definitions (interfaces, types)?
   → YES: types/

6. Does it improve PERFORMANCE?
   → YES: perf/

7. Is it STYLING changes (colors, fonts, spacing)?
   → YES: styles/

8. Is it LAYOUT changes (positioning, grid, responsive)?
   → YES: layout/

9. Is it DOCUMENTATION?
   → YES: docs/

10. Is it TESTING?
    → YES: test/

11. Is it dependency/config/build?
    → YES: deps/, config/, build/, agents/

12. Is it CI/CD related?
    → YES: ci/ or deploy/

13. Is it research/experimental?
    → YES: spike/ or experiment/

14. Is it just maintenance/cleanup?
    → YES: chore/

15. Still unsure?
    → Use the PRIMARY purpose of the branch
```

---

## Common Scenarios

### Styles vs Layout

**Use `styles/` when changing**:
- Colors, fonts, typography
- Spacing, padding, margins
- Borders, shadows, visual effects
- Theme variables
- CSS properties that don't affect structure

**Use `layout/` when changing**:
- Grid/flexbox structure
- Responsive breakpoints
- Component positioning
- Page structure
- Display/position properties

**When it's both**: Choose the PRIMARY purpose
- Repositioning elements AND changing colors → What's the main goal?
- Example: Making a responsive sidebar with new colors → `layout/make-sidebar-responsive` (layout is primary)

### Multiple Changes in One Branch

**General rule**: Use the prefix for the PRIMARY purpose

**Examples**:
- Adding a feature that requires refactoring → `feat/add-user-dashboard` (refactor is implementation detail)
- Fixing a bug that requires tests → `fix/handle-null-user` (test is part of the fix)
- Enhancing feature with performance improvements → `enhance/improve-search-speed` (perf is the mechanism)

**Exception**: If changes are equally significant and unrelated, consider splitting into multiple branches

### Personal vs Shared Branches

**Current workflow**: Solo development, no shared branches

**If collaborating in future**:
- Personal experiments: `experiment/<your-name>-<description>`
- Shared features: Standard `feat/` prefix
- No special handling needed currently

---

## Examples

### Good Branch Names

```
feat/calculate-user-stats
fix/correctly-render-button
enhance/improve-search-relevance
refactor/extract-validation-logic
types/add-api-response-types
types/define-user-interfaces
perf/optimize-graph-queries
styles/update-button-colors
layout/make-nav-responsive
docs/add-api-examples
test/add-e2e-tests
deps/upgrade-svelte-5
config/update-prettier-rules
agents/add-roadmap-workflow
chore/remove-deprecated-code
spike/investigate-neo4j
feat/breaking-api-redesign
```

### Bad Branch Names

```
feature/new-stuff              # Vague, use feat/ not feature/
fix-button                     # Missing prefix separator
FIX/button-bug                 # Uppercase (should be lowercase)
feat/adding-dashboard          # Not imperative (should be "add")
fix/bug                        # Not descriptive enough
refactor/fix-login             # Wrong prefix (it's a fix, not refactor)
feat/user_dashboard            # Underscores (should be hyphens)
breaking/api-redesign          # Type unclear (breaking what? feat? refactor?)
```

---

## Branch Lifecycle

### Creating a Branch

```bash
# From main
git checkout -b feat/add-user-stats

# Using LazyGit: 'n' for new branch
```

### Naming During Development

- Start with the right prefix immediately
- Don't use `wip/` unless truly incomplete/unstable
- If purpose changes significantly, rename: `git branch -m old-name new-name`

### Merging/Deleting

After merging to main:
```bash
git branch -d feat/add-user-stats
```

In LazyGit: Delete branch after merge (automatic prompt)

---

## Enforcement

### Manual Review (Current)
- Review branch name before creating
- Use this document as reference
- LazyGit shows all branches - easy to spot inconsistencies

### Future Automation (Optional)

**Git hooks** (`.git/hooks/pre-commit` or `.git/hooks/commit-msg`):
- Validate branch names match pattern
- Prevent commits to incorrectly named branches

**CI/CD checks**:
- Validate PR branch names
- Block merges from non-standard branches

**Not implementing yet** - manual review sufficient for solo work

---

## Review & Evolution

### When to Review

- **Monthly**: Check if new patterns emerge
- **Per project**: Different projects might need different prefixes
- **After learning Git workflows**: RS-02 (merge vs rebase) might inform branch strategy

### Evolution

This is version 1.0 of the convention. It may evolve based on:
- New project types (mobile apps, APIs, etc.)
- Team collaboration needs
- Tool integrations (if using GitHub Projects, Jira, etc.)
- Personal workflow discoveries

**Document changes**: Update this file and note version/date

---

## Quick Reference Card

Keep this handy for quick lookups:

```
Core Development:    feat/ enhance/ fix/ hotfix/
Code Quality:        refactor/ types/ perf/ test/ debug/
Docs & Content:      docs/ content/
Styling & UI:        styles/ layout/ a11y/
Dependencies:        deps/ build/ config/ agents/ chore/
CI/CD:               ci/ deploy/
Experimental:        spike/ experiment/ wip/

Breaking Changes:    <prefix>/breaking-<description>

Structure:           <prefix>/<imperative-verb-description>
Example:             feat/calculate-user-stats
```

---

## Related Documentation

- `git-configuration-documentation.md` - Git config and global ignore
- `terminal-setup-documentation.md` - Shell aliases including git shortcuts
- `dev-aliases.zsh` - Git command aliases
