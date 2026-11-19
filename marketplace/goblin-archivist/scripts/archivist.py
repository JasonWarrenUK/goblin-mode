#!/usr/bin/env python3
"""goblin-archivist's command line. Standard library only.

	archivist.py vaults [--obsidian-config PATH]
		List the vaults Obsidian knows, as JSON, sorted by path.

	archivist.py sniff --vault PATH --base PATH
		Survey the vault read-only and write survey.json, report.md and
		schema.draft.json to <base>/vault/sniff/. Prints those paths as JSON.

Exit codes: 0 done; 2 a bad path, an output folder or file inside the vault
or linked into it, an output folder in a git repository that does not
ignore it, git unable to answer, or a failed write; 3 the vault is not set;
4 the base folder is not set.

The skill passes the plugin's options straight through, so an option nobody
has set can arrive empty or as the literal `${user_config.KEY}`; both count
as unset.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _sniff import SniffError, read_json, write_outputs  # noqa: E402

OBSIDIAN_CONFIG = Path.home() / 'Library' / 'Application Support' / 'obsidian' / 'obsidian.json'
VAULT_FOLDER = 'vault'
SNIFF_FOLDER = 'sniff'


def is_unset(value: str | None) -> bool:
	return value is None or value.strip() == '' or value.strip().startswith('${')


def known_vaults(config_path: Path) -> list[dict[str, object]]:
	data = read_json(config_path) if config_path.exists() else None
	vaults = data.get('vaults') if isinstance(data, dict) else None
	if not isinstance(vaults, dict):
		return []
	listed = []
	for entry in vaults.values():
		if isinstance(entry, dict) and isinstance(entry.get('path'), str):
			listed.append({'path': entry['path'], 'open': entry.get('open') is True, 'exists': Path(entry['path']).is_dir()})
	return sorted(listed, key=lambda item: str(item['path']))


def sniff_folder(base: Path) -> Path:
	return base / VAULT_FOLDER / SNIFF_FOLDER


def main(argv: list[str] | None = None) -> int:
	parser = argparse.ArgumentParser(prog='archivist.py', description='goblin-archivist command line')
	commands = parser.add_subparsers(dest='command', required=True)
	vaults = commands.add_parser('vaults', help='list the vaults Obsidian knows')
	vaults.add_argument('--obsidian-config', type=Path, default=OBSIDIAN_CONFIG)
	sniff = commands.add_parser('sniff', help='survey a vault read-only')
	sniff.add_argument('--vault', default='')
	sniff.add_argument('--base', default='')
	args = parser.parse_args(argv)

	if args.command == 'vaults':
		print(json.dumps(known_vaults(args.obsidian_config), indent='\t'))
		return 0

	if is_unset(args.vault):
		print('The vault is not set. Run `archivist.py vaults` to list the vaults Obsidian knows.', file=sys.stderr)
		return 3
	if is_unset(args.base):
		print('The base folder for archivist output is not set.', file=sys.stderr)
		return 4
	vault = Path(args.vault).expanduser()
	base = Path(args.base).expanduser()
	try:
		paths = write_outputs(vault, sniff_folder(base))
	except SniffError as problem:
		print(str(problem), file=sys.stderr)
		return problem.code
	print(json.dumps({key: str(value) for key, value in paths.items()}, indent='\t'))
	return 0


if __name__ == '__main__':
	sys.exit(main())
