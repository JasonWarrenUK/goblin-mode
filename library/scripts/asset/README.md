# Asset toolkit

Shared renderers behind the `asset-*` skills. Installed once here so projects carry no image dependencies of their own.

```sh
cd ~/.claude/library/scripts/asset
bun install
bun fonts.ts                      # static WOFFs for card.ts (satori can't read variable fonts)
npx playwright install chromium   # for record.ts only
```

| Script | Runtime | Reads theme block | Output |
|---|---|---|---|
| `theme.ts <target>` | bun | any | path of the resolved theme file (exit 3 + a `/theme-factory` command when none) |
| `frame.ts in.png out.png` | bun | `frame` | gradient background, rounded card, shadow, optional chrome bar |
| `card.ts card.json out.png --size og\|github` | bun | `card` | satori → resvg social card |
| `record.ts flow.ts out.webm [--mp4]` | node | none | Playwright `recordVideo` run of a flow module |
| `fonts.ts` | bun | none | `fonts/<Family>-<weight>.woff` |

External CLIs the skills call directly: `shot-scraper` (pipx), `vhs` + `ttyd` + `ffmpeg`, `freeze` (`charmbracelet/tap/freeze`, not the `freeze` cask), `pdftoppm` (poppler). Flags and verified behaviour: `../../references/asset-tools.md`.

## Decisions

- **`@browserless/screenshot` dropped.** It only frames pages it captures itself (URL in, no PNG input, no corner radius), and it would have meant a second Chromium. One sharp-based framer handles screenshots and PDF pages the same way.
- **Playwright under Node.** Bun has had a run of `chromium.launch()` hangs (bun issues #38579, #34785, closed mid-2026); Node is the supported runtime, so `record.ts` uses `node --experimental-strip-types`.
- **Static fonts from fontsource.** satori's opentype parser throws on variable TTFs (`names[p.parseUShort()]`); fontsource publishes one static WOFF per weight.
- **Remotion considered, deferred.** A produced trailer is a different job from a screen recording; see `~/.claude/skills/FUTURE_SKILLS.md` (`asset-trailer`). Source: the Aug 2026 comparative report on open-source visual asset generation.
