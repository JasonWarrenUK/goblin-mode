#!/usr/bin/env python3
"""Tests for gh-guard.py: inline bodies, body files, heredocs and release notes.

Run from this directory: python3 -m unittest test_gh_guard -v
(or python3 -m pytest test_gh_guard.py). Stdlib only.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "gh-guard.py"

spec = importlib.util.spec_from_file_location("gh_guard", SCRIPT)
gh_guard = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(gh_guard)


def reason(command: str, cwd: str = ".") -> str | None:
	return gh_guard.check_command(command, cwd)


def run_hook(command: str, cwd: str = ".") -> subprocess.CompletedProcess[str]:
	payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd})
	return subprocess.run([sys.executable, str(SCRIPT), "--hook"], input=payload, capture_output=True, text=True)


class InlineBodies(unittest.TestCase):
	def test_gh_api_raw_field_body_is_blocked(self):
		self.assertIn("inline `-f body=", reason("gh api --method POST repos/o/r/pulls/1/comments/2/replies -f body='Fixed in abc'"))

	def test_gh_api_field_body_inline_is_blocked(self):
		self.assertIn("inline `-F body=", reason("gh api repos/o/r/issues/1/comments -F body='hello'"))

	def test_gh_api_field_body_from_file_passes(self):
		self.assertIsNone(reason("gh api --method POST repos/o/r/pulls/1/comments/2/replies -F body=@/tmp/reply.md"))

	def test_gh_api_raw_field_at_file_is_blocked_with_the_fix(self):
		self.assertIn("use `-F body=@<file>`", reason("gh api repos/o/r/issues/1/comments -f body=@reply.md"))

	def test_gh_api_without_a_body_is_ignored(self):
		self.assertIsNone(reason("gh api graphql -f query='query { viewer { login } }' -F pr=12"))
		self.assertIsNone(reason("gh api repos/o/r/pulls/1/reviews --input -"))

	def test_gh_pr_comment_inline_body_is_blocked(self):
		self.assertIn("inline `--body`", reason("gh pr comment 12 --body 'Thanks, fixed'"))
		self.assertIn("inline `-b`", reason("gh pr comment 12 -b 'Thanks, fixed'"))
		self.assertIn("inline `--body`", reason("gh pr comment 12 --body='Thanks'"))

	def test_gh_pr_review_and_issue_comment_inline_bodies_are_blocked(self):
		self.assertIn("gh pr review", reason("gh pr review 12 --comment -b 'looks fine'"))
		self.assertIn("gh issue comment", reason("gh issue comment 3 --body 'done'"))

	def test_body_file_passes(self):
		self.assertIsNone(reason("gh pr comment 12 --body-file ./scratch/reply.md"))
		self.assertIsNone(reason("gh pr review 12 --approve -F notes.md"))

	def test_heredoc_on_stdin_passes(self):
		self.assertIsNone(reason("gh pr comment 12 --body-file - <<'EOF'\nIt's fixed in abc123.\nEOF"))
		self.assertIsNone(reason("gh api --method POST repos/o/r/pulls/1/reviews --input - <<'JSON'\n{\"body\": \"it's\"}\nJSON"))

	def test_a_gh_call_quoted_inside_a_heredoc_is_not_a_call(self):
		command = "cat > notes.md <<'EOF'\nRun: gh pr comment 12 --body 'x'\nEOF"
		self.assertIsNone(reason(command))

	def test_review_without_a_body_passes(self):
		self.assertIsNone(reason("gh pr review 12 --approve"))

	def test_api_body_file_is_never_read(self):
		self.assertIsNone(reason('gh api repos/o/r/issues/1/comments -F body=@"$F"'))
		self.assertIsNone(reason("gh api repos/o/r/issues/1/comments -F body=@nonexistent.md"))

	def test_quoted_mention_is_not_a_call(self):
		self.assertIsNone(reason("echo 'gh pr comment 12 --body x' it's"))
		self.assertIsNone(reason('grep -rn "gh pr comment --body" skills'))

	def test_real_call_before_a_quoted_mention_is_still_checked(self):
		self.assertIn("inline `--body`", reason("gh pr comment 12 --body 'hi' && echo 'gh pr comment 13'"))

	def test_assignment_and_cd_prefixes_are_still_calls(self):
		self.assertIn("inline `--body`", reason("FOO=1 gh pr comment 12 --body 'hi'"))
		self.assertIn("inline `--body`", reason("cd x && gh pr comment 12 --body 'hi'"))


class ReleaseNotes(unittest.TestCase):
	def setUp(self):
		self.tmp = tempfile.TemporaryDirectory()
		self.dir = Path(self.tmp.name)
		(self.dir / "empty.md").write_text("\n\n")
		(self.dir / "notes.md").write_text("## 1.2.0\n\n- Added a thing\n")

	def tearDown(self):
		self.tmp.cleanup()

	def test_create_with_no_notes_source_is_blocked(self):
		self.assertIn("no notes source", reason("gh release create v1.2.0 --title v1.2.0"))

	def test_create_with_inline_notes_is_blocked(self):
		self.assertIn("inline `--notes`", reason("gh release create v1.2.0 --notes 'first cut'"))
		self.assertIn("inline `-n`", reason("gh release create v1.2.0 -n 'first cut'"))

	def test_create_with_an_empty_notes_file_is_blocked(self):
		self.assertIn("missing or empty", reason("gh release create v1.2.0 --notes-file empty.md", cwd=str(self.dir)))
		self.assertIn("missing or empty", reason(f"gh release create v1.2.0 -F {self.dir / 'absent.md'}"))

	def test_create_with_a_non_empty_notes_file_passes(self):
		self.assertIsNone(reason("gh release create v1.2.0 --notes-file notes.md", cwd=str(self.dir)))
		self.assertIsNone(reason(f"gh release create v1.2.0 --title v1.2.0 -F {self.dir / 'notes.md'}"))

	def test_create_with_a_heredoc_passes_only_when_it_has_text(self):
		self.assertIsNone(reason("gh release create v1.2.0 --notes-file - <<'EOF'\n## 1.2.0\n\n- a thing\nEOF"))
		self.assertIn("heredoc is blank", reason("gh release create v1.2.0 --notes-file - <<'EOF'\n\nEOF"))

	def test_generated_notes_pass(self):
		self.assertIsNone(reason("gh release create v1.2.0 --generate-notes"))
		self.assertIsNone(reason("gh release create v1.2.0 --notes-from-tag"))

	def test_unevaluable_notes_path_fails_open(self):
		self.assertIsNone(reason('gh release create "$TAG" --notes-file "$TAG.md"', cwd=str(self.dir)))
		self.assertIsNone(reason('N=notes.md; gh release create v1 --notes-file "$N"', cwd=str(self.dir)))
		self.assertIsNone(reason("gh release create v1 --notes-file `cat path`", cwd=str(self.dir)))

	def test_file_written_earlier_in_the_command_fails_open(self):
		self.assertIsNone(reason("python3 cut.py > rn.md && gh release create v1 --notes-file rn.md", cwd=str(self.dir)))

	def test_a_stderr_redirect_earlier_on_the_line_keeps_the_empty_check_live(self):
		self.assertIn("missing or empty", reason(f"some-check 2>/dev/null && gh release create v1 --notes-file {self.dir / 'empty.md'}"))
		self.assertIn("missing or empty", reason(f"some-check 2>&1 | tee log; gh release create v1 --notes-file {self.dir / 'empty.md'}"))

	def test_cd_before_the_call_fails_open(self):
		self.assertIsNone(reason(f"cd {self.dir} && gh release create v1 --notes-file absent.md"))

	def test_literal_empty_file_still_blocks(self):
		self.assertIn("missing or empty", reason(f"gh release create v1 --notes-file {self.dir / 'empty.md'}"))
		self.assertIn("missing or empty", reason("echo start && gh release create v1 --notes-file absent.md", cwd=str(self.dir)))

	def test_quoted_mention_is_not_a_call(self):
		self.assertIsNone(reason("echo 'gh release create v1' it's"))
		self.assertIsNone(reason("python3 t.py --command 'gh release create v1 --title x' --reason 'a' 'b' --n it's"))

	def test_real_call_before_a_quoted_mention_is_still_checked(self):
		self.assertIn("missing or empty", reason("gh release create v1 --notes-file absent.md && echo 'gh release create v2'", cwd=str(self.dir)))

	def test_edit_rules(self):
		self.assertIsNone(reason("gh release edit v1.2.0 --title 'v1.2.0'"))
		self.assertIn("inline `--notes`", reason("gh release edit v1.2.0 --notes 'fixed'"))
		self.assertIn("missing or empty", reason("gh release edit v1.2.0 --notes-file empty.md", cwd=str(self.dir)))
		self.assertIsNone(reason("gh release edit v1.2.0 --notes-file notes.md", cwd=str(self.dir)))


class HookMode(unittest.TestCase):
	def test_blocked_call_exits_2_with_the_reason_on_stderr(self):
		done = run_hook("gh pr comment 12 --body 'hi'")
		self.assertEqual(done.returncode, 2)
		self.assertTrue(done.stderr.startswith("gh-guard: "))

	def test_clean_call_exits_0(self):
		self.assertEqual(run_hook("gh pr comment 12 --body-file reply.md").returncode, 0)

	def test_unrelated_command_exits_0(self):
		self.assertEqual(run_hook("git status").returncode, 0)

	def test_unparseable_payload_fails_open(self):
		done = subprocess.run([sys.executable, str(SCRIPT), "--hook"], input="not json", capture_output=True, text=True)
		self.assertEqual(done.returncode, 0)

	def test_command_mode(self):
		done = subprocess.run([sys.executable, str(SCRIPT), "--command", "gh release create v1 --title v1"], capture_output=True, text=True)
		self.assertEqual(done.returncode, 2)
		self.assertIn("no notes source", done.stderr)


if __name__ == "__main__":
	unittest.main()
