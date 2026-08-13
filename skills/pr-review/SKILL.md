---
name: "PR: Review"
description: "{{ 𝛀𝛀𝛀 }} Review a pull request and post it as a GitHub review"
when_to_use: "When the user explicitly asks for a review posted to GitHub (inline comments + verdict), or when next-task-ship's Step 7 self-review runs. Posts to the PR immediately — for a read-only review printed to the terminal use pr-review-dry_run instead, and never invoke this speculatively."
model: opus
effort: high
disable-model-invocation: false # invocable so next-task-ship's Step 7 self-review can call it; it posts to GitHub, so never invoke without an explicit ask or that orchestration
allowed-tools: ["Bash(git:*)", "Bash(gh:*)", "Bash(node:*)", "Bash(jq:*)"]
arguments: ["mode", "pr"]
argument-hint: "[loose|strict] [PR number | URL]"
---

# PR Review with Comment

Thin wrapper around `pr-review-dry_run` — all methodology (foci, taxonomy, matrix, verdict logic, writing rules) lives there, including the loose/strict mode split. This skill only parses the mode keyword out of `$ARGUMENTS` and forwards it; it turns the resulting findings into a single GitHub review, using `partition-findings.mjs` (in this skill's folder) to do the deterministic diff-matching and payload assembly. Everything stays in context and in a single shell pipeline: no scratch files are read or written at any point.

```xml
<pull-request-review-and-comment>
  <task>Review the pull request identified within `$ARGUMENTS` (an optional loose/strict mode keyword plus the PR number/URL, in either order — see step 1) and post the findings as one GitHub review. If this skill has reviewed this PR before, build on that prior review instead of starting cold.</task>
  <steps>
    <step num="1">Before resolving the PR, split `$ARGUMENTS` into the mode keyword (`loose` or `strict`, if present, case-insensitive, order-agnostic) and the PR identifier. Pass only the identifier onward: resolve `owner`, `repo`, and `pull_number` — from it if it's a full URL, otherwise via `gh pr view <identifier> --json number,headRepositoryOwner,headRepository`.</step>
    <step num="2">Check for prior reviews from this skill: resolve the authenticated login via `gh api user --jq .login`, then `gh api repos/{owner}/{repo}/pulls/{pull_number}/reviews --jq '[.[] | select(.user.login == "<login>")]'` and `gh api repos/{owner}/{repo}/pulls/{pull_number}/comments --jq '[.[] | select(.user.login == "<login>")]'`. If either returns entries, this is a re-review — enter <follow-up-mode/>. Otherwise proceed cold.</step>
    <step num="3">Load the pr-review-dry_run skill and run it against the resolved PR identifier, forwarding the resolved mode (loose applies when no keyword was given), to produce structured findings, a summary, and a derived verdict. In follow-up mode, pass the prior findings in as context per <follow-up-mode/>. Do not skip or duplicate pr-review-dry_run's methodology here. Keep the findings, summary, and verdict in context — nothing gets written to disk at any point in this skill.</step>
    <step num="4">Assemble one JSON object in context (never on disk): `{ "verdict": ..., "findings": [...], "diff": "<verbatim gh pr diff output for the resolved PR identifier>", "summary": "<verbatim review summary prose>" }`. The summary prose (and every comment body inside `findings[].body`) must contain **no em-dashes, en-dashes, or other dash-family separators** — use a semicolon, colon, or parentheses instead. `partition-findings.mjs` hard-fails the run if it finds one, so getting this right up front avoids a wasted round-trip.</step>
    <step num="5">Feed that JSON straight into a single pipeline, with `partition-findings.mjs` reading it from stdin and `gh api` reading the resulting payload from stdin in turn — nothing touches disk at any point:
      <code>
node ${CLAUDE_SKILL_DIR}/partition-findings.mjs <<'JSON_EOF' | gh api --method POST repos/{owner}/{repo}/pulls/{pull_number}/reviews --input -
{ "verdict": "...", "findings": [...], "diff": "...", "summary": "..." }
JSON_EOF
      </code>
      `${CLAUDE_SKILL_DIR}` resolves to this skill's directory wherever it is installed. The script partitions findings per <mapping/>, composes the review body, **validates the summary and every comment body** (dash-family ban + a banned-emoji check on the summary — see <api-constraints/>), and writes the ready-to-POST payload to stdout; stats `{inline, folded, offDiffDemoted}` go to stderr so stdout stays pure JSON for `gh api` to consume. Omitting `event` on the `gh api` call is what keeps the review **pending** (author-only) rather than publishing immediately. Capture the returned `review_id` from the response. On non-zero exit from the node step, treat stderr as a hard failure — read the message, fix the offending prose in the heredoc's summary or findings, and re-run the whole pipeline. Do not attempt to hand-build the payload as a fallback, and do not split this into separate write-then-read steps through a file.</step>
    <step num="6">Auto-submit immediately using the verdict from pr-review-dry_run: `gh api --method POST repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/events -f event="$VERDICT"`, where `$VERDICT` is one of `APPROVE` / `REQUEST_CHANGES` / `COMMENT`.</step>
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
    <guide>Pass the prior findings (path, line, body, submitted_at) into the pr-review-dry_run run as context. pr-review-dry_run should evaluate whether each prior finding was addressed in the current diff, not re-flag it from scratch as if seeing the code for the first time.</guide>
    <guide>The composed summary leads with a short "Since my last review" delta before the current findings: one line each for what's now fixed (⚪), what's still open (⚫), and what's newly introduced (🟢). This is the only emoji vocabulary the delta may use — never 🆕 (renders as a GitHub `:new:` badge, not a plain glyph) and never ✅/⚠️ (superseded, off-palette next to the circle set). `partition-findings.mjs` hard-fails the run if it sees the banned set, so use the circles from the start. This is a brief acknowledgement, not a full changelog — a sentence per item, not a status table with links back to original threads.</guide>
    <guide>The verdict reflects the PR's current state, not a mechanical re-scan. A prior 🔴 that's now fixed should not resurface; a prior 🟡 left unaddressed can be repeated, but say so explicitly ("still open from last review") rather than presenting it as newly discovered.</guide>
  </follow-up-mode>
  <verdict-map>
    <guide>Mode selection happens in pr-review-dry_run. This map is mode-agnostic: it translates the derived verdict, whichever rule set produced it.</guide>
    <rule>pr-review-dry_run verdict "Request Changes" → event `REQUEST_CHANGES`</rule>
    <rule>pr-review-dry_run verdict "Comment" → event `COMMENT`</rule>
    <rule>pr-review-dry_run verdict "Approve" → event `APPROVE`</rule>
  </verdict-map>
  <toggle>
    <guide>To switch to manual submission (review pending in the GitHub UI until a human submits it): skip step 6 entirely and stop after step 5. One-line change — do not add complexity beyond deleting the step.</guide>
  </toggle>
</pull-request-review-and-comment>
```
