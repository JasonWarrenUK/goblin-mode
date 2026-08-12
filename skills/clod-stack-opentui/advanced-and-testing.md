# Tree-sitter, Framework Bindings, Common Patterns, Testing, Gotchas

Detail for `opentui-operative`.

## Tree-sitter Integration

### Global Registration

```typescript
import { addDefaultParsers } from "@opentui/core"

addDefaultParsers([{
  filetype: "python",
  wasm: "https://github.com/tree-sitter/tree-sitter-python/releases/download/v0.23.6/tree-sitter-python.wasm",
  queries: {
    highlights: ["https://raw.githubusercontent.com/.../highlights.scm"],
  },
}])
```

### Per-Client

```typescript
const client = new TreeSitterClient({ dataPath: "./parsers" })
client.addFiletypeParser({ filetype, wasm, queries })
```

### Utilities

```typescript
pathToFiletype("/foo/bar.ts")   // "typescript"
extToFiletype(".py")            // "python"
```

## Framework Bindings

### Solid.js (`@opentui/solid`)

```bash
bun install solid-js @opentui/solid
```

JSX components (snake_case): `text`, `box`, `scrollbox`, `input`, `textarea`, `select`, `tab_select`, `code`, `diff`, `markdown`, `ascii_font`, `line_number`

Hooks: `useRenderer()`, `useKeyboard()`, `useTerminalDimensions()`, `onResize()`, `usePaste()`, `useSelectionHandler()`, `useTimeline()`

Entry: `render(<App />)` or `testRender(<App />)` for testing.

### React (`@opentui/react`)

```bash
bun add @opentui/react @opentui/core react
```

JSX components (kebab-case): `<text>`, `<box>`, `<scrollbox>`, `<input>`, `<textarea>`, `<select>`, `<tab-select>`, `<code>`, `<diff>`, `<markdown>`, `<ascii-font>`, `<line-number>`

Hooks: `useRenderer()`, `useKeyboard()`, `useOnResize()`, `useTerminalDimensions()`, `useTimeline()`

Entry: `createRoot(renderer).render(<App />)`

## Common Patterns

### Screen Pattern (Full-screen Views)

```typescript
const CONTAINER_ID = "my-screen-root"

class MyScreen {
  private renderer: Renderer
  private keyHandler?: (key: KeyEvent) => void

  constructor(renderer: Renderer) {
    this.renderer = renderer
  }

  async render(): Promise<Result> {
    return new Promise((resolve) => {
      const container = new BoxRenderable(this.renderer, {
        id: CONTAINER_ID,
        flexDirection: "column",
        width: "100%",
        height: "100%",
        backgroundColor: "#1a1a2e",
      })

      // ... build UI tree ...

      this.renderer.root.add(container)
      select.focus()

      this.keyHandler = (key) => {
        if (key.name === "escape") resolve({ action: "back" })
      }
      this.renderer.keyInput.on("keypress", this.keyHandler)
    })
  }

  cleanup(): void {
    if (this.keyHandler) {
      this.renderer.keyInput.off("keypress", this.keyHandler)
    }
    this.renderer.root.remove(CONTAINER_ID)
  }
}
```

### Application Lifecycle

```typescript
const renderer = await createCliRenderer({ exitOnCtrlC: true })

// Build UI...
renderer.root.add(container)

// When done:
renderer.destroy()   // ALWAYS call this
```

### Dynamic Content Updates

```typescript
// Update text content
text.content = "New content"          // Triggers re-render automatically

// Update select options
select.options = newOptions
select.setSelectedIndex(0)

// Update colours
text.fg = "#FF0000"
box.backgroundColor = "#333"
```

### Swapping Child Renderables

```typescript
// Remove old child by ID, add new one
if (oldChild) {
  parent.remove(oldChild.id)
}
const newChild = new TextRenderable(renderer, { content: "New" })
parent.add(newChild)
```

## Testing with Mock Renderer

When unit testing screens/components that use OpenTUI, mock the renderer:

```typescript
import { vi } from "vitest"

function createMockRenderer() {
  const mockRoot = { add: vi.fn(), remove: vi.fn() }
  const mockKeyInput = {
    on: vi.fn(), off: vi.fn(), once: vi.fn(),
    emit: vi.fn(), removeAllListeners: vi.fn(),
  }
  const mockInternalKeyInput = {
    on: vi.fn(), off: vi.fn(), once: vi.fn(), emit: vi.fn(),
    onInternal: vi.fn(), offInternal: vi.fn(), removeAllListeners: vi.fn(),
  }

  return {
    root: mockRoot,
    keyInput: mockKeyInput,
    _internalKeyInput: mockInternalKeyInput,
    start: vi.fn(), stop: vi.fn(),
    requestRender: vi.fn(),
    width: 80, height: 24,
    addToHitGrid: vi.fn(),
    pushHitGridScissorRect: vi.fn(),
    popHitGridScissorRect: vi.fn(),
    clearHitGridScissorRects: vi.fn(),
    setCursorPosition: vi.fn(),
    setCursorStyle: vi.fn(),
    setCursorColor: vi.fn(),
    widthMethod: "wcwidth" as const,
    capabilities: null,
    requestLive: vi.fn(), dropLive: vi.fn(),
    hasSelection: false,
    getSelection: vi.fn().mockReturnValue(null),
    requestSelectionUpdate: vi.fn(),
    currentFocusedRenderable: null,
    focusRenderable: vi.fn(),
    registerLifecyclePass: vi.fn(),
    unregisterLifecyclePass: vi.fn(),
    getLifecyclePasses: vi.fn().mockReturnValue(new Set()),
    clearSelection: vi.fn(),
    startSelection: vi.fn(),
    updateSelection: vi.fn(),
    on: vi.fn(), off: vi.fn(), once: vi.fn(),
    emit: vi.fn(), removeAllListeners: vi.fn(),
  }
}
```

**Key testing patterns:**
- `SelectRenderable.focus()` requires `_internalKeyInput` with `onInternal`/`offInternal`
- Screen `render()` returns a Promise that waits for user input — don't `await` in tests
- `TextRenderable.content` returns `StyledText`, not string — access via `.content.chunks[0].text`
- Call `buildUI()` before testing event handlers that depend on the renderable tree

## Gotchas & Pitfalls

1. **`remove()` takes a string ID, not a renderable instance** — `parent.remove(child.id)` not `parent.remove(child)`
2. **`renderer.destroy()` not `stop()`** — `destroy()` restores terminal state. `stop()` only stops the render loop.
3. **`exitOnCtrlC: true` is default** — no manual Ctrl+C handler needed
4. **Automatic rendering** — no `renderer.start()` call needed; re-renders on tree changes
5. **`SelectRenderable.focus()` is required** — keyboard input won't work without it
6. **`backgroundColor` defaults to transparent** — set explicitly on SelectRenderable or items appear black
7. **`TextRenderable.content` returns `StyledText`** — not a plain string. Read via `.chunks[0].text`
8. **`_internalKeyInput` needed for `focus()`** — mock renderers must include this with `onInternal`/`offInternal`
9. **OpenTUI does NOT auto-cleanup** — `process.exit` or unhandled errors won't restore terminal. Always call `destroy()`.
10. **Mouse events bubble** — stop with `event.stopPropagation()`
11. **`visible = false` removes from layout** — equivalent to CSS `display: none`, not `visibility: hidden`
