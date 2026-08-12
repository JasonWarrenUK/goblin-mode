# Component Reference

Detail for `opentui-operative` — the full renderable catalogue (BoxRenderable through FrameBufferRenderable).

## BoxRenderable

Container with borders, backgrounds, and layout.

```typescript
new BoxRenderable(renderer, {
  id: "panel",
  width: 30, height: 10,
  backgroundColor: "#333366",
  borderStyle: "rounded",       // single | double | rounded | heavy
  borderColor: "#FFFFFF",
  border: true,                 // must be true for border to show
  title: "Panel Title",
  titleAlignment: "center",    // left | center | right
  padding: 1,
  gap: 1,
  flexDirection: "column",
  justifyContent: "center",
  alignItems: "flex-start",
  flexGrow: 1,
})
```

**Mouse events:** `onMouseDown`, `onMouseOver`, `onMouseOut`, `onMouseUp`, `onMouseMove`, `onMouseDrag`, `onMouseDragEnd`, `onMouseDrop`, `onMouseScroll`, `onMouse` (catch-all).

Mouse events bubble up. Stop with `event.stopPropagation()`.

## TextRenderable

Read-only styled text.

```typescript
new TextRenderable(renderer, {
  content: "Hello!",           // string or StyledText
  fg: "#00FF00",               // string | RGBA
  bg: "#000000",
  attributes: TextAttributes.BOLD | TextAttributes.UNDERLINE,
  selectable: true,
})
```

**Text attributes** (combine with bitwise OR): `BOLD`, `DIM`, `ITALIC`, `UNDERLINE`, `BLINK`, `INVERSE`, `HIDDEN`, `STRIKETHROUGH`

**Template literals:**
```typescript
import { t, bold, fg } from "@opentui/core"
text.content = t`${bold("Hello")} ${fg("#FF0000", "world")}!`
```

Helpers: `bold`, `dim`, `italic`, `underline`, `blink`, `reverse`, `strikethrough`, `fg`, `bg`

**GOTCHA:** `TextRenderable.content` returns a `StyledText` object, not a plain string. To read the raw text: `text.content.chunks[0].text`.

## SelectRenderable

Vertical list for choosing options.

```typescript
import { SelectRenderable, SelectRenderableEvents } from "@opentui/core"

const select = new SelectRenderable(renderer, {
  options: [
    { name: "Option 1", description: "First option", value: "one" },
    { name: "Option 2", description: "Second option", value: "two" },
  ],
  backgroundColor: theme.background,       // default is transparent (appears black!)
  selectedBackgroundColor: theme.highlight,
  selectedTextColor: theme.text,
  textColor: theme.text,
  descriptionColor: theme.textMuted,
  showDescription: true,
  showScrollIndicator: true,
  wrapSelection: false,
  fastScrollStep: 5,
  flexGrow: 1,
})
renderer.root.add(select)
select.focus()   // REQUIRED for keyboard input
```

**Keyboard controls:**

| Key | Action |
|-----|--------|
| Up / k | Move selection up |
| Down / j | Move selection down |
| Shift+Up / Shift+Down | Fast scroll (5 items) |
| Enter | Select current item |

**Events:**

```typescript
// ITEM_SELECTED: fires on Enter
select.on(SelectRenderableEvents.ITEM_SELECTED, (index: number, option: SelectOption) => {
  console.log(option.value)
})

// SELECTION_CHANGED: fires when highlighted item changes
select.on(SelectRenderableEvents.SELECTION_CHANGED, (index: number, option: SelectOption) => {
  console.log("Now highlighting:", option.name)
})
```

**SelectOption interface:**
```typescript
interface SelectOption {
  name: string
  description: string
  value?: any
}
```

**Programmatic methods:**
- `getSelectedIndex()` / `getSelectedOption()`
- `setSelectedIndex(n)` / `moveUp()` / `moveDown()` / `selectCurrent()`
- Dynamic updates: set `options`, `showDescription`, `showScrollIndicator`, `wrapSelection` as properties

**GOTCHA:** `backgroundColor` defaults to transparent — set it explicitly or items appear with black backgrounds.

## InputRenderable

Single-line text input.

```typescript
import { InputRenderable, InputRenderableEvents } from "@opentui/core"

const input = new InputRenderable(renderer, {
  width: 25,
  placeholder: "Enter your name...",
  value: "",
  maxLength: 1000,
  backgroundColor: "#1a1a1a",
  focusedBackgroundColor: "#222222",
  textColor: "#FFFFFF",
  cursorColor: "#00FF88",
})
input.focus()

input.on(InputRenderableEvents.INPUT, (value) => { /* every keystroke */ })
input.on(InputRenderableEvents.CHANGE, (value) => { /* on blur or Enter, if changed */ })
input.on(InputRenderableEvents.ENTER, () => { /* Enter key pressed */ })
```

## TextareaRenderable

Multi-line editable text. **No construct API yet.**

```typescript
import { TextareaRenderable } from "@opentui/core"

const textarea = new TextareaRenderable(renderer, {
  width: 50, height: 6,
  placeholder: "Type notes here...",
  wrapMode: "word",           // none | char | word
  backgroundColor: "#1a1a1a",
  focusedBackgroundColor: "#222222",
  textColor: "#FFFFFF",
  cursorColor: "#00FF88",
  onSubmit: () => { console.log(textarea.plainText) },
  onContentChange: () => { /* content changed */ },
  onCursorChange: () => { /* cursor moved */ },
  keyBindings: [{ name: "return", ctrl: true, action: "submit" }],
})
textarea.focus()
```

**Properties:** `plainText` (string), `cursorOffset` (number)

## TabSelectRenderable

Horizontal tab selection.

