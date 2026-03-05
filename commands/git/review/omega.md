---
description: "{{ 𝛀𝛀𝛀 }} Review a pull request and post a comment"
model: opus
argument-hint: "<pr-number-or-url>"
---

Review the pull request identified by `$ARGUMENTS`.

## Steps

1. Run `gh pr view $ARGUMENTS` to get PR title, description, author, and metadata
2. Run `gh pr diff $ARGUMENTS` to get the full diff
3. Read relevant source files for full context — especially files adjacent to changes that may be affected
4. Research project conventions from `CLAUDE.md` if present
5. Write a thorough review using the `<format>` below
6. Post it with `gh pr comment $ARGUMENTS --body "..."`

## Review Depth

Analyse exhaustively across all dimensions:

- **Correctness** — logic errors, off-by-ones, race conditions, unhandled edge cases
- **Security** — injection, auth bypasses, data exposure, OWASP top 10
- **Architecture** — does this fit the existing patterns? Does it introduce unnecessary complexity?
- **Performance** — N+1 queries, missing indexes, unnecessary allocations, unthrottled loops
- **Atomicity & transactions** — multi-step operations that should be wrapped
- **Error handling** — are failures silent? are errors swallowed?
- **Test coverage** — are the changes tested? are the tests meaningful?
- **Breaking changes** — removed/renamed exports, changed signatures, schema changes, API contract changes
- **Documentation** — are complex decisions explained?
- **Conventions** — naming, file structure, commit style, project patterns

<format>
## Code Review

### What Works Well

🟣 **[strength]** — [why it's good]

---

### Issues

### 🔴 [Blocking issue title]

[Detailed description. Root cause if identifiable. Code snippet showing the problem and/or the fix.]

### 🟡 [Concern title]

[Description. Suggested fix or alternative approach.]

### 🔵 [Minor quibble title]

[Description.]
</format>

<severity-key>
- 🔴 Red = blocking — must fix before merge
- 🟡 Yellow = concern — should fix, won't block
- 🔵 Blue = minor quibble — nice to have
- 🟣 Purple = point of excellence — worth calling out
</severity-key>

Use `### h3` headings for each individual issue so they render as anchored sections on GitHub. Group multiple issues of the same severity together. Order within a severity group by impact, highest first.

Omit any severity level that has no entries. Only include 🟣 sections if there's something genuinely worth praising — do not manufacture praise.

Do not pad the review. A short review with two real issues is better than a long review with filler.
