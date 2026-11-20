# Metadata Is Whatever I Say It Is

One page on the pinned stage (scope M6 to M12). Two invented skills, `roast-commit` and `roast-branch`, gain keys of their own over four steps; every step shows the files whole as they stand after it. Counts in braces are generated at build time.

Draft status: copy only, for Jason's voice pass. Every behavioural claim is listed in **Sources** at the end; anything not settled is in **Open questions**.

---

## Opening

Claude Code reads a fixed list of frontmatter fields and leaves `metadata` to you. In this page, you'll give two skills keys of your own, write a script that reads them, then make the script catch the day one of those keys stops being true.

### 1. Define a Key

Start with a skill that roasts your last commit message. Its frontmatter fetches the commit and takes away Claude's tools for running commands, editing files and handing the job to a helper agent; the `metadata:` block at the bottom is the new part. Write any keys you like under it, with any values. Claude doesn't see them either. The skill listing carries only `description` and `when_to_use`, and a skill you run reaches Claude as its body alone.

`.claude/skills/roast-commit/SKILL.md` after step 1:

```markdown
---
name: roast-commit
description: Roast the last commit message.
model: sonnet
effort: low
allowed-tools: Bash(git log *)
disallowed-tools: [Agent, Bash, Edit, Write, NotebookEdit]
metadata:
  family: roast
  heat: mild
---

The last commit, fetched before you read this:

!`git log -1 --format='%h %s%n%n%b'`

Roast the message in two sentences: one on what it says, one
on what it leaves out. Be rude about the message, never the
person who wrote it.
```

New in 1: every line.

- **1a** `` !`git log -1 --format='%h %s%n%n%b'` `` runs before Claude reads the skill, and its output takes the line's place, so Claude reads the commit itself. `allowed-tools` approves `git log` for it; without that approval the skill stops before it starts.
- **1b** `disallowed-tools` takes these five away from Claude until your next message. Tools from MCP servers you've connected stay unless you list them too. The injected `git log` still runs with Bash on the list.
- **1c** `metadata:` holds keys of your own. Claude Code doesn't act on its contents and drops a value that isn't a map, so every key sits indented under it. Don't reuse a frontmatter field's name, such as `paths`, as a key.
- **1d** `family: roast` groups this skill with the others you'll write; for now, no script reads it.
- **1e** `heat: mild` is invented, key and value both. Nothing in Claude Code knows what a heat is, or that `mild` comes before `scorching`.

### 2. Read It

Nothing reads `heat` yet, so it does nothing. Add a second roast at the other end of the scale, then a script at `scripts/roast-menu.py` that lists every skill in the roast family, mildest first. Run it from the project's root with `python3 scripts/roast-menu.py`.

`.claude/skills/roast-branch/SKILL.md` after step 2:

```markdown
---
name: roast-branch
description: Roast every commit on this branch, in order.
model: opus
effort: high
allowed-tools: Bash(git log *)
disallowed-tools: [Agent, Bash, Edit, Write, NotebookEdit]
metadata:
  family: roast
  heat: scorching
---

Every commit on this branch since it left main:

!`git log main..HEAD --reverse --format='%h %s'`

Read them as one story and roast the story: where it changed
its mind, what it fixed twice and which message gave up. Be
rude about the commits, never the person who wrote them.
```

`scripts/roast-menu.py` after step 2:

```python
#!/usr/bin/env python3
"""Print the roast skills as a menu, mildest first."""
import re
from pathlib import Path

HEAT = ["mild", "medium", "scorching"]


def field(block: str, key: str) -> str:
	m = re.search(rf"^\s*{key}:\s*(.*)$", block, re.MULTILINE)
	return m.group(1).strip() if m else ""


menu = []
for path in sorted(Path(".claude/skills").glob("*/SKILL.md")):
	block = path.read_text().split("---")[1]
	if field(block, "family") != "roast":
		continue
	name, heat = field(block, "name"), field(block, "heat")
	rank = HEAT.index(heat) if heat in HEAT else len(HEAT)
	menu.append((rank, f"{heat or '?':<10} /{name:<14} {field(block, 'description')}"))

print("\n".join(line for _, line in sorted(menu)))
```

