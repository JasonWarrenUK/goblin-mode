# Gum command reference

Every flag, default and keybinding below was read from `gum <cmd> --help` on v2.0.1 or from the command's Go source (`<cmd>/options.go`, `<cmd>/command.go`, `<cmd>/<cmd>.go`). Style sub-flags (`--x.foreground` and friends) are listed by prefix only; see [styling.md](styling.md) for the full set each prefix accepts.

Common to every interactive command: `--timeout=0s` (exit `124` when it elapses), `--[no-]show-help` (default on), `--padding "V H"`, `--header` where listed. Common to every command that reads stdin: `--[no-]strip-ansi` (default strip).

---

## choose

```
gum choose [<options>...] [flags]
```

Options come from args or, when there are none, from stdin split on `--input-delimiter` (default newline). **If both args and stdin are present, stdin is parsed as the `--selected` list.** It never adds options.

| Flag | Default | Notes |
|---|---|---|
| `--limit N` | `1` | Max items. Selection prefixes are hidden at 1 |
| `--no-limit` | | Unlimited; enables `ctrl+a` select-all |
| `--select-if-one` | | Print the only option and exit 0 without a TUI |
| `--ordered` | | Output follows the order items were toggled. Also sorts the displayed list alphabetically |
| `--height N` | `10` | Rows per page; longer lists paginate with dots |
| `--header TEXT` | `"Choose:"` | |
| `--cursor STR` | `"> "` | |
| `--cursor-prefix` `--selected-prefix` `--unselected-prefix` | `"• "` `"✓ "` `"• "` | Only shown when limit > 1 |
| `--selected a,b` | | Pre-selected items; `*` selects all. With limit 1 it just places the cursor |
| `--label-delimiter ":"` | `""` | Options are `label:value`; the label is shown, the value is printed. Every option must contain the delimiter or gum errors |
| `--input-delimiter` `--output-delimiter` | `"\n"` | |
| Style prefixes | | `cursor`, `header`, `item`, `selected` |

Keys: `↓`/`j`/`ctrl+n` and `↑`/`k`/`ctrl+p` move; `←`/`h` and `→`/`l` change page; `g`/`home` and `G`/`end` jump. Multi-select toggle: `space`, `tab`, `x` or `ctrl+@`. Select all (no-limit only): `a`, `A` or `ctrl+a`. Submit: `enter` or `ctrl+q`. Quit: `esc` (exit 1, "nothing selected"). Abort: `ctrl+c` (exit 130).

Output: selected values joined by `--output-delimiter`, ANSI-stripped when stdout is not a TTY.

---

## confirm

```
gum confirm [<prompt>] [flags]
```

Prompt defaults to `"Are you sure?"`. Exit `0` for affirmative, `1` for negative.

| Flag | Default | Notes |
|---|---|---|
| `--default` | `true` | Which button starts selected and what a timeout returns. Use `--default=false` for No |
| `--affirmative TEXT` `--negative TEXT` | `Yes` `No` | `--negative ""` hides the No button entirely |
| `--show-output` | | Also prints `<prompt> <chosen label>` to stdout |
| `--timeout` | `0s` | On expiry returns the default answer (exit 0 or 1), not 124 |
| Style prefixes | | `prompt`, `selected`, `unselected` |

**Piped stdin bypasses the TUI**: the first line `y` or `yes` exits 0; anything else exits 1. `echo y | gum confirm` is the scripting escape hatch.

Keys: `y`/`Y` yes; `n`/`N`/`q` no; `←`/`→`/`h`/`l`/`tab`/`shift+tab`/`ctrl+n`/`ctrl+p` toggle; `enter` submits the highlighted button; `esc` is No (exit 1); `ctrl+c` exit 130.

---

## file

```
gum file [<path>] [flags]
```

Starts at `<path>` (default `.`). Prints the selected absolute path.

