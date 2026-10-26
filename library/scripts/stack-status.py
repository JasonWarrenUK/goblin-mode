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
				  A base no open PR owns (`release/1.x`) is not a chain.
  local tracking  the `gh-stack` file `gh stack` keeps. v0.1.0 writes it to
				  `git rev-parse --git-dir`, so a linked worktree has its own
				  (`.git/worktrees/<name>/gh-stack`) and the main checkout's is
				  `.git/gh-stack`; v0.2.0 moved it to `<git common dir>/gh-stack`,
				  one file for every worktree. `gh stack --version` decides
				  which file counts here; the other is listed, not trusted. A
				  branch must be in it for `gh stack sync|rebase|up|down` to
				  work from this checkout; a stack whose every PR has merged is
				  stale there and blocks `gh stack submit` from the trunk. The
				  file's own `merged` flag only refreshes on `gh stack sync`, so
				  staleness is judged from GitHub's PR state.

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

OPEN_PR_FIELDS = "number,headRefName,baseRefName,title,state,isDraft,isCrossRepository"
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
STATE_FRAGMENT = "\tst%d: pullRequest(number: %d) { state }\n"


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


def github_lookups(numbers: list[int], state_numbers: list[int], cwd: str) -> tuple[dict[int, dict | None], dict[int, str | None]]:
	"""(PR number -> its GitHub stack or None, PR number -> its state or None), in one GraphQL call."""
	if not numbers and not state_numbers:
		return {}, {}
	owner, name = repo_owner_name(cwd)
	body = "".join(STACK_FRAGMENT % (n, n) for n in numbers) + "".join(STATE_FRAGMENT % (n, n) for n in state_numbers)
	# -f, not -F: -F turns an all-digit owner or repo name into an integer the String! variables reject
	data = run_json(["gh", "api", "graphql", "-f", "query=" + STACK_QUERY % body,
					 "-f", "owner=" + owner, "-f", "name=" + name], cwd)
	if not data or "data" not in data:
		fail("GitHub GraphQL query for stack membership failed")
	repository = data["data"]["repository"] or {}
	states = {n: (repository.get("st%d" % n) or {}).get("state") for n in state_numbers}
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
	return stacks, states


def gh_stack_version(cwd: str) -> str | None:
	"""The installed extension's version (`gh stack --version` prints `gh stack version 0.1.0`), or None."""
	out = run(["gh", "stack", "--version"], cwd)
	if not out:
		return None
	return out.strip().split()[-1].lstrip("v")


def version_tuple(version: str | None) -> tuple[int, ...]:
	parts = []
	for piece in (version or "0").split("."):
		digits = "".join(ch for ch in piece if ch.isdigit())
		parts.append(int(digits) if digits else 0)
	return tuple(parts)


SHARED_CATALOGUE_SINCE = (0, 2, 0)


def tracking_paths(cwd: str, version: str | None) -> list[tuple[Path, bool]]:
	"""(path a `gh-stack` file can be at, whether the installed version reads it from here).

	gh-stack v0.1.0 joins the file onto `git rev-parse --git-dir`, which in a linked worktree
	is the per-worktree admin dir (`.git/worktrees/<name>/`), so each worktree tracks on its
	own and the common-dir file is dead from there. v0.2.0 moved it to the common dir, one
	catalogue for every worktree, and migrates the old files on first run, so from then on
	a per-worktree file is a leftover. In the main checkout the two are one directory. With
	no extension installed the version is unknown and both files count."""
	shared = version_tuple(version) >= SHARED_CATALOGUE_SINCE
	paths: list[tuple[Path, bool]] = []
	for flag, active in (("--git-dir", version is None or not shared), ("--git-common-dir", version is None or shared)):
		out = run(["git", "rev-parse", "--path-format=absolute", flag], cwd)
		if not out:
			continue
		path = (Path(out) / "gh-stack").resolve()
		if any(path == p for p, _ in paths):
			paths[:] = [(p, a or active) for p, a in paths]
			continue
		paths.append((path, active))
	return paths


def local_tracking(cwd: str, version: str | None) -> tuple[list[dict], list[str]]:
	"""(every stack in the `gh-stack` files this checkout can see, the files that exist).

	Each stack says which file it came from and whether `gh stack` reads that file from this
	checkout (`active`). A stack recorded identically in both files is listed once, as active if
	either copy is. Staleness is judged in report(), once GitHub has been asked."""
	stacks: list[dict] = []
	seen: dict[tuple, dict] = {}
	files: list[str] = []
	for path, active in tracking_paths(cwd, version):
		if not path.is_file():
			continue
		try:
			data = json.loads(path.read_text())
		except ValueError:
			continue
		files.append(str(path))
		for stack in data.get("stacks", []):
			branches = [b.get("branch") for b in stack.get("branches", [])]
			key = (stack.get("number"), tuple(branches))
			if key in seen:
				if active and not seen[key]["active"]:
					seen[key].update(active=True, file=str(path))
				continue
			merged = [bool((b.get("pullRequest") or {}).get("merged")) for b in stack.get("branches", [])]
			missing = [b for b in branches
					   if run(["git", "show-ref", "--verify", "--quiet", "refs/heads/%s" % b], cwd) is None]
			seen[key] = {
				"number": stack.get("number"),
				"trunk": (stack.get("trunk") or {}).get("branch"),
				"branches": branches,
				"prs": [(b.get("pullRequest") or {}).get("number") for b in stack.get("branches", [])],
				"merged": merged,
				"stale": False,
				"missing_branches": missing,
				"file": str(path),
				"active": active,
			}
			stacks.append(seen[key])
	return stacks, files


