---
name: "Artefacts: Create Roadmap"
description: "{{ ƔƔƔ }} Generate an HTML dashboard showing the current state of a project roadmap."
model: opus
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Write", "Bash(open:*)", "Bash(mkdir:*)", "Bash(python3:*)"]
argument-hint: [roadmap name or path (optional)]
---

Uses the visual-explainer skill's rendering patterns and a colour palette derived from the project's palettes colour scheme.

## Step 1 — Locate the roadmap and check the format

The roadmap source of truth is `.claude/roadmaps.json` (a rich phase array). Locate it:

1. **`$ARGUMENTS` provided** — treat as a phase name or path; match it against the phase entries in `.claude/roadmaps.json` (or a `docs/roadmaps/{name}.md` path).
2. **`.claude/roadmaps.json`** — parse. If it has one active (non-`archived`) phase, use it; if several, list names and ask.
3. Stop and tell the user if nothing is found.

Run `python3 ~/.claude/library/scripts/detect_format.py`. On exit 3 (old simple format), prompt the user to run `roadmap-migrate` first. (The artefact writes nothing to the roadmap, so a read-only legacy render is possible in a pinch, but prefer migrating for a correct six-status dashboard.)

## Step 2 — Get the data from the scripts (do not hand-parse the Markdown)

The rich data comes from two scripts — one source of truth, so the dashboard and the roadmap never drift:

- **Counts:** `python3 ~/.claude/library/scripts/roadmap_stats.py --json` → `{phase, total, byStatus, donePct, milestones:[{id, name, total, done, byStatus, donePct}]}`. Six statuses: `todo, blocked, paused, deferred, done, out_of_scope` (there is no in-progress). These drive the hero KPI, the per-milestone progress bars, and the status tiles.
- **Graph:** `python3 ~/.claude/library/scripts/roadmap_graph.py --json` → `{nodes:[{id, kind:task|milestone|gate, status?, milestone?, description?}], edges:[{from, to, kind:task|milestone-dep|milestone-complete|gate}]}`. Build the Mermaid diagram from this — it already encodes the **terminal milestone-edge convention** (`milestone-complete` edges are `sink --> M{N}`; `milestone-dep` edges are `M{N} --> task`), so you neither compute sinks nor scrape the `.md`'s diagram.

Read the PHASE `.md` only for prose you want to surface (milestone goals, the intro/critical-path line). Do not parse `<a name>` anchors or `— **depends on**` clauses — that is the old format.

**Next Up** = tasks with `status: todo` (a `todo` task is by definition one whose dependencies are all `done`). There is no In Progress group.

## Step 3 — Load visual-explainer references

Resolve the installed path with Glob:

```text
~/.claude/plugins/cache/visual-explainer-marketplace/visual-explainer/*/
```

Read these files before generating any HTML:

- `references/css-patterns.md` — depth tiers, Mermaid zoom controls, overflow protection, collapsible pattern
- `references/libraries.md` — font pairings, CDN imports, Mermaid theming guide
- `templates/mermaid-flowchart.html` — the full `diagram-shell` pattern with zoom/pan JS (~200 lines; copy wholesale)
- `references/responsive-nav.md` — sticky sidebar TOC + mobile horizontal nav

Do **not** skip any of these. The zoom/pan JS in particular must be reproduced exactly.

## Step 4 — Aesthetic and palette

### Project Palette & Aesthetic

1. Search for `palette`, `colour` and other design files. Use what you find to style this artefact.
2. If none is found, use `#Default-Palette` & `#Default-Aesthetic`.

### Default Palette

Derive from the user's terminal gradient: warm pink (`#B34480`) → steel blue (`#3E7F96`), mapped to Reasonable Colors.

Load the CDN stylesheet in `<head>`:

```html
<link rel="stylesheet" href="https://unpkg.com/reasonable-colors@0.4.0/reasonable-colors.css">
```

Define semantic aliases — components reference these only, never RC vars directly:

