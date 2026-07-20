#!/usr/bin/env python3
"""roadmap.py — single CLI for the rich phase-array roadmap system.

Replaces the former five sibling scripts (detect_format, validate_roadmap,
recompute_roadmap, roadmap_stats, roadmap_graph) with one entry point and a
shared argument parser. Graph logic lives in _roadmap_core.py; this file owns
presentation (Mermaid, HTML render) and the subcommand plumbing.

Usage: roadmap.py SUBCOMMAND [PATH] [--phase NAME] [flags]

  detect     rich vs old-simple format verdict          (exit 0 rich / 3 old)
  validate   graph integrity + status correctness       (exit 0 clean / 1 not)
  recompute  fixed-point status recompute, writes back  [--check --json
                                                         --reformat --render]
  stats      status counts for the active phase         [--json]
  graph      dependency graph                           [--json --mermaid
                                                         --direction --omit-done
                                                         --palette]
  ready      actionable todo tasks with ordering signals [--json]
  render     deterministic HTML artefact from template   [--out PATH]

PATH is optional everywhere; without it the roadmap is located by walking up
from the cwd. --phase selects one phase by name when several are active
(without it, multiple active phases are an error — never a silent guess).

All subcommands exit 2 when the roadmap cannot be located or parsed.
Requires Python 3.8+, stdlib only. British spelling throughout.
"""
from __future__ import annotations

import argparse
import heapq
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from _roadmap_core import (
    IMPOSABLE_STATUSES,
    VALID_STATUSES,
    RoadmapError,
    active_phase,
    build_index,
    find_cycles,
    is_held,
    load,
    milestone_sinks,
    recompute_all,
)

# ---------------------------------------------------------------------------
# Canonical status→colour table (Reasonable Colors). The single source of
# truth for every projection: PHASE.md Mermaid (literal hexes — GitHub cannot
# resolve CSS vars), the artefact template (semantic vars) and the conventions
# reference at library/references/roadmap-conventions.md, which documents this
# table in prose. Semantics: done=green (finished), todo=gray (blank slate),
# blocked=red (stop), paused=purple (parked), deferred=cinnamon (shelved),
# out_of_scope=faded gray (struck from play), gate=yellow (external),
# milestone=sky (structural). Pink is accent-only, never a status.
# Shade pattern: light bg=shade 1, stroke/text=shade 4; dark bg=shade 6,
# stroke=shade 2 (gray uses 3/5 so the fade stays legible). Diff >=3 keeps AA.
# ---------------------------------------------------------------------------
STATUS_STYLE = {
    "todo": {
        "var": "todo", "bg": "#f6f6f6", "stroke": "#6f6f6f",
        "darkBg": "#222222", "darkStroke": "#8b8b8b", "extra": "",
    },
    "blocked": {
        "var": "blocked", "bg": "#fff8f6", "stroke": "#e0002b",
        "darkBg": "#530003", "darkStroke": "#ffddd8", "extra": "stroke-width:2px",
    },
    "paused": {
        "var": "paused", "bg": "#fdf4ff", "stroke": "#b01fe3",
        "darkBg": "#3a004f", "darkStroke": "#f7d9ff",
        "extra": "stroke-dasharray:4 3",
    },
    "deferred": {
        "var": "deferred", "bg": "#fff8f3", "stroke": "#ac5c00",
        "darkBg": "#371d00", "darkStroke": "#ffdfc6",
        "extra": "stroke-dasharray:2 4,font-style:italic",
    },
    "done": {
        "var": "done", "bg": "#e0ffd9", "stroke": "#008217",
        "darkBg": "#062800", "darkStroke": "#72ff6c", "extra": "",
    },
    "outOfScope": {
        "var": "out-of-scope", "bg": "#f6f6f6", "stroke": "#e2e2e2",
        "darkBg": "#222222", "darkStroke": "#3e3e3e",
        "extra": "stroke-dasharray:2 2",
    },
    "mile": {
        "var": "milestone", "bg": "#e3f7ff", "stroke": "#007590",
        "darkBg": "#001f28", "darkStroke": "#aee9ff", "extra": "font-weight:bold",
    },
    "external": {
        "var": "gate", "bg": "#fff9e5", "stroke": "#7d6f00",
        "darkBg": "#292300", "darkStroke": "#ffe53e",
        "extra": "stroke-dasharray:4 3,font-style:italic",
    },
}
STATUS_TO_CLASS = {
    "todo": "todo", "blocked": "blocked", "paused": "paused",
    "deferred": "deferred", "done": "done", "out_of_scope": "outOfScope",
}
_STATS_ORDER = ["done", "todo", "blocked", "paused", "deferred", "out_of_scope"]
_LABEL_MAX = 48


