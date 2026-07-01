---
name: "PR: Create Wordy"
description: "{{ ƔƔƔ }} Create a pull request to main"
model: sonnet
disable-model-invocation: true
allowed-tools: ["Bash(git:*)", "Bash(gh:*)", "Read", "Glob", "Grep"]
argument-hint: [issue numbers]
---

# Open a PR to `main`

## Steps

1. Look at the commits on this branch
2. Analyse the overall effect of these changes if merged into `main`
3. Use `<template>` to write the pull request content
4. Check for my approval, then:
    - If approved, create the PR to `main`
    - If not, incorporate changes and repeat step 3

```xml
<rules>
  <title-rules>
    <rule num="1">Brief and descriptive</rule>
    <rule num="2">Use title case</rule>
    <rule num="3">Be understandable to non-devs</rule>
  </title-rules>
  <overview-rules>
  	<rule num="1">At the end of the overview, use GH issue-closing syntax to note this PR closes the following issues: $ARGUMENTS</rule>
  </overview-rules>
  <summary-rules>
  	<rule num="1">Describe the PR with a non-technical, absurd metaphor.</rule>
  </summary-rules>
  <tldr-rules>
  	<rule num="1">List any steps devs must take after pulling this down</rule>
  </tldr-rules>
  <changes-rules>
	  <rule num="1">Break changes into files or categories depending on PR scope.</rule>
	  <rule num="2">Use collapsible details.</rule>
  </changes-rules>
</rules>
```

## Template

```md
# {{ title }}
## Overview
{{ overview }}
## Summary
{{ absurd metaphor }}
> [!TIP]
> {{ tldr }}
---
## Changes
{{ changes with collapsible details }}
---
```
