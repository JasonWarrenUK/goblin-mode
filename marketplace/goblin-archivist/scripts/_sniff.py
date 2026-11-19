"""The vault survey behind /goblin-archivist:sniff-vault.

Reads an Obsidian vault and writes nothing inside it. Produces three files in
an output folder outside the vault: survey.json (every count), report.md (the
same, for a person) and schema.draft.json (a schema drafted mechanically from
the counts). Claude's annotations go in a fourth file the script never
touches, so a rerun cannot overwrite them.

Deterministic: the walk is sorted, every collection is sorted on output and
nothing in the output depends on the clock, so two runs over an unchanged
vault give byte-identical files.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from _frontmatter import Frontmatter, Unparsed, read_frontmatter

SURVEY_VERSION = 1
REQUIRED_AT = 0.9
OPTIONAL_AT = 0.1
EXAMPLES = 3
TOP_VALUES = 5
CELL_WIDTH = 80

TYPE_KEYS = ('type', 'fileclass', 'category', 'kind')
TAG_KEYS = ('tags', 'tag')
DEPRECATED_KEYS = {'tag': 'tags', 'alias': 'aliases', 'cssclass': 'cssclasses'}

TASK_LINE = re.compile(r'^(?:[ \t]*>)*(?P<indent>[ \t]*)(?:[-*+]|\d+[.)])[ \t]+\[(?P<status>.)\][ \t]+(?P<text>.*)$')
FENCE = re.compile(r'^[ \t]*(```|~~~)')
INLINE_CODE = re.compile(r'`[^`]*`')
INLINE_TAG = re.compile(r'(?:^|(?<=[\s(]))#([^\s#!@$%^&*(),.?":{}|<>\[\]\'`;+=~\\]+)')
WIKILINK = re.compile(r'!?\[\[[^\]]+\]\]')
DATAVIEW_FIELD = re.compile(r'[\[(]([\w\- ]+)::[^\])]*[\])]')
BLOCK_ID = re.compile(r'\s\^[\w-]+\s*$')
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
DATETIME = re.compile(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$')
URL = re.compile(r'^[a-z][a-z0-9+.-]*://\S+$', re.IGNORECASE)
LINK = re.compile(r'^!?\[\[[^\]]+\]\]$')

TASK_SIGNIFIERS = {
	'📅': 'due',
	'⏳': 'scheduled',
	'🛫': 'start',
	'✅': 'done',
	'➕': 'created',
	'❌': 'cancelled',
	'🔁': 'recurrence',
	'🆔': 'id',
	'⛔': 'depends on',
	'🏁': 'on completion',
	'🔺': 'priority highest',
	'⏫': 'priority high',
	'🔼': 'priority medium',
	'🔽': 'priority low',
	'⏬': 'priority lowest',
}

OBSIDIAN_TYPE = {
	'text': 'text',
	'link': 'text',
	'url': 'text',
	'multiline text': 'text',
	'number': 'number',
	'boolean': 'checkbox',
	'date': 'date',
	'datetime': 'datetime',
}


class SniffError(Exception):
	"""A problem that stops the survey before it reads anything."""

	def __init__(self, message: str, code: int = 2) -> None:
		super().__init__(message)
		self.code = code


@dataclass
class Note:
	path: str
	frontmatter: Frontmatter
	decode_errors: bool
	note_type: str = ''
	type_rule: str = ''


@dataclass
class Walk:
	notes: list[Note] = field(default_factory=list)
	folders: Counter[str] = field(default_factory=Counter)
	canvases: list[str] = field(default_factory=list)
	bases: list[str] = field(default_factory=list)
	attachments: Counter[str] = field(default_factory=Counter)
	hidden: list[str] = field(default_factory=list)
	unreadable: list[str] = field(default_factory=list)


def top_folder(path: str) -> str:
	return path.split('/', 1)[0] if '/' in path else '(vault root)'


def parent_folder(path: str) -> str:
	return path.rsplit('/', 1)[0] if '/' in path else '(vault root)'


def sorted_counts(counter: Counter[str] | dict[str, int]) -> list[tuple[str, int]]:
	return sorted(counter.items(), key=lambda item: (-item[1], item[0]))


def read_json(path: Path) -> object:
	try:
		return json.loads(path.read_text(encoding='utf-8'))
	except (OSError, ValueError):
		return None


def walk_vault(vault: Path) -> Walk:
	"""Every file the vault holds outside dot-folders, in sorted order."""
	result = Walk()
	for root, dirs, files in os.walk(vault):
		relative_root = os.path.relpath(root, vault)
		relative_root = '' if relative_root == '.' else relative_root.replace(os.sep, '/')
		hidden = sorted(name for name in dirs if name.startswith('.'))
		if not relative_root:
			result.hidden.extend(hidden)
		dirs[:] = sorted(name for name in dirs if not name.startswith('.'))
		if relative_root:
			result.folders[relative_root] += 0
		for name in sorted(files):
			if name.startswith('.'):
				continue
			path = f'{relative_root}/{name}' if relative_root else name
			suffix = Path(name).suffix.lower()
			if suffix == '.md':
				try:
					data = (Path(root) / name).read_bytes()
				except OSError:
					result.unreadable.append(path)
					continue
				try:
					text, decode_errors = data.decode('utf-8'), False
				except UnicodeDecodeError:
					text, decode_errors = data.decode('utf-8', errors='replace'), True
				result.notes.append(Note(path, read_frontmatter(text), decode_errors))
				folder = relative_root
				while folder:
					result.folders[folder] += 1
					folder = folder.rsplit('/', 1)[0] if '/' in folder else ''
			elif suffix == '.canvas':
				result.canvases.append(path)
			elif suffix == '.base':
				result.bases.append(path)
			else:
				result.attachments[suffix or '(none)'] += 1
	result.notes.sort(key=lambda note: note.path)
	return result


def body_lines(body: str) -> list[str]:
	"""The body's lines with fenced code blanked, so nothing inside a fence counts."""
	lines = body.split('\n')
	out: list[str] = []
	fence = ''
	for line in lines:
		match = FENCE.match(line)
		if fence:
			if match and match.group(1) == fence:
				fence = ''
			out.append('')
			continue
		if match:
			fence = match.group(1)
			out.append('')
			continue
		out.append(line.rstrip('\r'))
	return out


