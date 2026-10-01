#!/usr/bin/env python3
"""Tests for md-lint.py: each typography rule, the clean template and hook mode.

Run from this directory: python3 -m unittest test_md_lint -v
(or python3 -m pytest test_md_lint.py). Stdlib only.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "md-lint.py"
TEMPLATE = HERE.parent / "templates" / "pr-description.md"

spec = importlib.util.spec_from_file_location("md_lint", SCRIPT)
md_lint = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(md_lint)


def rules(text: str) -> list[str]:
	return [rule for _, rule, _ in md_lint.lint(text)]


def run_hook(command: str, cwd: str = ".") -> subprocess.CompletedProcess[str]:
	payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd})
	return subprocess.run([sys.executable, str(SCRIPT), "--hook"], input=payload, capture_output=True, text=True)


class Setext(unittest.TestCase):
	def test_rule_under_paragraph_is_flagged(self):
		# PR #139: "Not checked: ..." became an h2
		self.assertEqual(rules("Not checked: the buttons.\n---\n## Changes\n"), ["setext"])

	def test_rule_after_blank_line_is_clean(self):
		self.assertEqual(rules("Not checked: the buttons.\n\n---\n\n## Changes\n"), [])

	def test_rule_under_heading_is_clean(self):
		self.assertEqual(rules("## Changes\n---\n"), [])

	def test_rule_under_list_is_clean(self):
		self.assertEqual(rules("- one\n- two\n---\n"), [])

	def test_equals_underline_is_flagged(self):
		self.assertEqual(rules("Title\n===\n"), ["setext"])


class HtmlTail(unittest.TestCase):
	def test_rule_after_closing_details_is_flagged(self):
		# PR #26 and #139: a literal --- before Update history
		self.assertEqual(rules("<details>\n<summary>Docs</summary>\n\n- a\n</details>\n---\n"), ["html-tail"])

	def test_blank_line_after_closing_details_is_clean(self):
		self.assertEqual(rules("<details>\n<summary>Docs</summary>\n\n- a\n\n</details>\n\n---\n"), [])

	def test_summary_gap_is_flagged(self):
		self.assertEqual(rules("<details>\n<summary>Docs</summary>\n- a\n\n</details>\n"), ["summary-gap"])

	def test_comment_after_closing_details_is_clean(self):
		self.assertEqual(rules("<details>\n<summary>x</summary>\n\n- a\n\n</details>\n<!-- pr-update-watermark: abc -->\n"), [])

	def test_inline_tag_leading_prose_is_clean(self):
		# GitHub renders both as one paragraph
		self.assertEqual(rules("<code>x</code> does y\nsecond line\n"), [])
		self.assertEqual(rules("<b>Note:</b> text\nmore\n"), [])

	def test_lone_tag_swallows_next_line(self):
		# CommonMark type 7: GitHub prints "Caption *em*" raw
		self.assertEqual(rules('<img src="a.png">\nCaption\n'), ["html-tail"])

	def test_one_hit_per_block(self):
		self.assertEqual(rules("</details>\nfirst\nsecond\n"), ["html-tail"])


class Summary(unittest.TestCase):
	def test_backticks_in_summary_are_flagged(self):
		self.assertIn("summary-backtick", rules("<details>\n<summary>Seed (`supabase/`)</summary>\n\n</details>\n"))

	def test_code_tag_in_summary_is_clean(self):
		self.assertEqual(rules("<details>\n<summary>Seed (<code>supabase/</code>)</summary>\n\n- a\n\n</details>\n"), [])


class DoubleRule(unittest.TestCase):
	def test_adjacent_rules_are_flagged(self):
		self.assertEqual(rules("text\n\n---\n\n---\n\n## Changes\n"), ["double-rule"])

	def test_rules_with_content_between_are_clean(self):
		self.assertEqual(rules("text\n\n---\n\n## Changes\n\nmore\n\n---\n"), [])


class Fences(unittest.TestCase):
	def test_fenced_content_is_skipped(self):
		self.assertEqual(rules("```markdown\ntext\n---\n</details>\nraw\n```\n"), [])


class Template(unittest.TestCase):
	def test_template_is_clean(self):
		self.assertEqual(md_lint.lint(TEMPLATE.read_text(encoding="utf-8")), [])


class Hook(unittest.TestCase):
	BAD = "## Overview\n\nText.\n---\n"
	GOOD = "## Overview\n\nText.\n\n---\n"

	def test_bad_heredoc_body_blocks(self):
		result = run_hook(f"gh pr create --base main --title \"T\" --body-file - <<'PR_EOF'\n{self.BAD}PR_EOF")
		self.assertEqual(result.returncode, 2)
		self.assertIn("setext", result.stderr)

	def test_good_heredoc_body_passes(self):
		result = run_hook(f"gh pr edit 5 --body-file - <<'PR_EOF'\n{self.GOOD}PR_EOF")
		self.assertEqual(result.returncode, 0)

	def test_no_body_flag_passes(self):
		self.assertEqual(run_hook("gh pr edit 5 --add-label bug").returncode, 0)

	def test_other_command_passes(self):
		self.assertEqual(run_hook("git status").returncode, 0)

	def test_inline_body_is_linted(self):
		self.assertEqual(run_hook('gh pr edit 5 --body "Text.\n---"').returncode, 2)

	def test_body_file_path_is_read(self):
		with tempfile.TemporaryDirectory() as directory:
			Path(directory, "body.md").write_text(self.BAD, encoding="utf-8")
			self.assertEqual(run_hook("gh pr create --body-file body.md", cwd=directory).returncode, 2)

	def test_gh_command_inside_another_heredoc_passes(self):
		command = f"cat > prompt.txt <<'EOF'\ngh pr edit 1 --body-file - <<'PR_EOF'\n{self.BAD}PR_EOF\nEOF"
		self.assertEqual(run_hook(command).returncode, 0)

	def test_garbage_payload_fails_open(self):
		result = subprocess.run([sys.executable, str(SCRIPT), "--hook"], input="not json", capture_output=True, text=True)
		self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
	unittest.main()
