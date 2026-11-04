#!/usr/bin/env python3
"""Tests for versioning-policy.py: the merged policy, the check exit codes and the setter.

Run from this directory: python3 -m unittest test_versioning_policy -v
Each test builds a throwaway git repo in a TemporaryDirectory and drives the
script as a subprocess, so the exit codes the readers depend on are the ones
under test.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "versioning-policy.py"


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
	return subprocess.run(["python3", "-I", str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True)


class VersioningPolicy(unittest.TestCase):
	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.repo = Path(self._tmp.name)
		subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
		(self.repo / ".claude-plugin").mkdir()
		(self.repo / ".claude-plugin" / "marketplace.json").write_text(json.dumps({"plugins": [{"name": "mission-control", "source": "./marketplace/mission-control"}]}))

	def tearDown(self) -> None:
		self._tmp.cleanup()

	def policy(self) -> dict:
		return json.loads((self.repo / ".claude" / "versioning.json").read_text())

	def _git(self, *args: str) -> None:
		subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=self.repo, check=True, capture_output=True)

	def _linked_worktree(self) -> Path:
		"""Commit the ignore rule, then add a detached linked worktree, as pr-land's landing worktree is."""
		(self.repo / ".gitignore").write_text(".claude/versioning.local.json\n")
		self._git("add", "-A")
		self._git("commit", "-qm", "init")
		linked = self.repo / "linked"
		self._git("worktree", "add", "-q", "--detach", str(linked), "HEAD")
		return linked

	def test_the_local_twin_is_shared_with_linked_worktrees(self) -> None:
		# pr-land tags from a detached landing worktree; the twin lives in the git directory every worktree shares
		linked = self._linked_worktree()
		_run(self.repo, "set", "omit", "tag", "root", "--local")
		self.assertTrue((self.repo / ".git" / "versioning.local.json").is_file(), "the twin sits in the common git dir, which nothing can commit")
		self.assertFalse((self.repo / ".claude" / "versioning.local.json").exists())
		self.assertEqual(_run(linked, "check", "tag", "root").returncode, 0, "a landing worktree sees the local omission")

	def test_set_local_from_a_linked_worktree_writes_to_the_shared_git_dir(self) -> None:
		linked = self._linked_worktree()
		out = _run(linked, "set", "omit", "tag", "root", "--local")
		self.assertEqual(out.returncode, 0, out.stderr)
		self.assertTrue((self.repo / ".git" / "versioning.local.json").is_file())
		self.assertFalse((linked / ".claude").exists(), "a file in the worktree would die with it")
		self.assertEqual(_run(self.repo, "check", "tag", "root").returncode, 0)

	def test_a_separate_git_dir_repository_shares_the_twin_with_its_worktrees(self) -> None:
		# git sets no core.worktree for --separate-git-dir and a linked worktree has no pointer back to the checkout, so only the git dir itself is a home every layout can find
		gitdir = self.repo / "gitdir"
		sep = self.repo / "sep"
		subprocess.run(["git", "init", "-q", "--separate-git-dir", str(gitdir), str(sep)], check=True, capture_output=True)
		(sep / ".claude").mkdir()
		(sep / ".claude" / "versioning.json").write_text('{\n\t"omit-gh-tag": [],\n\t"omit-release": [],\n\t"omit-changelog": []\n}\n')
		subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A"], cwd=sep, check=True, capture_output=True)
		subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"], cwd=sep, check=True, capture_output=True)
		linked = self.repo / "sep-linked"
		subprocess.run(["git", "worktree", "add", "-q", "--detach", str(linked), "HEAD"], cwd=sep, check=True, capture_output=True)
		_run(sep, "set", "omit", "tag", "root", "--local")
		self.assertTrue((gitdir / "versioning.local.json").is_file())
		self.assertEqual(_run(linked, "check", "tag", "root").returncode, 0)
		_run(linked, "set", "omit", "changelog", "root", "--local")
		self.assertEqual(_run(sep, "check", "changelog", "root").returncode, 0, "a write from the worktree lands in the one shared twin")

	def test_the_tracked_file_is_read_from_the_worktree_that_runs_the_check(self) -> None:
		linked = self._linked_worktree()
		_run(self.repo, "set", "omit", "changelog", "root")
		self.assertEqual(_run(self.repo, "check", "changelog", "root").returncode, 0)
		self.assertEqual(_run(linked, "check", "changelog", "root").returncode, 1, "the worktree's checkout of the tracked file governs, not the main checkout's")

	def test_ref_reads_the_policy_as_committed_not_the_working_tree(self) -> None:
		# pr-land Step 6 stands in the main checkout, which may be on any branch; origin/main's policy is the one that governs a landing
		self._git("add", "-A")
		self._git("commit", "-qm", "base")
		self._git("branch", "-M", "main")
		_run(self.repo, "set", "omit", "release", "root")
		self._git("add", "-A")
		self._git("commit", "-qm", "policy")
		self._git("checkout", "-q", "-b", "old", "HEAD~1")
		self.assertEqual(_run(self.repo, "check", "release", "root").returncode, 1, "the old branch has no policy file")
		self.assertEqual(_run(self.repo, "check", "release", "root", "--ref", "main").returncode, 0)
		self.assertEqual(json.loads(_run(self.repo, "show", "--json", "--ref", "main").stdout)["omit-release"], ["root"])

	def test_ref_still_unions_the_local_twin_from_the_working_tree(self) -> None:
		self._git("add", "-A")
		self._git("commit", "-qm", "base")
		_run(self.repo, "set", "omit", "changelog", "root", "--local")
		self.assertEqual(_run(self.repo, "check", "changelog", "root", "--ref", "HEAD").returncode, 0)

	def test_ref_reads_the_manifest_at_the_ref_and_an_unknown_ref_is_an_error(self) -> None:
		self._git("add", "-A")
		self._git("commit", "-qm", "base")
		self._git("branch", "-M", "main")
		self.assertEqual(_run(self.repo, "check", "release", "root", "--ref", "HEAD").returncode, 1, "a ref without the file omits nothing")
		out = _run(self.repo, "check", "release", "root", "--ref", "nope")
		self.assertEqual(out.returncode, 2)
		self.assertIn("unknown ref nope", out.stderr)
		# a plugin added at the ref but absent from the checkout is a known target under --ref
		(self.repo / ".claude-plugin" / "marketplace.json").write_text(json.dumps({"plugins": [{"name": "mission-control"}, {"name": "roadmap"}]}))
		self._git("add", "-A")
		self._git("commit", "-qm", "roadmap plugin")
		self._git("checkout", "-q", "HEAD~1")
		self.assertEqual(_run(self.repo, "check", "release", "roadmap").returncode, 2, "unknown in this checkout")
		self.assertEqual(_run(self.repo, "check", "release", "roadmap", "--ref", "main").returncode, 1, "known at the ref")

	def test_allow_notes_an_omission_the_other_file_still_holds(self) -> None:
		_run(self.repo, "set", "omit", "tag", "root")
		_run(self.repo, "set", "omit", "release", "root", "--local")
		out = _run(self.repo, "set", "allow", "release", "root", "--local")
		self.assertIn("still in omit-gh-tag", out.stdout, "the tag omission sits in the other file")
		self.assertEqual(_run(self.repo, "check", "release", "root").returncode, 0)
		_run(self.repo, "set", "omit", "changelog", "root")
		_run(self.repo, "set", "omit", "changelog", "root", "--local")
		out = _run(self.repo, "set", "allow", "changelog", "root", "--local")
		self.assertIn("still in omit-changelog in versioning.json", out.stdout)
		self.assertEqual(_run(self.repo, "check", "changelog", "root").returncode, 0)

	def test_no_policy_file_omits_nothing(self) -> None:
		for kind in ("tag", "release", "changelog"):
			self.assertEqual(_run(self.repo, "check", kind, "root").returncode, 1, kind)
		out = _run(self.repo, "show")
		self.assertEqual(out.returncode, 0, out.stderr)
		self.assertIn("none (every target is tagged", out.stdout)

	def test_set_omit_writes_canonical_json_and_check_reads_it(self) -> None:
		out = _run(self.repo, "set", "omit", "release", "root")
		self.assertEqual(out.returncode, 0, out.stderr)
		self.assertEqual((self.repo / ".claude" / "versioning.json").read_text(), '{\n\t"omit-gh-tag": [],\n\t"omit-release": ["root"],\n\t"omit-changelog": []\n}\n')
		self.assertEqual(_run(self.repo, "check", "release", "root").returncode, 0)
		self.assertEqual(_run(self.repo, "check", "tag", "root").returncode, 1, "a release omission leaves the tag alone")
		self.assertEqual(_run(self.repo, "check", "changelog", "root").returncode, 1)
		self.assertIn("already in", _run(self.repo, "set", "omit", "release", "root").stdout)

	def test_omit_tag_implies_omit_release_but_not_changelog(self) -> None:
		_run(self.repo, "set", "omit", "tag", "mission-control")
		self.assertEqual(_run(self.repo, "check", "tag", "mission-control").returncode, 0)
		self.assertEqual(_run(self.repo, "check", "release", "mission-control").returncode, 0, "a release needs a tag")
		self.assertEqual(_run(self.repo, "check", "changelog", "mission-control").returncode, 1)
		self.assertEqual(self.policy()["omit-release"], [], "the implication is read, not written")

	def test_allow_removes_and_warns_when_the_tag_omission_still_covers_the_release(self) -> None:
		_run(self.repo, "set", "omit", "tag", "root")
		_run(self.repo, "set", "omit", "release", "root")
		out = _run(self.repo, "set", "allow", "release", "root")
		self.assertEqual(out.returncode, 0, out.stderr)
		self.assertIn("still in omit-gh-tag", out.stdout)
		self.assertEqual(_run(self.repo, "check", "release", "root").returncode, 0)
		_run(self.repo, "set", "allow", "tag", "root")
		self.assertEqual(_run(self.repo, "check", "release", "root").returncode, 1)
		self.assertEqual(self.policy(), {"omit-gh-tag": [], "omit-release": [], "omit-changelog": []})

	def test_an_unknown_target_is_refused_when_the_marketplace_names_the_plugins(self) -> None:
		out = _run(self.repo, "set", "omit", "release", "misson-control")
		self.assertEqual(out.returncode, 2)
		self.assertIn("the targets are root, mission-control", out.stderr)
		self.assertFalse((self.repo / ".claude" / "versioning.json").exists())
		self.assertEqual(_run(self.repo, "check", "release", "nope").returncode, 2)

	def test_any_target_is_accepted_without_a_marketplace_manifest(self) -> None:
		(self.repo / ".claude-plugin" / "marketplace.json").unlink()
		self.assertEqual(_run(self.repo, "set", "omit", "changelog", "api").returncode, 0)
		self.assertEqual(_run(self.repo, "check", "changelog", "api").returncode, 0)

	def test_the_local_twin_is_unioned_in_and_written_with_the_flag(self) -> None:
		_run(self.repo, "set", "omit", "release", "root")
		out = _run(self.repo, "set", "omit", "changelog", "mission-control", "--local")
		self.assertEqual(out.returncode, 0, out.stderr)
		self.assertTrue((self.repo / ".git" / "versioning.local.json").is_file())
		self.assertEqual(self.policy()["omit-changelog"], [], "the tracked file is untouched by a local write")
		self.assertEqual(json.loads(_run(self.repo, "show", "--json").stdout), {"omit-gh-tag": [], "omit-release": ["root"], "omit-changelog": ["mission-control"]})
		self.assertEqual(_run(self.repo, "check", "changelog", "mission-control").returncode, 0)

	def test_a_broken_policy_file_is_an_error_not_a_silent_no(self) -> None:
		(self.repo / ".claude").mkdir()
		(self.repo / ".claude" / "versioning.json").write_text('{"omit-release": "root"}')
		out = _run(self.repo, "check", "release", "root")
		self.assertEqual(out.returncode, 2)
		self.assertIn("must be a list", out.stderr)
		(self.repo / ".claude" / "versioning.json").write_text('{"omit-releases": []}')
		self.assertIn("unknown key omit-releases", _run(self.repo, "show").stderr)


if __name__ == "__main__":
	unittest.main()