def blank_code(text: str) -> str:
	"""Inline code replaced by spaces of the same width, so positions hold."""
	return INLINE_CODE.sub(lambda match: ' ' * len(match.group(0)), text)


def inline_tags(line: str) -> list[str]:
	line = blank_code(line)
	tags = []
	for match in INLINE_TAG.finditer(line):
		tag = match.group(1).rstrip('/')
		if tag and not re.fullmatch(r'[\d/_-]+', tag):
			tags.append(tag)
	return tags


def frontmatter_tags(properties: dict[str, object]) -> list[str]:
	tags: list[str] = []
	for key, value in properties.items():
		if key.casefold() not in TAG_KEYS:
			continue
		values = value if isinstance(value, list) else [value] if isinstance(value, str) else []
		for item in values:
			if not isinstance(item, str):
				continue
			for piece in re.split(r'[,\s]+', item) if not isinstance(value, list) else [item]:
				piece = piece.strip().lstrip('#').rstrip('/')
				if piece:
					tags.append(piece)
	return tags


def shape(value: object) -> str:
	"""A value's shape in plain words: what the schema has to say it may hold."""
	if isinstance(value, Unparsed):
		return f'unparsed ({value.reason})'
	if value is None:
		return 'empty'
	if isinstance(value, bool):
		return 'boolean'
	if isinstance(value, (int, float)):
		return 'number'
	if isinstance(value, list):
		if not value:
			return 'empty list'
		inner = sorted({shape(item) for item in value})
		return f'list of {inner[0]}' if len(inner) == 1 else f'list of mixed ({", ".join(inner)})'
	text = str(value)
	if '\n' in text.strip():
		return 'multiline text'
	if DATE.match(text):
		return 'date'
	if DATETIME.match(text):
		return 'datetime'
	if LINK.match(text):
		return 'link'
	if URL.match(text):
		return 'url'
	return 'text'


def obsidian_type(key: str, shape_name: str) -> str | None:
	"""The Obsidian property type a shape maps to; None when it has none."""
	if key.casefold() == 'tags':
		return 'tags'
	if key.casefold() == 'aliases':
		return 'aliases'
	if shape_name.startswith('list'):
		return 'multitext'
	return OBSIDIAN_TYPE.get(shape_name)


def display(value: object) -> str:
	"""A value as it would read in a cell, trimmed."""
	if isinstance(value, Unparsed):
		text = value.raw
	elif isinstance(value, list):
		text = '[' + ', '.join(display(item) for item in value) + ']'
	elif value is None:
		text = '(empty)'
	elif value == '':
		text = '(empty string)'
	elif isinstance(value, bool):
		text = 'true' if value else 'false'
	else:
		text = str(value)
	text = text.replace('\n', '⏎')
	return text if len(text) <= CELL_WIDTH else text[: CELL_WIDTH - 1] + '…'


def moment_regex(format_string: str) -> re.Pattern[str]:
	"""A regex matching file names made by a moment.js date format."""
	tokens = [
		('YYYY', r'\d{4}'), ('gggg', r'\d{4}'), ('GGGG', r'\d{4}'),
		('MMMM', r'[^\W\d_]+'), ('MMM', r'[^\W\d_]+'), ('dddd', r'[^\W\d_]+'), ('ddd', r'[^\W\d_]+'),
		('YY', r'\d{2}'), ('MM', r'\d{2}'), ('DD', r'\d{2}'), ('Do', r'\d{1,2}[a-z]{2}'),
		('ww', r'\d{2}'), ('WW', r'\d{2}'), ('M', r'\d{1,2}'), ('D', r'\d{1,2}'), ('w', r'\d{1,2}'),
		('W', r'\d{1,2}'), ('Q', r'\d'), ('d', r'\d'),
	]
	out: list[str] = []
	position = 0
	while position < len(format_string):
		if format_string[position] == '[':
			end = format_string.find(']', position)
			end = len(format_string) if end < 0 else end
			out.append(re.escape(format_string[position + 1: end]))
			position = end + 1
			continue
		for token, pattern in tokens:
			if format_string.startswith(token, position):
				out.append(pattern)
				position += len(token)
				break
		else:
			out.append(re.escape(format_string[position]))
			position += 1
	return re.compile('^' + ''.join(out) + '$')


@dataclass
class Config:
	"""What the vault's .obsidian folder says, read from named files only."""

	app: dict[str, object] = field(default_factory=dict)
	core_enabled: list[str] = field(default_factory=list)
	community_enabled: list[str] = field(default_factory=list)
	installed: dict[str, dict[str, str]] = field(default_factory=dict)
	declared_types: dict[str, str] = field(default_factory=dict)
	daily: list[dict[str, str]] = field(default_factory=list)
	template_folders: list[dict[str, str]] = field(default_factory=list)
	plugin_data: dict[str, object] = field(default_factory=dict)
	unreadable: list[str] = field(default_factory=list)


