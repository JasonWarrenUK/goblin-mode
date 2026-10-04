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
| The band above the prompt | Three ranges split by dividers. The tier's rune at the left; the goblin in the middle, pacing while nothing happens, sitting after five minutes, sleeping after ten, startling when a prompt goes in, watching while Claude works and answering a poke; its dialogue at the right. |
| The line that closes a turn | `dOnE. 42s. tOoK 7 tHiNgS. bIt mE oNcE.` with the real numbers. |
| The hint under the prompt | The engine's line stays live; a tail in the goblin's register reacts to a fresh session, idling, an unsent draft and typing mid-turn. |
| Every question Claude asks | A face above the dialog, expression by context: expectant, nervous after a failed tool, folded arms for an interrogation, grinning late at night. |
| The goblin's dialogue | The band's right-hand range, for six seconds at a time: a poke, a yawn, a subagent returning, a compaction, a `/clear` and the commit-msg hook bouncing a message. |

The band and the question box take their frame from the model that served the last request, so a `/model` switch shows once a reply has come back from it: each model has its own frame and theme colour.

| Model | Rune | Frame | Colour |
|---|---|---|---|
| Fable | `ᚠ` | double line `╔═╗` | `accent` |
| Opus | `ᛟ` | heavy line `┏━┓` | `accent-2` |
| Sonnet | `ᛊ` | round `╭─╮` | `info` |
| Haiku | `ᚺ` | dotted, plus corners `+┈+`, dimmed | `ok` |

A skill that pinned one model while another answered draws `singleDouble` in `warn` with both runes. The band is drawn by hand with tees where the dividers meet the rules; the question box uses the engine's own border, which has no dotted style, so Haiku's box there is plain ASCII. The pin is read from `~/.claude/skills/` first, then `<project>/.claude/skills/`; plugin skills carry no pin.

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
| `hooks/idle.tsx` | The idle goblin, a `Client` surface module with its own frame clock and pointer |
| `hooks/goblin.ts` | The question face as Raster cells, the poke lines, the heckles |
| `hooks/day.ts` | The schedule, the ladder, the offsets, the fade and each state's style |
| `hooks/tier.ts` | Model id to tier, the skill pin, the frame per tier |
| `hooks/theme.ts` | Palette resolution per `library/references/theme-conventions.md` |
| `types/index.d.ts` | The `$.state` contract: `palette`, `day`, `frame`, `vitals`, `idle`, readable by a plugin that lists this one under `dependencies` |

Check it with `claude plugin validate marketplace/goblin-chrome` and `claude plugin test marketplace/goblin-chrome`; type-check with `tsc -p marketplace/goblin-chrome` once a session has laid the engine's types beside the manifest.
