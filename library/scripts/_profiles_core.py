"""_profiles_core.py: shared frontmatter parsing for the profiles stores
(library/profiles/dossier/*.md and library/profiles/personas/*.md).

Both stores share one schema: id, slug, description, quickFacts,
isRealPerson, updated, pronouns, linkedProfileIds, scope, and the nine
reader-behaviour fields (needs, stake, power, fluency, reads, skips,
trigger, charity, verdict_style). A dossier entry leaves the nine fields
`null`; a persona populates them and leaves `isRealPerson: false`.

`id` is a three-letter store prefix (DOS, PER) plus a three-digit number,
assigned once by assign_profile_ids.py and never reused or renumbered — it
is the stable target linkedProfileIds references, so a persona or dossier
entry can be renamed (its slug changed) without orphaning every link that
points at it. `slug` stays the human-readable, filename-matching handle used
for direct lookups (`get cedric`); `id` is what one profile's
linkedProfileIds names when pointing at another.

This module never distinguishes which store a file came from beyond the
directory it was read from — that decision belongs to the caller. It never
reads library/profiles/dossier/ unless explicitly pointed there, so a script
that only wants personas (like red-personas.py) can import this and stay
blind to the gitignored directory by simply never passing its path in.
"""
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DOSSIER_DIR = REPO_ROOT / "library" / "profiles" / "dossier"
PERSONAS_DIR = REPO_ROOT / "library" / "profiles" / "personas"

SHARED_META_KEYS = (
	"id", "slug", "description", "quickFacts", "isRealPerson", "updated",
	"pronouns", "linkedProfileIds", "scope",
)
STANCE_KEYS = [
	"needs", "stake", "power", "fluency", "reads", "skips",
	"trigger", "charity", "verdict_style",
]
REQUIRED_KEYS = list(SHARED_META_KEYS) + STANCE_KEYS


def read_profile(path: Path) -> dict:
	text = path.read_text()
	m = re.match(r"^---\n(.*?\n)---\n(.*)$", text, re.DOTALL)
	if not m:
		raise ValueError(f"{path}: no frontmatter block found")
	data = yaml.safe_load(m.group(1)) or {}
	data["_body"] = m.group(2)
	data["_path"] = path
	return data


def load_store(directory: Path) -> list[dict]:
	if not directory.is_dir():
		return []
	return [
		read_profile(p) for p in sorted(directory.glob("*.md"))
		if p.name != "README.md"
	]


def in_scope(profile: dict, scope: str) -> bool:
	return scope in (profile.get("scope") or [])


def find_by_id(profile_id: str, *directories: Path) -> dict | None:
	for directory in directories:
		for p in load_store(directory):
			if p.get("id") == profile_id:
				return p
	return None
