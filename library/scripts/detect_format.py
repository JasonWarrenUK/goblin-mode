#!/usr/bin/env python3
"""Detect whether a roadmap is in the old simple format or the rich format.

The rewritten roadmap skills call this and branch on the exit code, so the
old-vs-rich heuristic lives in one place rather than being re-implemented in
each skill.

A roadmap is OLD (simple) format if ANY of:
  1. roadmaps.json parses to an OBJECT with a top-level "roadmaps" key (the old
     pointer registry) rather than an ARRAY of phase objects; or
  2. the referenced .md contains `<a name="m` or `#m{N}-{doing|todo|blocked|done}`
     section anchors; or
  3. the .md uses prose `— **depends on` clauses with a `graph TD` block and no
     `graph LR` block (the simple diagram style).

Usage: detect_format.py [ROADMAP_JSON_PATH]
  Path optional; without it the roadmap is located by walking up from the cwd.

Exit codes: 0 = rich format, 3 = old (simple) format (migration needed),
2 = could not be located or parsed.

Prints a one-line verdict to stdout.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from _roadmap_core import RoadmapError, load, resolve_roadmap_path

_ANCHOR_RE = re.compile(r'<a name="m\d|#m\d+-(?:doing|todo|blocked|done)')


def _md_paths(data, json_path):
    """Every .md path referenced by the roadmap json, resolved against its dir."""
    base = Path(json_path).resolve().parent.parent  # .claude/ -> project root
    paths = []
    if isinstance(data, list):
        for phase in data:
            if phase.get("path"):
                paths.append(base / phase["path"])
    elif isinstance(data, dict):
        for entry in data.get("roadmaps", []):
            if isinstance(entry, dict) and entry.get("path"):
                paths.append(base / entry["path"])
    return [p for p in paths if p.exists()]


def main() -> int:
    explicit = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        path, data = load(explicit)
    except RoadmapError as exc:
        print(f"✗ {exc}")
        return 2

    # 1. pointer-registry object vs phase array
    if isinstance(data, dict) and "roadmaps" in data:
        print("old: roadmaps.json is a pointer registry, not a phase array")
        return 3

    # 2 + 3. inspect the referenced markdown
    for md in _md_paths(data, path):
        text = md.read_text()
        if _ANCHOR_RE.search(text):
            print(f"old: {md.name} uses <a name>/#m anchors")
            return 3
        if "graph TD" in text and "graph LR" not in text and "**depends on" in text:
            print(f"old: {md.name} uses graph TD + prose depends-on")
            return 3

    print("rich: phase-array roadmaps.json, no old-format markers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
