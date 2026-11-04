#!/usr/bin/env python3
"""versioning-policy.py: which targets of this repository skip a tag, a release or a changelog.

The policy lives in `.claude/versioning.json` at the repository root, with an
optional gitignored `.claude/versioning.local.json` beside it whose lists are
unioned in. Three lists, each naming targets (`root`, or a plugin name from
`.claude-plugin/marketplace.json`):

	{
		"omit-gh-tag": [],
		"omit-release": ["root"],
		"omit-changelog": []
	}

A GitHub release is created on a tag, so a target in `omit-gh-tag` is treated
as omitted from releases too. A changelog stands alone: a target can keep its
changelog with no tag, or its tag with no changelog.

Where each file is read from. The tracked file comes from the checkout the
script runs in (a landing worktree on origin/main reads main's copy, which is
what should govern a landing), or from a ref with `--ref`, for a caller whose
checkout may sit on any branch. The gitignored twin exists only in the main
checkout, so it is always read from there and written there, whichever linked
worktree the script runs in.

usage:
	versioning-policy.py show [--json] [--ref REF]
	versioning-policy.py check <tag|release|changelog> <target> [--ref REF]
	versioning-policy.py set <omit|allow> <tag|release|changelog> <target> [--local]

exit codes:
	check: 0 the target is omitted, 1 it is not, 2 error
	show, set: 0 ok, 2 error (an unknown target, kind, verb or ref; no repository)

Readers: safe-version-next.sh (tag), pr-land and doc-changelog (release,
changelog). The project-versioning_policy skill is the setter.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

KINDS = ("tag", "release", "changelog")
KEYS = {"tag": "omit-gh-tag", "release": "omit-release", "changelog": "omit-changelog"}
ORDER = ("omit-gh-tag", "omit-release", "omit-changelog")
POLICY = ".claude/versioning.json"
TWIN = ".claude/versioning.local.json"
MANIFEST = ".claude-plugin/marketplace.json"


def git(*args: str) -> subprocess.CompletedProcess:
	return subprocess.run(["git", *args], capture_output=True, text=True)


def toplevel() -> Path:
	done = git("rev-parse", "--show-toplevel")
	if done.returncode != 0:
		raise SystemExit(fail("not inside a git repository"))
	return Path(done.stdout.strip())


def main_checkout(top: Path) -> Path:
	"""The directory holding the gitignored twin: the main checkout, shared by every linked worktree.

	The parent of the common git dir is the main checkout for a plain repository and its linked
	worktrees. A submodule or a --separate-git-dir repository keeps its common dir elsewhere and
	records the work tree in core.worktree, relative to that dir. A bare repository has no main
	checkout, and git before 2.31 has no --path-format; both fall back to the checkout given.
	"""
	done = git("rev-parse", "--path-format=absolute", "--git-common-dir")
	if done.returncode != 0:
		return top
	common = Path(done.stdout.strip())
	configured = git("--git-dir", str(common), "config", "--get", "core.worktree")
	if configured.returncode == 0 and configured.stdout.strip():
		return (common / configured.stdout.strip()).resolve()
	return common.parent if common.name == ".git" else top


def fail(message: str) -> int:
	print(f"✗ {message}", file=sys.stderr)
	return 2


def blob(ref: str, relative: str) -> str | None:
	"""A file's text at a ref, or None when the ref lacks it; an unknown ref is an error."""
	if git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode != 0:
		raise SystemExit(fail(f"unknown ref {ref}"))
	shown = git("show", f"{ref}:{relative}")
	return shown.stdout if shown.returncode == 0 else None


def parse(text: str | None, where: str) -> dict[str, list[str]]:
	if text is None:
		return {key: [] for key in ORDER}
	try:
		data = json.loads(text)
	except json.JSONDecodeError as error:
		raise SystemExit(fail(f"{where}: not valid JSON ({error.msg} at line {error.lineno})"))
	if not isinstance(data, dict):
		raise SystemExit(fail(f"{where}: expected an object with the omit-* lists"))
	out: dict[str, list[str]] = {}
	for key in ORDER:
		value = data.get(key, [])
		if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
			raise SystemExit(fail(f"{where}: {key} must be a list of target names"))
		out[key] = sorted(set(value))
	unknown = sorted(set(data) - set(ORDER))
	if unknown:
		raise SystemExit(fail(f"{where}: unknown key{'s' if len(unknown) > 1 else ''} {', '.join(unknown)}; the keys are {', '.join(ORDER)}"))
	return out


def read(path: Path) -> dict[str, list[str]]:
	return parse(path.read_text() if path.is_file() else None, str(path))


def merged(root: Path, ref: str | None = None) -> dict[str, list[str]]:
	tracked = parse(blob(ref, POLICY), f"{ref}:{POLICY}") if ref else read(root / POLICY)
	local = read(main_checkout(root) / TWIN)
	return {key: sorted(set(tracked[key]) | set(local[key])) for key in ORDER}