def read_config(vault: Path) -> Config:
	config = Config()
	base = vault / '.obsidian'

	def load(name: str) -> object:
		path = base / name
		if not path.exists():
			return None
		value = read_json(path)
		if value is None:
			config.unreadable.append(name)
		return value

	app = load('app.json')
	config.app = app if isinstance(app, dict) else {}
	core = load('core-plugins.json')
	if isinstance(core, dict):
		config.core_enabled = sorted(key for key, value in core.items() if value is True)
	elif isinstance(core, list):
		config.core_enabled = sorted(str(item) for item in core)
	community = load('community-plugins.json')
	config.community_enabled = sorted(str(item) for item in community) if isinstance(community, list) else []
	plugins_dir = base / 'plugins'
	if plugins_dir.is_dir():
		for folder in sorted(plugins_dir.iterdir()):
			manifest = read_json(folder / 'manifest.json') if (folder / 'manifest.json').exists() else None
			if isinstance(manifest, dict):
				config.installed[str(manifest.get('id', folder.name))] = {
					'name': str(manifest.get('name', folder.name)),
					'version': str(manifest.get('version', '')),
					'folder': folder.name,
				}
			for plugin_id in ('obsidian-tasks-plugin', 'templater-obsidian', 'periodic-notes', 'share-note', 'digitalgarden', 'obsidian-linter'):
				if folder.name == plugin_id and (folder / 'data.json').exists():
					data = read_json(folder / 'data.json')
					if data is None:
						config.unreadable.append(f'plugins/{plugin_id}/data.json')
					else:
						config.plugin_data[plugin_id] = data
	types = load('types.json')
	if isinstance(types, dict) and isinstance(types.get('types'), dict):
		config.declared_types = {str(key): str(value) for key, value in types['types'].items()}
	daily = load('daily-notes.json')
	if isinstance(daily, dict) or (daily is None and 'daily-notes' in config.core_enabled):
		daily = daily if isinstance(daily, dict) else {}
		config.daily.append({
			'source': 'core daily notes' + ('' if 'daily-notes' in config.core_enabled else ' (plugin off)'),
			'folder': str(daily.get('folder', '') or '').strip('/'),
			'format': str(daily.get('format', '') or 'YYYY-MM-DD'),
			'template': str(daily.get('template', '') or ''),
		})
	periodic = config.plugin_data.get('periodic-notes')
	if isinstance(periodic, dict):
		for period in ('daily', 'weekly', 'monthly', 'quarterly', 'yearly'):
			settings = periodic.get(period)
			if isinstance(settings, dict) and settings.get('enabled'):
				default_format = {'daily': 'YYYY-MM-DD', 'weekly': 'gggg-[W]ww', 'monthly': 'YYYY-MM', 'quarterly': 'YYYY-[Q]Q', 'yearly': 'YYYY'}[period]
				config.daily.append({
					'source': f'periodic notes ({period})',
					'period': period,
					'folder': str(settings.get('folder', '') or '').strip('/'),
					'format': str(settings.get('format', '') or default_format),
					'template': str(settings.get('template', '') or ''),
				})
	templates = load('templates.json')
	if isinstance(templates, dict) and templates.get('folder'):
		config.template_folders.append({'source': 'core templates' + ('' if 'templates' in config.core_enabled else ' (plugin off)'), 'folder': str(templates['folder']).strip('/')})
	templater = config.plugin_data.get('templater-obsidian')
	if isinstance(templater, dict) and templater.get('templates_folder'):
		config.template_folders.append({'source': 'Templater', 'folder': str(templater['templates_folder']).strip('/')})
	return config


def ignored_by(path: str, rule: str) -> bool:
	"""Whether one of Obsidian's excluded-files rules covers a path: a /regex/ or a path prefix."""
	if len(rule) > 2 and rule.startswith('/') and rule.endswith('/'):
		try:
			return re.search(rule[1:-1], path) is not None
		except re.error:
			return False
	return path.startswith(rule) or path == rule.rstrip('/') + '.md'


def in_folder(path: str, folder: str) -> bool:
	return not folder or path.startswith(folder + '/')


def classify(note: Note, config: Config) -> None:
	"""Give a note its apparent type and the rule that gave it."""
	properties = note.frontmatter.properties
	for folder in config.template_folders:
		if folder['folder'] and in_folder(note.path, folder['folder']):
			note.note_type = 'template'
			note.type_rule = f'in the {folder["source"]} folder'
			return
	for wanted in TYPE_KEYS:
		for key, value in properties.items():
			if key.casefold() != wanted:
				continue
			if isinstance(value, str) and value.strip():
				note.note_type = value.strip().casefold()
				note.type_rule = f'property `{key}`'
				return
			if isinstance(value, list) and value and all(isinstance(item, str) for item in value):
				note.note_type = ' + '.join(sorted(item.strip().casefold() for item in value))
				note.type_rule = f'property `{key}` (list)'
				return
	stem = note.path[:-3]
	for daily in sorted(config.daily, key=lambda item: 'plugin off' in item['source']):
		relative = stem[len(daily['folder']) + 1:] if daily['folder'] else stem
		if in_folder(note.path, daily['folder']) and moment_regex(daily['format']).match(relative):
			period = daily.get('period', 'daily')
			note.note_type = period
			note.type_rule = f'{daily["source"]} folder and format'
			return
	note.note_type = f'untyped in {top_folder(note.path)}'
	note.type_rule = 'top-level folder'


def task_signature(text: str) -> str:
	"""The order of the metadata on a task line, its words left out."""
	text = text.replace('\ufe0f', '')
	kinds: list[tuple[int, str]] = []
	for emoji, name in TASK_SIGNIFIERS.items():
		for match in re.finditer(re.escape(emoji), text):
			kinds.append((match.start(), name))
	for match in DATAVIEW_FIELD.finditer(text):
		kinds.append((match.start(), f'[{match.group(1).strip()}::]'))
	for match in WIKILINK.finditer(text):
		kinds.append((match.start(), '[[link]]'))
	for match in INLINE_TAG.finditer(blank_code(text)):
		kinds.append((match.start(), '#tag'))
	block = BLOCK_ID.search(text)
	if block:
		kinds.append((block.start(), '^block-id'))
	kinds.sort()
	parts: list[str] = []
	first = kinds[0][0] if kinds else len(text)
	if text[:first].strip():
		parts.append('text')
	for _, name in kinds:
		if not parts or parts[-1] != name:
			parts.append(name)
	return ' · '.join(parts) if parts else '(empty)'


