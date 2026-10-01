<!--
	pr-description.md: shared PR body template (CLAUDE.md §8.8).
	Used by pr-create and pr-update so the two can never drift.
	{{ slot }} descriptions say what goes in the slot, not example content.
	Optional blocks: Screenshots (shiny style only), Breaking change (only
	when something breaks) and Verification (only when something was run).
	Dropping one drops its own trailing --- too, so no two rules end up
	adjacent.
	Typography: keep every blank line below. A --- directly under text turns
	that text into a heading; text directly under </details> renders raw.
	Inside <summary> use <code>, never backticks. library/scripts/md-lint.py
	checks all of this.
-->
# {{ title: brief, descriptive, title case, understandable to non-devs }}

## Summary

{{ a non-technical, absurd metaphor describing the PR }}

> [!TIP]
> {{ tldr: any steps devs must take after pulling this down }}

> [!WARNING]
> {{ breaking change, optional: what breaks and what anyone relying on it must do; omit the whole alert when nothing breaks }}

## Overview

{{ overview: what the PR does and why, in plain language a non-dev can follow; 2-4 sentences, or a lead-in line and at most 5 bullets when the PR holds several distinct units of work; no code identifiers, file paths, figures or test results (those belong in Changes and Verification); a stacked PR opens with its parent line; when issue numbers were supplied, end with GitHub issue-closing syntax (e.g. "Closes #12, closes #34") }}

---

<details>
<summary><h2>Screenshots</h2></summary>

{{ screenshots: one collapsible <details> per named screenshot file, each with a caption }}

</details>

---

## Changes

{{ changes: one collapsible <details> per file or category depending on PR scope, each shaped as:
<details>
<summary>Area name (<code>path/</code>)</summary>

1-2 sentence intro: what this area now does and why it needed changing.

- the change, because the reason; where existing behaviour changed, add before → after
- …

**Review:** where to look first, the riskiest spot and how to check it.

</details>

}}

---

<details>
<summary><h2>Verification</h2></summary>

**Checked**

{{ checked: numbered list of what was run or tried and its result }}

**Not checked**

{{ not checked: bullets of what was left untested and why; omit this heading and list when everything was checked }}

</details>

---
