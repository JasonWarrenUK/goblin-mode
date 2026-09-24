#!/usr/bin/env python3
"""build-roadmap-plugin.py: assembles the shareable `roadmap` plugin.

The roadmap skills live in skills/* and library/* as the source of truth for
this config. Teammates on other projects get them as a Claude Code plugin
instead, served from this repo's marketplace (.claude-plugin/marketplace.json).
This script generates that plugin under marketplace/roadmap/ from the live sources,
rewriting every ~/.claude path to ${CLAUDE_PLUGIN_ROOT} and every skill
cross-reference to its namespaced `roadmap:<name>` form. Never hand-edit
marketplace/roadmap/: edit the source, then rerun this.

Every build is validated before anything is written: missing sources, plugin
paths that point at files the plugin doesn't ship, leftover ~/.claude paths
and skill names from this config that the plugin can't resolve all fail the
build with one line per problem.

usage: build-roadmap-plugin.py [--check | --sources]
	--check     exit 1 if marketplace/roadmap/ would change, without writing
	--sources   print every source path the build reads, one per line (the
	            pre-commit hook uses this to decide whether to rebuild)
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
README_SOURCE = "library/sources/plugins/roadmap/readme.md"

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

# ${CLAUDE_PLUGIN_ROOT} only resolves in skill content and hook commands; a
# reference or template is read raw, so it gets a placeholder a reader fills in
# from the calling skill's resolved CLI line instead
UNRESOLVED_ROOT = (r'"?\$\{CLAUDE_PLUGIN_ROOT\}"?', "<plugin-root>")

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
	(
		"library/references/roadmap-conventions.md",
		"(single CLI) and `_roadmap_core.py`.",
		"(single CLI) and `_roadmap_core.py`.\n`<plugin-root>` is the plugin's install directory; every skill's CLI line\ngives it resolved.",
	),
]


class BuildError(Exception):
	"""One or more problems that make the plugin unsafe to publish."""

	def __init__(self, problems: list[str]) -> None:
		super().__init__("\n".join(problems))
		self.problems = problems


def skill_rewrites() -> list[tuple[str, str]]:
	# Longest names first so roadmap-create-interview never matches as roadmap-create
	names = sorted(SKILLS, key=len, reverse=True)
	return [
		(rf"(?<![\w.-]){re.escape(src)}(?![\w-]|\.\w)", f"{PLUGIN_NAME}:{SKILLS[src]}")
		for src in names
	]


def transform(text: str, source: str) -> str:
	for rel, old, new in DECOUPLINGS:
		if rel != source:
			continue
		count = text.count(old)
		if count != 1:
			raise BuildError([f"{rel}: decoupling matched {count} times, expected 1: {old.strip()[:70]!r}"])
		text = text.replace(old, new)
	for pattern, replacement in PATH_REWRITES + skill_rewrites():
		text = re.sub(pattern, replacement, text)
	if not source.startswith("skills/"):
		text = re.sub(*UNRESOLVED_ROOT, text)
	return text


def source_paths() -> list[str]:
	"""Every repo-relative file the build reads, including this script."""
	return [
		*(f"skills/{src}/SKILL.md" for src in SKILLS),
		*FILES.values(),
		README_SOURCE,
		"library/scripts/build-roadmap-plugin.py",
	]


def check_sources(root: Path) -> None:
	sources = source_paths()
	problems = [
		f"missing source: {rel} (renamed or moved? update SKILLS/FILES/README_SOURCE in this script)"
		for rel in sources
		if not (root / rel).is_file()
	]
	problems += [
		f"decoupling targets {rel}, which the build never reads (update DECOUPLINGS)"
		for rel in dict.fromkeys(rel for rel, _, _ in DECOUPLINGS)
		if rel not in sources
	]
	if problems:
		raise BuildError(problems)


# A plugin-root reference with or without quotes around the variable, or the
# placeholder non-skill files get: ${CLAUDE_PLUGIN_ROOT}/scripts/x.py,
# "${CLAUDE_PLUGIN_ROOT}"/scripts/x.py or <plugin-root>/scripts/x.py
PLUGIN_REF = re.compile(r'(?:\$\{CLAUDE_PLUGIN_ROOT\}"?|<plugin-root>)/([\w./-]+[\w])')
# The exact form only: the drift check's ${CLAUDE_PLUGIN_ROOT:-...} is a real
# environment variable in the hook process
ROOT_PLACEHOLDER = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}")
# Plugin directories whose content Claude Code substitutes the placeholder in
RESOLVING_DIRS = {"skills", "hooks"}
HOME_REF = re.compile(r'(~|"?\$HOME"?|\$\{HOME\})/\.claude\b')


def validate(root: Path, out: Path) -> None:
	"""Fail if the built plugin refers to anything a teammate won't have."""
	skill_names = sorted(
		(d.name for d in (root / "skills").iterdir() if (d / "SKILL.md").is_file()),
		key=len,
		reverse=True,
	)
	# A skill of this config named in plugin text, not already namespaced (roadmap:x)
	# and not part of a longer word, path or file name (roadmap-conventions.md)
	foreign_skill = (
		re.compile(r"(?<![\w.:/-])(" + "|".join(map(re.escape, skill_names)) + r")(?![\w-]|\.\w)")
		if skill_names
		else None
	)
	problems: list[str] = []
	for path in sorted(out.rglob("*")):
		if not path.is_file() or path.suffix not in {".md", ".py", ".sh", ".json", ".html"}:
			continue
		rel = path.relative_to(out)
		for lineno, line in enumerate(path.read_text().splitlines(), start=1):
			where = f"{rel}:{lineno}"
			for match in PLUGIN_REF.finditer(line):
				if not (out / match.group(1)).exists():
					problems.append(f"{where}: {match.group(0)} is not shipped in the plugin (add it to FILES)")
			if rel.parts[0] not in RESOLVING_DIRS and ROOT_PLACEHOLDER.search(line):
				problems.append(f"{where}: ${{CLAUDE_PLUGIN_ROOT}} never resolves outside skills/ and hooks/ (use <plugin-root>)")
			if HOME_REF.search(line):
				problems.append(f"{where}: path into ~/.claude survives the build (add a PATH_REWRITES rule or a decoupling)")
			if foreign_skill:
				for match in foreign_skill.finditer(line):
					problems.append(f"{where}: skill {match.group(1)!r} is not in the plugin (add it to SKILLS or decouple the reference)")
	if problems:
		raise BuildError(problems)


