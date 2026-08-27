# Future skills

Ideas agreed in principle, deliberately not built yet. Each entry says what it would do, why it was deferred and what would trigger building it. Delete the entry when the skill lands.

## `layout-factory`

**Family:** `layout` · **Sibling of:** `theme-factory`

Themes (`.claude/themes/`) carry colour, type and shape tokens only. Layout (page shell, measure, grid, header style, component recipes, density) is a separate axis, so the same theme can render onto a dense dashboard or a long-read essay. `layout-factory` would own `.claude/layouts/<name>.json` with the same verbs as `theme-factory` (`print`, `display`, `new`, update-in-place) and `display html` in `theme-factory` would render the theme onto a chosen layout instead of the built-in swatch page.

**Deferred because:** the `html` target already renders onto the default opening block described in `library/references/artefact-conventions.md`; a second layout hasn't been needed yet.

**Build when:** an artefact needs a shell the conventions' default can't express (dashboard grid, slide deck, print-first document).

## `asset-trailer`

**Family:** `asset` · **Engine:** [Remotion](https://www.remotion.dev/)

A produced trailer rather than a screen recording: React-authored scenes (title card, zoom on a framed screenshot, captions, transitions) rendered to MP4. Highest ceiling of any asset skill; also motion design in code, a different kind of work from the capture-and-frame pipeline the other `asset-*` skills run.

**Licensing:** free for individuals and companies of up to three people; Creators tier $25/seat/month above that; source-available, not MIT. Fine at Jason's headcount, worth re-checking if that changes.

**Deferred because:** the four project types are covered by VHS, shot-scraper storyboards and Playwright recordings; a trailer is a marketing decision, not a documentation one.

**Build when:** a specific project needs a launch video, and the `asset-demo` output isn't enough. Source: the Aug 2026 comparative report on open-source visual asset generation (`~/Downloads/outwards/→ Claude/compass_artifact_wf-62140548…`).
