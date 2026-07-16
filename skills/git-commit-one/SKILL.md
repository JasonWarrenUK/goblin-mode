---
name: "Commit: One"
description: "{{ 𝚫𝚫𝚫 }} Generate a commit message. If nothing staged, stage all changes."
model: haiku
effort: low
disable-model-invocation: true
allowed-tools: ["Bash(git:*)"]
---

## Current state

```!
git status --short
git diff --cached --stat
```

## Steps

1. Per the state above: if no changes staged, stage all. If files are already staged, *do not* stage more files.
2. Generate commit message per conventional commits format.
3. Show message and await approval:
    - If approved, push to upstream
    - If changes requested, revise and repeat

<template format-reference="https://www.conventionalcommits.org/en/v1.0.0/">
  `type(scope?): description\n\nbody (optional)\n\nBREAKING CHANGE: footer (if applicable)`
</template>

<conventions>
  - Subject line: imperative mood, lowercase, no period, max 50 chars (`add feature` not `added feature` or `adds feature`)
  - Body: explain *what* and *why*, not *how*; wrap at 72 chars
</conventions>