def survey(vault: Path) -> dict[str, object]:
	"""Read the vault and return every count as one JSON-ready dict."""
	vault = vault.resolve()
	if not vault.is_dir():
		raise SniffError(f'no folder at {vault}')
	config = read_config(vault)
	walk = walk_vault(vault)
	for note in walk.notes:
		classify(note, config)

	types: dict[str, dict[str, object]] = {}
	type_counts: Counter[str] = Counter()
	type_rules: dict[str, Counter[str]] = defaultdict(Counter)
	type_folders: dict[str, Counter[str]] = defaultdict(Counter)
	properties: dict[str, dict[str, object]] = {}
	prop_notes: Counter[str] = Counter()
	prop_shapes: dict[str, Counter[str]] = defaultdict(Counter)
	prop_values: dict[str, Counter[str]] = defaultdict(Counter)
	prop_types: dict[str, Counter[str]] = defaultdict(Counter)
	prop_folders: dict[str, Counter[str]] = defaultdict(Counter)
	type_props: dict[str, Counter[str]] = defaultdict(Counter)
	tag_notes: dict[str, set[str]] = defaultdict(set)
	tag_sources: dict[str, Counter[str]] = defaultdict(Counter)
	statuses: Counter[str] = Counter()
	signatures: Counter[str] = Counter()
	signature_examples: dict[str, list[str]] = defaultdict(list)
	signature_folders: dict[str, Counter[str]] = defaultdict(Counter)
	task_folders: Counter[str] = Counter()
	invalid: list[dict[str, object]] = []
	unclosed: list[str] = []
	unparsed: list[dict[str, str]] = []
	duplicates: list[dict[str, object]] = []
	deprecated: Counter[str] = Counter()
	decode_problems: list[str] = []
	with_frontmatter = 0
	templates: list[dict[str, object]] = []
	share_prefix = 'share'
	share_data = config.plugin_data.get('share-note')
	if isinstance(share_data, dict) and isinstance(share_data.get('yamlField'), str) and share_data['yamlField']:
		share_prefix = share_data['yamlField']
	garden: dict[str, list[str]] = {'dg-publish': [], 'dg-home': []}
	garden_keys: Counter[str] = Counter()
	shared: list[str] = []

	for note in walk.notes:
		front = note.frontmatter
		type_counts[note.note_type] += 1
		type_rules[note.note_type][note.type_rule] += 1
		type_folders[note.note_type][top_folder(note.path)] += 1
		if note.decode_errors:
			decode_problems.append(note.path)
		if front.errors and front.present:
			invalid.append({'path': note.path, 'error': front.errors[0], 'raw': front.raw})
		elif front.errors:
			unclosed.append(note.path)
		if front.present:
			with_frontmatter += 1
		if front.duplicates:
			duplicates.append({'path': note.path, 'keys': sorted(set(front.duplicates))})
		for key, value in front.properties.items():
			prop_notes[key] += 1
			shape_name = shape(value)
			prop_shapes[key][shape_name] += 1
			prop_folders[key][top_folder(note.path)] += 1
			type_props[note.note_type][key] += 1
			kind = obsidian_type(key, shape_name)
			if kind and shape_name not in ('empty', 'empty list'):
				prop_types[key][kind] += 1
			if isinstance(value, list):
				for item in value:
					prop_values[key][display(item)] += 1
			else:
				prop_values[key][display(value)] += 1
			if isinstance(value, Unparsed):
				unparsed.append({'path': note.path, 'key': key, 'reason': value.reason, 'raw': value.raw})
			if key.casefold() in DEPRECATED_KEYS:
				deprecated[key] += 1
			if key.startswith('dg-'):
				garden_keys[key] += 1
				if key in garden and (value is True or value == 'true'):
					garden[key].append(note.path)
		if f'{share_prefix}_link' in front.properties:
			shared.append(note.path)
		for tag in frontmatter_tags(front.properties):
			tag_notes[tag].add(note.path)
			tag_sources[tag]['frontmatter'] += 1
		for line in body_lines(front.body):
			task = TASK_LINE.match(line)
			if task:
				statuses[task.group('status')] += 1
				signature = task_signature(task.group('text'))
				signatures[signature] += 1
				signature_folders[signature][top_folder(note.path)] += 1
				task_folders[top_folder(note.path)] += 1
				if len(signature_examples[signature]) < EXAMPLES:
					signature_examples[signature].append(f'{note.path}: {line.strip()}')
			for tag in inline_tags(line):
				tag_notes[tag].add(note.path)
				tag_sources[tag]['inline'] += 1
		if note.note_type == 'template':
			body = front.body
			templates.append({
				'path': note.path,
				'properties': list(front.properties) if front.is_valid else [],
				'frontmatter': 'valid' if front.is_valid else 'invalid' if front.present else 'none',
				'templater': '<%' in front.raw or '<%' in body,
				'core_variables': '{{' in front.raw or '{{' in body,
			})

	for key in sorted(prop_notes):
		properties[key] = {
			'notes': prop_notes[key],
			'shapes': dict(sorted_counts(prop_shapes[key])),
			'obsidian_types': dict(sorted_counts(prop_types[key])),
			'declared_type': config.declared_types.get(key),
			'top_values': dict(sorted_counts(prop_values[key])[:TOP_VALUES]),
			'distinct_values': len(prop_values[key]),
			'top_folders': dict(sorted_counts(prop_folders[key])),
		}
	variants: dict[str, list[str]] = defaultdict(list)
	for key in prop_notes:
		variants[re.sub(r'[\s_-]+', '', key.casefold())].append(key)
	property_variants = sorted(sorted(group) for group in variants.values() if len(group) > 1)

	for name, count in sorted_counts(type_counts):
		types[name] = {
			'notes': count,
			'rules': dict(sorted_counts(type_rules[name])),
			'folders': dict(sorted_counts(type_folders[name])),
			'properties': {key: round(value / count, 3) for key, value in sorted_counts(type_props[name])},
		}

	tags = {
		tag: {'notes': len(paths), 'frontmatter': tag_sources[tag]['frontmatter'], 'inline': tag_sources[tag]['inline']}
		for tag, paths in sorted(tag_notes.items(), key=lambda item: (-len(item[1]), item[0]))
	}
	tag_groups: dict[str, list[str]] = defaultdict(list)
	for tag in tag_notes:
		tag_groups[tag.casefold()].append(tag)
	tag_variants = sorted(sorted(group) for group in tag_groups.values() if len(group) > 1)

	ignore_filters = [str(item) for item in config.app.get('userIgnoreFilters', []) if isinstance(item, str)] if isinstance(config.app.get('userIgnoreFilters'), list) else []
	ignored = {item: sum(1 for note in walk.notes if ignored_by(note.path, item)) for item in ignore_filters}

	tasks_data = config.plugin_data.get('obsidian-tasks-plugin')
	tasks_settings: dict[str, object] = {}
	if isinstance(tasks_data, dict):
		for key in ('globalFilter', 'taskFormat', 'removeGlobalFilter', 'setCreatedDate', 'setDoneDate', 'setCancelledDate'):
			if key in tasks_data:
				tasks_settings[key] = tasks_data[key]
		status_settings = tasks_data.get('statusSettings')
		if isinstance(status_settings, dict):
			defined = []
			for group in ('coreStatuses', 'customStatuses'):
				for item in status_settings.get(group, []) or []:
					if isinstance(item, dict):
						defined.append({
							'symbol': str(item.get('symbol', '')),
							'name': str(item.get('name', '')),
							'type': str(item.get('type', '')),
							'group': 'core' if group == 'coreStatuses' else 'custom',
						})
			tasks_settings['statuses'] = defined

	linter_data = config.plugin_data.get('obsidian-linter')
	linter: dict[str, object] = {}
	if isinstance(linter_data, dict):
		linter['settings'] = {key: value for key, value in sorted(linter_data.items()) if isinstance(value, bool)}
		linter['foldersToIgnore'] = linter_data.get('foldersToIgnore', [])
		linter['filesToIgnore'] = linter_data.get('filesToIgnore', [])
		rules = linter_data.get('ruleConfigs')
		if isinstance(rules, dict):
			linter['enabled_rules'] = {
				name: {key: value for key, value in sorted(settings.items()) if key != 'enabled'}
				for name, settings in sorted(rules.items())
				if isinstance(settings, dict) and settings.get('enabled') is True
			}
			linter['disabled_rules'] = sorted(name for name, settings in rules.items() if isinstance(settings, dict) and settings.get('enabled') is not True)

	declared_mismatches = []
	for key, declared in sorted(config.declared_types.items()):
		observed = prop_types.get(key)
		if observed:
			other = {kind: count for kind, count in observed.items() if kind != declared}
			if other:
				declared_mismatches.append({'property': key, 'declared': declared, 'observed_otherwise': dict(sorted_counts(other))})

	plugins = []
	for plugin_id in sorted(set(config.installed) | set(config.community_enabled)):
		info = config.installed.get(plugin_id, {})
		plugins.append({
			'id': plugin_id,
			'name': info.get('name', ''),
			'version': info.get('version', ''),
			'enabled': plugin_id in config.community_enabled,
			'installed': plugin_id in config.installed,
		})

	return {
		'survey_version': SURVEY_VERSION,
		'totals': {
			'notes': len(walk.notes),
			'with_frontmatter': with_frontmatter,
			'invalid_frontmatter': len(invalid),
			'unclosed_frontmatter': len(unclosed),
			'folders': len(walk.folders),
			'canvases': len(walk.canvases),
			'bases': len(walk.bases),
			'attachments': sum(walk.attachments.values()),
			'tasks': sum(statuses.values()),
		},
		'layout': {
			'folders': {folder: walk.folders[folder] for folder in sorted(walk.folders, key=lambda name: name.split('/'))},
			'hidden_folders': walk.hidden,
			'attachments': dict(sorted_counts(walk.attachments)),
			'canvases': walk.canvases,
			'bases': walk.bases,
			'ignore_filters': ignored,
		},
		'types': types,
		'properties': properties,
		'property_variants': property_variants,
		'deprecated_keys': {key: {'count': count, 'use': DEPRECATED_KEYS[key.casefold()]} for key, count in sorted(deprecated.items())},
		'declared_type_mismatches': declared_mismatches,
		'tags': tags,
		'tag_variants': tag_variants,
		'templates': {'folders': config.template_folders, 'files': templates},
		'periodic': config.daily,
		'tasks': {
			'plugin': tasks_settings,
			'statuses_in_use': dict(sorted_counts(statuses)),
			'by_folder': dict(sorted_counts(task_folders)),
			'signatures': {
				signature: {'count': count, 'folders': dict(sorted_counts(signature_folders[signature])), 'examples': signature_examples[signature]}
				for signature, count in sorted_counts(signatures)
			},
		},
		'plugins': {'core_enabled': config.core_enabled, 'community': plugins},
		'publishing': {
			'digital_garden': {
				'installed': 'digitalgarden' in config.installed,
				'enabled': 'digitalgarden' in config.community_enabled,
				'published_notes': garden['dg-publish'],
				'published_by_folder': dict(sorted_counts(Counter(parent_folder(path) for path in garden['dg-publish']))),
				'home': garden['dg-home'],
				'dg_keys': dict(sorted_counts(garden_keys)),
			},
			'share_note': {
				'installed': 'share-note' in config.installed,
				'enabled': 'share-note' in config.community_enabled,
				'property_prefix': share_prefix,
				'shared_notes': shared,
				'shared_by_folder': dict(sorted_counts(Counter(parent_folder(path) for path in shared))),
			},
		},
		'linter': {'installed': 'obsidian-linter' in config.installed, 'enabled': 'obsidian-linter' in config.community_enabled, **linter},
		'problems': {
			'invalid_frontmatter': invalid,
			'unclosed_frontmatter': unclosed,
			'unparsed_values': unparsed,
			'duplicate_keys': duplicates,
			'decode_errors': decode_problems,
			'unreadable_config': sorted(config.unreadable),
			'unreadable_notes': walk.unreadable,
		},
	}


