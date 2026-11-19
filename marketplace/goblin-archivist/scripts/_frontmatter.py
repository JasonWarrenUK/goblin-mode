"""Frontmatter reading for goblin-archivist, standard library only.

Python ships no YAML parser, so this reads the subset of YAML that Obsidian
properties use: scalars, quoted strings, flow lists, block lists and block
scalars. Anything valid but outside that subset (nested maps, lists of maps,
anchors, flow maps) comes back as an `Unparsed` value holding its raw text,
never a guess. Anything that is not valid YAML at all marks the whole block
invalid, as Obsidian does when it shows no properties for a broken block.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field

__all__ = ['Frontmatter', 'Unparsed', 'parse_scalar', 'read_frontmatter', 'split_frontmatter']


@dataclass(frozen=True)
class Unparsed:
	"""A value that is valid YAML but outside the subset this module reads."""

	raw: str
	reason: str


@dataclass
class Frontmatter:
	"""What one note's frontmatter block held."""

	present: bool = False
	raw: str = ''
	properties: dict[str, object] = field(default_factory=dict)
	errors: list[str] = field(default_factory=list)
	duplicates: list[str] = field(default_factory=list)
	body: str = ''
	body_line: int = 1

	@property
	def is_valid(self) -> bool:
		return self.present and not self.errors


_FENCE = re.compile(r'^---\s*$')
_CLOSE = re.compile(r'^(---|\.\.\.)\s*$')
_KEY = re.compile(
	r"""^(?P<key>"(?:[^"\\]|\\.)*"|'(?:[^']|'')*'|[^\s#'"\-?:,\[\]{}&*!|>%@`][^:]*?|-[^\s:][^:]*?)\s*:(?=\s|$)\s*(?P<rest>.*)$"""
)
_INT = re.compile(r'^[-+]?[0-9]+$')
_OCT = re.compile(r'^0o[0-7]+$')
_HEX = re.compile(r'^0x[0-9a-fA-F]+$')
_FLOAT = re.compile(r'^[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?$')
_BLOCK_HEADER = re.compile(r'^[|>]([+-]?[1-9]?|[1-9][+-])\s*(#.*)?$')
_BARE_WIKILINK = re.compile(r'^\[\[[^\[\]]+\]\]$')
_BARE_WIKILINK_REASON = 'unquoted [[link]], which YAML reads as a list inside a list'


def split_frontmatter(text: str) -> tuple[str | None, str, int, str | None]:
	"""Split a note into (frontmatter text, body, body's first line number, problem).

	The frontmatter text is None when the note has no block. A note that opens
	with `---` and never closes it has no block either, and the problem says so.
	"""
	if text.startswith('﻿'):
		text = text[1:]
	lines = text.split('\n')
	if not lines or not _FENCE.match(lines[0].rstrip('\r')):
		return None, text, 1, None
	for index in range(1, len(lines)):
		if _CLOSE.match(lines[index].rstrip('\r')):
			raw = '\n'.join(line.rstrip('\r') for line in lines[1:index])
			body = '\n'.join(lines[index + 1:])
			return raw, body, index + 2, None
	return None, text, 1, 'frontmatter opens with --- and never closes'


def read_frontmatter(text: str) -> Frontmatter:
	"""Read one note's frontmatter into a `Frontmatter`."""
	raw, body, body_line, problem = split_frontmatter(text)
	if raw is None:
		result = Frontmatter(body=body, body_line=body_line)
		if problem:
			result.errors.append(problem)
		return result
	result = Frontmatter(present=True, raw=raw, body=body, body_line=body_line)
	properties, errors, duplicates = _parse_block(raw)
	result.errors.extend(errors)
	result.duplicates.extend(duplicates)
	result.properties = {} if errors else properties
	return result


class _Invalid(Exception):
	pass


def _indent(line: str) -> int:
	return len(line) - len(line.lstrip(' '))


def _is_blank_or_comment(line: str) -> bool:
	stripped = line.strip()
	return stripped == '' or stripped.startswith('#')


