---
name: "Repo: Critique"
description: "{{ 𝛀𝛀𝛀 }} Probe the project for weaknesses"
model: opus
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep"]
argument-hint: [focus of analysis]
---

# Repo Critique

<overview>
  Identify weaknesses in this codebase's implementation.
</overview>
<steps>
  <step num="1">Analyse the codebase as a developer would when reading unfamiliar code.</step>
  <step num="2">If $ARGUMENTS contains content, focus analysis on that area.</step>
  <step num="3">Provide practical overview of weaknesses in implemented code only (not missing features).</step>
</steps>
<inputs>
  $ARGUMENTS
</inputs>
