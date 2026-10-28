#!/usr/bin/env python3
"""Guard for what `gh` posts to GitHub: bodies from files, release notes that exist.

Two classes of mistake, each seen in a real session:

    inline-body       a comment, review or reply body given inline on the
                      command line (`gh api -f body='...'`, `gh pr comment
                      --body '...'`): shell quoting strips apostrophes, and
                      the permission classifier reads words inside the body
                      as part of the command
    release-notes     `gh release create` with no notes source, inline
                      `--notes`, or a notes file that is empty: a BSD sed
                      incompatibility once produced an empty notes file and
                      two releases went out with blank bodies

Usage:
    gh-guard.py --hook                        PreToolUse JSON on stdin
    gh-guard.py --command TEXT [--cwd DIR]    check one command by hand

Exit 2 with the reason on stderr when a rule trips, so the call is blocked
and the reason reaches Claude. Exit 0 otherwise. Anything the script cannot
parse or evaluate exits 0: the hook fails open. A notes path holding a shell
variable, a file the same command writes first or a relative path behind a
`cd` cannot be read at hook time, so none of those blocks.

Allowed shapes: `-F body=@<file>`, `--body-file <file>`, `--body-file -` and
`--input -` fed by a heredoc, `--notes-file <non-empty file>`, `--notes-file -`
fed by a non-blank heredoc, `--generate-notes`, `--notes-from-tag`.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path

HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1[^\n]*\n(.*?)\n\s*\2\s*(?:\n|$)", re.S)
GH_CALL = re.compile(r"\bgh\s+(api|pr\s+comment|pr\s+review|issue\s+comment|release\s+create|release\s+edit)\b")

BODY_ADVICE = (
	"write the body to a file in the session scratchpad directory and pass `-F body=@<file>` (gh api) "
	"or `--body-file <file>` (gh pr/issue): apostrophes get stripped from quoted strings and the classifier "
	"trips on words inside them. A heredoc on `--body-file -` or `--input -` is fine too."
)
NOTES_ADVICE = (
	"release notes must come from `--notes-file <file>` naming a non-empty file (or `--notes-file -` fed by a "
	"non-blank heredoc), `--generate-notes` or `--notes-from-tag`. A BSD sed incompatibility once wrote an empty "
	"notes file and two releases went out blank; check the file before publishing."
)


def _inside_quotes(text: str) -> bool:
	"""Whether a shell reading `text` would still be inside a single- or double-quoted string at its end."""
	quote = None
	index = 0
	while index < len(text):
		char = text[index]
		if quote == "'":
			if char == "'":
				quote = None
		elif quote == '"':
			if char == "\\":
				index += 1
			elif char == '"':
				quote = None
		elif char == "\\":
			index += 1
		elif char in ("'", '"'):
			quote = char
		index += 1
	return quote is not None


def _calls(command: str) -> list[tuple[str, str, str]]:
	"""Every (subcommand, tail, prefix) for a gh call that is a real call: not inside a heredoc body and not inside a quoted string.

	The prefix is the command text before the call, with heredoc bodies blanked, so a caller can see a `cd` or a redirect that ran first."""
	quoted = [heredoc.span(3) for heredoc in HEREDOC.finditer(command)]
	blanked = command
	for start, end in reversed(quoted):
		blanked = blanked[:start] + " " * (end - start) + blanked[end:]
	matches = [
		found for found in GH_CALL.finditer(command)
		if not any(start <= found.start() < end for start, end in quoted) and not _inside_quotes(blanked[: found.start()])
	]
	calls = []
	for index, found in enumerate(matches):
		end = matches[index + 1].start() if index + 1 < len(matches) else len(command)
		calls.append((re.sub(r"\s+", " ", found.group(1)), command[found.start():end], blanked[: found.start()]))
	return calls


def _tokens(tail: str) -> tuple[list[str] | None, list[str]]:
	"""Shell words of a call with heredoc bodies blanked out, plus those bodies in order."""
	heredocs = list(HEREDOC.finditer(tail))
	words = tail
	for heredoc in reversed(heredocs):
		words = words[: heredoc.start(3)] + words[heredoc.end():]
	try:
		return shlex.split(words), [heredoc.group(3) for heredoc in heredocs]
	except ValueError:
		return None, []


def _flag_values(tokens: list[str], flags: tuple[str, ...]) -> list[tuple[str, str | None]]:
	"""(flag, value) for every occurrence of the flags, inline `=` form included; value None when the flag ends the line."""
	found = []
	for index, token in enumerate(tokens):
		key, equals, inline = token.partition("=")
		if key not in flags:
			continue
		if equals:
			found.append((key, inline))
		else:
			found.append((key, tokens[index + 1] if index + 1 < len(tokens) else None))
	return found


def _notes_file_ok(value: str, heredocs: list[str], cwd: str) -> bool:
	if value == "-":
		return bool(heredocs) and bool(heredocs[0].strip())
	path = Path(value).expanduser()
	if not path.is_absolute():
		path = Path(cwd) / path
	try:
		return path.is_file() and bool(path.read_text(encoding="utf-8").strip())
	except OSError:
		return False


UNEVALUABLE = re.compile(r"[$`]")
MOVED_OR_WROTE = re.compile(r"(^|[;&|(\s])cd\s|>")


def check_call(subcommand: str, tail: str, cwd: str, prefix: str = "") -> str | None:
	"""The reason this gh call should be blocked, or None. `prefix` is what ran before the call on the same line."""
	tokens, heredocs = _tokens(tail)
	if tokens is None:
		return None

	if subcommand == "api":
		for flag, value in _flag_values(tokens, ("-f", "--raw-field", "-F", "--field")):
			if value is None or not value.startswith("body="):
				continue
			body = value[len("body="):]
			if flag in ("-F", "--field") and body.startswith("@"):
				continue
			if flag in ("-f", "--raw-field") and body.startswith("@"):
				return f"gh api: `{flag} body=@...` posts the literal text `{body}`; use `-F body=@<file>` so gh reads the file."
			return f"gh api: inline `{flag} body=...`; {BODY_ADVICE}"
		return None

	if subcommand in ("pr comment", "pr review", "issue comment"):
		for flag, _ in _flag_values(tokens, ("-b", "--body")):
			return f"gh {subcommand}: inline `{flag}`; {BODY_ADVICE}"
		return None

	if subcommand in ("release create", "release edit"):
		for flag, _ in _flag_values(tokens, ("-n", "--notes")):
			return f"gh {subcommand}: inline `{flag}`; {NOTES_ADVICE}"
		files = _flag_values(tokens, ("-F", "--notes-file"))
		for flag, value in files:
			if value is not None and value != "-" and (UNEVALUABLE.search(value) or MOVED_OR_WROTE.search(prefix)):
				continue  # a variable, a file this command writes first or a path behind a cd: not readable at hook time
			if value is None or not _notes_file_ok(value, heredocs, cwd):
				where = "the heredoc is blank" if value == "-" else f"`{value}` is missing or empty"
				return f"gh {subcommand}: `{flag}` {where}; {NOTES_ADVICE}"
		if subcommand == "release edit":
			return None
		generated = any(token in ("--generate-notes", "--notes-from-tag") or token.startswith("--notes-from-tag=") for token in tokens)
		if files or generated:
			return None
		return f"gh release create: no notes source; {NOTES_ADVICE}"

	return None


def check_command(command: str, cwd: str) -> str | None:
	for subcommand, tail, prefix in _calls(command):
		reason = check_call(subcommand, tail, cwd, prefix)
		if reason:
			return reason
	return None


def hook() -> int:
	try:
		payload = json.load(sys.stdin)
		command = payload.get("tool_input", {}).get("command", "")
		reason = check_command(command, payload.get("cwd", "."))
	except Exception:
		return 0
	if not reason:
		return 0
	print(f"gh-guard: {reason}", file=sys.stderr)
	return 2


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--hook", action="store_true", help="read a PreToolUse payload on stdin and check the gh call it carries")
	parser.add_argument("--command", help="check this command text")
	parser.add_argument("--cwd", default=".", help="directory relative paths resolve against (with --command)")
	args = parser.parse_args()

	if args.hook:
		return hook()
	if args.command is None:
		parser.error("give --command TEXT or --hook")
	reason = check_command(args.command, args.cwd)
	if not reason:
		return 0
	print(f"gh-guard: {reason}", file=sys.stderr)
	return 2


if __name__ == "__main__":
	raise SystemExit(main())
