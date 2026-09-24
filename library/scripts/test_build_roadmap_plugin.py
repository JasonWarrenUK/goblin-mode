#!/usr/bin/env python3
"""Tests for build-roadmap-plugin.py's safeguards.

Run from this directory: python3 -m unittest test_build_roadmap_plugin -v
Stdlib only. Each test copies the live sources into a TemporaryDirectory
shaped like this repo, breaks them the way a rename or move would, and checks
the build refuses with a message naming the problem.
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "build-roadmap-plugin.py"
REPO_ROOT = SCRIPT.parents[2]

_spec = importlib.util.spec_from_file_location("build_roadmap_plugin", SCRIPT)
plugin = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plugin)


class BuildSafeguards(unittest.TestCase):
	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.root = Path(self._tmp.name) / "repo"
		self.out = Path(self._tmp.name) / "out"
		for rel in plugin.source_paths():
			target = self.root / rel
			target.parent.mkdir(parents=True, exist_ok=True)
			shutil.copyfile(REPO_ROOT / rel, target)

	def tearDown(self) -> None:
		self._tmp.cleanup()

	def build_problems(self) -> list[str]:
		with self.assertRaises(plugin.BuildError) as caught:
			plugin.build(self.root, self.out)
		return caught.exception.problems

	def append(self, rel: str, text: str) -> None:
		path = self.root / rel
		path.write_text(path.read_text() + text)

	def test_clean_sources_build(self) -> None:
		plugin.build(self.root, self.out)
		self.assertTrue((self.out / "skills" / "maintain" / "SKILL.md").is_file())
		self.assertEqual(
			(self.out / "README.md").read_text(),
			(self.root / plugin.README_SOURCE).read_text(),
		)

	def test_renamed_skill_dir_is_named(self) -> None:
		(self.root / "skills" / "roadmap-review").rename(self.root / "skills" / "roadmap-audit")
		problems = self.build_problems()
		self.assertEqual(len(problems), 1)
		self.assertIn("missing source: skills/roadmap-review/SKILL.md", problems[0])

	def test_moved_script_is_named(self) -> None:
		(self.root / "library" / "tools").mkdir()
		(self.root / "library" / "scripts" / "roadmap.py").rename(self.root / "library" / "tools" / "roadmap.py")
		self.assertIn("missing source: library/scripts/roadmap.py", self.build_problems()[0])

	def test_unshipped_plugin_file_is_caught(self) -> None:
		self.append("skills/roadmap-maintain/SKILL.md", '\nRun `python3 "$HOME"/.claude/library/scripts/roadmap-extra.py`.\n')
		problems = self.build_problems()
		self.assertTrue(any("skills/maintain/SKILL.md" in p and "scripts/roadmap-extra.py is not shipped" in p for p in problems))

	def test_leftover_home_path_is_caught(self) -> None:
		self.append("skills/roadmap-maintain/SKILL.md", "\nSee `~/.claude/docs/notes.md`.\n")
		self.assertTrue(any("path into ~/.claude survives" in p for p in self.build_problems()))

	def test_renamed_sibling_reference_is_caught(self) -> None:
		# The renamed skill exists in this config but not in the plugin
		(self.root / "skills" / "roadmap-audit").mkdir()
		(self.root / "skills" / "roadmap-audit" / "SKILL.md").write_text("---\nname: audit\n---\n")
		self.append("skills/roadmap-create/SKILL.md", "\nSee `roadmap-audit`.\n")
		self.assertTrue(any("skill 'roadmap-audit' is not in the plugin" in p for p in self.build_problems()))

	def test_excluded_skill_reference_is_caught(self) -> None:
		(self.root / "skills" / "next-task-ship").mkdir()
		(self.root / "skills" / "next-task-ship" / "SKILL.md").write_text("---\nname: ship\n---\n")
		self.append("skills/next-task-suggest/SKILL.md", "\nThen hand over to `next-task-ship`.\n")
		self.assertTrue(any("skill 'next-task-ship'" in p for p in self.build_problems()))

	def test_namespaced_and_file_names_are_not_flagged(self) -> None:
		# roadmap:maintain, roadmap-conventions.md and paths must never trip the skill check
		(self.root / "skills" / "roadmap-conventions").mkdir()
		(self.root / "skills" / "roadmap-conventions" / "SKILL.md").write_text("---\nname: x\n---\n")
		plugin.build(self.root, self.out)

	def test_stale_decoupling_is_named(self) -> None:
		path = self.root / "library" / "references" / "roadmap-conventions.md"
		path.write_text(path.read_text().replace("(Jason's terminal gradient)", "(the terminal gradient)"))
		self.assertIn("decoupling matched 0 times", self.build_problems()[0])

	def test_sources_lists_every_input(self) -> None:
		result = subprocess.run(
			[sys.executable, str(SCRIPT), "--sources"], capture_output=True, text=True, check=True
		)
		self.assertIn("skills/roadmap-maintain/SKILL.md", result.stdout.splitlines())
		self.assertIn(plugin.README_SOURCE, result.stdout.splitlines())

	def test_cli_reports_problems_and_writes_nothing(self) -> None:
		# The script finds its repo from its own location, so a copy runs against the fixture
		(self.root / "skills" / "roadmap-review" / "SKILL.md").unlink()
		result = subprocess.run(
			[sys.executable, str(self.root / "library" / "scripts" / "build-roadmap-plugin.py")],
			capture_output=True, text=True,
		)
		self.assertEqual(result.returncode, 1)
		self.assertIn("1 problem(s), nothing written", result.stderr)
		self.assertIn("missing source: skills/roadmap-review/SKILL.md", result.stderr)
		self.assertNotIn("Traceback", result.stderr)
		self.assertFalse((self.root / "marketplace").exists())

if __name__ == "__main__":
	unittest.main()
