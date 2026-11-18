---
name: "Unroll Chart"
description: "Generate the chart (the roadbook's interactive HTML page) deterministically via roadbook.py render."
when_to_use: "When you want to view or share the current roadbook as the chart, an interactive HTML page, rather than reading roadbook.json directly."
model: sonnet # was haiku: auto mode skips haiku and keeps the session model, which is sometimes Fable or Opus here; sonnet pins it
effort: low
metadata:
  glyph: ᛊ
  family: artefact
disable-model-invocation: false
allowed-tools: ["Read", "Glob", "Bash(python3:*)", "Bash(open:*)"]
arguments: ["phase"]
argument-hint: "[phase name (optional, when several are active)]"
---

Render the chart: the roadbook's interactive HTML page. The HTML is generated deterministically by `roadbook.py render` from the template at `${CLAUDE_PLUGIN_ROOT}/templates/chart.html`: this skill runs the command and opens the result; it writes no HTML itself. Same data in, same file out, so a regenerated chart diffs cleanly and can never drift from `roadbook.json`.

Shared conventions (statuses, colour table): `${CLAUDE_PLUGIN_ROOT}/references/roadbook-conventions.md`.

## Steps

1. **Check the format.** Run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py detect`. Exit **3** = old simple format: stop and tell the user to run `goblin-scout:rebind-roadbook` first. Exit **2** = could not locate/parse; ask for the path. Proceed on exit 0.
2. **Render.** Run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py render`, adding `--phase "$ARGUMENTS"` when the user named a phase (required if several are active; an archived phase can be named here to re-render its chart). Output: the phase's `artefact` path from `roadbook.json` when set (`goblin-scout:configure-roadbook` sets it), else `{project_root}/docs/artefacts/chart-{slug}.html` (`docs/artefacts/roadmap-{slug}.html` while the file is still the pre-3.0.0 `roadmaps.json`); the command prints where it wrote. On a validation-discrepancy note in the output, still render (the page shows a discrepancy banner) but include the discrepancies in your report.
3. **Open and report.** `open` the written file. Report: the file path; milestone and waypoint counts plus done percentage (`roadbook.py stats`); the unblocked `todo` waypoints and the ones on a trail (`roadbook.py ready`; surfaced directly, no need to open the file); any validation discrepancies.

## Notes

- The chart refreshes automatically when `goblin-scout:tend-roadbook` runs (`recompute --render`); invoke this skill for the first render or an on-demand refresh.
- Collapse defaults belong to the template, and generated markup never carries an `open` attribute by hand. Two sections open by default. The Overview section's own `<details>` ships `open` in the template, so the headline and progress cards are the first thing a reader sees. A tier group's `<details>` opens by computation, never by hand: `roadbook.py`'s `overview_layout()` marks it open only once its tier itself is open (every milestone in every lower tier is `done`) and it holds a ready or in-progress waypoint; see roadbook-conventions.md's Milestone sort and tier grouping section. Everything else defaults to **closed**: every milestone `<details>` and, inside each milestone, the Blocked, Done and Out of Scope status groups (each a `<details>` whose heading carries its waypoint count). Never hand-edit an `open` attribute in a generated file; a different default is a template change.
- The dependency graph's direction (`TD`/`LR`) is chosen per render by `roadbook.py`'s `choose_direction()`, from the same live nodes/edges the diagram draws. The diagram shell has no height cap (a tall diagram just makes the page scroll), so this is a width-only comparison against the real layout column's width: whichever direction lays the widest layer or the longest chain out narrower wins, a tie keeps `TD`. A long thin chain picks `TD` (one node wide); a wide fan picks `LR` (spread across ranks instead of side by side). Never hardcode a direction in the template; a different choice belongs in `choose_direction()`'s constants.
- Sections, palette and behaviour live in the template. To change the chart's look, edit `templates/chart.html`; to change status colours, change the canonical table (`STATUS_STYLE` in `roadbook.py` + the conventions reference); never patch a generated file.
- The chart is generated in the CLI's own canonical form (tabs, single-line JSON payload); Prettier's form would differ. A repo that runs Prettier (or another formatter) in a pre-commit hook or CI should exclude it: add `docs/artefacts/chart-*.html` (and `docs/artefacts/roadmap-*.html` in a project that predates 3.0.0, whose chart keeps its old path) to `.prettierignore`, the same way `.claude/roadbook.json` (or `.claude/roadmaps.json`) is already excluded, so regenerating the chart never fights the formatter.
- The template follows a fixed artefact contract (theme-sourced palette, IBM Plex Mono/Sans pairing, the three-state light/dark/explicit-toggle contract with its masthead toggle control, collapsible milestone `<details>` closed by default). Any future template edit should stay inside that contract rather than drift from it: the template is the one place to fix a divergence, never a generated file.
