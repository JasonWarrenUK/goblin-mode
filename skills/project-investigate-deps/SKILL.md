---
name: "Repo: Analyse Package Deps"
description: "{{ 𝛀𝛀𝛀 }} Investigate this repo's dependencies in detail"
model: opus
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Bash(~/.claude/library/scripts/deps-dump.sh:*)", "WebSearch", "WebFetch"]
argument-hint: ["optional: concerning dep"]
---

# Repo Package & Dependency Analysis

<overview>
  Provide an in-depth analysis of this codebase's package dependencies, particularly $ARGUMENTS.
</overview>
<steps>
  1. Run `"$HOME"/.claude/library/scripts/deps-dump.sh` — it detects the package manager from lockfiles and dumps declared versions, outdated report and audit output in one pass. Analyse that dump rather than orchestrating the package-manager CLIs yourself.
  2. For anything the dump flags (or $ARGUMENTS names), check deprecation notices & security advisories online.
  3. Suggest fixes and updates, ordered by risk.
</steps>
