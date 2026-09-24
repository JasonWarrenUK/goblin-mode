#!/usr/bin/env python3
"""build-roadmap-plugin.py: assembles the shareable `roadmap` plugin.

The roadmap skills live in skills/* and library/* as the source of truth for
this config. Teammates on other projects get them as a Claude Code plugin
instead, served from this repo's marketplace (.claude-plugin/marketplace.json).
This script generates that plugin under marketplace/roadmap/ from the live sources,
rewriting every ~/.claude path to ${CLAUDE_PLUGIN_ROOT} and every skill
cross-reference to its namespaced `roadmap:<name>` form. Never hand-edit
marketplace/roadmap/: edit the source, then rerun this.

usage: build-roadmap-plugin.py [--check]
	--check   exit 1 if marketplace/roadmap/ would change, without writing (for CI /
	          pre-commit use)
"""
from __future__ import annotations

import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "marketplace" / "roadmap"
PLUGIN_NAME = "roadmap"
# copied verbatim: edit the layout there, never in marketplace/roadmap/
README_SOURCE = REPO_ROOT / "library" / "sources" / "plugins" / "roadmap" / "readme.md"

# source skill dir -> plugin skill dir (invoked as roadmap:<dir>)
SKILLS = {
	"roadmap-create": "create",
	"roadmap-create-interview": "create-interview",
	"roadmap-migrate": "migrate",
	"roadmap-update-tasks": "update-tasks",
	"roadmap-update-devs": "update-devs",
	"roadmap-maintain": "maintain",
	"roadmap-review": "review",
	"artefact-roadmap": "dashboard",
	"next-task-suggest": "next-suggest",
	"next-task-group": "next-group",
}

# published path -> source path, both relative to their roots
FILES = {
	"scripts/roadmap.py": "library/scripts/roadmap.py",
	"scripts/_roadmap_core.py": "library/scripts/_roadmap_core.py",
	"templates/roadmap-artefact.html": "library/templates/roadmap-artefact.html",
	"references/roadmap-conventions.md": "library/references/roadmap-conventions.md",
}

PLUGIN_JSON = """{
	"name": "roadmap",
	"description": "Roadmaps as a dependency graph: JSON source of truth, mechanical status recompute, projected task lists, Mermaid diagrams, an HTML dashboard and the interview, review and next-task skills that drive it.",
	"author": {
		"name": "Jason Warren"
	},
	"homepage": "https://github.com/JasonWarrenUK/goblin-mode",
	"keywords": ["roadmap", "planning", "dependency-graph"]
}
"""

HOOKS_JSON = """{
	"hooks": {
		"SessionStart": [
			{
				"hooks": [
					{
						"type": "command",
						"command": "sh \\"${CLAUDE_PLUGIN_ROOT}/scripts/roadmap-drift-check.sh\\""
					}
				]
			}
		]
	}
}
"""

# POSIX port of library/scripts/roadmap-drift-check.sh: teammates may not have zsh
DRIFT_CHECK = """#!/bin/sh
# SessionStart hook: one-line nudge when the cwd's roadmap has drifted.
# Silent unless a rich roadmap exists AND validate reports discrepancies.
root="${CLAUDE_PLUGIN_ROOT:-$(dirname "$0")/..}"
python3 "$root/scripts/roadmap.py" detect >/dev/null 2>&1 || exit 0
python3 "$root/scripts/roadmap.py" validate >/dev/null 2>&1 && exit 0
printf '%s\\n' "Roadmap drift: roadmap.py validate reports discrepancies; consider running /roadmap:maintain"
exit 0
"""

# Ordered (pattern, replacement) pairs applied to every text file.
PATH_REWRITES: list[tuple[str, str]] = [
	(r'"\$HOME"/\.claude/library/scripts/', '"${CLAUDE_PLUGIN_ROOT}"/scripts/'),
	(r"~/\.claude/library/(references|templates|scripts)/", r"${CLAUDE_PLUGIN_ROOT}/\1/"),
	(r"(?<![\w/.-])library/(references|templates|scripts)/", r"\1/"),
]

