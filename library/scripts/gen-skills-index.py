#!/usr/bin/env python3
"""gen-skills-index.py: regenerates skills/README.md from skill frontmatter.

Reads every skills/*/SKILL.md, classifies each by its invocation shape, and
writes the three-table index (Command Skills / Model-Invocable Skills / Role
Skills). The index carries a "regenerate from frontmatter; do not hand-edit"
banner precisely so this script is the single source of truth for it;
running it after any frontmatter change keeps the counts and descriptions
honest instead of letting them drift, the way they drifted before this sweep.

Also rewrites the marker-delimited counts block in the root README.md's
"What's In Here" table (skills/agents/hooks counts), so that table's claim
that its counts are generated is actually true, rather than the hand-
maintained numbers that caused the original drift this script exists to
prevent.

usage: gen-skills-index.py [--check]
	--check   exit 1 if skills/README.md or README.md would change, without
	          writing either (for CI / pre-commit use)
"""
import sys
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"
INDEX_PATH = SKILLS_DIR / "README.md"
ROOT_README_PATH = REPO_ROOT / "README.md"
AGENTS_DIR = REPO_ROOT / "agents"
GLOBAL_HOOKS_DIR = REPO_ROOT / "hooks"
PROJECT_HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"

COUNTS_START = "<!-- gen-skills-index: counts start (do not hand-edit; run gen-skills-index.py) -->"
COUNTS_END = "<!-- gen-skills-index: counts end -->"

TIER_ROWS = [
	("ᚺ", "Haiku (fast)"),
	("ᛊ", "Sonnet (balanced)"),
	("ᛟ", "Opus (thorough)"),
	("ᚠ", "Fable (frontier)"),
]

DESC_MAX = 100  # matches the truncation width already in use in skills/README.md


def read_frontmatter(path: Path) -> dict:
	text = path.read_text()
	m = re.match(r"^---\n(.*?\n)---\n", text, re.DOTALL)
	if not m:
		raise ValueError(f"{path}: no frontmatter block found")
	data = yaml.safe_load(m.group(1))
	return data or {}


def strip_runic(description: str) -> tuple[str, str | None]:
	"""Split a "{{ glyph }} rest" description into (rest, model_from_glyph)."""
	m = re.match(r"^\{\{\s*(𝚫𝚫𝚫|ƔƔƔ|𝛀𝛀𝛀)\s*\}\}\s*(.*)$", description, re.DOTALL)
	if not m:
		return description, None
	glyph, rest = m.group(1), m.group(2)
	model = {"𝚫𝚫𝚫": "haiku", "ƔƔƔ": "sonnet", "𝛀𝛀𝛀": "opus"}[glyph]
	return rest, model


def truncate(text: str, width: int = DESC_MAX) -> str:
	text = " ".join(text.split())  # collapse embedded newlines/whitespace
	if len(text) <= width:
		return text
	return text[:width].rstrip() + "…"


def classify(name: str, fm: dict) -> str:
	"""Return one of "command", "model-invocable", "role"."""
	if fm.get("user-invocable") is False:
		return "role"
	if fm.get("disable-model-invocation") is True:
		return "command"
	# disable-model-invocation: false, or the flag is absent entirely
	# (e.g. scheme:create-interview); both mean "the model can invoke it".
	return "model-invocable"


def _iter_skill_dirs():
	"""Yield (skill_dir, label) for every skill under skills/.

	A plain skill is `skills/<name>/SKILL.md`, labelled `<name>`. A folder
	holding `.claude-plugin/plugin.json` is a plugin loaded as `<name>@skills-dir`;
	its skills live one level down in `<name>/skills/<skill>/SKILL.md` and are
	labelled `<name>:<skill>`, which is how Claude Code namespaces them.
	"""
	for entry in sorted(SKILLS_DIR.iterdir()):
		if (entry / "SKILL.md").is_file():
			yield entry, entry.name
			continue
		if not (entry / ".claude-plugin" / "plugin.json").is_file():
			continue
		plugin_skills = entry / "skills"
		if not plugin_skills.is_dir():
			continue
		for sub in sorted(plugin_skills.iterdir()):
			if (sub / "SKILL.md").is_file():
				yield sub, f"{entry.name}:{sub.name}"


