#!/usr/bin/env python3
"""Builds site/src/lib/content/metadata.ts from the approved Metadata draft.

The step 4 files are read from site/design/content/metadata-specimen/step4,
where the script was run for real; steps 1 to 3 are derived from them by the
edits the draft describes. Prose is copied from metadata-draft.md by hand into
the tables below, so a copy change is made in both. Run from the repository
root:

    python3 -I site/design/content/tools/gen-metadata.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SPECIMEN = ROOT / "site/design/content/metadata-specimen/step4"
OUT = ROOT / "site/src/lib/content/metadata.ts"

COMMIT = ".claude/skills/roast-commit/SKILL.md"
BRANCH = ".claude/skills/roast-branch/SKILL.md"
MENU = "scripts/roast-menu.py"


def read(rel: str) -> str:
	return (SPECIMEN / rel).read_text().rstrip("\n")


def without(text: str, line: str) -> str:
	lines = text.split("\n")
	assert line in lines, line
	lines.remove(line)
	return "\n".join(lines)


def swap(text: str, old: str, new: str) -> str:
	assert text.count(old) == 1, old
	return text.replace(old, new)


def code(html: str) -> str:
	"""Markdown backticks to <code>, escaping the code's own angle brackets and ampersands."""
	def one(inner: str) -> str:
		inner = inner.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("`", "&#96;")
		return f"<code>{inner}</code>"
	html = re.sub(r"`` (.+?) ``", lambda m: one(m.group(1)), html)
	return re.sub(r"`([^`]+)`", lambda m: one(m.group(1)), html)


HANDS_OFF = "  hands-off: true"
FULL_LIST = "disallowed-tools: [Agent, Bash, Edit, Write, NotebookEdit]"
DRIFTED_LIST = "disallowed-tools: [Agent, Edit, Write, NotebookEdit]"

commit4 = read(COMMIT)
branch4 = read(BRANCH)
menu4 = read(MENU)

commit3 = commit4
branch3 = swap(branch4, DRIFTED_LIST, FULL_LIST)
commit1 = without(commit3, HANDS_OFF)
branch2 = without(branch3, HANDS_OFF)
menu2 = menu4
for line in ["import sys", 'REMOVED = {"Agent", "Bash", "Edit", "Write", "NotebookEdit"}',
		'\tremoved = set(re.findall(r"\\w+", field(block, "disallowed-tools")))',
		'\tif field(block, "hands-off") == "true" and not REMOVED <= removed:',
		"\t\tproblems.append(f\"{name}: hands-off, but Claude keeps {', '.join(sorted(REMOVED - removed))}\")",
		"for problem in problems:", "\tprint(problem, file=sys.stderr)", "sys.exit(1 if problems else 0)"]:
	menu2 = without(menu2, line)
menu2 = swap(menu2, "menu, problems = [], []", "menu = []")


def line_of(text: str, needle: str) -> int:
	hits = [n for n, line in enumerate(text.split("\n"), 1) if needle in line]
	assert len(hits) == 1, (needle, hits)
	return hits[0]


def every(text: str) -> list[int]:
	return list(range(1, len(text.split("\n")) + 1))


MENU_OUT = (
	"mild       /roast-commit   Roast the last commit message.\n"
	"scorching  /roast-branch   Roast every commit on this branch, in order."
)


def file(path: str, lang: str, text: str, **extra: object) -> dict:
	return {"path": path, "lang": lang, "text": text, **extra}


def callout(label: str, path: str, text: str, needle: str, html: str, to: str | None = None) -> dict:
	out = {"label": label, "file": path, "line": line_of(text, needle), "html": code(html)}
	if to is not None:
		out["to"] = line_of(text, to)
	return out


