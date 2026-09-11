#!/usr/bin/env python3
"""Tests for prose-metrics.py: transcript aggregation, masking and recording.

Run from this directory: python3 -m unittest test_prose_metrics -v
(or python3 -m pytest test_prose_metrics.py). Stdlib only.
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
SCRIPT = HERE / "prose-metrics.py"

spec = importlib.util.spec_from_file_location("prose_metrics", SCRIPT)
prose_metrics = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(prose_metrics)


def entry(day: str, text: str, kind: str = "assistant", sidechain: bool = False) -> str:
	return json.dumps({
		"type": kind,
		"isSidechain": sidechain,
		"timestamp": f"{day}T12:00:00.000Z",
		"message": {"content": [{"type": "text", "text": text}]},
	})


class Aggregation(unittest.TestCase):
	def setUp(self):
		self.tmp = tempfile.TemporaryDirectory()
		self.root = Path(self.tmp.name) / "projects"
		(self.root / "p1").mkdir(parents=True)
		lines = [
			entry("2026-09-01", "one two three — four"),
			entry("2026-09-01", "colors here, and `background-color` there"),
			entry("2026-09-02", "clean words only"),
			entry("2026-09-02", "user text — ignored", kind="user"),
			entry("2026-09-02", "subagent — ignored", sidechain=True),
			"not json at all",
		]
		(self.root / "p1" / "s.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

	def tearDown(self):
		self.tmp.cleanup()

	def test_counts_assistant_text_only(self):
		rows = prose_metrics.scan_transcripts(self.root, "2026-01-01")
		self.assertEqual(set(rows), {"2026-09-01", "2026-09-02"})
		self.assertEqual(rows["2026-09-01"]["msgs"], 2)
		self.assertEqual(rows["2026-09-02"]["msgs"], 1)

	def test_em_dash_and_spelling_counted_code_masked(self):
		rows = prose_metrics.scan_transcripts(self.root, "2026-01-01")
		day = rows["2026-09-01"]
		self.assertEqual(day["emdash"], 1)
		self.assertEqual(day["amer_or"], 1)  # "colors", not the masked CSS property

	def test_since_filters_days(self):
		rows = prose_metrics.scan_transcripts(self.root, "2026-09-02")
		self.assertEqual(set(rows), {"2026-09-02"})

	def test_merge_prefers_fuller_fresh_rows(self):
		history = {"2026-09-01": {**prose_metrics.empty_row(), "words": 500}, "2026-08-01": {**prose_metrics.empty_row(), "words": 9}}
		fresh = {"2026-09-01": {**prose_metrics.empty_row(), "words": 12}}
		merged = prose_metrics.merge(history, fresh)
		self.assertEqual(merged["2026-09-01"]["words"], 500)  # pruned transcript loses to recorded history
		self.assertEqual(merged["2026-08-01"]["words"], 9)

	def test_record_writes_state_and_cli_renders(self):
		state = Path(self.tmp.name) / "state.json"
		result = subprocess.run(
			[sys.executable, str(SCRIPT), "--since", "2026-01-01", "--record", "--projects", str(self.root), "--state", str(state)],
			capture_output=True, text=True,
		)
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertIn("2026-09-01", result.stdout)
		self.assertIn("emdash/1k", result.stdout)
		saved = json.loads(state.read_text())
		self.assertEqual(saved["2026-09-01"]["emdash"], 1)


if __name__ == "__main__":
	unittest.main()
