# Theme conventions

The single source for how colour, type and shape are defined for anything Claude renders: HTML artefacts, VHS tapes, freeze stills, social cards, framed screenshots, ghostty terminal themes, TUI styles. Skills read this; `theme-factory` writes the files it describes.

## Files

```
<project>/.claude/themes/
	<family>.json            core: palette, gradient, type, shape, contrast, rationale
	<family>-html.json       target block for HTML artefacts
	<family>-vhs.json        target block for VHS tapes
	<family>-freeze.json     … one file per target the family has been extended to
~/.claude/library/themes/
	clod.json, clod-*.json   global fallback family
	seen.json                originality register (signatures of every registered theme)
~/.claude/library/templates/themes/
	core.json, <target>.json every key present, values null: "is this file complete" is a diff
```

A **family** is a core file plus any number of target files. Family names are short lowercase slugs (`clod`, `ember`, `tidewater`). Target file names are always `<family>-<target>.json`; nothing else in the directory contains a hyphen, which is how the scripts tell cores from targets.

## Resolution order

When a skill needs a theme for target T:

1. A family named in the invocation (`/asset-card ember`, "use the tidewater theme").
2. The only `<family>-T.json` in `.claude/themes/`; if there are several, ask which.
3. A core `<family>.json` with no T file: offer `/theme-factory "T" from <family>`.
4. The global `~/.claude/library/themes/clod-T.json`.
5. No theme anywhere: offer `/theme-factory "T"`.

Never derive colours ad hoc from a project's CSS inside an asset skill. That is theme-factory's job (it uses the CSS as a seed); the asset skill's job is to consume a theme deterministically.

## Core schema (`clod-theme/core@1`)

| Block | Holds | Rule |
|---|---|---|
| `rationale` | `mood`, `inspiration`, `anchor_reason`, `rule_bent`, `rejected[]` | Every field a real sentence; `rejected` lists at least one palette considered and turned down, with why. The validator fails a theme with no describable idea. |
| `anchor` | the one hue the theme is built around: `name`, `hex`, `oklch` | Everything else is derived from or chosen against this. |
| `palette` | 12 named swatches, each `{ light, dark, role }` | Both variants always. Names are semantic (`ink`, `surface`, `accent`); consumers never see raw hues. |
| `gradient` | three stops per variant | Lightness monotonic across stops; adjacent chromatic stops ≥ 20° apart in OKLCH hue (a muddy centre is the usual failure). |
| `typography` | `display`, `body`, `mono` families with fallbacks; `scale` | Google Fonts names where possible; artefacts may load from fonts.googleapis.com and nowhere else. |
| `shape` | radii, shadow, spacing unit | Consumed by html, frame, card. |
| `contrast` | fg/bg pairs with required level; `ratio` filled by the validator | AA 4.5:1 for text pairs, AA-large 3:1 for status colours. The file documents its own guarantee. |
| `provenance` | `seed`, `derived_from`, `created`, `updated`, `tool` | `seed` says where the idea came from (CSS file, image, mood words, reference palette). |

### Derivation rule

1. Pick the anchor from the seed: the dominant chromatic colour of a project's CSS, an image's most saturated cluster or the hue the mood words imply.
2. Surfaces: `surface` is a near-neutral carrying a trace of the anchor's hue (chroma 0.01 to 0.03 in OKLCH), lightness ≈ 0.97 light / 0.20 dark. `surface-raised` sits one step towards the ink.
3. Ink: near-neutral opposite the surface, same faint hue.
4. `accent` is the anchor itself (dark variant) and a darkened version that clears 4.5:1 on the light surface (light variant). `accent-2` is a harmony partner: complementary, split-complementary or triadic, chosen by which survives both surfaces.
5. Status colours keep conventional hue regions (ok ≈ 140°, warn ≈ 80°, danger ≈ 25°, info ≈ 250°) but at the theme's chroma and lightness so they belong to it.
6. Gradient: anchor → harmony partner, with a mid stop on the short hue path; check the muddy-centre rule.
7. Run `validate.ts`; adjust until PASS; if WARN on originality, stop and show the user the nearest match.

## Target files (`clod-theme/target@1`)

Each target file has `family`, `target`, `extends` (the core file name), `rationale.mapping_notes` and one block named after the target holding exactly the shape its consumer reads. `emit.ts` turns that block into the consumer's native text with no further decisions.