def build(root: Path, out: Path) -> None:
	check_sources(root)
	for src, dest in SKILLS.items():
		source = f"skills/{src}/SKILL.md"
		target = out / "skills" / dest / "SKILL.md"
		target.parent.mkdir(parents=True, exist_ok=True)
		target.write_text(transform((root / source).read_text(), source))
	for dest, source in FILES.items():
		target = out / dest
		target.parent.mkdir(parents=True, exist_ok=True)
		target.write_text(transform((root / source).read_text(), source))
	(out / ".claude-plugin").mkdir(parents=True, exist_ok=True)
	(out / ".claude-plugin" / "plugin.json").write_text(PLUGIN_JSON)
	(out / "hooks").mkdir(exist_ok=True)
	(out / "hooks" / "hooks.json").write_text(HOOKS_JSON)
	(out / "scripts" / "roadmap-drift-check.sh").write_text(DRIFT_CHECK)
	shutil.copyfile(root / README_SOURCE, out / "README.md")
	for script in (out / "scripts").iterdir():
		script.chmod(0o755)
	validate(root, out)


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
	args = sys.argv[1:]
	if "--sources" in args:
		print("\n".join(source_paths()))
		return
	check = "--check" in args
	with tempfile.TemporaryDirectory() as tmp:
		staged = Path(tmp) / "roadmap"
		try:
			build(REPO_ROOT, staged)
		except BuildError as error:
			print(f"build-roadmap-plugin: {len(error.problems)} problem(s), nothing written:", file=sys.stderr)
			for problem in error.problems:
				print(f"  {problem}", file=sys.stderr)
			sys.exit(1)
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
