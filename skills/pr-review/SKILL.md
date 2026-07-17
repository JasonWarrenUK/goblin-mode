---
name: "PR: Review"
description: "{{ 𝛀𝛀𝛀 }} Review a pull request"
when_to_use: "When you want a read-only review of a PR's diff printed to the conversation — for a posted GitHub review use pr-review-comment, which calls this skill internally."
model: opus
disable-model-invocation: false # required so pr-review-comment can call it
allowed-tools: ["Bash(git:*)", "Bash(gh:*)", "Read", "Glob", "Grep"]
disallowed-tools: ["Edit", "Write", "NotebookEdit"] # reviews, never fixes
argument-hint: ["PR number/url"]
---

# PR Review

Canonical review methodology. Produces structured findings only; **never posts to GitHub**. `pr-review-comment` loads this skill and handles posting — keep all methodology here to avoid divergence.

```xml
<pull-request-review>
  <task>Review the pull request identified by `$ARGUMENTS` and produce structured findings. Do not post anything to GitHub.</task>
  <steps>
    <step num="1">Run `gh pr view $ARGUMENTS` to get PR title, description, and metadata</step>
    <step num="2">Run `gh pr diff $ARGUMENTS` to get the full diff — always PR vs `origin/main`, regardless of the local branch checked out</step>
    <step num="3">Research project conventions stored in `CLAUDE.md`, `.claude/**/*` and `docs/*`. Before critiquing implementation, check whether the dev is following established project practice</step>
    <step num="4">Classify every finding by <taxonomy/> type and by scope (line / file / cross-file)</step>
    <step num="5">Where a line-scoped 🔴/🟠/🟡 finding has a concrete fix, write it as a committable ```suggestion block per <suggestions/></step>
    <step num="6">Write every comment body **and the `summary`** (including the follow-up delta, when in that mode) per the writing-style skill's anti-slop rules (no em dashes, no contrastive couplets, no parade-of-examples, lead with specifics). This isn't just style guidance here — when this skill's output feeds `pr-review-comment`, its `partition-findings.mjs` hard-fails the post on any em-dash/en-dash in the summary or a comment body. Get it right here, upstream, rather than relying on that gate to catch it</step>
    <step num="7">Emit findings using <output/>. This is the full deliverable — stop here, nothing gets posted</step>
  </steps>
  <foci>
    <focus>Correctness — will this break anything?</focus>
    <focus>Security — any obvious vulnerabilities?</focus>
    <focus>Glaring convention violations</focus>
    <focus>Reinforcement — genuine strengths worth calling out, not token praise</focus>
  </foci>
  <taxonomy>
    <!-- Replaces any older 🟣/🔴/🟡/🔵 four-colour key. This is the only taxonomy. -->
    <row emoji="🔴" type="major changes" ceiling="Request Changes">Blocking — must fix before merge</row>
    <row emoji="🟠" type="minor changes" ceiling="Comment">Should fix, won't block. Same ceiling and treatment as nits</row>
    <row emoji="🟡" type="nits" ceiling="Comment">Nice to have</row>
    <row emoji="🟣" type="admiration" ceiling="Approve">Accolade — only when genuinely warranted</row>
  </taxonomy>
  <matrix>
    <!-- Type x Scope -> where the comment anchors + suggestion eligibility -->
    <row type="major/minor changes, nits" scope="line" anchor="line highlight (inline diff comment)" suggestion="yes, if a concrete fix exists" />
    <row type="major/minor changes, nits" scope="file" anchor="file-level comment" suggestion="no" />
    <row type="major/minor changes, nits" scope="cross-file" anchor="top-level review comment" suggestion="no" />
    <row type="admiration" scope="line" anchor="file-level comment — admiration never uses a line highlight, even when the praise is line-scoped" suggestion="no" />
    <row type="admiration" scope="file" anchor="file-level comment" suggestion="no" />
    <row type="admiration" scope="cross-file" anchor="top-level review comment" suggestion="no" />
  </matrix>
  <suggestions>
    <guide>Emit a ```suggestion block only for line-scoped 🔴/🟠/🟡 findings with a concrete, single-location fix.</guide>
    <guide>Skip suggestions where the fix spans multiple non-contiguous lines, requires judgement calls, or isn't safely committable as-is.</guide>
    <guide>Never emit suggestions for admiration — there's nothing to commit.</guide>
  </suggestions>
  <verdict>
    <guide>Derive one overall verdict from the highest ceiling present across all findings (highest-ceiling-wins):</guide>
    <rule>Any 🔴 present → Request Changes</rule>
    <rule>Else any 🟠 or 🟡 present → Comment</rule>
    <rule>Else only 🟣 present (or no findings) → Approve</rule>
  </verdict>
  <guides>
    <guide>Keep it concise. Flag only the most important issues — skip minor style nits unless they're genuinely worth a 🟡.</guide>
    <guide>Before critiquing implementation, check whether the dev is following established project practice.</guide>
    <guide>Omit any type that has no entries. Only include 🟣 findings if there's something genuinely worth praising — token praise is worse than none.</guide>
  </guides>
  <output type="structured">
    For each finding:
    - `type`: 🔴 | 🟠 | 🟡 | 🟣
    - `scope`: line | file | cross-file
    - `file`: path (omit for cross-file)
    - `line` or `range`: omit for file/cross-file scope
    - `body`: the comment text (writing-style rules applied)
    - `suggestion`: optional ```suggestion block (line-scoped changes/nits only)

    Plus:
    - `summary`: overall review body (top-level comment content). When run in follow-up mode (see `pr-review-comment`'s `<follow-up-mode/>`), the leading "Since my last review" delta uses only ⚪ fixed / ⚫ still open / 🟢 new — never 🆕 (renders as a GitHub `:new:` badge) or ✅/⚠️ (superseded, off-palette)
    - `verdict`: Request Changes | Comment | Approve, derived per <verdict/>
  </output>
</pull-request-review>
```
