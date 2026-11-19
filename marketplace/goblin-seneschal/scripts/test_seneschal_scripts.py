#!/usr/bin/env python3
"""Tests for goblin-seneschal's copies of the library scripts: the flags that
point them at the user's own suite and stores, the one-line `missing:` exit 2
when those are absent, and audit-prose's SKIP for a skill that is not
installed.

Run from this directory: python3 -m unittest test_seneschal_scripts -v
Each test drives a script as a subprocess against a throwaway directory, so
the exit codes and lines the skills relay are the ones under test.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _run(script: str, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
	return subprocess.run([sys.executable, str(HERE / script), *args], capture_output=True, text=True, env=env)


def _load(name: str, file: str):
	spec = importlib.util.spec_from_file_location(name, HERE / file)
	module = importlib.util.module_from_spec(spec)
	assert spec.loader is not None
	spec.loader.exec_module(module)
	return module


HAS_YAML = importlib.util.find_spec("yaml") is not None

PERSONA = """---
id: PER001
slug: tam
description: an invented reader
quickFacts: []
isRealPerson: false
updated: 2026-11-18
pronouns: they/them
linkedProfileIds: []
scope: test
---
Body.
"""


class Scripts(unittest.TestCase):
	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.root = Path(self._tmp.name)

	def tearDown(self) -> None:
		self._tmp.cleanup()

	def test_prose_metrics_names_a_missing_scanner_and_exits_2(self) -> None:
		result = _run("prose-metrics.py", "--scan", str(self.root / "nowhere" / "slop-scan.py"), "--state", str(self.root / "m.json"))
		self.assertEqual(result.returncode, 2, result.stderr)
		self.assertIn("missing:", result.stderr)
		self.assertIn("slop-scan.py", result.stderr)
		self.assertFalse((self.root / "m.json").exists())

	def test_prose_health_names_a_missing_suite_and_exits_2_before_auditing_anything(self) -> None:
		result = _run("prose-health.py", "--no-record", "--scripts-dir", str(self.root / "empty"))
		self.assertEqual(result.returncode, 2, result.stderr)
		self.assertIn("missing:", result.stderr)
		self.assertIn("prose_scripts_dir", result.stderr)
		self.assertEqual(result.stdout, "", "nothing is audited")

	def test_prose_health_expands_a_home_relative_flag(self) -> None:
		env = {**os.environ, "HOME": str(self.root)}
		result = _run("prose-health.py", "--no-record", "--scripts-dir", "~/suite", env=env)
		self.assertEqual(result.returncode, 2, result.stderr)
		self.assertIn(str(self.root / "suite" / "slop-scan.py"), result.stderr)

	def test_a_named_skill_that_is_not_installed_reads_skip_and_an_installed_one_still_fails(self) -> None:
		health = _load("prose_health", "prose-health.py")
		health.CONFIG_DIR = self.root
		(self.root / "skills").mkdir()
		status, check, detail = health.check_skills()
		self.assertEqual((status, check), ("SKIP", "skills"), detail)
		skill = self.root / "skills" / "pr-create"
		skill.mkdir()
		(skill / "SKILL.md").write_text("no gate text here\n")
		status, _, detail = health.check_skills()
		self.assertEqual(status, "FAIL", detail)
		self.assertIn("pr-create: slop-scan.py --strict", detail)
		(skill / "SKILL.md").write_text("slop-scan.py --strict\nBash(~/.claude/library/scripts/slop-scan.py:*)\n")
		status, _, detail = health.check_skills()
		self.assertEqual(status, "PASS", detail)
		self.assertIn(f"{len(health.SKILL_WIRING) - 1} not installed, skipped", detail)

	@unittest.skipUnless(HAS_YAML, "PyYAML not installed")
	def test_frontmatter_check_leaves_a_missing_style_file_to_the_style_check(self) -> None:
		health = _load("prose_health_missing_style", "prose-health.py")
		health.CONFIG_DIR = self.root
		health.STYLE = self.root / "output-styles" / "nowhere.md"
		(self.root / "skills").mkdir()
		status, check, detail = health.check_frontmatter()
		self.assertEqual((status, check), ("PASS", "frontmatter"), detail)

	@unittest.skipUnless(HAS_YAML, "PyYAML not installed")
	def test_frontmatter_check_names_a_broken_style_file_outside_the_config_dir_by_its_full_path(self) -> None:
		health = _load("prose_health_outside_style", "prose-health.py")
		health.CONFIG_DIR = self.root / "config"
		(health.CONFIG_DIR / "skills").mkdir(parents=True)
		style = self.root / "elsewhere" / "style.md"
		style.parent.mkdir()
		style.write_text("no frontmatter at all\n")
		health.STYLE = style
		status, _, detail = health.check_frontmatter()
		self.assertEqual(status, "FAIL", detail)
		self.assertIn(str(style), detail)

	@unittest.skipUnless(HAS_YAML, "PyYAML not installed")
	def test_profiles_names_a_missing_store_and_exits_2(self) -> None:
		result = _run("profiles.py", "--dossier-dir", str(self.root / "no-dossier"), "--personas-dir", str(self.root / "no-personas"), "count")
		self.assertEqual(result.returncode, 2, result.stderr)
		self.assertIn("missing:", result.stderr)
		self.assertIn("dossier store", result.stderr)
		self.assertIn("personas store", result.stderr)

	@unittest.skipUnless(HAS_YAML, "PyYAML not installed")
	def test_profiles_reads_the_stores_the_flags_name(self) -> None:
		personas = self.root / "personas"
		personas.mkdir()
		(personas / "tam.md").write_text(PERSONA)
		result = _run("profiles.py", "--dossier-dir", str(self.root / "no-dossier"), "--personas-dir", str(personas), "count", "--store", "personas")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "personas: 1")
		shown = _run("profiles.py", "--personas-dir", str(personas), "get", "tam", "--store", "personas")
		self.assertEqual(shown.returncode, 0, shown.stderr)
		self.assertIn("## personas: tam", shown.stdout)


if __name__ == "__main__":
	unittest.main()
