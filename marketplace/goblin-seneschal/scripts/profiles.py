#!/usr/bin/env python3
"""profiles.py: store-agnostic lookup, listing and counting across both
profile stores (library/profiles/dossier/*.md and
library/profiles/personas/*.md).

Neither store is privileged over the other here: both are read through the
same _profiles_core.py parser, on the same shared schema. This is the CLI
goblin-seneschal's `consult-dossiers` skill calls; it is a copy of
goblin-mode's library/scripts/profiles.py with the store locations taken
from flags.

The stores are the user's own and never ship with the plugin. A store that
was asked for and does not exist, or a missing PyYAML, gets one line naming
what is missing and exit 2.

usage:
	profiles.py [--dossier-dir DIR] [--personas-dir DIR] list [--store {dossier|personas|both}] [--format {short|full}]
	profiles.py [--dossier-dir DIR] [--personas-dir DIR] count [--store {dossier|personas|both}]
	profiles.py [--dossier-dir DIR] [--personas-dir DIR] get {slug-or-id} [--store {dossier|personas|both}]
"""
import sys
import argparse
from pathlib import Path

try:
	from _profiles_core import DOSSIER_DIR, PERSONAS_DIR, SHARED_META_KEYS, load_store, find_by_id
except ImportError as error:
	print(f"missing: {error.name or 'a module'} (PyYAML: pip install pyyaml)", file=sys.stderr)
	sys.exit(2)

FULL_FIELDS = [k for k in SHARED_META_KEYS if k != "updated"]

# Set by main() from the flags.
STORE_DIRS: dict[str, Path] = {"dossier": DOSSIER_DIR, "personas": PERSONAS_DIR}


def _stores(name: str) -> list[tuple[str, Path]]:
	names = ["dossier", "personas"] if name == "both" else [name]
	return [(label, STORE_DIRS[label]) for label in names]


def cmd_list(args: argparse.Namespace) -> int:
	for label, directory in _stores(args.store):
		profiles = load_store(directory)
		print(f"## {label} ({len(profiles)})")
		if not profiles:
			print("  (none)")
			continue
		if args.format == "short":
			for p in profiles:
				print(f"  {p.get('slug')}")
		else:
			for p in profiles:
				print(f"  --- {p.get('slug')} ---")
				for key in FULL_FIELDS:
					print(f"  {key}: {p.get(key)}")
		print()
	return 0


def cmd_count(args: argparse.Namespace) -> int:
	for label, directory in _stores(args.store):
		profiles = load_store(directory)
		print(f"{label}: {len(profiles)}")
	return 0


def _resolve(name: str, directory) -> dict | None:
	profiles = {p.get("slug"): p for p in load_store(directory)}
	if name in profiles:
		return profiles[name]
	return find_by_id(name, directory)


def cmd_get(args: argparse.Namespace) -> int:
	found = False
	for label, directory in _stores(args.store):
		p = _resolve(args.slug, directory)
		if p is None:
			continue
		found = True
		print(f"## {label}: {p.get('slug')}")
		for key, value in p.items():
			if key.startswith("_"):
				continue
			print(f"{key}: {value}")
		print()
		print(p["_body"].strip())
		print()
	if not found:
		print(f"profile not found in any store: {args.slug}", file=sys.stderr)
		return 1
	return 0


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--dossier-dir", type=Path, default=DOSSIER_DIR, help="the dossier store (real colleagues)")
	parser.add_argument("--personas-dir", type=Path, default=PERSONAS_DIR, help="the personas store")
	sub = parser.add_subparsers(dest="command", required=True)

	p_list = sub.add_parser("list")
	p_list.add_argument("--store", default="both", choices=["dossier", "personas", "both"])
	p_list.add_argument("--format", default="short", choices=["short", "full"])
	p_list.set_defaults(func=cmd_list)

	p_count = sub.add_parser("count")
	p_count.add_argument("--store", default="both", choices=["dossier", "personas", "both"])
	p_count.set_defaults(func=cmd_count)

	p_get = sub.add_parser("get")
	p_get.add_argument("slug")
	p_get.add_argument("--store", default="both", choices=["dossier", "personas", "both"])
	p_get.set_defaults(func=cmd_get)

	args = parser.parse_args()
	STORE_DIRS["dossier"] = args.dossier_dir.expanduser()
	STORE_DIRS["personas"] = args.personas_dir.expanduser()
	asked = _stores(args.store)
	missing = [f"{label} store {directory}" for label, directory in asked if not directory.is_dir()]
	if len(missing) == len(asked):
		print(f"missing: {'; '.join(missing)} (the dossier_dir and personas_dir options)", file=sys.stderr)
		return 2
	if missing:
		print(f"skipped: {'; '.join(missing)} is not there", file=sys.stderr)
	return args.func(args)


if __name__ == "__main__":
	sys.exit(main())
