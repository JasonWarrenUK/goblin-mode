#!/usr/bin/env python3
"""Tests for type-guard.py: the three hook modes, the ast-grep rules and the opt-outs.

Run from this directory: python3 -m unittest test_type_guard -v
(or python3 -m pytest test_type_guard.py). Stdlib only. The scan tests need
ast-grep on PATH or in TYPE_GUARD_AST_GREP and skip cleanly without it.
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
SCRIPT = HERE / "type-guard.py"

spec = importlib.util.spec_from_file_location("type_guard", SCRIPT)
type_guard = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(type_guard)

AST_GREP = type_guard.find_ast_grep()

BAD_TS = """export interface Account {
	id: string;
	readonly orderId?: string;
	status: string;
	isOpen: boolean;
}
export class Thing { id: string; private state: string = 'x' }
type Obj = { userId: string }
function f(id: string, status: string) {}
"""

GOOD_TS = """export type CustomerId = string & { readonly __brand: 'CustomerId' };
export type AccountStatus = 'active' | 'archived';
export interface Account { id: CustomerId; status: AccountStatus; grid: string; isOpen: boolean }
function f(id: string) {}
"""

BAD_PY = """from dataclasses import dataclass

@dataclass
class Account:
	id: str
	order_id: str = ""
	status: str
	run_status: str = "x"

	def m(self, user_id: str, status: str) -> None:
		local_id: str = user_id

def f(user_id: str, status: str) -> None:
	other_id: str = "x"
"""

GOOD_PY = """from dataclasses import dataclass
from typing import NewType
UserId = NewType("UserId", str)

@dataclass
class Account:
	user_id: UserId
	name: str
