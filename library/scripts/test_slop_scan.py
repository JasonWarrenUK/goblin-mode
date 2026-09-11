#!/usr/bin/env python3
"""Tests for slop-scan.py: strict gate mode, stdin, masking and the report path.

Run from this directory: python3 -m unittest test_slop_scan -v
(or python3 -m pytest test_slop_scan.py). Stdlib only.
"""
from __future__ import annotations

import importlib.util
import io
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "slop-scan.py"

spec = importlib.util.spec_from_file_location("slop_scan", SCRIPT)
slop_scan = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(slop_scan)


def run_strict(text: str) -> tuple[int, str]:
	"""Run strict mode over `text` in-process; return (exit status, stdout)."""
	buffer = io.StringIO()
	with redirect_stdout(buffer):
		status = slop_scan.strict("<test>", text, ".txt", prefix=False)
	return status, buffer.getvalue()


class StrictExitCodes(unittest.TestCase):
	def test_clean_text_exits_zero(self):
		status, out = run_strict("fix: tidy the parser again\n")
		self.assertEqual(status, 0)
		self.assertEqual(out, "")

	def test_em_dash_exits_one_with_one_line(self):
		status, out = run_strict("fix: tidy — again\n")
		self.assertEqual(status, 1)
		self.assertEqual(out.splitlines(), ["L1 em dash: fix: tidy — again"])

	def test_spelling_hit_names_the_token(self):
		status, out = run_strict("chore: the color of the badge\n")
		self.assertEqual(status, 1)
		self.assertIn("L1 American -or 'color':", out)

	def test_line_numbers_survive_blank_lines(self):
		status, out = run_strict("feat: thing\n\nBody line one.\nBody with an — dash.\n")
		self.assertEqual(status, 1)
		self.assertTrue(out.startswith("L4 em dash:"))


class StrictMasking(unittest.TestCase):
	def test_css_property_is_masked(self):
		self.assertEqual(run_strict("fix: background-color on Card\n")[0], 0)

	def test_media_query_is_masked(self):
		self.assertEqual(run_strict("fix: honour prefers-color-scheme\n")[0], 0)

	def test_branch_name_is_masked(self):
		self.assertEqual(run_strict("merge feat/colorize into main\n")[0], 0)

	def test_file_path_is_masked(self):
		self.assertEqual(run_strict("move src/lib/Color.svelte\n")[0], 0)

	def test_bare_identifier_still_caught(self):
		status, out = run_strict("call colorize() before render\n")
		self.assertEqual(status, 1)
		self.assertIn("'colorize'", out)

	def test_british_towards_is_not_american_usage(self):
		self.assertEqual(run_strict("lean towards the simpler fix\n")[0], 0)
		self.assertEqual(run_strict("lean toward the simpler fix\n")[0], 1)

	def test_inline_code_is_masked(self):
		self.assertEqual(run_strict("rename `optimize` to `optimise`\n")[0], 0)

	def test_url_is_masked(self):
		self.assertEqual(run_strict("see https://example.com/color/theater\n")[0], 0)

	def test_fenced_block_is_skipped(self):
		text = "docs: example\n\n```\ncolor: red; — inside a fence\n```\n"
		self.assertEqual(run_strict(text)[0], 0)

	def test_prose_after_fence_is_still_scanned(self):
		text = "docs: example\n\n```\nx\n```\nthe color outside\n"
		status, out = run_strict(text)
		self.assertEqual(status, 1)
		self.assertTrue(out.startswith("L6 "))


class StrictQuoting(unittest.TestCase):
	def test_blockquote_line_is_skipped(self):
		self.assertEqual(run_strict("docs: note\n\n> quoted — with a dash\n")[0], 0)

	def test_scanner_output_line_is_skipped(self):
		self.assertEqual(run_strict("the hook said:\nL1 em dash: fix: tidy — again\n")[0], 0)

	def test_scanner_output_with_path_prefix_is_skipped(self):
		self.assertEqual(run_strict("skills/x/SKILL.md:L4 American -or 'color': the color of it\n")[0], 0)

	def test_double_quoted_span_is_masked(self):
		self.assertEqual(run_strict('rename the "Color — Picker" dialog\n')[0], 0)

	def test_curly_quoted_span_is_masked(self):
		self.assertEqual(run_strict("rename the “Color — Picker” dialog\n")[0], 0)

	def test_text_outside_quotes_still_caught(self):
		status, out = run_strict('the "quoted — bit" and a real — dash\n')
		self.assertEqual(status, 1)
		self.assertEqual(len(out.splitlines()), 1)

	def test_unbalanced_quote_masks_only_its_own_line(self):
		status, out = run_strict('he said "no — way\nnext line has a real — dash\n')
		self.assertEqual(status, 1)
		self.assertTrue(out.startswith("L2 "))

	def test_apostrophes_do_not_mask(self):
		self.assertEqual(run_strict("it's the color of Jason's badge\n")[0], 1)


