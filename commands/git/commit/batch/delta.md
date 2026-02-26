---
description: "{{ 𝚫𝚫𝚫 }} Split uncommitted changes into granular commits."
model: haiku
disable-model-invocation: true
---

## Steps
1. Run `git diff --stat HEAD` and `git status` to get a full picture of all changes.
2. Analyse the changes and group them into logical commit units — each group should represent a single coherent change (e.g. one feature, one fix, one refactor).
3. Present the proposed commit plan as a numbered list:
   - Group name / files involved
   - Suggested commit message (conventional commits format)
4. Await approval:
   - If approved, execute commits sequentially: stage the relevant files for each group, commit, then move to the next.
   - If changes requested, revise the plan and repeat from step 3.
5. After all commits, push to upstream.

## Grouping Guidelines
- Prefer smaller, atomic commits over large ones
- Keep unrelated changes in separate commits even if they touch the same area
- Config/dependency changes separate from feature code
- Test changes alongside the code they test (same commit), unless the test is independent
- Generated files (lockfiles, build artefacts) get their own commit if significant

<template format-reference="https://www.conventionalcommits.org/en/v1.0.0/">
  `type(scope?): description\n\nbody (optional)\n\nBREAKING CHANGE: footer (if applicable)`
</template>

<conventions>
  - Subject line: imperative mood, lowercase, no period, max 50 chars (`add feature` not `added feature` or `adds feature`)
  - Body: explain *what* and *why*, not *how*; wrap at 72 chars
</conventions>
