# Artefact Design Conventions

Shared reference for every artefact Claude creates for Jason: a claude.ai/Cowork
Artifact, a Claude Code project artefact (`docs/artefacts/*.html`), or the
styling pass inside `import-scaffold_artefact`. Distilled in interview from
ten artefacts Jason holds up as exemplary (spanning claude.ai Artifacts,
Claude Code project docs, and RPG-kit one-offs), then generalised with him
past those specific examples so the rules would still make sense on an
artefact that looks nothing like any of the ten.

**This document encodes values and structural patterns, not a fixed skin.**
Hues, exact fonts, and voice vary artefact to artefact on purpose. Nothing
below should make two artefacts about different things look like the same
template with new words in it. The rules that *are* fixed are marked as such;
everything else is a structural default with room to vary.

The `artefact-conventions` skill is what actually walks these rules at
write-time (location, existing-project-aesthetic check, interview when
there's no established convention yet). This document is what it applies.

---

## Location (fixed)

Every artefact — from a named skill or created ad hoc mid-conversation —
lives under `<project-root>/docs/artefacts/`. This is what lets the "check
for an existing artefact first" rule in the `artefact-conventions` skill
work at all.

- **Default**: `docs/artefacts/{slug}.html`.
- **Any depth of nesting beneath `docs/artefacts/` is valid.** A set of
  related artefacts may live in a collection directory, at whatever depth
  the set justifies:
  `docs/artefacts/skill-explainers/{index,red-sabotage,dossier-record}.html`.
  A collection directory gets an `index.html` hub linking its members; a
  member with no hub is just a nested file with nothing pointing at it.
- **`<project-root>/site/` is also valid, and only when the user asks for
  it explicitly.** Never infer it from the content, and never move an
  artefact there unprompted; that path means the artefact is part of a
  published site rather than project documentation.

Because nesting is allowed, the "what's already there" check must be
recursive, and it must cover **both** locations. A flat
`ls docs/artefacts/*.html` misses every collection, and a check that skips
`site/` will read an empty `docs/artefacts/` as "this project has no
artefact aesthetic yet" when in fact the aesthetic is published and live.

A `site/` that holds artefacts should carry a `site/CLAUDE.md` recording
what may and may not be written there. Read it before adding a page.

## Masthead

Nearly every example opens with the same four-part structure, regardless of
mood: an **eyebrow/kicker** (small, uppercase, letter-spaced, tinted with the
accent colour — project name, date, or "before the deltas" framing), the
**h1**, a **standfirst/lede** (one or two sentences, wider measure, muted
tone, states what the reader is about to get), and a **meta-strip** (small
mono row of key facts — model used, dataset size, compiled date, runtime —
`font-variant-numeric: tabular-nums` where it's numeric). Use it as the
default opening; a short narrative piece can compress or drop the meta-strip
if there's nothing worth putting in it.

## Palette (fixed source, bespoke mapping)

**Reasonable Colors is always the token source** — this is fixed, not a
per-artefact choice, for the accessibility guarantee (see
`reasonable-colors-reference.md` for the contrast table). What *is* bespoke
per artefact is which RC hues get chosen and what they mean: a blueprint-teal
instrument palette for pipeline docs, parchment/oxblood for an RPG kit,
violet for a linguistics piece. RC's palette (24 colour sets + grays, 6
shades each) is wide enough that "always RC" and "a distinct mood per
artefact" are not in tension.

**Semantic CSS custom properties only.** Markup and components never
reference `--color-{name}-{shade}` directly — always through a semantic alias
(`--ink`, `--surface`, `--accent`, `--verd`, whatever names fit this
artefact's own vocabulary). Document *why* each alias maps to which RC hue,
the way `those-who-came-before/site/assets/site.css` does:

```css
/*
  Mapping notes: --terra (accent, links) maps to amber; --verd (structural
  boxes, callouts) maps to emerald; --bronze (kickers, headings) maps to
  cinnamon. Shade gaps of 3 hold body-text contrast (4.5:1) and gaps of 4
  hold AAA (7:1) per the RC contrast table.
*/
:root {
  --terra: var(--color-amber-4);
  --verd:  var(--color-emerald-4);
  --bronze: var(--color-cinnamon-4);
}
```

That comment block is the point: a future read of this file should be able
to reconstruct the palette decision without re-deriving it.

### One hue per skill family (for artefacts about skills)

When an artefact documents a specific skill, its palette is keyed to that
skill's `metadata.family`, not chosen fresh. Pages in the same collection
share their layout and differ in hue, so the colour tells a reader which
family they are in before the title does.

- A family's hues are decided once, when its first artefact is written, and
  documented as mapping notes in that artefact's stylesheet. Every later
  artefact for the same family reads those notes and reuses them.
- Two families never share a primary hue. Check the existing pages in the
  collection before picking.
- A surface that belongs to no family — a collection index, a cross-family
  overview — takes no hue of its own. Grey ground, with colour appearing
  only where it belongs to a family: a card, a chip, a link out.
- Established mappings: `red` → red/teal/cinnamon, `dossier` →
  indigo/violet/grey, `clod-config` → amber/emerald.

## Theming (fixed contract)

Three states — light, dark, and "follow system" — every time, matching the
`Artifact` tool's own documented contract:

```css
:root {
  /* light tokens, unguarded — this is the default */
  --ink: #171c21;
  --paper: #fbfaf7;
}

@media (prefers-color-scheme: dark) {
  /* wins when the OS is dark AND no explicit light choice is set */
  :root:not([data-theme="light"]) {
    --ink: #e8e9e6;
    --paper: #12161a;
  }
}

/* wins in both directions when a toggle sets data-theme explicitly */
:root[data-theme="dark"] {
  --ink: #e8e9e6;
  --paper: #12161a;
}
```

Give `body` an explicit background from a token — a transparent body borrows
whatever ground the viewer is painting behind it. Single-look-only (no dark
block) is allowed when the mood itself calls for commitment — a parchment RPG
kit, a forced-dark terminal aesthetic — but say so explicitly rather than
quietly omitting dark support.

## Typography (structural rule, free choice)

Pair one distinctive display/body voice with one monospace workhorse for
labels, data, eyebrows, and mono detail. The pairing structure is fixed; the
actual face is not. Pick deliberately per artefact tone; don't reach for
Inter/Roboto reflexively. Google Fonts is fine as the one external
dependency.

**Jason's shortlist, offered first:** Texturina, Fraunces (`SOFT` 100,
`WONK` 1, `opsz` 144), Grenze, Eczar, Young Serif. Chosen from a fourteen-way
bakeoff in August 2026; the full table with axis values and the rejected
faces lives in the `artefact-conventions` skill, Step 2b. Where a face
carries variable axes, **the axis values are part of the choice** and belong
in the mapping-notes comment next to the palette: Fraunces without `WONK 1`
was rated a different typeface from Fraunces with it.

**An optical-size axis does not make a display face readable at body size.**
Texturina was set as both on the goblin-mode site with `opsz` 72 for `h1` and
18 for body, and the body text was rejected on sight: the texture that earns
the face its place at 30px is noise across three thousand words. `opsz`
adjusts contrast and spacing; it does not remove the character you chose the
face for.

So the pairing is **three voices, not two**, whenever the display face has
real character:

- `--display` for titles only: `h1`, section titles, card titles.
- `--serif` (or a plain book face) for everything actually read: body,
  ledes, lists, tables, callouts.
- `--mono` for labels, data, eyebrows and chips.

Reach for one family covering display and body only when the face is a
workhorse to begin with. Judge it at body size and body length before
committing, never at display size alone.

## Structure: collapsibility (default past a threshold)

Once an artefact exceeds roughly **4 distinct sections**, or reads as
something a reader will scan rather than read start to end, default to
collapsible sections:

```html
<details class="section">
  <summary>Section title <span class="hint">one-line gloss</span></summary>
  <div class="section-body">…</div>
</details>
```

Custom rotating chevron via `summary::before`, never the native
`::-webkit-details-marker`. Closed by default — the reader chooses what to
expand, not the page. Short or narrative pieces (a few sections, meant to be
read straight through) stay linear; don't collapse for the sake of it.

## Structure: table of contents (default past the same threshold)

Once content is dense enough to justify one, add a table of contents. Default
to linking only `h2`s; add `h3`s under their parent `h2` when a section's
subsections are themselves substantial enough to jump to directly — don't
link every heading level reflexively.

The TOC must always satisfy **one** of these two containment rules:

- a `<details>` element, **closed by default**, styled distinctly from the
  artefact's other `<details>` sections (a reader must never mistake the TOC
  chevron for a content section's), or
- a **sticky sidebar** with its own independent scroll state, so scrolling
  the TOC never scrolls the page and vice versa.

A bare inline list of links with no container is never sufficient once the
threshold is met — it competes with the masthead for attention and gives the
reader nothing to collapse away.

## Statlines (fixed)

The meta-strip carries **only metrics that inform a reader who is not the
author**. A count that describes Jason's own private usage of a thing (how
many entries his directory currently holds, how many times he has run it)
tells a reader nothing and takes the slot a real metric wanted. Measure the
*subject*: its steps, its fields, its passes, its moving parts.