def draft_schema(data: dict[str, object]) -> dict[str, object]:
	"""A schema drafted from the survey by fixed rules; a proposal, nothing more."""
	properties = data['properties']
	assert isinstance(properties, dict)
	property_types: dict[str, object] = {}
	for key, info in properties.items():
		observed = info['obsidian_types']
		ranked = sorted_counts(observed)
		property_types[key] = {
			'type': ranked[0][0] if ranked else None,
			'declared': info['declared_type'],
			'conflicts': dict(ranked[1:]),
			'notes': info['notes'],
		}
	types: dict[str, object] = {}
	type_data = data['types']
	assert isinstance(type_data, dict)
	for name, info in type_data.items():
		if name == 'template':
			continue
		required = sorted(key for key, share in info['properties'].items() if share >= REQUIRED_AT)
		optional = sorted(key for key, share in info['properties'].items() if OPTIONAL_AT <= share < REQUIRED_AT)
		rare = sorted(key for key, share in info['properties'].items() if share < OPTIONAL_AT)
		types[name] = {
			'notes': info['notes'],
			'from': info['rules'],
			'folders': info['folders'],
			'required': required,
			'optional': optional,
			'rare': rare,
		}
	tags = data['tags']
	assert isinstance(tags, dict)
	roots: Counter[str] = Counter()
	children: dict[str, set[str]] = defaultdict(set)
	for tag, info in tags.items():
		root, _, rest = tag.partition('/')
		roots[root] += info['notes']
		if rest:
			children[root].add(rest)
	tasks = data['tasks']
	assert isinstance(tasks, dict)
	return {
		'schema_version': 1,
		'draft': True,
		'drafted_by': 'goblin-archivist sniff-vault',
		'thresholds': {'required_at': REQUIRED_AT, 'optional_at': OPTIONAL_AT},
		'types': types,
		'properties': property_types,
		'tags': {root: {'notes': count, 'children': sorted(children[root])} for root, count in sorted_counts(roots)},
		'tasks': {
			'statuses_in_use': tasks['statuses_in_use'],
			'statuses_defined': tasks['plugin'].get('statuses', []),
			'formats_in_use': {signature: info['count'] for signature, info in list(tasks['signatures'].items())[:TOP_VALUES]},
		},
	}