def _parse_block(raw: str) -> tuple[dict[str, object], list[str], list[str]]:
	lines = raw.split('\n')
	properties: dict[str, object] = {}
	duplicates: list[str] = []
	index = 0
	try:
		for number, line in enumerate(lines, start=1):
			if line.startswith('\t') and line.strip():
				raise _Invalid(f'line {number}: a tab used for indentation')
		while index < len(lines):
			line = lines[index]
			if _is_blank_or_comment(line):
				index += 1
				continue
			if _indent(line) != 0:
				raise _Invalid(f'line {index + 1}: indented line with no key above it')
			match = _KEY.match(line)
			if not match:
				raise _Invalid(f'line {index + 1}: expected `key: value`')
			key = _unquote_key(match.group('key'), index + 1)
			rest = match.group('rest')
			key_line = index + 1
			children: list[str] = []
			index += 1
			while index < len(lines):
				candidate = lines[index]
				if candidate.strip() == '' or candidate.lstrip().startswith('#'):
					children.append(candidate)
					index += 1
					continue
				if _indent(candidate) > 0 or (rest.strip() == '' and _starts_sequence_item(candidate)):
					children.append(candidate)
					index += 1
					continue
				break
			while children and (children[-1].strip() == '' or children[-1].startswith('#')):
				children.pop()
			value = _parse_value(rest, children, key_line + 1)
			if key in properties:
				duplicates.append(key)
			properties[key] = value
	except _Invalid as problem:
		return {}, [str(problem)], duplicates
	return properties, [], duplicates


def _starts_sequence_item(line: str) -> bool:
	stripped = line.lstrip(' ')
	return stripped == '-' or stripped.startswith('- ')


def _unquote_key(key: str, number: int) -> str:
	if key.startswith('"'):
		return _double_quoted(key, number)
	if key.startswith("'"):
		return key[1:-1].replace("''", "'")
	return key.strip()


_COMMENT = re.compile(r'(^|[ \t])#')


def _strip_comment(text: str) -> str:
	"""Drop a plain scalar's trailing comment: a `#` at the start or after a space or tab."""
	match = _COMMENT.search(text)
	return text if match is None else text[: match.start()]


def _parse_value(rest: str, children: list[str], first_child_line: int) -> object:
	text = rest.strip()
	if text == '' or text.startswith('#'):
		children = [child for child in children if not child.lstrip().startswith('#')]
		while children and children[-1].strip() == '':
			children.pop()
		if not any(child.strip() for child in children):
			return None
		first = next(child for child in children if child.strip())
		if _starts_sequence_item(first):
			return _block_sequence(children, first_child_line)
		if _KEY.match(first.strip()):
			return Unparsed(_dedent(children), 'nested map')
		raise _Invalid(f'line {first_child_line}: indented text under an empty key')
	if _BLOCK_HEADER.match(text):
		return _block_scalar(text, children)
	if text.startswith('['):
		joined = ' '.join([text] + [child.strip() for child in children])
		return _flow_sequence(joined, first_child_line)
	if text.startswith('{'):
		return Unparsed('\n'.join([rest] + children), 'flow map')
	if text[0] in '&*!':
		return Unparsed('\n'.join([rest] + children), 'anchor, alias or explicit tag')
	if text[0] in '"\'':
		joined = _fold_lines([text] + [child.strip() for child in children])
		value, tail = _quoted_prefix(joined, first_child_line)
		if _strip_comment(' ' + tail).strip():
			raise _Invalid(f'line {first_child_line - 1}: text after a closing quote')
		return value
	if text.startswith('- ') or text == '-':
		raise _Invalid(f'line {first_child_line - 1}: a list item on the same line as its key')
	if text[0] in '@`|>%':
		raise _Invalid(f'line {first_child_line - 1}: a plain value cannot start with {text[0]!r}')
	parts = [_strip_comment(text).strip()]
	for child in children:
		stripped = child.strip()
		if stripped.startswith('#'):
			continue
		if _KEY.match(stripped):
			raise _Invalid(f'line {first_child_line}: a key under a value that already has text')
		parts.append(_strip_comment(stripped).strip())
	plain = _fold_lines(parts)
	if ': ' in plain or plain.endswith(':'):
		raise _Invalid(f'line {first_child_line - 1}: a plain value holds `: `; quote it')
	return parse_scalar(plain)


def _fold_lines(parts: list[str]) -> str:
	"""Join continuation lines the way YAML folds a multi-line flow scalar."""
	out: list[str] = []
	for part in parts:
		if part == '':
			out.append('\n')
		elif out and out[-1] != '\n':
			out.append(' ' + part)
		else:
			out.append(part)
	return ''.join(out)


def _dedent(children: list[str]) -> str:
	widths = [_indent(child) for child in children if child.strip()]
	width = min(widths) if widths else 0
	return '\n'.join(child[width:] for child in children)


