#!/usr/bin/env python3
"""stack-status.py: what GitHub, the PR bases and the local `gh stack` tracking
each say about a branch's place in a stack, so a skill or hook reads one verdict
instead of guessing from the base branch.

Three sources disagree in practice, and each disagreement is a different fix:

  GitHub stack    the `stack` field on the pull request (GraphQL). Present: the
				  PR is a layer of a linked stack. Absent: GitHub does not know
				  the PR as stacked, whatever its base says.
  PR bases        a PR whose base is another open PR's branch, or whose branch
				  is the base of an open PR, is chained. Chained without a
				  GitHub stack means `gh stack link`, never `gh stack init`.
  local tracking  `<git common dir>/gh-stack`, the file `gh stack` keeps. A
				  branch must be in it for `gh stack sync|rebase|up|down` to
				  work from this checkout; a stack whose every PR has merged is
				  stale there and blocks `gh stack submit` from the trunk.

usage: stack-status.py [--json] [--open] [branch|pr-number|pr-url ...]
  no target     the current branch
  --open        every open pull request in the repository
  --json        one JSON object instead of the table
verdicts: linked | chained-unlinked | independent | no-pr
exit codes: 0 reported, 2 environment or usage error (gh missing, not a repo,
			GitHub unreachable)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

OPEN_PR_FIELDS = "number,headRefName,baseRefName,title,state,isDraft"
STACK_QUERY = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
%s
  }
}
"""
STACK_FRAGMENT = """
	pr%d: pullRequest(number: %d) {
	  number
	  stack {
		number
		size
		baseRefName
		entries(first: 50) { nodes { position pullRequest { number headRefName state } } }
	  }
	}
"""


def fail(message: str) -> None:
	print(message, file=sys.stderr)
	sys.exit(2)


def run(args: list[str], cwd: str | None = None) -> str | None:
	try:
		done = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=30)
	except (OSError, subprocess.TimeoutExpired):
		return None
	return done.stdout.strip() if done.returncode == 0 else None


def run_json(args: list[str], cwd: str | None = None):
	out = run(args, cwd)
	if out is None:
		return None
	try:
		return json.loads(out)
	except ValueError:
		return None


def default_branch(cwd: str) -> str:
	head = run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd)
	if head and "/" in head:
		return head.split("/", 1)[1]
	name = run(["gh", "repo", "view", "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name"], cwd)
	return name or "main"


def repo_owner_name(cwd: str) -> tuple[str, str]:
	info = run_json(["gh", "repo", "view", "--json", "owner,name"], cwd)
	if not info:
		fail("gh repo view failed: not a GitHub repository, or gh is not signed in")
	return info["owner"]["login"], info["name"]


def open_prs(cwd: str) -> list[dict]:
	prs = run_json(["gh", "pr", "list", "--state", "open", "--limit", "200", "--json", OPEN_PR_FIELDS], cwd)
	if prs is None:
		fail("gh pr list failed: GitHub unreachable or gh not signed in")
	return prs


def github_stacks(numbers: list[int], cwd: str) -> dict[int, dict | None]:
	"""PR number -> its GitHub stack (or None), in one GraphQL call."""
	if not numbers:
		return {}
	owner, name = repo_owner_name(cwd)
	body = "".join(STACK_FRAGMENT % (n, n) for n in numbers)
	data = run_json(["gh", "api", "graphql", "-f", "query=" + STACK_QUERY % body,
					 "-F", "owner=" + owner, "-F", "name=" + name], cwd)
	if not data or "data" not in data:
		fail("GitHub GraphQL query for stack membership failed")
	repository = data["data"]["repository"] or {}
	stacks = {}
	for n in numbers:
		pr = repository.get("pr%d" % n)
		stack = (pr or {}).get("stack")
		if stack:
			stack["entries"] = [
				{"position": e["position"], "number": e["pullRequest"]["number"],
				 "branch": e["pullRequest"]["headRefName"], "state": e["pullRequest"]["state"]}
				for e in stack["entries"]["nodes"]]
		stacks[n] = stack
	return stacks


