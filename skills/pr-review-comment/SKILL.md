---
name: "PR: Review & Comment"
description: "{{ 𝛀𝛀𝛀 }} Review a pull request and post it as a GitHub review"
model: opus
disable-model-invocation: true
allowed-tools: ["Bash(git:*)", "Bash(gh:*)", "Read", "Glob", "Grep"]
argument-hint: ["PR number/url"]
---

# PR Review with Comment

Thin wrapper around `pr-review` — all methodology (foci, taxonomy, matrix, verdict logic, writing rules) lives there. This skill only turns those findings into a single GitHub review.

```xml
<pull-request-review-and-comment>
  <task>Review the pull request identified by `$ARGUMENTS` and post the findings as one GitHub review.</task>
  <steps>
    <step num="1">Load the pr-review skill and run it against `$ARGUMENTS` to produce structured findings, a summary, and a derived verdict. Do not skip or duplicate its methodology here.</step>
    <step num="2">Resolve `owner`, `repo`, and `pull_number` — from `$ARGUMENTS` if it's a full URL, otherwise via `gh pr view $ARGUMENTS --json number,headRepositoryOwner,headRepository`.</step>
    <step num="3">Map each finding to a review comment per <mapping/> and write the array to a scratch file (e.g. `/tmp/pr-review-comments.json`) — build via heredoc, not inline-escaped JSON, to avoid quoting issues.</step>
    <step num="4">Create the review as **pending**: `gh api --method POST repos/{owner}/{repo}/pulls/{pull_number}/reviews -f body="$SUMMARY" --input /tmp/pr-review-comments.json`. Omit `event` entirely — this is what keeps the review PENDING (author-only) rather than publishing immediately.</step>
    <step num="5">Auto-submit immediately using the verdict from pr-review: `gh api --method POST repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/events -f event="$VERDICT"`, where `$VERDICT` is one of `APPROVE` / `REQUEST_CHANGES` / `COMMENT`.</step>
  </steps>
  <mapping>
    <!-- Turns a pr-review finding into a GitHub review API comment entry -->
    <rule scope="line">{ "path": file, "line": line (or "start_line"/"line" for a range), "side": "RIGHT", "body": body (+ suggestion block if present) }</rule>
    <rule scope="file">{ "path": file, "subject_type": "file", "body": body }</rule>
    <rule scope="cross-file">fold into the top-level review `body` (the summary) instead of a comments[] entry</rule>
    <rule scope="line-but-off-diff">demote to a file-level comment: { "path": file, "subject_type": "file", "body": body } — never fail or misplace a comment whose target line isn't in the diff hunks</rule>
    <rule type="admiration">always file-level per pr-review's matrix, even when scope is "line" — never a line highlight</rule>
  </mapping>
  <verdict-map>
    <rule>pr-review verdict "Request Changes" → event `REQUEST_CHANGES`</rule>
    <rule>pr-review verdict "Comment" → event `COMMENT`</rule>
    <rule>pr-review verdict "Approve" → event `APPROVE`</rule>
  </verdict-map>
  <toggle>
    <guide>To switch to manual submission (review pending in the GitHub UI until a human submits it): skip step 5 entirely and stop after step 4. One-line change — do not add complexity beyond deleting the step.</guide>
  </toggle>
</pull-request-review-and-comment>
```