```css
:root {
  /* Milestone — sky family (≈ #3E7F96) */
  --color-milestone:      var(--color-sky-4);     /* #007590 */
  --color-milestone-bg:   var(--color-sky-1);     /* #e3f7ff */
  --color-milestone-text: var(--color-sky-6);     /* #001f28 */

  /* Primary accent — pink family (≈ #B34480) */
  --color-primary:        var(--color-pink-4);    /* #d2008f */
  --color-primary-bg:     var(--color-pink-1);    /* #fff7fb */
  --color-primary-text:   var(--color-pink-6);    /* #4b0030 */

  /* Task status — six statuses (no in-progress) */
  --color-done:           var(--color-teal-4);    /* #007c6e */
  --color-done-bg:        var(--color-teal-1);    /* #d7fff7 */
  --color-todo:           var(--color-gray-4);    /* #6f6f6f */
  --color-todo-bg:        var(--color-gray-1);    /* #f6f6f6 */
  --color-blocked:        var(--color-pink-4);
  --color-blocked-bg:     var(--color-pink-1);
  --color-paused:         var(--color-purple-4);
  --color-paused-bg:      var(--color-purple-1);
  --color-deferred:       var(--color-gray-4);
  --color-deferred-bg:    var(--color-gray-1);
  --color-gate:           var(--color-yellow-5);  /* external gate */
  --color-gate-bg:        var(--color-yellow-1);
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-milestone:      var(--color-sky-2);   /* #aee9ff */
    --color-milestone-bg:   var(--color-sky-6);   /* #001f28 */
    --color-milestone-text: var(--color-sky-1);
    --color-primary:        var(--color-pink-2);  /* #ffdcec */
    --color-primary-bg:     var(--color-pink-6);
    --color-primary-text:   var(--color-pink-1);
    --color-done:           var(--color-teal-2);
    --color-done-bg:        var(--color-teal-6);
    --color-todo:           var(--color-gray-3);
    --color-todo-bg:        var(--color-gray-6);
    --color-blocked:        var(--color-pink-3);
    --color-blocked-bg:     var(--color-pink-6);
    --color-paused:         var(--color-purple-2);
    --color-paused-bg:      var(--color-purple-6);
    --color-deferred:       var(--color-gray-3);
    --color-deferred-bg:    var(--color-gray-6);
    --color-gate:           var(--color-yellow-2);
    --color-gate-bg:        var(--color-yellow-6);
  }
}
```

Shade differences of ≥ 3 guarantee WCAG AA body text contrast on all pairs.

### Default Aesthetic

**Editorial + Blueprint hybrid:**

- Light: warm off-white (`var(--color-gray-1)`), sky-tinted milestone headers, generous whitespace, subtle CSS grid-line background pattern
- Dark: deep near-black, muted sky/pink accents, low-opacity borders
- Font: **IBM Plex Sans + IBM Plex Mono** — load via Google Fonts CDN
- No emoji in section headers — use styled monospace labels with coloured dot indicators
- Forbidden: Inter/Roboto body font, violet/indigo accents, gradient-text headings, glowing animated shadows

## Step 5 — Generate the HTML

### Output location

```bash
mkdir -p {project_root}/docs/artefacts
```

Write to `{project_root}/docs/artefacts/roadmap-{name}.html`.

### Page structure

Use the responsive section navigation from `references/responsive-nav.md`. Four sections:

1. **Overview** — overall progress KPI cards + per-milestone mini progress bars
2. **Milestones** — one collapsible card per milestone with full task breakdown
3. **Dependency Graph** — Mermaid diagram of the full task graph
4. **Next Up** — unblocked tasks grouped by milestone

### Section 1: Overview

Hero KPI card (`ve-card--hero`): **`{done}/{total} tasks — {pct}% complete`**. Large type, accent-tinted background.

Per-milestone mini-cards in a CSS Grid row:

- Milestone name and number
- `{done}/{total}` count
- Coloured progress bar — CSS `linear-gradient`, width set via inline `style`:

```html
<div class="progress-bar">
  <div class="progress-fill" style="width: {pct}%"></div>
</div>
```

Colour the fill by milestone health: high completion → `--color-done`, has `todo` work ready → `--color-todo`, all work parked behind a gate → `--color-paused`, deferred to a later phase → `--color-deferred`, otherwise blocked → `--color-blocked`.

### Section 2: Milestones

One `<details>/<summary>` per milestone. Open whichever milestone contains the most recently referenced task; collapse the rest.

