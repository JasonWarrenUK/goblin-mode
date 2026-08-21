---
name: "PR: Update"
description: "Update a PR description to account for commits made since it was last written"
when_to_use: "When commits have been pushed to a branch after its PR was opened or last described; offer it whenever new work lands on a branch with an open PR rather than leaving the description stale."
model: sonnet
effort: medium
metadata:
  glyph: ᛊ
  family: pr
disable-model-invocation: false # invocable by Claude so it can offer a refresh when new commits leave the description stale; its approval step still gates the write
allowed-tools: ["Bash(git:*)", "Bash(gh:*)", "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/pr-facts.sh:*)", "Read", "Glob", "Grep"]
arguments: ["pr"]
argument-hint: "[PR number]"
---

# Update an Existing PR

Update the description of PR #$ARGUMENTS.

## Steps

### 1. Gather the facts in one call

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/pr-facts.sh $ARGUMENTS
```

It prints the PR metadata, the current body, the watermark (`<!-- pr-update-watermark: <sha> -->`, or "none" when the whole branch is new), every commit since it with per-commit stats, and the SHA to use as the next watermark. Analyse that dump rather than running exploratory `gh`/`git` calls. Exit **3** means no new commits; tell me the description is already up to date and stop. Exit **2**: report the script's message.

### 2. Analyse the new commits

From the dump, understand what changed and why. Group related commits into coherent change categories. Run `git show <sha>` on a specific commit only where the stat alone can't tell you what a change is.

### 3. Produce the updated PR body

Take the existing body (in the dump) and update it:

- **Do not rewrite from scratch.** Preserve existing content unless it is now inaccurate.
- The body structure follows `${CLAUDE_PLUGIN_ROOT}/templates/pr-description.md` (the same template `goblin:pr-create` fills); keep updates within that structure rather than adding new top-level sections.
- **Integrate, never append.** Fold the new work into the existing sections: `## Changes` gains or amends entries, summaries absorb the new scope, stale statements get corrected in place. Bolting an "updates since" block onto the end of the description is the failure mode this step exists to prevent: the reader must see one coherent current description, not a base version plus a changelog of patches.
- **Provenance lives in its own trail, not in the body content.** Maintain a single collapsible block immediately above the watermark:

  ```markdown
  <details><summary>Update history</summary>

  - 2026-08-13: folded in <one-line summary> (`<first-sha>..<last-sha>`)
  </details>
  ```

  Append one dated line per update run. This block records *that* and *when* the description changed; the substantive content itself always lands in the sections above.
- If the description references behaviour that has changed, correct it.
- Insert or replace the watermark comment at the very end of the body, using the `next watermark sha` from the dump:

```text
<!-- pr-update-watermark: <latest-sha> -->
```

### 4. Show me the diff

Display the updated body in full and a brief summary of what changed vs the previous description. **Wait for my approval.**

### 5. Apply the update

Once approved: `gh pr edit $ARGUMENTS --body "<updated body>"`. Confirm success.
