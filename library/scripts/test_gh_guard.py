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
