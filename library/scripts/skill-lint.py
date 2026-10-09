#!/usr/bin/env python3
"""skill-lint.py: checks a skill's frontmatter against the metadata convention.

The convention (clod-config-skill_conventions) says `metadata.glyph` mirrors
the `model:` field, rune for tier, and is omitted when `model` is omitted:

	ᚺ haiku · ᛊ sonnet · ᛟ opus · ᚠ fable

Nothing enforced that, and a skill drifted (sonnet with Haiku's rune) until
goblin-chrome happened to read the field. This script is the gate: it reads
the frontmatter as text, stdlib only, and reports every skill whose glyph
disagrees with its model, carries a glyph without a model, or pins a model
without a glyph.

usage: skill-lint.py [SKILL.md ...]
	With no arguments, lints every skills/*/SKILL.md under the repo root.
	Exit 1 when anything is reported, so a hook or CI step can gate on it.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"

RUNE_FOR_TIER = {"haiku": "ᚺ", "sonnet": "ᛊ", "opus": "ᛟ", "fable": "ᚠ"}
TIER_FOR_RUNE = {rune: tier for tier, rune in RUNE_FOR_TIER.items()}


def frontmatter_block(text: str) -> str | None:
	m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.DOTALL)
	return m.group(1) if m else None


def scalar(raw: str) -> str | None:
	"""A plain or quoted YAML scalar without its trailing comment or quotes; empty is None."""
	no_comment = re.sub(r"\s+#.*$", "", raw).strip()
	m = re.match(r"""^(["'])(.*)\1$""", no_comment)
	value = m.group(2) if m else no_comment
	return value or None


def top_level(block: str, key: str) -> str | None:
	m = re.search(rf"^{re.escape(key)}:[ \t]*(.*)$", block, re.MULTILINE)
	return scalar(m.group(1)) if m else None


def metadata_key(block: str, key: str) -> str | None:
	"""The value of `key:` nested under a top-level `metadata:` block."""
	lines = block.split("\n")
	start = next((i for i, line in enumerate(lines) if re.match(r"^metadata:\s*(#.*)?$", line)), None)
	if start is None:
		return None
	for line in lines[start + 1:]:
		if line and not line[0].isspace():
			break
		m = re.match(rf"^\s+{re.escape(key)}:[ \t]*(.*)$", line)
		if m:
			return scalar(m.group(1))
	return None


def tier_of(model: str) -> str | None:
	"""Which tier a model alias or full id belongs to; None for one the runes do not cover."""
	lowered = model.lower()
	for tier in ("haiku", "sonnet", "fable"):
		if tier in lowered:
			return tier
	if "opus" in lowered or "mythos" in lowered:
		return "opus"
	return None


def lint_text(text: str) -> list[str]:
	"""Every finding for one SKILL.md, as a short sentence each; empty when it conforms."""
	block = frontmatter_block(text)
	if block is None:
		return ["no frontmatter block"]
	model = top_level(block, "model")
	if model == "inherit":
		model = None
	glyph = metadata_key(block, "glyph")

	if model is None and glyph is None:
		return []
	if model is None:
		return [f"glyph {glyph} set without a model: field (omit the glyph when the model is omitted)"]
	tier = tier_of(model)
	if tier is None:
		return [f"model {model} is not a tier the runes cover"]
	expected = RUNE_FOR_TIER[tier]
	if glyph is None:
		return [f"model {model} set without metadata.glyph (expected {expected})"]
	if glyph != expected:
		have = TIER_FOR_RUNE.get(glyph)
		said = f"{glyph} ({have})" if have else f"{glyph} (not a tier rune)"
		return [f"glyph {said} does not mirror model {model} (expected {expected})"]
	return []


def lint_path(path: Path) -> list[str]:
	return lint_text(path.read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
	targets = [Path(a) for a in argv] if argv else sorted(SKILLS_DIR.glob("*/SKILL.md"))
	if not targets:
		print("skill-lint.py: no SKILL.md files to lint", file=sys.stderr)
		return 1
	hits = 0
	for path in targets:
		for finding in lint_path(path):
			hits += 1
			try:
				shown = path.resolve().relative_to(REPO_ROOT)
			except ValueError:
				shown = path
			print(f"{shown}: {finding}")
	if hits:
		print(f"skill-lint.py: {hits} finding{'s' if hits != 1 else ''} in {len(targets)} skill{'s' if len(targets) != 1 else ''}", file=sys.stderr)
		return 1
	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
