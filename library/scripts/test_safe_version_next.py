#!/usr/bin/env python3
"""Tests for safe-version-next.sh's root/plugin scoping and 0.x guard.

Run from this directory: python3 -m unittest test_safe_version_next -v
Each test builds a throwaway git repo in a TemporaryDirectory, drives the
script as a subprocess (it's zsh, not Python; nothing here reimplements its
logic) and asserts on stdout/stderr/exit code. Skipped entirely when svu
isn't installed, since every case needs it.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "safe-version-next.sh"


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
	return subprocess.run(
		[str(SCRIPT), *args],
		cwd=cwd,
		capture_output=True,
		text=True,
	)


def _git(cwd: Path, *args: str) -> None:
	subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _commit(cwd: Path, path: str, message: str) -> None:
	target = cwd / path
	target.parent.mkdir(parents=True, exist_ok=True)
	target.write_text(target.read_text() + "x\n" if target.exists() else "x\n")
	_git(cwd, "add", "-A")
	_git(cwd, "commit", "-q", "-m", message)


@unittest.skipUnless(shutil.which("svu"), "svu not installed")
class SafeVersionNext(unittest.TestCase):
	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.repo = Path(self._tmp.name)
		_git(self.repo, "init", "-q")
		_git(self.repo, "config", "user.email", "t@t")
		_git(self.repo, "config", "user.name", "t")

	def tearDown(self) -> None:
		self._tmp.cleanup()

	def test_root_untagged_docs_only_history_has_nothing_to_release(self) -> None:
		_commit(self.repo, "a", "docs: readme")
		result = _run(self.repo)
		self.assertEqual(result.returncode, 3, result.stderr)
		self.assertIn("nothing to release", result.stderr)

	def test_root_untagged_with_a_fix_bumps_from_zero(self) -> None:
		_commit(self.repo, "a", "docs: readme")
		_commit(self.repo, "b", "fix: thing")
		result = _run(self.repo)
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "v0.0.1")

	def test_a_target_in_omit_gh_tag_exits_4_before_any_version_is_computed(self) -> None:
		_commit(self.repo, "a", "fix: thing")
		_commit(self.repo, "pkg/f", "feat(pkg): init")
		(self.repo / ".claude").mkdir()
		(self.repo / ".claude" / "versioning.json").write_text('{\n\t"omit-gh-tag": ["root"],\n\t"omit-release": [],\n\t"omit-changelog": []\n}\n')
		result = _run(self.repo)
		self.assertEqual(result.returncode, 4, result.stderr)
		self.assertEqual(result.stdout, "", "no tag is printed for an omitted target")
		self.assertIn("omitted by policy: root is in omit-gh-tag", result.stderr)
		plugin = _run(self.repo, "--plugin", "pkg", "--dir", "pkg")
		self.assertEqual(plugin.returncode, 0, "the plugin series is unaffected by the root's omission")
		self.assertEqual(plugin.stdout.strip(), "pkg-v0.1.0")
		(self.repo / ".claude" / "versioning.json").write_text('{\n\t"omit-gh-tag": [],\n\t"omit-release": ["root"],\n\t"omit-changelog": []\n}\n')
		self.assertEqual(_run(self.repo).returncode, 0, "a release omission alone still tags")

	def test_plugin_bootstrap_with_no_tag_and_no_built_manifest_starts_at_0_1_0(self) -> None:
		_commit(self.repo, "pkg/f", "feat(pkg): init")
		result = _run(self.repo, "--plugin", "pkg", "--dir", "pkg")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "pkg-v0.1.0")

	def test_plugin_bootstrap_honours_an_already_built_manifest_version(self) -> None:
		_commit(self.repo, "pkg/f", "feat(pkg): init")
		manifest = self.repo / "pkg" / ".claude-plugin" / "plugin.json"
		manifest.parent.mkdir(parents=True, exist_ok=True)
		manifest.write_text('{\n\t"name": "pkg",\n\t"version": "0.3.0"\n}\n')
		result = _run(self.repo, "--plugin", "pkg", "--dir", "pkg")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "pkg-v0.3.0")

	def test_root_0x_to_1x_guard_holds_at_0x(self) -> None:
		_commit(self.repo, "a", "feat: init")
		_git(self.repo, "tag", "v0.1.0")
		_commit(self.repo, "b", "feat!: break it")
		result = _run(self.repo)
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "v0.2.0")
		self.assertIn("guard:", result.stderr)

	def test_plugin_0x_to_1x_guard_holds_at_0x(self) -> None:
		_commit(self.repo, "pkg/f", "feat(pkg): init")
		_git(self.repo, "tag", "pkg-v0.1.0")
		_commit(self.repo, "pkg/g", "feat(pkg)!: break it")
		result = _run(self.repo, "--plugin", "pkg", "--dir", "pkg")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "pkg-v0.2.0")
		self.assertIn("guard:", result.stderr)

	def test_plugin_only_bumps_on_commits_touching_its_own_subtree(self) -> None:
		_commit(self.repo, "pkg/f", "feat(pkg): init")
		_git(self.repo, "tag", "pkg-v0.1.0")
		_commit(self.repo, "other/g", "feat(other): unrelated")
		result = _run(self.repo, "--plugin", "pkg", "--dir", "pkg")
		self.assertEqual(result.returncode, 3, result.stderr)
		self.assertIn("nothing to release", result.stderr)


if __name__ == "__main__":
	unittest.main()
