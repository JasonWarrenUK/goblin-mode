#!/usr/bin/env python3
"""Tests for skill-lint.py: the glyph-mirrors-model rule and the exit code.

Run from this directory: python3 -m unittest test_skill_lint -v
(or python3 -m pytest test_skill_lint.py). Stdlib only.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "skill-lint.py"

spec = importlib.util.spec_from_file_location("skill_lint", SCRIPT)
skill_lint = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(skill_lint)


def skill(model: str | None, glyph: str | None, extra: str = "") -> str:
	lines = ["---", "name: x"]
	if model is not None:
		lines.append(f"model: {model}")
	lines.append("metadata:")
	if glyph is not None:
		lines.append(f"  glyph: {glyph}   # a comment")
	lines.append("  family: pr")
	if extra:
		lines.append(extra)
	lines += ["---", "", "# body", "model: haiku", "  glyph: ᚺ"]
	return "\n".join(lines)


class GlyphRule(unittest.TestCase):
	def test_matching_pairs_pass(self) -> None:
		for model, glyph in [("haiku", "ᚺ"), ("sonnet", "ᛊ"), ("opus", "ᛟ"), ("fable", "ᚠ"), ("claude-sonnet-5-5", "ᛊ"), ("claude-mythos-5-1", "ᛟ")]:
			with self.subTest(model=model):
				self.assertEqual(skill_lint.lint_text(skill(model, glyph)), [])

	def test_mismatch_names_both_tiers(self) -> None:
		[finding] = skill_lint.lint_text(skill("sonnet", "ᚺ"))
		self.assertIn("ᚺ (haiku)", finding)
		self.assertIn("expected ᛊ", finding)

	def test_glyph_without_model_and_model_without_glyph(self) -> None:
		self.assertIn("without a model", skill_lint.lint_text(skill(None, "ᛟ"))[0])
		self.assertIn("without metadata.glyph", skill_lint.lint_text(skill("opus", None))[0])
		self.assertIn("expected ᛟ", skill_lint.lint_text(skill("opus", None))[0])

	def test_knowledge_skill_with_neither_passes(self) -> None:
		self.assertEqual(skill_lint.lint_text(skill(None, None)), [])
		self.assertEqual(skill_lint.lint_text(skill("inherit", None)), [])

	def test_quotes_and_comments_are_stripped(self) -> None:
		self.assertEqual(skill_lint.lint_text(skill('"opus"', "ᛟ")), [])

	def test_glyph_is_only_read_under_metadata(self) -> None:
		text = "---\nname: x\nmodel: opus\nglyph: ᛟ\nmetadata:\n  family: pr\n---\n"
		self.assertIn("without metadata.glyph", skill_lint.lint_text(text)[0])

	def test_unknown_model_and_missing_frontmatter_are_reported(self) -> None:
		self.assertIn("not a tier", skill_lint.lint_text(skill("gpt-9", "ᛟ"))[0])
		self.assertEqual(skill_lint.lint_text("no frontmatter"), ["no frontmatter block"])


class Cli(unittest.TestCase):
	def run_on(self, *texts: str) -> subprocess.CompletedProcess[str]:
		with tempfile.TemporaryDirectory() as tmp:
			paths = []
			for i, text in enumerate(texts):
				p = Path(tmp) / f"s{i}" / "SKILL.md"
				p.parent.mkdir()
				p.write_text(text, encoding="utf-8")
				paths.append(str(p))
			return subprocess.run([sys.executable, str(SCRIPT), *paths], capture_output=True, text=True)

	def test_exit_code_follows_findings(self) -> None:
		clean = self.run_on(skill("opus", "ᛟ"), skill(None, None))
		self.assertEqual(clean.returncode, 0, clean.stderr)
		self.assertEqual(clean.stdout, "")
		dirty = self.run_on(skill("opus", "ᛟ"), skill("sonnet", "ᚺ"))
		self.assertEqual(dirty.returncode, 1)
		self.assertIn("expected ᛊ", dirty.stdout)
		self.assertIn("1 finding in 2 skills", dirty.stderr)

	def test_the_repo_conforms(self) -> None:
		result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
	unittest.main()
