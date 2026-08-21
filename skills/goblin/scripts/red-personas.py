#!/usr/bin/env python3
"""red-personas.py: exact lookup, filtering and summary-level auditing for the
`red` skill family's persona store (library/profiles/personas/*.md).

Each persona file is a `---`-delimited YAML frontmatter block (slug,
description, quickFacts, isRealPerson, updated, pronouns, linkedProfileIds,
scope, and a one-line summary of each of the nine reader-behaviour fields)
followed by the full nine-field prose body a human reads during the
interview/roster/dossier-derivation steps. This script only ever reads
frontmatter; it never parses the prose body, and it never writes a persona
file itself — that stays the calling skill's job, after the user approves a
drafted persona (see ../../library/references/red/methodology.md Step 1a/1c).

This script never reads library/profiles/dossier/ — that directory is
gitignored on purpose, and a persona's link back to it (in linkedProfileIds)
names the dossier slug but never carries dossier content. Staleness comparison
against the live dossier entry happens in the calling skill at resolution
time, not here, so this file stays blind to the one directory in this repo
that must never be read by a tracked script and printed to a tracked or shared
surface. It shares its frontmatter parser with the dossier side via
_profiles_core.py (see library/scripts/profiles.py for the hoisted, store-
agnostic CLI); this file keeps its own narrower CLI so red-doc/red-branch's
allowed-tools permission strings do not need to change.

usage:
	red-personas.py roster --scope {doc|branch}
	red-personas.py get {slug}
	red-personas.py find-typo {slug} --scope {doc|branch}
	red-personas.py audit
"""
import sys
import re
import argparse

from _profiles_core import (
	PERSONAS_DIR, REQUIRED_KEYS, SHARED_META_KEYS, STANCE_KEYS,
	read_profile, load_store, in_scope, find_by_id,
)

SUMMARY_KEYS = STANCE_KEYS
STRONG_SIGNAL_KEYS = ["power", "fluency", "trigger"]


def load_all() -> list[dict]:
	return load_store(PERSONAS_DIR)


def cmd_roster(args: argparse.Namespace) -> int:
	personas = [p for p in load_all() if in_scope(p, args.scope)]
	if not personas:
		print(f"No personas scoped to '{args.scope}' yet.")
		return 0
	for p in personas:
		print(f"## {p.get('slug')}  (scope: {', '.join(p.get('scope') or [])})")
		for key in SUMMARY_KEYS:
			print(f"  {key}: {p.get(key, '(missing)')}")
		if p.get("linkedProfileIds"):
			print(f"  linkedProfileIds: {p['linkedProfileIds']}")
		print()
	return 0


def cmd_get(args: argparse.Namespace) -> int:
	path = PERSONAS_DIR / f"{args.slug}.md"
	persona = read_profile(path) if path.is_file() else find_by_id(args.slug, PERSONAS_DIR)
	if persona is None:
		print(f"persona not found: {args.slug}", file=sys.stderr)
		return 1
	for key in list(SHARED_META_KEYS) + SUMMARY_KEYS:
		print(f"{key}: {persona.get(key)}")
	print()
	print(persona["_body"].strip())
	return 0


def _edit_distance_1(a: str, b: str) -> bool:
	if a == b:
		return False
	if abs(len(a) - len(b)) > 1:
		return False
	# substitution
	if len(a) == len(b):
		diffs = sum(1 for x, y in zip(a, b) if x != y)
		return diffs == 1
	# insertion/deletion: check every single-char removal from the longer string
	longer, shorter = (a, b) if len(a) > len(b) else (b, a)
	for i in range(len(longer)):
		if longer[:i] + longer[i + 1:] == shorter:
			return True
	return False