def cell(value: object) -> str:
	text = display(value) if not isinstance(value, str) else value
	return text.replace('|', '\\|').replace('\n', ' ')


def table(headers: list[str], rows: list[list[object]]) -> list[str]:
	if not rows:
		return ['_None._', '']
	lines = ['| ' + ' | '.join(headers) + ' |', '|' + '|'.join('---' for _ in headers) + '|']
	lines += ['| ' + ' | '.join(cell(item) for item in row) + ' |' for row in rows]
	return lines + ['']


def plural(count: int, word: str) -> str:
	return f'{count} {word}' if count == 1 else f'{count} {word}s'


def counts_text(counts: dict[str, int]) -> str:
	return ', '.join(f'{key} ({value})' for key, value in counts.items())


def render_report(data: dict[str, object], schema: dict[str, object]) -> str:
	"""The survey as Markdown for a person to read beside the vault."""
	totals = data['totals']
	layout = data['layout']
	out: list[str] = ['# Vault sniffed', '']
	out += ['Read-only survey by goblin-archivist. Every number below comes from a fixed script; the draft schema beside this file follows from them by the thresholds in section 12.', '']

	out += ['## 1. Totals', '']
	out += table(['What', 'Count'], [[key.replace('_', ' '), value] for key, value in totals.items()])

	empty = sum(1 for count in layout['folders'].values() if count == 0)
	out += ['## 2. Folder layout', '', 'Notes per folder, counting every note below it. Hidden folders at the root (never read): ' + (', '.join(f'`{name}`' for name in layout['hidden_folders']) or 'none') + '.', '']
	out += [f'{plural(empty, "folder")} with no note anywhere below (attachments only, or empty) are left out here; `survey.json` lists every folder.', '']
	out += table(['Folder', 'Notes'], [['\u00a0\u00a0' * folder.count('/') + folder.rsplit('/', 1)[-1] + '/', count] for folder, count in layout['folders'].items() if count])
	out += ['Attachments by extension: ' + (counts_text(layout['attachments']) or 'none') + '.', '']
	out += [f'Canvases: {len(layout["canvases"])}. Bases: {len(layout["bases"])}.', '']
	if layout['ignore_filters']:
		out += ['Obsidian is told to ignore (`userIgnoreFilters`); notes there are still counted:', '']
		out += table(['Filter', 'Notes'], [[key, value] for key, value in layout['ignore_filters'].items()])

	out += ['## 3. Note types (apparent)', '', 'A note\'s type comes from the first rule that fits: a `type`, `fileClass`, `category` or `kind` property; a template folder; a daily or periodic note folder and file name format; otherwise its top-level folder.', '']
	out += table(['Type', 'Notes', 'Rule', 'Folders'], [[name, info['notes'], counts_text(info['rules']), counts_text(info['folders'])] for name, info in data['types'].items()])

	out += ['## 4. Properties', '', f'{totals["with_frontmatter"]} of {plural(totals["notes"], "note")} have a frontmatter block; {totals["invalid_frontmatter"]} of those will not parse (section 11).', '']
	rows = []
	for key, info in data['properties'].items():
		rows.append([f'`{key}`', info['notes'], counts_text(info['shapes']), info['declared_type'] or '', counts_text(info['top_values']), info['distinct_values']])
	out += table(['Property', 'Notes', 'Shapes', 'Declared', 'Top values', 'Distinct'], rows)
	if data['property_variants']:
		out += ['Names that differ only in case, spaces, hyphens or underscores:', '']
		out += [f'- {", ".join(f"`{name}`" for name in group)}' for group in data['property_variants']] + ['']
	if data['deprecated_keys']:
		out += ['Singular keys Obsidian dropped in 1.9:', '']
		out += [f'- `{key}`: {plural(info["count"], "note")}; Obsidian reads `{info["use"]}`' for key, info in data['deprecated_keys'].items()] + ['']
	if data['declared_type_mismatches']:
		out += ['Properties whose values disagree with the type declared in `.obsidian/types.json`:', '']
		out += table(['Property', 'Declared', 'Observed otherwise'], [[f'`{item["property"]}`', item['declared'], counts_text(item['observed_otherwise'])] for item in data['declared_type_mismatches']])

	out += ['## 5. Tags', '', f'{len(data["tags"])} distinct tags. Inline tags inside code fences, inline code and URLs are not counted.', '']
	out += table(['Tag', 'Notes', 'In frontmatter', 'Inline'], [[f'#{tag}', info['notes'], info['frontmatter'], info['inline']] for tag, info in data['tags'].items()])
	if data['tag_variants']:
		out += ['Tags that differ only in case:', ''] + [f'- {", ".join(f"#{tag}" for tag in group)}' for group in data['tag_variants']] + ['']

	templates = data['templates']
	out += ['## 6. Templates', '']
	out += ['Template folders: ' + (', '.join(f'`{item["folder"]}` ({item["source"]})' for item in templates['folders']) or 'none configured') + '.', '']
	out += table(['Template', 'Frontmatter', 'Properties', 'Templater', 'Core {{variables}}'], [[item['path'], item['frontmatter'], ', '.join(item['properties']), 'yes' if item['templater'] else 'no', 'yes' if item['core_variables'] else 'no'] for item in templates['files']])
	if data['periodic']:
		out += ['Daily and periodic notes:', '']
		out += table(['Source', 'Folder', 'Format', 'Template'], [[item['source'], item['folder'] or '(root)', item['format'], item['template']] for item in data['periodic']])

	tasks = data['tasks']
	out += ['## 7. Tasks', '']
	plugin = tasks['plugin']
	if plugin:
		settings = {key: value for key, value in plugin.items() if key != 'statuses'}
		out += ['Tasks plugin settings: ' + (', '.join(f'`{key}` = {display(value)}' for key, value in settings.items()) or 'none read') + '.', '']
		if plugin.get('statuses'):
			out += table(['Symbol', 'Name', 'Type', 'Group', 'Lines'], [[f'`[{item["symbol"]}]`', item['name'], item['type'], item['group'], tasks['statuses_in_use'].get(item['symbol'], 0)] for item in plugin['statuses']])
	defined = {item['symbol'] for item in plugin.get('statuses', [])} if plugin else set()
	undefined = {symbol: count for symbol, count in tasks['statuses_in_use'].items() if symbol not in defined}
	if undefined:
		out += ['Status symbols in use that the Tasks plugin does not define: ' + counts_text({f'[{key}]': value for key, value in undefined.items()}) + '.', '']
	out += ['Task line formats, as the order of their metadata (`text` is the description):', '']
	out += table(['Format', 'Lines', 'Folders', 'Examples'], [[signature, info['count'], counts_text(info['folders']), ' ⁂ '.join(info['examples'])] for signature, info in tasks['signatures'].items()])

	plugins = data['plugins']
	out += ['## 8. Plugins', '', 'Core plugins on: ' + (', '.join(plugins['core_enabled']) or 'none recorded') + '.', '']
	out += table(['Community plugin', 'Name', 'Version', 'Enabled', 'Installed'], [[item['id'], item['name'], item['version'], 'yes' if item['enabled'] else 'no', 'yes' if item['installed'] else 'no'] for item in plugins['community']])

	publishing = data['publishing']
	garden = publishing['digital_garden']
	share = publishing['share_note']
	out += ['## 9. Publishing', '', 'Both plugins publish note by note, by a property on the note, so this lists flagged notes grouped by folder.', '']
	out += [f'**Digital Garden** (installed: {"yes" if garden["installed"] else "no"}, enabled: {"yes" if garden["enabled"] else "no"}): {plural(len(garden["published_notes"]), "note")} with `dg-publish: true`; home note: {", ".join(garden["home"]) or "none"}.', '']
	out += table(['Folder', 'Published notes'], [[folder, count] for folder, count in garden['published_by_folder'].items()])
	if garden['dg_keys']:
		out += ['`dg-` properties in use: ' + counts_text(garden['dg_keys']) + '.', '']
	out += [f'**Share Note** (installed: {"yes" if share["installed"] else "no"}, enabled: {"yes" if share["enabled"] else "no"}, property prefix `{share["property_prefix"]}`): {plural(len(share["shared_notes"]), "note")} with `{share["property_prefix"]}_link`.', '']
	out += table(['Folder', 'Shared notes'], [[folder, count] for folder, count in share['shared_by_folder'].items()])
	if garden['published_notes'] or share['shared_notes']:
		out += ['Every flagged note:', ''] + [f'- {path} (Digital Garden)' for path in garden['published_notes']] + [f'- {path} (Share Note)' for path in share['shared_notes']] + ['']

	linter = data['linter']
	out += ['## 10. Linter', '']
	out += [f'Installed: {"yes" if linter["installed"] else "no"}; enabled: {"yes" if linter["enabled"] else "no"}.', '']
	if linter.get('settings'):
		out += ['Switches: ' + ', '.join(f'`{key}` = {display(value)}' for key, value in linter['settings'].items()) + '.', '']
	if 'enabled_rules' in linter:
		out += ['Rules it applies (each can rewrite a note):', '']
		out += table(['Rule', 'Settings'], [[name, ', '.join(f'{key} = {display(value)}' for key, value in settings.items())] for name, settings in linter['enabled_rules'].items()])
		out += [f'Rules off: {len(linter["disabled_rules"])}. Folders it skips: ' + (', '.join(f'`{item}`' for item in linter.get('foldersToIgnore', [])) or 'none') + '.', '']

	problems = data['problems']
	out += ['## 11. Problems', '']
	out += [f'Frontmatter that will not parse: {plural(len(problems["invalid_frontmatter"]), "note")}.', '']
	for item in problems['invalid_frontmatter']:
		out += [f'### {item["path"]}', '', f'{item["error"]}', '', '```yaml', item['raw'], '```', '']
	if problems['unclosed_frontmatter']:
		out += ['Notes that open a frontmatter block and never close it (Obsidian shows no properties):', ''] + [f'- {path}' for path in problems['unclosed_frontmatter']] + ['']
	if problems['unparsed_values']:
		out += ['Values valid in YAML but outside what the survey reads, quoted as found:', '']
		for item in problems['unparsed_values']:
			out += [f'- {item["path"]}, `{item["key"]}` ({item["reason"]}):', '', '  ```yaml', *[f'  {line}' for line in item['raw'].split('\n')], '  ```', '']
	if problems['duplicate_keys']:
		out += ['Keys set twice in one block (the last value is the one counted):', ''] + [f'- {item["path"]}: {", ".join(item["keys"])}' for item in problems['duplicate_keys']] + ['']
	if problems['decode_errors']:
		out += ['Notes that are not valid UTF-8:', ''] + [f'- {path}' for path in problems['decode_errors']] + ['']
	if problems['unreadable_notes']:
		out += ['Notes that could not be read (a broken link, or no permission):', ''] + [f'- {path}' for path in problems['unreadable_notes']] + ['']
	if problems['unreadable_config']:
		out += ['Config files that would not parse: ' + ', '.join(f'`{name}`' for name in problems['unreadable_config']) + '.', '']

	out += ['## 12. Draft schema', '', f'`schema.draft.json` beside this report. A property is required for a type when at least {int(REQUIRED_AT * 100)}% of that type\'s notes carry it, optional from {int(OPTIONAL_AT * 100)}%, rare below. Each property takes the Obsidian type most of its values fit; the others are listed as conflicts.', '']
	rows = []
	for name, info in schema['types'].items():
		rows.append([name, info['notes'], ', '.join(info['required']), ', '.join(info['optional']), len(info['rare'])])
	out += table(['Type', 'Notes', 'Required', 'Optional', 'Rare'], rows)
	conflicted = [[f'`{key}`', info['type'] or '(none)', counts_text(info['conflicts'])] for key, info in schema['properties'].items() if info['conflicts']]
	if conflicted:
		out += ['Properties whose values fit more than one type:', ''] + table(['Property', 'Draft type', 'Also seen'], conflicted)
	return '\n'.join(out).rstrip('\n') + '\n'


