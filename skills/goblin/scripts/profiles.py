#!/usr/bin/env python3
"""profiles.py: store-agnostic lookup, listing and counting across both
profile stores (the dossier and the persona store).

Neither store is privileged over the other here: both are read through the
same _profiles_core.py parser, on the same shared schema. This is the CLI
`goblin:hud-profiles` calls. red-doc/red-branch keep calling red-personas.py
directly for the personas-only, narrower surface their allowed-tools
permission strings already name.

The "personas" store here searches two directories via personas_dirs()
(a user's local ~/.claude/library/profiles/personas/, then the plugin's
shipped personas/), merged and de-duplicated by slug so this CLI's counts
and listings match red-personas.py's view of what personas actually exist.

This script's dossier-reading commands only work on a machine that has
the dossier populated — that directory is gitignored, so a fresh checkout
of this repo has none of it. `list --store dossier` on such a checkout
returns nothing, correctly.

usage:
	profiles.py list [--store {dossier|personas|both}] [--format {short|full}]
	profiles.py count [--store {dossier|personas|both}]
	profiles.py get {slug-or-id} [--store {dossier|personas|both}]
"""
import sys
import argparse

from _profiles_core import DOSSIER_DIR, SHARED_META_KEYS, load_store, personas_dirs


FULL_FIELDS = [k for k in SHARED_META_KEYS if k != "updated"]


def _load_personas() -> list[dict]:
	seen_slugs = set()
	merged = []
	for directory in personas_dirs():
		for p in load_store(directory):
			slug = p.get("slug")
			if slug in seen_slugs:
				continue
			seen_slugs.add(slug)
			merged.append(p)
	return merged


def _stores(name: str) -> list[tuple[str, list[dict]]]:
	dossier = load_store(DOSSIER_DIR)
	personas = _load_personas()
	if name == "dossier":
		return [("dossier", dossier)]
	if name == "personas":
		return [("personas", personas)]
	return [("dossier", dossier), ("personas", personas)]


def cmd_list(args: argparse.Namespace) -> int:
	for label, profiles in _stores(args.store):
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
	for label, profiles in _stores(args.store):
		print(f"{label}: {len(profiles)}")
	return 0


def _resolve(name: str, profiles: list[dict]) -> dict | None:
	by_slug = {p.get("slug"): p for p in profiles}
	if name in by_slug:
		return by_slug[name]
	for p in profiles:
		if p.get("id") == name:
			return p
	return None


def cmd_get(args: argparse.Namespace) -> int:
	found = False
	for label, profiles in _stores(args.store):
		p = _resolve(args.slug, profiles)
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
	return args.func(args)


if __name__ == "__main__":
	sys.exit(main())
