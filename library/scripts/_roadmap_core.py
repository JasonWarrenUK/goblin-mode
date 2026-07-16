#!/usr/bin/env python3
"""Shared core for the roadmap scripts in this directory.

The roadmap source of truth is `.claude/roadmaps.json`, an array of phase
objects `{name, path, archived?, externalGates, milestones}`. The active phase
is the single non-`archived` entry. Statuses are recomputed mechanically from
the dependency graph under the precedence rule

    deferred > paused > blocked > todo

with `done` and `out_of_scope` terminal, and root-seeded `paused`/`deferred`
(a parked status on a task with empty `dependsOn`) held as authored.

This module is imported by roadmap.py (the single CLI entry point), which
lives beside it in ~/.claude/library/scripts/. It has no dependencies outside
the standard library and requires Python 3.8+. British spelling throughout.
"""
from __future__ import annotations

import json
from pathlib import Path

# Precedence: higher rank wins when several dependencies impose a status.
RANK = {"todo": 0, "blocked": 1, "paused": 2, "deferred": 3}
TERMINAL = {"done", "out_of_scope"}
VALID_STATUSES = {"todo", "blocked", "paused", "deferred", "done", "out_of_scope"}
IMPOSABLE_STATUSES = {"blocked", "paused", "deferred"}


class RoadmapError(Exception):
    """Raised when the roadmap cannot be located or parsed (caller → exit 2)."""


def resolve_roadmap_path(explicit=None) -> Path:
    """Locate `.claude/roadmaps.json` with two-tier resolution.

    1. An explicit path argument (the caller already knows where it is) — used
       directly. This is the deterministic, primary path.
    2. Otherwise walk up from the current working directory looking for
       `.claude/roadmaps.json`. Scripts are run from the project root, so this
       finds the right project. (We deliberately do NOT walk up from __file__:
       this module lives in ~/.claude/library, far from any project.)

    Raises RoadmapError if neither yields a readable file.
    """
    if explicit:
        p = Path(explicit).expanduser()
        if p.is_dir():
            p = p / ".claude" / "roadmaps.json"
        if not p.exists():
            raise RoadmapError(f"roadmap not found at {p}")
        return p
    here = Path.cwd().resolve()
    for parent in [here, *here.parents]:
        candidate = parent / ".claude" / "roadmaps.json"
        if candidate.exists():
            return candidate
    raise RoadmapError(
        "could not locate .claude/roadmaps.json above the current directory; "
        "pass the path explicitly")


def load(explicit=None):
    """Return (path, parsed_json). Raises RoadmapError on locate/parse failure."""
    path = resolve_roadmap_path(explicit)
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise RoadmapError(f"{path} is not valid JSON: {exc}") from exc
    return path, data


def active_phase(data, selector=None):
    """The single non-archived phase. `data` may be a phase array or one phase.

    Rejects the old simple-format pointer registry (`{"roadmaps": [...]}`),
    which is not a phase array — callers should run `roadmap.py detect` /
    migrate. When more than one non-archived phase exists this raises rather
    than silently picking one; pass `selector` (a phase name) to disambiguate.
    """
    if isinstance(data, dict) and "roadmaps" in data and "milestones" not in data:
        raise RoadmapError(
            "roadmaps.json is an old-format pointer registry, not a phase array; "
            "run roadmap-migrate first")
    phases = data if isinstance(data, list) else [data]
    live = [p for p in phases if not p.get("archived")]
    if not live:
        raise RoadmapError("no active (non-archived) phase found")
    if selector:
        matches = [p for p in live if p.get("name") == selector]
        if not matches:
            names = ", ".join(repr(p.get("name")) for p in live)
            raise RoadmapError(
                f"no active phase named {selector!r} (active: {names})")
        chosen = matches[-1]
    elif len(live) > 1:
        names = ", ".join(repr(p.get("name")) for p in live)
        raise RoadmapError(
            f"{len(live)} active phases ({names}); archive the finished ones "
            "or select one with --phase")
    else:
        chosen = live[0]
    if not chosen.get("milestones"):
        raise RoadmapError(
            "active phase has no 'milestones' array — not a rich-format roadmap")
    return chosen


def count_active_phases(data):
    phases = data if isinstance(data, list) else [data]
    return sum(1 for p in phases if not p.get("archived"))


def _require_id(obj, kind, context):
    """Return obj['id'] or raise RoadmapError (clean exit 2, not a KeyError)."""
    if not isinstance(obj, dict) or "id" not in obj:
        raise RoadmapError(f"{kind} in {context} is missing its 'id' field")
    return obj["id"]


def build_index(phase):
    """Return (tasks, milestones, gates) indexes for a phase.

    tasks: {task_id: task_dict}
    milestones: {milestone_id: [member task ids]}
    gates: {gate_id: gate_dict}

    Malformed entries (missing 'id') raise RoadmapError so every caller fails
    with a clean exit 2 rather than a KeyError traceback.
    """
    tasks = {}
    milestones = {}
    for m in phase.get("milestones", []):
        mid = _require_id(m, "milestone", f"phase {phase.get('name')!r}")
        milestones[mid] = [
            _require_id(t, "task", f"milestone {mid}") for t in m.get("tasks", [])
        ]
        for t in m.get("tasks", []):
            tasks[t["id"]] = t
    gates = {}
    for g in phase.get("externalGates", []):
        gates[_require_id(g, "gate", f"phase {phase.get('name')!r}")] = g
    return tasks, milestones, gates