```typescript
import { TabSelectRenderable, TabSelectRenderableEvents } from "@opentui/core"

const tabs = new TabSelectRenderable(renderer, {
  width: 60,
  options: [
    { name: "Tab 1", description: "First tab" },
    { name: "Tab 2", description: "Second tab" },
  ],
  tabWidth: 20,
  showScrollArrows: true,
  showDescription: true,
  showUnderline: true,
  wrapSelection: false,
})
tabs.focus()

tabs.on(TabSelectRenderableEvents.ITEM_SELECTED, (index, option) => { })
tabs.on(TabSelectRenderableEvents.SELECTION_CHANGED, (index, option) => { })
```

**Keys:** Left/`[` = prev, Right/`]` = next, Enter = select

**Methods:** `getSelectedIndex()`, `setSelectedIndex(n)`, `setOptions(array)`

## ScrollBoxRenderable

Scrollable container.

```typescript
const scrollbox = new ScrollBoxRenderable(renderer, {
  width: 60, height: 20,
  scrollX: false,
  scrollY: true,            // default
  stickyScroll: false,      // "bottom" | "top" | "left" | "right" when truthy
  viewportCulling: true,    // Render only visible children (default)
})
```

**Keyboard (when focused):** Arrow keys, Page Up/Down, Home, End.

**Methods:**
- `scrollBy()` — relative scrolling by lines, pixels, or viewport
- `scrollTo()` — absolute positioning

**Internal structure:** `wrapper`, `viewport`, `content`, `horizontalScrollBar`, `verticalScrollBar`

**Sub-component options:** `rootOptions`, `wrapperOptions`, `viewportOptions`, `contentOptions`, `scrollbarOptions`

## ScrollBarRenderable

Standalone scrollbar. **No construct API yet.**

```typescript
const scrollbar = new ScrollBarRenderable(renderer, {
  orientation: "vertical",   // vertical | horizontal
  height: 10,
  showArrows: true,
  trackOptions: { backgroundColor: "#222222", foregroundColor: "#888888" },
  onChange: (position) => { console.log(position) },
})
scrollbar.scrollSize = 200
scrollbar.viewportSize = 20
scrollbar.scrollPosition = 0
scrollbar.focus()
```

**Keys:** Up/Down or k/j (vertical), Left/Right or h/l (horizontal), PageUp/Down, Home/End

## SliderRenderable

Draggable slider. **No construct API yet.**

```typescript
const slider = new SliderRenderable(renderer, {
  orientation: "horizontal",   // horizontal | vertical
  width: 30, height: 1,
  min: 0, max: 100, value: 25,
  backgroundColor: "#333",
  foregroundColor: "#0f0",
  onChange: (value) => { console.log(value) },
})
```

## ASCIIFontRenderable

ASCII art font display.

```typescript
new ASCIIFontRenderable(renderer, {
  text: "Iris",
  font: "block",            // tiny | block | shade | slick | huge | grid | pallet
  color: "#FFFFFF",          // or array for gradient: ["#FF0000", "#0000FF"]
  backgroundColor: "transparent",
  selectable: false,
})
```

Both Renderable (`ASCIIFontRenderable`) and Construct (`ASCIIFont`) APIs available.

## CodeRenderable

Syntax-highlighted code with Tree-sitter.

```typescript
import { CodeRenderable, SyntaxStyle, RGBA } from "@opentui/core"

const syntaxStyle = SyntaxStyle.fromStyles({
  default: { fg: RGBA.fromHex("#E6EDF3") },
  keyword: { fg: RGBA.fromHex("#FF7B72") },
  string: { fg: RGBA.fromHex("#A5D6FF") },
  comment: { fg: RGBA.fromHex("#8B949E"), italic: true },
  function: { fg: RGBA.fromHex("#D2A8FF") },
})

const code = new CodeRenderable(renderer, {
  content: "const x = 1;",
  filetype: "typescript",
  syntaxStyle,
  streaming: false,
  conceal: true,
  selectable: true,
  wrapMode: "none",
})
```

**Token names:** `keyword`, `string`, `comment`, `function`, `operator`, `variable`, `type`, `number`, `constant`, plus `markup.*` for markdown.

## MarkdownRenderable

Markdown renderer. **No construct API yet.**

```typescript
new MarkdownRenderable(renderer, {
  content: "# Hello\n\nSome **bold** text.",
  syntaxStyle,
  conceal: true,       // Hide markdown markers
  streaming: false,    // Incremental update optimisation
  renderNode: (node) => { /* custom rendering per block */ },
})
```

## LineNumberRenderable

Line number gutter. **No construct API yet.**

```typescript
const lineNumbers = new LineNumberRenderable(renderer, {
  target: codeRenderable,   // Must implement LineInfoProvider
  minWidth: 3,
  paddingRight: 1,
  fg: "#6b7280",
  bg: "#161b22",
})

lineNumbers.setLineColor(3, "#2b6cb0")
lineNumbers.setLineSign(3, { before: ">", beforeColor: "#2b6cb0" })
```

## DiffRenderable

Unified or split diffs. **No construct API yet.**

```typescript
new DiffRenderable(renderer, {
  diff: unifiedDiffString,
  view: "unified",          // unified | split
  filetype: "typescript",
  syntaxStyle,
  showLineNumbers: true,
  addedBg: "#1a4d1a",
  removedBg: "#4d1a1a",
  addedSignColor: "#22c55e",
  removedSignColor: "#ef4444",
})
```

## FrameBufferRenderable

Low-level rendering surface.

```typescript
new FrameBufferRenderable(renderer, {
  width: 40, height: 20,
  respectAlpha: false,
})
```

**Drawing methods:** `setCell`, `setCellWithAlphaBlending`, `drawText`, `fillRect`, `drawFrameBuffer`
