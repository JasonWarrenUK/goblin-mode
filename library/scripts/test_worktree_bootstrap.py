#!/usr/bin/env python3
"""Tests for worktree-bootstrap.sh's env linking, lockfile installs and exit codes.

Run from this directory: python3 -m unittest test_worktree_bootstrap -v
Each test builds a throwaway repo and worktree in a TemporaryDirectory and
drives the script as a subprocess (it's zsh, not Python). Installers are fake
executables on PATH that append their name, arguments and cwd to a log file.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("worktree-bootstrap.sh")
TOOLS = ("bun", "poetry", "uv", "pnpm", "npm")


def git(cwd: Path, *args: str) -> None:
	subprocess.run(
		["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t", *args],
		check=True,
		capture_output=True,
	)


@unittest.skipUnless(shutil.which("zsh") and shutil.which("git"), "needs zsh and git")
class WorktreeBootstrapTest(unittest.TestCase):
	def setUp(self) -> None:
		self.tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self.tmp.cleanup)
		root = Path(self.tmp.name).resolve()
		self.main = root / "main"
		self.worktree = root / "wt"
		self.bin = root / "bin"
		self.log = root / "installs.log"
		self.main.mkdir()
		self.bin.mkdir()
		git(self.main, "init", "-q", "-b", "main")
		(self.main / ".gitignore").write_text(".env*\n!.env.example\nnode_modules/\n")
		self.commit({".gitignore": ".env*\n!.env.example\nnode_modules/\n"})

	def commit(self, files: dict[str, str]) -> None:
		for relative, content in files.items():
			path = self.main / relative
			path.parent.mkdir(parents=True, exist_ok=True)
			path.write_text(content)
		git(self.main, "add", "-A")
		git(self.main, "commit", "-q", "-m", "fixture", "--allow-empty")

	def add_worktree(self) -> None:
		git(self.main, "worktree", "add", "-q", "-b", "feat/x", str(self.worktree))

	def fake_tools(self, *names: str, fail: tuple[str, ...] = ()) -> None:
		for name in names:
			exe = self.bin / name
			exit_code = 1 if name in fail else 0
			exe.write_text(
				f'#!/bin/sh\necho "{name} $* @ $(pwd)" >> "{self.log}"\n'
				f'[ {exit_code} -eq 0 ] || echo "{name} exploded" >&2\nexit {exit_code}\n'
			)
			exe.chmod(0o755)

	def run_script(self, path: Path | None = None) -> subprocess.CompletedProcess[str]:
		env = {**os.environ, "PATH": f"{self.bin}:/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"}
		return subprocess.run(
			["zsh", str(SCRIPT), str(path or self.worktree)],
			capture_output=True,
			text=True,
			env=env,
		)

	def installs(self) -> list[str]:
		return self.log.read_text().splitlines() if self.log.exists() else []

	def test_links_ignored_env_files_at_matching_paths(self) -> None:
		self.commit({"apps/api/.env.example": "X=\n"})
		(self.main / ".env").write_text("A=1\n")
		(self.main / "apps/api/.env.local").write_text("B=2\n")
		self.add_worktree()
		result = self.run_script()
		self.assertEqual(result.returncode, 0, result.stderr)
		for relative in (".env", "apps/api/.env.local"):
			link = self.worktree / relative
			self.assertTrue(link.is_symlink(), relative)
			self.assertEqual(link.resolve(), (self.main / relative).resolve())
		self.assertIn("linked .env", result.stdout)

	def test_example_files_are_not_linked(self) -> None:
		self.commit({".env.example": "X=\n"})
		self.add_worktree()
		self.run_script()
		self.assertFalse((self.worktree / ".env.example").is_symlink())

	def test_existing_file_is_left_alone(self) -> None:
		(self.main / ".env").write_text("main\n")
		self.add_worktree()
		(self.worktree / ".env").write_text("mine\n")
		result = self.run_script()
		self.assertEqual(result.returncode, 0)
		self.assertEqual((self.worktree / ".env").read_text(), "mine\n")
		self.assertFalse((self.worktree / ".env").is_symlink())

	def test_rerun_does_not_relink(self) -> None:
		(self.main / ".env").write_text("A=1\n")
		self.add_worktree()
		self.run_script()
		second = self.run_script()
		self.assertEqual(second.returncode, 0)
		self.assertNotIn("linked", second.stdout)

	def test_each_lockfile_runs_its_tool_in_its_own_directory(self) -> None:
		self.commit({
			"poetry.lock": "", "svc/uv.lock": "", "web/pnpm-lock.yaml": "", "cli/package-lock.json": "",
		})
		self.fake_tools(*TOOLS)
		self.add_worktree()
		result = self.run_script()
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
		wt = str(self.worktree)
		self.assertIn(f"poetry install @ {wt}", self.installs())
		self.assertIn(f"uv sync @ {wt}/svc", self.installs())
		self.assertIn(f"pnpm install --frozen-lockfile @ {wt}/web", self.installs())
		self.assertIn(f"npm ci @ {wt}/cli", self.installs())

	def test_workspace_member_lockfile_is_skipped(self) -> None:
		self.commit({"bun.lock": "", "apps/web/bun.lock": ""})
		self.fake_tools(*TOOLS)
		self.add_worktree()
		self.run_script()
		self.assertEqual(len(self.installs()), 1)
		self.assertIn(f"bun install @ {self.worktree}", self.installs()[0])

	def test_missing_tool_fails_but_later_steps_still_run(self) -> None:
		self.commit({"bun.lock": "", "api/poetry.lock": ""})
		self.fake_tools("poetry")
		self.add_worktree()
		result = self.run_script()
		self.assertEqual(result.returncode, 1)
		self.assertIn("failed . (bun): bun is not installed", result.stdout)
		self.assertEqual(len(self.installs()), 1)
		self.assertIn("poetry install", self.installs()[0])

	def test_failed_install_reports_last_line_and_exits_one(self) -> None:
		self.commit({"poetry.lock": ""})
		self.fake_tools("poetry", fail=("poetry",))
		self.add_worktree()
		result = self.run_script()
		self.assertEqual(result.returncode, 1)
		self.assertIn("failed . (poetry): poetry exploded", result.stdout)

	def test_usage_errors_exit_two(self) -> None:
		self.assertEqual(self.run_script(Path(self.tmp.name) / "missing").returncode, 2)
		outside = Path(self.tmp.name) / "plain"
		outside.mkdir()
		self.assertEqual(self.run_script(outside).returncode, 2)


if __name__ == "__main__":
	unittest.main()
