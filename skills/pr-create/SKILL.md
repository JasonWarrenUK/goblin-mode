---
name: "PR: Create"
description: "{{ ƔƔƔ }} Create a pull request to main — wordy or shiny (with screenshots), ready-for-review or draft"
when_to_use: "When a branch is ready (or nearly ready) to open as a PR and needs a description written from its commits."
model: sonnet
disable-model-invocation: true
allowed-tools: ["Bash(git:*)", "Bash(gh:*)", "Read", "Glob", "Grep"]
argument-hint: "[shiny|wordy] [draft] [screenshot files or issue numbers...]"
---

# Open a PR to `main`

Replaces the former pr-shiny-create / pr-shiny-draft / pr-wordy-create / pr-wordy-draft quartet: one skill, two axes.

```xml
<pull-request-create>
    <arguments>
        <axis name="style">First token of $ARGUMENTS if it is `shiny` or `wordy`. Default: `wordy`. Shiny adds a Screenshots section.</axis>
        <axis name="mode">If the token `draft` appears anywhere in $ARGUMENTS, create the PR as a draft. Default: ready for review.</axis>
        <axis name="extras">Remaining tokens: screenshot file paths (shiny) or issue numbers to close (wordy). Empty means no screenshots section content / no issue-closing line — never invent either.</axis>
    </arguments>
    <steps>
        <step num="1">Look at the commits on this branch (`git log` against `origin/main`)</step>
        <step num="2">Analyse the overall effect of these changes if merged into `main`</step>
        <step num="3">Fill the template at `~/.claude/library/templates/pr-description.md` exactly — each {{ slot }} describes its content. For wordy style, omit the Screenshots block entirely (and its trailing `---`). For shiny style, one collapsible `&lt;details&gt;` per named screenshot.</step>
        <step num="4">Show the draft description and **stop for approval**. If changes are requested, incorporate them and repeat step 3.</step>
        <step num="5">On approval, create the PR to `main` with `gh pr create` — add `--draft` when mode is draft. Report the PR URL.</step>
    </steps>
    <rules>
        <rule>The template is the single source of the body structure — do not restructure it.</rule>
        <rule>Title: brief, descriptive, title case, understandable to non-devs.</rule>
        <rule>Summary: a non-technical, absurd metaphor.</rule>
        <rule>TL;DR: steps devs must take after pulling this down.</rule>
        <rule>Changes: break into files or categories depending on PR scope; use collapsible details.</rule>
    </rules>
</pull-request-create>
```
