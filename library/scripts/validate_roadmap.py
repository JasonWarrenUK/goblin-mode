#!/usr/bin/env python3
"""Validate a roadmap in .claude/roadmaps.json.

Checks, for the active (non-archived) phase:
  1. dependsOn / blocks parity — every task->gate dependency is mirrored in the
     gate's blocks[], and every gate blocks[] entry lists the gate in its dependsOn.
  2. Every dependsOn entry resolves to a task, a milestone, or a gate, and
     every gate's optional `imposes` is one of blocked, paused, deferred.
  3. Acyclicity — the task->task dependsOn graph has no cycles. Conceptual
     loops (e.g. an iterative-flagged pair) are expressed via the `iterative`
     flag, never a real back-edge. A detected cycle is reported and the status
     recompute is skipped, since a cycle lets the fixed point self-confirm
     corrupt statuses as clean.
  4. Status correctness — each recomputable task's stored status matches the
     mechanical recompute under the precedence rule
     deferred > paused > blocked > todo.

Terminal statuses (done, out_of_scope) and root-seeded paused/deferred tasks
(a parked status with empty dependsOn) are left as authored, not recomputed.

Usage: validate_roadmap.py [ROADMAP_JSON_PATH]
  The path is optional; without it the roadmap is located by walking up from
  the current working directory. Run from the project root, or pass the path.

Exit codes: 0 = clean, 1 = one or more discrepancies (printed to stdout),
2 = the roadmap could not be located or parsed.
"""
from __future__ import annotations

import sys

from _roadmap_core import (
    IMPOSABLE_STATUSES,
    VALID_STATUSES,
    RoadmapError,
    active_phase,
    build_index,
    count_active_phases,
    find_cycles,
    is_held,
    load,
    recompute_all,
)


def main() -> int:
    explicit = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        path, data = load(explicit)
        if count_active_phases(data) > 1:
            print(f"WARNING: {count_active_phases(data)} active phases; "
                  "validating the last one.")
        phase = active_phase(data)
    except RoadmapError as exc:
        print(f"✗ {exc}")
        return 2
    tasks, milestones, gates = build_index(phase)
    problems = []

    # 1 + 2: dependency resolution, status enum, and gate parity
    known = set(tasks) | set(milestones) | set(gates)
    gate_expected_blocks = {gid: set() for gid in gates}
    for tid, task in tasks.items():
        if task.get("status") not in VALID_STATUSES:
            problems.append(f"{tid}: invalid status {task.get('status')!r}")
        for dep in task.get("dependsOn", []):
            if dep not in known:
                problems.append(f"{tid}: dependsOn {dep!r} resolves to nothing")
            if dep in gates:
                gate_expected_blocks[dep].add(tid)

    for gid, gate in gates.items():
        imposes = gate.get("imposes")
        if imposes is not None and imposes not in IMPOSABLE_STATUSES:
            problems.append(
                f"gate {gid}: imposes {imposes!r} not in "
                f"{{blocked, paused, deferred}}")
        declared = set(gate.get("blocks", []))
        expected = gate_expected_blocks[gid]
        for missing in sorted(expected - declared):
            problems.append(f"gate {gid}: blocks[] missing {missing} (task depends on gate)")
        for extra in sorted(declared - expected):
            problems.append(f"gate {gid}: blocks[] lists {extra} but it does not depend on {gid}")

    # 3: acyclicity of task->task dependsOn, then status correctness.
    # A cycle makes the fixed-point self-confirm stored values, so report it
    # and skip the recompute rather than validate corruption as clean.
    cycles = find_cycles(tasks)
    for cycle in cycles:
        problems.append("cycle detected: " + " -> ".join(cycle))

    if not cycles:
        computed = recompute_all(tasks, milestones, gates)
        for tid, task in tasks.items():
            if is_held(task):
                continue  # held seeds are authored, not recomputed
            expected = computed.get(tid)
            if expected != task.get("status"):
                problems.append(
                    f"{tid}: stored {task.get('status')!r} but recompute gives {expected!r}")
    else:
        problems.append(
            "status recompute skipped: resolve the cycle(s) above first")

    if problems:
        print(f"✗ {len(problems)} discrepancy(ies) in '{phase.get('name')}':")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"✓ '{phase.get('name')}' clean: "
          f"{len(tasks)} tasks, {len(milestones)} milestones, {len(gates)} gates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
