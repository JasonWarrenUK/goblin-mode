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
| The band above the prompt | A goblin that paces while nothing happens, sits after five minutes, sleeps after ten, startles when a prompt goes in, watches while Claude works and can be poked with the mouse. Beside it a context metre and a line that says how full the bag is, in alternating caps. |
| The line that closes a turn | `dOnE. 42s. tOoK 7 tHiNgS. bIt mE oNcE.` with the real numbers. |
| The footer mode pills | `plan` is `sChEmInG`, accept-edits is `lEt It CoOk`, auto is `uNsUpErViSeD`, and the day adds its own. |
| The hint under the prompt | The engine's line stays live; a tail in the goblin's register reacts to a fresh session, idling, an unsent draft and typing mid-turn. |
| Every question Claude asks | A face above the dialog, expression by context: expectant, nervous after a failed tool, folded arms for an interrogation, grinning late at night. |
| Toasts | A subagent returning, a compaction, a `/clear` and the commit-msg hook bouncing a message. |

Every box takes its frame from the model that served the current request: double line for the top tier (`ᛟ`) and for Fable (`ᚠ`), round for the middle, ASCII and dim for the small one and a mismatched `singleDouble` with both runes when a skill pinned one tier and another answered. The pin is read from `~/.claude/skills/` first, then `<project>/.claude/skills/`; plugin skills carry no pin.

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
| `hooks/goblin.ts` | The face and metre as Raster cells, the voice line, the heckles |
| `hooks/day.ts` | The schedule, the ladder, the offsets, the fade and each state's style |
| `hooks/tier.ts` | Model id to tier, the skill pin, the frame per tier |
| `hooks/theme.ts` | Palette resolution per `library/references/theme-conventions.md` |
| `types/index.d.ts` | The `$.state` contract: `palette`, `day`, `frame`, `vitals`, `idle`, readable by a plugin that lists this one under `dependencies` |

Check it with `claude plugin validate marketplace/goblin-chrome` and `claude plugin test marketplace/goblin-chrome`; type-check with `tsc -p marketplace/goblin-chrome` once a session has laid the engine's types beside the manifest.