| Flag | Default | Notes |
|---|---|---|
| `--file` | `true` | Allow selecting files |
| `--directory` | `false` | Allow selecting directories. At least one of the two must be true |
| `-a, --all` | | Show dotfiles |
| `-p, --[no-]permissions` `-s, --[no-]size` | shown | |
| `-c, --cursor STR` | `">"` | |
| `--height N` | `10` | 0 means fit the terminal |
| `--header TEXT` | | |
| Style prefixes | | `cursor`, `symlink`, `directory`, `file`, `permissions`, `selected`, `file-size`, `header` |

Keys (bubbles filepicker defaults): `j`/`↓`/`ctrl+n` and `k`/`↑`/`ctrl+p` move; `J`/`pgdown` and `K`/`pgup` page; `g`/`G` first and last; `l`/`→`/`enter` opens a directory; `h`/`←`/`backspace` goes back; `enter` on a file selects it. Gum binds `esc`/`q` to quit (exit 1, "no file selected") ahead of the picker's own `esc`, so `esc` never navigates up. `ctrl+c` aborts.

---

## filter

```
gum filter [<options>...] [flags]
```

Options from args, else stdin split on `--input-delimiter`. **With neither, it lists files under the current directory.**

| Flag | Default | Notes |
|---|---|---|
| `--limit N` `--no-limit` `--select-if-one` | `1` | As `choose`. `--select-if-one` fires when the initial match set has a single entry |
| `--[no-]strict` | strict | Strict returns only a matched item. `--no-strict` returns the typed text when nothing matches |
| `--[no-]fuzzy` | fuzzy | Off means prefix-of-word matching |
| `--[no-]fuzzy-sort` | sort | Rank by fuzzy score; off keeps input order |
| `--value TEXT` | | Initial filter text |
| `--placeholder` `--prompt` | `"Filter..."` `"> "` | |
| `--header TEXT` | | |
| `--width N` `--height N` | `0` | 0 fills the terminal |
| `--reverse` | | Prompt at the bottom, list above (fzf-style) |
| `--indicator` `--selected-prefix` `--unselected-prefix` | `"•"` `" ◉ "` `" ○ "` | |
| `--selected a,b` | | Pre-select; `*` for all |
| `--input-delimiter` `--output-delimiter` | `"\n"` | |
| Style prefixes | | `indicator`, `selected-indicator`, `unselected-prefix`, `header`, `text`, `cursor-text`, `match`, `prompt`, `placeholder` |

Keys: typing filters; `↓`/`ctrl+n`/`ctrl+j` and `↑`/`ctrl+p`/`ctrl+k` move. `esc` first blurs the search box (then `j`/`k`/`g`/`G` navigate) and a second `esc` quits; `/` refocuses the search. Multi-select: `tab` toggles and moves down, `shift+tab` toggles and moves up, `ctrl+@` (ctrl+space) toggles in place, `ctrl+a` selects all. `enter`/`ctrl+q` submit; `ctrl+c` aborts.

Output: multi-select results come out in **map order, which is not stable**. Sort the output yourself or use `choose --ordered` when order matters. ANSI in options is stripped for matching but the original coloured string is what gets printed.

---

## format

```
gum format [<template>...] [flags]
```

| Flag | Default | Notes |
|---|---|---|
| `-t, --type` | `markdown` | `markdown`, `template`, `code`, `emoji` |
| `--theme` | `pink` | Markdown only: `dark`, `light`, `pink`, `dracula`, `notty`, `ascii`, `tokyo-night`, or a path to a Glamour style JSON |
| `-l, --language` | | Code only; Chroma lexer name |

Args are joined with newlines; otherwise stdin. Use `--` before args that start with `#` or `-`: `gum format -- "# Title" "- item"`. Template helpers and details in [styling.md](styling.md).

---

## input

```
gum input [flags]
```