def _block_scalar(header: str, children: list[str]) -> str:
	style = header[0]
	chomp = '+' if '+' in header else '-' if '-' in header.split('#')[0] else ''
	text_lines = _dedent(children).split('\n') if children else []
	if style == '|':
		content = '\n'.join(text_lines)
	else:
		folded: list[str] = []
		for line in text_lines:
			if line == '':
				folded.append('\n')
			elif folded and folded[-1] != '\n':
				folded.append(' ' + line)
			else:
				folded.append(line)
		content = ''.join(folded)
	if chomp == '-':
		return content.rstrip('\n')
	if chomp == '+':
		return content + '\n'
	return content.rstrip('\n') + '\n' if content else ''


def _block_sequence(children: list[str], first_line: int) -> object:
	items: list[object] = []
	item_indent = _indent(next(child for child in children if child.strip()))
	current: list[str] | None = None
	current_line = first_line
	for offset, child in enumerate(children):
		if child.strip() == '':
			if current is not None:
				current.append('')
			continue
		width = _indent(child)
		if width == item_indent and _starts_sequence_item(child):
			if current is not None:
				items.append(_sequence_item(current, current_line))
			current = [child.strip()[1:].strip()]
			current_line = first_line + offset
		elif width > item_indent and current is not None:
			current.append(child.strip())
		else:
			raise _Invalid(f'line {first_line + offset}: list item out of line')
	if current is not None:
		items.append(_sequence_item(current, current_line))
	for item in items:
		if isinstance(item, Unparsed):
			return Unparsed(_dedent(children), item.reason)
	return items


def _sequence_item(parts: list[str], line: int) -> object:
	while parts and parts[-1] == '':
		parts.pop()
	head = parts[0] if parts else ''
	if head == '' and len(parts) > 1:
		return Unparsed('\n'.join(parts), 'list item holding a nested block')
	if _KEY.match(head):
		return Unparsed('\n'.join(parts), 'list of maps')
	if head.startswith('- ') or head == '-':
		return Unparsed('\n'.join(parts), 'list of lists')
	if _BARE_WIKILINK.match(head):
		return Unparsed('\n'.join(parts), _BARE_WIKILINK_REASON)
	if head.startswith('['):
		return Unparsed('\n'.join(parts), 'list of lists')
	if head.startswith('{'):
		return Unparsed('\n'.join(parts), 'list of maps')
	if head.startswith(('"', "'")):
		value, tail = _quoted_prefix(_fold_lines(parts), line)
		if _strip_comment(' ' + tail).strip():
			raise _Invalid(f'line {line}: text after a closing quote')
		return value
	return parse_scalar(_fold_lines([_strip_comment(part).strip() for part in parts]))


def _flow_chars(text: str, previous: str = '') -> Iterator[tuple[int, str, bool]]:
	"""Walk a flow collection: (position, character, inside a quoted item).

	A quote opens a quoted item only where an item starts, after `[`, `{`, `,`
	or `:`, so the apostrophe in `[Bob's plan]` is plain text. Inside double
	quotes a backslash escapes the next character; inside single quotes `''`
	is a quote.
	"""
	quote = ''
	position = 0
	while position < len(text):
		char = text[position]
		if quote:
			if quote == '"' and char == '\\':
				yield position, char, True
				if position + 1 < len(text):
					yield position + 1, text[position + 1], True
				position += 2
				continue
			if char == quote and quote == "'" and text[position + 1: position + 2] == "'":
				yield position, char, True
				yield position + 1, char, True
				position += 2
				continue
			if char == quote:
				quote = ''
				previous = char
			yield position, char, True
			position += 1
			continue
		if char in '"\'' and previous in ('', '[', '{', ',', ':'):
			quote = char
			yield position, char, True
			position += 1
			continue
		yield position, char, False
		if not char.isspace():
			previous = char
		position += 1


