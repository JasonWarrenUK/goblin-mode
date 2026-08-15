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
lives at `<project-root>/docs/artefacts/{slug}.html`. No other location, no
exceptions. This is what lets the "check for an existing artefact first"
rule in the `artefact-conventions` skill work at all.

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
actual fonts are not — Newsreader/Bricolage Grotesque/Iowan Old
Style/Fraunces have all been used, paired with IBM Plex Mono or similar. Pick
deliberately per artefact tone; don't reach for Inter/Roboto reflexively.
Google Fonts is fine as the one external dependency.

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
