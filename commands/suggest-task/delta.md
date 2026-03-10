---
description: "{{ 𝚫𝚫𝚫 }} Suggest the next logical task based on codebase analysis"
argument-hint: [optional focus area]
model: haiku
---

Analyse the current state of the codebase, then compare it to the project documentation. Suggest the next logical task I can complete.

## Rules
1. If the task will take longer than 45 minutes, subdivide it and suggest the first subtask.
2. If $ARGUMENTS contains content, focus suggestions on that area.
3. Conserve tokens by being selective in which files you read.
4. Where possible, use dev scripts in @./package.json & @./scripts rather than reading file content.

<focus value="$ARGUMENTS" />
