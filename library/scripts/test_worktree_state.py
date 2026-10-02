#!/usr/bin/env python3
"""Tests for worktree-state.sh's counts, base resolution and refusals.

Run from this directory: python3 -m unittest test_worktree_state -v
Each test builds a throwaway repo with a bare `origin` in a
TemporaryDirectory, then drives the script as a subprocess (it's zsh, not
Python; nothing here reimplements its logic). Skipped entirely when jq isn't
installed.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "worktree-state.sh"


def _git(cwd: Path, *args: str) -> str:
	return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
		text=True).stdout


@unittest.skipUnless(shutil.which("jq"), "jq not installed")
class WorktreeState(unittest.TestCase):
	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.root = Path(self._tmp.name).resolve()
		origin = self.root / "origin.git"
		self.repo = self.root / "repo"
		_git(self.root, "init", "-q", "--bare", "-b", "main", str(origin))
		_git(self.root, "clone", "-q", str(origin), str(self.repo))
		_git(self.repo, "config", "user.email", "t@t")
		_git(self.repo, "config", "user.name", "t")
		_git(self.repo, "checkout", "-q", "-b", "main")
		self._commit("chore: init")
		_git(self.repo, "push", "-q", "-u", "origin", "main")

	def tearDown(self) -> None:
		self._tmp.cleanup()

	def _commit(self, message: str) -> None:
		_git(self.repo, "commit", "-q", "--allow-empty", "-m", message)

	def _run(self, *args: str) -> tuple[int, dict, str]:
		result = subprocess.run([str(SCRIPT), *args], capture_output=True, text=True)
		report = json.loads(result.stdout) if result.stdout.strip() else {}
		return result.returncode, report, result.stderr

	def test_clean_and_level_with_its_upstream(self) -> None:
		code, report, _ = self._run(str(self.repo))
		self.assertEqual(code, 0)
		self.assertEqual(report, {"path": str(self.repo), "dirty": 0,
			"base": "origin/main", "ahead": 0, "behind": 0})

	def test_counts_untracked_and_modified_files(self) -> None:
		(self.repo / "a.txt").write_text("a")
		(self.repo / "b.txt").write_text("b")
		code, report, _ = self._run(str(self.repo))
		self.assertEqual((code, report["dirty"]), (0, 2))

	def test_ahead_and_behind_against_an_explicit_base(self) -> None:
		_git(self.repo, "checkout", "-q", "-b", "feat/x")
		self._commit("feat: one")
		self._commit("feat: two")
		_git(self.repo, "checkout", "-q", "main")
		self._commit("chore: on main")
		_git(self.repo, "push", "-q", "origin", "main")
		_git(self.repo, "checkout", "-q", "feat/x")
		code, report, _ = self._run(str(self.repo), "origin/main")
		self.assertEqual(code, 0)
		self.assertEqual((report["base"], report["ahead"], report["behind"]),
			("origin/main", 2, 1))

	def test_no_upstream_and_no_base_gives_null_counts(self) -> None:
		_git(self.repo, "checkout", "-q", "-b", "local-only")
		code, report, _ = self._run(str(self.repo))
		self.assertEqual(code, 0)
		self.assertEqual((report["base"], report["ahead"], report["behind"]),
			(None, None, None))

	def test_a_linked_worktree_reports_its_own_state(self) -> None:
		linked = self.root / "linked"
		_git(self.repo, "worktree", "add", "-q", "-b", "feat/y", str(linked))
		(linked / "c.txt").write_text("c")
		code, report, _ = self._run(str(linked), "origin/main")
		self.assertEqual((code, report["dirty"], report["ahead"]), (0, 1, 0))
		self.assertEqual(self._run(str(self.repo))[1]["dirty"], 0)

	def test_an_option_as_base_is_refused_and_runs_nothing(self) -> None:
		marker = self.root / "ran"
		code, report, stderr = self._run(str(self.repo), f"--output={marker}")
		self.assertEqual((code, report), (2, {}))
		self.assertIn("not a commit", stderr)
		self.assertFalse(marker.exists())

	def test_unknown_base_is_refused(self) -> None:
		code, _, stderr = self._run(str(self.repo), "origin/nope")
		self.assertEqual(code, 2)
		self.assertIn("not a commit", stderr)

	def test_not_a_repository_is_refused(self) -> None:
		plain = self.root / "plain"
		plain.mkdir()
		code, _, stderr = self._run(str(plain))
		self.assertEqual(code, 2)
		self.assertIn("not inside a git work tree", stderr)

	def test_missing_directory_is_refused(self) -> None:
		code, _, stderr = self._run(str(self.root / "gone"))
		self.assertEqual(code, 2)
		self.assertIn("not a directory", stderr)

	def test_wrong_argument_count_is_refused(self) -> None:
		self.assertEqual(self._run()[0], 2)
		self.assertEqual(self._run(str(self.repo), "origin/main", "extra")[0], 2)


if __name__ == "__main__":
	unittest.main()