| Flag | Default | Notes |
|---|---|---|
| `--placeholder` `--prompt` | `"Type something..."` `"> "` | |
| `--value TEXT` | | Initial value; stdin is used if this is empty |
| `--char-limit N` | **`400`** | 0 for unlimited |
| `--width N` | `0` | 0 is terminal width |
| `--password` | | Masks characters |
| `--header TEXT` | | |
| `--cursor.mode` | `blink` | `blink`, `hide`, `static` |
| Style prefixes | | `prompt`, `placeholder`, `cursor`, `header` |

Keys: standard textinput editing; `enter` submits; `esc` quits (exit 1); `ctrl+c` aborts.

---

## join

```
gum join <text>... [--horizontal | --vertical] [--align left|center|right|top|middle|bottom]
```

Horizontal by default. Quote every block argument. Details in [styling.md](styling.md).

---

## log

```
gum log <text>... [flags]
```

Writes to **stderr** unless `-o/--file` is given (appends). Uses `charmbracelet/log`.

| Flag | Default | Notes |
|---|---|---|
| `-l, --level` | `none` | `none`, `debug`, `info`, `warn`, `error`, `fatal`. `fatal` exits 1 after logging |
| `-s, --structured` | | First arg is the message, the rest are `key value` pairs |
| `-f, --format` | | First arg is a printf template; **all args are strings, so use `%s`**. Mutually exclusive with `-s` |
| `--formatter` | `text` | `text`, `json`, `logfmt` |
| `-t, --time FMT` | | Named: `kitchen`, `rfc822`, `rfc3339`, `datetime`, `dateonly`, `timeonly`, `stamp`, `ansic`, `unixdate` and the other Go `time` constants (case-insensitive); anything else is a Go layout string |
| `--prefix TEXT` | | Rendered as `PREFIX: message` |
| `--min-level LVL` | | Suppress lines below this level. Env `GUM_LOG_LEVEL` is the usual way to set it script-wide |
| `-o, --file PATH` | | Append to a file; nothing goes to stderr |
| Style prefixes | | `level`, `time`, `prefix`, `message`, `key`, `value`, `separator` |

```zsh
gum log --level info --structured "Deploying" env prod version "$v"   # INFO Deploying env=prod version=1.2
gum log --formatter json --level warn --time rfc3339 "Slow response"  # {"time":"...","level":"warn","msg":"Slow response"}
GUM_LOG_LEVEL=warn gum log --level debug "hidden"                     # prints nothing
```

Without `-s` or `-f` every arg is joined with spaces into one message.

---

## pager

```
gum pager [<content>] [flags]
```

Content from the argument or stdin. Exits 0 on quit; a `--timeout` exits 124. Unlike the other TUIs, `pager` draws on **stdout**, so it cannot sit inside `$(...)` or a pipeline.

| Flag | Default | Notes |
|---|---|---|
| `--show-line-numbers` | off | |
| `--[no-]soft-wrap` | wrap | |
| Style | | top-level `--foreground`/`--background`, prefixes `line-number`, `match`, `match-highlight`, `help` |

Keys: viewport scrolling (`↑`/`k`, `↓`/`j`, `pgup`/`b`, `pgdown`/`space`/`f`, `u`/`ctrl+u` and `d`/`ctrl+d` half pages); `g`/`home` top, `G`/`end` bottom; `/` opens search, `enter` confirms it, `n` next match, `N`/`p` previous, `esc`/`ctrl+c`/`ctrl+d` cancel the search; `q`/`esc` quit; `ctrl+c` aborts.

---

## spin

```
gum spin [flags] -- <command>...
```

Runs the command with a spinner on stderr. **Exit code is the command's own.** Put `--` before the command so its flags are not parsed by gum.

