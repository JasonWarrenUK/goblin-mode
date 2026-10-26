#!/usr/bin/env python3
"""Tests for stack-status.py's verdicts, chain walking and local-tracking reads.

Run from this directory: python3 -m unittest test_stack_status -v
Each test builds a throwaway repo with a bare `origin` in a TemporaryDirectory
and puts a stub `gh` first on PATH that answers from a fixture dict, so no test
touches GitHub. The script is driven as a subprocess with --json.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "stack-status.py"

STUB_GH = textwrap.dedent("""\
	#!/usr/bin/env python3
	import json, os, sys
	fixture = json.load(open(os.environ["GH_STUB_FIXTURE"]))
	args = sys.argv[1:]
	if args[:1] == ["--version"]:
		print("gh version stub"); sys.exit(0)
	if args[:2] == ["stack", "--version"]:
		version = fixture.get("gh_stack_version", "0.1.0")
		if version is None:
			sys.exit(1)  # extension not installed
		print("gh stack version %s" % version); sys.exit(0)
	if args[:2] == ["repo", "view"]:
		print(json.dumps({"owner": {"login": "org"}, "name": "repo", "defaultBranchRef": {"name": "main"}})); sys.exit(0)
	if args[:2] == ["pr", "list"]:
		print(json.dumps(fixture["open_prs"])); sys.exit(0)
	if args[:2] == ["pr", "view"]:
		pr = fixture.get("pr_view", {}).get(args[2])
		if pr is None:
			sys.exit(1)
		print(json.dumps(pr)); sys.exit(0)
	if args[:2] == ["api", "graphql"]:
		if "-F" in args:
			sys.exit(1)  # -F coerces an all-digit owner or repo name to an integer; the script must send -f
		print(json.dumps({"data": {"repository": fixture.get("graphql", {})}})); sys.exit(0)
	sys.exit(1)
	""")


def _git(cwd: Path, *args: str) -> str:
	return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def stack(number: int, layers: list[tuple[int, str, str]]) -> dict:
	return {"number": number, "size": len(layers), "baseRefName": "main",
			"entries": {"nodes": [{"position": i + 1, "pullRequest": {"number": n, "headRefName": b, "state": s}}
								  for i, (n, b, s) in enumerate(layers)]}}


def pr(number: int, head: str, base: str = "main") -> dict:
	return {"number": number, "headRefName": head, "baseRefName": base, "title": "PR %d" % number,
			"state": "OPEN", "isDraft": False, "isCrossRepository": False}


class StackStatus(unittest.TestCase):
	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.root = Path(self._tmp.name).resolve()
		origin = self.root / "origin.git"
		self.repo = self.root / "repo"
		_git(self.root, "init", "-q", "--bare", "-b", "main", str(origin))
		_git(self.root, "clone", "-q", str(origin), str(self.repo))
		_git(self.repo, "config", "user.email", "t@t")
		_git(self.repo, "config", "user.name", "t")
		_git(self.repo, "checkout", "-q", "-b", "main")
		_git(self.repo, "commit", "-q", "--allow-empty", "-m", "chore: init")
		_git(self.repo, "push", "-q", "-u", "origin", "main")
		_git(self.repo, "remote", "set-head", "origin", "main")
		for branch in ("feat/a", "feat/b"):
			_git(self.repo, "branch", branch, "main")
		bin_dir = self.root / "bin"
		bin_dir.mkdir()
		stub = bin_dir / "gh"
		stub.write_text(STUB_GH)
		stub.chmod(0o755)
		self.fixture = self.root / "fixture.json"
		self.env = dict(os.environ, PATH="%s:%s" % (bin_dir, os.environ["PATH"]), GH_STUB_FIXTURE=str(self.fixture))

	def tearDown(self) -> None:
		self._tmp.cleanup()

	def run_script(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
		return subprocess.run(["python3", str(SCRIPT), *args], cwd=cwd or self.repo, env=self.env,
							  capture_output=True, text=True)

	def status(self, *args: str, fixture: dict) -> dict:
		self.fixture.write_text(json.dumps(fixture))
		done = self.run_script("--json", *args)
		self.assertEqual(done.returncode, 0, done.stderr)
		return json.loads(done.stdout)

	def write_tracking(self, stacks: list[dict]) -> None:
		(self.repo / ".git" / "gh-stack").write_text(json.dumps({"schemaVersion": 1, "stacks": stacks}))

	def test_linked_layer_tracked_locally(self) -> None:
		self.write_tracking([{"number": 7, "trunk": {"branch": "main"}, "branches": [
			{"branch": "feat/a", "pullRequest": {"number": 10}},
			{"branch": "feat/b", "pullRequest": {"number": 11}}]}])
		fixture = {"open_prs": [pr(10, "feat/a"), pr(11, "feat/b", "feat/a")],
				   "graphql": {"pr11": {"number": 11, "stack": stack(7, [(10, "feat/a", "OPEN"), (11, "feat/b", "OPEN")])}}}
		row = self.status("feat/b", fixture=fixture)["rows"][0]
		self.assertEqual(row["verdict"], "linked")
		self.assertEqual(row["github_stack"]["number"], 7)
		self.assertEqual(row["chain"], [10, 11])
		self.assertEqual(row["tracked_locally"], {"stack": 7, "branch_exists": True})

	def test_chained_by_base_without_github_stack(self) -> None:
		fixture = {"open_prs": [pr(10, "feat/a"), pr(11, "feat/b", "feat/a")],
				   "graphql": {"pr10": {"number": 10, "stack": None}}}
		result = self.status("feat/a", fixture=fixture)
		row = result["rows"][0]
		self.assertEqual(row["verdict"], "chained-unlinked")
		self.assertEqual(row["children"], [11])
		self.assertIsNone(row["tracked_locally"])
		self.fixture.write_text(json.dumps(fixture))
		table = self.run_script("feat/a").stdout
		self.assertIn("`gh stack link 10 11`", table)

	def test_independent_pr(self) -> None:
		fixture = {"open_prs": [pr(10, "feat/a")], "graphql": {"pr10": {"number": 10, "stack": None}}}
		row = self.status("feat/a", fixture=fixture)["rows"][0]
		self.assertEqual(row["verdict"], "independent")

	def test_branch_without_pr_and_current_branch_default(self) -> None:
		_git(self.repo, "checkout", "-q", "feat/b")
		fixture = {"open_prs": [], "graphql": {}}
		result = self.status(fixture=fixture)
		self.assertEqual(result["rows"][0]["branch"], "feat/b")
		self.assertEqual(result["rows"][0]["verdict"], "no-pr")
		self.assertEqual(result["rows"][0]["worktree"], str(self.repo))

	def test_pr_number_resolves_to_its_branch(self) -> None:
		fixture = {"open_prs": [pr(10, "feat/a")], "pr_view": {"10": pr(10, "feat/a")},
				   "graphql": {"pr10": {"number": 10, "stack": None}}}
		row = self.status("10", fixture=fixture)["rows"][0]
		self.assertEqual(row["branch"], "feat/a")
		self.assertEqual(row["pr"], 10)

	def test_stale_tracking_and_missing_branches(self) -> None:
		self.write_tracking([
			{"number": 3, "trunk": {"branch": "main"}, "branches": [
				{"branch": "old/x", "pullRequest": {"number": 1, "merged": True}},
				{"branch": "old/y", "pullRequest": {"number": 2, "merged": True}}]},
			{"trunk": {"branch": "main"}, "branches": [
				{"branch": "feat/a", "pullRequest": {"number": 10}},
				{"branch": "feat/gone", "pullRequest": {"number": 12}}]}])
		fixture = {"open_prs": [pr(10, "feat/a")], "graphql": {"pr10": {"number": 10, "stack": None}}}
		result = self.status("feat/a", fixture=fixture)
		stale, local_only = result["local_tracking"]
		self.assertTrue(stale["stale"])
		self.assertEqual(stale["missing_branches"], ["old/x", "old/y"])
		self.assertIsNone(local_only["number"])
		self.assertFalse(local_only["stale"])
		self.assertEqual(local_only["missing_branches"], ["feat/gone"])
		self.assertEqual(result["rows"][0]["tracked_locally"], {"stack": None, "branch_exists": True})
		self.fixture.write_text(json.dumps(fixture))
		self.assertIn("`gh stack unstack 3 --local`", self.run_script("feat/a").stdout)

	def test_open_covers_every_open_pr(self) -> None:
		fixture = {"open_prs": [pr(10, "feat/a"), pr(11, "feat/b", "feat/a")],
				   "graphql": {"pr10": {"number": 10, "stack": None}, "pr11": {"number": 11, "stack": None}}}
		rows = self.status("--open", fixture=fixture)["rows"]
		self.assertEqual([r["pr"] for r in rows], [10, 11])
		self.assertEqual([r["verdict"] for r in rows], ["chained-unlinked", "chained-unlinked"])

	def table(self, *args: str, fixture: dict) -> str:
		self.fixture.write_text(json.dumps(fixture))
		return self.run_script(*args).stdout

	def test_base_no_open_pr_owns_is_independent(self) -> None:
		fixture = {"open_prs": [pr(10, "feat/a", "release/1.x"), pr(11, "feat/b", "feat/gone")],
				   "graphql": {"pr10": {"number": 10, "stack": None}, "pr11": {"number": 11, "stack": None}}}
		rows = self.status("--open", fixture=fixture)["rows"]
		self.assertEqual([r["verdict"] for r in rows], ["independent", "independent"])
		self.assertEqual([r["chain"] for r in rows], [[10], [11]])
		self.assertIn("ordinary PR on release/1.x", self.table("feat/a", fixture=fixture))

	def test_fork_pr_from_trunk_is_independent(self) -> None:
		fork = dict(pr(12, "main"), isCrossRepository=True)
		fixture = {"open_prs": [pr(10, "feat/a"), fork],
				   "graphql": {"pr10": {"number": 10, "stack": None}, "pr12": {"number": 12, "stack": None}}}
		row = self.status("--open", fixture=fixture)["rows"][1]
		self.assertEqual(row["verdict"], "independent")
		self.assertEqual(row["children"], [])
		self.assertEqual(row["chain"], [12])
		self.assertIsNone(row["worktree"])
		self.assertEqual(row["tracked_in"], [])
		self.assertIn("main (#12) is an ordinary PR on main", self.table("--open", fixture=fixture))

	def test_fork_pr_on_a_layer_is_not_its_child(self) -> None:
		fork = dict(pr(12, "contrib", "feat/a"), isCrossRepository=True)
		fixture = {"open_prs": [pr(10, "feat/a"), fork],
				   "graphql": {"pr10": {"number": 10, "stack": None}, "pr12": {"number": 12, "stack": None}}}
		rows = self.status("--open", fixture=fixture)["rows"]
		self.assertEqual([r["verdict"] for r in rows], ["independent", "independent"])
		self.assertEqual(rows[0]["children"], [])
		self.assertEqual(rows[1]["chain"], [12])

	def test_link_hint_climbs_the_whole_chain(self) -> None:
		fixture = {"open_prs": [pr(10, "feat/a"), pr(11, "feat/b", "feat/a"), pr(12, "feat/c", "feat/b")],
				   "graphql": {"pr10": {"number": 10, "stack": None}, "pr11": {"number": 11, "stack": None}}}
		row = self.status("feat/a", fixture=fixture)["rows"][0]
		self.assertEqual(row["link_order"], [10, 11, 12])
		self.assertEqual(row["fork"], [])
		self.assertIn("`gh stack link 10 11 12`", self.table("feat/a", fixture=fixture))
		self.assertIn("`gh stack link 10 11 12`", self.table("feat/b", fixture=fixture))

	def test_link_hint_names_each_path_of_a_fork(self) -> None:
		fixture = {"open_prs": [pr(10, "feat/a"), pr(11, "feat/b", "feat/a"), pr(12, "feat/c", "feat/a")],
				   "graphql": {"pr10": {"number": 10, "stack": None}, "pr11": {"number": 11, "stack": None}}}
		row = self.status("feat/a", fixture=fixture)["rows"][0]
		self.assertEqual(row["fork"], [11, 12])
		table = self.table("feat/a", fixture=fixture)
		self.assertNotIn("link 10 11 12", table)
		self.assertIn("`gh stack link 10 11`", table)
		self.assertIn("`gh stack link 10 12`", table)
		self.assertIn("`gh stack link 10 11`", self.table("feat/b", fixture=fixture))

	def test_unsynced_merged_stack_is_stale(self) -> None:
		self.write_tracking([{"number": 3, "trunk": {"branch": "main"}, "branches": [
			{"branch": "old/x", "pullRequest": {"number": 1}},
			{"branch": "old/y", "pullRequest": {"number": 2, "merged": True}}]}])
		fixture = {"open_prs": [pr(10, "feat/a")],
				   "graphql": {"pr10": {"number": 10, "stack": None}, "st1": {"state": "MERGED"}}}
		result = self.status("feat/a", fixture=fixture)
		self.assertTrue(result["local_tracking"][0]["stale"])
		self.assertIn("`gh stack unstack 3 --local`", self.table("feat/a", fixture=fixture))

	def test_closed_unsubmitted_or_open_layers_keep_a_stack_live(self) -> None:
		cases = {
			"merged plus closed": ([{"number": 1}, {"number": 2}], {"st1": {"state": "MERGED"}, "st2": {"state": "CLOSED"}}),
			"merged plus no PR yet": ([{"number": 1}, None], {"st1": {"state": "MERGED"}}),
			"merged plus unknown state": ([{"number": 1}, {"number": 2}], {"st1": {"state": "MERGED"}}),
			"merged plus open": ([{"number": 1}, {"number": 10}], {"st1": {"state": "MERGED"}}),
		}
		for label, (pulls, graphql) in cases.items():
			with self.subTest(label):
				self.write_tracking([{"number": 3, "trunk": {"branch": "main"}, "branches": [
					{"branch": "old/%d" % i, "pullRequest": p} for i, p in enumerate(pulls)]}])
				fixture = {"open_prs": [pr(10, "feat/a")],
						   "graphql": dict(graphql, pr10={"number": 10, "stack": None})}
				self.assertFalse(self.status("feat/a", fixture=fixture)["local_tracking"][0]["stale"])

	def test_stale_is_judged_for_a_branch_without_a_pr(self) -> None:
		self.write_tracking([{"number": 3, "trunk": {"branch": "main"}, "branches": [
			{"branch": "old/x", "pullRequest": {"number": 1}}]}])
		fixture = {"open_prs": [], "graphql": {"st1": {"state": "MERGED"}}}
		result = self.status("feat/b", fixture=fixture)
		self.assertEqual(result["rows"][0]["verdict"], "no-pr")
		self.assertTrue(result["local_tracking"][0]["stale"])

	def test_branch_in_two_tracked_stacks_shows_both(self) -> None:
		self.write_tracking([
			{"number": 5, "trunk": {"branch": "main"}, "branches": [
				{"branch": "feat/a", "pullRequest": {"number": 10}}, {"branch": "feat/b", "pullRequest": {"number": 11}}]},
			{"number": 9, "trunk": {"branch": "main"}, "branches": [
				{"branch": "feat/a", "pullRequest": {"number": 10}}]}])
		fixture = {"open_prs": [pr(10, "feat/a"), pr(11, "feat/b", "feat/a")],
				   "graphql": {"pr10": {"number": 10, "stack": stack(9, [(10, "feat/a", "OPEN")])}}}
		row = self.status("feat/a", fixture=fixture)["rows"][0]
		self.assertEqual([e["stack"] for e in row["tracked_in"]], [5, 9])
		self.assertEqual(row["tracked_locally"], {"stack": 9, "branch_exists": True})
		table = self.table("feat/a", fixture=fixture)
		self.assertIn("in 2 stacks: #5, #9", table)
		self.assertIn("tracked in 2 local stacks (#5, #9)", table)

	def test_tracked_layer_reads_in_stack(self) -> None:
		self.write_tracking([{"number": 7, "trunk": {"branch": "main"}, "branches": [
			{"branch": "feat/a", "pullRequest": {"number": 10}}, {"branch": "feat/b", "pullRequest": {"number": 11}}]}])
		fixture = {"open_prs": [pr(10, "feat/a"), pr(11, "feat/b", "feat/a")],
				   "graphql": {"pr11": {"number": 11, "stack": stack(7, [(10, "feat/a", "OPEN"), (11, "feat/b", "OPEN")])}}}
		self.assertIn("is in stack #7, layer 2 of 2 and tracked here", self.table("feat/b", fixture=fixture))

	def linked_worktree(self, branch: str) -> tuple[Path, Path]:
		"""(worktree path, its per-worktree git admin dir) for `branch`, checked out beside the repo."""
		tree = self.root / ("tree-%s" % branch.replace("/", "-"))
		_git(self.repo, "worktree", "add", "-q", str(tree), branch)
		admin = Path(_git(tree, "rev-parse", "--path-format=absolute", "--git-dir").strip()).resolve()
		self.assertNotEqual(admin, (self.repo / ".git").resolve())
		return tree, admin

	def test_v0_1_0_tracking_in_a_linked_worktree_is_read_there(self) -> None:
		# gh-stack v0.1.0 writes `gh-stack` to `git rev-parse --git-dir`, the per-worktree admin
		# dir, so a stack checked out in a worktree is tracked there and nowhere else
		tree, admin = self.linked_worktree("feat/b")
		(admin / "gh-stack").write_text(json.dumps({"schemaVersion": 1, "repository": "", "stacks": [
			{"number": 7, "trunk": {"branch": "main"}, "branches": [
				{"branch": "feat/a", "pullRequest": {"number": 10}},
				{"branch": "feat/b", "pullRequest": {"number": 11}}]}]}))
		self.write_tracking([])  # the common-dir file v0.1.0 leaves empty beside it
		fixture = {"open_prs": [pr(10, "feat/a"), pr(11, "feat/b", "feat/a")],
				   "graphql": {"pr11": {"number": 11, "stack": stack(7, [(10, "feat/a", "OPEN"), (11, "feat/b", "OPEN")])}}}
		self.fixture.write_text(json.dumps(fixture))
		done = self.run_script("--json", cwd=tree)
		self.assertEqual(done.returncode, 0, done.stderr)
		result = json.loads(done.stdout)
		self.assertEqual(result["rows"][0]["tracked_locally"], {"stack": 7, "branch_exists": True})
		self.assertEqual(result["tracking_files"], [str(admin / "gh-stack"), str((self.repo / ".git" / "gh-stack").resolve())])
		self.assertEqual(result["local_tracking"][0]["file"], str(admin / "gh-stack"))
		table = self.run_script(cwd=tree).stdout
		self.assertIn("tracked here", table)
		self.assertNotIn("`gh stack checkout 11`", table)
		# the main checkout sees only the common-dir file, so the same stack is untracked from there
		self.assertIsNone(self.status("feat/b", fixture=fixture)["rows"][0]["tracked_locally"])

	def test_a_stack_in_both_files_is_listed_once(self) -> None:
		tree, admin = self.linked_worktree("feat/b")
		layers = [{"branch": "feat/a", "pullRequest": {"number": 10}}, {"branch": "feat/b", "pullRequest": {"number": 11}}]
		(admin / "gh-stack").write_text(json.dumps({"schemaVersion": 1, "stacks": [
			{"number": 7, "trunk": {"branch": "main"}, "branches": layers}]}))
		self.write_tracking([{"number": 7, "trunk": {"branch": "main"}, "branches": layers},
							 {"number": 9, "trunk": {"branch": "main"}, "branches": [{"branch": "feat/a", "pullRequest": {"number": 10}}]}])
		fixture = {"open_prs": [pr(10, "feat/a"), pr(11, "feat/b", "feat/a")],
				   "graphql": {"pr11": {"number": 11, "stack": stack(7, [(10, "feat/a", "OPEN"), (11, "feat/b", "OPEN")])}}}
		self.fixture.write_text(json.dumps(fixture))
		result = json.loads(self.run_script("--json", cwd=tree).stdout)
		self.assertEqual(result["gh_stack_version"], "0.1.0")
		self.assertEqual([s["number"] for s in result["local_tracking"]], [7, 9])
		# v0.1.0 reads only this worktree's own file from here, so #9 is listed but not live
		self.assertEqual([s["active"] for s in result["local_tracking"]], [True, False])
		self.assertEqual(result["rows"][0]["tracked_in"], [{"stack": 7, "branch_exists": True}])
		table = self.run_script(cwd=tree).stdout
		self.assertIn("gh stack v0.1.0 tracks per worktree", table)
		self.assertIn("not read by gh stack from this worktree", table)

	def test_v0_2_0_reads_the_common_dir_and_flags_a_leftover_worktree_file(self) -> None:
		tree, admin = self.linked_worktree("feat/b")
		(admin / "gh-stack").write_text(json.dumps({"schemaVersion": 1, "stacks": [
			{"number": 7, "trunk": {"branch": "main"}, "branches": [
				{"branch": "feat/a", "pullRequest": {"number": 10}}, {"branch": "feat/b", "pullRequest": {"number": 11}}]}]}))
		self.write_tracking([{"number": 9, "trunk": {"branch": "main"}, "branches": [{"branch": "feat/a", "pullRequest": {"number": 10}}]}])
		fixture = {"gh_stack_version": "0.2.1", "open_prs": [pr(10, "feat/a"), pr(11, "feat/b", "feat/a")],
				   "graphql": {"pr11": {"number": 11, "stack": stack(7, [(10, "feat/a", "OPEN"), (11, "feat/b", "OPEN")])}}}
		self.fixture.write_text(json.dumps(fixture))
		result = json.loads(self.run_script("--json", cwd=tree).stdout)
		self.assertEqual(result["gh_stack_version"], "0.2.1")
		self.assertEqual([(s["number"], s["active"]) for s in result["local_tracking"]], [(7, False), (9, True)])
		row = result["rows"][0]
		self.assertIsNone(row["tracked_locally"])
		table = self.run_script(cwd=tree).stdout
		self.assertIn("one catalogue for every worktree", table)
		self.assertIn("migrates it", table)
		self.assertIn("`gh stack checkout 11`", table)

	def test_a_stack_in_both_files_reports_the_active_copys_file(self) -> None:
		tree, admin = self.linked_worktree("feat/b")
		layers = [{"branch": "feat/a", "pullRequest": {"number": 10}}]
		(admin / "gh-stack").write_text(json.dumps({"schemaVersion": 1, "stacks": [
			{"number": 7, "trunk": {"branch": "main"}, "branches": layers}]}))
		self.write_tracking([{"number": 7, "trunk": {"branch": "main"}, "branches": layers}])
		self.fixture.write_text(json.dumps({"gh_stack_version": "0.2.1", "open_prs": [pr(10, "feat/a")], "graphql": {}}))
		result = json.loads(self.run_script("--json", cwd=tree).stdout)
		[tracked] = result["local_tracking"]
		self.assertTrue(tracked["active"])
		self.assertEqual(tracked["file"], str((self.repo / ".git" / "gh-stack").resolve()))

	def test_stale_stack_in_another_checkouts_file_says_where_to_unstack(self) -> None:
		tree, _ = self.linked_worktree("feat/b")
		self.write_tracking([{"number": 3, "trunk": {"branch": "main"}, "branches": [
			{"branch": "old/x", "pullRequest": {"number": 1, "merged": True}}]}])
		fixture = {"open_prs": [], "graphql": {}}
		self.fixture.write_text(json.dumps(fixture))
		table = self.run_script(cwd=tree).stdout
		self.assertIn("`gh stack unstack 3 --local`, from the checkout whose file it is in", table)
		self.assertNotIn("from the checkout whose file", self.table("feat/a", fixture=fixture))

	def test_without_the_extension_every_file_counts(self) -> None:
		self.write_tracking([{"number": 7, "trunk": {"branch": "main"}, "branches": [{"branch": "feat/a", "pullRequest": {"number": 10}}]}])
		fixture = {"gh_stack_version": None, "open_prs": [pr(10, "feat/a")], "graphql": {"pr10": {"number": 10, "stack": None}}}
		result = self.status("feat/a", fixture=fixture)
		self.assertIsNone(result["gh_stack_version"])
		self.assertTrue(result["local_tracking"][0]["active"])
		self.assertIn("gh stack is not installed", self.table("feat/a", fixture=fixture))

	def test_no_tracking_file_names_the_paths_looked_in(self) -> None:
		fixture = {"open_prs": [], "graphql": {}}
		table = self.table("feat/a", fixture=fixture)
		self.assertIn("No `gh-stack` file", table)
		self.assertIn(str((self.repo / ".git" / "gh-stack").resolve()), table)

	def test_outside_a_repository_exits_2(self) -> None:
		self.fixture.write_text(json.dumps({"open_prs": []}))
		done = self.run_script("feat/a", cwd=self.root)
		self.assertEqual(done.returncode, 2)
		self.assertIn("not inside a git repository", done.stderr)


if __name__ == "__main__":
	unittest.main()
