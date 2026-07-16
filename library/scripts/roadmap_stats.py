#!/usr/bin/env python3
"""Emit roadmap status counts for the active phase.

One source of truth for the numbers that the artefact's KPI cards / progress
bars and the ROADMAP_OVERVIEW header both need, so they can never drift.

Usage: roadmap_stats.py [ROADMAP_JSON_PATH] [--json]
  (no flag)  a compact human table: phase totals + per-milestone breakdown
  --json     {total, byStatus, donePct, milestones:[{id,name,total,done,byStatus,donePct}]}

Path optional; without it the roadmap is located by walking up from the cwd.

Exit codes: 0 = ok, 2 = the roadmap could not be located or parsed.
"""
from __future__ import annotations

import json
import sys

from _roadmap_core import (
    VALID_STATUSES,
    RoadmapError,
    active_phase,
    load,
)

_ORDER = ["done", "todo", "blocked", "paused", "deferred", "out_of_scope"]


def _counts(tasks):
    c = {s: 0 for s in VALID_STATUSES}
    for t in tasks:
        s = t.get("status")
        if s in c:
            c[s] += 1
    return c


def _pct(done, total):
    return round(done / total * 100) if total else 0


def build_stats(phase):
    all_counts = {s: 0 for s in VALID_STATUSES}
    total = 0
    milestones = []
    for m in phase.get("milestones", []):
        tasks = m.get("tasks", [])
        c = _counts(tasks)
        for s in c:
            all_counts[s] += c[s]
        total += len(tasks)
        milestones.append({
            "id": m["id"],
            "name": m.get("name", ""),
            "total": len(tasks),
            "done": c["done"],
            "byStatus": c,
            "donePct": _pct(c["done"], len(tasks)),
        })
    return {
        "phase": phase.get("name"),
        "total": total,
        "byStatus": all_counts,
        "donePct": _pct(all_counts["done"], total),
        "milestones": milestones,
    }


def _human(stats):
    lines = [
        f"{stats['phase']}: {stats['byStatus']['done']}/{stats['total']} done "
        f"({stats['donePct']}%)",
        "  " + "  ".join(f"{s}={stats['byStatus'][s]}"
                         for s in _ORDER if stats['byStatus'][s]),
        "",
    ]
    for m in stats["milestones"]:
        active = "  ".join(f"{s}={m['byStatus'][s]}"
                           for s in _ORDER if m['byStatus'][s])
        lines.append(f"  {m['id']:4} {m['done']}/{m['total']:<3} {m['name']}")
        if active:
            lines.append(f"       {active}")
    return "\n".join(lines)


def main() -> int:
    args = sys.argv[1:]
    as_json = "--json" in args
    positional = [a for a in args if not a.startswith("--")]
    explicit = positional[0] if positional else None

    try:
        _path, data = load(explicit)
        stats = build_stats(active_phase(data))
    except RoadmapError as exc:
        print(f"✗ {exc}")
        return 2
    print(json.dumps(stats, indent="\t") if as_json else _human(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
