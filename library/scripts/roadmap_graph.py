#!/usr/bin/env python3
"""Emit the roadmap dependency graph as JSON, with terminal milestone edges.

The artefact builds its Mermaid diagram from this instead of regex-scraping the
PHASE .md, so the terminal-milestone-edge convention lives in exactly one place
(milestone_sinks in _roadmap_core) and the artefact is immune to a hand-edited or
malformed .md diagram.

Terminal-edge convention: a milestone node M{N} is a SINK for its own tasks and a
SOURCE for anything depending on the whole milestone. So:
  - each of M{N}'s sink tasks (nothing else in the milestone depends on them)
    gets an edge  {sink} -> M{N}   (kind "milestone-complete")
  - a task x whose dependsOn lists M{N} gets an edge  M{N} -> x  (kind "milestone-dep")
  - a task-to-task dependency d -> t gets an edge (kind "task"); a gate g -> t
    (kind "gate"). Soft/iterative edges are not emitted (they are annotations).

Nodes carry status so the caller can class them; done/out_of_scope tasks are still
emitted (the caller decides whether to omit completed nodes).

Usage: roadmap_graph.py [ROADMAP_JSON_PATH] [--json]
  --json is accepted for symmetry; JSON is always emitted.
  Path optional; without it the roadmap is located by walking up from the cwd.

Exit codes: 0 = ok, 2 = the roadmap could not be located or parsed.
"""
from __future__ import annotations

import json
import sys

from _roadmap_core import (
    RoadmapError,
    active_phase,
    build_index,
    load,
    milestone_sinks,
)


def build_graph(phase):
    tasks, milestones, gates = build_index(phase)
    sinks = milestone_sinks(phase)

    nodes = []
    for m in phase.get("milestones", []):
        nodes.append({"id": m["id"], "kind": "milestone", "label": m.get("name", "")})
    for gid, gate in gates.items():
        nodes.append({"id": gid, "kind": "gate", "label": gate.get("name", "")})
    for m in phase.get("milestones", []):
        for t in m.get("tasks", []):
            nodes.append({
                "id": t["id"],
                "kind": "task",
                "milestone": m["id"],
                "status": t.get("status"),
                "description": t.get("description", ""),
                "iterative": bool(t.get("iterative")),
            })

    edges = []
    # task/milestone/gate dependency edges (dep -> task), terminal for milestones
    for tid, task in tasks.items():
        for dep in task.get("dependsOn", []):
            if dep in tasks:
                edges.append({"from": dep, "to": tid, "kind": "task"})
            elif dep in milestones:
                # milestone-as-dependency: node gates the dependent
                edges.append({"from": dep, "to": tid, "kind": "milestone-dep"})
            elif dep in gates:
                edges.append({"from": dep, "to": tid, "kind": "gate"})
    # terminal milestone-completion edges: sink tasks flow INTO the node
    for mid, sink_ids in sinks.items():
        for sid in sink_ids:
            edges.append({"from": sid, "to": mid, "kind": "milestone-complete"})

    return {"phase": phase.get("name"), "nodes": nodes, "edges": edges}


def main() -> int:
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    explicit = positional[0] if positional else None
    try:
        _path, data = load(explicit)
        graph = build_graph(active_phase(data))
    except RoadmapError as exc:
        print(f"✗ {exc}")
        return 2
    print(json.dumps(graph, indent="\t"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
