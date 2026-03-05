---
description: "{{ 𝚫𝚫𝚫 }} Review a pull request and post a comment"
model: haiku
argument-hint: "<pr-number-or-url>"
---

Review the pull request identified by `$ARGUMENTS`.

## Steps

1. Run `gh pr view $ARGUMENTS` to get PR title, description, and metadata
2. Run `gh pr diff $ARGUMENTS` to get the full diff
3. Write a review comment using the `<format>` below
4. Post it with `gh pr comment $ARGUMENTS --body "..."`

## Review Focus

Keep it concise. Flag only the most important issues. Skip minor style nits.

- Correctness — will this break anything?
- Security — any obvious vulnerabilities?
- Glaring convention violations

<format>
## Code Review

### What Works Well

🟣 **[strength]** — [why it's good]

---

### Issues

### 🔴 [Blocking issue title]

[Description. Code snippet if needed.]

### 🟡 [Concern title]

[Description.]

### 🔵 [Minor quibble title]

[Description.]
</format>

<severity-key>
- 🔴 Red = blocking — must fix before merge
- 🟡 Yellow = concern — should fix, won't block
- 🔵 Blue = minor quibble — nice to have
- 🟣 Purple = point of excellence — worth calling out
</severity-key>

Omit any severity level that has no entries. Only include 🟣 sections if there's something genuinely worth praising.
