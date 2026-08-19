---
name: "PR: Handle Review"
description: "Work through a PR's change requests: verify each independently, fix what holds up, reply to every thread"
when_to_use: "When a PR has received review feedback (human or pr-review) and the change requests need triaging, fixing and answering rather than blind acceptance."
model: opus
effort: high
metadata:
  glyph: ᛟ
  family: pr
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Edit", "Write", "Bash(git:*)", "Bash(gh:*)", "Bash(jq:*)", "Bash(npm:*)", "Bash(bun:*)", "Bash(pnpm:*)", "Bash(deno:*)", "Bash(python3:*)", "Task"]
arguments: ["pr"]
argument-hint: "[PR number | URL]"
---

# Handle a PR Review

Takes the review feedback on a PR and closes the loop: independent verification of every change request, fixes for the ones that hold up, granular commits via `commit-batch`, and a reply on every thread. Two approval gates: one before any code changes, one before anything is posted to GitHub.

Reviewers are sometimes wrong. The core of this skill is that no change request is implemented on the reviewer's authority alone, and none is dismissed without evidence.

## Step 1: Resolve the PR

Resolve `owner`, `repo` and `pull_number` from `$ARGUMENTS`: directly if it's a full URL, otherwise via `gh pr view $ARGUMENTS --json number,headRefName,headRepositoryOwner,headRepository`. Resolve the authenticated login with `gh api user --jq .login`, needed to separate the reviewers' comments from our own.

Check out the PR branch if not already on it (`gh pr checkout {pull_number}`). Run `git status` first; if the working tree holds unrelated uncommitted work, stop and ask rather than mixing it into review fixes.

## Step 2: Gather the change requests

Two sources, both required:

1. **Review threads** (line-anchored). REST doesn't expose resolved state, so use GraphQL:

   ```bash
   gh api graphql -f query='query($owner:String!,$repo:String!,$pr:Int!){repository(owner:$owner,name:$repo){pullRequest(number:$pr){reviewThreads(first:100){nodes{isResolved isOutdated path line comments(first:50){nodes{databaseId author{login} body}}}}}}}' -f owner={owner} -f repo={repo} -F pr={pull_number}
   ```

   Keep threads where `isResolved` is false and the latest comment is **not** from the authenticated login (those are already answered). `isOutdated` threads stay in scope: the code moved, but the concern may not have.

2. **Review bodies**: `gh pr view {pull_number} --json reviews`; a `CHANGES_REQUESTED` or `COMMENTED` review body often carries file-level or cross-file asks that never became threads. Extract each actionable ask as its own item.

If there is nothing to handle, say so and stop.

## Step 3: Verify each request independently

For every item, read the actual code on the branch (not the diff snippet in the comment) and test the claim: does the bug exist, does the suggested change actually improve things, does it contradict an established project convention (`CLAUDE.md`, `.claude/**/*`, `docs/`)? Where a claim is checkable by running something (a test, a typecheck, a quick script), run it rather than reasoning about it.

**When there are 4 or more items to verify, dispatch one read-only subagent per item** (or per tightly-related cluster, when several items point at the same code) instead of working the loop sequentially. Each subagent gets the item's thread/review-body text, the branch context needed to locate it, and returns: the classification below, the `file:line` evidence, a minimal proposed fix description, and any regression test needed. Subagents verify only; none of them edits a file — that stays in Step 4, after Gate 1, so two proposed fixes never collide in the same file before you've seen both. Below 4 items, verify directly; dispatch overhead outweighs the saving.

Classify each item:

- **Valid**: the request holds; plan a concrete fix.
- **Valid but out of scope**: real, but belongs in a follow-up (new feature ask, pre-existing issue this PR didn't cause). Plan a deferral reply naming where it's tracked (offer to add it to the roadmap if one exists).
- **Invalid**: the request doesn't hold. Record the specific counter-evidence (`file:line`, test output, convention citation); this becomes the pushback reply.

## Gate 1: Triage approval

Present a triage table: thread reference, one-line summary of the ask, verdict, evidence, and the planned action (fix description / deferral / pushback). **Stop and await approval.** Adjust verdicts the user overrules; they may know context the code doesn't show.

## Step 4: Implement the approved fixes

1. Fix each approved item. **Follow-up commits only; never amend or rebase commits the reviewers have already seen.**
2. Discover the project's test, typecheck and lint commands from `package.json` (or ecosystem equivalent) and run all three until green. A red gate never proceeds to commit.
3. Once every approved item is fixed and the gate is green, invoke the `commit-batch` skill to split the fixes into granular commits and push. Its own plan-approval pause applies as normal: that pause belongs to `commit-batch`, not this skill; don't suppress it and don't treat it as a substitute for Gate 2.

## Step 5: Draft the replies

One reply per item, written per the writing-style skill's rules (no em-dashes, no contrastive couplets, lead with specifics):

- **Fixed**: what changed and the commit SHA that carries it. One or two sentences; the diff speaks.
- **Deferred**: acknowledge the point, say where it's now tracked, and why it's out of this PR's scope.
- **Pushback**: the evidence, politely: what the code actually does, with `file:line` citations or test output. State the disagreement plainly and leave the door open in your own words, matched to the thread's tone; never a stock closing phrase. The reviewer decides whether to press.

## Gate 2: Reply approval

Show every drafted reply against its thread. **Stop and await approval.** Nothing has been posted yet; edits here are free.

## Step 6: Post

- Thread replies: `gh api --method POST repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies -f body=...`, where `comment_id` is the `databaseId` of the thread's first comment.
- Review-body asks with no thread: one consolidated reply via `gh pr comment`, quoting each ask above its answer.
- **Never resolve threads**; the reviewer closes their own threads when satisfied.

Finish by reporting: items fixed / deferred / pushed back, commits pushed, replies posted. Offer to re-request review from the reviewers whose requests were addressed (`gh api --method POST repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers -f 'reviewers[]=...'`); offer, don't do it unasked.

## Red flags

**Never:** implement a request without verifying it first; dismiss a request without `file:line` evidence; amend or force-push over reviewed commits; post anything to GitHub before Gate 2 approval; resolve a reviewer's thread; push with a red test/typecheck/lint gate.

<raw-arguments value="$ARGUMENTS" />
