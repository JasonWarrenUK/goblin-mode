---
description: "{{ ƔƔƔ }} Review a pull request and post a comment"
model: sonnet
argument-hint: "<pr-number-or-url>"
---

Review the pull request identified by `$ARGUMENTS`.

## Steps

1. Run `gh pr view $ARGUMENTS` to get PR title, description, and metadata
2. Run `gh pr diff $ARGUMENTS` to get the full diff
3. Where helpful, read relevant source files for context on changed code
4. Write a thorough review comment using the `<format>` below
5. Post it with `gh pr comment $ARGUMENTS --body "..."`

## Review Focus

- **Correctness** — logic errors, edge cases, off-by-ones
- **Security** — injection, auth bypasses, data exposure
- **Conventions** — project naming, structure, and style patterns
- **Performance** — N+1s, unnecessary allocations, missing indexes
- **Test coverage** — are the changes meaningfully tested?
- **Breaking changes** — removed exports, changed signatures, schema changes

<format>
## Code Review

### What Works Well

🟣 **[strength]** — [why it's good]

---

### Issues

### 🔴 [Blocking issue title]

[Description. Code snippet if needed.]

### 🟡 [Concern title]

[Description. Suggested fix if applicable.]

### 🔵 [Minor quibble title]

[Description.]
</format>

<severity-key>
- 🔴 Red = blocking — must fix before merge
- 🟡 Yellow = concern — should fix, won't block
- 🔵 Blue = minor quibble — nice to have
- 🟣 Purple = point of excellence — worth calling out
</severity-key>

Omit any severity level that has no entries. Only include 🟣 sections if there's something genuinely worth praising — don't manufacture praise.

Use `### h3` headings for each individual issue so they render as anchored sections on GitHub.
