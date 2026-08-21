#!/usr/bin/env python3
"""profiles.py: store-agnostic lookup and listing across both profile stores
(library/profiles/dossier/*.md and library/profiles/personas/*.md).

Neither store is privileged over the other here: both are read through the
same _profiles_core.py parser, on the same shared schema. This is the CLI
`hud-profiles` calls. red-doc/red-branch keep calling red-personas.py
directly for the personas-only, narrower surface their allowed-tools
permission strings already name.

This script's dossier-reading commands only work on a machine that has
library/profiles/dossier/ populated — that directory is gitignored, so a
fresh checkout of this repo has none of it. `list --store dossier` on such a
checkout returns nothing, correctly.

usage:
	profiles.py list [--store {dossier|personas|both}]
	profiles.py get {slug} [--store {dossier|personas|both}]
"""
import sys
import argparse

from _profiles_core import DOSSIER_DIR, PERSONAS_DIR, load_store


def _stores(name: str) -> list[tuple[str, "Path"]]:
	if name == "dossier":
		return [("dossier", DOSSIER_DIR)]
	if name == "personas":
		return [("personas", PERSONAS_DIR)]
	return [("dossier", DOSSIER_DIR), ("personas", PERSONAS_DIR)]


def cmd_list(args: argparse.Namespace) -> int:
	for label, directory in _stores(args.store):
		profiles = load_store(directory)
		print(f"## {label} ({len(profiles)})")
		if not profiles:
			print("  (none)")
			continue
		for p in profiles:
			print(f"  {p.get('slug')}: {p.get('description', '(no description)')}")
		print()
	return 0


def cmd_get(args: argparse.Namespace) -> int:
	found = False
	for label, directory in _stores(args.store):
		path = directory / f"{args.slug}.md"
		if not path.is_file():
			continue
		found = True
		profiles = {p["_path"].stem: p for p in load_store(directory)}
		p = profiles.get(args.slug)
		if p is None:
			continue
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
	p_list.set_defaults(func=cmd_list)

	p_get = sub.add_parser("get")
	p_get.add_argument("slug")
	p_get.add_argument("--store", default="both", choices=["dossier", "personas", "both"])
	p_get.set_defaults(func=cmd_get)

	args = parser.parse_args()
	return args.func(args)


if __name__ == "__main__":
	sys.exit(main())
