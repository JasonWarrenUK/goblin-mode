---
name: "PR: Review (Dry Run)"
description: "Review a pull request's diff and print structured findings to the terminal. Holds the canonical review methodology that pr-review and branch-qa_review both call."
when_to_use: "When you want a read-only review of a PR's diff printed to the conversation: for a posted GitHub review use pr-review, which calls this skill internally."
model: opus
effort: high
metadata:
  glyph: ᛟ
  family: pr
  goblin-spinner: reading the diff|drafting findings|printing verdicts
disable-model-invocation: false # required so pr-review can call it
allowed-tools: ["Bash(git:*)", "Bash(gh:*)", "Bash(cd:*)", "Bash(npm:*)", "Bash(bun:*)", "Bash(pnpm:*)", "Bash(deno:*)", "Bash(python3:*)", "Bash(pytest:*)", "Bash(poetry:*)", "Bash(poe:*)", "Bash(go:*)", "Read", "Glob", "Grep"]
disallowed-tools: ["Edit", "Write", "NotebookEdit"] # reviews, never fixes
arguments: ["mode", "pr"]
argument-hint: "[loose|strict] [PR number | URL]"
---

# PR Review

Canonical review methodology. Produces structured findings only; **never posts to GitHub**. `pr-review` loads this skill and handles posting; keep all methodology here to avoid divergence.

