#!/usr/bin/env python3
"""Typography gate for Markdown that GitHub renders: PR bodies first.

Catches the faults that render wrongly without ever looking wrong in the
source, each one seen in a real PR:

    setext            a --- (or ===) directly under paragraph text turns
                      that paragraph into a heading
    html-tail         text directly under an HTML block line (</details>,
                      <img>...) joins the HTML block and renders raw
    summary-gap       the same, directly under a <summary> line: the
                      first paragraph of a <details> body renders raw
    summary-backtick  backticks inside <summary> print literally; use <code>
    double-rule       two --- rules with only blank lines between them,
                      left behind when an optional block is dropped

Usage:
    md-lint.py TARGET [TARGET...]     file, or - for stdin
    md-lint.py --hook                 PreToolUse JSON on stdin (see below)

Output matches slop-scan.py --strict: one `L<n> <rule>: <excerpt>` line per
hit, exit 1 on any hit. Fenced code blocks are skipped.

--hook mode backs hooks/pr-body-lint.sh. It reads the Claude Code
PreToolUse payload, pulls the PR body out of a `gh pr create` or
`gh pr edit` command (heredoc on --body-file -, a --body-file path or
--body), and exits 2 with the hits on stderr so the call is blocked and the
hits reach Claude. No body in the command, or anything it cannot parse,
exits 0: the hook fails open.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path

FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
RULE = re.compile(r"^\s{0,3}(-{2,}|={2,})\s*$")
HR = re.compile(r"^\s{0,3}((-\s*){3,}|(\*\s*){3,}|(_\s*){3,})$")
ATX = re.compile(r"^\s{0,3}#{1,6}(\s|$)")
LIST_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])(\s|$)")
QUOTE = re.compile(r"^\s{0,3}>")
TABLE = re.compile(r"^\s*\|")
# CommonMark HTML block types 6 and 7: a line opening with a block-level tag,
# or one tag standing alone. Both run until the next blank line, swallowing
# whatever text follows them. An inline tag leading prose (`<code>x</code>
# does y`) opens nothing; GitHub renders it as a paragraph.
BLOCK_TAGS = (
	"address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt"
	"|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main"
	"|menu|menuitem|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead"
	"|title|tr|track|ul"
)
HTML_LINE = re.compile(
	rf"^\s{{0,3}}(</?({BLOCK_TAGS})(\s|/?>|$)|</?[A-Za-z][A-Za-z0-9-]*(\s[^<>]*)?/?>\s*$)",
	re.I,
)
COMMENT = re.compile(r"^\s{0,3}<!--")
SUMMARY = re.compile(r"<summary>(.*?)</summary>", re.I)


def excerpt(text: str, width: int = 70) -> str:
	text = text.strip()
	return text if len(text) <= width else text[: width - 1] + "…"


def lint(raw: str) -> list[tuple[int, str, str]]:
	"""Return (line number, rule, excerpt) for every hit, in line order."""
	hits: list[tuple[int, str, str]] = []
	in_fence = False
	fence_marker = ""
	in_html = False
	html_flagged = False
	in_comment = False
	paragraph_start: str | None = None
	previous = ""
	last_rule_line = 0
	blank_since_rule = True

	for number, line in enumerate(raw.splitlines(), start=1):
		fence = FENCE.match(line)
		if in_fence:
			if fence and fence.group(1)[0] == fence_marker[0] and len(fence.group(1)) >= len(fence_marker):
				in_fence = False
			previous = line
			continue
		if fence:
			in_fence, fence_marker = True, fence.group(1)
			in_html = False
			paragraph_start = None
			previous = line
			continue

		if in_comment:
			if "-->" in line:
				in_comment = False
			previous = line
			continue

		blank = not line.strip()

		for match in SUMMARY.finditer(line):
			if "`" in match.group(1):
				hits.append((number, "summary-backtick", excerpt(match.group(0))))

		if blank:
			in_html = False
			html_flagged = False
			paragraph_start = None
			previous = line
			continue

		if in_html:
			if not (HTML_LINE.match(line) or COMMENT.match(line)) and not html_flagged:
				rule = "summary-gap" if SUMMARY.search(previous) else "html-tail"
				hits.append((number, rule, excerpt(line)))
				html_flagged = True
			previous = line
			continue

		if COMMENT.match(line):
			if "-->" not in line:
				in_comment = True
			previous = line
			continue

		if RULE.match(line) and paragraph_start is not None:
			opener = paragraph_start
			if not (LIST_ITEM.match(opener) or QUOTE.match(opener) or TABLE.match(opener)):
				hits.append((number, "setext", excerpt(previous)))
			paragraph_start = None
			previous = line
			continue

		if HR.match(line):
			if last_rule_line and blank_since_rule:
				hits.append((number, "double-rule", f"rules on L{last_rule_line} and L{number}"))
			last_rule_line = number
			blank_since_rule = True
			paragraph_start = None
			previous = line
			continue
		blank_since_rule = False

		# Type 6 opens even mid-paragraph; treat every tag-led line as opening.
		if HTML_LINE.match(line):
			in_html = True
			paragraph_start = None
			previous = line
			continue

		if ATX.match(line):
			paragraph_start = None
		elif paragraph_start is None:
			paragraph_start = line
		previous = line

	return hits


def print_hits(hits: list[tuple[int, str, str]], name: str, prefix: bool, stream) -> None:
	for number, rule, text in hits:
		where = f"{name}:L{number}" if prefix else f"L{number}"
		print(f"{where} {rule}: {text}", file=stream)


HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1[^\n]*\n(.*?)\n\s*\2\s*(?:\n|$)", re.S)
GH_PR = re.compile(r"\bgh\s+pr\s+(create|edit)\b")


def body_from_command(command: str, cwd: str) -> str | None:
	"""The PR body a gh pr create/edit command would send, or None."""
	# A gh pr command quoted inside some other heredoc (a file being written) is not a call.
	quoted = [heredoc.span(3) for heredoc in HEREDOC.finditer(command)]
	match = next(
		(found for found in GH_PR.finditer(command) if not any(start <= found.start() < end for start, end in quoted)),
		None,
	)
	if not match:
		return None
	tail = command[match.start():]
	head = tail.split("\n", 1)[0]
	# A heredoc's body is not shell words; otherwise a quoted --body may span lines.
	words = head.split("<<", 1)[0] if "<<" in head else tail
	try:
		tokens = shlex.split(words)
	except ValueError:
		return None
	for index, token in enumerate(tokens):
		key, _, inline = token.partition("=")
		if key not in ("--body-file", "-F", "--body", "-b"):
			continue
		value = inline if inline else (tokens[index + 1] if index + 1 < len(tokens) else None)
		if value is None:
			return None
		if key in ("--body", "-b"):
			return value
		if value == "-":
			heredoc = HEREDOC.search(tail)
			return heredoc.group(3) if heredoc else None
		path = Path(value).expanduser()
		if not path.is_absolute():
			path = Path(cwd) / path
		return path.read_text(encoding="utf-8") if path.is_file() else None
	return None


def hook() -> int:
	try:
		payload = json.load(sys.stdin)
		command = payload.get("tool_input", {}).get("command", "")
		body = body_from_command(command, payload.get("cwd", "."))
	except Exception:
		return 0
	if not body:
		return 0
	hits = lint(body)
	if not hits:
		return 0
	print("md-lint: this PR body renders wrongly on GitHub. Fix each line (usually a missing blank line) and rerun:", file=sys.stderr)
	print_hits(hits, "body", False, sys.stderr)
	return 2


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("targets", nargs="*", help="files to lint, or - for stdin")
	parser.add_argument("--hook", action="store_true", help="read a PreToolUse payload and lint the gh pr body it carries")
	args = parser.parse_args()

	if args.hook:
		return hook()
	if not args.targets:
		parser.error("give a TARGET or --hook")

	missing = [target for target in args.targets if target != "-" and not Path(target).is_file()]
	if missing:
		print("not a file: " + ", ".join(missing), file=sys.stderr)
		return 1

	status = 0
	for target in args.targets:
		raw = sys.stdin.read() if target == "-" else Path(target).read_text(encoding="utf-8")
		hits = lint(raw)
		print_hits(hits, target, len(args.targets) > 1, sys.stdout)
		status |= 1 if hits else 0
	return status


if __name__ == "__main__":
	raise SystemExit(main())