def _flow_sequence(text: str, line: int) -> object:
	depth = 0
	end = -1
	for position, char, quoted in _flow_chars(text):
		if quoted:
			continue
		if char in '[{':
			depth += 1
		elif char in ']}':
			depth -= 1
			if depth == 0:
				end = position
				break
	if end < 0:
		raise _Invalid(f'line {line - 1}: a flow list that never closes')
	if _strip_comment(' ' + text[end + 1:]).strip():
		raise _Invalid(f'line {line - 1}: text after a flow list')
	inner = text[1:end]
	if _BARE_WIKILINK.match(text[: end + 1]):
		return Unparsed(text[: end + 1], _BARE_WIKILINK_REASON)
	if '[' in _outside_quotes(inner) or '{' in _outside_quotes(inner):
		return Unparsed(text[: end + 1], 'nested flow collection')
	items: list[object] = []
	for piece in _split_commas(inner):
		piece = piece.strip()
		if piece == '':
			continue
		if piece[0] in '"\'':
			value, tail = _quoted_prefix(piece, line)
			if tail.strip():
				raise _Invalid(f'line {line - 1}: text after a closing quote in a flow list')
			items.append(value)
		else:
			items.append(parse_scalar(piece))
	return items


def _outside_quotes(text: str) -> str:
	"""The characters of a flow list's inside that are not in a quoted item."""
	return ''.join(char for _, char, quoted in _flow_chars(text, '[') if not quoted)


def _split_commas(text: str) -> list[str]:
	"""A flow list's inside split at the commas outside quoted items."""
	pieces: list[str] = []
	current: list[str] = []
	for _, char, quoted in _flow_chars(text, '['):
		if char == ',' and not quoted:
			pieces.append(''.join(current))
			current = []
		else:
			current.append(char)
	pieces.append(''.join(current))
	return pieces


def _quoted_prefix(text: str, line: int) -> tuple[str, str]:
	"""Read the quoted string at the start of text; return (value, what follows)."""
	quote = text[0]
	position = 1
	while position < len(text):
		char = text[position]
		if quote == '"' and char == '\\':
			position += 2
			continue
		if char == quote:
			if quote == "'" and position + 1 < len(text) and text[position + 1] == "'":
				position += 2
				continue
			body = text[: position + 1]
			value = _double_quoted(body, line) if quote == '"' else body[1:-1].replace("''", "'")
			return value, text[position + 1:]
		position += 1
	raise _Invalid(f'line {line - 1}: a quoted string that never closes')


_ESCAPES = {'n': '\n', 't': '\t', '"': '"', '\\': '\\', '/': '/', '0': '\0', 'r': '\r', ' ': ' '}


def _double_quoted(body: str, line: int) -> str:
	inner = body[1:-1]
	out: list[str] = []
	position = 0
	while position < len(inner):
		char = inner[position]
		if char != '\\':
			out.append(char)
			position += 1
			continue
		code = inner[position + 1: position + 2]
		if code in _ESCAPES:
			out.append(_ESCAPES[code])
			position += 2
		elif code in ('x', 'u', 'U'):
			width = {'x': 2, 'u': 4, 'U': 8}[code]
			digits = inner[position + 2: position + 2 + width]
			try:
				point = int(digits, 16)
			except ValueError as problem:
				raise _Invalid(f'line {line}: a bad \\{code} escape') from problem
			position += 2 + width
			if 0xD800 <= point <= 0xDBFF:
				# The JSON spelling of a character beyond the first plane: a high
				# surrogate escape must be followed by a low one, and the two are one.
				low = inner[position: position + 6]
				if not re.fullmatch(r'\\u[dD][c-fC-F][0-9a-fA-F]{2}', low):
					raise _Invalid(f'line {line}: a \\u surrogate escape with no partner')
				point = 0x10000 + ((point - 0xD800) << 10) + (int(low[2:], 16) - 0xDC00)
				position += 6
			elif 0xDC00 <= point <= 0xDFFF:
				raise _Invalid(f'line {line}: a \\u surrogate escape with no partner')
			try:
				out.append(chr(point))
			except ValueError as problem:
				raise _Invalid(f'line {line}: a bad \\{code} escape') from problem
		else:
			raise _Invalid(f'line {line}: an unknown escape \\{code}')
	return ''.join(out)


def parse_scalar(text: str) -> object:
	"""Resolve a plain scalar by YAML 1.2's core schema; dates stay strings."""
	if text in ('', '~', 'null', 'Null', 'NULL'):
		return None
	if text in ('true', 'True', 'TRUE'):
		return True
	if text in ('false', 'False', 'FALSE'):
		return False
	if _INT.match(text):
		return int(text)
	if _OCT.match(text):
		return int(text[2:], 8)
	if _HEX.match(text):
		return int(text[2:], 16)
	if _FLOAT.match(text) and any(char.isdigit() for char in text):
		return float(text)
	if text.lower() in ('.inf', '+.inf', '-.inf', '.nan'):
		return text
	return text
