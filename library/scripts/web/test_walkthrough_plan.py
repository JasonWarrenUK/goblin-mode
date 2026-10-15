#!/usr/bin/env python3
"""Tests for walkthrough-plan.py: naming, state merging, YAML shape.

Run from this directory: python3 -m unittest test_walkthrough_plan -v. Stdlib only.
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
spec = importlib.util.spec_from_file_location("walkthrough_plan", HERE / "walkthrough-plan.py")
plan = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(plan)


def run(argv):
	out, err = io.StringIO(), io.StringIO()
	with redirect_stdout(out), redirect_stderr(err):
		code = plan.main(argv)
	return code, out.getvalue(), err.getvalue()


class NamingTests(unittest.TestCase):
	def test_device_prefix_only_with_many_devices(self):
		self.assertEqual(plan.capture_name("phone", "home", None, True), "phone-home")
		self.assertEqual(plan.capture_name("phone", "home", None, False), "home")
		self.assertEqual(plan.capture_name("desktop", "document", "filters-open", True), "desktop-document-filters-open")


class BuildTests(unittest.TestCase):
	def test_routes_times_devices_plus_states(self):
		planned = [{"route": "document", "specifier": "filters-open", "javascript": "open()"}]
		discovered = [
			{"route": "document", "device": "phone", "specifier": "filters-open-2", "javascript": "open()"},
			{"route": "document", "device": "phone", "specifier": "more-open", "javascript": "more()"},
		]
		entries, unplanned = plan.build("http://localhost:5173", {"home": "/", "document": "/documents/5"},
										{"phone": 390, "desktop": 1440}, planned, discovered, "docs/assets/shots", 800)
		names = [e["output"].rsplit("/", 1)[1] for e in entries]
		self.assertEqual(names, [
			"phone-home.png", "desktop-home.png",
			"phone-document.png", "phone-document-filters-open.png", "phone-document-more-open.png",
			"desktop-document.png", "desktop-document-filters-open.png", "desktop-document-more-open.png",
		])
		self.assertEqual([u["name"] for u in unplanned], ["phone-document-more-open", "desktop-document-more-open"])
		self.assertEqual(entries[2]["url"], "http://localhost:5173/documents/5")
		self.assertNotIn("height", entries[0])
		self.assertEqual(entries[3]["javascript"], "open()")

	def test_file_base_and_single_device(self):
		entries, _ = plan.build("/site", {"home": "/index.html"}, {"desktop": 1440}, [], [], "shots", 500)
		self.assertEqual(entries[0]["output"], "shots/home.png")
		self.assertEqual(entries[0]["url"], "/site/index.html")

	def test_yaml_marks_unplanned_and_quotes_js(self):
		text = plan.to_yaml([{"output": "s/a.png", "url": "u", "width": 1, "wait": 2, "javascript": "x: 'y'", "unplanned": True}])
		self.assertIn("# unplanned", text)
		self.assertIn('javascript: "x: \'y\'"', text)


class CliTests(unittest.TestCase):
	def test_writes_out_and_summary(self):
		with tempfile.TemporaryDirectory() as tmp:
			out = Path(tmp) / "docs" / "assets" / "walkthrough.yml"
			code, stdout, _ = run(["--base", "http://x", "--routes", '{"home":"/"}', "--devices", '{"desktop":1440}', "--out", str(out), "--json"])
			self.assertEqual(code, 0)
			self.assertTrue(out.exists())
			self.assertEqual(json.loads(stdout)["entries"], 1)
			self.assertIn('output: "docs/assets/walkthrough/home.png"', out.read_text())

	def test_bad_routes(self):
		code, _, err = run(["--base", "http://x", "--routes", "[]", "--devices", '{"d":1}'])
		self.assertEqual(code, 2)
		self.assertIn("non-empty", err)


if __name__ == "__main__":
	unittest.main()
