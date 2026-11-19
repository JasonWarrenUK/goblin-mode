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
		# a walk that never ends (a cycle in the renames map) fails here instead of hanging
		timeout=60,
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

	def _renamed(self, old_tag: str, renames: dict, declared: str | None = None, message: str = "feat(new)!: rename old to new", before_rename: str | None = None, manifest_text: str | None = None) -> None:
		"""Tag `old/` at `old_tag` (none when empty), optionally commit `before_rename` under `old/`, then move it to `new/` in one commit with the marketplace's renames map. `manifest_text` writes new/'s plugin.json verbatim."""
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
		if manifest_text is not None:
			manifest = self.repo / "new" / ".claude-plugin" / "plugin.json"
			manifest.parent.mkdir(parents=True, exist_ok=True)
			manifest.write_text(manifest_text)
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

	def test_a_renamed_0x_plugin_declaring_above_1_0_0_is_held_in_0x(self) -> None:
		# only exactly 1.0.0 is the human's word on crossing; a higher hand-set number is not
		self._renamed("old-v0.13.0", {"old": "new"}, declared="2.0.0")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "new-v0.14.0")
		self.assertIn("guard:", result.stderr)
		self.assertIn("declares 2.0.0", result.stderr)

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

	def test_two_earlier_names_folding_into_one_are_both_tried_and_the_fold_is_reported(self) -> None:
		# insertion order puts the untagged name first; the tagged one must still be found
		self._renamed("old-v3.1.0", {"other": "new", "old": "new"}, message="fix(new): fold old and other into new")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "new-v3.1.1")
		self.assertIn("several earlier names", result.stderr)

	def test_an_unreadable_renames_map_says_so_instead_of_starting_a_fresh_series_in_silence(self) -> None:
		self._renamed("old-v2.4.0", {"old": "new"})
		listed = '"plugins": [{"name": "new", "source": "./new"}]'
		for broken in (f'{{{listed}, "renames": ["old", "new"]}}', f'{{{listed}, "renames": {{"old": "new"}},}}'):
			(self.repo / ".claude-plugin" / "marketplace.json").write_text(broken)
			result = _run(self.repo, "--plugin", "new", "--dir", "new")
			self.assertEqual(result.returncode, 0, result.stderr)
			self.assertIn("renames:", result.stderr, broken)
			self.assertEqual(result.stdout.strip(), "new-v0.1.0", broken)

	def test_a_rename_with_nothing_to_release_names_the_old_tag(self) -> None:
		self._renamed("old-v0.4.0", {"old": "new"}, message="chore(new): rename old to new")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 3, result.stderr)
		self.assertIn("since old-v0.4.0", result.stderr)

	def test_a_plugin_tagged_under_its_new_prefix_ignores_the_renames_map(self) -> None:
		self._renamed("old-v2.4.0", {"old": "new"})
		_git(self.repo, "tag", "new-v3.0.0")
		_commit(self.repo, "new/h", "fix(new): thing")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "new-v3.0.1")

	def _moved_from_elsewhere(self) -> None:
		"""`old` lives at legacy/old, and the marketplace already lists it when old-v2.4.0 is tagged, so its directory can only come from the tagged marketplace (the sibling guess, mp/old, is wrong). A breaking commit under legacy/old follows the tag, then it moves to mp/new."""
		marketplace = self.repo / ".claude-plugin" / "marketplace.json"
		marketplace.parent.mkdir(parents=True, exist_ok=True)
		marketplace.write_text(json.dumps({"plugins": [{"name": "old", "source": "./legacy/old"}]}))
		_commit(self.repo, "legacy/old/f", "feat(old): init")
		_git(self.repo, "tag", "old-v2.4.0")
		_commit(self.repo, "legacy/old/e", "feat(old)!: drop thing")
		(self.repo / "mp").mkdir()
		_git(self.repo, "mv", "legacy/old", "mp/new")
		marketplace.write_text(json.dumps({"plugins": [{"name": "new", "source": "./mp/new"}], "renames": {"old": "new"}}))
		_commit(self.repo, "mp/new/g", "fix(new): move old to new")

	def test_the_old_directory_comes_from_the_marketplace_as_tagged(self) -> None:
		self._moved_from_elsewhere()
		result = _run(self.repo, "--plugin", "new", "--dir", "mp/new")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "new-v3.0.0")

	def test_a_run_from_a_subdirectory_still_scans_the_old_directory(self) -> None:
		self._moved_from_elsewhere()
		result = _run(self.repo / "mp", "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "new-v3.0.0")

	def test_two_tagged_earlier_names_at_one_depth_exit_2_naming_both(self) -> None:
		self._renamed("old-v1.2.0", {"old": "new", "mid": "new"}, message="fix(new): fold old and mid into new")
		_git(self.repo, "tag", "mid-v2.0.0", "HEAD~1")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 2, result.stderr)
		self.assertEqual(result.stdout, "", "no tag is printed while a person has to pick")
		self.assertIn("old-v1.2.0", result.stderr)
		self.assertIn("mid-v2.0.0", result.stderr)

	def test_a_tagged_name_behind_an_untagged_sibling_is_never_dropped(self) -> None:
		# old and b both became new; c became b. old is tagged one hop back, c two hops back behind b
		for c_tag, declared in (("c-v5.0.0", "1.0.0"), ("c-v0.9.0", "0.3.0")):
			with self.subTest(c_tag=c_tag):
				self.tearDown()
				self.setUp()
				self._renamed("old-v0.3.0", {"old": "new", "b": "new", "c": "b"}, declared=declared, message="fix(new): fold old and b into new")
				_git(self.repo, "tag", c_tag, "HEAD~1")
				result = _run(self.repo, "--plugin", "new", "--dir", "new")
				self.assertEqual(result.returncode, 2, result.stderr)
				self.assertEqual(result.stdout, "")
				self.assertIn("old-v0.3.0", result.stderr)
				self.assertIn(c_tag, result.stderr)

	def test_a_fold_below_the_first_level_never_drops_a_tagged_series(self) -> None:
		# b became new; c and d became b; e became d. c is tagged two hops back, e three hops back behind the untagged d
		for c_tag, e_tag, declared in (("c-v1.0.0", "e-v5.0.0", None), ("c-v0.3.0", "e-v2.1.0", "1.0.0")):
			with self.subTest(c_tag=c_tag, e_tag=e_tag):
				self.tearDown()
				self.setUp()
				self._renamed("", {"b": "new", "c": "b", "d": "b", "e": "d"}, declared=declared, message="fix(new): fold into new")
				_git(self.repo, "tag", c_tag, "HEAD~1")
				_git(self.repo, "tag", e_tag, "HEAD~1")
				result = _run(self.repo, "--plugin", "new", "--dir", "new")
				self.assertEqual(result.returncode, 2, result.stderr)
				self.assertEqual(result.stdout, "")
				self.assertIn(c_tag, result.stderr)
				self.assertIn(e_tag, result.stderr)

	def test_a_sibling_plugin_named_with_a_digit_after_the_v_is_refused_not_read_as_a_version(self) -> None:
		# api-v2 is another plugin; its tag api-v2-v0.1.0 matches api-v[0-9]* and svu would read it as 2.0.0
		_commit(self.repo, "api/f", "feat(api): init")
		_git(self.repo, "tag", "api-v0.3.0")
		_commit(self.repo, "api-v2/f", "feat(api-v2): init")
		_git(self.repo, "tag", "api-v2-v0.1.0")
		_commit(self.repo, "api/g", "fix(api): thing")
		result = _run(self.repo, "--plugin", "api", "--dir", "api")
		self.assertEqual(result.returncode, 2, result.stderr)
		self.assertEqual(result.stdout, "")
		self.assertIn("api-v2-v0.1.0", result.stderr)

	def test_a_sibling_named_with_a_digit_after_the_v_is_refused_on_the_rename_path_too(self) -> None:
		self._renamed("old-v0.3.0", {"old": "new"}, message="fix(new): rename old to new")
		_git(self.repo, "tag", "old-v2-v0.1.0")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 2, result.stderr)
		self.assertEqual(result.stdout, "")
		self.assertIn("old-v2-v0.1.0", result.stderr)

	def test_dir_given_as_dot_from_inside_the_plugin_still_finds_the_old_sibling(self) -> None:
		# no marketplace listed old when it was tagged, so its directory is the sibling guess
		self._renamed("old-v2.4.0", {"old": "new"}, message="fix(new): rename old to new", before_rename="feat(old)!: drop thing")
		for given in (".", "./"):
			with self.subTest(given=given):
				result = _run(self.repo / "new", "--plugin", "new", "--dir", given)
				self.assertEqual(result.returncode, 0, result.stderr)
				self.assertEqual(result.stdout.strip(), "new-v3.0.0")

	def test_a_declared_version_that_is_not_three_numbers_exits_2_naming_the_file_and_the_value(self) -> None:
		# printed as a fresh series' tag, p-v0.3 would be refused by the tag-shape check at the very next release
		# a leading zero is not semver; whitespace around the digits is a typo, never nothing declared
		for declared in ("0", "0.3", "0.5", "0.3.0.", "0.03.0", "0.3.00", " 1.0.0", "1.0 "):
			with self.subTest(declared=declared):
				self.tearDown()
				self.setUp()
				_commit(self.repo, "pkg/f", "feat(pkg): init")
				manifest = self.repo / "pkg" / ".claude-plugin" / "plugin.json"
				manifest.parent.mkdir(parents=True)
				manifest.write_text(f'{{\n\t"name": "pkg",\n\t"version": "{declared}"\n}}\n')
				result = _run(self.repo, "--plugin", "pkg", "--dir", "pkg")
				self.assertEqual(result.returncode, 2, result.stderr)
				self.assertEqual(result.stdout, "")
				self.assertIn("plugin.json", result.stderr)
				self.assertIn(f'"{declared}"', result.stderr)

	def test_a_renamed_plugin_declaring_a_two_part_version_exits_2_rather_than_losing_the_warning(self) -> None:
		self._renamed("old-v0.2.0", {"old": "new"}, declared="1.0")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 2, result.stderr)
		self.assertIn('"1.0"', result.stderr)

	def test_a_renamed_plugin_declaring_a_leading_zero_exits_2(self) -> None:
		self._renamed("old-v0.2.0", {"old": "new"}, declared="01.0.0")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 2, result.stderr)
		self.assertIn('"01.0.0"', result.stderr)

	def test_a_series_already_tagged_still_exits_2_on_a_malformed_manifest(self) -> None:
		# the tag would come out right, but the manifest is wrong whatever the series and pr-land would write over it unasked
		_commit(self.repo, "pkg/f", "feat(pkg): init")
		_git(self.repo, "tag", "pkg-v0.2.0")
		manifest = self.repo / "pkg" / ".claude-plugin" / "plugin.json"
		manifest.parent.mkdir(parents=True)
		manifest.write_text('{\n\t"name": "pkg",\n\t"version": "1.0"\n}\n')
		_commit(self.repo, "pkg/g", "fix(pkg): thing")
		result = _run(self.repo, "--plugin", "pkg", "--dir", "pkg")
		self.assertEqual(result.returncode, 2, result.stderr)
		self.assertEqual(result.stdout, "")
		self.assertIn('"1.0"', result.stderr)

	def test_a_declared_pre_release_still_reads_as_nothing_declared(self) -> None:
		# a semver pre-release is a valid version, so it is not refused; it never crosses the guard either
		self._renamed("old-v0.2.0", {"old": "new"}, declared="1.0.0-rc.1")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "new-v0.3.0")

	def test_each_branch_of_the_map_continues_to_its_own_nearest_tag(self) -> None:
		# b is untagged and c, behind it, is the only tagged name: its series goes on
		self._renamed("", {"old": "new", "b": "new", "c": "b"}, message="fix(new): fold old and b into new")
		_git(self.repo, "tag", "c-v2.1.0", "HEAD~1")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "new-v2.1.1")

	def test_a_cycle_in_the_renames_map_ends_and_still_finds_the_tagged_name(self) -> None:
		for renames in ({"old": "new", "new": "old"}, {"old": "new", "new": "mid", "mid": "old"}):
			with self.subTest(renames=renames):
				self.tearDown()
				self.setUp()
				self._renamed("old-v1.2.0", renames, message="fix(new): rename old to new")
				result = _run(self.repo, "--plugin", "new", "--dir", "new")
				self.assertEqual(result.returncode, 0, result.stderr)
				self.assertEqual(result.stdout.strip(), "new-v1.2.1")

	def test_a_sibling_plugin_whose_name_extends_the_old_one_is_not_read_as_its_series(self) -> None:
		self._renamed("old-v2.4.0", {"old": "new"}, message="fix(new): rename old to new")
		_git(self.repo, "tag", "old-viewer-v9.0.0")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "new-v2.4.1")

	def test_a_tag_svu_cannot_read_exits_2_instead_of_reading_as_untagged(self) -> None:
		# svu 3.4.1 passes over some unreadable tags beside a readable one (old-v1.2.3.4) and refuses others (old-v9x)
		for bad in ("old-v9x", "new-v9x"):
			with self.subTest(bad=bad):
				self.tearDown()
				self.setUp()
				self._renamed("old-v2.4.0", {"old": "new"}, message="fix(new): rename old to new")
				_git(self.repo, "tag", bad)
				result = _run(self.repo, "--plugin", "new", "--dir", "new")
				self.assertEqual(result.returncode, 2, result.stderr)
				self.assertEqual(result.stdout, "")
				self.assertIn(bad, result.stderr)

	def test_only_the_top_level_version_counts_as_declared(self) -> None:
		nested = '{\n\t"name": "new",\n\t"dependencies": [\n\t\t{\n\t\t\t"name": "x",\n\t\t\t"version": "1.0.0"\n\t\t}\n\t],\n\t"version": "0.13.1"\n}\n'
		one_line = '{"name": "new", "version": "0.13.1", "engine": {"version": "1.0.0"}}\n'
		for text in (nested, one_line):
			with self.subTest(text=text):
				self.tearDown()
				self.setUp()
				self._renamed("old-v0.13.1", {"old": "new"}, manifest_text=text)
				result = _run(self.repo, "--plugin", "new", "--dir", "new")
				self.assertEqual(result.returncode, 0, result.stderr)
				self.assertEqual(result.stdout.strip(), "new-v0.14.0")
				self.assertIn("guard:", result.stderr)

	def test_a_renamed_plugin_whose_manifest_disagrees_with_the_series_says_so(self) -> None:
		self._renamed("old-v2.4.0", {"old": "new"}, declared="3.0.0", message="chore(new): rename old to new", before_rename="feat(old): thing")
		result = _run(self.repo, "--plugin", "new", "--dir", "new")
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "new-v2.5.0")
		self.assertIn("declares 3.0.0", result.stderr)


if __name__ == "__main__":
	unittest.main()
