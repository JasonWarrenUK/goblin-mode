# goblin-chrome

> [!NOTE]
> A Claude Code mod from [goblin-mode](https://github.com/JasonWarrenUK/goblin-mode): goblin-mode's face inside the terminal. Pure chrome. It changes nothing Claude does.

---

## 1. Install

```sh
claude plugin marketplace add JasonWarrenUK/goblin-mode
claude plugin install goblin-chrome@goblin-mode
```

Needs Claude Code 2.1.287 or later. Draws in the terminal; the hooks run everywhere else and draw nothing.

---

## 2. What it draws

| Where | What |
|---|---|
| The band above the prompt | Three ranges split by dividers. The tier's rune at the left; the goblin in the middle, pacing while nothing happens, sitting after five minutes, sleeping after ten, startling when a prompt goes in, watching while Claude works and answering a poke; its dialogue at the right. While a skill runs it holds that family's prop, `(ಠ_ಠ)[#]` for `pr`; each subagent out stands beside it as a minion, `o.O ಠ.ಠ  (ಠ_ಠ)`, three shown and the rest a count. |
| The spinner | While a skill with `goblin-spinner` words runs, one of them a minute in the house dress: `••• dElEtInG eViDeNcE •••`. A subagent's spinner keeps the engine's word. |
| The line that closes a turn | `dOnE. 42s. tOoK 7 tHiNgS. bIt mE oNcE.` with the real numbers. |
| The hint under the prompt | The engine's line stays live; a tail in the goblin's register reacts to a fresh session, idling, an unsent draft and typing mid-turn. |
| Every question Claude asks | A face above the dialog, expression by context: expectant, nervous after a failed tool, folded arms for an interrogation, grinning late at night. |
| The goblin's dialogue | The band's right-hand range, for six seconds at a time: a poke, a yawn, a subagent going out or returning, a compaction, a `/clear` and the commit-msg hook bouncing a message. |

The band and the question box take their frame from the model that served the last request, so a `/model` switch shows once a reply has come back from it: each model has its own frame and theme colour.

| Model | Rune | Frame | Colour |
|---|---|---|---|
| Fable | `ᚠ` | double line `╔═╗` | `accent` |
| Opus | `ᛟ` | heavy line `┏━┓` | `accent-2` |
| Sonnet | `ᛊ` | round `╭─╮` | `info` |
| Haiku | `ᚺ` | dotted, plus corners `+┈+`, dimmed | `ok` |

A skill that pinned one model while another answered draws `singleDouble` in `warn` with both runes. The band is drawn by hand with tees where the dividers meet the rules; the question box uses the engine's own border, which has no dotted style, so Haiku's box there is plain ASCII.

### 2.1. What it reads from skills and agents

When a skill's prompt is expanded, the mod reads its `SKILL.md` from `~/.claude/skills/` first, then `<project>/.claude/skills/`. Plugin skills live elsewhere and read as nothing set. What is read from a skill lasts until the turn completes; a minion lasts until its own turn completes or the session starts over.

| Field | Where | What it does |
|---|---|---|
| `model` | top level | Pins the frame's tier; a different model answering draws the mismatch frame. |
| `metadata.family` | under `metadata:` | Picks the prop the goblin holds, from the `PROPS` table in `hooks/goblin.ts`: a parcel for `pr`, a lens for `clod-lens`, a pen for `clod-approach`. A family without a prop walks empty-handed. |
| `metadata.goblin-spinner` | under `metadata:` | Bar-separated spinner words, `merging\|deleting evidence\|tagging`, shown one a minute. |
| `goblin-minion` | top level of an agent file | The face the subagent wears in the parade, one to five single-width characters; `o.o` when unset. Agent files are read from `~/.claude/agents/` then `<project>/.claude/agents/`. |

A prop is up to four terminal cells of BMP text, so the band's arithmetic holds; the sprite grows by the prop's width and the pacing room shrinks to match. Widths are measured as a terminal draws them: a CJK ideograph such as the one in `[三]` counts two cells, while ambiguous-width glyphs (box drawing, shades, arrows, geometric shapes) count one, as the band's own frame already assumes. A minion face that would not fit the rule (wider than five cells, a space, an emoji) is ignored for the default.

The day has nine states on the local clock, fading over ten minutes, shifted one row towards lively on a Friday from four, one towards tired on a Sunday and one towards tired once the session passes four hours. Colours come from the project's theme in `.claude/themes/`, the `clod` family when it has none.

---

## 3. Options

Set in `/config` or under `pluginConfigs` in `settings.json`.

| Option | Default | What it does |
|---|---|---|
| `enabled` | `true` | The one switch. Off, every hook passes through and nothing draws. |
| `audio` | `false` | Play `fx/cackle.wav` when the commit-msg hook bounces a message. |
| `schedule` | `04=bed,06=caught,08=grumpy,11=functional,14=slump,16=second,19=perking,22=prime,01=feral` | `HH=state` or `HH:MM=state` pairs, 24h local. A malformed schedule falls back to the default whole. |
| `theme` | empty | A theme family in `.claude/themes` to dress in. Empty picks the only family there, else `clod`. |

---

## 4. Files

| File | Holds |
|---|---|
| `hooks/register.tsx` | The hooks module: every event handled and every drawing |
| `hooks/idle.tsx` | The idle goblin, a `Client` surface module with its own frame clock and pointer; the prop in its hand and the minion parade |
| `hooks/goblin.ts` | The question face as Raster cells, the props by family, the poke lines, the heckles |
| `hooks/frontmatter.ts` | The five keys read from a skill or agent file's frontmatter, as text |
| `hooks/day.ts` | The schedule, the ladder, the offsets, the fade and each state's style |
| `hooks/tier.ts` | Model id to tier, the skill pin, the frame per tier |
| `hooks/theme.ts` | Palette resolution per `library/references/theme-conventions.md` |
| `types/index.d.ts` | The `$.state` contract: `palette`, `day`, `frame`, `vitals`, `idle`, `run`, readable by a plugin that lists this one under `dependencies` |

Check it with `claude plugin validate marketplace/goblin-chrome` and `claude plugin test marketplace/goblin-chrome`; type-check with `tsc -p marketplace/goblin-chrome` once a session has laid the engine's types beside the manifest.