def targets(root: Path, ref: str | None = None) -> list[str] | None:
	"""The names a target may take: root plus every plugin the marketplace manifest lists; None when there is no manifest, so any name is accepted."""
	text = blob(ref, MANIFEST) if ref else ((root / MANIFEST).read_text() if (root / MANIFEST).is_file() else None)
	if text is None:
		return None
	try:
		plugins = json.loads(text).get("plugins", [])
	except (json.JSONDecodeError, AttributeError):
		return None
	return ["root"] + sorted(str(p.get("name")) for p in plugins if isinstance(p, dict) and p.get("name"))


def omitted(policy: dict[str, list[str]], kind: str, target: str) -> bool:
	if kind == "release":
		return target in policy["omit-release"] or target in policy["omit-gh-tag"]
	return target in policy[KEYS[kind]]


def write(path: Path, policy: dict[str, list[str]]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	body = "{\n" + ",\n".join(f'\t"{key}": {json.dumps(policy[key])}' for key in ORDER) + "\n}\n"
	path.write_text(body)


def cmd_show(args: argparse.Namespace) -> int:
	root = toplevel()
	policy = merged(root, args.ref)
	if args.json:
		print(json.dumps(policy))
		return 0
	source = f"{args.ref}:{POLICY}" if args.ref else str(root / POLICY)
	present = blob(args.ref, POLICY) is not None if args.ref else (root / POLICY).is_file()
	print(f"policy: {source if present else 'none (every target is tagged, released and given a changelog)'}")
	twin = main_checkout(root) / TWIN
	if twin.is_file():
		print(f"local twin: {twin}")
	for key in ORDER:
		print(f"{key}: {', '.join(policy[key]) or '(none)'}")
	if policy["omit-gh-tag"]:
		print("a target in omit-gh-tag gets no release either: a release needs a tag")
	return 0


def cmd_check(args: argparse.Namespace) -> int:
	root = toplevel()
	known = targets(root, args.ref)
	if known is not None and args.target not in known:
		return fail(f"unknown target {args.target}; the targets are {', '.join(known)}")
	return 0 if omitted(merged(root, args.ref), args.kind, args.target) else 1


def cmd_set(args: argparse.Namespace) -> int:
	root = toplevel()
	known = targets(root)
	if known is not None and args.target not in known:
		return fail(f"unknown target {args.target}; the targets are {', '.join(known)}")
	# the twin lives in the main checkout whichever worktree this runs from; a copy inside a linked worktree would die with it
	path = main_checkout(root) / TWIN if args.local else root / POLICY
	policy = read(path)
	key = KEYS[args.kind]
	before = set(policy[key])
	after = before | {args.target} if args.verb == "omit" else before - {args.target}
	if after == before:
		print(f"{args.target} already {'in' if args.verb == 'omit' else 'absent from'} {key} ({path.name}); nothing written")
		return 0
	policy[key] = sorted(after)
	write(path, policy)
	print(f"{args.target} {'added to' if args.verb == 'omit' else 'removed from'} {key} in {path}")
	if args.verb == "omit" and args.kind == "tag":
		print(f"{args.target} gets no release either: a release needs a tag")
	if args.verb == "allow":
		# the merged policy is what the readers see: an omission the other file still holds, or the tag omission that covers a release, keeps the target omitted
		still = merged(root)
		if args.kind == "release" and args.target in still["omit-gh-tag"]:
			print(f"note: {args.target} is still in omit-gh-tag, which omits its release too; allow tag as well to release it")
		if args.target in still[key]:
			other = Path(POLICY).name if args.local else Path(TWIN).name
			print(f"note: {args.target} is still in {key} in {other}; allow it there as well")
	return 0


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="which targets skip a tag, a release or a changelog")
	sub = parser.add_subparsers(dest="command", required=True)
	show = sub.add_parser("show", help="the merged policy (tracked file plus the local twin)")
	show.add_argument("--json", action="store_true")
	show.add_argument("--ref", help="read the tracked file at this ref (origin/main, say) instead of the checkout")
	show.set_defaults(run=cmd_show)
	check = sub.add_parser("check", help="exit 0 when the target is omitted from the kind, 1 when it is not")
	check.add_argument("kind", choices=KINDS)
	check.add_argument("target")
	check.add_argument("--ref", help="read the tracked file and the marketplace manifest at this ref instead of the checkout; the local twin is read from the main checkout as always")
	check.set_defaults(run=cmd_check)
	setter = sub.add_parser("set", help="omit or allow a target for a kind")
	setter.add_argument("verb", choices=("omit", "allow"))
	setter.add_argument("kind", choices=KINDS)
	setter.add_argument("target")
	setter.add_argument("--local", action="store_true", help="write the gitignored .local twin in the main checkout instead of the tracked file")
	setter.set_defaults(run=cmd_set)
	return parser


def main(argv: list[str]) -> int:
	args = build_parser().parse_args(argv)
	return args.run(args)


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