```xml
<pull-request-review>
  <task>Review the pull request identified within `$ARGUMENTS` (an optional loose/strict mode keyword plus the PR number/URL, in either order) and produce structured findings. Do not post anything to GitHub.</task>
  <steps>
    <step num="1">Split `$ARGUMENTS` into the mode keyword (`loose` or `strict`, if present, case-insensitive, order-agnostic; absent means loose) and the PR identifier; see <verdict/> for the mode rule. Run `gh pr view <identifier>` to get PR title, description, and metadata</step>
    <step num="2">Run `gh pr diff <identifier>` to get the full diff: always the PR against its own base branch (`main` normally; the parent branch when the PR is a stacked layer), regardless of the local branch checked out. Never widen a stacked PR's diff to `origin/main`; the layers below it are their own PRs' reviews, not this one's</step>
    <step num="3">Research project conventions stored in `CLAUDE.md`, `.claude/**/*` and `docs/*`. Before critiquing implementation, check whether the dev is following established project practice</step>
    <step num="3a">In follow-up mode (prior findings were passed in): before reading for anything new, go through each prior finding and decide fixed or still open against the current diff, with the commit that fixed it where one exists. That list is the delta the summary opens with (see <output/>); a still-open finding is repeated as "still open from last review", never presented as newly found. Only then look for new issues</step>
    <step num="3b">In `strict` mode, run the project's test suite on the PR head; see <test-run/>. A diff that reads correctly can still fail the suite: fixes in October 2026 that looked right in review failed the wider suite and edge-case data on the next round. A red suite is a finding on its own (the <blocking-gate/> trigger for a failing test), with the failing test names and the first assertion message in the body. Loose mode skips the run and says so in the terminal output</step>
    <step num="4">Classify every finding by <taxonomy/> type and by scope (line / file / cross-file)</step>
    <step num="5">Where a line-scoped 🔴/🟠/🟡 finding has a concrete fix, write it as a committable ```suggestion block per <suggestions/></step>
    <step num="6">Write every comment body **and the `summary`** (including the follow-up delta, when in that mode) per the writing-style skill's anti-slop rules (no em dashes, no contrastive couplets, no parade-of-examples, lead with specifics). This isn't just style guidance here: when this skill's output feeds `pr-review`, its `partition-findings.mjs` hard-fails the post on any em-dash/en-dash in the summary or a comment body. Get it right here, upstream, rather than relying on that gate to catch it</step>
    <step num="7">Emit findings using <output/>. This is the full deliverable; stop here, nothing gets posted</step>
  </steps>
  <foci>
    <focus>Correctness: will this break anything?</focus>
    <focus>Security: any obvious vulnerabilities?</focus>
    <focus>Glaring convention violations</focus>
    <focus>Reinforcement: genuine strengths worth calling out, not token praise</focus>
  </foci>
  <taxonomy>
    <!-- This is the only taxonomy. -->
    <row emoji="🔴" type="major changes" ceiling="Request Changes">Would be wrong to merge as-is. Decided by the closed trigger list in <blocking-gate/>, never by how big or effortful the fix is</row>
    <row emoji="🟠" type="minor changes" ceiling="Comment (strict) / Approve (loose)">Correct as written, but would be better changed. Same ceiling and treatment as nits</row>
    <row emoji="🟡" type="nits" ceiling="Comment (strict) / Approve (loose)">Nice to have</row>
    <row emoji="🟣" type="admiration" ceiling="Approve">Accolade: only when genuinely warranted</row>
  </taxonomy>
  <blocking-gate>
    <guide>🔴 is a merge gate, not a severity band. The question is never "how bad is this?" but "is this a thing on the list below?". Size and effort-to-fix are irrelevant: a one-character fix is 🔴 if it trips a trigger, and a day of work is 🟠 if it doesn't.</guide>
    <guide>The trigger list is closed. Only these block:</guide>
    <trigger>Correctness bug on a reachable path: wrong output, crash, hang or silent no-op. Reachable means you can state the concrete input, state or call sequence that produces it; if you cannot name that trigger case, it is 🟠, not 🔴</trigger>
    <trigger>Security issue: injection, auth bypass, leaked secret or credential, missing validation at a trust boundary, RLS gap on multi-tenant data</trigger>
    <trigger>Data loss or migration hazard: destructive or irreversible schema change, unguarded delete, a multi-step write that isn't in a transaction</trigger>
    <trigger>Breaking change to an exported or public contract without the `!` marker or `BREAKING CHANGE:` footer on its commit</trigger>
    <trigger>Violation of a documented convention that itself guards correctness, security or data integrity: RLS on multi-tenant tables, validation at boundaries, transactions around multi-step writes, secrets kept out of the repo. Style, prose, naming and formatting conventions never block, however plainly `CLAUDE.md` states them; those are 🟠 at most</trigger>
    <trigger>A test that asserts nothing, is skipped or is committed failing, with no note explaining why; in strict mode this includes any test the <test-run/> finds failing on the PR head</trigger>
    <guide>Anything you believe should block but that trips no trigger is written as 🟠 with an explicit "I'd argue this should block: &lt;reason&gt;" line ending its body. That line is the signal for growing this list deliberately; never promote such a finding to 🔴 on your own judgement, in either mode. That line is live prose inside `findings[].body`, so it carries the same dash ban as every other body; a stray em-dash there hard-fails the whole post downstream.</guide>
  </blocking-gate>
  <matrix>
    <!-- Type x Scope -> where the comment anchors + suggestion eligibility -->
    <!-- "Review body" anchors are sections of the top-level review comment: GitHub's review API has no file-level comments (see pr-review's <api-constraints/>), and a line-scoped finding whose line isn't in the diff is demoted to the body's "Off-diff notes" section with its location kept. -->
    <row type="major/minor changes, nits" scope="line" anchor="line highlight (inline diff comment)" suggestion="yes, if a concrete fix exists" />
    <row type="major/minor changes, nits" scope="file" anchor="review body, File-scoped notes section" suggestion="no" />
    <row type="major/minor changes, nits" scope="cross-file" anchor="review body, Cross-file notes section" suggestion="no" />
    <row type="admiration" scope="line" anchor="review body, Accolades section; admiration never uses a line highlight, even when the praise is line-scoped" suggestion="no" />
    <row type="admiration" scope="file" anchor="review body, Accolades section" suggestion="no" />
    <row type="admiration" scope="cross-file" anchor="review body, Accolades section" suggestion="no" />
  </matrix>
  <test-run>
    <guide>Never check the PR out in the current checkout: it may be another session's, and `pr-land` forbids switching the main checkout for the same reason. Fetch the head by its pull ref (GitHub serves `pull/{number}/head` for a fork's PR too, where the head branch is not on `origin`) and run in a detached, throwaway worktree, then remove it from outside:</guide>
    <code>
git fetch origin pull/{number}/head \
  && git worktree add --detach "${TMPDIR:-/tmp}/pr-review-{repo}-{number}" FETCH_HEAD \
  && cd "${TMPDIR:-/tmp}/pr-review-{repo}-{number}"
# install if the lockfile asks for it, then the suite:
# the project's own command, read from package.json scripts, pyproject's poe tasks, a Makefile or CLAUDE.md
cd "$(git rev-parse --path-format=absolute --git-common-dir)/.." && git worktree remove --force "${TMPDIR:-/tmp}/pr-review-{repo}-{number}"
    </code>
    <guide>The suite command is the project's, discovered rather than guessed: `package.json`'s `test` script, `pyproject.toml`'s poe `test` task or `pytest`, `go test ./...`, whatever `CLAUDE.md` names. No discoverable suite: say so in the summary and move on; never invent one. A suite that needs a running service or a database the worktree cannot reach is reported as not run, with the reason, not as failing.</guide>
    <guide>The worktree is removed whether the suite passed or not; a stale `pr-review-*` worktree from an earlier run is removed before a new one is added.</guide>
  </test-run>
  <suggestions>
    <guide>Emit a ```suggestion block only for line-scoped 🔴/🟠/🟡 findings with a concrete, single-location fix.</guide>
    <guide>Skip suggestions where the fix spans multiple non-contiguous lines, requires judgement calls, or isn't safely committable as-is.</guide>
    <guide>Never emit suggestions for admiration; there's nothing to commit.</guide>
  </suggestions>
  <verdict>
    <guide>Two modes, `loose` and `strict`, either given explicitly anywhere in `$ARGUMENTS` (order-agnostic, case-insensitive). Absent keyword means loose. A mode keyword is never a PR identifier. Any other unrecognised bare word in the mode slot is an error, not a silent fallback.</guide>
    <guide>Mode changes the verdict only. Findings, taxonomy, scope classification, suggestion eligibility and comment bodies are identical in both modes; a 🟠 is still written and posted as a 🟠. <blocking-gate/> is mode-independent: loose never softens a trigger into 🟠, strict never promotes a non-trigger into 🔴.</guide>
    <guide>Derive one overall verdict from the highest ceiling present across all findings (highest-ceiling-wins):</guide>
    <rule mode="both">Any 🔴 present → Request Changes</rule>
    <rule mode="strict">Else any 🟠 or 🟡 present → Comment</rule>
    <rule mode="loose">Else any 🟠 or 🟡 present → Approve (the Comment rung collapses; findings still post as inline comments)</rule>
    <rule mode="both">Else only 🟣 present (or no findings) → Approve</rule>
    <guide>Loose posts no marker to the PR explaining the collapsed verdict. The finding emoji already carry severity. Report the mode in the terminal output only.</guide>
  </verdict>
  <guides>
    <guide>Keep it concise. Flag only the most important issues; skip minor style nits unless they're genuinely worth a 🟡. Concision applies to 🟠 and 🟡 alone: every finding that trips a <blocking-gate/> trigger gets reported, however small it looks.</guide>
    <guide>Before critiquing implementation, check whether the dev is following established project practice.</guide>
    <guide>Omit any type that has no entries. Only include 🟣 findings if there's something genuinely worth praising; token praise is worse than none.</guide>
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
    - `summary`: overall review body (top-level comment content). When run in follow-up mode (see `pr-review`'s `<follow-up-mode/>`), the leading "Since my last review" delta uses only ⚪ fixed / ⚫ still open / 🟢 new; never 🆕 (renders as a GitHub `:new:` badge) or ✅/⚠️ (superseded, off-palette)
    - `verdict`: Request Changes | Comment | Approve, derived per <verdict/>
    - `mode`: loose | strict; which rule set produced the verdict, so the caller doesn't have to re-derive it
    - `tests`: passed | failed (with the failing names) | not run (with the reason); strict mode always fills this
  </output>
</pull-request-review>
```
