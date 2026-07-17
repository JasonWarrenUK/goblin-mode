#!/usr/bin/env python3
"""gen-skills-index.py — regenerates skills/README.md from skill frontmatter.

Reads every skills/*/SKILL.md, classifies each by its invocation shape, and
writes the three-table index (Command Skills / Model-Invocable Skills / Role
Skills). The index carries a "regenerate from frontmatter; do not hand-edit"
banner precisely so this script is the single source of truth for it —
running it after any frontmatter change keeps the counts and descriptions
honest instead of letting them drift, the way they drifted before this sweep.

usage: gen-skills-index.py [--check]
	--check   exit 1 if skills/README.md would change, without writing it
	          (for CI / pre-commit use)
"""
import sys
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"
INDEX_PATH = SKILLS_DIR / "README.md"

TIER_ROWS = [
	("𝚫𝚫𝚫", "Haiku — fast"),
	("ƔƔƔ", "Sonnet — balanced"),
	("𝛀𝛀𝛀", "Opus — thorough"),
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
	# (e.g. roadmap-create-interview) — both mean "the model can invoke it".
	return "model-invocable"


def main() -> int:
	check_only = "--check" in sys.argv

	rows = []
	for skill_dir in sorted(SKILLS_DIR.iterdir()):
		skill_md = skill_dir / "SKILL.md"
		if not skill_md.is_file():
			continue
		fm = read_frontmatter(skill_md)
		raw_desc = (fm.get("description") or "").strip()
		desc, glyph_model = strip_runic(raw_desc)
		model = fm.get("model") or glyph_model or ""
		rows.append(
			{
				"dir": skill_dir.name,
				"name": fm.get("name", skill_dir.name),
				"model": model,
				"description": desc,
				"when_to_use": (fm.get("when_to_use") or "").strip(),
				"kind": classify(skill_dir.name, fm),
			}
		)

	if not rows:
		print("gen-skills-index.py: no skills found — refusing to write an empty index", file=sys.stderr)
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
	lines.append("Ambient knowledge roles (`role-*`), loaded by Claude when relevant.")
	lines.append("")
	lines.append("| Skill | Description | When to use |")
	lines.append("|-------|-------------|-------------|")
	for r in role_rows:
		lines.append(
			f"| `{r['dir']}` | {truncate(r['description'])} | {truncate(r['when_to_use'], 120)} |"
		)
	lines.append("")

	new_content = "\n".join(lines).rstrip() + "\n"

	if check_only:
		old_content = INDEX_PATH.read_text() if INDEX_PATH.exists() else ""
		if old_content != new_content:
			print("skills/README.md is stale — run gen-skills-index.py to regenerate.", file=sys.stderr)
			return 1
		print("skills/README.md is up to date.")
		return 0

	INDEX_PATH.write_text(new_content)
	print(
		f"Wrote {INDEX_PATH.relative_to(REPO_ROOT)} — "
		f"{len(command_rows)} command, {len(invocable_rows)} model-invocable, "
		f"{len(role_rows)} role skills."
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