Inside each card, labelled groups by status (omit empty groups):

```text
○ To Do   ✗ Blocked   ⏸ Paused   ⤓ Deferred   ✓ Done
```

There is no In Progress group. Order the groups to lead with actionable work (To Do, Blocked) and trail with parked/complete (Paused, Deferred, Done).

Task items: ID badge (monospace, small, accent-tinted) + description + dependency note.

**Overflow rule:** never `display: flex` on `<li>`. Use `position: relative` + `padding-left` for status indicators. All grid/flex children get `min-width: 0`.

### Section 3: Dependency Graph

Use the full `diagram-shell` pattern from `templates/mermaid-flowchart.html`. Never bare `<pre class="mermaid">`.

Build the diagram from `roadmap_graph.py --json` (Step 2). Emit nodes for each `milestone`/`gate`/non-done `task`; emit every edge verbatim (its direction already follows the terminal convention). Class each task node by its `status`.

Map all six statuses plus milestone/gate to the semantic palette:

```text
classDef open     fill:var(--color-todo-bg),      stroke:var(--color-todo),      color:var(--color-todo);
classDef blocked  fill:var(--color-blocked-bg),   stroke:var(--color-blocked),   color:var(--color-blocked);
classDef paused   fill:var(--color-paused-bg),    stroke:var(--color-paused),    color:var(--color-paused);
classDef deferred fill:var(--color-deferred-bg),  stroke:var(--color-deferred),  color:var(--color-deferred);
classDef done     fill:var(--color-done-bg),      stroke:var(--color-done),      color:var(--color-done);
classDef mile     fill:var(--color-milestone-bg), stroke:var(--color-milestone), color:var(--color-milestone-text);
classDef external fill:var(--color-gate-bg),      stroke:var(--color-gate),      color:var(--color-gate);
```

- **`classDef` lines must come AFTER the graph-type declaration.** Emit `graph TD` (or `graph LR`) as the first line, then every `classDef`, then nodes/edges/`class` statements. Placing a `classDef` before `graph TD` is a Mermaid syntax error and the diagram silently fails to render (the raw source shows instead).
- Use `graph TD`. For 15+ nodes add `layout: 'elk'` (see libraries.md CDN import).
- Mermaid theme: `theme: 'base'` with `themeVariables` matching the page palette.
- `fontSize: 16` in `themeVariables`.
- Line breaks in labels: use `<br/>`, never `\n`.
- Omit completed (`done`) tasks & fully-done milestones. Keep `paused`/`deferred` tasks (they are live-but-parked, not complete).

### Section 4: Next Up

Flat prioritised list of the **`todo`** tasks (a `todo` task is by definition unblocked — all its dependencies are `done`). There is no In Progress group. Group by milestone. Each item: task ID badge + description + milestone label pill.

## Step 6 — Quality checks

Before writing the file:

- [ ] Every `.mermaid-wrap` has +/−/reset/expand buttons, Ctrl/Cmd+scroll zoom, drag-to-pan, click-to-expand
- [ ] Light and dark themes both look intentional
- [ ] No page-level `.node` CSS class (breaks Mermaid SVG positioning)
- [ ] All grid/flex children have `min-width: 0`; `overflow-wrap: break-word` on text containers
- [ ] Progress bar percentages match the `roadmap_stats.py` counts
- [ ] Every Mermaid diagram emits `graph TD`/`graph LR` FIRST, then `classDef` lines (never a classDef before the graph-type line — it silently breaks the render)
- [ ] Six statuses handled (todo, blocked, paused, deferred, done, out_of_scope); no In Progress group anywhere
- [ ] Reasonable Colors CDN `<link>` present in `<head>`
- [ ] IBM Plex Sans + IBM Plex Mono loaded via Google Fonts
- [ ] No Inter/Roboto, no violet/indigo accents, no gradient-text headings, no emoji headers, no animated glow shadows

## Step 7 — Open and confirm

```bash
open {project_root}/docs/artefacts/roadmap-{name}.html
```

Report:

- File path written
- Roadmap name, milestone count, total task count
- The unblocked `todo` tasks (surfaced immediately, without needing to open the file), and any validation discrepancy from `validate_roadmap.py`
