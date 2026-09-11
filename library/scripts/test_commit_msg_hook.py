#!/usr/bin/env python3
"""Tests for hooks/commit-msg: what it scans, what it blanks and how it exits.

Drives the hook as a subprocess over fixture messages, the way git would.
Run from this directory: python3 -m unittest test_commit_msg_hook -v
(or python3 -m pytest test_commit_msg_hook.py). Stdlib only.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOK = HERE.parent.parent / "hooks" / "commit-msg"


class HookCase(unittest.TestCase):
	"""One temp directory per test; git sees no global or system config."""

	def setUp(self):
		self.tmp = Path(tempfile.mkdtemp())
		self.empty_config = self.tmp / "gitconfig"
		self.empty_config.write_text("", encoding="utf-8")

	def tearDown(self):
		shutil.rmtree(self.tmp, ignore_errors=True)

	def env(self, **extra: str) -> dict[str, str]:
		base = {
			**os.environ,
			"SLOP_NO_LOG": "1",
			"GIT_CONFIG_GLOBAL": str(self.empty_config),
			"GIT_CONFIG_NOSYSTEM": "1",
		}
		base.update(extra)
		return base

	def run_hook(self, message: str, cwd: Path | None = None, **extra: str) -> subprocess.CompletedProcess[str]:
		path = self.tmp / "COMMIT_EDITMSG"
		path.write_text(message, encoding="utf-8")
		return subprocess.run(
			["/bin/sh", str(HOOK), str(path)],
			cwd=cwd or self.tmp,
			env=self.env(**extra),
			capture_output=True,
			text=True,
		)

	def init_repo(self) -> Path:
		repo = self.tmp / "repo"
		repo.mkdir()
		subprocess.run(["git", "init", "-q", str(repo)], env=self.env(), check=True)
		return repo

	def assertRejected(self, result: subprocess.CompletedProcess[str], *needles: str) -> None:
		self.assertEqual(result.returncode, 1, result.stderr)
		for needle in needles:
			self.assertIn(needle, result.stderr)

	def assertPassed(self, result: subprocess.CompletedProcess[str]) -> None:
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stderr, "")


class Rejection(HookCase):
	def test_em_dash_in_body_rejects_with_line_number(self):
		result = self.run_hook("feat: add thing\n\nThis is a body — with an em dash.\n")
		self.assertRejected(result, "  L3 em dash:", "do not use --no-verify")

	def test_clean_message_passes(self):
		self.assertPassed(self.run_hook("feat: add thing\n\nA plain body.\n"))

	def test_line_numbers_match_commit_editmsg_after_blanked_lines(self):
		result = self.run_hook("feat: x\n\n# comment\n# comment\nBody with — dash on line 5\n")
		self.assertRejected(result, "  L5 em dash:")

	def test_every_breach_gets_its_own_line(self):
		result = self.run_hook("feat: x\n\none, two, and three\n\nand a — dash\n")
		self.assertRejected(result, "  L3 Oxford comma:", "  L5 em dash:")


class BlankedLines(HookCase):
	def test_comment_lines_are_not_scanned(self):
		self.assertPassed(self.run_hook("feat: x\n\n# comment — with em dash\n"))

	def test_custom_comment_char_is_honoured(self):
		repo = self.init_repo()
		subprocess.run(["git", "config", "core.commentChar", ";"], cwd=repo, env=self.env(), check=True)
		self.assertPassed(self.run_hook("feat: x\n\n; comment — with em dash\n", cwd=repo))
		self.assertRejected(self.run_hook("feat: x\n\n# no longer — a comment\n", cwd=repo), "  L3 em dash:")

	def test_scissors_diff_is_not_scanned(self):
		message = "feat: x\n\n# ------------------------ >8 ------------------------\ndiff --git a/x b/x\n-old — line\n"
		self.assertPassed(self.run_hook(message))

	def test_git_generated_subjects_are_not_scanned(self):
		for subject in ('Merge branch "feat/x — y"', 'Revert "feat: thing — here"', "fixup! feat: thing — here"):
			with self.subTest(subject=subject):
				self.assertPassed(self.run_hook(subject + "\n"))

	def test_revert_boilerplate_is_not_scanned(self):
		self.assertPassed(self.run_hook('Revert "feat: x"\n\nThis reverts commit abc123 — dashed.\n'))

	def test_indented_quoted_material_is_not_scanned(self):
		self.assertPassed(self.run_hook("feat: x\n\n    quoted — with em dash\n\tand — tabbed\n"))


class Trailers(HookCase):
	def test_known_trailer_keys_are_not_scanned(self):
		message = "feat: x\n\nbody\n\nCo-authored-by: Someone — Else <a@b.c>\nRefs: #12 — see\n"
		self.assertPassed(self.run_hook(message))

	def test_trailer_keys_match_case_insensitively(self):
		self.assertPassed(self.run_hook("feat: x\n\nbody\n\nCo-Authored-By: Someone — Else <a@b.c>\n"))

	def test_continuation_lines_belong_to_the_trailer(self):
		self.assertPassed(self.run_hook("feat: x\n\nbody\n\nCo-authored-by: A —\n  continued — line\n"))

	def test_final_prose_paragraph_with_a_label_is_scanned(self):
		self.assertRejected(self.run_hook("feat: x\n\nbody\n\nNote: em dash — here\n"), "  L5 em dash:")

	def test_mixed_block_is_scanned_whole(self):
		message = "feat: x\n\nbody\n\nCo-authored-by: A <a@b.c>\nNote: em dash — here\n"
		self.assertRejected(self.run_hook(message), "  L6 em dash:")

	def test_breaking_change_footer_is_scanned(self):
		for footer in ("BREAKING CHANGE", "BREAKING-CHANGE"):
			with self.subTest(footer=footer):
				result = self.run_hook(f"feat!: x\n\nbody\n\n{footer}: the API — changed\n")
				self.assertRejected(result, "  L5 em dash:")


class RepoConfig(HookCase):
	def test_opt_out_skips_the_scan(self):
		repo = self.init_repo()
		subprocess.run(["git", "config", "slop.commitMsg", "off"], cwd=repo, env=self.env(), check=True)
		self.assertPassed(self.run_hook("feat: x — y\n", cwd=repo))

	def test_delegates_to_the_repo_hook_with_the_message_path(self):
		repo = self.init_repo()
		scripts = repo / "scripts"
		scripts.mkdir()
		inner = scripts / "commit-msg"
		inner.write_text('#!/bin/sh\nprintf "%s" "$1" > "$(dirname "$0")/seen"\nexit 3\n', encoding="utf-8")
		inner.chmod(inner.stat().st_mode | stat.S_IXUSR)
		result = self.run_hook("feat: clean\n", cwd=repo)
		self.assertEqual(result.returncode, 3)
		self.assertEqual((scripts / "seen").read_text(encoding="utf-8"), str(self.tmp / "COMMIT_EDITMSG"))

	def test_rejection_happens_before_delegation(self):
		repo = self.init_repo()
		scripts = repo / "scripts"
		scripts.mkdir()
		inner = scripts / "commit-msg"
		inner.write_text("#!/bin/sh\ntouch \"$(dirname \"$0\")/seen\"\n", encoding="utf-8")
		inner.chmod(inner.stat().st_mode | stat.S_IXUSR)
		self.assertRejected(self.run_hook("feat: x — y\n", cwd=repo), "  L1 em dash:")
		self.assertFalse((scripts / "seen").exists())

	def test_non_executable_repo_hook_is_ignored(self):
		repo = self.init_repo()
		(repo / "scripts").mkdir()
		(repo / "scripts" / "commit-msg").write_text("#!/bin/sh\nexit 3\n", encoding="utf-8")
		self.assertPassed(self.run_hook("feat: clean\n", cwd=repo))


class FailOpen(HookCase):
	def test_missing_python3_never_blocks(self):
		bin_dir = self.tmp / "bin"
		bin_dir.mkdir()
		for tool in ("git", "awk"):
			found = shutil.which(tool)
			self.assertIsNotNone(found, f"{tool} not on PATH")
			(bin_dir / tool).symlink_to(found)
		self.assertPassed(self.run_hook("feat: x — y\n", PATH=str(bin_dir)))


class Logging(HookCase):
	def test_each_run_appends_one_json_line(self):
		home = self.tmp / "home"
		state = home / ".claude" / "library" / "state"
		state.mkdir(parents=True)
		self.run_hook("feat: x — y, one, two, and three\n", HOME=str(home), SLOP_NO_LOG="")
		self.run_hook("feat: clean\n", HOME=str(home), SLOP_NO_LOG="")
		lines = (state / "commit-msg-log.jsonl").read_text(encoding="utf-8").splitlines()
		self.assertEqual(len(lines), 2)
		reject, passed = (json.loads(line) for line in lines)
		self.assertEqual(reject["result"], "reject")
		self.assertEqual(set(reject["rules"].split("|")), {"em dash", "Oxford comma"})
		self.assertEqual(passed["result"], "pass")
		self.assertEqual(passed["rules"], "")
		self.assertTrue(reject["ts"].endswith("Z"))


if __name__ == "__main__":
	unittest.main()
