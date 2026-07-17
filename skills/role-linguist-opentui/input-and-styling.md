# Keyboard Input, Focus, Colours, Console, Environment Variables

Detail for `opentui-operative`.

## Keyboard Input

### Global Key Handler

```typescript
renderer.keyInput.on("keypress", (key: KeyEvent) => {
  console.log(key.name, key.ctrl, key.shift, key.meta)
})

renderer.keyInput.on("paste", (event: PasteEvent) => {
  console.log(event.text)
})
```

### KeyEvent Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | `string` | Key identifier (e.g. "a", "escape", "f1", "return") |
| `sequence` | `string` | Raw escape sequence |
| `ctrl` | `boolean` | Ctrl modifier |
| `shift` | `boolean` | Shift modifier |
| `meta` | `boolean` | Alt/Meta modifier |
| `option` | `boolean` | macOS Option key |

**Event methods:** `preventDefault()`, `stopPropagation()`

### Per-Renderable Key Handling

```typescript
new InputRenderable(renderer, {
  onKeyDown: (key) => {
    if (key.name === "escape") input.blur()
  },
  onPaste: (event) => { console.log(event.text) },
})
```

### Raw Input Handler

```typescript
renderer.addInputHandler((sequence) => {
  if (sequence === "\x1b[A") return true   // consumed
  return false                              // pass through
})
```

## Focus Management

```typescript
input.focus()           // Give focus
input.blur()            // Remove focus
console.log(input.focused)   // Check state
```

**Auto-focus:** Left-clicking a renderable auto-focuses nearest focusable ancestor. Disable globally with `{ autoFocus: false }` or per-interaction with `event.preventDefault()` in `onMouseDown`.

**Events:**
```typescript
import { RenderableEvents } from "@opentui/core"
input.on(RenderableEvents.FOCUSED, () => { })
input.on(RenderableEvents.BLURRED, () => { })
```

**Internal key routing:** `focus()` uses `_internalKeyInput.onInternal()` — the renderer's internal key handler that ensures global handlers can `preventDefault` before renderable handlers process events.

## Colours

### RGBA Class

```typescript
import { RGBA } from "@opentui/core"

RGBA.fromInts(255, 0, 0, 255)        // From integers (0-255)
RGBA.fromValues(0.0, 1.0, 0.0, 1.0)  // From normalised floats (0.0-1.0)
RGBA.fromHex("#800080")               // From hex string
RGBA.fromHex("#FF000080")             // With alpha
```

### String Colour Support

Components accept: hex strings (`"#FF0000"`), CSS colour names (`"red"`), RGBA objects, `"transparent"`.

### parseColor() Utility

```typescript
import { parseColor } from "@opentui/core"
const rgba = parseColor("#FF0000")   // Converts various formats to RGBA
```

### Common Constants

`RGBA.white`, `RGBA.black`, `RGBA.red`, `RGBA.green`, `RGBA.blue`, `RGBA.transparent`

> **Palette advisory:** When choosing hex values for OpenTUI components, prefer colours from [Reasonable Colors](https://www.reasonable.work/colors/) (`library/references/reasonable-colors-reference.md`). The LCH-based palette is designed for consistent rendering across display types, which matters more in terminal contexts than web. Use `RGBA.fromHex()` with RC hex values directly.

## Console Overlay

OpenTUI captures all `console.log/info/warn/error/debug` calls to prevent interference with the UI.

```typescript
const renderer = await createCliRenderer({
  consoleOptions: {
    position: ConsolePosition.BOTTOM,   // TOP | BOTTOM | LEFT | RIGHT
    sizePercent: 30,
  },
})

renderer.console.toggle()
```

**Keyboard (when focused):** Arrow keys to scroll, `+`/`-` to resize.

**Env vars:**
- `OTUI_USE_CONSOLE=false` — disable capture
- `SHOW_CONSOLE=true` — start visible
- `OTUI_DUMP_CAPTURES=true` — output on exit

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OTUI_USE_ALTERNATE_SCREEN` | `true` | Alternate screen buffer |
| `OTUI_SHOW_STATS` | `false` | Debug overlay at startup |
| `OTUI_DEBUG` | `false` | Debug input capture |
| `OTUI_NO_NATIVE_RENDER` | `false` | Disable native rendering |
| `OTUI_DUMP_CAPTURES` | `false` | Dump captured output on exit |
| `OTUI_OVERRIDE_STDOUT` | `true` | Override stdout (debug) |
| `OTUI_USE_CONSOLE` | `true` | Enable console capture |
| `SHOW_CONSOLE` | `false` | Show console at startup |
| `OTUI_TS_STYLE_WARN` | `false` | Warn on missing syntax styles |
| `OTUI_TREE_SITTER_WORKER_PATH` | `""` | Tree-sitter worker path |
| `OTUI_DEBUG_FFI` | `false` | Debug logging for FFI |
| `OTUI_TRACE_FFI` | `false` | Tracing for FFI |
| `OPENTUI_FORCE_WCWIDTH` | `false` | Use wcwidth for char widths |
| `OPENTUI_FORCE_UNICODE` | `false` | Force Mode 2026 Unicode |
| `OPENTUI_NO_GRAPHICS` | `false` | Disable Kitty graphics detection |
| `OPENTUI_FORCE_NOZWJ` | `false` | No ZWJ width method |
| `OPENTUI_FORCE_EXPLICIT_WIDTH` | — | Force explicit width detection |