def judge_staleness(tracking: list[dict], open_numbers: set[int], states: dict[int, str | None]) -> None:
	"""A stack is stale when every layer has a PR that is no longer open and has merged.

	The tracking file's own `merged` flag counts, but it lags GitHub until `gh stack sync`
	runs, so a PR it does not flag is judged from GitHub's state. An unknown state, a closed
	PR and a layer with no PR yet all keep the stack live."""
	for stack in tracking:
		stack["stale"] = bool(stack["prs"]) and all(
			n is not None and n not in open_numbers and (merged or states.get(n) == "MERGED")
			for n, merged in zip(stack["prs"], stack["merged"]))


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
				prs_by_head: dict[str, dict], prs_by_base: dict[str, list[dict]]) -> str:
	if pr is None:
		return "no-pr"
	if stack:
		return "linked"
	if pr["isCrossRepository"]:
		return "independent"
	base = pr["baseRefName"]
	if (base != default and base in prs_by_head) or prs_by_base.get(pr["headRefName"]):
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


def climb(pr: dict, prs_by_base: dict[str, list[dict]]) -> tuple[list[dict], list[dict]]:
	"""(open PRs above `pr` while each has exactly one child, the children where the climb forked).

	A stack is one line, so a PR with two open children ends the climb: the fork is
	returned and the caller names one candidate per child."""
	above, seen, current = [], {pr["number"]}, pr
	while True:
		children = prs_by_base.get(current["headRefName"], [])
		if len(children) != 1 or children[0]["number"] in seen:
			return above, children if len(children) > 1 else []
		current = children[0]
		seen.add(current["number"])
		above.append(current)


def report(targets: list[str], all_open: bool, cwd: str) -> dict:
	default = default_branch(cwd)
	prs = open_prs(cwd)
	# a fork's head branch name says nothing about this repository's branches, and a stack lives in one repository
	same_repo = [pr for pr in prs if not pr["isCrossRepository"]]
	prs_by_head = {pr["headRefName"]: pr for pr in same_repo}
	prs_by_base: dict[str, list[dict]] = {}
	for pr in same_repo:
		prs_by_base.setdefault(pr["baseRefName"], []).append(pr)
	version = gh_stack_version(cwd)
	tracking, tracking_files = local_tracking(cwd, version)
	tracked_in: dict[str, list[dict]] = {}
	for tracked_stack in tracking:
		if not tracked_stack["active"]:
			continue  # listed for information; `gh stack` will not read it from this checkout
		for tracked_branch in tracked_stack["branches"]:
			tracked_in.setdefault(tracked_branch, []).append(tracked_stack)
	trees = worktrees(cwd)

	if all_open:
		resolved = [(pr["headRefName"], pr) for pr in prs]
	else:
		resolved = [resolve_target(t, prs_by_head, cwd) for t in targets]
	numbers = [pr["number"] for _, pr in resolved if pr]
	open_numbers = {pr["number"] for pr in prs}
	unflagged = sorted({n for s in tracking for n, merged in zip(s["prs"], s["merged"])
						if n is not None and n not in open_numbers and not merged})
	stacks, states = github_lookups(numbers, unflagged, cwd)
	judge_staleness(tracking, open_numbers, states)

	rows = []
	for branch, pr in resolved:
		stack = stacks.get(pr["number"]) if pr else None
		foreign = bool(pr and pr["isCrossRepository"])
		entries = [{"stack": s["number"], "branch_exists": branch not in s["missing_branches"]}
				   for s in tracked_in.get(branch, [])] if branch and not foreign else []
		github_number = stack["number"] if stack else None
		# the single-stack shape stays for consumers: the entry GitHub agrees with, else the first
		tracked = next((e for e in entries if e["stack"] == github_number), entries[0] if entries else None)
		above, fork = climb(pr, prs_by_base) if pr and not foreign else ([], [])
		chain = [p["number"] for p in chain_of(pr, prs_by_head, default)] if pr and not foreign else [pr["number"]] if pr else []
		rows.append({
			"branch": branch,
			"pr": pr["number"] if pr else None,
			"title": pr["title"] if pr else None,
			"base": pr["baseRefName"] if pr else None,
			"draft": pr["isDraft"] if pr else None,
			"github_stack": stack,
			"chain": chain,
			"children": [] if foreign else [p["number"] for p in prs_by_base.get(branch or "", [])],
			"link_order": chain + [p["number"] for p in above],
			"fork": [p["number"] for p in fork],
			"tracked_locally": tracked,
			"tracked_in": entries,
			"worktree": trees.get(branch) if branch and not foreign else None,
			"verdict": verdict_for(branch, pr, stack, default, prs_by_head, prs_by_base),
		})
	return {"default_branch": default, "rows": rows, "local_tracking": tracking, "gh_stack_version": version,
			"tracking_files": tracking_files, "tracking_paths": [str(p) for p, _ in tracking_paths(cwd, version)]}


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
			describe_stack(row["github_stack"], row["pr"]), describe_tracking(row["tracked_locally"], row["tracked_in"]),
			row["worktree"] or "none", row["verdict"]))
	print()
	print("## Local Tracking")
	print()
	print(describe_version(result["gh_stack_version"]))
	if not result["tracking_files"]:
		print("No `gh-stack` file: nothing tracked in this checkout. Looked in %s." % ", ".join(
			"`%s`" % p for p in result["tracking_paths"]))
	elif not result["local_tracking"]:
		print("Nothing tracked in this checkout (%s)." % ", ".join("`%s`" % p for p in result["tracking_files"]))
	else:
		for path in result["tracking_files"]:
			print("Read from `%s`." % path)
	for stack in result["local_tracking"]:
		label = "#%s" % stack["number"] if stack["number"] else "local only, not submitted"
		notes = []
		if not stack["active"]:
			notes.append("in `%s`, not read by gh stack from this worktree" % stack["file"])
			if version_tuple(result["gh_stack_version"]) >= SHARED_CATALOGUE_SINCE:
				notes.append("a pre-0.2.0 leftover: the next `gh stack` command migrates it")
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
		where = "" if stack["active"] else ", from the checkout whose file it is in (`%s`)" % stack["file"]
		print("- stack #%s is stale in local tracking: `gh stack unstack %s --local`%s" % (stack["number"], stack["number"], where))


