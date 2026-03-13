---
description: "{{ 𝛀𝛀𝛀 }} Review a pull request and post a comment"
model: opus
argument-hint: "<pr-number-or-url>"
allowed-tools: ["Bash", "Read", "Glob", "Grep"]
---

<pull-request-review>
  <task>Review the pull request identified by `$ARGUMENTS`.</task>
  <steps>
    <step num="1">Run `gh pr view $ARGUMENTS` to get PR title, description, and metadata</step>
    <step num="2">Run `gh pr diff $ARGUMENTS` to get the full diff</step>
    <step num="3">Research project conventions stored in `CLAUDE.md`, `.claude/**/*` and `docs/*`</step>
    <step num="4">Write a review comment using the `<format>` below</step>
    <step num="5">Post it with `gh pr comment $ARGUMENTS --body "..."`</step>
  </steps>
  <foci>
    <focus>Correctness — will this break anything?</focus>
    <focus>Security — any obvious vulnerabilities?</focus>
    <focus>Glaring convention violations</focus>
  <foci>
  <guidance>
    <guide>Keep it concise.</guide>
    <guide>Flag only the most important issues. Skip minor style nits.</guide>
    <guide>Before critiquing implementation, check whether the dev is following established project practice</guide>
  </guidance>
  <format type="md">
    # Code Review
    ## What Works Well
    🟣 **[strength]** — [why it's good]
    ## Issues
    ### 🔴 [Blocking issue title]
    [Description. Code snippet if needed.]
    ### 🟡 [Concern title]
    [Description.]
    ### 🔵 [Minor quibble title]
    [Description.]
  </format>
  <key type="list">
    <guide>Omit any severity level that has no entries. Only include 🟣 sections if there's something genuinely worth praising.</guide>
    <key-item>🟣 Purple: point of excellence — worth calling out</key-item>
    <key-item>🔴 Red: blocking — must fix before merge</key-item>
    <key-item>🟡 Yellow: concern — should fix, won't block</key-item>
    <key-item>🔵 Blue: minor quibble — nice to have</key-item>
  </key>
</pull-request-review>