def project_root(json_path):
    """The project root a roadmap belongs to. roadmaps.json conventionally
    lives at <root>/.claude/roadmaps.json; when it lives elsewhere, treat its
    own directory as the root rather than blindly taking parent.parent."""
    p = Path(json_path).resolve()
    return p.parent.parent if p.parent.name == ".claude" else p.parent


# ---------------------------------------------------------------------------
# detect
# ---------------------------------------------------------------------------
_ANCHOR_RE = re.compile(r'<a name="m\d|#m\d+-(?:doing|todo|blocked|done)')


def _md_paths(data, json_path):
    """Every .md path referenced by the roadmap json, resolved from its root."""
    base = project_root(json_path)
    paths = []
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        entries = data.get("roadmaps", []) if "roadmaps" in data else [data]
    else:
        entries = []
    for entry in entries:
        if isinstance(entry, dict) and entry.get("path"):
            paths.append(base / entry["path"])
    return [p for p in paths if p.exists()]


def cmd_detect(args) -> int:
    try:
        path, data = load(args.path)
    except RoadmapError as exc:
        print(f"✗ {exc}")
        return 2

    if isinstance(data, dict) and "roadmaps" in data:
        print("old: roadmaps.json is a pointer registry, not a phase array")
        return 3

    for md in _md_paths(data, path):
        try:
            text = md.read_text()
        except (OSError, UnicodeDecodeError) as exc:
            print(f"note: could not read {md.name} ({exc}); skipping it")
            continue
        if _ANCHOR_RE.search(text):
            print(f"old: {md.name} uses <a name>/#m anchors")
            return 3
        if "graph TD" in text and "graph LR" not in text and "**depends on" in text:
            print(f"old: {md.name} uses graph TD + prose depends-on")
            return 3

    print("rich: phase-array roadmaps.json, no old-format markers")
    return 0


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------
def _validate_phase(phase):
    """Return the list of discrepancies for one phase (empty = clean)."""
    tasks, milestones, gates = build_index(phase)
    problems = []

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
        for dep in task.get("softDependsOn", []):
            if dep not in known:
                problems.append(f"{tid}: softDependsOn {dep!r} resolves to nothing")

    for gid, gate in gates.items():
        imposes = gate.get("imposes")
        if imposes is not None and imposes not in IMPOSABLE_STATUSES:
            problems.append(
                f"gate {gid}: imposes {imposes!r} not in "
                f"{{blocked, paused, deferred}}")
        declared = set(gate.get("blocks", []))
        expected = gate_expected_blocks[gid]
        for missing in sorted(expected - declared):
            problems.append(
                f"gate {gid}: blocks[] missing {missing} (task depends on gate)")
        for extra in sorted(declared - expected):
            problems.append(
                f"gate {gid}: blocks[] lists {extra} but it does not depend on {gid}")

    cycles = find_cycles(tasks, milestones)
    for cycle in cycles:
        problems.append("cycle detected: " + " -> ".join(cycle))

    if not cycles:
        computed = recompute_all(tasks, milestones, gates)
        for tid, task in tasks.items():
            if is_held(task):
                continue
            expected = computed.get(tid)
            if expected != task.get("status"):
                problems.append(
                    f"{tid}: stored {task.get('status')!r} "
                    f"but recompute gives {expected!r}")
    else:
        problems.append("status recompute skipped: resolve the cycle(s) above first")

    return problems


