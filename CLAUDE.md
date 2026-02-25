# Jason Warren - Claude Code Config

> Last updated: 2025-02-05

---

## Technical Profile

**Languages:** TypeScript (primary), JavaScript ES2022+, Python (learning)
**Frontend:** Svelte/SvelteKit preferred, React/Next.js when required
**Backend:** Node.js, Express, API design
**Databases:** PostgreSQL, Supabase (RLS expertise), Neo4j, MongoDB
**Testing:** Vitest preferred, Jest familiar — coverage is a known weakness
**Tooling:** Git, Zed, Vite, bun/npm/pnpm (project-specific)

---

## Communication

- **No sycophancy.** No "Great question!" No hedging. Direct answers only.
- **British English** — see spelling rules below
- Clever humour welcome when it lands; forced humour isn't
- Concrete examples over abstract explanations
- Explicit over implicit (neurodivergent-friendly)
- Don't pretend weaknesses are strengths

### Spelling (Non-Negotiable)

Use British spelling in all code comments, documentation, and output:

- `-ise` not `-ize` (organisation, normalise, initialise)
- `-our` not `-or` (colour, behaviour, favour)
- `-re` not `-er` (centre, metre)
- `-ogue` not `-og` (catalogue, dialogue)
- Double consonants: travelled, cancelled, modelling

If unsure: https://www.oxfordlearnersdictionaries.com

---

## Claude Code Behaviour

### Linear Integration

When working with Linear issues, set status to 'In Progress' when starting work and 'In Review' when a PR is created. Never set issues to 'Done' unless explicitly asked.

### Code Editing

**Do not edit files directly unless explicitly asked.** Instead:

1. Show the proposed code
2. Wait for me to make the edit

This applies to all file modifications. When I say "do it" or "make the change", then edit directly.

### Plans

When asked to plan work:

- Extremely concise; sacrifice grammar for brevity
- No preamble or context I already know
- End with unresolved questions (if any)

### Asking vs Proceeding

- **Ambiguous requirements:** Ask first
- **Clear intent, unclear implementation:** Make a reasonable call, flag assumptions
- **Refactoring adjacent code:** Stay surgical unless asked to clean up
- **Multiple valid approaches:** Present options briefly, recommend one

### Verification

Never commit code that hasn't been verified:

- New features: test manually or run automated tests
- Bug fixes: verify the fix resolves the issue
- Refactors: ensure behaviour unchanged

---

## Code Conventions

### Paradigm

Pragmatic over ideological. OOP when it fits, functional when it fits. Clear structure matters more than paradigm purity.

### Naming

```typescript
// ✅ Clear, semantic names
const authenticatedUserId = await getAuthenticatedUser();
const monthlyRevenue = calculateMonthlyRevenue(transactions);

// ❌ Cryptic abbreviations
const authUsrId = await getAuth();
const revM = calcMR(txs);
```

- Files: `kebab-case.ts`, React components: `PascalCase.tsx`
- Variables/functions: descriptive over brief

### TypeScript Standards

- Strict mode enabled
- Interfaces over types for object shapes
- Avoid `any` — use `unknown` when type is uncertain
- Explicit return types on exported functions
- Leverage discriminated unions

### Code Style

- Files use **tabs for indentation** (not spaces)
- When editing: preserve exact tab characters, never convert to spaces
- Always use Edit tool for modifications, never sed/awk

### Testing

Testing is a known weakness. No systematic TDD, no comprehensive coverage culture.

When tests exist:

- **File naming:** `module-name.test.ts` alongside source
- **Fixtures pattern:** Test data in `tests/fixtures/<module>.ts` as named exports
- **Import style:** `import * as fixtures from '../fixtures/<module>'`
- Integration tests for critical paths preferred over exhaustive unit coverage

---

## Git Workflow

### Commit Style

Conventional Commits: `type(scope): description`

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

Detailed commit bodies when context needed. Good git history is documentation.

### Commit Granularity

- Commit frequently with clear, granular changes
- Each commit should be a single logical unit
- More atomic commits = better history

### Breaking Change Detection

**Always flag potential breaking changes**, even when I'm handling commits. Warn when changes might need `BREAKING CHANGE:` footer or `!` indicator:

- Removed/renamed exports (functions, types, components)
- Changed function signatures
- Modified return types or response shapes
- Database schema changes
- API endpoint changes
- Environment variable additions/changes
- Configuration format changes

Format: `⚠️ Breaking change — consider feat!: or BREAKING CHANGE: footer`

### Branch Naming

`<prefix>/<short-description>` — all lowercase, hyphens between words, imperative mood

**Prefixes:** `feat/`, `fix/`, `enhance/`, `refactor/`, `test/`, `docs/`, `config/`

Branches represent minimal tangible improvements. When in doubt, go smaller.

### Git Worktrees

When working with git worktrees: (1) always check which branch already exists before creating a new one, (2) never try to remove a worktree while your shell is inside it, (3) use the correct existing branch name rather than creating duplicates.

### Pull Requests

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

## Security Defaults

- Never commit secrets (environment variables only)
- Row-Level Security for multi-tenant data
- Input validation at boundaries (Zod, etc.)
- HTTPS only, secure cookies
- Transactions for multi-step operations
- Avoid N+1 queries

---

## Database

### SQL

When running SQL against the database, prefer writing to a .sql file and executing it rather than using inline shell commands with escaped quotes.

---

## Documentation

- **Mermaid diagrams** for architecture and data flow
- **Inline comments** sparingly — code should explain itself
- **ADRs** for significant technical choices
- Headers: `##` main, `###` subsections
- Code blocks: always specify language

---

## Project Overrides

Project-level configs take precedence:

- `.claude/CLAUDE.md` or `CLAUDE.md` in project root
- Nested configs for subsystems (e.g., `frontend/CLAUDE.md`)
- Project settings override everything here
