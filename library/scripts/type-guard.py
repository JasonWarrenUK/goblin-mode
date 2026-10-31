#!/usr/bin/env python3
"""type-guard.py: keeps domain intent in type definitions (clod-approach-types).

The preference ("an identifier is never a bare string, a status is a closed
set") faded a few compactions into every long session. This script is the
part of the fix that survives compaction: three Claude Code hook modes, each
reading the hook payload on stdin, plus a by-hand scan.

usage:
	type-guard.py remind      PreToolUse (matcher Edit|Write). When the text about to
	                          be written declares a type (interface, class, dataclass,
	                          struct ...), prints the reminder as additionalContext.
	                          At most once per session every REMIND_EVERY_MINUTES, so
	                          it cannot nag.
	type-guard.py scan        PostToolUse (matcher Edit|Write). Runs the ast-grep rules
	                          in library/ast-grep over the .ts or .py file just written.
	                          A hit prints one `L<n> <rule> (<text>): <fix>` line per
	                          finding to stderr and exits 2, so Claude fixes the file
	                          before moving on.
	type-guard.py compact     SessionStart (matcher compact). Prints the reminder as
	                          additionalContext, because compaction is exactly where
	                          the preference used to vanish.
	type-guard.py --file PATH Scan one file by hand; findings on stdout, exit 1 on a hit.

Per-repo opt-out:   git config typeGuard.enforce false    (scan)
                    git config typeGuard.remind false     (remind and compact)
Everything off:     TYPE_GUARD_OFF=1
ast-grep location:  on PATH, in the usual install dirs or in TYPE_GUARD_AST_GREP=/path

Fail-open: no ast-grep, no payload, no reminder file or any exception means
exit 0 and silence in hook mode, never a blocked edit. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
RULES_CONFIG = REPO_ROOT / "library" / "ast-grep" / "sgconfig.yml"
REMINDER = REPO_ROOT / "skills" / "clod-approach-types" / "reminder.md"
REMIND_EVERY_MINUTES = 30

# Paths the scan and the reminder both leave alone: generated or vendored
# trees, type declaration bundles and test files (a fixture-local shape is
# noise, and the compiler already rejects a bare string where a branded type
# is expected).
SKIP_PATH = re.compile(r"(^|/)(node_modules|dist|build|\.svelte-kit|\.venv|venv|__pycache__)/|\.d\.ts$")
TEST_FILE = re.compile(r"\.(test|spec)\.[cm]?tsx?$|(^|/)(test_[^/]*\.py|[^/]*_test\.py|conftest\.py)$")

# What counts as "about to declare a type" per language, for the reminder.
DECLARES_TYPE = {
	"ts": re.compile(r"\b(interface|type|enum|class)\s+[A-Z]\w*"),
	"py": re.compile(r"^\s*class\s+\w+|@dataclass|BaseModel|TypedDict|NamedTuple|NewType\(", re.MULTILINE),
	"go": re.compile(r"\btype\s+\w+\s+(struct|interface|string|u?int\w*|float\w*)\b"),
}
SCANNED = {"ts", "py"}


def language(path: str) -> str | None:
	suffix = Path(path).suffix.lower()
	if suffix in {".ts", ".mts", ".cts", ".tsx"}:
		return "ts"
	if suffix in {".py", ".pyi"}:
		return "py"
	if suffix == ".go":
		return "go"
	return None


def skipped(path: str) -> bool:
	normalised = path.replace("\\", "/")
	return bool(SKIP_PATH.search(normalised) or TEST_FILE.search(normalised))


def git_bool(key: str, cwd: str) -> bool:
	"""True unless the repo at cwd sets the key to false. No git, no repo: True."""
	try:
		out = subprocess.run(
			["git", "config", "--type=bool", "--get", key],
			cwd=cwd, capture_output=True, text=True, timeout=5,
		)
	except Exception:
		return True
	return out.stdout.strip() != "false"


def find_ast_grep() -> str | None:
	override = os.environ.get("TYPE_GUARD_AST_GREP")
	if override and Path(override).is_file():
		return override
	found = shutil.which("ast-grep")
	if found:
		return found
	home = Path.home()
	for candidate in (
		home / ".bun" / "bin" / "ast-grep",
		Path("/opt/homebrew/bin/ast-grep"),
		Path("/usr/local/bin/ast-grep"),
		home / ".cargo" / "bin" / "ast-grep",
		home / ".local" / "bin" / "ast-grep",
	):
		if candidate.is_file():
			return str(candidate)
	return None


def scan_file(path: str, ast_grep: str) -> list[str]:
	"""One `L<n> <rule> (<text>): <fix>` line per finding, in line order."""
	out = subprocess.run(
		[ast_grep, "scan", "-c", str(RULES_CONFIG), "--json=compact", path],
		capture_output=True, text=True, timeout=60,
	)
	findings = json.loads(out.stdout or "[]")
	lines: list[tuple[int, str]] = []
	for finding in findings:
		n = finding["range"]["start"]["line"] + 1
		text = " ".join(finding["text"].split())
		fix = finding.get("message", "").strip()
		lines.append((n, f"L{n} {finding['ruleId']} ({text}): {fix}"))
	return [line for _, line in sorted(lines)]


def reminder_text() -> str:
	for candidate in (REMINDER, Path.home() / ".claude" / "skills" / "clod-approach-types" / "reminder.md"):
		if candidate.is_file():
			return candidate.read_text(encoding="utf-8").strip()
	return ""


def emit_context(event: str, text: str) -> None:
	print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}))


def state_dir() -> Path:
	configured = os.environ.get("TYPE_GUARD_STATE_DIR")
	return Path(configured) if configured else Path(tempfile.gettempdir()) / "type-guard"


def stamp_for(session_id: str) -> Path:
	return state_dir() / re.sub(r"[^\w.-]", "_", session_id or "no-session")


def due(session_id: str) -> bool:
	"""True once per REMIND_EVERY_MINUTES per session; touching the stamp starts the window."""
	stamp = stamp_for(session_id)
	stamp.parent.mkdir(parents=True, exist_ok=True)
	if stamp.exists() and time.time() - stamp.stat().st_mtime < REMIND_EVERY_MINUTES * 60:
		return False
	stamp.touch()
	return True


def _file_path(payload: dict) -> str:
	return str(payload.get("tool_input", {}).get("file_path", "") or "")


def _new_text(payload: dict) -> str:
	tool_input = payload.get("tool_input", {})
	return str(tool_input.get("content") or tool_input.get("new_string") or "")


def remind(payload: dict) -> int:
	path = _file_path(payload)
	lang = language(path)
	if not lang or skipped(path):
		return 0
	if not DECLARES_TYPE[lang].search(_new_text(payload)):
		return 0
	if not git_bool("typeGuard.remind", str(Path(path).parent) if path else "."):
		return 0
	if not due(str(payload.get("session_id", ""))):
		return 0
	text = reminder_text()
	if text:
		emit_context("PreToolUse", text)
	return 0


def compact(payload: dict) -> int:
	if not git_bool("typeGuard.remind", str(payload.get("cwd") or ".")):
		return 0
	text = reminder_text()
	if not text:
		return 0
	emit_context("SessionStart", text)
	# The reminder is now in fresh context; start the remind window from here.
	stamp = stamp_for(str(payload.get("session_id", "")))
	stamp.parent.mkdir(parents=True, exist_ok=True)
	stamp.touch()
	return 0


def scan(payload: dict) -> int:
	path = _file_path(payload)
	if language(path) not in SCANNED or skipped(path) or not Path(path).is_file():
		return 0
	if not git_bool("typeGuard.enforce", str(Path(path).parent)):
		return 0
	ast_grep = find_ast_grep()
	if not ast_grep:
		return 0
	hits = scan_file(path, ast_grep)
	if not hits:
		return 0
	print("type-guard: the types just written carry no domain intent (see clod-approach-types); fix these before moving on:", file=sys.stderr)
	for hit in hits:
		print(hit, file=sys.stderr)
	return 2


def hook(mode: str) -> int:
	if os.environ.get("TYPE_GUARD_OFF"):
		return 0
	try:
		payload = json.load(sys.stdin)
		if not isinstance(payload, dict):
			return 0
		return {"remind": remind, "scan": scan, "compact": compact}[mode](payload)
	except Exception:
		return 0


def by_hand(path: str) -> int:
	ast_grep = find_ast_grep()
	if not ast_grep:
		print("type-guard: ast-grep not found (install it, or set TYPE_GUARD_AST_GREP)", file=sys.stderr)
		return 2
	if not Path(path).is_file():
		print(f"type-guard: no such file: {path}", file=sys.stderr)
		return 2
	hits = scan_file(path, ast_grep)
	for hit in hits:
		print(hit)
	return 1 if hits else 0


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("mode", nargs="?", choices=["remind", "scan", "compact"], help="hook mode; reads the payload on stdin")
	parser.add_argument("--file", help="scan this file by hand instead")
	args = parser.parse_args()
	if args.file:
		return by_hand(args.file)
	if not args.mode:
		parser.error("give a hook mode or --file PATH")
	return hook(args.mode)


if __name__ == "__main__":
	sys.exit(main())
