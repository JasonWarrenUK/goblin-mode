#!/usr/bin/env python3
"""Recompute roadmap task statuses from the dependency graph and write them back.

Runs the same mechanical fixed-point recompute as validate_roadmap.py (precedence
deferred > paused > blocked > todo), then — by default — writes the corrected
statuses back into .claude/roadmaps.json. Only the `status` field of changed
tasks is altered; the file is re-serialised with tab indentation, which
round-trips byte-for-byte with a roadmap authored to these conventions, so field
order, notes and the iterative flag are preserved.

Held seeds (done, out_of_scope, and root-seeded paused/deferred) are never
recomputed. If a task->task cycle is present the recompute is meaningless, so the
tool refuses to write and exits 1.

Usage: recompute_roadmap.py [ROADMAP_JSON_PATH] [--check] [--json]
  (no flag)  rewrite roadmaps.json in place; print each `{ID}: old -> new` change
  --check    compute but do NOT write; print the same change list (preview)
  --json     print the full {id: status} map as JSON (implies no write)

Path optional; without it the roadmap is located by walking up from the cwd.

Exit codes: 0 = success (changes or none), 1 = cycle detected (nothing written),
2 = the roadmap could not be located or parsed.
"""
from __future__ import annotations

import json
import sys

from _roadmap_core import (
    RoadmapError,
    active_phase,
    build_index,
    find_cycles,
    is_held,
    load,
    recompute_all,
)


def main() -> int:
    args = sys.argv[1:]
    check = "--check" in args
    as_json = "--json" in args
    positional = [a for a in args if not a.startswith("--")]
    explicit = positional[0] if positional else None

    try:
        path, data = load(explicit)
        phase = active_phase(data)
    except RoadmapError as exc:
        print(f"✗ {exc}")
        return 2
    tasks, milestones, gates = build_index(phase)

    cycles = find_cycles(tasks)
    if cycles:
        print("✗ cycle detected; refusing to recompute:")
        for cycle in cycles:
            print("  - " + " -> ".join(cycle))
        return 1

    computed = recompute_all(tasks, milestones, gates)

    if as_json:
        # Every task's effective status: held seeds keep their stored value.
        full = {}
        for tid, task in tasks.items():
            full[tid] = task.get("status") if is_held(task) else computed.get(tid)
        print(json.dumps(full, indent="\t"))
        return 0

    changes = []
    for tid, task in tasks.items():
        if is_held(task):
            continue
        new = computed.get(tid)
        old = task.get("status")
        if new != old:
            changes.append((tid, old, new))

    if not check:
        for tid, _old, new in changes:
            tasks[tid]["status"] = new
        if changes:
            path.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n")

    if changes:
        verb = "would change" if check else "changed"
        print(f"{verb} {len(changes)} status(es):")
        for tid, old, new in changes:
            print(f"  {tid}: {old} -> {new}")
    else:
        print("no status changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