def describe_version(version: str | None) -> str:
	if version is None:
		return "gh stack is not installed (`gh extension install github/gh-stack`); every tracking file found is listed."
	if version_tuple(version) >= SHARED_CATALOGUE_SINCE:
		return "gh stack v%s keeps one catalogue for every worktree in the git common dir." % version
	return "gh stack v%s tracks per worktree: only the file in this checkout's own git dir counts here." % version


def describe_tracking(tracked: dict | None, entries: list[dict]) -> str:
	if tracked is None:
		return "no"
	if len(entries) > 1:
		return "in %d stacks: %s" % (len(entries), ", ".join("#%s" % e["stack"] if e["stack"] else "local only" for e in entries))
	label = "#%s" % tracked["stack"] if tracked["stack"] else "local only"
	return label if tracked["branch_exists"] else label + " (branch missing)"


def next_step(row: dict, default: str) -> str:
	branch = row["branch"] or "?"
	if row["verdict"] == "no-pr":
		return "%s has no open PR: nothing to stack yet" % branch
	if row["verdict"] == "independent":
		return "%s (#%s) is an ordinary PR on %s" % (branch, row["pr"], row["base"] or default)
	if row["verdict"] == "chained-unlinked":
		order = " ".join(str(n) for n in row["link_order"])
		if row["fork"]:
			options = " or ".join("`gh stack link %s %d`" % (order, n) for n in row["fork"])
			return ("%s (#%s) is chained by base but the chain forks above #%s into %s: a stack is one line, so link "
					"one path (%s) and retarget the other" % (
						branch, row["pr"], row["link_order"][-1], ", ".join("#%d" % n for n in row["fork"]), options))
		return ("%s (#%s) is chained by base but GitHub holds no stack: `gh stack link %s` (bottom to top), "
				"not `gh stack init`" % (branch, row["pr"], order))
	stack_number = row["github_stack"]["number"]
	tracked = row["tracked_locally"]
	if len(row["tracked_in"]) > 1:
		numbers = [e["stack"] for e in row["tracked_in"]]
		return ("%s (#%s) is tracked in %d local stacks (%s): `gh stack` refuses it until all but one are removed, "
				"`gh stack unstack <n> --local`" % (
					branch, row["pr"], len(numbers), ", ".join("#%s" % n if n else "local only" for n in numbers)))
	if tracked is None or not tracked["branch_exists"]:
		return ("%s (#%s) is a layer of stack #%s but %s: `gh stack checkout %s` before `gh stack sync`, "
				"`rebase`, `up` or `down`" % (branch, row["pr"], stack_number,
											  "not tracked here" if tracked is None else "the branch is not checked out here",
											  row["pr"]))
	return "%s (#%s) is %s and tracked here: `gh stack` commands work from this checkout" % (
		branch, row["pr"], describe_stack(row["github_stack"], row["pr"]).replace("#", "in stack #", 1))


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
