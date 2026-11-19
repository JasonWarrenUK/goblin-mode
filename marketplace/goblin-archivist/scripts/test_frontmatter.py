"""Tests for the frontmatter subset parser. Run from this directory:

	python3 -m unittest discover -p 'test_*.py'
"""

from __future__ import annotations

import unittest

from _frontmatter import Unparsed, parse_scalar, read_frontmatter


def note(block: str, body: str = 'Body.\n') -> str:
	return f'---\n{block}\n---\n{body}'


class SplitTest(unittest.TestCase):
	def test_no_block(self) -> None:
		result = read_frontmatter('# Title\n\nText.\n')
		self.assertFalse(result.present)
		self.assertEqual(result.errors, [])
		self.assertEqual(result.body, '# Title\n\nText.\n')

	def test_unclosed_block_is_no_block_with_a_problem(self) -> None:
		result = read_frontmatter('---\ntitle: x\nno close\n')
		self.assertFalse(result.present)
		self.assertEqual(len(result.errors), 1)

	def test_empty_block(self) -> None:
		result = read_frontmatter('---\n---\nText.\n')
		self.assertTrue(result.present)
		self.assertEqual(result.properties, {})
		self.assertEqual(result.body, 'Text.\n')
		self.assertEqual(result.body_line, 3)

	def test_bom_and_crlf(self) -> None:
		result = read_frontmatter('\ufeff---\r\nstatus: done\r\n---\r\nText\r\n')
		self.assertEqual(result.properties, {'status': 'done'})


class ScalarTest(unittest.TestCase):
	def test_core_schema(self) -> None:
		self.assertIsNone(parse_scalar(''))
		self.assertIsNone(parse_scalar('~'))
		self.assertIs(parse_scalar('true'), True)
		self.assertIs(parse_scalar('False'), False)
		self.assertEqual(parse_scalar('42'), 42)
		self.assertEqual(parse_scalar('-3.5'), -3.5)
		self.assertEqual(parse_scalar('0x1f'), 31)
		self.assertEqual(parse_scalar('2026-01-05'), '2026-01-05')
		self.assertEqual(parse_scalar('yes'), 'yes')

	def test_quoted_values_stay_strings(self) -> None:
		result = read_frontmatter(note('a: "42"\nb: \'true\'\nc: "line\\nbreak"\nd: \'it\'\'s\''))
		self.assertEqual(result.properties, {'a': '42', 'b': 'true', 'c': 'line\nbreak', 'd': "it's"})

	def test_comment_after_plain_value(self) -> None:
		result = read_frontmatter(note('status: draft # not yet\ntags: #looks-like-a-tag'))
		self.assertEqual(result.properties, {'status': 'draft', 'tags': None})

	def test_tab_before_a_comment(self) -> None:
		self.assertEqual(read_frontmatter(note('status: draft\t# not yet')).properties, {'status': 'draft'})

	def test_leading_zeros_are_an_integer(self) -> None:
		self.assertIs(type(parse_scalar('007')), int)
		self.assertEqual(parse_scalar('007'), 7)

	def test_url_value(self) -> None:
		result = read_frontmatter(note('link: https://example.invalid/a#b'))
		self.assertEqual(result.properties, {'link': 'https://example.invalid/a#b'})


class ListTest(unittest.TestCase):
	def test_flow_list(self) -> None:
		result = read_frontmatter(note('tags: [a, "b, c", 3]'))
		self.assertEqual(result.properties, {'tags': ['a', 'b, c', 3]})

	def test_block_list_indented_and_flush(self) -> None:
		result = read_frontmatter(note('a:\n  - one\n  - "[[Two]]"\nb:\n- three\n- four'))
		self.assertEqual(result.properties, {'a': ['one', '[[Two]]'], 'b': ['three', 'four']})

	def test_apostrophe_inside_a_plain_flow_item(self) -> None:
		result = read_frontmatter(note("aliases: [Bob's plan, it's fine]\ndg-publish: true"))
		self.assertEqual(result.errors, [])
		self.assertEqual(result.properties, {'aliases': ["Bob's plan", "it's fine"], 'dg-publish': True})

	def test_escaped_quote_inside_a_quoted_flow_item(self) -> None:
		result = read_frontmatter(note('k: ["a\\"b", c]'))
		self.assertEqual(result.errors, [])
		self.assertEqual(result.properties, {'k': ['a"b', 'c']})

	def test_empty_flow_list(self) -> None:
		self.assertEqual(read_frontmatter(note('tags: []')).properties, {'tags': []})

	def test_unquoted_wikilink_is_unparsed_with_a_reason(self) -> None:
		value = read_frontmatter(note('up: [[Home]]')).properties['up']
		self.assertIsInstance(value, Unparsed)
		self.assertIn('unquoted', value.reason)
		item = read_frontmatter(note('related:\n  - [[Home]]')).properties['related']
		self.assertIsInstance(item, Unparsed)
		self.assertIn('unquoted', item.reason)

	def test_list_of_maps_is_unparsed(self) -> None:
		value = read_frontmatter(note('people:\n  - name: ravi\n    role: builder')).properties['people']
		self.assertIsInstance(value, Unparsed)
		self.assertEqual(value.reason, 'list of maps')
		self.assertIn('role: builder', value.raw)


class BlockTest(unittest.TestCase):
	def test_literal_and_folded(self) -> None:
		result = read_frontmatter(note('a: |\n  one\n  two\nb: >-\n  one\n  two'))
		self.assertEqual(result.properties, {'a': 'one\ntwo\n', 'b': 'one two'})

	def test_nested_map_is_unparsed_verbatim(self) -> None:
		value = read_frontmatter(note('source:\n  author: tam\n  year: 2025')).properties['source']
		self.assertIsInstance(value, Unparsed)
		self.assertEqual(value.reason, 'nested map')
		self.assertEqual(value.raw, 'author: tam\nyear: 2025')

	def test_multiline_plain_scalar(self) -> None:
		result = read_frontmatter(note('title: a long\n  title here'))
		self.assertEqual(result.properties, {'title': 'a long title here'})

	def test_empty_value(self) -> None:
		self.assertEqual(read_frontmatter(note('status:\nrepo: ')).properties, {'status': None, 'repo': None})


class InvalidTest(unittest.TestCase):
	def assertInvalid(self, block: str) -> None:
		result = read_frontmatter(note(block))
		self.assertTrue(result.present)
		self.assertTrue(result.errors, block)
		self.assertEqual(result.properties, {})

	def test_unterminated_quote(self) -> None:
		self.assertInvalid('title: "Kites, unterminated\ntags: idea')

	def test_colon_in_plain_value(self) -> None:
		self.assertInvalid('title: a: b')

	def test_tab_indent(self) -> None:
		self.assertInvalid('tags:\n\t- a')

	def test_not_a_key(self) -> None:
		self.assertInvalid('just some words')

	def test_unclosed_flow_list(self) -> None:
		self.assertInvalid('tags: [a, b')

	def test_duplicate_keys_are_recorded_last_wins(self) -> None:
		result = read_frontmatter(note('a: 1\na: 2'))
		self.assertEqual(result.properties, {'a': 2})
		self.assertEqual(result.duplicates, ['a'])

	def test_quoted_key(self) -> None:
		self.assertEqual(read_frontmatter(note('"odd key": 1')).properties, {'odd key': 1})


if __name__ == '__main__':
	unittest.main()