def cmd_find_typo(args: argparse.Namespace) -> int:
	personas = [p for p in load_all() if in_scope(p, args.scope)]
	slug = args.slug.lower()
	candidates = []
	for p in personas:
		existing = p.get("slug", "")
		if existing == slug:
			print(f"'{slug}' already exists in scope '{args.scope}'.")
			return 0
		if existing.startswith(slug) or slug.startswith(existing):
			candidates.append(existing)
		elif existing.rstrip("s") == slug or slug.rstrip("s") == existing:
			candidates.append(existing)
		elif _edit_distance_1(existing, slug):
			candidates.append(existing)
	if candidates:
		print(f"'{slug}' not found in scope '{args.scope}'. Near miss: {', '.join(candidates)}")
	else:
		print(f"'{slug}' not found in scope '{args.scope}'. No near-miss candidates; likely genuinely new.")
	return 0


def _tokens(text: str) -> set[str]:
	return set(re.findall(r"[a-z]+", (text or "").lower()))


def _jaccard(a: str, b: str) -> float:
	ta, tb = _tokens(a), _tokens(b)
	if not ta and not tb:
		return 1.0
	if not ta or not tb:
		return 0.0
	return len(ta & tb) / len(ta | tb)


# Free-text summaries almost never match verbatim even when the underlying
# stance is identical (drafters reword for the specific domain), so exact
# string equality is too brittle to catch a real near-duplicate. This is a
# heuristic, not a certainty: it flags for a human look, it never merges.
SIMILARITY_THRESHOLD = 0.3


def _field_similarity(a: dict, b: dict) -> tuple[list[str], list[str]]:
	similar, differed = [], []
	for key in SUMMARY_KEYS:
		if key == "verdict_style":
			continue  # presentation, not differentiation, per the plan
		score = _jaccard(a.get(key), b.get(key))
		if score >= SIMILARITY_THRESHOLD:
			similar.append(f"{key} ({score:.2f})")
		else:
			differed.append(key)
	return similar, differed


def cmd_audit(args: argparse.Namespace) -> int:
	personas = load_all()
	issues = 0

	for p in personas:
		missing = [k for k in REQUIRED_KEYS if k not in p]
		if missing:
			issues += 1
			print(f"Missing-field warning: {p.get('slug', p['_path'].stem)} is missing {', '.join(missing)}")

	for i, a in enumerate(personas):
		for b in personas[i + 1:]:
			strong_scores = [_jaccard(a.get(k), b.get(k)) for k in STRONG_SIGNAL_KEYS]
			# Two of the three strong-signal fields is the threshold: three-of-three
			# exact-token-overlap on power+fluency+trigger is rare even for two
			# personas sharing a real stance, because domain-specific wording
			# (a document's Deep Dive vs a branch's call-site) varies the fluency
			# and trigger clauses even when the underlying rigour is identical.
			# Requiring all three misses real near-duplicates; two catches the
			# stance without catching every persona that shares one common word.
			strong_hits = sum(1 for s in strong_scores if s >= SIMILARITY_THRESHOLD)
			if strong_hits >= 2:
				similar, differed = _field_similarity(a, b)
				issues += 1
				print(f"Near-duplicate warning (heuristic — review before merging): {a.get('slug')} / {b.get('slug')}")
				print(f"  similar fields: {', '.join(similar) if similar else '(none)'}")
				print(f"  differ: {', '.join(differed) if differed else '(none)'}")
				print(f"  strong-signal hits: {strong_hits}/3 on power/fluency/trigger")
				print()

	if issues == 0:
		print("No missing-field or near-duplicate issues.")
	return 0


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	sub = parser.add_subparsers(dest="command", required=True)

	p_roster = sub.add_parser("roster")
	p_roster.add_argument("--scope", required=True, choices=["doc", "branch"])
	p_roster.set_defaults(func=cmd_roster)

	p_get = sub.add_parser("get")
	p_get.add_argument("slug")
	p_get.set_defaults(func=cmd_get)

	p_typo = sub.add_parser("find-typo")
	p_typo.add_argument("slug")
	p_typo.add_argument("--scope", required=True, choices=["doc", "branch"])
	p_typo.set_defaults(func=cmd_find_typo)

	p_audit = sub.add_parser("audit")
	p_audit.set_defaults(func=cmd_audit)

	args = parser.parse_args()
	return args.func(args)


if __name__ == "__main__":
	sys.exit(main())