# Lines tied to the rest of Jason's config, removed or reworded for the plugin.
# Each (source-relative path, old, new) must match exactly once or the build fails.
DECOUPLINGS: list[tuple[str, str, str]] = [
	(
		"skills/next-task-suggest/SKILL.md",
		"# read-only suggestion; invocable so next-task-ship's Step 1 can call it and \"what should I work on?\" loads it",
		"# read-only suggestion; invocable so \"what should I work on?\" loads it",
	),
	(
		"skills/artefact-roadmap/SKILL.md",
		"- The template already follows `~/.claude/library/references/artefact-conventions.md` (theme-sourced palette",
		"- The template follows a fixed artefact contract (theme-sourced palette",
	),
	(
		"skills/roadmap-review/SKILL.md",
		"\n\nWhen the findings are substantial or worth sharing, also offer to render them visually: map them to `artefact-audit`'s JSON shape and run that skill in render-only mode. Decline gracefully if the terminal summary is all that's wanted.",
		"",
	),
	(
		"library/references/roadmap-conventions.md",
		"Pink is the primary accent (Jason's terminal gradient) and is never a status\ncolour.",
		"Pink is the primary accent and is never a status\ncolour.",
	),
	(
		"library/references/roadmap-conventions.md",
		"  recorded by `next-task-ship` at PR creation (worth setting by hand when\n  shipping outside that skill). It lets a later run detect that a `done`\n  dependency is still unmerged and stack a dependent branch on it instead of\n  branching from main (see `library/references/stacked-prs.md`). It is never",
		"  worth setting by hand when a task ships. It lets a later run detect that a\n  `done` dependency is still unmerged and stack a dependent branch on it\n  instead of branching from main. It is never",
	),
	(
		"library/references/roadmap-conventions.md",
		"| Ship the next task end-to-end | `next-task-ship` |\n",
		"",
	),
	(
		"library/scripts/_roadmap_core.py",
		"lives beside it in ~/.claude/library/scripts/.",
		"lives beside it in scripts/.",
	),
	(
		"library/references/roadmap-conventions.md",
		" If `~`\nis not expanded in your shell context, use `\"$HOME\"` (as above).",
		"",
	),
	(
		"library/scripts/_roadmap_core.py",
		"this module lives in ~/.claude/library, far from any project.)",
		"this module lives in the plugin, far from any project.)",
	),
	(
		"library/templates/roadmap-artefact.html",
		"control from library/references/artefact-conventions.md;",
		"control from the artefact conventions;",
	),
]


def skill_rewrites() -> list[tuple[str, str]]:
	# Longest names first so roadmap-create-interview never matches as roadmap-create
	names = sorted(SKILLS, key=len, reverse=True)
	return [
		(rf"(?<![\w.-]){re.escape(src)}(?![\w-])", f"{PLUGIN_NAME}:{SKILLS[src]}")
		for src in names
	]


def transform(text: str, source: str) -> str:
	for rel, old, new in DECOUPLINGS:
		if rel != source:
			continue
		count = text.count(old)
		if count != 1:
			sys.exit(f"build-roadmap-plugin: decoupling in {rel} matched {count} times, expected 1:\n  {old[:80]}")
		text = text.replace(old, new)
	for pattern, replacement in PATH_REWRITES + skill_rewrites():
		text = re.sub(pattern, replacement, text)
	return text


def build(out: Path) -> None:
	for src, dest in SKILLS.items():
		source = f"skills/{src}/SKILL.md"
		target = out / "skills" / dest / "SKILL.md"
		target.parent.mkdir(parents=True, exist_ok=True)
		target.write_text(transform((REPO_ROOT / source).read_text(), source))
	for dest, source in FILES.items():
		target = out / dest
		target.parent.mkdir(parents=True, exist_ok=True)
		target.write_text(transform((REPO_ROOT / source).read_text(), source))
	(out / ".claude-plugin").mkdir(parents=True, exist_ok=True)
	(out / ".claude-plugin" / "plugin.json").write_text(PLUGIN_JSON)
	(out / "hooks").mkdir(exist_ok=True)
	(out / "hooks" / "hooks.json").write_text(HOOKS_JSON)
	(out / "scripts" / "roadmap-drift-check.sh").write_text(DRIFT_CHECK)
	shutil.copyfile(README_SOURCE, out / "README.md")
	for script in (out / "scripts").iterdir():
		script.chmod(0o755)


def snapshot(root: Path) -> dict[str, bytes]:
	if not root.exists():
		return {}
	# __pycache__ appears whenever the scripts run; it is never part of the build
	return {
		str(p.relative_to(root)): p.read_bytes()
		for p in sorted(root.rglob("*"))
		if p.is_file() and "__pycache__" not in p.parts
	}


def main() -> None:
	check = "--check" in sys.argv[1:]
	with tempfile.TemporaryDirectory() as tmp:
		staged = Path(tmp) / "roadmap"
		build(staged)
		if snapshot(staged) == snapshot(OUT_DIR):
			print("marketplace/roadmap: up to date")
			return
		if check:
			sys.exit("marketplace/roadmap: stale; run library/scripts/build-roadmap-plugin.py")
		if OUT_DIR.exists():
			shutil.rmtree(OUT_DIR)
		shutil.copytree(staged, OUT_DIR)
		print("marketplace/roadmap: rebuilt")


if __name__ == "__main__":
	main()