## Headings (fixed)

**Title Case, every heading, every level.** Sentence case is a drift, not a
style choice.

## Collapsed sections: subgrouping and granularity (fixed)

Any page carrying **more than five collapsed `h2` sections must subgroup
them** and give the groups visible contrast: a banner with a roman numeral
and a group title, a per-group accent on the section borders, or both. A
flat run of ten identical collapsed rows is a wall, and the reader cannot
tell where one theme ends.

**Granularity is a layout property, not a length one.** Derived by comparing
pages Jason rated good against pages he rated bad; the two groups separated
cleanly on this and on nothing else, including word count:

- **Six or more collapsed sections, across two or more strands.**
- **Roughly 200 to 400 words per section.**

The bad example was *longer* than two of the good ones (2,175 words) and
failed anyway, because it held those words in three sections at 725 words
each. Under six sections the sidebar rail runs out of entries and the
two-column shell is chrome with an empty left half. Over ~400 words a
section stops being a unit the reader can decide to skip. A page too thin
for six sections should gain substance or lose the rail, never keep the
frame and leave it empty.

## Table of contents (fixed, expanded)

The containment rule above still holds: a closed `<details>` or a sticky
sidebar with independent scroll. Two further rules:

- **A TOC must earn its space.** If the bottom of an inline TOC can sit on
  the same screen as the last heading it links to, the TOC is redundant
  scenery. Delete it.
