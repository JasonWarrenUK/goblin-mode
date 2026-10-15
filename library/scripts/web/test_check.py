#!/usr/bin/env python3
"""Tests for check.py: one class per subcommand, a finding and a clean run each.

Run from this directory: python3 -m unittest test_check -v
(or python3 -m pytest test_check.py). Stdlib only.
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
spec = importlib.util.spec_from_file_location("check", HERE / "check.py")
check = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(check)


def run(argv):
	out, err = io.StringIO(), io.StringIO()
	with redirect_stdout(out), redirect_stderr(err):
		code = check.main(argv)
	return code, out.getvalue(), err.getvalue()


class Temp(unittest.TestCase):
	def setUp(self):
		self.tmp = tempfile.TemporaryDirectory()
		self.root = Path(self.tmp.name)

	def tearDown(self):
		self.tmp.cleanup()

	def write(self, rel, text=""):
		p = self.root / rel
		p.parent.mkdir(parents=True, exist_ok=True)
		p.write_text(text)
		return p


class ExportTests(Temp):
	def test_resolution_missing_and_stale(self):
		p = self.write("observations.json", json.dumps({"exported": "2020-01-01T00:00:00Z", "artifact": "u", "entries": [
			{"seq": 1, "status": "fixed", "resolution": ""}, {"seq": 2, "status": "declined", "resolution": "because"}]}))
		code, out, _ = run(["--json", "export", str(p), "--max-age", "1"])
		self.assertEqual(code, 1)
		findings = json.loads(out)
		self.assertEqual([f["principle"] for f in findings], [7, 7])
		self.assertEqual(findings[0]["where"], "#1")
		self.assertIn("older than 1h", findings[1]["title"])

	def test_clean(self):
		p = self.write("observations.json", json.dumps({"exported": None, "artifact": "u", "entries": [{"seq": 1, "status": "open"}]}))
		code, out, _ = run(["export", str(p)])
		self.assertEqual((code, out.strip()), (0, "no findings"))


class CoverageTests(Temp):
	def test_missing_and_unknown(self):
		shots = self.root / "shots"
		for name in ["phone-home.png", "desktop-home.png", "desktop-record.png", "desktop-record-filters-open.png", "tablet-home.png", "notes.txt"]:
			self.write(f"shots/{name}")
		code, out, _ = run(["--json", "coverage", str(shots), "--routes", "home,record", "--devices", "phone,desktop"])
		self.assertEqual(code, 1)
		titles = {(f["where"], f["title"].split(" ")[0]) for f in json.loads(out)}
		self.assertIn(("phone-record", "no"), titles)
		self.assertIn(("tablet-home.png", "capture"), titles)
		self.assertEqual(len(titles), 2)

	def test_single_device_has_no_prefix(self):
		shots = self.root / "shots"
		self.write("shots/home.png"); self.write("shots/record-900.png")
		code, _, _ = run(["coverage", str(shots), "--routes", "home,record", "--devices", "desktop"])
		self.assertEqual(code, 0)

	def test_not_a_directory(self):
		code, _, err = run(["coverage", str(self.root / "nope"), "--routes", "a", "--devices", "b"])
		self.assertEqual(code, 2)
		self.assertIn("not a directory", err)


class ClassesTests(Temp):
	def test_collision_and_dependence(self):
		self.write("src/app.css", ".card { padding: 0 } .mine { color: red } /* .ghost { } */")
		self.write("src/routes/+page.svelte", '<div class="card btn mine other" class:active={on}></div>')
		lib = self.write("lib/skeleton.css", ".card{margin:0}.btn{}.active{}@media (min-width: 1px){.ghost{}}")
		code, out, _ = run(["--json", "classes", "--source", str(self.root / "src"), "--library", str(lib)])
		self.assertEqual(code, 1)
		findings = json.loads(out)
		by_sev = {f["severity"]: sorted(f["title"].split(" ")[0] for f in findings if f["severity"] == f["severity"]) for f in findings}
		majors = [f for f in findings if f["severity"] == "major"]
		nits = [f for f in findings if f["severity"] == "nit"]
		self.assertEqual([f["title"].split(" ")[0] for f in majors], [".card"])
		self.assertEqual(sorted(f["title"].split(" ")[0] for f in nits), [".active", ".btn"])
		self.assertTrue(majors[0]["where"].endswith("app.css"))

	def test_no_library_css(self):
		self.write("src/a.css", ".x{}")
		code, _, err = run(["classes", "--source", str(self.root / "src"), "--library", str(self.root / "missing.css")])
		self.assertEqual(code, 2)
		self.assertIn("no library CSS", err)


WIREFRAME = """<style>:root { --navy: #000; --orange: #f00; --callout: #b00; --mono: x; }</style>
<div class="mock"><span class="co abs">1</span><span class="co abs">2</span></div>
<ul class="explain"><li><span class="co">1</span> R1</li><li><span class="co">3</span> R2</li></ul>"""


class TokensTests(Temp):
	def test_foreign_tokens_and_callout_mismatch(self):
		w = self.write("wireframe.html", WIREFRAME)
		css = self.write("app.css", ":root { --navy: #000; }")
		code, out, _ = run(["--json", "tokens", str(w), "--product", str(css)])
		self.assertEqual(code, 1)
		titles = [f["title"] for f in json.loads(out)]
		self.assertIn("1 custom properties the product's CSS does not define", titles)
		self.assertIn("callout 2 has no explain item", titles)
		self.assertIn("explain item 3 has no badge in the mock", titles)

	def test_clean(self):
		w = self.write("wireframe.html", """<style>:root{--navy:#000;--callout:#b00;}</style><div><span class="co abs">1</span></div><ul><li><span class="co">1</span> R1</li></ul>""")
		css = self.write("app.css", ":root { --navy: #000; }")
		code, _, _ = run(["tokens", str(w), "--product", str(css)])
		self.assertEqual(code, 0)


class BriefTests(Temp):
	def test_placeholders_left(self):
		s = self.write("scope.md", "## 3. Copy brief (principle 10)\n\n| | |\n|---|---|\n| Addresses | [who] |\n| Register | brisk |\n\n## 4. Inventory\n")
		code, out, _ = run(["brief", str(s)])
		self.assertEqual(code, 1)
		self.assertIn("1 placeholders", out)

	def test_missing_section(self):
		s = self.write("scope.md", "## 1. Who\n\ntext\n")
		code, out, _ = run(["brief", str(s)])
		self.assertEqual(code, 1)
		self.assertIn("no copy brief section", out)

	def test_filled(self):
		s = self.write("scope.md", "## 3. Copy brief (principle 10)\n\n| | |\n|---|---|\n| Addresses | reviewers |\n| Register | brisk |\n\n## 4. Inventory\n")
		code, out, _ = run(["brief", str(s)])
		self.assertEqual((code, out.strip()), (0, "no findings"))


if __name__ == "__main__":
	unittest.main()
