# Jason Warren - Claude Code Config

| Prop    | Value |
|---------|-------|
| Updated | 2026-06-15 |

<!-- toc:start -->
## Table of Contents

- [1. Technical Profile](#1-technical-profile)
  - [1a. Scales: Preference & Proficiency](#1a-scales-preference-proficiency)
    - [1a1. Preference](#1a1-preference)
    - [1a2. Proficiency](#1a2-proficiency)
  - [1b. Domains](#1b-domains)
    - [1b1. Languages](#1b1-languages)
  - [1.2. Frontend](#12-frontend)
  - [1.3. Backend](#13-backend)
  - [1.4. TUI](#14-tui)
  - [1.5. Databases](#15-databases)
  - [1.6. Testing](#16-testing)
  - [1.7. Tooling](#17-tooling)
  - [1.8 Packages & Apps](#18-packages-apps)
    - [1.8.1. System Apps](#181-system-apps)
    - [1.8.2. JS/TS Ecosystem](#182-jsts-ecosystem)
    - [1.8.3. Other Ecosystems](#183-other-ecosystems)
- [2. Shell Scripting](#2-shell-scripting)
- [3. Communication](#3-communication)
  - [3.1. Golden Rules](#31-golden-rules)
  - [3.2. Spelling (Non-Negotiable)](#32-spelling-non-negotiable)
  - [3.3. Guidelines](#33-guidelines)
- [4. Agent Skills](#4-agent-skills)
  - [4.1. Skill Creation](#41-skill-creation)
    - [4.1.1. YAML Frontmatter: New Convention](#411-yaml-frontmatter-new-convention)
    - [4.1.2. YAML Frontmatter: Old Convention](#412-yaml-frontmatter-old-convention)
- [5. Verification](#5-verification)
- [6. Claude Code Behaviour](#6-claude-code-behaviour)
  - [6.1. Task Tracker Integration](#61-task-tracker-integration)
  - [6.2. Plans](#62-plans)
  - [6.3. Asking vs Proceeding](#63-asking-vs-proceeding)
  - [6.4. Verification](#64-verification)
- [7. Code Conventions](#7-code-conventions)
  - [7.1. Paradigm](#71-paradigm)
  - [7.2. Naming](#72-naming)
    - [7.2.1. Variables & Functions](#721-variables-functions)
    - [7.2.2. Files](#722-files)
  - [7.3. TypeScript Standards](#73-typescript-standards)
  - [7.4. Code Style](#74-code-style)
  - [7.5. Colour Palette](#75-colour-palette)
  - [7.6. Testing](#76-testing)
- [8. Git Workflow](#8-git-workflow)
  - [8.1. Commit Style](#81-commit-style)
  - [8.2. Versioning with svu](#82-versioning-with-svu)
  - [8.3. Commit Granularity](#83-commit-granularity)
  - [8.4. PR & Commit Style](#84-pr-commit-style)
  - [8.5. Breaking Change Detection](#85-breaking-change-detection)
  - [8.6. Branch Naming](#86-branch-naming)
  - [8.7. Git Worktrees](#87-git-worktrees)
  - [8.8. Pull Requests](#88-pull-requests)
- [9. Security Defaults](#9-security-defaults)
- [10. Database](#10-database)
  - [10.1. SQL](#101-sql)
- [11. Documentation](#11-documentation)
- [12. Project Overrides](#12-project-overrides)
<!-- toc:end -->

## 1. Technical Profile

Options are listed in order of preference & proficiency

### 1a. Scales: Preference & Proficiency

#### 1a1. Preference

| Value | Definition |
|-------|------------|
|   1   | "Love using" or "Learning this is a high priority" |
|   2   | "Like using" or "Want to learn" |
|   3   | "No strong feelings" |
|   4   | "Dislike using" or "Not that interested in learning" |
|   5   | "Hate using" or "Actively don't want to learn" |

#### 1a2. Proficiency

| Value | Definition |
|-------|------------|
|   1   | Proficient with advanced features |
|   2   | Proficient with base features |
|   3   | Actively learning or limited experience |
|   4   | Have dabbled slightly |
|   5   | No experience |

### 1b. Domains

#### 1b1. Languages

| Priority | Status     | Language |
|----------|------------|----------|
|    1     | Preferred  | TypeScript |
|    2     | Proficient | JavaScript |
|    3     |  Learning  |  Python  |
|    4     |  Learning  |    Go    |
|    5     |  Dabbled   |    C#    |

### 1.2. Frontend

| #   | Status        | Front End | Full Stack |
|-----|---------------|-----------|------------|
|  1  |   Preferred   | Svelte 5  | SvelteKit 2 |
|  2  | When Required |   React   |  Next.js   |

### 1.3. Backend

| #   | Status        | Runtime | Server |
|-----|---------------|---------|--------|
|  1  |   Preferred   |   Bun   | undecided |
|  2  |  Interested   |  Deno   |  Oak   |
|  3  | When Required |  Node   | Express |

### 1.4. TUI

This is ordered by *familiarity*, not preference

| #   | Language | Libraries |
|-----|----------|-----------|
|  1  |    Go    | Charm (bubbletea, bubbles, lipgloss etc) |
|  2  |    TS    |  OpenTUI  |
|  3  |  Python  |  Textual  |

### 1.5. Databases

One db tech stack per paradigm

| Paradigm   | Stack                | Notes |
|------------|----------------------|-------|
| Relational | PostgreSQL, Supabase | RLS expertise |
|   Graph    |        Neo4j         | Preferred data model |
|   Object   |       MongoDB        | Limited experience |

### 1.6. Testing

No preference, limited knowledge. Libraries used so far: Vitest, Jest

### 1.7. Tooling

| Role       | Tool |
|------------|------|
| Versioning | git, Github, svu |
|    IDE     | Zed  |
| Deployment | Vercel, Deno Deploy, Github Pages |

### 1.8 Packages & Apps

#### 1.8.1. System Apps

| #   | Tool |
|-----|------|
|  1  | Homebrew |

#### 1.8.2. JS/TS Ecosystem

Primarily determined by project context, but for tiebreaks use the following preference order:

| #   | Tool |
|-----|------|
|  1  | bun  |
|  2  | deno |
|  3  | npm, pnpm |

#### 1.8.3. Other Ecosystems

Undecided on favoured python package manager

---

## 2. Shell Scripting

- Target zsh syntax (not bash) for shell scripts on this system
- Use macOS-compatible flags: `sed -i ''` (with empty string), avoid GNU-only options
- Suppress debug output and avoid shadowing readonly variables

---

## 3. Communication

### 3.1. Golden Rules

*Never* break these

1. **Em-dashes:** Absolutely no em-dashes under any circumstances. Replace with a colon, semicolon, comma, or restructure.
2. **No contrastive couplets:** No "it's not x; it's y", "not X but Y", "less about X, more about Y". State the point directly.
3. **No sycophancy:** No "Great question!" No hedging. Direct answers only.
4. **No Oxford commas.**
5. **No vague competence claims or undefended preferences.** Only include what can be said with conviction.

For writing prose specifically, the `role-viewpoint-writing_style` skill is the authoritative source. It includes a self-check gate that must run before any draft reaches Jason.

### 3.2. Spelling (Non-Negotiable)

Use British spelling in all code comments, documentation, and output:

- `-ise` not `-ize` (organisation, normalise, initialise)
- `-our` not `-or` (colour, behaviour, favour)
- `-re` not `-er` (centre, metre)
- `-ogue` not `-og` (catalogue, dialogue)
- Double consonants: travelled, cancelled, modelling

If unsure: <https://www.oxfordlearnersdictionaries.com>

### 3.3. Guidelines

1. Clever humour welcome when it lands; forced humour isn't
2. Concrete examples over abstract explanations. Let the specific do the work a summarising sentence pretends to do.
3. Explicit over implicit (neurodivergent-friendly)
4. Don't pretend weaknesses are strengths
5. Casual register, British idiom. Never American colloquialisms.
6. Conviction without performance. State opinions inline; don't build to them or defend them pre-emptively.

---

## 4. Agent Skills

- All skills live in `~/.claude/skills/` as `SKILL.md` files
- Command skills have `disable-model-invocation: true`; knowledge skills have `user-invocable: false`.

### 4.1. Skill Creation

1. Always create skills in the project-local `.claude/skills/` directory unless explicitly told to create them globally
2. Check for naming conflicts with personal-level skills (~/.claude/skills/) since personal scope shadows project scope
3. Use the new naming convention when creating or editing skills, but be aware of the old naming convention

#### 4.1.1. YAML Frontmatter: New Convention

Use the runic letter convention in the YAML frontmatter `description` field to signal which model a command uses:
 a. `𝚫𝚫𝚫` = haiku
 b. `ƔƔƔ` = sonnet
 c. `𝛀𝛀𝛀` = opus

Format: `description: "{{ ƔƔƔ }} Command description here"`

#### 4.1.2. YAML Frontmatter: Old Convention

Use the Greek letter convention in the YAML frontmatter `description` field to signal which model a command uses:
 a. `ᚻᛕ` = haiku
 b. `ᛇᚤ` = sonnet
 c. `ᛜᚹ` = opus
 d. `ᚨᛔ` = fable

Format: `description: "{{ ᛇᚤ }} Command description here"`

---

## 5. Verification

- When asked about CLI flags, config precedence, or API behaviour, verify against current source/docs before answering — do not guess from memory
- When recommending model versions or provider defaults, check the provider's current docs first

---

## 6. Claude Code Behaviour

### 6.1. Task Tracker Integration

This config is tracker-agnostic — it makes no assumption about which project-management tool (if any) a given project uses. See `docs/reference/task-trackers/` for the shared status-transition convention (In Progress → In Review → Done, never automatic) and tool-specific detail for Linear, GitHub Issues, and git-native.

### 6.2. Plans

When asked to plan work:

- Extremely concise; sacrifice grammar for brevity
- No preamble or context I already know
- End with unresolved questions (if any)
- Use the question tool until all questions are resolved

### 6.3. Asking vs Proceeding

- **Ambiguous requirements:** Ask first
- **Clear intent, unclear implementation:** Make a reasonable call, flag assumptions
- **Refactoring adjacent code:** Stay surgical unless asked to clean up
- **Multiple valid approaches:** Present options briefly, recommend one

### 6.4. Verification

Never commit code that hasn't been verified:

- New features: test manually or run automated tests
- Bug fixes: verify the fix resolves the issue
- Refactors: ensure behaviour unchanged

---

## 7. Code Conventions

### 7.1. Paradigm

Pragmatic over ideological. OOP when it fits, functional when it fits. Clear structure matters more than paradigm purity.

### 7.2. Naming

#### 7.2.1. Variables & Functions

```typescript
// ✅ Clear, semantic names
const authenticatedUserId = await getAuthenticatedUser();
const monthlyRevenue = calculateMonthlyRevenue(transactions);

// ❌ Cryptic abbreviations
const authUsrId = await getAuth();
const revM = calcMR(txs);
```

#### 7.2.2. Files

| Format           | Convention |
|------------------|------------|
|   ts, js, json   | `ts-file.ts`, `json-file.json` |
| jsx, tsx, svelte | `ReactComponent.tsx`, `SvelteComponent.svelte` |

### 7.3. TypeScript Standards

- Strict mode enabled
- Interfaces over types for object shapes
- Avoid `any` — use `unknown` when type is uncertain
- Explicit return types on exported functions
- Leverage discriminated unions

### 7.4. Code Style

- Files use **tabs for indentation** (not spaces)
- When editing: preserve exact tab characters, never convert to spaces
- Always use Edit tool for modifications, never sed/awk

### 7.5. Colour Palette

Use [Reasonable Colors](https://www.reasonable.work/colors/) as the default palette for all frontend/styling work.

**Install:**

- npm: `reasonable-colors`
- CDN: `unpkg.com/reasonable-colors@0.4.0/reasonable-colors.css`

**Variable convention:** `--color-COLORNAME-SHADE` (e.g. `--color-azure-3`)

- 24 colour sets + grays, 6 shades each (1 = lightest, 6 = darkest)
- Shade difference → contrast ratio: diff 2 = 3:1 (AA large), diff 3 = 4.5:1 (AA body), diff 4 = 7:1 (AAA)

**Usage rules:**

- The `color` spelling in var names is acceptable — it's a third-party convention
- Always define semantic aliases; never use RC vars directly in components:

  ```css
  :root {
    --color-primary: var(--color-azure-3);
    --color-primary-bg: var(--color-azure-1);
    --color-primary-text: var(--color-azure-6);
  }
  ```

- Projects may override this default in project-level CLAUDE.md

**Local reference:** `library/references/reasonable-colors-reference.md`

### 7.6. Testing

Always assume that creating tests for new features is in-scope *unless* context clearly indicates otherwise

- **File naming:** `module-name.test.ts` alongside source
- **Fixtures pattern:** Test data in `tests/fixtures/<module>.ts` as named exports
- **Import style:** `import * as fixtures from '../fixtures/<module>'`
- Integration tests for critical paths preferred over exhaustive unit coverage

---

## 8. Git Workflow

### 8.1. Commit Style

Conventional Commits: `type(scope): description`

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

Detailed commit bodies when context needed. Good git history is documentation.

### 8.2. Versioning with `svu`

Use [`svu`](https://github.com/caarlos0/svu) as the default tool for deriving semver tags from conventional-commit history. `svu` doesn't commit, push, or merge; it computes the next version, so pair it with `git tag`.

**Always tag** at these moments — run `svu next`, then tag and push:

| Moment             | Command sequence |
|--------------------|------------------|
|    PR creation     | `git tag "$(svu next)" && git push --tags` |
|  Merge to `main`   | `git tag "$(svu next)" && git push --tags` |
| Merge to `staging` | `git tag "$(svu next)" && git push --tags` |

**Mid-branch commits:** proactively offer a tag *only* when the pending bump is **major or minor**. Stay silent on **patch** bumps. Detect the bump level by comparing `svu current` with `svu next`:

- Different major segment → major; offer a tag.
- Same major, different minor → minor; offer a tag.
- Only the patch segment changed → patch; do **not** offer.

Surface the proposed version (e.g. `⬆️ minor bump available — tag v1.3.0?`) rather than tagging silently.

---

### 8.3. Commit Granularity

- Commit frequently with clear, granular changes
- Each commit should be a single logical unit
- More atomic commits = better history
- When splitting changes into commits, default to granular thematic splits (one logical change per commit) and confirm grouping before committing

### 8.4. PR & Commit Style

- PR descriptions should be humble-factual, not apologetic or permission-seeking

### 8.5. Breaking Change Detection

**Always flag potential breaking changes**, even when I'm handling commits. Warn when changes might need `BREAKING CHANGE:` footer or `!` indicator:

- Removed/renamed exports (functions, types, components)
- Changed function signatures
- Modified return types or response shapes
- Database schema changes
- API endpoint changes
- Environment variable additions/changes
- Configuration format changes

Format: `⚠️ Breaking change — consider feat!: or BREAKING CHANGE: footer`

### 8.6. Branch Naming

`<prefix>/<short-description>` — all lowercase, hyphens between words, imperative mood

**Prefixes:** `feat/`, `fix/`, `enhance/`, `refactor/`, `test/`, `docs/`, `config/`

Branches represent minimal tangible improvements. When in doubt, go smaller.

### 8.7. Git Worktrees

When working with git worktrees: (1) always check which branch already exists before creating a new one, (2) never try to remove a worktree while your shell is inside it, (3) use the correct existing branch name rather than creating duplicates, (4) after removing a worktree, cd to the main repo directory.

### 8.8. Pull Requests

**Always** use this structure for PR descriptions, regardless of how the PR was triggered:

- **Title:** Brief, descriptive, title case, understandable to non-devs
- **Summary:** Describe the PR with a non-technical, absurd metaphor
- **TL;DR:** List any steps devs must take after pulling this down
- **Changes:** Break into files or categories depending on scope; use collapsible details

Template:

```md
# {{ title }}
## Overview
{{ overview }}
## Summary
{{ absurd metaphor }}
> [!TIP]
> {{ tldr }}
---
## Changes
{{ changes with collapsible details }}
---
```

Before creating: analyse all commits on the branch, show the draft, and await approval.

---

## 9. Security Defaults

- Never commit secrets (environment variables only)
- Row-Level Security for multi-tenant data
- Input validation at boundaries (Zod, etc.)
- HTTPS only, secure cookies
- Transactions for multi-step operations
- Avoid N+1 queries

---

## 10. Database

### 10.1. SQL

When running SQL against the database, prefer writing to a .sql file and executing it rather than using inline shell commands with escaped quotes.

---

## 11. Documentation

- **Mermaid diagrams** for architecture and data flow
- **Inline comments** sparingly — code should explain itself
- **ADRs** for significant technical choices
- Headers: `##` main, `###` subsections
- Code blocks: always specify language

---

## 12. Project Overrides

Project-level configs take precedence:

- `.claude/CLAUDE.md` or `CLAUDE.md` in project root
- Nested configs for subsystems (e.g., `frontend/CLAUDE.md`)
- Project settings override everything here
