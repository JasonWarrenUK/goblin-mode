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
reads the dossier directory unless explicitly pointed there, so a script
that only wants personas (like red-personas.py) can import this and stay
blind to the gitignored directory by simply never passing its path in.

Two different anchors, deliberately. This module ships inside the `goblin`
plugin, whose install path varies (loaded in place from
~/.claude/skills/goblin when developed locally, or copied into a per-version
cache directory when installed from a marketplace). SHIPPED_PERSONAS_DIR
(bob.md, cedric.md — the generic examples every installer gets) travels
*inside* the plugin, so it is correctly __file__-relative: that resolves to
the right place under either install method, because the plugin's own
directory structure is what moves together. DOSSIER_DIR and
USER_PERSONAS_DIR are the opposite case: per-installer personal data that
must survive a plugin update and must resolve the same way regardless of
install method, so they are anchored to the fixed, well-known
~/.claude/library/profiles/ location instead of anywhere relative to
__file__ — in the marketplace-cache case, __file__'s parents have no
library/ sibling at all. personas_dirs() searches both persona locations, so
a user's own custom personas (or `goblin.md`, kept local rather than shipped)
in the fixed location are found alongside the shipped generic pair.
"""
import re
from pathlib import Path

import yaml

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SHIPPED_PERSONAS_DIR = PLUGIN_ROOT / "personas"

HOME_CLAUDE_DIR = Path.home() / ".claude"
DOSSIER_DIR = HOME_CLAUDE_DIR / "library" / "profiles" / "dossier"
USER_PERSONAS_DIR = HOME_CLAUDE_DIR / "library" / "profiles" / "personas"


def personas_dirs() -> list[Path]:
	"""Search order: a user's own local persona (USER_PERSONAS_DIR) shadows
	a shipped one of the same slug (SHIPPED_PERSONAS_DIR), since a local
	override is more likely to be the one the user actually wants found
	first when both directories are searched by slug."""
	return [USER_PERSONAS_DIR, SHIPPED_PERSONAS_DIR]

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