| Flag | Default | Notes |
|---|---|---|
| `-s, --spinner` | `dot` | `line`, `dot`, `minidot`, `jump`, `pulse`, `points`, `globe`, `moon`, `monkey`, `meter`, `hamburger` |
| `--title TEXT` | `"Loading..."` | |
| `-a, --align` | `left` | `left` or `right` of the title |
| `--show-output` | | Stream stdout and stderr while running (TTY only) |
| `--show-stdout` `--show-stderr` | | Stream one of them (TTY only) |
| `--show-error` | | Show the command's output only if it fails |
| Style prefixes | | `spinner`, `title` |

When stdout is not a TTY the command's output passes straight through regardless of `--show-output`, which is why `result=$(gum spin -- cmd)` captures cleanly. With `--show-output` on a TTY the output is printed after the spinner clears, so `$(...)` capture inside a terminal also works.

---

## style

```
gum style [<text>...] [flags]
```

See [styling.md](styling.md) for the full flag table. Highlights: `--border rounded`, `--padding "1 2"`, `--margin "1 0"`, `--foreground 212`, `--bold`, `--align center --width 50`. Each positional arg is one line. Env vars are unprefixed.

---

## table

```
gum table [flags]  < data.csv
```

Reads CSV from stdin or `-f/--file`. First row is the header unless `-c/--columns` supplies names. Interactive by default: prints the chosen row as CSV to stdout. `-p/--print` renders a static table instead.

| Flag | Default | Notes |
|---|---|---|
| `-s, --separator` | `,` | Single character |
| `-c, --columns a,b` | | Override or supply headers (then every row is data) |
| `-w, --widths 10,20` | auto | Per-column widths; unset means fit the widest cell |
| `--height N` | `0` | Visible rows |
| `-r, --return-column N` | `0` | 1-based column to print; 0 prints the whole row |
| `-p, --print` | | Static render, no TTY needed |
| `-b, --border` | `rounded` | Print mode: `rounded`, `thick`, `normal`, `hidden`, `double`, `none` |
| `--lazy-quotes` | | Tolerate stray quotes in fields |
| `--fields-per-record N` | `0` | Enforce column count |
| `--[no-]hide-count` | shown | Row count in the help line |
| Style prefixes | | `border`, `cell`, `header`, `selected` |

Rows with fewer fields than columns are padded; rows with more error out with `invalid number of columns`.

Keys: `↑`/`↓` navigate; `enter` selects; `esc`/`q`/`ctrl+q` quit; `ctrl+c` aborts. **Quitting exits 0 with an empty line on stdout** (verified through a pty), unlike every other picker, so test for empty output rather than a non-zero status.

```zsh
gum table < flavours.csv | cut -d, -f1          # whole row, then cut
gum table --return-column 1 < flavours.csv      # same thing, no cut
gum table --print --border double < report.csv  # static
```

---

## version-check

```
gum version-check '<constraint>'
```

Semver constraint such as `'>=2.0.0'`, `'~1.14'`, `'<3'`. Exit 0 when the running gum satisfies it, 1 (with a message on stderr) when not. Quote the constraint so the shell does not treat `>` as a redirect.

---

## write

```
gum write [flags]
```

| Flag | Default | Notes |
|---|---|---|
| `--width N` `--height N` | `0` `5` | 0 width is terminal width |
| `--placeholder` `--prompt` | `"Write something..."` `"┃ "` | |
| `--header TEXT` | | |
| `--value TEXT` | | Initial text; stdin used if empty (carriage returns removed) |
| `--char-limit N` | `0` | Unlimited by default (unlike `input`) |
| `--max-lines N` | `0` | |
| `--show-cursor-line` `--show-line-numbers` | off | |
| `--cursor.mode` | `blink` | |
| Style prefixes | | `base`, `cursor-line-number`, `cursor-line`, `cursor`, `end-of-buffer`, `line-number`, `header`, `placeholder`, `prompt` |

Keys: **`enter` submits**; `ctrl+j` inserts a newline; `ctrl+e` opens `$EDITOR` on the current text and reloads it on exit; `esc` quits (exit 1, "not submitted"); `ctrl+c` aborts. The README's `ctrl+d` is not bound in v2.
