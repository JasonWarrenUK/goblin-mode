---
name: "PR: Create"
description: "Create a pull request to main, or a stacked PR onto a parent branch: wordy or shiny (with screenshots), ready-for-review or draft"
when_to_use: "When a branch is ready (or nearly ready) to open as a PR and needs a description written from its commits; reached via next-task-ship's Step 6, branch-qa_review's Ready verdict or an explicit ask. Never invoke just because a branch looks finished; its approval step gates the actual creation."
model: sonnet
effort: medium
metadata:
  glyph: ᛊ
  family: pr
disable-model-invocation: false # invocable so next-task-ship (Step 6) and branch-qa_review's Ready offer can call it; its own approval step gates PR creation
allowed-tools: ["Bash(git:*)", "Bash(gh:*)", "Read", "Glob", "Grep"]
argument-hint: "[shiny|wordy] [draft] [base <branch>] [screenshot files or issue numbers...]"
---

# Open a PR to `main` (or, stacked, to a parent branch)

Replaces the former pr-shiny-create / pr-shiny-draft / pr-wordy-create / pr-wordy-draft quartet: one skill, two axes.

```xml
<pull-request-create>
    <arguments>
        <axis name="style">First token of $ARGUMENTS if it is `shiny` or `wordy`. Default: `wordy`. Shiny adds a Screenshots section.</axis>
        <axis name="mode">If the token `draft` appears anywhere in $ARGUMENTS, create the PR as a draft. Default: ready for review.</axis>
        <axis name="auto">If the token `auto` appears anywhere in $ARGUMENTS (passed only by an orchestrating skill whose own gate already ran, e.g. next-task-ship), skip step 4's pause and create immediately.</axis>
        <axis name="base">The token pair `base &lt;branch&gt;` anywhere in $ARGUMENTS sets the PR's base branch. Default: `main`. A non-main base makes this a **stacked PR** layered on the parent branch's open PR; see ~/.claude/library/references/stacked-prs.md.</axis>
        <axis name="extras">Remaining tokens: screenshot file paths (shiny) or issue numbers to close (wordy). Empty means no screenshots section content / no issue-closing line; never invent either.</axis>
    </arguments>
    <steps>
        <step num="1">Look at the commits on this branch (`git log` against `origin/&lt;base&gt;`, default `origin/main`); for a stacked PR this scopes the log to this layer only, which is the point</step>
        <step num="2">Analyse the overall effect of these changes if merged into the base branch</step>
        <step num="3">Fill the template at `~/.claude/library/templates/pr-description.md` exactly; each {{ slot }} describes its content. For wordy style, omit the Screenshots block entirely (and its trailing `---`). For shiny style, one collapsible `&lt;details&gt;` per named screenshot.</step>
        <step num="4">Show the draft description and **stop for approval**; if changes are requested, incorporate them and repeat step 3. Under the `auto` token, show the description but do not pause.</step>
        <step num="5">On approval, create the PR with `gh pr create --base &lt;base&gt;`; add `--draft` when mode is draft. For a non-main base, then link it into the parent's stack (`gh stack link &lt;parent-pr&gt; &lt;new-pr&gt;`); under `auto` do this immediately, otherwise offer it. Report the PR URL.</step>
    </steps>
    <rules>
        <rule>The template is the single source of the body structure: do not restructure it.</rule>
        <rule>When the base isn't main, the Overview opens by naming the parent: "Layer on #&lt;parent-pr&gt;; review that first." The rest of the description covers this layer only.</rule>
        <rule>Title: brief, descriptive, title case, understandable to non-devs.</rule>
        <rule>Summary: a non-technical, absurd metaphor.</rule>
        <rule>TL;DR: steps devs must take after pulling this down.</rule>
        <rule>Changes: break into files or categories depending on PR scope; use collapsible details.</rule>
    </rules>
</pull-request-create>
```