def main() -> int:
	check_only = "--check" in sys.argv

	rows = []
	for skill_dir, label in _iter_skill_dirs():
		fm = read_frontmatter(skill_dir / "SKILL.md")
		raw_desc = (fm.get("description") or "").strip()
		desc, glyph_model = strip_runic(raw_desc)
		model = fm.get("model") or glyph_model or ""
		glyph = (fm.get("metadata") or {}).get("glyph", "")
		rows.append(
			{
				"dir": label,
				"name": fm.get("name", label),
				"model": f"{glyph} {model}".strip(),
				"description": desc,
				"when_to_use": (fm.get("when_to_use") or "").strip(),
				"kind": classify(label, fm),
			}
		)

	if not rows:
		print("gen-skills-index.py: no skills found; refusing to write an empty index", file=sys.stderr)
		return 1

	command_rows = [r for r in rows if r["kind"] == "command"]
	invocable_rows = [r for r in rows if r["kind"] == "model-invocable"]
	role_rows = [r for r in rows if r["kind"] == "role"]

	lines = []
	lines.append("# Skills")
	lines.append("")
	lines.append(
		"Slash commands and knowledge skills for Claude Code. Regenerate this index "
		"from frontmatter when skills change; do not hand-edit rows."
	)
	lines.append("")
	lines.append("Run `python3 ~/.claude/library/scripts/gen-skills-index.py` after adding, "
		"renaming, or re-describing a skill.")
	lines.append("")
	lines.append("| Tier glyph | Model |")
	lines.append("|------|-------|")
	for glyph, label in TIER_ROWS:
		lines.append(f"| `{glyph}` | {label} |")
	lines.append("")
	lines.append("---")
	lines.append("")

	lines.append("## Command Skills")
	lines.append("")
	lines.append("User-invocable slash commands (`disable-model-invocation: true`).")
	lines.append("")
	lines.append("| Command | Model | Description |")
	lines.append("|---------|-------|-------------|")
	for r in command_rows:
		lines.append(f"| `/{r['dir']}` | {r['model']} | {truncate(r['description'])} |")
	lines.append("")
	lines.append("---")
	lines.append("")

	lines.append("## Model-Invocable Skills")
	lines.append("")
	lines.append("Claude can load these automatically when relevant.")
	lines.append("")
	lines.append("| Skill | Model | Description |")
	lines.append("|-------|-------|-------------|")
	for r in invocable_rows:
		lines.append(f"| `/{r['dir']}` | {r['model']} | {truncate(r['description'])} |")
	lines.append("")
	lines.append("---")
	lines.append("")

	lines.append("## Role Skills")
	lines.append("")
	lines.append("Ambient knowledge roles (`user-invocable: false`), loaded by Claude when relevant.")
	lines.append("")
	lines.append("| Skill | Description | When to use |")
	lines.append("|-------|-------------|-------------|")
	for r in role_rows:
		lines.append(
			f"| `{r['dir']}` | {truncate(r['description'])} | {truncate(r['when_to_use'], 120)} |"
		)
	lines.append("")

	new_content = "\n".join(lines).rstrip() + "\n"

	root_readme_result = _sync_root_readme_counts(
		len(command_rows), len(invocable_rows), len(role_rows), check_only
	)
	if root_readme_result != 0:
		return root_readme_result

	if check_only:
		old_content = INDEX_PATH.read_text() if INDEX_PATH.exists() else ""
		if old_content != new_content:
			print("skills/README.md is stale; run gen-skills-index.py to regenerate.", file=sys.stderr)
			return 1
		print("skills/README.md and README.md counts are up to date.")
		return 0

	INDEX_PATH.write_text(new_content)
	print(
		f"Wrote {INDEX_PATH.relative_to(REPO_ROOT)}: "
		f"{len(command_rows)} command, {len(invocable_rows)} model-invocable, "
		f"{len(role_rows)} role skills."
	)
	return 0


def _sync_root_readme_counts(n_command: int, n_invocable: int, n_role: int, check_only: bool) -> int:
	"""Rewrite the marker-delimited counts table in the root README.md.

	Only the block between COUNTS_START/COUNTS_END is touched; everything
	else in README.md is hand-authored prose this script must never rewrite.
	Agents/hooks are counted here too (by directory, not frontmatter), so the
	whole "What's In Here" table is generated rather than hand-maintained,
	which is what caused the original drift this script exists to prevent.
	"""
	n_agents = len(list(AGENTS_DIR.glob("*.md"))) if AGENTS_DIR.is_dir() else 0
	# hooks/*.sh only: hooks/pre-commit is a git dispatcher, not a Claude Code
	# hook (see docs/reference/hooks.md), and must not be counted here.
	n_global_hooks = len(list(GLOBAL_HOOKS_DIR.glob("*.sh"))) if GLOBAL_HOOKS_DIR.is_dir() else 0
	n_project_hooks = len(list(PROJECT_HOOKS_DIR.glob("*.sh"))) if PROJECT_HOOKS_DIR.is_dir() else 0

	block = "\n".join([
		COUNTS_START,
		"| Component     | Count | What it does |",
		"|----------------|-------|--------------|",
		f"| **Skills (command)** | {n_command} | Slash commands you invoke (e.g. `/commit-one`) |",
		f"| **Skills (role)**    | {n_role} | Ambient knowledge that loads automatically when relevant |",
		f"| **Skills (model-invocable command)** | {n_invocable} | Command skills the model can also self-invoke |",
		f"| **Agents**     | {n_agents} | Autonomous sub-processes for multi-step work |",
		f"| **Hooks**      | {n_global_hooks} global + {n_project_hooks} project-level | Scripts triggered by git and session events |",
		COUNTS_END,
	])

	if not ROOT_README_PATH.exists():
		print(f"gen-skills-index.py: {ROOT_README_PATH} not found; skipping root README sync",
		      file=sys.stderr)
		return 0
	original = ROOT_README_PATH.read_text()
	pattern = re.compile(
		re.escape(COUNTS_START) + r".*?" + re.escape(COUNTS_END), re.DOTALL
	)
	if not pattern.search(original):
		print(f"gen-skills-index.py: no counts markers found in {ROOT_README_PATH}; "
		      "add COUNTS_START/COUNTS_END around the 'What's In Here' table to enable sync",
		      file=sys.stderr)
		return 0
	updated = pattern.sub(block, original, count=1)

	if check_only:
		if updated != original:
			print("README.md counts block is stale; run gen-skills-index.py to regenerate.",
			      file=sys.stderr)
			return 1
		return 0

	if updated != original:
		ROOT_README_PATH.write_text(updated)
		print(f"Wrote {ROOT_README_PATH.relative_to(REPO_ROOT)}: "
		      f"{n_command} command, {n_role} role, {n_invocable} model-invocable skills, "
		      f"{n_agents} agents, {n_global_hooks} global + {n_project_hooks} project hooks.")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