def max_status(a, b):
    return a if RANK[a] >= RANK[b] else b


def imposed_status(dep, computed, tasks, milestones, gates):
    """Status this dependency imposes, using the current computed map.

    Task/milestone deps propagate a parked status: a not-done dependency
    imposes at least 'blocked', and more if it is itself paused/deferred.
    """
    if dep in tasks:
        dep_status = computed.get(dep, tasks[dep].get("status"))
        if dep_status == "done":
            return None
        if dep_status in TERMINAL:  # out_of_scope dep — treat as satisfied
            return None
        return max_status("blocked", dep_status if dep_status in RANK else "blocked")
    if dep in milestones:
        member_ids = milestones[dep]
        worst = None
        for tid in member_ids:
            s = computed.get(tid, tasks.get(tid, {}).get("status"))
            if s == "done" or s in TERMINAL:
                continue
            imp = max_status("blocked", s if s in RANK else "blocked")
            worst = imp if worst is None else max_status(worst, imp)
        return worst
    if dep in gates:
        imposed = gates[dep].get("imposes", "blocked")
        # Bad values are reported by validate_roadmap; degrade to the default
        # here so recompute cannot raise a KeyError from RANK.
        return imposed if imposed in RANK else "blocked"
    return "UNRESOLVED"


def is_held(t):
    """A held seed is never recomputed: done/out_of_scope, or a root-seeded
    paused/deferred task (empty dependsOn with a parked stored status)."""
    s = t.get("status")
    if s in TERMINAL:
        return True
    if s in ("paused", "deferred") and not t.get("dependsOn"):
        return True
    return False


def find_cycles(tasks, milestones=None):
    """Detect cycles in the dependsOn graph, including through milestones.

    Task->task edges are direct. A milestone participates as its own node:
    a task depending on M{N} follows an edge into M{N}, and M{N} "depends on"
    every member task (it completes when they do). This catches convergence
    loops such as task -> M2 -> member -> task, which the fixed-point
    recompute would otherwise mask behind its iteration cap. The skills
    require dependsOn to stay acyclic — a conceptual loop (e.g. an
    iterative-flagged pair) is expressed via the `iterative` flag, never via a
    real back-edge. A stored cycle would let the fixed-point recompute
    self-confirm corrupt statuses, so we surface it instead of recomputing.

    Returns a list of cycles, each a list of node ids closing the loop, e.g.
    ["1SF.1", "1SF.2", "1SF.1"] or ["1SF.1", "M2", "2SF.3", "1SF.1"].
    """
    milestones = milestones or {}
    edges = {
        tid: [d for d in task.get("dependsOn", [])
              if d in tasks or d in milestones]
        for tid, task in tasks.items()
    }
    for mid, member_ids in milestones.items():
        edges[mid] = [t for t in member_ids if t in tasks]
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {nid: WHITE for nid in edges}
    cycles = []

    for start in edges:
        if colour[start] != WHITE:
            continue
        # Iterative DFS: stack holds (node, index-into-its-edges).
        stack = [(start, 0)]
        path = [start]
        colour[start] = GREY
        while stack:
            node, i = stack[-1]
            if i < len(edges[node]):
                stack[-1] = (node, i + 1)
                nxt = edges[node][i]
                if colour[nxt] == GREY:               # back-edge => cycle
                    j = path.index(nxt)
                    cycles.append(path[j:] + [nxt])
                elif colour[nxt] == WHITE:
                    colour[nxt] = GREY
                    path.append(nxt)
                    stack.append((nxt, 0))
            else:
                colour[node] = BLACK
                path.pop()
                stack.pop()
    return cycles


def recompute_all(tasks, milestones, gates):
    """Fixed-point recompute of every recomputable task's status."""
    computed = {}
    for tid, t in tasks.items():
        if is_held(t):
            computed[tid] = t.get("status")  # held fixed, still propagates
    for _ in range(len(tasks) + 2):  # converges well within this many passes
        changed = False
        for tid, task in tasks.items():
            if is_held(task):
                continue
            best = "todo"
            for dep in task.get("dependsOn", []):
                imp = imposed_status(dep, computed, tasks, milestones, gates)
                if imp in (None, "UNRESOLVED"):
                    continue
                best = max_status(best, imp)
            if computed.get(tid) != best:
                computed[tid] = best
                changed = True
        if not changed:
            break
    return computed


def milestone_sinks(phase):
    """Return {milestone_id: [sink task ids]}.

    A task is a milestone sink iff no *other task in the same milestone* lists
    it in its dependsOn. Cross-milestone dependents do not disqualify a sink —
    the milestone completes when its own leaves are done. Sinks are the tasks
    that point INTO the milestone node under the terminal-edge convention
    (`{sink} --> M{N}`). IDs are returned in ascending order.
    """
    result = {}
    for m in phase.get("milestones", []):
        mid = _require_id(m, "milestone", f"phase {phase.get('name')!r}")
        member_ids = [_require_id(t, "task", f"milestone {mid}")
                      for t in m.get("tasks", [])]
        members = set(member_ids)
        depended_on = set()
        for t in m.get("tasks", []):
            for d in t.get("dependsOn", []):
                if d in members:
                    depended_on.add(d)
        sinks = [tid for tid in member_ids if tid not in depended_on]
        result[mid] = sorted(sinks)
    return result