- **Sticky sidebar is the default.** Prefer inline only when the sidebar is
  needed for something else.

## Slugs (fixed)

Never repeat the collection in the leaf. `families/dossier/record.html`,
never `families/dossier/dossier-record.html`. The path already said it.

## Epistemic honesty (required, structural — never hedging prose)

Every artefact must be honest about what it actually knows, and that honesty
belongs in the **structure**, not in the prose. Prose states things directly;
uncertainty gets a visual home instead of a verbal hedge. "Might possibly
potentially" in running text is not this rule being followed — it's the rule
being dodged.

- **Sourced footer, always.** What files/queries/commits/dates the artefact
  was built from. A reader should be able to tell where every claim on the
  page came from without asking.
- **Status/confidence marking, for reference-genre content.** A chip, a
  coloured dot, a legend — vocabulary is contextual per artefact domain, pick
  what fits: `built / partial / absent` for build status, `firm / provisional
  / open` for measurement confidence, `verified / corrected / unaudited /
  known-defect / unusable` for an audit trail. Define an explicit legend and
  hold one consistent colour-role mapping *within* a single artefact — don't
  invent a fourth vocabulary just for variety.
- **An absent or unmeasured value is always marked, never left blank.** A
  blank cell reads as zero or "nothing to report"; say `not measured` and why.
- **Narrative pieces get an honesty footnote instead of chips** — what's
  real versus composed/estimated/a period pastiche, stated plainly at the
  point a reader would otherwise assume more rigor than exists.
- **The sources list is collapsed by default.** It is provenance, not
  reading matter.
- **Disclaimer prose in footers is banned**, and may not be relocated into
  the body to survive. "This has not been tested end to end", "sections
  marked X describe untested behaviour", "every count came from the tool":
  all of it restates what the chips already say, and hedging that says
  nothing new reads as insincere. Prefer no footer prose to bad footer
  prose. The honest content survives as a **specific, committed statement of
  fact** in the body ("four of the five files predate the skill file by four
  minutes"), never as an apology for the page.

## Technical hygiene

- Self-contained: inline CSS, vanilla JS, Google Fonts as the only external
  dependency. No frameworks for a static HTML artefact.
- `overflow-x: auto` wrapper around every wide table, diagram, or inline SVG
  — the page body itself never scrolls horizontally.
- `font-variant-numeric: tabular-nums` on any element carrying numeric data.
- British spelling, no em dashes, no contrastive "not X but Y" couplets —
  standing rules, restated because artefact prose is still prose.

## Relationship to the `Artifact` tool's own skills

For a claude.ai/Cowork `Artifact` publish specifically, this document adds a
layer on top of — never replaces — Anthropic's built-in `artifact-design` /
`artifact-diagramming` / `artifact-capabilities` skills. Favicon, CSP
self-containment, and runtime capabilities stay owned by those. This
document is the *only* gate for the Claude Code `docs/artefacts/*.html`
pathway, which has no automatic equivalent today.