class OxfordComma(unittest.TestCase):
	def hits(self, text: str) -> list[str]:
		found = slop_scan.scan_group([(1, text)], slop_scan.HOUSE_RULES, None)
		return [label for label, _, _ in found]

	def test_plain_oxford_comma_is_caught(self):
		self.assertIn("Oxford comma", self.hits("adds a, b, and c"))

	def test_versions_with_dots_are_caught(self):
		self.assertIn("Oxford comma", self.hits("supports v1.2, v1.3, and v1.4"))

	def test_does_not_cross_a_full_stop(self):
		self.assertNotIn("Oxford comma", self.hits("Fixed foo, bar. Then baz, and qux"))

	def test_does_not_cross_a_colon(self):
		self.assertNotIn("Oxford comma", self.hits("x, y: z, and w"))

	def test_compound_clause_is_a_known_false_positive(self):
		# Not a list: the comma joins two independent clauses. The pattern
		# cannot tell the difference; pinned so a regex change is deliberate.
		self.assertIn("Oxford comma", self.hits("After the merge, we tag the release, and the changelog regenerates."))


class BorrowedWeight(unittest.TestCase):
	def labels(self, text: str) -> list[str]:
		found = slop_scan.scan_group([(1, text)], slop_scan.BORROWED_WEIGHT, None)
		return [label for label, _, _ in found]

	def test_participial_tail(self):
		self.assertIn("participial tail", self.labels("Tests passed, highlighting the value of CI."))

	def test_borrowed_authority(self):
		self.assertIn("borrowed authority", self.labels("Experts say this is fine."))
		self.assertIn("borrowed authority", self.labels("It is widely regarded as safe."))

	def test_significance_inflation(self):
		self.assertIn("significance inflation", self.labels("A pivotal moment for the team."))

	def test_chatbot_residue(self):
		self.assertIn("chatbot residue", self.labels("I hope this helps! Let me know if you need more."))

	def test_borrowed_weight_is_not_a_house_rule(self):
		self.assertEqual(run_strict("Experts say it was pivotal, highlighting the shift.\n")[0], 0)


class ReportMode(unittest.TestCase):
	def test_report_prints_name_and_groups(self):
		buffer = io.StringIO()
		with redirect_stdout(buffer):
			slop_scan.report("sample.md", "A robust plan — really.\n", ".md", 6, 8)
		out = buffer.getvalue()
		self.assertIn("sample.md", out)
		self.assertIn("## House-rule breaches  (1)", out)
		self.assertIn("## LLM lexicon", out)

	def test_house_only_drops_other_groups(self):
		buffer = io.StringIO()
		with redirect_stdout(buffer):
			slop_scan.report("sample.md", "A robust plan — really.\n", ".md", 6, 8, house_only=True)
		out = buffer.getvalue()
		self.assertIn("## House-rule breaches", out)
		self.assertNotIn("## LLM lexicon", out)


class CommandLine(unittest.TestCase):
	def run_cli(self, *args: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
		return subprocess.run(
			[sys.executable, str(SCRIPT), *args],
			input=stdin,
			capture_output=True,
			text=True,
		)

	def test_stdin_strict_exit_one(self):
		result = self.run_cli("--strict", "-", stdin="fix: tidy — again\n")
		self.assertEqual(result.returncode, 1)
		self.assertEqual(result.stdout.strip(), "L1 em dash: fix: tidy — again")

	def test_stdin_strict_exit_zero(self):
		result = self.run_cli("--strict", "-", stdin="fix: background-color on Card\n")
		self.assertEqual(result.returncode, 0)
		self.assertEqual(result.stdout, "")

	def test_missing_file_still_errors(self):
		result = self.run_cli("--strict", "/nonexistent/file.md")
		self.assertEqual(result.returncode, 1)
		self.assertIn("not a file", result.stderr)

	def test_multiple_targets_prefix_names(self):
		result = self.run_cli("--strict", str(HERE / "test_slop_scan.py"), "-", stdin="a — b\n")
		self.assertEqual(result.returncode, 1)
		self.assertIn("<stdin>:L1 em dash:", result.stdout)


if __name__ == "__main__":
	unittest.main()