def dump(value: object) -> str:
	return json.dumps(value, indent='\t', ensure_ascii=False, sort_keys=False) + '\n'


def is_within(path: Path, folder: Path) -> bool:
	"""Whether path is folder or below it, compared by file identity.

	Comparing names would miss `Vault` against `vault` on a file system that
	ignores case, which macOS does by default.
	"""
	for candidate in (path, *path.parents):
		try:
			if candidate.exists() and candidate.samefile(folder):
				return True
		except OSError:
			continue
	return False


def committable(path: Path) -> str | None:
	"""The repository that would track a file at path, or None.

	None when no existing folder above path is in a git work tree, when git
	ignores the path there, or when git cannot be run.
	"""
	anchor = next((candidate for candidate in (path, *path.parents) if candidate.is_dir()), None)
	if anchor is None:
		return None
	try:
		top = subprocess.run(['git', '-C', str(anchor), 'rev-parse', '--show-toplevel'], capture_output=True, text=True, check=False)
		if top.returncode != 0:
			return None
		probe = path / 'report.md'
		ignored = subprocess.run(['git', '-C', str(anchor), 'check-ignore', '-q', str(probe)], capture_output=True, check=False)
	except OSError:
		return None
	return None if ignored.returncode == 0 else top.stdout.strip()


def write_outputs(vault: Path, out: Path) -> dict[str, Path]:
	"""Survey the vault and write the three files.

	Refuses an output folder inside the vault, and one inside a repository
	that does not ignore it, since the report quotes the vault freely.
	"""
	vault = vault.resolve()
	out = out.resolve()
	if is_within(out, vault):
		raise SniffError(f'the output folder {out} is inside the vault; the survey writes nothing there')
	repository = committable(out)
	if repository:
		raise SniffError(f'the output folder {out} is inside the repository {repository}, which does not ignore it; the report quotes the vault, so it must never be committed')
	data = survey(vault)
	schema = draft_schema(data)
	out.mkdir(parents=True, exist_ok=True)
	paths = {'survey': out / 'survey.json', 'report': out / 'report.md', 'schema': out / 'schema.draft.json'}
	paths['survey'].write_text(dump(data), encoding='utf-8')
	paths['schema'].write_text(dump(schema), encoding='utf-8')
	paths['report'].write_text(render_report(data, schema), encoding='utf-8')
	return paths