| Target | Block is | Consumer | Emit |
|---|---|---|---|
| `html` | CSS custom properties, light + dark, type and shape tokens, Google Fonts list | artefact skills, frontend_styler, import-scaffold | `:root` block with the three-state theme switch |
| `vhs` | VHS `Set` values plus an inline `Theme` object (16 ANSI + bg/fg/cursor/selection) | asset-demo | `Set …` lines for the top of a tape |
| `freeze` | freeze `--config` JSON | asset-still | JSON file |
| `card` | colours, fonts, sizes for the satori card template | asset-card | JSON (read by `card.ts`) |
| `frame` | gradient, chrome, margin, radius, shadow | asset-shot, asset-pdf | JSON (read by `frame.ts`) |
| `ghostty` | terminal-config theme file keys | terminal-config `_apply_theme` | key/value file |
| `tui` | lipgloss/OpenTUI style map | clod-stack-opentui, Charm apps | JSON |

Adding a target type is `theme-target`'s job: template, mapping row here, emitter case.

### Core → target mapping

The core is copied, never re-derived. Only the target block is generated, by these rules, so two runs give the same answer.

**vhs / ghostty** (dark variant only; terminals are dark):
`background=surface`, `foreground=ink`, `selection=line`, `cursor=accent`; `black=line`, `red=danger`, `green=ok`, `yellow=accent`, `blue=info`, `magenta=accent-2 rotated +150°` (via `rotateHue`), `cyan=accent-2`, `white=ink-muted`; bright row = normal row with OKLCH lightness +0.08 (`brightWhite=ink`). `MarginFill` = light-variant `accent-2`. ghostty `gradient-*` = dark gradient.

**freeze**: `theme` = the chroma style whose own background is nearest `surface(dark)` in OKLab and whose accent hue matches (warm → `monokai`, cool → `dracula`, neutral → `github-dark`); note the choice in `mapping_notes`. Verified limitation: freeze paints the window with the chroma style's background and ignores `background`/`--background` for the window (they only affect the outer canvas), so the window colour is chosen, not set. `border.color=line(dark)`, shadow and radius from `shape`.

**card**: `variant` chosen so the card reads on both GitHub UI modes (default dark). Background = surfaces as a subtle gradient; `title=ink`, `tagline=ink-muted`, `meta=accent-2`, `accent_bar=accent`, `hero.frame_color=line`.

**frame**: background = the variant's gradient; `chrome_colors.bar=surface-raised`, dots = `[danger, warn, ok]`; `border.color=line`; radius/shadow from `shape`.

**html**: tokens are the palette verbatim per variant plus `--gradient`; type and shape tokens from core; `google_fonts` from `typography`.

**tui**: `title.fg=accent`, `body.fg=ink`, `muted.fg=ink-muted`, `selected={fg: accent-ink, bg: accent}`, `border.fg=line`, status = status swatches.

When a target needs colours the core lacks (16 ANSI slots), synthesise by rotating the anchor's hue in OKLCH at fixed intervals and say so in `mapping_notes`.

## Extending across targets

`/theme-factory "vhs" from ember`. `from` names a family; when only one family exists it may be omitted. The new file records `provenance.derived_from` implicitly via `extends`; `theme-factory print` flags a target file whose core has changed since (`updated` newer than the target's own `updated`).

## Quality gates

1. **Mechanical** (`validate.ts`, exit 1): completeness against the template, rationale present, every contrast pair meets its level, gradient monotonic and hue-spread, ≥ 3 hue families among accent/status swatches unless `"monochrome": true`.
2. **Originality** (`validate.ts`, exit 2): mean OKLab distance from every registered theme (project + global + `seen.json`) below 0.06, or within 0.05 of a blocklisted palette (`scripts/theme/blocklist.json`: tailwind-indigo-slate, purple-pink-hero, clod-terminal-default, dracula, nord). The skill stops, shows the nearest match and waits; the model cannot lift a warning on its own. Only the user's explicit instruction (`anyway`, "keep it", "I want it close to X") proceeds, and the theme's `rationale.rule_bent` must then say so.
3. **Judgement** (in the skill): before writing, three lines in the reply: the mood, the anchor and why, the one rule bent. Then a preview (`display`) and a stop for approval.

## Layout is not theme

`html` themes carry tokens only. Page shell, measure, grid, component recipes and density belong to a layout, which today is the default opening block in `artefact-conventions.md`. A `layout-factory` sibling is listed in `skills/FUTURE_SKILLS.md`.

## Palette references

Seed libraries the interview may offer, none mandatory: the project's own CSS, an image, mood words or a reference palette such as `reasonable-colors-reference.md` (24 hues × 6 shades with a known contrast table). Reference palettes are starting points; the theme that ships must pass the originality gate on its own.
