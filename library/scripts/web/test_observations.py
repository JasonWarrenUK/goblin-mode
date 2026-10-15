#!/usr/bin/env python3
"""Tests for observations.py: export assembly, contract faults, status verdicts, add.

Run from this directory: python3 -m unittest test_observations -v
(or python3 -m pytest test_observations.py). Stdlib only.
"""
from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "observations.py"

spec = importlib.util.spec_from_file_location("observations", SCRIPT)
observations = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(observations)


def entry(**over):
	base = {"seq": 1, "where": "Home", "severity": "minor", "title": "A thing",
			"status": "open", "resolution": "", "areas": ["layout"], "source": "jason",
			"createdAt": "2026-10-15T10:00:00Z"}
	base.update(over)
	return base


def run(argv):
	out, err = io.StringIO(), io.StringIO()
	with redirect_stdout(out), redirect_stderr(err):
		code = observations.main(argv)
	return code, out.getvalue(), err.getvalue()


class ExportTests(unittest.TestCase):
	def setUp(self):
		self.tmp = tempfile.TemporaryDirectory()
		self.root = Path(self.tmp.name)
		self.docs = self.root / "observations"
		self.docs.mkdir()
		self.out = self.root / "observations.json"

	def tearDown(self):
		self.tmp.cleanup()

	def write_doc(self, doc_id, body):
		(self.docs / f"{doc_id}.json").write_text(json.dumps(body))

	def test_export_sorts_by_seq_and_keeps_ids(self):
		self.write_doc("b", entry(seq=2, title="second"))
		self.write_doc("a", entry(seq=1, title="first"))
		code, out, _ = run(["export", str(self.docs), "--artifact", "https://claude.ai/artifact/x", "--out", str(self.out)])
		self.assertEqual(code, 0, out)
		export = json.loads(self.out.read_text())
		self.assertEqual([e["title"] for e in export["entries"]], ["first", "second"])
		self.assertEqual([e["id"] for e in export["entries"]], ["a", "b"])
		self.assertEqual(export["artifact"], "https://claude.ai/artifact/x")
		self.assertTrue(export["exported"].endswith("Z"))

	def test_fixed_without_resolution_is_a_fault(self):
		self.write_doc("a", entry(status="fixed"))
		code, out, _ = run(["export", str(self.docs), "--artifact", "u", "--out", str(self.out)])
		self.assertEqual(code, 1)
		self.assertIn("without a resolution", out)
		self.assertFalse(self.out.exists())

	def test_check_finding_needs_principle(self):
		self.write_doc("a", entry(source="check"))
		code, out, _ = run(["export", str(self.docs), "--artifact", "u", "--out", str(self.out)])
		self.assertEqual(code, 1)
		self.assertIn("integer principle", out)

	def test_duplicate_seq_and_bad_area(self):
		self.write_doc("a", entry(seq=1, areas=["layout", "vibes"]))
		self.write_doc("b", entry(seq=1))
		code, out, _ = run(["export", str(self.docs), "--artifact", "u", "--out", str(self.out)])
		self.assertEqual(code, 1)
		self.assertIn("duplicate seq", out)
		self.assertIn("'vibes'", out)

	def test_unreadable_document(self):
		(self.docs / "a.json").write_text("{nope")
		code, _, err = run(["export", str(self.docs), "--artifact", "u", "--out", str(self.out)])
		self.assertEqual(code, 2)
		self.assertIn("unreadable", err)


class StatusTests(unittest.TestCase):
	def setUp(self):
		self.tmp = tempfile.TemporaryDirectory()
		self.path = Path(self.tmp.name) / "observations.json"

	def tearDown(self):
		self.tmp.cleanup()

	def write(self, entries, exported="2026-10-15T10:00:00Z"):
		self.path.write_text(json.dumps({"exported": exported, "artifact": "u", "entries": entries}))

	def test_clean_export_passes(self):
		self.write([entry(status="fixed", resolution="done"), entry(seq=2, status="waived", resolution="fine", source="check", principle=4)])
		code, out, _ = run(["status", str(self.path)])
		self.assertEqual(code, 0, out)
		self.assertIn("blocks sign-off: nothing", out)

	def test_open_entry_blocks(self):
		self.write([entry()])
		code, out, _ = run(["status", str(self.path)])
		self.assertEqual(code, 1)
		self.assertIn("1 open", out)
		self.assertIn("#1 minor Home: A thing", out)

	def test_unwaived_check_finding_named(self):
		self.write([entry(source="check", principle=9)])
		code, out, _ = run(["status", str(self.path), "--json"])
		self.assertEqual(code, 1)
		summary = json.loads(out)
		self.assertIn("1 unwaived principles findings", summary["blocks"])

	def test_stale_export_blocks_only_with_max_age(self):
		self.write([entry(status="fixed", resolution="done")], exported="2020-01-01T00:00:00Z")
		code, _, _ = run(["status", str(self.path)])
		self.assertEqual(code, 0)
		code, out, _ = run(["status", str(self.path), "--max-age", "24"])
		self.assertEqual(code, 1)
		self.assertIn("older than 24h", out)

	def test_not_an_export(self):
		self.path.write_text("[]")
		code, _, err = run(["status", str(self.path)])
		self.assertEqual(code, 2)
		self.assertIn("not an export file", err)


class AddTests(unittest.TestCase):
	def setUp(self):
		self.tmp = tempfile.TemporaryDirectory()
		self.path = Path(self.tmp.name) / "deep" / "observations.json"

	def tearDown(self):
		self.tmp.cleanup()

	def test_add_creates_file_and_assigns_seq(self):
		finding = json.dumps({"where": "Queue", "severity": "major", "title": "Toolbar moved", "source": "check", "principle": 4})
		code, out, _ = run(["add", str(self.path), "--entry", finding])
		self.assertEqual(code, 0, out)
		export = json.loads(self.path.read_text())
		e = export["entries"][0]
		self.assertEqual((e["seq"], e["status"], e["id"]), (1, "open", "local-1"))
		self.assertTrue(e["createdAt"])
		code, out, _ = run(["add", str(self.path), "--entry", finding])
		self.assertEqual(code, 0)
		self.assertEqual([e["seq"] for e in json.loads(self.path.read_text())["entries"]], [1, 2])

	def test_add_rejects_contract_faults(self):
		bad = json.dumps({"where": "Queue", "severity": "huge", "title": "x"})
		code, out, _ = run(["add", str(self.path), "--entry", bad])
		self.assertEqual(code, 1)
		self.assertIn("severity 'huge'", out)
		self.assertFalse(self.path.exists())


if __name__ == "__main__":
	unittest.main()
