#!/usr/bin/env python3
"""Tests for checkout-occupied.sh's session matching and exit codes.

Run from this directory: python3 -m unittest test_checkout_occupied -v
Each test builds a throwaway git repo and a fake sessions directory in a
TemporaryDirectory, then drives the script as a subprocess (it's zsh, not
Python; nothing here reimplements its logic). A live session is a `sleep`
child process, since the script only asks whether the pid is alive. Skipped
entirely when jq isn't installed.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "checkout-occupied.sh"


def _git(cwd: Path, *args: str) -> None:
	subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@unittest.skipUnless(shutil.which("jq"), "jq not installed")
class CheckoutOccupied(unittest.TestCase):
	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		root = Path(self._tmp.name).resolve()
		self.repo = root / "repo"
		self.sessions = root / "sessions"
		self.repo.mkdir()
		self.sessions.mkdir()
		_git(self.repo, "init", "-q", "-b", "main")
		_git(self.repo, "config", "user.email", "t@t")
		_git(self.repo, "config", "user.name", "t")
		_git(self.repo, "commit", "-q", "--allow-empty", "-m", "chore: init")
		self._children: list[subprocess.Popen] = []

	def tearDown(self) -> None:
		for child in self._children:
			child.kill()
			child.wait()
		self._tmp.cleanup()

	def _live_pid(self) -> int:
		child = subprocess.Popen(["sleep", "60"])
		self._children.append(child)
		return child.pid

	def _dead_pid(self) -> int:
		child = subprocess.Popen(["true"])
		child.wait()
		return child.pid

	def _session(self, name: str, pid: int, cwd: Path) -> None:
		(self.sessions / f"{pid}.json").write_text(json.dumps({
			"pid": pid,
			"sessionId": f"id-{name}",
			"cwd": str(cwd),
			"name": name,
			"status": "busy",
		}))

	def _run(self, *args: str, cwd: Path | None = None) -> tuple[int, dict, str]:
		result = subprocess.run(
			[str(SCRIPT), *args],
			cwd=cwd or self.repo,
			capture_output=True,
			text=True,
			env={**os.environ, "CLAUDE_SESSIONS_DIR": str(self.sessions)},
		)
		report = json.loads(result.stdout) if result.stdout.strip() else {}
		return result.returncode, report, result.stderr

	def test_no_sessions_reports_a_free_checkout(self) -> None:
		code, report, stderr = self._run()
		self.assertEqual(code, 0, stderr)
		self.assertFalse(report["occupied"])
		self.assertEqual(report["sessions"], [])
		self.assertEqual(report["branch"], "main")
		self.assertEqual(report["dirty_files"], 0)

	def test_live_session_in_the_checkout_occupies_it(self) -> None:
		self._session("record-corrections", self._live_pid(), self.repo)
		code, report, stderr = self._run()
		self.assertEqual(code, 1, stderr)
		self.assertTrue(report["occupied"])
		self.assertEqual([s["name"] for s in report["sessions"]], ["record-corrections"])

	def test_session_started_in_a_subdirectory_counts(self) -> None:
		subdirectory = self.repo / "services"
		subdirectory.mkdir()
		self._session("deep", self._live_pid(), subdirectory)
		code, report, _ = self._run()
		self.assertEqual(code, 1)
		self.assertEqual(report["sessions"][0]["name"], "deep")

	def test_dead_session_is_ignored(self) -> None:
		self._session("gone", self._dead_pid(), self.repo)
		code, report, stderr = self._run()
		self.assertEqual(code, 0, stderr)
		self.assertEqual(report["sessions"], [])

	def test_calling_session_is_left_out(self) -> None:
		# This test process is an ancestor of the script, as a Claude session is
		self._session("caller", os.getpid(), self.repo)
		code, report, stderr = self._run()
		self.assertEqual(code, 0, stderr)
		self.assertEqual(report["sessions"], [])

	def test_session_in_a_worktree_does_not_occupy_the_main_checkout(self) -> None:
		worktree = self.repo.parent / "repo-worktrees" / "feature"
		_git(self.repo, "worktree", "add", "-q", "-b", "feat/thing", str(worktree))
		self._session("in-worktree", self._live_pid(), worktree)
		code, report, stderr = self._run()
		self.assertEqual(code, 0, stderr)
		self.assertEqual(report["sessions"], [])
		code, report, _ = self._run(str(worktree))
		self.assertEqual(code, 1)
		self.assertEqual(report["branch"], "feat/thing")

	def test_session_whose_directory_was_deleted_is_ignored(self) -> None:
		self._session("orphan", self._live_pid(), self.repo.parent / "deleted-worktree")
		code, report, stderr = self._run()
		self.assertEqual(code, 0, stderr)
		self.assertEqual(report["sessions"], [])

	def test_dirty_files_are_counted(self) -> None:
		(self.repo / "a.py").write_text("x\n")
		(self.repo / "b.py").write_text("x\n")
		code, report, _ = self._run()
		self.assertEqual(code, 0)
		self.assertEqual(report["dirty_files"], 2)

	def test_path_outside_a_repository_is_an_error(self) -> None:
		code, _, stderr = self._run(str(self.sessions))
		self.assertEqual(code, 2)
		self.assertIn("not inside a git repository", stderr)


if __name__ == "__main__":
	unittest.main()
