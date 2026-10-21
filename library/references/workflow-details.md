# Workflow Details

Moved from CLAUDE.md sections 7.5, 7.6, 8.2, 8.7 and 8.8 on 2026-10-21. Text is unchanged.

### 7.5. Colour and Theme

Colour, type and shape for anything rendered (HTML artefacts, app styling, terminal GIFs, code stills, social cards, framed screenshots) come from a **project theme** in `.claude/themes/`, created and maintained by `/theme-factory`. Format, resolution order and quality gates: `library/references/theme-conventions.md`.

**Usage rules:**

- Components and artefacts reference semantic aliases only (`--ink`, `--surface`, `--accent`, `--danger`); the theme's `html` target file emits them, light and dark, via `library/scripts/theme/emit.ts`
- No inline hex values in components or skills; a missing colour is a theme change, not a local constant
- Every theme ships its own verified contrast table (AA 4.5:1 body, 3:1 large) and passes an originality gate; only the user can lift an originality warning
- No theme in the project yet: run `/theme-factory "html"` (or the target you need) before styling; the global `clod` family is the fallback until then

**Seed palettes** (optional starting points for a new theme, none mandatory): the project's own CSS, an image, mood words or a reference palette such as `library/references/reasonable-colors-reference.md`.

### 7.6. Testing

Always assume that creating tests for new features is in-scope *unless* context clearly indicates otherwise

- **File naming:** `module-name.test.ts` alongside source
- **Fixtures pattern:** Test data in `tests/fixtures/<module>.ts` as named exports
- **Import style:** `import * as fixtures from '../fixtures/<module>'`
- Integration tests for critical paths preferred over exhaustive unit coverage

### 8.2. Versioning with `svu`

See the `project-tag_version` skill for when to tag and the bump-detection rule. Tags always come from `safe-version-next.sh`, never bare `svu next`: it wraps `svu current`/`svu next` and refuses to cross 0.x → 1.x itself (declaring the API stable is a human decision; it emits a 0.x minor bump instead). Once a project deliberately tags `1.0.0`, the guard becomes a no-op and later major bumps pass through normally.

### 8.7. Git Worktrees

When working with git worktrees: (1) always check which branch already exists before creating a new one, (2) never try to remove a worktree while your shell is inside it, (3) use the correct existing branch name rather than creating duplicates, (4) after removing a worktree, cd to the main repo directory.

### 8.8. Pull Requests

Handled by the `pr-create` and `pr-update` skills, both filling the shared template at `library/templates/pr-description.md`. Review feedback is worked through with `pr-handle_review` (verify independently, fix, reply); approved PRs land with `pr-land` (merge commit, tag, roadmap sync, cleanup).

Dependent work stacks: when a branch builds on another branch whose PR is still open, it branches from that branch and opens a stacked PR (GitHub stacks, `gh stack`), never from main. Mechanics and caveats: `library/references/stacked-prs.md`.

