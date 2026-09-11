#!/usr/bin/env python3
"""Health check for the prose-gating suite: is every layer still wired?

One PASS / WARN / FAIL line per check, then the output-quality trend from
prose-metrics.py (recorded as a side effect). Exit 1 when anything FAILs.
The deterministic half of the hud-prose_health skill.

Checks:
  settings     outputStyle at user level, attribution trailers cleared
  style        keep-coding-instructions on, style file passes strict scan
  hook         core.hooksPath, commit-msg executable, live reject/pass test
  hook-log     rejections vs passes in the last 7 and 28 days
  skills       the prose and commit skills still carry their gate text
  frontmatter  every skill, agent and style frontmatter parses as YAML
  tree         strict scan over the context-loaded files
  tests        test_slop_scan.py, test_prose_metrics.py and test_commit_msg_hook.py
  index        gen-skills-index.py --check
  output       house-rule rate in Claude's own terminal output, last 7 days

Usage:
    prose-health.py [--no-record] [--json]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
SCRIPTS = CONFIG_DIR / "library" / "scripts"
SCAN = SCRIPTS / "slop-scan.py"
HOOK = CONFIG_DIR / "hooks" / "commit-msg"
HOOK_LOG = CONFIG_DIR / "library" / "state" / "commit-msg-log.jsonl"
STYLE = CONFIG_DIR / "output-styles" / "british-dev-goblin.md"

# Residual strict hits accepted at the last audit (clause-joining commas the
# Oxford pattern cannot tell from list commas, plus one vendored line).
KNOWN_RESIDUALS = 12

SKILL_WIRING = {
	"pr-create": ["slop-scan.py --strict", "Bash(~/.claude/library/scripts/slop-scan.py:*)"],
	"pr-update": ["slop-scan.py --strict", "Bash(~/.claude/library/scripts/slop-scan.py:*)"],
	"doc-readme": ["slop-scan.py --strict", "Bash(~/.claude/library/scripts/slop-scan.py:*)"],
	"doc-changelog": ["slop-scan.py --strict", "Bash(~/.claude/library/scripts/slop-scan.py:*)"],
	"commit-one": ["commit-msg:", "Never pass `--no-verify`"],
	"commit-batch": ["commit-msg:", "Never pass `--no-verify`"],
	"next-task-ship": ["commit-msg:", "Never pass `--no-verify`"],
	"clod-role-git_manager": ["hooks/commit-msg"],
}

Result = tuple[str, str, str]  # (status, check, detail)


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
	return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def frontmatter(path: Path) -> str | None:
	match = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf-8", errors="replace"), re.S)
	return match.group(1) if match else None


# ------------------------------------------------------------------ checks


def check_settings() -> Result:
	try:
		settings = json.loads((CONFIG_DIR / "settings.json").read_text(encoding="utf-8"))
	except (OSError, json.JSONDecodeError) as error:
		return ("FAIL", "settings", f"settings.json unreadable: {error}")
	problems = []
	if settings.get("outputStyle") != "british-dev-goblin":
		problems.append(f"outputStyle={settings.get('outputStyle')!r}, expected british-dev-goblin")
	attribution = settings.get("attribution", {})
	if attribution.get("commit") or attribution.get("pr") or attribution.get("sessionUrl", True):
		problems.append("attribution trailers not cleared")
	if problems:
		return ("FAIL", "settings", "; ".join(problems))
	return ("PASS", "settings", "outputStyle at user level, attribution cleared")


def check_style() -> Result:
	if not STYLE.is_file():
		return ("FAIL", "style", f"{STYLE.name} missing")
	head = frontmatter(STYLE) or ""
	problems = []
	if not re.search(r"^keep-coding-instructions:\s*true\s*$", head, re.M):
		problems.append("keep-coding-instructions is not true")
	scan = run([sys.executable, str(SCAN), "--strict", str(STYLE)])
	if scan.returncode:
		problems.append(f"{len(scan.stdout.splitlines())} strict hit(s) in the style file")
	if problems:
		return ("FAIL", "style", "; ".join(problems))
	return ("PASS", "style", "keep-coding-instructions on, file passes strict scan")


def check_hook() -> Result:
	problems = []
	hooks_path = run(["git", "config", "--global", "core.hooksPath"]).stdout.strip()
	if Path(hooks_path).expanduser() != CONFIG_DIR / "hooks":
		problems.append(f"core.hooksPath={hooks_path or 'unset'}")
	if not HOOK.is_file():
		return ("FAIL", "hook", "hooks/commit-msg missing")
	if not os.access(HOOK, os.X_OK):
		problems.append("hooks/commit-msg not executable")
	if not shutil.which("python3"):
		problems.append("python3 not on PATH (hook fails open)")
	env = {**os.environ, "SLOP_NO_LOG": "1"}
	with tempfile.TemporaryDirectory() as tmp:
		bad = Path(tmp) / "bad"
		bad.write_text("fix: tidy — again\n", encoding="utf-8")
		good = Path(tmp) / "good"
		good.write_text("fix: tidy again\n", encoding="utf-8")
		if run(["sh", str(HOOK), str(bad)], cwd=tmp, env=env).returncode == 0:
			problems.append("hook accepted an em dash")
		if run(["sh", str(HOOK), str(good)], cwd=tmp, env=env).returncode != 0:
			problems.append("hook rejected a clean message")
	if problems:
		return ("FAIL", "hook", "; ".join(problems))
	return ("PASS", "hook", "global hooksPath, executable, rejects and passes correctly")


def check_hook_log() -> Result:
	if not HOOK_LOG.is_file():
		return ("WARN", "hook-log", "no commits logged yet")
	now = dt.datetime.now(dt.timezone.utc)
	counts = {7: [0, 0], 28: [0, 0]}
	for line in HOOK_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
		try:
			entry = json.loads(line)
			when = dt.datetime.fromisoformat(entry["ts"].replace("Z", "+00:00"))
		except (json.JSONDecodeError, KeyError, ValueError):
			continue
		age = (now - when).days
		for window, pair in counts.items():
			if age < window:
				pair[0 if entry.get("result") == "reject" else 1] += 1
	r7, p7 = counts[7]
	r28, p28 = counts[28]
	total7 = r7 + p7
	rate = f"{100 * r7 / total7:.0f}%" if total7 else "n/a"
	return ("PASS", "hook-log", f"7d: {r7} rejected / {total7} commits ({rate}); 28d: {r28} / {r28 + p28}")


def check_skills() -> Result:
	missing = []
	for skill, needles in SKILL_WIRING.items():
		path = CONFIG_DIR / "skills" / skill / "SKILL.md"
		text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
		for needle in needles:
			if needle not in text:
				missing.append(f"{skill}: {needle}")
	if missing:
		return ("FAIL", "skills", "; ".join(missing))
	return ("PASS", "skills", f"{len(SKILL_WIRING)} skills carry their gate text")


def check_frontmatter() -> Result:
	try:
		import yaml
	except ImportError:
		return ("WARN", "frontmatter", "PyYAML not installed; skipped")
	files = sorted((CONFIG_DIR / "skills").glob("*/SKILL.md")) + sorted((CONFIG_DIR / "agents").glob("*.md")) + [STYLE]
	broken = []
	for path in files:
		head = frontmatter(path)
		if head is None:
			broken.append(f"{path.relative_to(CONFIG_DIR)} (none)")
			continue
		try:
			yaml.safe_load(head)
		except yaml.YAMLError:
			broken.append(str(path.relative_to(CONFIG_DIR)))
	if broken:
		return ("FAIL", "frontmatter", "; ".join(broken))
	return ("PASS", "frontmatter", f"{len(files)} frontmatter blocks parse")


def context_files() -> list[Path]:
	skip = ("node_modules", "skill-creator", "pytest_cache", "reasonable-colors-reference.md")
	files = [CONFIG_DIR / "CLAUDE.md", STYLE]
	for base in ("agents", "skills", "library/templates", "library/references"):
		files += sorted(p for p in (CONFIG_DIR / base).rglob("*.md") if not any(s in str(p) for s in skip))
	docs = CONFIG_DIR / "docs"
	files += [docs / "README.md", docs / "architecture.md", docs / "glossary.md"]
	files += sorted((docs / "reference").glob("*.md")) + sorted((docs / "guides").glob("*.md"))
	files += sorted((docs / "reference" / "task-trackers").glob("*.md"))
	return [f for f in files if f.is_file()]


def check_tree() -> tuple[Result, list[str]]:
	scan = run([sys.executable, str(SCAN), "--strict", *map(str, context_files())], cwd=CONFIG_DIR)
	hits = [line for line in scan.stdout.splitlines() if "American -or 'color': color:" not in line]
	if len(hits) > KNOWN_RESIDUALS:
		return ("WARN", "tree", f"{len(hits)} strict hits, {KNOWN_RESIDUALS} accepted at last audit"), hits
	return ("PASS", "tree", f"{len(hits)} strict hits, within the {KNOWN_RESIDUALS} accepted"), []


def check_tests() -> Result:
	tests = [SCRIPTS / "test_slop_scan.py", SCRIPTS / "test_prose_metrics.py", SCRIPTS / "test_commit_msg_hook.py"]
	result = run([sys.executable, "-m", "pytest", "-q", *map(str, tests)], cwd=SCRIPTS)
	summary = (result.stdout.strip().splitlines() or ["no output"])[-1]
	return ("PASS" if result.returncode == 0 else "FAIL", "tests", summary)


def check_index() -> Result:
	result = run([sys.executable, str(SCRIPTS / "gen-skills-index.py"), "--check"], cwd=CONFIG_DIR)
	detail = (result.stdout.strip() or result.stderr.strip()).splitlines()[-1:] or ["no output"]
	return ("PASS" if result.returncode == 0 else "WARN", "index", detail[0])


def check_output(record: bool) -> tuple[Result, str]:
	args = [sys.executable, str(SCRIPTS / "prose-metrics.py"), "--days", "14", "--json"]
	if record:
		args.append("--record")
	result = run(args)
	try:
		rows = json.loads(result.stdout)
	except json.JSONDecodeError:
		return ("WARN", "output", "prose-metrics.py produced no rows"), result.stderr.strip()
	cutoff = (dt.date.today() - dt.timedelta(days=7)).isoformat()
	recent = [row for day, row in rows.items() if day >= cutoff]
	words = sum(row["words"] for row in recent)
	if not words:
		return ("WARN", "output", "no assistant output in the last 7 days"), ""
	em = sum(row["emdash"] + row["endash"] for row in recent)
	house = sum(sum(row[k] for k in ("emdash", "endash", "oxford", "ize", "amer_or", "amer_er", "amer_use")) for row in recent)
	em_rate = 1000 * em / words
	house_rate = 1000 * house / words
	status = "PASS" if em_rate <= 0.5 else "WARN" if em_rate <= 3 else "FAIL"
	detail = f"7d: {em_rate:.2f} em dashes and {house_rate:.2f} house-rule hits per 1k words over {words} words"
	table = run([sys.executable, str(SCRIPTS / "prose-metrics.py"), "--days", "14"]).stdout.rstrip()
	return (status, "output", detail), table


# -------------------------------------------------------------------- main


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--no-record", action="store_true", help="do not write prose-metrics.json")
	parser.add_argument("--json", action="store_true", help="emit results as JSON")
	args = parser.parse_args()

	results: list[Result] = [check_settings(), check_style(), check_hook(), check_hook_log(), check_skills(), check_frontmatter()]
	tree, tree_hits = check_tree()
	results.append(tree)
	results += [check_tests(), check_index()]
	output, table = check_output(record=not args.no_record)
	results.append(output)

	if args.json:
		print(json.dumps({"results": [dict(zip(("status", "check", "detail"), r)) for r in results], "tree_hits": tree_hits, "metrics": table}, indent=1))
	else:
		print(f"prose-health  {dt.date.today().isoformat()}")
		for status, check, detail in results:
			print(f"{status:4}  {check:12} {detail}")
		if tree_hits:
			print("\ntree hits:")
			for hit in tree_hits:
				print(f"  {hit}")
		if table:
			print(f"\n{table}")
	return 1 if any(status == "FAIL" for status, _, _ in results) else 0


if __name__ == "__main__":
	raise SystemExit(main())