"""


def run(mode: str, payload: dict, env: dict | None = None) -> subprocess.CompletedProcess[str]:
	merged = {**os.environ, **(env or {})}
	merged.pop("TYPE_GUARD_OFF", None)
	return subprocess.run(
		[sys.executable, str(SCRIPT), mode],
		input=json.dumps(payload), capture_output=True, text=True, env=merged,
	)


def context_of(result: subprocess.CompletedProcess[str]) -> str | None:
	if not result.stdout.strip():
		return None
	return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]


def write_payload(path: str, content: str, session: str = "s1") -> dict:
	return {"session_id": session, "hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {"file_path": path, "content": content}}


def edit_payload(path: str, new_string: str, session: str = "s1") -> dict:
	return {"session_id": session, "hook_event_name": "PreToolUse", "tool_name": "Edit", "tool_input": {"file_path": path, "old_string": "x", "new_string": new_string}}


class Classification(unittest.TestCase):
	def test_language_by_suffix(self):
		self.assertEqual(type_guard.language("a/b.ts"), "ts")
		self.assertEqual(type_guard.language("a/b.tsx"), "ts")
		self.assertEqual(type_guard.language("a/b.mts"), "ts")
		self.assertEqual(type_guard.language("a/b.py"), "py")
		self.assertEqual(type_guard.language("a/b.pyi"), "py")
		self.assertEqual(type_guard.language("a/b.go"), "go")
		self.assertIsNone(type_guard.language("a/B.svelte"))
		self.assertIsNone(type_guard.language("a/b.md"))

	def test_skipped_paths(self):
		for path in (
			"x/node_modules/y/z.ts", "x/dist/z.ts", "x/build/z.py", "x/.svelte-kit/z.ts",
			"x/.venv/lib/z.py", "x/types.d.ts", "x/a.test.ts", "x/a.spec.tsx", "x/test_a.py",
			"x/a_test.py", "x/conftest.py", "C:\\repo\\node_modules\\z.ts",
		):
			self.assertTrue(type_guard.skipped(path), path)
		for path in ("src/account.ts", "src/distribution.ts", "src/targeting.ts", "app/models.py", "tests.py"):
			self.assertFalse(type_guard.skipped(path), path)

	def test_declaration_detection(self):
		ts = type_guard.DECLARES_TYPE["ts"]
		self.assertTrue(ts.search("export interface Account {"))
		self.assertTrue(ts.search("type Id = string"))
		self.assertTrue(ts.search("export class Thing {"))
		self.assertFalse(ts.search("const total = items.length"))
		py = type_guard.DECLARES_TYPE["py"]
		self.assertTrue(py.search("@dataclass\nclass A:"))
		self.assertTrue(py.search("class A(BaseModel):"))
		self.assertTrue(py.search("X = NewType('X', str)"))
		self.assertFalse(py.search("def f():\n\treturn 1"))
		go = type_guard.DECLARES_TYPE["go"]
		self.assertTrue(go.search("type Account struct {"))
		self.assertTrue(go.search("type UserID string"))
		self.assertFalse(go.search("func main() {}"))


class Remind(unittest.TestCase):
	def setUp(self):
		self.tmp = tempfile.TemporaryDirectory()
		self.env = {"TYPE_GUARD_STATE_DIR": self.tmp.name}

	def tearDown(self):
		self.tmp.cleanup()

	def test_write_declaring_a_type_gets_the_reminder(self):
		result = run("remind", write_payload("/p/src/account.ts", "export interface Account { id: string }"), self.env)
		self.assertEqual(result.returncode, 0)
		self.assertIn("branded", context_of(result))
		self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"], "PreToolUse")

	def test_edit_new_string_counts(self):
		result = run("remind", edit_payload("/p/app/models.py", "@dataclass\nclass Account:\n\tid: str"), self.env)
		self.assertIn("NewType", context_of(result))

	def test_go_gets_the_reminder_too(self):
		result = run("remind", write_payload("/p/account.go", "type Account struct { ID string }"), self.env)
		self.assertIn("type UserID string", context_of(result))

	def test_second_call_in_the_same_session_is_silent(self):
		first = run("remind", write_payload("/p/a.ts", "interface A {}", "same"), self.env)
		second = run("remind", write_payload("/p/b.ts", "interface B {}", "same"), self.env)
		self.assertIsNotNone(context_of(first))
		self.assertIsNone(context_of(second))

	def test_another_session_is_not_throttled_by_the_first(self):
		run("remind", write_payload("/p/a.ts", "interface A {}", "one"), self.env)
		other = run("remind", write_payload("/p/a.ts", "interface A {}", "two"), self.env)
		self.assertIsNotNone(context_of(other))

	def test_content_without_a_declaration_is_silent(self):
		result = run("remind", write_payload("/p/a.ts", "export const total = 1;"), self.env)
		self.assertIsNone(context_of(result))

	def test_svelte_and_test_files_are_silent(self):
		self.assertIsNone(context_of(run("remind", write_payload("/p/A.svelte", "<script lang='ts'>interface Props {}</script>"), self.env)))
		self.assertIsNone(context_of(run("remind", write_payload("/p/a.test.ts", "interface Fixture {}"), self.env)))

	def test_off_switch(self):
		result = subprocess.run(
			[sys.executable, str(SCRIPT), "remind"], input=json.dumps(write_payload("/p/a.ts", "interface A {}")),
			capture_output=True, text=True, env={**os.environ, **self.env, "TYPE_GUARD_OFF": "1"},
		)
		self.assertEqual(result.returncode, 0)
		self.assertEqual(result.stdout, "")

	def test_garbage_payload_is_silent(self):
		result = subprocess.run([sys.executable, str(SCRIPT), "remind"], input="not json", capture_output=True, text=True, env={**os.environ, **self.env})
		self.assertEqual(result.returncode, 0)
		self.assertEqual(result.stdout, "")


class Compact(unittest.TestCase):
	def test_compaction_gets_the_reminder(self):
		with tempfile.TemporaryDirectory() as tmp:
			result = run("compact", {"session_id": "c1", "hook_event_name": "SessionStart", "source": "compact", "cwd": tmp}, {"TYPE_GUARD_STATE_DIR": tmp})
			self.assertEqual(result.returncode, 0)
			self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"], "SessionStart")
			self.assertIn("closed set", context_of(result))

	def test_compaction_starts_the_remind_window(self):
		with tempfile.TemporaryDirectory() as tmp:
			env = {"TYPE_GUARD_STATE_DIR": tmp}
			run("compact", {"session_id": "c2", "cwd": tmp}, env)
			after = run("remind", write_payload("/p/a.ts", "interface A {}", "c2"), env)
			self.assertIsNone(context_of(after))


@unittest.skipUnless(AST_GREP, "ast-grep not installed")
class Scan(unittest.TestCase):
	def setUp(self):
		self.tmp = tempfile.TemporaryDirectory()
		self.root = Path(self.tmp.name)

	def tearDown(self):
		self.tmp.cleanup()

	def scan(self, name: str, content: str) -> subprocess.CompletedProcess[str]:
		path = self.root / name
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(content, encoding="utf-8")
		payload = {"session_id": "s", "hook_event_name": "PostToolUse", "tool_name": "Write", "cwd": str(self.root), "tool_input": {"file_path": str(path), "content": content}, "tool_response": {"filePath": str(path), "type": "create"}}
		return run("scan", payload)

	def test_bare_ts_fields_block_with_line_numbers(self):
		result = self.scan("account.ts", BAD_TS)
		self.assertEqual(result.returncode, 2, result.stderr)
		lines = result.stderr.splitlines()
		self.assertIn("clod-approach-types", lines[0])
		findings = [line for line in lines[1:]]
		self.assertEqual(len(findings), 6, result.stderr)
		self.assertTrue(findings[0].startswith("L2 ts-bare-id-field (id: string): "), findings[0])
		self.assertIn("L3 ts-bare-id-field (readonly orderId?: string)", result.stderr)
		self.assertIn("L4 ts-bare-status-field (status: string)", result.stderr)
		self.assertIn("L7 ts-bare-id-field (id: string)", result.stderr)
		self.assertIn("L7 ts-bare-status-field (private state: string = 'x')", result.stderr)
		self.assertIn("L8 ts-bare-id-field (userId: string)", result.stderr)
		self.assertNotIn("isOpen", result.stderr)
		self.assertNotIn("L9", result.stderr, "function parameters are not fields")

	def test_branded_ts_passes(self):
		result = self.scan("account.ts", GOOD_TS)
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stderr, "")

	def test_bare_py_fields_block_and_locals_do_not(self):
		result = self.scan("models.py", BAD_PY)
		self.assertEqual(result.returncode, 2, result.stderr)
		self.assertIn("L5 py-bare-id-field (id: str)", result.stderr)
		self.assertIn('L6 py-bare-id-field (order_id: str = "")', result.stderr)
		self.assertIn("L7 py-bare-status-field (status: str)", result.stderr)
		self.assertIn('L8 py-bare-status-field (run_status: str = "x")', result.stderr)
		self.assertNotIn("local_id", result.stderr)
		self.assertNotIn("other_id", result.stderr)
		self.assertNotIn("user_id", result.stderr, "parameters are not fields")

	def test_newtype_py_passes(self):
		result = self.scan("models.py", GOOD_PY)
		self.assertEqual(result.returncode, 0, result.stderr)

	def test_test_files_and_other_suffixes_pass(self):
		self.assertEqual(self.scan("account.test.ts", BAD_TS).returncode, 0)
		self.assertEqual(self.scan("test_models.py", BAD_PY).returncode, 0)
		self.assertEqual(self.scan("Account.svelte", BAD_TS).returncode, 0)
		self.assertEqual(self.scan("account.go", "type A struct { ID string }").returncode, 0)

	def test_missing_file_passes(self):
		payload = {"tool_input": {"file_path": str(self.root / "gone.ts")}}
		self.assertEqual(run("scan", payload).returncode, 0)

	def test_repo_opt_out(self):
		subprocess.run(["git", "init", "-q", str(self.root)], check=True)
		subprocess.run(["git", "-C", str(self.root), "config", "typeGuard.enforce", "false"], check=True)
		result = self.scan("account.ts", BAD_TS)
		self.assertEqual(result.returncode, 0, result.stderr)

	def test_by_hand_scan(self):
		path = self.root / "account.ts"
		path.write_text(BAD_TS, encoding="utf-8")
		result = subprocess.run([sys.executable, str(SCRIPT), "--file", str(path)], capture_output=True, text=True)
		self.assertEqual(result.returncode, 1)
		self.assertEqual(len(result.stdout.splitlines()), 6)
		clean = self.root / "clean.ts"
		clean.write_text(GOOD_TS, encoding="utf-8")
		self.assertEqual(subprocess.run([sys.executable, str(SCRIPT), "--file", str(clean)], capture_output=True, text=True).returncode, 0)


if __name__ == "__main__":
	unittest.main()