steps = [
	{
		"id": "1",
		"title": "Define a Key",
		"prose": [code("Start with a skill that roasts your last commit message. Its frontmatter fetches the commit and takes away Claude's tools for running commands, editing files and handing the job to a helper agent; the `metadata:` block at the bottom is the new part. Write any keys you like under it, with any values. Claude doesn't see them either. The skill listing carries only `description` and `when_to_use`, and a skill you run reaches Claude as its body alone.")],
		"files": [file(COMMIT, "markdown", commit1, added=every(commit1))],
		"callouts": [
			callout("1a", COMMIT, commit1, "!`git log -1", "`` !`git log -1 --format='%h %s%n%n%b'` `` runs before Claude reads the skill, and its output takes the line's place, so Claude reads the commit itself. `allowed-tools` approves `git log` for it; without that approval the skill stops before it starts."),
			callout("1b", COMMIT, commit1, "disallowed-tools:", "`disallowed-tools` takes these five away from Claude until your next message. Tools from MCP servers you've connected stay unless you list them too. The injected `git log` still runs with Bash on the list."),
			callout("1c", COMMIT, commit1, "metadata:", "`metadata:` holds keys of your own. Claude Code doesn't act on its contents and drops a value that isn't a map, so every key sits indented under it. Don't reuse a frontmatter field's name, such as `paths`, as a key."),
			callout("1d", COMMIT, commit1, "family: roast", "`family: roast` groups this skill with the others you'll write; for now, no script reads it."),
			callout("1e", COMMIT, commit1, "heat: mild", "`heat: mild` is invented, key and value both. Nothing in Claude Code knows what a heat is, or that `mild` comes before `scorching`."),
		],
	},
	{
		"id": "2",
		"title": "Read It",
		"prose": [code("Nothing reads `heat` yet, so it does nothing. Add a second roast at the other end of the scale, then a script at `scripts/roast-menu.py` that lists every skill in the roast family, mildest first. Run it from the project's root with `python3 scripts/roast-menu.py`.")],
		"files": [
			file(BRANCH, "markdown", branch2, added=every(branch2)),
			file(MENU, "python", menu2, added=every(menu2)),
		],
		"callouts": [
			callout("2a", BRANCH, branch2, "main..HEAD", "`main..HEAD` is every commit on this branch since it left main, and `--reverse` puts them oldest first, so Claude reads the branch in the order it happened."),
			callout("2b", BRANCH, branch2, "model: opus", "`model: opus` at `effort: high`, because reading a whole branch as one story takes more than a single message does.", to="effort: high"),
			callout("2c", MENU, menu2, "HEAT = [", "`HEAT` holds the order. YAML has no idea that `mild` comes before `scorching`, so the script decides."),
			callout("2d", MENU, menu2, "def field(", "`field()` reads the frontmatter as text with one regular expression. Python's standard library has no YAML parser, and `skill-lint.py` in this repository reads its keys the same way.", to="return m.group(1)"),
			callout("2e", MENU, menu2, "rank = HEAT.index", "A heat the script doesn't know sorts last, and a missing one prints as `?`. Nothing checked the value when you wrote it, so the script is the only place that decides what a typo means.", to="menu.append("),
		],
		"output": {"label": "python3 scripts/roast-menu.py", "text": MENU_OUT},
	},
	{
		"id": "3",
		"title": "Add a Key That Repeats Another Field",
		"prose": [code("A script that wants to know whether a roast is safe to run on someone else's branch would rather read one word than a list of tools. Add `hands-off: true` to both roasts. It says what their `disallowed-tools` line already enforces. The menu prints the same as before, because nothing reads the new key yet.")],
		"files": [
			file(COMMIT, "markdown", commit3, added=[line_of(commit3, "hands-off")]),
			file(BRANCH, "markdown", branch3, added=[line_of(branch3, "hands-off")]),
		],
		"callouts": [
			callout("3a", COMMIT, commit3, "hands-off: true", "`hands-off: true` repeats what `disallowed-tools` enforces. Claude Code acts on the list and ignores the key."),
			callout("3b", COMMIT, commit3, "disallowed-tools:", "Change one and the other goes on saying what it said; Claude Code never compares them."),
		],
		"output": {"label": "python3 scripts/roast-menu.py", "text": MENU_OUT},
	},
	{
		"id": "4",
		"title": "Check It",
		"prose": [code("noor wants `roast-branch` to run `git blame` on the worst commit, takes Bash off its `disallowed-tools` list and leaves `hands-off: true` where it was. Claude has Bash again during the roast, and the frontmatter still says hands off. Teach the script what `hands-off` means, and make it fail when a skill claims it without taking those tools away.")],
		"files": [
			file(BRANCH, "markdown", branch4, added=[line_of(branch4, "disallowed-tools:")], removed=[{"before": line_of(branch4, "disallowed-tools:"), "text": FULL_LIST}]),
			file(MENU, "python", menu4,
				added=[line_of(menu4, n) for n in ["import sys", "REMOVED = {", "menu, problems", "removed = set(", 'field(block, "hands-off")', "problems.append(", "for problem in problems", "file=sys.stderr", "sys.exit("]],
				fold=[[1, line_of(menu4, "import re")], [line_of(menu4, "REMOVED = {") + 1, line_of(menu4, "menu, problems") - 1]]),
		],
		"callouts": [
			callout("4a", BRANCH, branch4, "disallowed-tools:", "`disallowed-tools` has lost Bash; `hands-off: true` is still there."),
			callout("4b", MENU, menu4, "REMOVED = {", "`REMOVED` writes down what `hands-off` means, once, in the only place that reads it."),
			callout("4c", MENU, menu4, 'field(block, "hands-off")', "`REMOVED <= removed` holds when every tool in `REMOVED` is also on the skill's list."),
			callout("4d", MENU, menu4, "sys.exit(", "`sys.exit(1 if problems else 0)` makes the script fail, so a git hook or a CI step can refuse the change that broke the promise."),
		],
		"output": {"label": "python3 scripts/roast-menu.py (exits with status 1)", "text": MENU_OUT + "\nroast-branch: hands-off, but Claude keeps Bash"},
	},
]