New in 2: both files, every line.

- **2a** `main..HEAD` is every commit on this branch since it left main, and `--reverse` puts them oldest first, so Claude reads the branch in the order it happened.
- **2b** `model: opus` at `effort: high`, because reading a whole branch as one story takes more than a single message does.
- **2c** `HEAT` holds the order. YAML has no idea that `mild` comes before `scorching`, so the script decides.
- **2d** `field()` reads the frontmatter as text with one regular expression. Python's standard library has no YAML parser, and `skill-lint.py` in this repository reads its keys the same way.
- **2e** A heat the script doesn't know sorts last, and a missing one prints as `?`. Nothing checked the value when you wrote it, so the script is the only place that decides what a typo means.

The script prints:

```text
mild       /roast-commit   Roast the last commit message.
scorching  /roast-branch   Roast every commit on this branch, in order.
```

### 3. Add a Key That Repeats Another Field

A script that wants to know whether a roast is safe to run on someone else's branch would rather read one word than a list of tools. Add `hands-off: true` to both roasts. It says what their `disallowed-tools` line already enforces. The menu prints the same as before, because nothing reads the new key yet.

`.claude/skills/roast-commit/SKILL.md` after step 3:

```markdown
---
name: roast-commit
description: Roast the last commit message.
model: sonnet
effort: low
allowed-tools: Bash(git log *)
disallowed-tools: [Agent, Bash, Edit, Write, NotebookEdit]
metadata:
  family: roast
  heat: mild
  hands-off: true
---

The last commit, fetched before you read this:

!`git log -1 --format='%h %s%n%n%b'`

Roast the message in two sentences: one on what it says, one
on what it leaves out. Be rude about the message, never the
person who wrote it.
```

`.claude/skills/roast-branch/SKILL.md` after step 3: the same `hands-off: true` line under `heat: scorching`.

New in 3: `hands-off: true` in both files.

- **3a** `hands-off: true` repeats what `disallowed-tools` enforces. Claude Code acts on the list and ignores the key.
- **3b** Change one and the other goes on saying what it said; Claude Code never compares them.

### 4. Check It

noor wants `roast-branch` to run `git blame` on the worst commit, takes Bash off its `disallowed-tools` list and leaves `hands-off: true` where it was. Claude has Bash again during the roast, and the frontmatter still says hands off. Teach the script what `hands-off` means, and make it fail when a skill claims it without taking those tools away.

`.claude/skills/roast-branch/SKILL.md` after step 4:

```markdown
---
name: roast-branch
description: Roast every commit on this branch, in order.
model: opus
effort: high
allowed-tools: Bash(git log *)
disallowed-tools: [Agent, Edit, Write, NotebookEdit]
metadata:
  family: roast
  heat: scorching
  hands-off: true
---

Every commit on this branch since it left main:

!`git log main..HEAD --reverse --format='%h %s'`

Read them as one story and roast the story: where it changed
its mind, what it fixed twice and which message gave up. Be
rude about the commits, never the person who wrote them.
```

`scripts/roast-menu.py` after step 4 (the opening lines folded):

```python
...
import sys
from pathlib import Path

HEAT = ["mild", "medium", "scorching"]
REMOVED = {"Agent", "Bash", "Edit", "Write", "NotebookEdit"}
...

menu, problems = [], []
for path in sorted(Path(".claude/skills").glob("*/SKILL.md")):
	block = path.read_text().split("---")[1]
	if field(block, "family") != "roast":
		continue
	name, heat = field(block, "name"), field(block, "heat")
	removed = set(re.findall(r"\w+", field(block, "disallowed-tools")))
	if field(block, "hands-off") == "true" and not REMOVED <= removed:
		problems.append(f"{name}: hands-off, but Claude keeps {', '.join(sorted(REMOVED - removed))}")
	rank = HEAT.index(heat) if heat in HEAT else len(HEAT)
	menu.append((rank, f"{heat or '?':<10} /{name:<14} {field(block, 'description')}"))

print("\n".join(line for _, line in sorted(menu)))
for problem in problems:
	print(problem, file=sys.stderr)
sys.exit(1 if problems else 0)
```

