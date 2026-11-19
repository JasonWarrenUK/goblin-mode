"""Tests for the vault survey, against the invented vault in fixtures/vault.

Every note in that vault is made up; nothing in it comes from a real vault.
Run from this directory:

	python3 -m unittest discover -p 'test_*.py'
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import archivist
from _sniff import TASK_LINE, SniffError, body_lines, inline_tags, moment_regex, shape, survey, task_signature, write_outputs

FIXTURE = Path(__file__).resolve().parent / 'fixtures' / 'vault'


def fingerprint(root: Path) -> dict[str, tuple[str, int]]:
	"""Every file under root with its hash and modification time."""
	out = {}
	for path in sorted(root.rglob('*')):
		if path.is_file():
			out[str(path.relative_to(root))] = (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
	return out


class HelperTest(unittest.TestCase):
	def test_inline_tags_skip_code_urls_headings_and_numbers(self) -> None:
		self.assertEqual(inline_tags('# Heading #real and `#code` and x#no'), ['real'])
		self.assertEqual(inline_tags('see https://a.invalid/p#frag (#paren)'), ['paren'])
		self.assertEqual(inline_tags('#123 #y2k #a/b/'), ['y2k', 'a/b'])
		self.assertEqual(inline_tags('see [top](#top) and [[Note#Heading]] but #real'), ['real'])
		# CommonMark 0.31.2 section 6.1: a span closes on a backtick run as long as its opener
		self.assertEqual(inline_tags('Write ``#notatag`` to show a tag.'), [])
		self.assertEqual(inline_tags('`` ` #nottag `` and #real'), ['real'])
		self.assertEqual(inline_tags('`#a` #b `#c`'), ['b'])

	def test_tasks_in_blockquotes_and_callouts(self) -> None:
		vault = Path(tempfile.mkdtemp())
		try:
			(vault / 'Note.md').write_text('> [!todo]\n> - [ ] in a callout 📅 2026-01-01\n>> - [x] nested quote\n', encoding='utf-8')
			self.assertEqual(survey(vault)['tasks']['statuses_in_use'], {' ': 1, 'x': 1})
		finally:
			shutil.rmtree(vault)

	def test_task_lines_match_tasks_own_pattern(self) -> None:
		# obsidian-tasks src/Task/TaskRegularExpressions.ts: indentation [\\s\\t>]*, a list marker,
		# one or more spaces, [status], then ' *' before the description
		for line, status in (('- [ ]', ' '), ('- [x]Done', 'x'), ('- [ ] spaced', ' '), ('1) [/] numbered', '/'), ('> - [?] quoted', '?')):
			match = TASK_LINE.match(line)
			self.assertIsNotNone(match, line)
			self.assertEqual(match.group('status'), status, line)
		for line in ('-[ ] no space after the marker', 'text - [ ] mid-line', '- [] empty box', '- [A](#a)', '1. [1](#fn1)', '- [x]: reference'):
			self.assertIsNone(TASK_LINE.match(line), line)

	def test_fence_closes_only_on_a_matching_fence(self) -> None:
		body = '````md\n```\n- [ ] inside\n```\n- [ ] still inside\n````\n- [ ] outside\n~~~\n```\n- [ ] in tildes\n~~~\n'
		self.assertEqual([line for line in body_lines(body) if line], ['- [ ] outside'])

	def test_fence_inside_a_quote_or_callout(self) -> None:
		body = '> [!example]\n> ```md\n> - [ ] quoted fence #nottag\n> ```\n> - [ ] after the fence\n>> ~~~\n>> - [ ] deeper\n>> ~~~\n'
		self.assertEqual([line for line in body_lines(body) if line], ['> [!example]', '> - [ ] after the fence'])

	def test_a_quoted_fence_line_does_not_close_an_unquoted_fence(self) -> None:
		# CommonMark 0.31.2 section 4.5: only spaces may precede a closing fence
		body = '```md\n> [!example]\n> ```sh\n> echo hello\n> ```\n- [ ] not a task #notatag\n```\n\n- [ ] water the ferns #garden\n- [x] mend the kite #sky\n'
		self.assertEqual([line for line in body_lines(body) if line], ['- [ ] water the ferns #garden', '- [x] mend the kite #sky'])

	def test_a_quoted_fence_ends_where_its_quote_ends(self) -> None:
		body = '> ```\n> echo hello #incode\n\n- [ ] water the ferns #garden\n'
		self.assertEqual([line for line in body_lines(body) if line], ['- [ ] water the ferns #garden'])

	def test_a_fence_two_quotes_deep(self) -> None:
		body = '>> ```\n>> - [ ] code\n> - [ ] quote one deep\n- [ ] outside\n'
		self.assertEqual([line for line in body_lines(body) if line], ['> - [ ] quote one deep', '- [ ] outside'])

	def test_a_fence_opening_on_its_list_marker_line(self) -> None:
		# CommonMark 0.31.2 section 5.3, example 318: a fence may open on the line of its list marker
		rest = '- then the rest\n\n- [ ] water the ferns #garden\n- [x] mend the kite #sky\n'
		for opener in ('- ```sh', '1. ```sh', '* ~~~', '> - ```sh'):
			quote = '> ' if opener.startswith('>') else ''
			closer = '~~~' if '~' in opener else '```'
			body = f'{opener}\n{quote}  echo hello #notatag\n{quote}  {closer}\n' + rest
			# The opener line keeps only its marker ('-', '1.', '*', '> -'), which holds no task or tag.
			visible = [line for line in body_lines(body) if line and line not in ('-', '1.', '*', '> -')]
			self.assertEqual(visible, ['- then the rest', '- [ ] water the ferns #garden', '- [x] mend the kite #sky'], opener)

	def test_a_fence_opening_after_a_task_box_keeps_the_task(self) -> None:
		body = '- [ ] ```sh\n  echo hello #notatag\n  ```\n- [ ] water the ferns #garden\n'
		lines = [line for line in body_lines(body) if line]
		self.assertEqual(lines, ['- [ ]', '- [ ] water the ferns #garden'])
		self.assertEqual([TASK_LINE.match(line).group('status') for line in lines], [' ', ' '])

	def test_inline_code_on_a_list_line_is_not_a_fence(self) -> None:
		body = '- ```inline``` text #real\n- [ ] next\n'
		self.assertEqual([line for line in body_lines(body) if line], ['- ```inline``` text #real', '- [ ] next'])

	def test_task_signature_orders_metadata(self) -> None:
		self.assertEqual(task_signature('Mend 🔼 ⏳ 2026-01-06 🔁 every week'), 'text · priority medium · scheduled · recurrence')
		self.assertEqual(task_signature('Read [[A]] [due:: 2026-01-09] ^abc'), 'text · [[link]] · [due::] · ^block-id')
		self.assertEqual(task_signature('📅️ 2026-01-01 Odd order'), 'due')
		self.assertEqual(task_signature(''), '(empty)')

	def test_task_signature_reads_every_date_signifier_tasks_accepts(self) -> None:
		# obsidian-tasks src/TaskSerializer/DefaultTaskSerializer.ts: due is 📅, 📆 or 🗓; scheduled is ⏳ or ⌛
		for emoji in ('📅', '📆', '🗓'):
			self.assertEqual(task_signature(f'Post {emoji} 2026-01-07'), 'text · due', emoji)
		for emoji in ('⏳', '⌛'):
			self.assertEqual(task_signature(f'Wait {emoji} 2026-01-07'), 'text · scheduled', emoji)

	def test_global_filter_limits_what_counts_as_a_task(self) -> None:
		vault = Path(tempfile.mkdtemp())
		try:
			plugin = vault / '.obsidian' / 'plugins' / 'obsidian-tasks-plugin'
			plugin.mkdir(parents=True)
			(plugin / 'data.json').write_text(json.dumps({'globalFilter': '#task'}), encoding='utf-8')
			(vault / 'Note.md').write_text('- [ ] #task real\n- [ ] just a checklist\n', encoding='utf-8')
			tasks = survey(vault)['tasks']
			self.assertEqual(tasks['statuses_in_use'], {' ': 1})
			self.assertEqual(tasks['outside_global_filter'], 1)
		finally:
			shutil.rmtree(vault)

	def test_shapes(self) -> None:
		self.assertEqual(shape('2026-01-05'), 'date')
		self.assertEqual(shape('2026-01-05T10:00'), 'datetime')
		self.assertEqual(shape('[[Note]]'), 'link')
		self.assertEqual(shape(['[[A]]', 'b']), 'list of mixed (link, text)')
		self.assertEqual(shape([]), 'empty list')
		self.assertEqual(shape(True), 'boolean')

	def test_moment_formats(self) -> None:
		self.assertTrue(moment_regex('YYYY-MM-DD').match('2026-01-05'))
		self.assertTrue(moment_regex('YYYY/MM/YYYY-MM-DD ddd').match('2026/01/2026-01-05 Mon'))
		self.assertTrue(moment_regex('gggg-[W]ww').match('2026-W02'))
		self.assertFalse(moment_regex('YYYY-MM-DD').match('Kites'))


class SurveyTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls) -> None:
		cls.data = survey(FIXTURE)

	def test_totals_skip_dot_folders(self) -> None:
		totals = self.data['totals']
		self.assertEqual(totals['notes'], 12)
		self.assertEqual(totals['canvases'], 1)
		self.assertEqual(totals['bases'], 1)
		self.assertEqual(totals['attachments'], 2)
		self.assertEqual(self.data['layout']['hidden_folders'], ['.obsidian', '.trash'])
		self.assertNotIn('secret', self.data['types'])

	def test_types_and_their_rules(self) -> None:
		types = self.data['types']
		self.assertEqual(types['project']['notes'], 3)
		self.assertEqual(types['daily']['notes'], 2)
		self.assertEqual(types['template']['notes'], 2)
		self.assertEqual(types['idea']['rules'], {'property `fileClass`': 1})

	def test_properties_and_variants(self) -> None:
		properties = self.data['properties']
		self.assertEqual(properties['tags']['notes'], 5)
		self.assertEqual(properties['source']['shapes'], {'unparsed (nested map)': 1})
		self.assertEqual(properties['due']['declared_type'], 'date')
		self.assertIn(['Status', 'status'], self.data['property_variants'])
		self.assertIn('tag', self.data['deprecated_keys'])

	def test_invalid_frontmatter_is_reported_not_counted(self) -> None:
		invalid = self.data['problems']['invalid_frontmatter']
		self.assertEqual([item['path'] for item in invalid], ['Ideas/Kites.md'])
		self.assertNotIn('title', self.data['properties'])

	def test_tags_from_frontmatter_and_body(self) -> None:
		tags = self.data['tags']
		for tag in ('daily', 'mood/good', 'weather/rain', 'idea/flight', 'y2k', 'code', 'garden', 'kitchen'):
			self.assertIn(tag, tags)
		for absent in ('notatag', '123', 'section', 'a'):
			self.assertNotIn(absent, tags)
		self.assertIn(['Idea', 'idea'], self.data['tag_variants'])

	def test_tasks(self) -> None:
		tasks = self.data['tasks']
		self.assertEqual(tasks['statuses_in_use'], {' ': 4, '-': 1, '/': 1, '?': 1, 'x': 1})
		self.assertEqual(tasks['plugin']['taskFormat'], 'tasksPluginEmoji')
		self.assertEqual(len(tasks['plugin']['statuses']), 5)

	def test_publishing_is_per_note(self) -> None:
		publishing = self.data['publishing']
		self.assertEqual(publishing['digital_garden']['published_notes'], ['Projects/Lantern/Lantern.md'])
		self.assertEqual(publishing['share_note']['shared_notes'], ['Projects/Teapot.md'])
		self.assertEqual(publishing['share_note']['property_prefix'], 'share')

	def test_secrets_in_plugin_data_never_reach_the_output(self) -> None:
		text = json.dumps(self.data)
		self.assertNotIn('invented-secret-never-reported', text)
		self.assertNotIn('invented-token-never-reported', text)

	def test_linter(self) -> None:
		linter = self.data['linter']
		self.assertTrue(linter['settings']['lintOnSave'])
		self.assertEqual(sorted(linter['enabled_rules']), ['format-tags-in-yaml', 'trailing-spaces', 'yaml-timestamp'])
		self.assertEqual(linter['foldersToIgnore'], ['Templates'])

	def test_plugins(self) -> None:
		community = {item['id']: item for item in self.data['plugins']['community']}
		self.assertFalse(community['calendar']['enabled'])
		self.assertTrue(community['digitalgarden']['enabled'])
		self.assertIn('templates', self.data['plugins']['core_enabled'])
		self.assertNotIn('daily-notes', self.data['plugins']['core_enabled'])

	def test_ignore_filters(self) -> None:
		self.assertEqual(self.data['layout']['ignore_filters'], {'Archive/Old/': 1})


class OutputTest(unittest.TestCase):
	def setUp(self) -> None:
		self.tmp = Path(tempfile.mkdtemp())

	def tearDown(self) -> None:
		shutil.rmtree(self.tmp)

	def test_two_runs_give_identical_files_and_touch_nothing_in_the_vault(self) -> None:
		before = fingerprint(FIXTURE)
		first = write_outputs(FIXTURE, self.tmp / 'one')
		second = write_outputs(FIXTURE, self.tmp / 'two')
		self.assertEqual(fingerprint(FIXTURE), before)
		for key in ('survey', 'report', 'schema'):
			self.assertEqual(first[key].read_bytes(), second[key].read_bytes(), key)

	def test_annotations_file_survives_a_rerun(self) -> None:
		out = self.tmp / 'out'
		write_outputs(FIXTURE, out)
		notes = out / 'schema.notes.md'
		notes.write_text('Claude was here.\n', encoding='utf-8')
		write_outputs(FIXTURE, out)
		self.assertEqual(notes.read_text(encoding='utf-8'), 'Claude was here.\n')

	def test_refuses_an_output_folder_inside_the_vault(self) -> None:
		vault = self.tmp / 'vault'
		shutil.copytree(FIXTURE, vault)
		with self.assertRaises(SniffError):
			write_outputs(vault, vault / 'reports')
		self.assertFalse((vault / 'reports').exists())

	def test_refuses_the_vault_named_in_a_different_case(self) -> None:
		vault = self.tmp / 'casevault'
		shutil.copytree(FIXTURE, vault)
		probe = self.tmp / 'CASEVAULT'
		if not probe.exists():
			self.skipTest('case-sensitive file system')
		with self.assertRaises(SniffError):
			write_outputs(vault, probe / 'reports')
		self.assertFalse((vault / 'reports').exists())

	def test_refuses_an_output_file_that_links_into_the_vault(self) -> None:
		vault = self.tmp / 'vault'
		shutil.copytree(FIXTURE, vault)
		note = vault / 'Untitled.md'
		before = note.read_bytes()
		for name in ('report.md', 'survey.json', 'schema.draft.json'):
			out = self.tmp / f'sym-{name}'
			out.mkdir()
			(out / name).symlink_to(note)
			with self.assertRaises(SniffError, msg=name):
				write_outputs(vault, out)
		notes_link = self.tmp / 'sym-notes'
		notes_link.mkdir()
		(notes_link / 'schema.notes.md').symlink_to(note)
		with self.assertRaises(SniffError, msg='schema.notes.md symlink'):
			write_outputs(vault, notes_link)
		notes_hard = self.tmp / 'hard-notes'
		notes_hard.mkdir()
		os.link(note, notes_hard / 'schema.notes.md')
		with self.assertRaises(SniffError, msg='schema.notes.md hard link'):
			write_outputs(vault, notes_hard)
		hard = self.tmp / 'hard'
		hard.mkdir()
		os.link(note, hard / 'survey.json')
		with self.assertRaises(SniffError):
			write_outputs(vault, hard)
		self.assertEqual(note.read_bytes(), before)

	def test_refuses_an_output_folder_that_is_a_link_into_the_vault(self) -> None:
		vault = self.tmp / 'vault'
		shutil.copytree(FIXTURE, vault)
		(self.tmp / 'sniff').symlink_to(vault / 'Ideas', target_is_directory=True)
		with self.assertRaises(SniffError):
			write_outputs(vault, self.tmp / 'sniff')
		self.assertFalse((vault / 'Ideas' / 'report.md').exists())

	def test_a_rerun_replaces_files_rather_than_writing_through_them(self) -> None:
		out = self.tmp / 'out'
		write_outputs(FIXTURE, out)
		inode = (out / 'report.md').stat().st_ino
		write_outputs(FIXTURE, out)
		self.assertNotEqual((out / 'report.md').stat().st_ino, inode)
		self.assertEqual(sorted(path.name for path in out.iterdir()), ['report.md', 'schema.draft.json', 'survey.json'])

	def test_a_lone_surrogate_does_not_stop_the_survey(self) -> None:
		vault = self.tmp / 'vault'
		shutil.copytree(FIXTURE, vault)
		(vault / 'Escaped.md').write_text('---\nk: "\\ud83d"\n---\n', encoding='utf-8')
		paths = write_outputs(vault, self.tmp / 'out')
		data = json.loads(paths['survey'].read_text(encoding='utf-8'))
		self.assertIn('Escaped.md', [item['path'] for item in data['problems']['invalid_frontmatter']])

	def test_a_git_failure_refuses_rather_than_reading_as_no_repository(self) -> None:
		import _sniff
		real_run = _sniff.subprocess.run

		def broken(arguments, **options):
			return subprocess.CompletedProcess(arguments, 128, '', 'fatal: detected dubious ownership in repository\n')

		_sniff.subprocess.run = broken
		try:
			with self.assertRaises(SniffError):
				write_outputs(FIXTURE, self.tmp / 'out')
		finally:
			_sniff.subprocess.run = real_run
		self.assertFalse((self.tmp / 'out').exists())

	def test_git_is_asked_in_one_language(self) -> None:
		import _sniff
		real_run = _sniff.subprocess.run
		seen = []

		def translated(arguments, **options):
			environment = options.get('env') or os.environ
			seen.append(environment.get('LC_ALL'))
			if environment.get('LC_ALL') == 'C':
				return subprocess.CompletedProcess(arguments, 128, '', 'fatal: not a git repository (or any of the parent directories): .git\n')
			return subprocess.CompletedProcess(arguments, 128, '', 'fatal: Kein Git-Repository (oder irgendeines der Elternverzeichnisse): .git\n')

		_sniff.subprocess.run = translated
		try:
			write_outputs(FIXTURE, self.tmp / 'out')
		finally:
			_sniff.subprocess.run = real_run
		self.assertTrue(seen)
		self.assertEqual(set(seen), {'C'})

	def test_a_git_warning_before_the_answer_still_reads_as_no_repository(self) -> None:
		import _sniff
		real_run = _sniff.subprocess.run

		def warned(arguments, **options):
			return subprocess.CompletedProcess(arguments, 128, '', "warning: unable to access '/h/.gitconfig': Is a directory\nfatal: not a git repository (or any of the parent directories): .git\n")

		_sniff.subprocess.run = warned
		try:
			write_outputs(FIXTURE, self.tmp / 'out')
		finally:
			_sniff.subprocess.run = real_run
		self.assertTrue((self.tmp / 'out' / 'report.md').exists())

	def test_a_path_holding_the_phrase_does_not_read_as_no_repository(self) -> None:
		import _sniff
		real_run = _sniff.subprocess.run

		def lookalike(arguments, **options):
			return subprocess.CompletedProcess(arguments, 128, '', "fatal: cannot change to '/x/not a git repository/y': No such file or directory\n")

		_sniff.subprocess.run = lookalike
		try:
			with self.assertRaises(SniffError):
				write_outputs(FIXTURE, self.tmp / 'out')
		finally:
			_sniff.subprocess.run = real_run

	def test_git_variables_in_the_environment_cannot_hide_a_repository(self) -> None:
		repo = self.tmp / 'repo'
		(repo / 'sub').mkdir(parents=True)
		subprocess.run(['git', 'init', '-q', str(repo)], check=True)
		for variable, value in (('GIT_DIR', str(self.tmp / 'nowhere')), ('GIT_CEILING_DIRECTORIES', str(repo)), ('GIT_WORK_TREE', str(self.tmp))):
			saved = os.environ.get(variable)
			os.environ[variable] = value
			try:
				with self.assertRaises(SniffError, msg=variable):
					write_outputs(FIXTURE, repo / 'sub' / 'reports')
			finally:
				if saved is None:
					os.environ.pop(variable, None)
				else:
					os.environ[variable] = saved
		self.assertFalse((repo / 'sub' / 'reports').exists())

	def test_unreadable_note_is_reported_not_fatal(self) -> None:
		vault = self.tmp / 'vault'
		shutil.copytree(FIXTURE, vault)
		(vault / 'Dangling.md').symlink_to(self.tmp / 'nowhere.md')
		data = survey(vault)
		self.assertEqual(data['problems']['unreadable_notes'], ['Dangling.md'])
		self.assertEqual(data['totals']['notes'], 12)

	def test_refuses_an_output_folder_a_repository_would_commit(self) -> None:
		repo = self.tmp / 'repo'
		repo.mkdir()
		subprocess.run(['git', 'init', '-q', str(repo)], check=True)
		(repo / '.gitignore').write_text('private/\n', encoding='utf-8')
		with self.assertRaises(SniffError):
			write_outputs(FIXTURE, repo / 'reports')
		self.assertFalse((repo / 'reports').exists())
		write_outputs(FIXTURE, repo / 'private' / 'reports')
		self.assertTrue((repo / 'private' / 'reports' / 'report.md').exists())

	def test_refuses_a_repository_that_ignores_only_some_output_files(self) -> None:
		repo = self.tmp / 'mdonly'
		repo.mkdir()
		subprocess.run(['git', 'init', '-q', str(repo)], check=True)
		(repo / '.gitignore').write_text('*.md\n', encoding='utf-8')
		with self.assertRaises(SniffError):
			write_outputs(FIXTURE, repo / 'archivist-sniff')
		self.assertFalse((repo / 'archivist-sniff').exists())

	def test_symlinked_folders_are_reported(self) -> None:
		vault = self.tmp / 'vault'
		shutil.copytree(FIXTURE, vault)
		elsewhere = self.tmp / 'elsewhere'
		elsewhere.mkdir()
		(elsewhere / 'Linked.md').write_text('Linked note.\n', encoding='utf-8')
		(vault / 'Linked').symlink_to(elsewhere, target_is_directory=True)
		data = survey(vault)
		self.assertEqual(data['problems']['symlinked_folders'], ['Linked'])
		self.assertEqual(data['totals']['notes'], 12)

	def test_draft_schema(self) -> None:
		paths = write_outputs(FIXTURE, self.tmp / 'out')
		schema = json.loads(paths['schema'].read_text(encoding='utf-8'))
		self.assertTrue(schema['draft'])
		self.assertNotIn('template', schema['types'])
		self.assertEqual(schema['types']['idea']['required'], ['empty', 'fileClass', 'published', 'rating', 'source', 'status', 'summary', 'tags'])
		self.assertEqual(schema['properties']['status']['conflicts'], {'text': 1})
		self.assertEqual(schema['properties']['tags']['type'], 'tags')
		self.assertIn('mood', schema['tags'])
		self.assertEqual(schema['tags']['mood']['children'], ['good'])


class CommandTest(unittest.TestCase):
	def run_cli(self, *argv: str) -> tuple[int, str, str]:
		out, err = io.StringIO(), io.StringIO()
		with redirect_stdout(out), redirect_stderr(err):
			code = archivist.main(list(argv))
		return code, out.getvalue(), err.getvalue()

	def test_unset_options(self) -> None:
		self.assertEqual(self.run_cli('sniff', '--vault', '', '--base', '/tmp')[0], 3)
		self.assertEqual(self.run_cli('sniff', '--vault', '${user_config.vault}', '--base', '/tmp')[0], 3)
		self.assertEqual(self.run_cli('sniff', '--vault', str(FIXTURE), '--base', '${user_config.base}')[0], 4)

	def test_a_disk_error_is_exit_2_with_a_message(self) -> None:
		blocker = Path(tempfile.mkdtemp())
		try:
			(blocker / 'file').write_text('not a folder\n', encoding='utf-8')
			code, _, err = self.run_cli('sniff', '--vault', str(FIXTURE), '--base', str(blocker / 'file'))
			self.assertEqual(code, 2)
			self.assertIn('could not write', err)
		finally:
			shutil.rmtree(blocker)

	def test_missing_vault(self) -> None:
		self.assertEqual(self.run_cli('sniff', '--vault', '/nonexistent/vault', '--base', '/tmp')[0], 2)

	def test_sniff_writes_under_base_vault_sniff(self) -> None:
		base = Path(tempfile.mkdtemp())
		try:
			code, out, _ = self.run_cli('sniff', '--vault', str(FIXTURE), '--base', str(base))
			self.assertEqual(code, 0)
			paths = json.loads(out)
			self.assertEqual(Path(paths['report']).parent, (base / 'vault' / 'sniff').resolve())
		finally:
			shutil.rmtree(base)

	def test_vaults_lists_obsidian_config(self) -> None:
		tmp = Path(tempfile.mkdtemp())
		try:
			config = tmp / 'obsidian.json'
			config.write_text(json.dumps({'vaults': {
				'b': {'path': str(tmp / 'second'), 'ts': 2},
				'a': {'path': str(FIXTURE), 'ts': 1, 'open': True},
			}}), encoding='utf-8')
			code, out, _ = self.run_cli('vaults', '--obsidian-config', str(config))
			self.assertEqual(code, 0)
			listed = json.loads(out)
			self.assertEqual([item['path'] for item in listed], sorted([str(FIXTURE), str(tmp / 'second')]))
			by_path = {item['path']: item for item in listed}
			self.assertEqual((by_path[str(FIXTURE)]['exists'], by_path[str(FIXTURE)]['open']), (True, True))
			self.assertEqual((by_path[str(tmp / 'second')]['exists'], by_path[str(tmp / 'second')]['open']), (False, False))
		finally:
			shutil.rmtree(tmp)

	def test_vaults_without_obsidian(self) -> None:
		code, out, _ = self.run_cli('vaults', '--obsidian-config', os.devnull + '-missing')
		self.assertEqual((code, json.loads(out)), (0, []))


if __name__ == '__main__':
	unittest.main()
