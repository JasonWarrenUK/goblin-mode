# Gum styling reference

Verified against gum v2.0.1 (`style/options.go`, `gum style --help`, `format/README.md`).

## Colour values

Two forms only:

| Form | Example | Notes |
|---|---|---|
| ANSI 256 index | `212`, `99`, `240` | `0`-`15` are the terminal's palette; `16`-`231` the colour cube; `232`-`255` greys |
| Hex | `"#FF0000"`, `"#04B575"` | Quote it so the shell never treats `#` as a comment |

Named colours (`red`, `pink`) are rejected. Gum's own accent is `212` (pink) with `99` (purple) for headers and `240` for muted text; matching those keeps a script visually consistent with gum's defaults.

Output colour is downgraded or stripped to suit the destination: piped stdout gets plain text, `NO_COLOR=1` strips even on a TTY and `CLICOLOR_FORCE=1` keeps ANSI when piping (useful when the output feeds `gum join` or a pager that understands colour).

## `gum style` flags

```
--foreground, --background            colour
--border                              none | hidden | normal | rounded | thick | double
--border-foreground, --border-background
--align                               left | center | right | bottom | middle | top
--width, --height                     integers; 0 means natural size
--margin, --padding                   "V H" or "T R B L" in cells, e.g. "1 2" or "0 1 0 1"
--bold --faint --italic --strikethrough --underline
--trim                                strip leading/trailing whitespace from every input line
--[no-]strip-ansi                     strip ANSI from stdin (default: strip)
```

Each positional argument becomes its own line inside the box, so `gum style --border rounded "Title" "Body"` renders two lines. Content can also come from stdin.

Env vars for `style` are unprefixed: `FOREGROUND`, `BACKGROUND`, `BORDER`, `BORDER_FOREGROUND`, `BORDER_BACKGROUND`, `ALIGN`, `HEIGHT`, `WIDTH`, `MARGIN`, `PADDING`, `BOLD`, `FAINT`, `ITALIC`, `STRIKETHROUGH`, `UNDERLINE`. Exporting `BORDER=double` therefore affects every `gum style` call in the session, which is convenient for theming a script and surprising when it leaks from a parent shell.

## Styled sub-elements on other commands

Every other command exposes its visual parts as a flag prefix. `--help` shows only `.foreground` and `.background` for each, but the whole `style` flag set is accepted under every prefix (the fields are declared `hidden` in `style/options.go`, not absent):

```
--<prefix>.foreground   --<prefix>.background
--<prefix>.border       --<prefix>.border-foreground   --<prefix>.border-background
--<prefix>.align        --<prefix>.width               --<prefix>.height
--<prefix>.margin       --<prefix>.padding
--<prefix>.bold  --<prefix>.faint  --<prefix>.italic  --<prefix>.strikethrough  --<prefix>.underline
```

Prefixes by command:

| Command | Prefixes |
|---|---|
| `choose` | `cursor`, `header`, `item`, `selected` |
| `confirm` | `prompt`, `selected`, `unselected` |
| `file` | `cursor`, `symlink`, `directory`, `file`, `permissions`, `selected`, `file-size`, `header` |
| `filter` | `indicator`, `selected-indicator`, `unselected-prefix`, `header`, `text`, `cursor-text`, `match`, `prompt`, `placeholder` |
| `input` | `prompt`, `placeholder`, `cursor`, `header` |
| `log` | `level`, `time`, `prefix`, `message`, `key`, `value`, `separator` |
| `pager` | (top-level `--foreground`/`--background`), `line-number`, `match`, `match-highlight`, `help` |
| `spin` | `spinner`, `title` |
| `table` | `border`, `cell`, `header`, `selected` |
| `write` | `base`, `cursor-line-number`, `cursor-line`, `cursor`, `end-of-buffer`, `line-number`, `header`, `placeholder`, `prompt` |

Examples from the upstream test script:

```zsh
gum write --base.padding 1 --cursor.foreground 99 --prompt.foreground 99
gum choose --cursor "* " --cursor.foreground 99 --selected.foreground 99 A B C
gum spin --title.bold --title.foreground 99 --spinner minidot -- sleep 1
```

