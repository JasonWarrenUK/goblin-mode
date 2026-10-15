---
name: "Asset: Shot"
description: "Capture website screenshots from a generated, committed shots.yml (routes → shot-scraper) and frame them with the project's theme into README-ready mockups"
when_to_use: "When a project needs screenshots for its README, portfolio page or social card; when the user mentions screenshots, mockups, captures or points at a URL or site directory."
model: sonnet
effort: medium
metadata:
  glyph: ᛊ
  family: asset
  goblin-spinner: snapping screenshots|framing shots|waiting for the page
disable-model-invocation: true
allowed-tools: ["Read", "Write", "Edit", "Glob", "Grep", "Bash", "AskUserQuestion"]
argument-hint: "[urls, paths or a site directory] [plain wording: 'no frame', 'regenerate config', 'mobile too', a theme family]"
---

# Screenshots and framed mockups

Load `asset-conventions` first; tool flags are in `~/.claude/library/references/asset-tools.md`.

```xml
<asset-shot>
	<arguments>
		Free text. Recognise: a `.yml` path (use that config instead of `docs/assets/shots.yml`; `web-walkthrough` passes `docs/assets/walkthrough.yml`); URLs or paths (explicit targets, skip route detection); a directory (static site: capture its `index.html` and any top-level `.html`); "no frame" / "raw" (skip framing); "regenerate" / "fresh config" (rebuild `shots.yml` from routes even if one exists); "mobile" / "phone" (add a 390-wide viewport per route); "full page" (omit `height`); a theme family name (pass as `--family`). Anything else is a hint for which routes matter.
	</arguments>
	<steps>
		<step num="1">Detect project type and capture base per the conventions. For a dev-server project, check whether a server is already listening (`lsof -iTCP -sTCP:LISTEN -P | grep -E 'node|bun|deno'`); if not, start `bun run dev` in the background, read the port from its output, and stop it at the end.</step>
		<step num="2">
			Config. A `.yml` path in the arguments is the config. Else if `docs/assets/shots.yml` exists and no regenerate hint was given, use it. Otherwise build one: one entry per route at 1440 wide with `height: 900` (viewport crop) plus a second full-page entry for the home route with the specifier `full`; `wait: 800`; `output: docs/assets/shots/&lt;name&gt;.png` where the name follows the capture naming rule in `asset-conventions` (`&lt;viewport&gt;-&lt;route&gt;[-&lt;specifier&gt;]`, the viewport prefix only when more than one viewport is captured, so a "mobile" run prefixes every capture with its width). Use `javascript:` to hide cookie banners or dev overlays when the project has them. Show a config you built and stop for approval (a config given by `.yml` path or already committed is used as is); explicit URL/path arguments still get a config, so the run is repeatable.
		</step>
		<step num="3">`shot-scraper multi &lt;config&gt; --retina`, where the config is the one Step 2 chose (`docs/assets/shots.yml` unless a `.yml` path was given). On a failure for one entry, retry that entry once with `wait` doubled, then report it.</step>
		<step num="4">Unless "no frame": resolve the `frame` theme (`theme.ts frame --project .`), then for each capture `bun ~/.claude/library/scripts/asset/frame.ts &lt;dir&gt;/&lt;name&gt;.png &lt;dir&gt;/framed/&lt;name&gt;.png --project . [--family X]`, where `&lt;dir&gt;` is the directory of the entry's `output` (`docs/assets/shots` for the README set, `docs/assets/walkthrough` for a walkthrough), same name as the raw capture. Full-page captures get `--no-chrome` (a 6000px tall browser window looks wrong).</step>
		<step num="5">Quality gate from the conventions on every framed PNG. Then report in the conventions' format, with the README snippet per image.</step>
	</steps>
	<rules>
		<rule>`shots.yml` is the source of truth once approved; edits go there, not into ad hoc CLI flags.</rule>
		<rule>Never capture a deployed URL that needs login; use the dev server with seeded data and say so.</rule>
		<rule>No colour or margin decisions in this skill; the frame block owns them.</rule>
	</rules>
</asset-shot>
```