Changed in 4: `Bash` gone from `roast-branch`'s list; in the script, `import sys`, the `REMOVED` line, the two `hands-off` lines and the last three.

- **4a** `disallowed-tools` has lost Bash; `hands-off: true` is still there.
- **4b** `REMOVED` writes down what `hands-off` means, once, in the only place that reads it.
- **4c** `REMOVED <= removed` holds when every tool in `REMOVED` is also on the skill's list.
- **4d** `sys.exit(1 if problems else 0)` makes the script fail, so a git hook or a CI step can refuse the change that broke the promise.

The script prints the menu, then:

```text
roast-branch: hands-off, but Claude keeps Bash
```

and exits with status 1.

### The Real Thing: `skills/commit-one/SKILL.md` and the Three Readers

Every one of this repository's {skillCount} skills carries `family`, across {familyCount} families; {glyphCount} carry `glyph` and {spinnerCount} carry `goblin-spinner`. `commit-one` has all three, and each has its own reader.

`skills/commit-one/SKILL.md`:

```markdown
---
name: "Commit: One"
description: "Generate a commit message. If nothing staged, stage all changes."
...
model: sonnet # was haiku: auto mode skips haiku and keeps the session model, which is sometimes Fable here; sonnet pins it
effort: low
metadata:
  glyph: ᛊ
  family: commit
  goblin-spinner: writing the message|staging|committing
...
---
```

`library/scripts/skill-lint.py`:

```python
"""skill-lint.py: checks a skill's frontmatter against the metadata convention.

The convention (clod-config-skill_conventions) says `metadata.glyph` mirrors
the `model:` field, rune for tier, and is omitted when `model` is omitted:

	ᚺ haiku · ᛊ sonnet · ᛟ opus · ᚠ fable

Nothing enforced that, and a skill drifted (sonnet with Haiku's rune) until
goblin-jester happened to read the field. This script is the gate: it reads
the frontmatter as text, stdlib only, and reports every skill whose glyph
disagrees with its model, carries a glyph without a model, or pins a model
without a glyph.
...
"""
...
	if glyph != expected:
		have = TIER_FOR_RUNE.get(glyph)
		said = f"{glyph} ({have})" if have else f"{glyph} (not a tier rune)"
		return [f"glyph {said} does not mirror model {model} (expected {expected})"]
```

`marketplace/goblin-jester/hooks/goblin.ts`:

```ts
export const PROPS: Record<string, string> = {
	...
	commit: '[⇓]', // a commit going down
	...
	red: '[!]', // a red flag
	...
}
...
export const propFor = (family: string | null): string => (family !== null && Object.hasOwn(PROPS, family) ? (PROPS[family] ?? '') : '')
```

`marketplace/goblin-jester/hooks/frontmatter.ts`:

```ts
/**
 * A `|`-separated list, trimmed, empties dropped. Plugin authors write these
 * too, so each word loses its control and format characters (an escape would
 * reach the terminal; a bidi override would reorder the band) and its line
 * separators, and is cut to `SPINNER_WORD_MAX`.
 */
export const splitBar = (value: string | null): readonly string[] =>
	...
```

- **R.a** `glyph: ᛊ` repeats `model: sonnet` as a rune, as `hands-off` repeats `disallowed-tools`. On 30 September 2026, `project-tag_version` moved from haiku to sonnet and kept Haiku's rune, ᚺ, until goblin-jester read the field. The rune was fixed on 8 October, and `skill-lint.py` arrived the next day.
- **R.b** `family: commit` puts `[⇓]` in the goblin's hand while the skill runs. A family missing from `PROPS` gets an empty hand, so `roast` would need its own line before the goblin held anything.
- **R.c** `goblin-spinner` holds the words the spinner cycles through while the skill runs. Its reader strips control characters and cuts each word to `SPINNER_WORD_MAX`, because a plugin's author writes these too and a stray escape would reach your terminal.

