---
name: "Analyse: Investigate Target"
description: "Investigate a codebase in detail and write findings to a document, for a named concept, subsystem or question"
when_to_use: "When you need a deep, written-down investigation of how something works or why it's built a certain way: deeper than a quick grep, with output that persists as a doc."
model: opus
effort: high
metadata:
  glyph: ᛟ
  family: analyse
disable-model-invocation: true
# Forked, but on the default general-purpose agent rather than Explore: this
# skill Writes its investigation doc, and Explore is read-only. $ARGUMENTS
# must carry the whole brief.
context: fork
background: false # keep the full tool set (backgrounded forks run with a narrower one, and this skill needs Write) and deliver the doc in-turn
allowed-tools: ["Read", "Glob", "Grep", "Write"]
argument-hint: "[focus of investigation]"
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
