---
name: "PR: Review & Comment"
description: "{{ 𝛀𝛀𝛀 }} Review a pull request and post it as a GitHub review"
model: opus
disable-model-invocation: true
allowed-tools: ["Bash(git:*)", "Bash(gh:*)", "Bash(node:*)", "Bash(jq:*)", "Read", "Glob", "Grep"]
argument-hint: ["PR number/url"]
---

# PR Review with Comment

Thin wrapper around `pr-review` — all methodology (foci, taxonomy, matrix, verdict logic, writing rules) lives there. This skill turns those findings into a single GitHub review, using `partition-findings.mjs` (in this skill's folder) to do the deterministic diff-matching and payload assembly.

```xml
<pull-request-review-and-comment>
  <task>Review the pull request identified by `$ARGUMENTS` and post the findings as one GitHub review. If this skill has reviewed this PR before, build on that prior review instead of starting cold.</task>
  <steps>
    <step num="1">Resolve `owner`, `repo`, and `pull_number` — from `$ARGUMENTS` if it's a full URL, otherwise via `gh pr view $ARGUMENTS --json number,headRepositoryOwner,headRepository`.</step>
    <step num="2">Check for prior reviews from this skill: resolve the authenticated login via `gh api user --jq .login`, then `gh api repos/{owner}/{repo}/pulls/{pull_number}/reviews --jq '[.[] | select(.user.login == "<login>")]'` and `gh api repos/{owner}/{repo}/pulls/{pull_number}/comments --jq '[.[] | select(.user.login == "<login>")]'`. If either returns entries, this is a re-review — enter <follow-up-mode/>. Otherwise proceed cold.</step>
    <step num="3">Load the pr-review skill and run it against `$ARGUMENTS` to produce structured findings, a summary, and a derived verdict. In follow-up mode, pass the prior findings in as context per <follow-up-mode/>. Do not skip or duplicate pr-review's methodology here.</step>
    <step num="4">Write the findings to a scratch file as `{ "verdict": ..., "findings": [...] }` (e.g. `/tmp/pr-findings.json`) — build via a direct file write, not inline-escaped JSON, to avoid quoting issues with emoji/backticks/suggestion fences. Capture `gh pr diff $ARGUMENTS` verbatim to `/tmp/pr.diff` and the review summary prose verbatim to `/tmp/pr-summary.md`. The summary prose (and every comment body) must contain **no em-dashes, en-dashes, or other dash-family separators** — use a semicolon, colon, or parentheses instead. `partition-findings.mjs` hard-fails the run if it finds one, so getting this right up front avoids a wasted round-trip.</step>
    <step num="5">Run `node ~/.claude/skills/pr-review-comment/partition-findings.mjs --findings /tmp/pr-findings.json --diff /tmp/pr.diff --summary-file /tmp/pr-summary.md --out /tmp/review-payload.json` (the script lives alongside this SKILL.md — adjust the path if this skill was loaded from a project-local `.claude/skills/` instead). This partitions findings per <mapping/>, composes the review body, **validates the summary and every comment body** (dash-family ban + a banned-emoji check on the summary — see <api-constraints/>), and writes the ready-to-POST payload. It prints `{inline, folded, offDiffDemoted}` stats to stdout. On non-zero exit, treat stderr as a hard failure — read the message, fix the offending prose in `/tmp/pr-summary.md` or the findings, and re-run step 5. Do not attempt to hand-build the payload as a fallback.</step>
    <step num="6">Create the review as **pending**: `gh api --method POST repos/{owner}/{repo}/pulls/{pull_number}/reviews --input /tmp/review-payload.json`. Omit `event` entirely — this is what keeps the review PENDING (author-only) rather than publishing immediately. Capture the returned `review_id`.</step>
    <step num="7">Auto-submit immediately using the verdict from pr-review: `gh api --method POST repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/events -f event="$VERDICT"`, where `$VERDICT` is one of `APPROVE` / `REQUEST_CHANGES` / `COMMENT`.</step>
  </steps>
  <api-constraints>
    <!-- Verified against GitHub REST docs (2022-11-28). State these plainly so the model never re-derives them live and never reintroduces the bug this skill used to have. -->
    <fact>The review-create endpoint's `comments[]` array accepts ONLY line-anchored entries (path, body, line, side, start_line, start_side). It does NOT accept `subject_type` — that field is response-only on this endpoint, not a request field. File-level comments therefore CANNOT be batched into a pending review. This is why file-level, cross-file, off-diff, and admiration findings all fold into the top-level review `body` instead — see <mapping/>.</fact>
    <fact>This endpoint is REST, not GraphQL. `gh api` calls it directly as REST. Don't chase a GraphQL explanation if a payload is rejected — check the payload shape against this block first.</fact>
    <fact>Omitting `event` on review-create leaves the review PENDING. `POST .../reviews/{review_id}/events` with an `event` value submits it.</fact>
    <fact>There is no endpoint to append file-level comments to an existing pending review after creation. Get the body right in the initial POST.</fact>
    <fact>`partition-findings.mjs` validates prose before writing the payload: the summary and every comment body are rejected if they contain an em-dash, en-dash, horizontal bar, or figure dash; the summary is additionally rejected if it contains 🆕, ✅, or ⚠️ (superseded vocabulary — 🆕 in particular renders as a GitHub `:new:` badge, not a plain glyph). This is a ban-list, not an allow-list — the summary can otherwise carry any emoji. This backstops a real incident where a posted review's follow-up delta used that banned vocabulary; see <follow-up-mode/> for the correct one.</fact>
  </api-constraints>
  <mapping>
    <!-- What partition-findings.mjs does — documentation of its behaviour, not instructions for the model to reimplement. -->
    <rule scope="line" condition="in-diff">→ `comments[]` entry: { path, line (or start_line+line for a range), side: "RIGHT", body: type-emoji-prefixed, + suggestion block if present }</rule>
    <rule scope="line" condition="off-diff">a finding whose target line isn't inside a diff hunk is demoted into the body's "Off-diff notes" section — never dropped, never misrouted into comments[]</rule>
    <rule scope="file">folds into the body's "File-scoped notes" section</rule>
    <rule scope="cross-file">folds into the body's "Cross-file notes" section</rule>
    <rule type="admiration">🟣 always folds into the body's "Accolades" section, one bullet per finding, each individually prefixed with 🟣 — never an inline comment, never a single umbrella heading absorbing the emoji, even when the finding is line-scoped</rule>
  </mapping>
  <follow-up-mode>
    <guide>Triggered when step 2 finds any prior review or review comment on this PR from the authenticated user. This means the skill has reviewed this PR before — treat it as a continuation, not a fresh review.</guide>
    <guide>Pass the prior findings (path, line, body, submitted_at) into the pr-review run as context. pr-review should evaluate whether each prior finding was addressed in the current diff, not re-flag it from scratch as if seeing the code for the first time.</guide>
    <guide>The composed summary leads with a short "Since my last review" delta before the current findings: one line each for what's now fixed (⚪), what's still open (⚫), and what's newly introduced (🟢). This is the only emoji vocabulary the delta may use — never 🆕 (renders as a GitHub `:new:` badge, not a plain glyph) and never ✅/⚠️ (superseded, off-palette next to the circle set). `partition-findings.mjs` hard-fails the run if it sees the banned set, so use the circles from the start. This is a brief acknowledgement, not a full changelog — a sentence per item, not a status table with links back to original threads.</guide>
    <guide>The verdict reflects the PR's current state, not a mechanical re-scan. A prior 🔴 that's now fixed should not resurface; a prior 🟡 left unaddressed can be repeated, but say so explicitly ("still open from last review") rather than presenting it as newly discovered.</guide>
  </follow-up-mode>
  <verdict-map>
    <rule>pr-review verdict "Request Changes" → event `REQUEST_CHANGES`</rule>
    <rule>pr-review verdict "Comment" → event `COMMENT`</rule>
    <rule>pr-review verdict "Approve" → event `APPROVE`</rule>
  </verdict-map>
  <toggle>
    <guide>To switch to manual submission (review pending in the GitHub UI until a human submits it): skip step 7 entirely and stop after step 6. One-line change — do not add complexity beyond deleting the step.</guide>
  </toggle>
</pull-request-review-and-comment>
```
