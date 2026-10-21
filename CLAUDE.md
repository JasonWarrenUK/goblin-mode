# Jason Warren - Claude Code Config

| Prop    | Value |
|---------|-------|
| Updated | 2026-10-21 |

Reference detail lives in `~/.claude/library/references/`:

- `technical-profile.md`: languages, frontend, backend, TUI, databases, test runners, tooling, packages, preference and proficiency scales
- `workflow-details.md`: colour and theme usage rules, test file layout, svu versioning, worktrees, pull requests

## 1. Technical Profile

TypeScript first, then JavaScript, Python, Go. Svelte 5 and SvelteKit 2 for frontend (React and Next.js when required). Bun first for runtime and packages, then Deno, then npm or pnpm. PostgreSQL and Supabase for relational data, Neo4j for graph. Python work uses FastAPI with Poetry and poethepoet. Load `technical-profile.md` for anything beyond these defaults.

---

## 2. Shell Scripting

- Target zsh syntax (not bash) for shell scripts on this system
- Use macOS-compatible flags: `sed -i ''` (with empty string), avoid GNU-only options
- Suppress debug output and avoid shadowing readonly variables

---

## 3. Communication

### 3.1. Golden Rules

*Never* break these

1. **Em-dashes:** Absolutely no em-dashes under any circumstances. Replace with a colon, semicolon, comma or restructure.
2. **No contrastive couplets:** No "it's not x; it's y", "not X but Y", "less about X, more about Y". State the point directly.
3. **No sycophancy:** No "Great question!" No hedging. Direct answers only.
4. **No Oxford commas.**
5. **No vague competence claims or undefended preferences.** Only include what can be said with conviction.

For writing prose specifically, the `clod-approach-writing_style` skill is the authoritative source. It includes a self-check gate that must run before any draft reaches Jason.

### 3.2. Spelling (Non-Negotiable)

Use British spelling in all code comments, documentation and output:

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
7. Lead with specifics; never open with generic framing.
8. Vary punctuation; no run of three sentences with the same shape.

These apply to every token of output: terminal chatter, commit messages and PR bodies included, not only prose tasks.

When quoting a banned form (a rule that names it, a scan hit, an error message), wrap it in backticks. The scanner and the commit-msg hook mask backticks, double quotes, blockquotes and their own output lines; nothing else counts as a quotation.

---

## 4. Agent Skills

- All skills live in `~/.claude/skills/` as `SKILL.md` files
- Command skills have `disable-model-invocation: true`; knowledge skills have `user-invocable: false`.
- Exception: a command skill may set `disable-model-invocation: false` when its trigger moment is one Claude sees before the user does (stale PR description, post-merge status drift) **and** it contains its own approval gate before anything irreversible. The gate is the safety net; without one, keep it `true`.
- Placement rules and the model-tag frontmatter convention: `clod-config-skill_conventions` skill

---

## 5. Verification

Verify before answering, always. A checkable fact gets checked before it is stated: CLI flags, config precedence, API and library behaviour, model versions and provider defaults, what a file contains, what a command does. Run the check or read the source first, then cite it (file, URL or command). Never answer from memory on anything checkable; if it cannot be verified, say so rather than guess.

---

## 6. Claude Code Behaviour

### 6.1. Task Tracker Integration

Tracker-agnostic. Status convention (In Progress, In Review, Done, never automatic) and per-tool detail: `docs/reference/task-trackers/`.

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

Clear, semantic names (`authenticatedUserId`, `calculateMonthlyRevenue`), never cryptic abbreviations (`authUsrId`, `calcMR`).

| Format           | Convention |
|------------------|------------|
|   ts, js, json   | `ts-file.ts`, `json-file.json` |
| jsx, tsx, svelte | `ReactComponent.tsx`, `SvelteComponent.svelte` |

### 7.3. TypeScript Standards

- Strict mode enabled
- Interfaces over types for object shapes
- Avoid `any`; use `unknown` when type is uncertain
- Explicit return types on exported functions
- Use discriminated unions

### 7.4. Code Style

- Files use **tabs for indentation** (not spaces)
- When editing: preserve exact tab characters, never convert to spaces
- Always use Edit tool for modifications, never sed/awk
- `replace_all` only after enumerating call sites with Grep and confirming they share one argument shape
- Exception: CHIRPdb (Python, PEP 8) uses spaces via `autopep8`/`flake8`; that project's tooling wins over this default

### 7.5. Colour and Theme

Anything rendered takes colour, type and shape from a project theme in `.claude/themes/` (built by `/theme-factory`); no inline hex values. Usage rules, seed palettes and the fallback: `workflow-details.md`.

### 7.6. Testing

Assume tests for new features are in scope unless context clearly says otherwise. Integration tests for critical paths over exhaustive unit coverage. File naming and fixtures pattern: `workflow-details.md`.

---

## 8. Git Workflow

### 8.1. Commit Style

Conventional Commits: `type(scope): description`

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

Detailed commit bodies when context needed. Good git history is documentation.

### 8.2. Versioning with `svu`

Tags come from `safe-version-next.sh`, never bare `svu next`. See the `project-tag_version` skill.

### 8.3. Commit Granularity

- Commit frequently; each commit is a single logical unit
- Default to granular thematic splits and confirm grouping before committing

### 8.4. PR & Commit Style

PR descriptions are humble-factual, not apologetic or permission-seeking.

### 8.5. Breaking Change Detection

**Always flag potential breaking changes**, even when I'm handling commits. Warn when changes might need `BREAKING CHANGE:` footer or `!` indicator:

- Removed/renamed exports (functions, types, components)
- Changed function signatures
- Modified return types or response shapes
- Database schema changes
- API endpoint changes
- Environment variable additions/changes
- Configuration format changes

Format: `⚠️ Breaking change: consider feat!: or BREAKING CHANGE: footer`

### 8.6. Branch Naming

`<prefix>/<short-description>`: all lowercase, hyphens between words, imperative mood

**Prefixes:** `feat/`, `fix/`, `enhance/`, `refactor/`, `test/`, `docs/`, `config/`, `chore/`, `ci/`, `deps/`, `hotfix/`, `spike/`, `agents/`

Branches represent minimal tangible improvements. When in doubt, go smaller.

### 8.7. Git Worktrees

Check which branch already exists before creating one; never remove a worktree while your shell is inside it. Full rules: `workflow-details.md`.

### 8.8. Pull Requests

Handled by the `pr-create`, `pr-update`, `pr-handle_review` and `pr-land` skills (template: `library/templates/pr-description.md`). Stacked PRs: `library/references/stacked-prs.md`.

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

Write SQL to a `.sql` file and execute it rather than inline shell with escaped quotes.

## 11. Documentation

Mermaid for architecture and data flow, ADRs for significant choices, inline comments sparingly, always specify a language on code blocks.

## 12. Project Overrides

`.claude/CLAUDE.md` or `CLAUDE.md` in the project root, and nested configs, take precedence over everything here.
