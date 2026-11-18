#!/usr/bin/env python3
"""Tests for safe-version-next.sh's root/plugin scoping and 0.x guard.

Run from this directory: python3 -m unittest test_safe_version_next -v
Each test builds a throwaway git repo in a TemporaryDirectory, drives the
script as a subprocess (it's zsh, not Python; nothing here reimplements its
logic) and asserts on stdout/stderr/exit code. Skipped entirely when svu
isn't installed, since every case needs it.
"""
from __future__ import annotations

import json
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
		# a broken policy file fails open, and says so: the reader's refusal reaches stderr beside the tag
		(self.repo / ".claude" / "versioning.json").write_text('{"omit-release": "root"}')
		broken = _run(self.repo)
		self.assertEqual(broken.returncode, 0, broken.stderr)
		self.assertTrue(broken.stdout.startswith("v"), "a tag is still printed")
		self.assertIn("omit-release must be a list of target names", broken.stderr)

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

	def _renamed(self, old_tag: str, renames: dict, declared: str | None = None, message: str = "feat(new)!: rename old to new", before_rename: str | None = None) -> None:
		"""Tag `old/` at `old_tag` (none when empty), optionally commit `before_rename` under `old/`, then move it to `new/` in one commit with the marketplace's renames map."""
		_commit(self.repo, "old/f", "feat(old): init")
		if old_tag:
			_git(self.repo, "tag", old_tag)
		if before_rename is not None:
			_commit(self.repo, "old/e", before_rename)
		_git(self.repo, "mv", "old", "new")
		if declared is not None:
			manifest = self.repo / "new" / ".claude-plugin" / "plugin.json"
			manifest.parent.mkdir(parents=True, exist_ok=True)
			manifest.write_text(f'{{\n\t"name": "new",\n\t"version": "{declared}"\n}}\n')
		marketplace = self.repo / ".claude-plugin" / "marketplace.json"
		marketplace.parent.mkdir(parents=True, exist_ok=True)
		marketplace.write_text(json.dumps({"plugins": [{"name": "new", "source": "./new"}], "renames": renames}))
		_commit(self.repo, "new/g", message)

	def test_a_renamed_2x_plugin_with_a_breaking_commit_takes_the_next_major_under_its_new_prefix(self) -> None:
		self._renamed("old-v2.4.0", {"old": "new"})
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "new-v3.0.0")

	def test_a_renamed_0x_plugin_declaring_1_0_0_crosses_the_guard(self) -> None:
		self._renamed("old-v0.2.0", {"old": "new"}, declared="1.0.0")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "new-v1.0.0")
		self.assertNotIn("guard:", result.stderr)

	def test_a_renamed_0x_plugin_not_declaring_1_0_0_is_still_held_in_0x(self) -> None:
		self._renamed("old-v0.2.0", {"old": "new"}, declared="0.2.0")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "new-v0.3.0")
		self.assertIn("guard:", result.stderr)

	def test_a_renamed_plugin_follows_the_chain_back_past_an_untagged_name(self) -> None:
		self._renamed("old-v1.2.0", {"old": "mid", "mid": "new"}, message="fix(new): rename old to new")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "new-v1.2.1")

	def test_a_renamed_plugin_continues_the_nearest_tagged_earlier_name(self) -> None:
		self._renamed("old-v1.2.0", {"old": "mid", "mid": "new"}, message="fix(new): rename mid to new")
		_git(self.repo, "tag", "mid-v2.0.0", "HEAD~1")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "new-v2.0.1")

	def test_commits_under_the_old_directory_since_its_last_tag_count_towards_the_bump(self) -> None:
		self._renamed("old-v2.4.0", {"old": "new"}, message="fix(new): rename old to new", before_rename="feat(old)!: drop thing")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "new-v3.0.0")

	def test_a_renamed_0x_plugin_declaring_1_0_0_crosses_even_when_the_rename_commit_bumps_nothing(self) -> None:
		self._renamed("old-v0.2.0", {"old": "new"}, declared="1.0.0", message="chore(new): rename old to new")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "new-v1.0.0")

	def test_a_renamed_plugin_with_no_old_tags_bootstraps_from_its_manifest(self) -> None:
		self._renamed("", {"old": "new"}, declared="0.3.0")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "new-v0.3.0")

	def test_a_plugin_tagged_under_its_new_prefix_ignores_the_renames_map(self) -> None:
		self._renamed("old-v2.4.0", {"old": "new"})
		_git(self.repo, "tag", "new-v3.0.0")
		_commit(self.repo, "new/h", "fix(new): thing")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "new-v3.0.1")


if __name__ == "__main__":
	unittest.main()
