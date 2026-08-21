#!/usr/bin/env python3
"""assign_profile_ids.py: assign a stable `id` (three-letter store prefix +
three-digit number, e.g. DOS001, PER002) to every profile file that lacks one.

Idempotent by construction: a file that already has `id` is left untouched.
New ids are highest-existing-plus-one per prefix, never a re-sort — running
this twice, or running it after adding one new profile, never renumbers an
existing file. That stability is what lets linkedProfileIds reference id
instead of slug: an id must outlive a slug rename.

usage:
	assign_profile_ids.py [--dry-run]
"""
import sys
import re
import argparse
from pathlib import Path

from _profiles_core import DOSSIER_DIR, PERSONAS_DIR

PREFIXES = {
	DOSSIER_DIR: "DOS",
	PERSONAS_DIR: "PER",
}


def _existing_max(directory: Path, prefix: str) -> int:
	highest = 0
	if not directory.is_dir():
		return highest
	for path in sorted(directory.glob("*.md")):
		if path.name == "README.md":
			continue
		text = path.read_text()
		m = re.search(rf"^id: {prefix}(\d{{3}})$", text, re.MULTILINE)
		if m:
			highest = max(highest, int(m.group(1)))
	return highest


def assign(directory: Path, prefix: str, dry_run: bool) -> list[str]:
	changed = []
	if not directory.is_dir():
		return changed
	next_num = _existing_max(directory, prefix) + 1
	for path in sorted(directory.glob("*.md")):
		if path.name == "README.md":
			continue
		text = path.read_text()
		if re.search(r"^id: \w+\d+$", text, re.MULTILINE):
			continue
		m = re.match(r"^(---\n)(.*?\n)(---\n.*)$", text, re.DOTALL)
		if not m:
			print(f"skip (no frontmatter): {path}", file=sys.stderr)
			continue
		new_id = f"{prefix}{next_num:03d}"
		next_num += 1
		new_frontmatter = f"id: {new_id}\n" + m.group(2)
		new_text = m.group(1) + new_frontmatter + m.group(3)
		changed.append(f"{path}: {new_id}")
		if not dry_run:
			path.write_text(new_text)
	return changed


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--dry-run", action="store_true")
	args = parser.parse_args()

	all_changed = []
	for directory, prefix in PREFIXES.items():
		all_changed.extend(assign(directory, prefix, args.dry_run))

	if not all_changed:
		print("No files needed an id; nothing to do.")
		return 0

	verb = "Would assign" if args.dry_run else "Assigned"
	print(f"{verb} {len(all_changed)} id(s):")
	for line in all_changed:
		print(f"  {line}")
	return 0


if __name__ == "__main__":
	sys.exit(main())
