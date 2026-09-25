<!--
	pr-description.md: shared PR body template (CLAUDE.md §8.8).
	Used by pr-create and pr-update so the two can never drift.
	{{ slot }} descriptions say what goes in the slot, not example content.
	The Screenshots section is shiny-style only: omit the whole <details>
	block (and its trailing ---) for wordy-style PRs.
-->
# {{ title: brief, descriptive, title case, understandable to non-devs }}
## Summary
{{ a non-technical, absurd metaphor describing the PR }}
> [!TIP]
> {{ tldr: any steps devs must take after pulling this down }}
## Overview
{{ overview: what the PR does and why, laid out to be scanned rather than read as one block: one paragraph per distinct unit of work (a docs suite, a roadmap addition, a follow-up pass each get their own); an enumeration of three or more items that is the point of its sentence becomes a numbered list under a lead-in line ending in a colon, with the sentence's remainder restarting as prose below it, while a parenthetical aside stays inline; when issue numbers were supplied, end with GitHub issue-closing syntax (e.g. "Closes #12, closes #34") }}
---
<details>
	<summary><h2>Screenshots</h2></summary>

{{ screenshots: one collapsible <details> per named screenshot file, each with a caption }}
</details>

---
## Changes
{{ changes: broken into files or categories depending on PR scope, in collapsible <details> }}
---