Every command also takes a top-level `--padding "V H"` around the whole widget.

## Env var naming

`GUM_<COMMAND>_<FLAG>`, upper-cased, with every dot and hyphen becoming `_`:

| Flag | Env var |
|---|---|
| `gum input --placeholder` | `GUM_INPUT_PLACEHOLDER` |
| `gum choose --cursor.foreground` | `GUM_CHOOSE_CURSOR_FOREGROUND` |
| `gum filter --selected-indicator.foreground` | `GUM_FILTER_SELECTED_PREFIX_FOREGROUND` (note the mismatch) |
| `gum pager --match-highlight.foreground` | `GUM_PAGER_MATCH_HIGH_FOREGROUND` (note the mismatch) |
| `gum log --min-level` | `GUM_LOG_LEVEL` |
| `gum file <path>` | `GUM_FILE_PATH` |

Flags in the `Selection` group (`--limit`, `--no-limit`, `--select-if-one`, `--strict`) and `confirm`'s `--default`, `--affirmative`, `--negative` have no env var. `gum <cmd> --help` prints the exact var next to each flag; trust that over the pattern when they disagree.

A theme for a whole script is a block of exports at the top:

```zsh
export GUM_CHOOSE_CURSOR_FOREGROUND="#f14e32"
export GUM_CHOOSE_SELECTED_FOREGROUND="#f14e32"
export GUM_CONFIRM_SELECTED_BACKGROUND="#f14e32"
export GUM_INPUT_CURSOR_FOREGROUND="#f14e32"
export GUM_SPIN_SPINNER_FOREGROUND="#f14e32"
```

## `gum format`

`-t/--type`: `markdown` (default), `code`, `template`, `emoji`. Input is positional args (joined with newlines) or stdin.

**Markdown** themes (`--theme`): `dark`, `light`, `pink` (default), `dracula`, `notty`, `ascii`, `tokyo-night`. Any other value is treated as a path to a Glamour JSON style file, so a typo produces `glamour: error reading file`. Tables, lists, headings and fenced code all render.

**Code**: `-l/--language` picks the Chroma lexer (`ts`, `go`, `py`, `json`, `zsh` ...). Without it, Chroma guesses.

**Template**: Go templates with the Termenv helpers. Verified working: `Bold`, `Italic`, `Underline`, `Faint`, `CrossOut`, `Color "fg" "bg"`, `Foreground "fg"`, `Background "bg"`. Colour arguments follow the same 256-index or hex rules.

```zsh
echo '{{ Bold "Tasty" }} {{ Italic "Bubble" }} {{ Color "99" "0" " Gum " }}' | gum format -t template
```

**Emoji**: replaces `:name:` shortcodes using the GitHub emoji list (`:heart:`, `:candy:`, `:rocket:`).

`format` writes through the same colour-profile writer as `style`, so piped output is plain text unless `CLICOLOR_FORCE=1` is set.

## `gum join`

```
gum join [--horizontal | --vertical] [--align left|center|right|top|middle|bottom] BLOCK...
```

Horizontal is the default. Each argument is one block; multi-line blocks are placed side by side (horizontal) or stacked (vertical) and padded to align. `--align` controls the cross-axis (vertical position of shorter blocks in a horizontal join, horizontal position of narrower lines in a vertical join).

Always quote `$(gum style ...)` results when passing them to `join`, otherwise word-splitting destroys the newlines:

```zsh
left=$(gum style --border double --padding "1 3" "Left")
right=$(gum style --border double --padding "1 3" "Right")
gum join --horizontal --align center "$left" "$right"
```

`join` reads its own colour from the blocks it is given, so run the `style` calls with `CLICOLOR_FORCE=1` if the final output must keep colour when piped.

## Spinners

`--spinner` (or `-s`): `line`, `dot` (default), `minidot`, `jump`, `pulse`, `points`, `globe`, `moon`, `monkey`, `meter`, `hamburger`. `--align left|right` puts the spinner before or after the title.

## Cursor modes

`input` and `write` accept `--cursor.mode blink|hide|static`.