COMMIT_ONE = "\n".join([
	"---",
	'name: "Commit: One"',
	'description: "Generate a commit message. If nothing staged, stage all changes."',
	"...",
	"model: sonnet # was haiku: auto mode skips haiku and keeps the session model, which is sometimes Fable here; sonnet pins it",
	"effort: low",
	"metadata:",
	"  glyph: ᛊ",
	"  family: commit",
	"  goblin-spinner: writing the message|staging|committing",
	"...",
	"---",
])
SKILL_LINT = "\n".join([
	'"""skill-lint.py: checks a skill\'s frontmatter against the metadata convention.',
	"",
	"The convention (clod-config-skill_conventions) says `metadata.glyph` mirrors",
	"the `model:` field, rune for tier, and is omitted when `model` is omitted:",
	"",
	"\tᚺ haiku · ᛊ sonnet · ᛟ opus · ᚠ fable",
	"",
	"Nothing enforced that, and a skill drifted (sonnet with Haiku's rune) until",
	"goblin-jester happened to read the field. This script is the gate: it reads",
	"the frontmatter as text, stdlib only, and reports every skill whose glyph",
	"disagrees with its model, carries a glyph without a model, or pins a model",
	"without a glyph.",
	"...",
	'"""',
	"...",
	"\tif glyph != expected:",
	"\t\thave = TIER_FOR_RUNE.get(glyph)",
	'\t\tsaid = f"{glyph} ({have})" if have else f"{glyph} (not a tier rune)"',
	'\t\treturn [f"glyph {said} does not mirror model {model} (expected {expected})"]',
])
GOBLIN = "\n".join([
	"export const PROPS: Record<string, string> = {",
	"\t...",
	"\tcommit: '[⇓]', // a commit going down",
	"\t...",
	"\tred: '[!]', // a red flag",
	"\t...",
	"}",
	"...",
	"export const propFor = (family: string | null): string => (family !== null && Object.hasOwn(PROPS, family) ? (PROPS[family] ?? '') : '')",
])
FRONTMATTER = "\n".join([
	"/**",
	" * A `|`-separated list, trimmed, empties dropped. Plugin authors write these",
	" * too, so each word loses its control and format characters (an escape would",
	" * reach the terminal; a bidi override would reorder the band) and its line",
	" * separators, and is cut to `SPINNER_WORD_MAX`.",
	" */",
	"export const splitBar = (value: string | null): readonly string[] =>",
	"\t...",
])
C1 = "skills/commit-one/SKILL.md"

