---
name: "Repo: Investigate Target"
description: "{{ 𝛀𝛀𝛀 }} Investigate a codebase in detail"
model: opus
disable-model-invocation: true
# Forked, but on the default general-purpose agent rather than Explore: this
# skill Writes its investigation doc, and Explore is read-only. $ARGUMENTS
# must carry the whole brief.
context: fork
allowed-tools: ["Read", "Glob", "Grep", "Write"]
argument-hint: [focus of investigation]
---

# Targeted Repo Investigation

<overview>
  Provide an in-depth analysis of this codebase, focussing squarely on $ARGUMENTS.
</overview>
<steps>
  <step num="1">Probe deeply into all files & the relationships between them.</step>
  <step num="2">If no focus is specified, consider the codebase as a whole.</step>
  <step num="3">Create a structured .md document in @docs/investigations/ with your findings</step>
</steps>
