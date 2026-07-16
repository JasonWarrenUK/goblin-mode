<!--
	pr-description.md — shared PR body template (CLAUDE.md §8.8).
	Used by pr-create and pr-update so the two can never drift.
	{{ slot }} descriptions say what goes in the slot, not example content.
	The Screenshots section is shiny-style only: omit the whole <details>
	block (and its trailing ---) for wordy-style PRs.
-->
# {{ title — brief, descriptive, title case, understandable to non-devs }}
## Overview
{{ overview — what the PR does and why; when issue numbers were supplied, end with GitHub issue-closing syntax (e.g. "Closes #12, closes #34") }}
## Summary
{{ a non-technical, absurd metaphor describing the PR }}
> [!TIP]
> {{ tldr — any steps devs must take after pulling this down }}
---
<details>
	<summary><h2>Screenshots</h2></summary>

{{ screenshots — one collapsible <details> per named screenshot file, each with a caption }}
</details>

---
## Changes
{{ changes — broken into files or categories depending on PR scope, in collapsible <details> }}
---