real = {
	"name": "commit-one",
	"intro": code("Every one of this repository's {metadataSkills} skills carries `family`, across {metadataFamilies} families; {metadataGlyphs} carry `glyph` and {metadataSpinners} carry `goblin-spinner`. `commit-one` has all three, and each has its own reader."),
	"files": [
		file(C1, "markdown", COMMIT_ONE),
		file("library/scripts/skill-lint.py", "python", SKILL_LINT),
		file("marketplace/goblin-jester/hooks/goblin.ts", "ts", GOBLIN),
		file("marketplace/goblin-jester/hooks/frontmatter.ts", "ts", FRONTMATTER),
	],
	"callouts": [
		callout("R.a", C1, COMMIT_ONE, "glyph: ᛊ", "`glyph: ᛊ` repeats `model: sonnet` as a rune, as `hands-off` repeats `disallowed-tools`. On 30 September 2026, `project-tag_version` moved from haiku to sonnet and kept Haiku's rune, ᚺ, until goblin-jester read the field. The rune was fixed on 8 October, and `skill-lint.py` arrived the next day."),
		callout("R.b", C1, COMMIT_ONE, "family: commit", "`family: commit` puts `[⇓]` in the goblin's hand while the skill runs. A family missing from `PROPS` gets an empty hand, so `roast` would need its own line before the goblin held anything."),
		callout("R.c", C1, COMMIT_ONE, "goblin-spinner:", "`goblin-spinner` holds the words the spinner cycles through while the skill runs. Its reader strips control characters and cuts each word to `SPINNER_WORD_MAX`, because a plugin's author writes these too and a stray escape would reach your terminal."),
	],
}

exercise = {
	"title": "Try it: mark four keys",
	"prompt": [code(p) for p in [
		"Before adding a key, ask three questions of it. Could it be worked out from the file? Does anything you run read it? Would a wrong value show? `hands-off` fails the first, and until step 4 it failed the third. Mark these four the same way, then pick one and teach `roast-menu.py` to read it.",
		"`exercised`: whether anyone has run the skill end to end.",
		"`reads` and `writes`: the files the skill depends on.",
		"`surface`: where its output lands, such as the terminal or GitHub.",
		"`status`: `stable`, `provisional` or `retired`.",
	]],
	"answer": [
		{"table": {
			"head": ["Key", "Worked out from the file?", "Read by something you run?", "A wrong value shows?"],
			"rows": [[code(c) for c in row] for row in [
				["`exercised`", "No", "Once you write the reader", "No: nothing re-runs the skill to check"],
				["`reads`, `writes`", "Partly: the paths are in the body", "Once you write the reader", "Yes, if the reader checks each path exists"],
				["`surface`", "Partly: `gh` in `allowed-tools` points at GitHub", "Once you write the reader", "Only if something compares it with `allowed-tools`"],
				["`status`", "No", "Once you write the reader", "Yes for `retired`, the first time a menu hides a roast you wanted"],
			]],
		}},
		{"prose": code("`status` is the easiest to read. In `roast-menu.py`, skip retired roasts straight after the family check:")},
		{"code": '\tif field(block, "status") == "retired":\n\t\tcontinue', "lang": "python"},
	],
}

page = {
	"title": "Metadata Is Whatever I Say It Is",
	"intro": code("Claude Code reads a fixed list of frontmatter fields and leaves `metadata` to you. In this page, you'll give two skills keys of your own, write a script that reads them, then make the script catch the day one of those keys stops being true."),
	"steps": steps,
	"realThing": real,
	"exercise": exercise,
}

body = json.dumps(page, ensure_ascii=False, indent="\t")
OUT.write_text(
	"// Generated by site/design/content/tools/gen-metadata.py from the approved draft\n"
	"// (site/design/content/metadata-draft.md); edit the draft and the generator, then rerun.\n"
	"// Count placeholders in braces are filled from the build's facts on the page.\n\n"
	"import type { StagePage } from './tutorial.types.ts';\n\n"
	f"export const METADATA: StagePage = {body};\n"
)
print(f"wrote {OUT.relative_to(ROOT)}")
