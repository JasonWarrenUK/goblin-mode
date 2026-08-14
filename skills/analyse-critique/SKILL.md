---
name: "Analyse: Critique"
description: "Probe the project for architectural weaknesses, technical debt and risk; a deliberately critical read"
when_to_use: "When you want an honest 'what's actually wrong here' pass on a codebase: before a big refactor, before onboarding someone or when something feels fragile but you can't name why."
model: opus
effort: high
metadata:
  glyph: ᛟ
  family: analyse
disable-model-invocation: true
# Forked into a read-only Explore agent: needs no conversation history, and
# its large read footprint stays out of the main context. $ARGUMENTS must
# carry the whole brief.
context: fork
agent: Explore
allowed-tools: ["Read", "Glob", "Grep"]
argument-hint: "[focus of analysis]"
---

# Repo Critique

<overview>
  Identify weaknesses in this codebase's implementation.
</overview>
<steps>
  <step num="1">Analyse the codebase as a developer would when reading unfamiliar code.</step>
  <step num="2">If $ARGUMENTS contains content, focus analysis on that area.</step>
  <step num="3">Provide practical overview of weaknesses in implemented code only (not missing features).</step>
  <step num="4">Close the report by noting that, if it's worth sharing, the findings map onto `artefact-audit`'s JSON shape and its render-only mode produces a shareable HTML page. (This skill runs in a read-only fork; rendering happens back in the main conversation if the offer is taken.)</step>
</steps>
<inputs>
  $ARGUMENTS
</inputs>