def local_tracking(cwd: str) -> list[dict]:
	"""Every stack in `<git common dir>/gh-stack`, with staleness judged offline."""
	common = run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd)
	if not common:
		return []
	path = Path(common) / "gh-stack"
	if not path.is_file():
		return []
	try:
		data = json.loads(path.read_text())
	except ValueError:
		return []
	stacks = []
	for stack in data.get("stacks", []):
		branches = [b.get("branch") for b in stack.get("branches", [])]
		merged = [bool((b.get("pullRequest") or {}).get("merged")) for b in stack.get("branches", [])]
		missing = [b for b in branches
				   if run(["git", "show-ref", "--verify", "--quiet", "refs/heads/%s" % b], cwd) is None]
		stacks.append({
			"number": stack.get("number"),
			"trunk": (stack.get("trunk") or {}).get("branch"),
			"branches": branches,
			"prs": [(b.get("pullRequest") or {}).get("number") for b in stack.get("branches", [])],
			"stale": bool(branches) and all(merged),
			"missing_branches": missing,
		})
	return stacks


def worktrees(cwd: str) -> dict[str, str]:
	"""branch -> worktree path, from `git worktree list --porcelain`."""
	out = run(["git", "worktree", "list", "--porcelain"], cwd) or ""
	mapping, path = {}, None
	for line in out.splitlines():
		if line.startswith("worktree "):
			path = line[len("worktree "):]
		elif line.startswith("branch refs/heads/") and path:
			mapping[line[len("branch refs/heads/"):]] = path
	return mapping


def resolve_target(target: str, prs_by_head: dict[str, dict], cwd: str) -> tuple[str | None, dict | None]:
	"""(branch, open PR dict or None) for a branch name, PR number or PR URL."""
	if target in prs_by_head:
		return target, prs_by_head[target]
	if target.lstrip("#").isdigit() or "/pull/" in target:
		pr = run_json(["gh", "pr", "view", target.lstrip("#"), "--json", OPEN_PR_FIELDS], cwd)
		if pr:
			return pr["headRefName"], pr if pr["state"] == "OPEN" else None
		return None, None
	return target, None


def verdict_for(branch: str | None, pr: dict | None, stack: dict | None, default: str,
				prs_by_base: dict[str, list[dict]]) -> str:
	if pr is None:
		return "no-pr"
	if stack:
		return "linked"
	if pr["baseRefName"] != default or prs_by_base.get(pr["headRefName"]):
		return "chained-unlinked"
	return "independent"


def chain_of(pr: dict, prs_by_head: dict[str, dict], default: str) -> list[dict]:
	"""The open PRs from the bottom of the base chain up to `pr`, bottom first."""
	chain, seen, current = [], set(), pr
	while current and current["number"] not in seen:
		seen.add(current["number"])
		chain.append(current)
		if current["baseRefName"] == default:
			break
		current = prs_by_head.get(current["baseRefName"])
	return list(reversed(chain))


def report(targets: list[str], all_open: bool, cwd: str) -> dict:
	default = default_branch(cwd)
	prs = open_prs(cwd)
	prs_by_head = {pr["headRefName"]: pr for pr in prs}
	prs_by_base: dict[str, list[dict]] = {}
	for pr in prs:
		prs_by_base.setdefault(pr["baseRefName"], []).append(pr)
	tracking = local_tracking(cwd)
	tracked_in = {b: s for s in tracking for b in s["branches"]}
	trees = worktrees(cwd)

	if all_open:
		resolved = [(pr["headRefName"], pr) for pr in prs]
	else:
		resolved = [resolve_target(t, prs_by_head, cwd) for t in targets]
	numbers = [pr["number"] for _, pr in resolved if pr]
	stacks = github_stacks(numbers, cwd)

	rows = []
	for branch, pr in resolved:
		stack = stacks.get(pr["number"]) if pr else None
		tracked = tracked_in.get(branch) if branch else None
		if tracked is not None:
			tracked = {"stack": tracked["number"], "branch_exists": branch not in tracked["missing_branches"]}
		rows.append({
			"branch": branch,
			"pr": pr["number"] if pr else None,
			"title": pr["title"] if pr else None,
			"base": pr["baseRefName"] if pr else None,
			"draft": pr["isDraft"] if pr else None,
			"github_stack": stack,
			"chain": [p["number"] for p in chain_of(pr, prs_by_head, default)] if pr else [],
			"children": [p["number"] for p in prs_by_base.get(branch or "", [])],
			"tracked_locally": tracked,
			"worktree": trees.get(branch) if branch else None,
			"verdict": verdict_for(branch, pr, stack, default, prs_by_base),
		})
	return {"default_branch": default, "rows": rows, "local_tracking": tracking}


