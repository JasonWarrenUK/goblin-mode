# Asset tools reference

Verified 2026-08-26 against upstream docs and local binaries. The `asset-*` skills read this rather than guessing flags. Re-verify when a tool's major version changes.

## Toolkit (`~/.claude/library/scripts/asset/`)

| Script | Runtime | Does |
|---|---|---|
| `theme.ts <target> [--project dir] [--family name]` | bun | Resolves the theme target file per `theme-conventions.md`; exit 3 with the `/theme-factory` invocation to run when none exists |
| `frame.ts <in.png> <out.png> [--chrome\|--no-chrome] [--max-width N]` | bun | Gradient background, rounded corners, shadow, drawn chrome bar; reads the `frame` block |
| `card.ts <card.json> <out.png> [--size og\|github]` | bun | satori → resvg social card; reads the `card` block; fonts from `fonts/` |
| `record.ts <flow.ts> <out.webm> [--width N] [--height N] [--mp4]` | **node** | Playwright `recordVideo` runner; flow default-exports `async (page) => {}` |
| `fonts.ts` | bun | Fetches static WOFFs (Inter 400/600, Inter Tight 700, JetBrains Mono 400) from fontsource. satori cannot parse variable fonts |

`bun install` once in the toolkit dir; `npx playwright install chromium` for record.ts. `@browserless/screenshot` was evaluated and dropped: it only frames pages it captures itself (no PNG input, no radius), so one sharp-based framer covers screenshots and PDF pages alike.

## shot-scraper (pipx, `~/.local/bin/shot-scraper`)

Docs: https://shot-scraper.datasette.io/en/stable/

- Single: `shot-scraper URL-or-path -o out.png -w 1280 [-h 800] [--retina] [-s "#selector"] [-p 20] [--wait 500] [-j "js"]`. Height omitted = full page. Local HTML: pass the path directly (relative assets resolve).
- Batch: `shot-scraper multi shots.yml [--retina]`. Per-shot keys: `output`, `url` (URL or local path), `width`, `height`, `selector`, `selectors`, `selector_all`, `padding`, `quality`, `wait` (ms), `wait_for` (JS expression), `javascript`, `js_file`. No `full-page` key; omit `height`.
- Video: `shot-scraper video storyboard.yml [-o out.webm] [--mp4]` (ffmpeg needed for `--mp4`). Top level: `output`, `url`, `viewport: {width, height}`, `cursor` (bool or `{visible, clicks, color, size}`), `wait`, `wait_for`, `javascript`, `server` (background command), `scenes[]`. Scene: `name`, `open`, `wait_for`, `do[]`. Verbs: `click` (selector or `{selector, button, count}`), `type {into, text, delay_ms}`, `fill {into, text}`, `press` (key or `{selector, key}`), `scroll` (px, `{x, y, duration}` or `{to: selector, duration}`), `pause` (s), `wait_for`, `wait_for_url`, `open`, `screenshot`, `javascript`. Not expressible: hover, drag, keyboard chords mid-flow, waiting on a network response, multiple tabs; those go to `record.ts`.

## VHS (`/opt/homebrew/bin/vhs`, needs ttyd + ffmpeg)

Docs: https://github.com/charmbracelet/vhs

- `Set` lines must precede any non-setting command. `Output demo.gif` / `.mp4` / `.webm` / `frames/`; several `Output` lines allowed. `Require gum`.
- Settings: `Shell`, `FontSize`, `FontFamily "…"`, `Width`, `Height`, `LetterSpacing`, `LineHeight`, `TypingSpeed 50ms`, `Padding`, `Margin`, `MarginFill "#hex"`, `WindowBar Colorful|ColorfulRight|Rings|RingsRight`, `WindowBarSize`, `BorderRadius`, `Framerate`, `PlaybackSpeed`, `LoopOffset`, `CursorBlink`.
- `Set Theme {json}` inline with keys `name, background, foreground, cursor, selection, black, red, green, yellow, blue, magenta, cyan, white, brightBlack … brightWhite`. `emit.ts` produces the exact lines from a `vhs` theme block.
- Actions: `Type "…"`, `Type@200ms "…"`, `Enter [n]`, `Backspace [n]`, `Tab`, `Space`, arrows, `Ctrl+R`, `Sleep 2s`, `Wait /regex/`, `Wait+Screen`, `Hide`/`Show`, `Screenshot file.png`, `Source other.tape`.

## freeze (`/opt/homebrew/bin/freeze`, v0.2.2, formula `charmbracelet/tap/freeze`; plain `brew install freeze` installs an unrelated cask)

Docs: https://github.com/charmbracelet/freeze

- `freeze file.ts -o out.png` (`.svg`, `.webp`), `freeze --execute "cmd" -o out.png`, `--lines 10,30`, `--language`, `--theme`, `--window`, `--background`, `--border.radius/width/color`, `--shadow.blur/x/y`, `--padding`, `--margin`, `--font.family/size/ligatures`, `--line-height`, `--show-line-numbers`, `--width`, `--height`, `--wrap`.
- `--config file.json` keys: `theme, background, window, border{radius,width,color}, shadow{blur,x,y} | false, padding[], margin[], font{family,size,ligatures}, line_height, show_line_numbers, language, width, height, wrap`. `emit.ts` produces this file from a `freeze` theme block.

## pdftoppm (poppler 26.06)

- `pdftoppm -png -r 300 [-f N] [-l M] in.pdf prefix` → `prefix-01.png …` (zero-padded to page-count width; numbering keeps original page numbers). `-singlefile` for one page without suffix. `-scale-to px` as an alternative to DPI.

## Playwright (`playwright` 1.62 in the toolkit)

- `chromium.launch()`, `browser.newContext({ recordVideo: { dir, size } })`; the video file exists only after `context.close()`. Run under Node; Bun launch hangs are a recent history (bun issues #38579, #34785).

## GitHub social preview upload

No API. Settings page `https://github.com/<owner>/<repo>/settings`, "Social preview" → Edit → file input. PNG/JPG/GIF under 1 MB, 1280×640 recommended. Selectors used by gh-social-preview: `#edit-social-preview-button`, `input#repo-image-file-input`; success = 2xx `PUT` to `/upload/repository-images/`. GitHub can change these without notice; the skill drives the user's own logged-in Chrome via the claude-in-chrome MCP so no credentials are stored.