### Try it: mark four keys

Before adding a key, ask three questions of it. Could it be worked out from the file? Does anything you run read it? Would a wrong value show? `hands-off` fails the first, and until step 4 it failed the third. Mark these four the same way, then pick one and teach `roast-menu.py` to read it:

- `exercised`: whether anyone has run the skill end to end
- `reads` and `writes`: the files the skill depends on
- `surface`: where its output lands, such as the terminal or GitHub
- `status`: `stable`, `provisional` or `retired`

**Answer.**

| Key | Worked out from the file? | Read by something you run? | A wrong value shows? |
|---|---|---|---|
| `exercised` | No | Once you write the reader | No: nothing re-runs the skill to check |
| `reads`, `writes` | Partly: the paths are in the body | Once you write the reader | Yes, if the reader checks each path exists |
| `surface` | Partly: `gh` in `allowed-tools` points at GitHub | Once you write the reader | Only if something compares it with `allowed-tools` |
| `status` | No | Once you write the reader | Yes for `retired`, the first time a menu hides a roast you wanted |

`status` is the easiest to read. In `roast-menu.py`, skip retired roasts straight after the family check:

```python
	if field(block, "status") == "retired":
		continue
```

---

## Open Questions

1. **NotebookEdit under `disallowed-tools`.** Test E showed Bash, Edit and Write absent from Claude's tools. NotebookEdit stayed in the deferred-tools list by name, and whether Claude could load and call it was not tested. The copy claims only what the docs say the field does.
2. **Which skills the counts cover.** The draft counts every `SKILL.md` in the repository, plugin skills included (85 on main on 2026-11-20). `skills/` alone holds 60. The build counts whatever the branch holds after the rebase.
3. **The Real Thing excerpts come from main.** The branch is behind main; the excerpts are read from `origin/main` at `55a37e8` and are re-read after the rebase.
4. **The drift R.a cites.** Settled from history: `4efab22` (2026-09-30) moved `project-tag_version` to `model: sonnet` and left `glyph: ᚺ`; `124d975` (2026-10-08) fixed the rune; the `95d248f` message names the skill and says the goblin read the field.

## Sources

| Claim | Source | Checked |
|---|---|---|
| `metadata` is a free-form map for your own tooling; Claude Code doesn't act on it, drops a non-map value; don't reuse field names such as `paths` | https://code.claude.com/docs/en/skills (frontmatter reference, `metadata` row) | 2026-11-20 |
| The skill listing carries `description` and `when_to_use` | same page, `description` and `when_to_use` rows | 2026-11-20 |
| An invoked skill reaches Claude as its body, without the frontmatter | the live-claims session transcript, Claude Code 2.1.329 (need #52) | 2026-11-20 |
| `` !`command` `` runs before Claude reads the skill and its output replaces the line; outside auto mode an unapproved command aborts the skill; `allowed-tools` pre-approves it | same page, "Inject dynamic context" and "Permission checks on injected commands" | 2026-11-20 |
| `disallowed-tools` removes tools until the next message | same page, `disallowed-tools` row | 2026-11-20 |
| The injected command runs with Bash in `disallowed-tools` | test E, Claude Code 2.1.329 (need #54) | 2026-11-20 |
| Python's standard library has no YAML parser; `skill-lint.py` reads keys as text | `skill-lint.py` docstring ("stdlib only") | 2026-11-20 |
| The menu output and exit status | `site/design/content/metadata-specimen/step4`, run with `python3 -I scripts/roast-menu.py` | 2026-11-20 |
| `project-tag_version` drifted 2026-09-30, fixed 2026-10-08; `skill-lint.py` arrived 2026-10-09 | commits `4efab22`, `124d975`, `95d248f` | 2026-11-20 |
| goblin-jester reads `family` for the prop and `goblin-spinner` for the spinner | `marketplace/goblin-jester/hooks/register.tsx` (`skill.prompt` handler), `goblin.ts`, `frontmatter.ts` on `origin/main` | 2026-11-20 |