def describe_stack(stack: dict | None, number: int | None) -> str:
	if not stack:
		return "none"
	position = next((e["position"] for e in stack["entries"] if e["number"] == number), "?")
	return "#%s, layer %s of %s" % (stack["number"], position, stack["size"])


def print_table(result: dict) -> None:
	print("## Stack Status")
	print()
	print("| Branch | PR | Base | GitHub stack | Tracked locally | Worktree | Verdict |")
	print("|---|---|---|---|---|---|---|")
	for row in result["rows"]:
		print("| %s | %s | %s | %s | %s | %s | %s |" % (
			row["branch"] or "?", "#%s" % row["pr"] if row["pr"] else "none", row["base"] or "",
			describe_stack(row["github_stack"], row["pr"]), describe_tracking(row["tracked_locally"]),
			row["worktree"] or "none", row["verdict"]))
	print()
	print("## Local Tracking")
	print()
	if not result["local_tracking"]:
		print("No `gh-stack` file: nothing tracked in this checkout.")
	for stack in result["local_tracking"]:
		label = "#%s" % stack["number"] if stack["number"] else "local only, not submitted"
		notes = []
		if stack["stale"]:
			notes.append("stale: every PR has merged")
		if stack["missing_branches"]:
			notes.append("not checked out here: " + ", ".join(stack["missing_branches"]))
		state = " (%s)" % "; ".join(notes) if notes else ""
		print("- %s on %s: %s%s" % (label, stack["trunk"], ", ".join(stack["branches"]), state))
	print()
	print("## Next")
	print()
	for row in result["rows"]:
		print("- %s" % next_step(row, result["default_branch"]))
	stale = [s for s in result["local_tracking"] if s["stale"] and s["number"]]
	for stack in stale:
		print("- stack #%s is stale in local tracking: `gh stack unstack %s --local`" % (stack["number"], stack["number"]))


def describe_tracking(tracked: dict | None) -> str:
	if tracked is None:
		return "no"
	label = "#%s" % tracked["stack"] if tracked["stack"] else "local only"
	return label if tracked["branch_exists"] else label + " (branch missing)"


def next_step(row: dict, default: str) -> str:
	branch = row["branch"] or "?"
	if row["verdict"] == "no-pr":
		return "%s has no open PR: nothing to stack yet" % branch
	if row["verdict"] == "independent":
		return "%s (#%s) is an ordinary PR on %s" % (branch, row["pr"], default)
	if row["verdict"] == "chained-unlinked":
		chain = " ".join(str(n) for n in row["chain"] + row["children"])
		return ("%s (#%s) is chained by base but GitHub holds no stack: `gh stack link %s` (bottom to top), "
				"not `gh stack init`" % (branch, row["pr"], chain))
	stack_number = row["github_stack"]["number"]
	tracked = row["tracked_locally"]
	if tracked is None or not tracked["branch_exists"]:
		return ("%s (#%s) is a layer of stack #%s but %s: `gh stack checkout %s` before `gh stack sync`, "
				"`rebase`, `up` or `down`" % (branch, row["pr"], stack_number,
											  "not tracked here" if tracked is None else "the branch is not checked out here",
											  row["pr"]))
	return "%s (#%s) is %s and tracked here: `gh stack` commands work from this checkout" % (
		branch, row["pr"], describe_stack(row["github_stack"], row["pr"]).replace("#", "layer of stack #", 1))


def main(argv: list[str]) -> int:
	as_json, all_open, targets = False, False, []
	for arg in argv:
		if arg == "--json":
			as_json = True
		elif arg == "--open":
			all_open = True
		elif arg.startswith("-"):
			fail("unknown option %s\n%s" % (arg, __doc__))
		else:
			targets.append(arg)
	cwd = os.getcwd()
	if run(["git", "rev-parse", "--is-inside-work-tree"], cwd) != "true":
		fail("not inside a git repository")
	if run(["gh", "--version"], cwd) is None:
		fail("gh not installed")
	if not all_open and not targets:
		current = run(["git", "branch", "--show-current"], cwd)
		if not current:
			fail("detached HEAD and no target given")
		targets = [current]
	result = report(targets, all_open, cwd)
	if as_json:
		print(json.dumps(result, indent=2))
	else:
		print_table(result)
	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