def cmd_validate(args) -> int:
    try:
        _path, data = load(args.path)
        phase = active_phase(data, args.phase)
    except RoadmapError as exc:
        print(f"✗ {exc}")
        return 2
    problems = _validate_phase(phase)
    tasks, milestones, gates = build_index(phase)
    if problems:
        print(f"✗ {len(problems)} discrepancy(ies) in '{phase.get('name')}':")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"✓ '{phase.get('name')}' clean: "
          f"{len(tasks)} tasks, {len(milestones)} milestones, {len(gates)} gates.")
    return 0


# ---------------------------------------------------------------------------
# recompute
# ---------------------------------------------------------------------------
def _canonical_text(data):
    return json.dumps(data, indent="\t", ensure_ascii=False) + "\n"


def _atomic_write(path, text):
    """Write via temp file + os.replace so a crash cannot truncate the file."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(text)
        os.replace(tmp, str(path))
    except BaseException:
        os.unlink(tmp)
        raise


def cmd_recompute(args) -> int:
    try:
        path, data = load(args.path)
        phase = active_phase(data, args.phase)
    except RoadmapError as exc:
        print(f"✗ {exc}")
        return 2
    tasks, milestones, gates = build_index(phase)

    cycles = find_cycles(tasks, milestones)
    if cycles:
        print("✗ cycle detected; refusing to recompute:")
        for cycle in cycles:
            print("  - " + " -> ".join(cycle))
        return 1

    computed = recompute_all(tasks, milestones, gates)

    if args.json:
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

    if not args.check and changes:
        # Reformat guard: if re-serialising the file as loaded (before any
        # status mutation) does not reproduce it byte-for-byte, a plain write
        # would silently reformat the whole file. Refuse unless told not to.
        original = path.read_text()
        if _canonical_text(data) != original and not args.reformat:
            print("✗ roadmaps.json is not in canonical form (tab-indented, "
                  "ensure_ascii off, trailing newline); a write would reformat "
                  "the whole file, not just statuses. Re-run with --reformat "
                  "to accept that, or normalise the file first.")
            return 1
        for tid, _old, new in changes:
            tasks[tid]["status"] = new
        _atomic_write(path, _canonical_text(data))

    if changes:
        verb = "would change" if args.check else "changed"
        print(f"{verb} {len(changes)} status(es):")
        for tid, old, new in changes:
            print(f"  {tid}: {old} -> {new}")
    else:
        print("no status changes.")

    if args.render and not args.check:
        out = _default_render_path(path, phase)
        if out.exists():
            _render_to(path, data, phase, out)
            print(f"refreshed artefact: {out}")
        else:
            print(f"note: no artefact at {out}; run `roadmap.py render` to create one")
    return 0


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------
def _counts(tasks):
    c = {s: 0 for s in VALID_STATUSES}
    invalid = []
    for t in tasks:
        s = t.get("status")
        if s in c:
            c[s] += 1
        else:
            invalid.append(t.get("id", "<no id>"))
    return c, invalid


def _pct(done, total):
    return round(done / total * 100) if total else 0


def build_stats(phase):
    all_counts = {s: 0 for s in VALID_STATUSES}
    all_invalid = []
    total = 0
    milestones = []
    for m in phase.get("milestones", []):
        tasks = m.get("tasks", [])
        c, invalid = _counts(tasks)
        for s in c:
            all_counts[s] += c[s]
        all_invalid.extend(invalid)
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
        "invalid": all_invalid,
        "donePct": _pct(all_counts["done"], total),
        "milestones": milestones,
    }


def _human_stats(stats):
    lines = [
        f"{stats['phase']}: {stats['byStatus']['done']}/{stats['total']} done "
        f"({stats['donePct']}%)",
        "  " + "  ".join(f"{s}={stats['byStatus'][s]}"
                         for s in _STATS_ORDER if stats['byStatus'][s]),
        "",
    ]
    for m in stats["milestones"]:
        active = "  ".join(f"{s}={m['byStatus'][s]}"
                           for s in _STATS_ORDER if m['byStatus'][s])
        lines.append(f"  {m['id']:4} {m['done']}/{m['total']:<3} {m['name']}")
        if active:
            lines.append(f"       {active}")
    if stats["invalid"]:
        lines.append("")
        lines.append(f"WARNING: {len(stats['invalid'])} task(s) with invalid "
                     f"status, excluded from byStatus: "
                     + ", ".join(stats["invalid"]))
    return "\n".join(lines)


def cmd_stats(args) -> int:
    try:
        _path, data = load(args.path)
        stats = build_stats(active_phase(data, args.phase))
    except RoadmapError as exc:
        print(f"✗ {exc}")
        return 2
    print(json.dumps(stats, indent="\t") if args.json else _human_stats(stats))
    return 0


# ---------------------------------------------------------------------------
# graph
# ---------------------------------------------------------------------------
def build_graph(phase):
    """Nodes+edges JSON, encoding the terminal-milestone-edge convention."""
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
    for tid, task in tasks.items():
        for dep in task.get("dependsOn", []):
            if dep in tasks:
                edges.append({"from": dep, "to": tid, "kind": "task"})
            elif dep in milestones:
                edges.append({"from": dep, "to": tid, "kind": "milestone-dep"})
            elif dep in gates:
                edges.append({"from": dep, "to": tid, "kind": "gate"})
        for dep in task.get("softDependsOn", []):
            if dep in tasks or dep in milestones or dep in gates:
                edges.append({"from": dep, "to": tid, "kind": "soft", "soft": True})
    for mid, sink_ids in sinks.items():
        for sid in sink_ids:
            edges.append({"from": sid, "to": mid, "kind": "milestone-complete"})

    return {"phase": phase.get("name"), "nodes": nodes, "edges": edges}


def _mermaid_label(text):
    text = " ".join(str(text).split())
    if len(text) > _LABEL_MAX:
        text = text[:_LABEL_MAX - 1].rstrip() + "…"
    return text.replace('"', "#quot;")


def _classdef_lines(palette):
    lines = []
    for cls, st in STATUS_STYLE.items():
        if palette == "vars":
            bg = f"var(--color-{st['var']}-bg)"
            stroke = f"var(--color-{st['var']})"
        elif palette == "dark":
            bg, stroke = st["darkBg"], st["darkStroke"]
        else:
            bg, stroke = st["bg"], st["stroke"]
        parts = [f"fill:{bg}", f"stroke:{stroke}", f"color:{stroke}"]
        if st["extra"]:
            parts.append(st["extra"])
        lines.append(f"\tclassDef {cls} {','.join(parts)}")
    return lines


def _topological_order(ids, order, edges):
    """Stable Kahn's algorithm: among the ready nodes, always emit the one
    that appears first in the roadmap. Any cycle remainder (invalid, but the
    diagram should still draw) is appended in roadmap order."""
    indeg = {}
    out = {}
    for e in edges:
        indeg[e["to"]] = indeg.get(e["to"], 0) + 1
        out.setdefault(e["from"], []).append(e["to"])
    heap = [(order[i], i) for i in ids if indeg.get(i, 0) == 0]
    heapq.heapify(heap)
    topo = []
    while heap:
        _, nid = heapq.heappop(heap)
        topo.append(nid)
        for tgt in out.get(nid, []):
            indeg[tgt] -= 1
            if indeg[tgt] == 0:
                heapq.heappush(heap, (order[tgt], tgt))
    emitted = set(topo)
    topo.extend(sorted((i for i in ids if i not in emitted), key=order.get))
    return topo


def mermaid_source(phase, direction="LR", omit_done=False, palette="light"):
    """The complete Mermaid diagram for a phase, classDefs included, so the
    PHASE.md projection and the artefact can never drift. classDefs come
    straight after the graph-type line (before it is a silent render failure).
    Gates that gate nothing (resolved/superseded, kept in the data for the
    record) are not drawn. Nodes and edges are emitted in topological order —
    every source declared before its dependants — which gives the layout
    engine a cleaner rank assignment and a more readable diagram.

    softDependsOn edges render dotted (-.->) and are fed into the same
    topological ordering as hard edges for layout stability; unlike
    dependsOn they may form cycles (Kahn's tolerates this by appending the
    remainder in roadmap order) and never impose status, block a milestone
    sink, or fail validation's acyclicity check.
    """
    graph = build_graph(phase)
    by_id = {n["id"]: n for n in graph["nodes"]}

    skipped = set()
    if omit_done:
        milestone_live = {}
        for n in graph["nodes"]:
            if n["kind"] == "task":
                live = n.get("status") != "done"
                milestone_live[n["milestone"]] = (
                    milestone_live.get(n["milestone"], False) or live)
                if not live:
                    skipped.add(n["id"])
        for n in graph["nodes"]:
            if n["kind"] == "milestone" and not milestone_live.get(n["id"], False):
                skipped.add(n["id"])

    live_edges = [e for e in graph["edges"]
                  if e["from"] not in skipped and e["to"] not in skipped]
    connected = ({e["from"] for e in live_edges}
                 | {e["to"] for e in live_edges})
    skipped.update(n["id"] for n in graph["nodes"]
                   if n["kind"] == "gate" and n["id"] not in connected)

    order = {n["id"]: i for i, n in enumerate(graph["nodes"])}
    ids = [n["id"] for n in graph["nodes"] if n["id"] not in skipped]
    topo = _topological_order(ids, order, live_edges)
    topo_idx = {nid: i for i, nid in enumerate(topo)}

    lines = [f"graph {direction}"]
    lines.extend(_classdef_lines(palette))

    status_members = {}
    for nid in topo:
        n = by_id[nid]
        if n["kind"] == "milestone":
            lines.append(f'\t{n["id"]}["{_mermaid_label(n["id"] + ": " + n["label"])}"]:::mile')
        elif n["kind"] == "gate":
            lines.append(f'\t{n["id"]}["{_mermaid_label(n["id"] + ": " + n["label"])}"]:::external')
        else:
            label = f'{n["id"]}: {n["description"]}'
            if n.get("iterative"):
                label += " ↻"
            lines.append(f'\t{n["id"]}["{_mermaid_label(label)}"]')
            cls = STATUS_TO_CLASS.get(n.get("status"))
            if cls:
                status_members.setdefault(cls, []).append(n["id"])

    for e in sorted(live_edges,
                    key=lambda e: (topo_idx.get(e["from"], len(topo)),
                                   topo_idx.get(e["to"], len(topo)))):
        arrow = "-.->" if e.get("soft") else "-->"
        lines.append(f'\t{e["from"]} {arrow} {e["to"]}')

    for cls in ["todo", "blocked", "paused", "deferred", "done", "outOfScope"]:
        members = status_members.get(cls)
        if members:
            lines.append(f'\tclass {",".join(sorted(members))} {cls}')

    return "\n".join(lines)


def cmd_graph(args) -> int:
    try:
        _path, data = load(args.path)
        phase = active_phase(data, args.phase)
    except RoadmapError as exc:
        print(f"✗ {exc}")
        return 2
    if args.mermaid:
        print(mermaid_source(phase, direction=args.direction,
                             omit_done=args.omit_done, palette=args.palette))
    else:
        print(json.dumps(build_graph(phase), indent="\t"))
    return 0


# ---------------------------------------------------------------------------
# ready
# ---------------------------------------------------------------------------
def build_ready(phase):
    """Actionable candidates: tasks whose effective status is todo, annotated
    with ordering signals so a small model can choose between valid options
    instead of deriving them."""
    tasks, milestones, gates = build_index(phase)
    computed = recompute_all(tasks, milestones, gates)
    effective = {
        tid: (t.get("status") if is_held(t) else computed.get(tid))
        for tid, t in tasks.items()
    }
    sinks = milestone_sinks(phase)
    stats = build_stats(phase)
    milestone_pct = {m["id"]: m["donePct"] for m in stats["milestones"]}
    milestone_name = {m["id"]: m["name"] for m in stats["milestones"]}
    task_milestone = {}
    for m in phase.get("milestones", []):
        for t in m.get("tasks", []):
            task_milestone[t["id"]] = m["id"]

    # Reverse reachability: completing X unblocks everything downstream of it,
    # following task->task edges and milestone membership (a sink completing
    # its milestone reaches tasks that depend on the milestone).
    dependents = {tid: set() for tid in tasks}
    for tid, t in tasks.items():
        for dep in t.get("dependsOn", []):
            if dep in tasks:
                dependents[dep].add(tid)
            elif dep in milestones:
                for member in milestones[dep]:
                    if member in dependents:
                        dependents[member].add(tid)

    def transitive(tid):
        seen, frontier = set(), [tid]
        while frontier:
            nxt = frontier.pop()
            for d in dependents.get(nxt, ()):
                if d not in seen:
                    seen.add(d)
                    frontier.append(d)
        return seen

    candidates = []
    for tid, t in tasks.items():
        if effective.get(tid) != "todo":
            continue
        mid = task_milestone.get(tid)
        candidates.append({
            "id": tid,
            "description": t.get("description", ""),
            "milestone": mid,
            "milestoneName": milestone_name.get(mid, ""),
            "milestoneDonePct": milestone_pct.get(mid, 0),
            "directDependents": len(dependents.get(tid, ())),
            "transitiveUnblocks": len(transitive(tid)),
            "isMilestoneSink": tid in sinks.get(mid, []),
            "notes": t.get("notes", ""),
            "assignee": t.get("assignee", ""),
        })
    candidates.sort(key=lambda c: (-c["transitiveUnblocks"],
                                   -c["milestoneDonePct"], c["id"]))
    return {"phase": phase.get("name"), "candidates": candidates}


def cmd_ready(args) -> int:
    try:
        _path, data = load(args.path)
        ready = build_ready(active_phase(data, args.phase))
    except RoadmapError as exc:
        print(f"✗ {exc}")
        return 2
    if args.json:
        print(json.dumps(ready, indent="\t"))
        return 0
    if not ready["candidates"]:
        print(f"{ready['phase']}: no unblocked todo tasks.")
        return 0
    print(f"{ready['phase']}: {len(ready['candidates'])} unblocked task(s), "
          "highest leverage first")
    for c in ready["candidates"]:
        sink = "  [completes milestone]" if c["isMilestoneSink"] else ""
        who = f"  ({c['assignee']})" if c.get("assignee") else ""
        print(f"  {c['id']:8} unblocks {c['transitiveUnblocks']:<3} "
              f"{c['milestone']} {c['milestoneDonePct']}% done{sink}{who}")
        print(f"           {c['description']}")
    return 0


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------
def _template_path():
    return Path(__file__).resolve().parent.parent / "templates" / "roadmap-artefact.html"


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-") or "roadmap"


def _default_render_path(json_path, phase):
    return (project_root(json_path) / "docs" / "artefacts"
            / f"roadmap-{_slug(phase.get('name'))}.html")


def _assert_header_comment_clean(template_html, template):
    """Guard against a stray comment-close in the template's header comment.

    The template opens with an HTML comment block documenting its placeholders.
    Its first comment-close sequence terminates that block; any *earlier* raw
    close in the prose (or a data blob accidentally injected there) ends the
    comment prematurely and spills the remainder onto the rendered page. The
    header comment therefore must hold exactly one close sequence, and it must
    fall before the <html> root. Fail render loudly rather than corrupt the
    artefact.
    """
    open_marker = "<!--"
    close_marker = "--" + ">"
    start = template_html.find(open_marker)
    root = template_html.find("<html")
    if start == -1 or root == -1:
        return
    header = template_html[start:root]
    closes = header.count(close_marker)
    if closes != 1:
        raise RoadmapError(
            f"template header comment must contain exactly one comment-close "
            f"sequence before <html>, found {closes} in {template}: a stray "
            "close in the prose spills the page. Reword so the comment holds "
            "no raw close sequence except its own terminator.")


def _render_to(json_path, data, phase, out):
    template = _template_path()
    if not template.exists():
        raise RoadmapError(f"render template missing at {template}")
    tasks = []
    for m in phase.get("milestones", []):
        for t in m.get("tasks", []):
            tasks.append({
                "id": t["id"],
                "description": t.get("description", ""),
                "status": t.get("status"),
                "dependsOn": t.get("dependsOn", []),
                "milestone": m["id"],
                "notes": t.get("notes", ""),
                "assignee": t.get("assignee", ""),
            })
    blob = {
        "phase": phase.get("name"),
        "generated": datetime.now().isoformat(timespec="seconds"),
        "stats": build_stats(phase),
        "tasks": tasks,
        "ready": build_ready(phase),
        "mermaid": mermaid_source(phase, direction="TD",
                                  omit_done=True, palette="vars"),
        "validation": _validate_phase(phase),
    }
    # Escape every "<" and ">" as its \uXXXX form so the payload can never
    # break out of its host element: "<" defuses "</script>" and the "<!--"
    # comment open, ">" defuses the "-->" comment close (the mermaid source is
    # full of "-->" edge arrows). < / > are valid JSON escapes and
    # JSON.parse restores the literal characters, so the data is unchanged.
    payload = (json.dumps(blob, ensure_ascii=False)
               .replace("<", "\\u003c")
               .replace(">", "\\u003e"))
    template_html = template.read_text()
    if template_html.count("%%DATA%%") != 1:
        raise RoadmapError(
            "template must contain exactly one %%DATA%% placeholder; found "
            f"{template_html.count('%%DATA%%')} in {template}")
    _assert_header_comment_clean(template_html, template)
    html = (template_html
            .replace("%%TITLE%%", str(phase.get("name") or "Roadmap"))
            .replace("%%DATA%%", payload))
    out.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(out, html)


def cmd_render(args) -> int:
    try:
        path, data = load(args.path)
        phase = active_phase(data, args.phase)
        out = Path(args.out) if args.out else _default_render_path(path, phase)
        _render_to(path, data, phase, out)
    except RoadmapError as exc:
        print(f"✗ {exc}")
        return 2
    print(f"wrote {out}")
    return 0


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="roadmap.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("path", nargs="?", default=None,
                        help="roadmaps.json path or project dir (optional)")
        sp.add_argument("--phase", default=None,
                        help="phase name when several are active")
        return sp

    common(sub.add_parser("detect", help="rich vs old-simple format"))
    common(sub.add_parser("validate", help="graph integrity + status check"))

    sp = common(sub.add_parser("recompute", help="recompute statuses, write back"))
    sp.add_argument("--check", action="store_true", help="preview, no write")
    sp.add_argument("--json", action="store_true",
                    help="print full {id: status} map, no write")
    sp.add_argument("--reformat", action="store_true",
                    help="allow rewriting a non-canonically-formatted file")
    sp.add_argument("--render", action="store_true",
                    help="refresh an existing HTML artefact after writing")

    sp = common(sub.add_parser("stats", help="status counts"))
    sp.add_argument("--json", action="store_true")

    sp = common(sub.add_parser("graph", help="dependency graph"))
    sp.add_argument("--json", action="store_true",
                    help="JSON output (the default)")
    sp.add_argument("--mermaid", action="store_true",
                    help="complete Mermaid source incl. classDefs")
    sp.add_argument("--direction", choices=["LR", "TD"], default="LR")
    sp.add_argument("--omit-done", action="store_true",
                    help="drop done tasks and fully-done milestones")
    sp.add_argument("--palette", choices=["light", "dark", "vars"],
                    default="light",
                    help="literal light/dark hexes, or CSS custom properties")

    sp = common(sub.add_parser("ready", help="actionable todo candidates"))
    sp.add_argument("--json", action="store_true")

    sp = common(sub.add_parser("render", help="write the HTML artefact"))
    sp.add_argument("--out", default=None, help="output path override")

    args = parser.parse_args(argv)
    return {
        "detect": cmd_detect,
        "validate": cmd_validate,
        "recompute": cmd_recompute,
        "stats": cmd_stats,
        "graph": cmd_graph,
        "ready": cmd_ready,
        "render": cmd_render,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
