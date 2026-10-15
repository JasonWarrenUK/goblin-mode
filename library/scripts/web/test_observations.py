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


class GuardTests(unittest.TestCase):
	"""The guard runs git against a throwaway repo with a main branch and a feature branch."""

	def setUp(self):
		import subprocess
		self.tmp = tempfile.TemporaryDirectory()
		self.repo = Path(self.tmp.name)
		self.git = lambda *a: subprocess.run(["git", "-C", str(self.repo), *a], check=True, capture_output=True, text=True)
		self.git("init", "-q", "-b", "main")
		self.git("config", "user.email", "t@example.com"); self.git("config", "user.name", "t")
		(self.repo / "README.md").write_text("x")
		self.git("add", "."); self.git("commit", "-q", "-m", "init")
		self.git("checkout", "-q", "-b", "feat/x")
		self.export = self.repo / "docs" / "artefacts" / "task" / "observations.json"
		self.export.parent.mkdir(parents=True)

	def tearDown(self):
		self.tmp.cleanup()

	def guard(self, cwd=None):
		import io, sys
		payload = json.dumps({"cwd": str(cwd or self.repo), "tool_input": {"command": "gh pr create --title x"}})
		stdin = sys.stdin
		sys.stdin = io.StringIO(payload)
		try:
			return run(["guard"])
		finally:
			sys.stdin = stdin

	def test_open_entry_on_branch_blocks(self):
		self.export.write_text(json.dumps({"exported": "2026-10-15T10:00:00Z", "artifact": "u", "entries": [entry(where="Queue", title="Toolbar moved", source="check", principle=4)]}))
		code, _, err = self.guard()
		self.assertEqual(code, 2)
		self.assertIn("docs/artefacts/task/observations.json: 1 open; 1 unwaived principles findings", err)
		self.assertIn("#1 minor Queue: Toolbar moved [principle 4]", err)

	def test_closed_export_passes_and_committed_counts(self):
		self.export.write_text(json.dumps({"exported": "2026-10-15T10:00:00Z", "artifact": "u", "entries": [entry(status="fixed", resolution="done")]}))
		self.git("add", "."); self.git("commit", "-q", "-m", "pass")
		code, _, err = self.guard()
		self.assertEqual((code, err), (0, ""))

	def test_subdirectory_cwd_still_blocks(self):
		"""git prints repo-root paths and resolves pathspecs from cwd: a session in app/ must still see the export."""
		(self.repo / "app").mkdir()
		self.export.write_text(json.dumps({"exported": "2026-10-15T10:00:00Z", "artifact": "u", "entries": [entry()]}))
		code, _, err = self.guard(cwd=self.repo / "app")
		self.assertEqual(code, 2, "untracked export, session in a subdirectory")
		self.assertIn("docs/artefacts/task/observations.json: 1 open", err)
		self.git("add", "."); self.git("commit", "-q", "-m", "add")
		code, _, err = self.guard(cwd=self.repo / "app")
		self.assertEqual(code, 2, "committed export, session in a subdirectory")

	def test_not_a_repo_fails_open(self):
		import io, sys
		other = tempfile.TemporaryDirectory()
		try:
			stdin = sys.stdin
			sys.stdin = io.StringIO(json.dumps({"cwd": other.name}))
			try:
				code, _, _ = run(["guard"])
			finally:
				sys.stdin = stdin
			self.assertEqual(code, 0)
		finally:
			other.cleanup()


if __name__ == "__main__":
	unittest.main()
