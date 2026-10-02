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
  ready      actionable todo tasks with ordering signals [--json
                                                         --milestones --tiers]
  open       every task not done or out of scope        [--json
                                                         --milestones --tiers]
  render     deterministic HTML artefact from template   [--out PATH]
  claim      ID: record that someone has started a task [--assignee NAME
                                                         --reassign --date]
  release    ID: drop a claim                           [--unassign]
  end        ID: record when a done task finished       [--date --force]
  backfill-ended  date done tasks lacking `ended` from git history
                                                        [--dry-run --json]
  stamp-ended date the done tasks a branch finished     [--base --pr --date
                                                         --dry-run --json]
  hook       EVENT: Claude Code hook entry point (session-start,
             post-tool-use); reads the hook JSON on stdin, always exits 0

PATH is optional everywhere (after ID for claim and release); without it the
roadmap is located by walking up from the cwd. --phase selects one phase by
name when several are active (without it, multiple active phases are an
error — never a silent guess).

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
import zlib
from datetime import date, datetime
from pathlib import Path

from _roadmap_core import (
    IMPOSABLE_STATUSES,
    IN_PROGRESS,
    VALID_STATUSES,
    RoadmapError,
    active_phase,
    build_index,
    display_status,
    find_cycles,
    is_claimed,
    is_held,
    load,
    milestone_sinks,
    recompute_all,
)

# ---------------------------------------------------------------------------
# Canonical status→colour table: the roadmap system's own fixed palette
# (literal hexes, originally derived from Reasonable Colors shades 1/4 and
# 6/2; the values are now owned here and no external palette is loaded).
# The single source of truth for every projection: PHASE.md Mermaid (literal
# hexes — GitHub cannot resolve CSS vars), the artefact template (semantic
# vars, inlined at render from this table) and the conventions reference at
# library/references/roadmap-conventions.md, which documents this table in
# prose. Semantics: done=green (finished), todo=gray (blank slate),
# blocked=red (stop), paused=purple (parked), deferred=cinnamon (shelved),
# out_of_scope=gray, dotted (struck from play), gate=yellow (external),
# milestone=sky (structural), inProgress=azure (a claimed task still in
# play: a display class, never a stored status). Pink is accent-only, never
# a status. Azure and sky are close in hue, so a claimed task's Mermaid label
# also carries IN_PROGRESS_MARKER.
# Every light bg/stroke and dark bg/stroke pair here clears AA (4.5:1).
# ---------------------------------------------------------------------------
STATUS_STYLE = {
    "todo": {
        "var": "todo", "bg": "#f6f6f6", "stroke": "#6f6f6f",
        "darkBg": "#222222", "darkStroke": "#8b8b8b", "extra": "",
    },
    "inProgress": {
        "var": "in-progress", "bg": "#e8f2ff", "stroke": "#0071af",
        "darkBg": "#001c30", "darkStroke": "#c6e0ff", "extra": "",
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
    # The stroke is as faint as it can be while still clearing 3:1 against
    # both tier backgrounds (TIER_STYLE below) and 4.5:1 on its own fill.
    # That lands it within two hex steps of todo's gray, so the dotted
    # border (and the struck label in task lists) is what tells them apart.
    "outOfScope": {
        "var": "out-of-scope", "bg": "#f6f6f6", "stroke": "#717171",
        "darkBg": "#222222", "darkStroke": "#898989",
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
    "todo": "todo", IN_PROGRESS: "inProgress", "blocked": "blocked",
    "paused": "paused", "deferred": "deferred", "done": "done",
    "out_of_scope": "outOfScope",
}

# ---------------------------------------------------------------------------
# Tier backgrounds: the fill behind a tier's subgraph in the dependency
# graph of a tiered phase (see mermaid_source()). Keyed by Mermaid class
# name, same shape as STATUS_STYLE. Two backgrounds, chosen by the tier's
# state (tier_states()): slate for a tier that is underway, taupe with a
# dashed border for one still deferred behind a lower tier. Neither is a
# node colour. Both are muted mid-tones, because a node's fill is a
# near-white tint (near-black in dark) and its stroke carries the hue: the
# background has to sit between the two. Gates every pair must clear, in
# light and dark alike (test_roadmap.py's TierStyle enforces them):
#   - 3:1 or better against every node stroke and the diagram's edge line
#   - 1.35:1 or better against every node fill
#   - 4.5:1 or better for the tier's own label (its stroke colour)
# The two backgrounds share a luminance, so hue alone separates them: the
# dashed border and the state named in the subgraph label carry the same
# signal without colour.
# ---------------------------------------------------------------------------
TIER_STYLE = {
    "tierUnderway": {
        "var": "tier-underway", "bg": "#c3cede", "stroke": "#2f3b4c",
        "darkBg": "#343e4f", "darkStroke": "#d5deea", "extra": "",
    },
    "tierDeferred": {
        "var": "tier-deferred", "bg": "#dccbb9", "stroke": "#4a3826",
        "darkBg": "#4a3c2f", "darkStroke": "#ecdccb",
        "extra": "stroke-dasharray:6 4",
    },
}
TIER_STATE_TO_CLASS = {
    "underway": "tierUnderway", "done": "tierUnderway",
    "deferred": "tierDeferred",
}
IN_PROGRESS_MARKER = " ▸"
_STATS_ORDER = ["done", "todo", "blocked", "paused", "deferred", "out_of_scope"]
_LABEL_MAX = 48

# ---------------------------------------------------------------------------
# Milestone-level derived state (distinct from task status above). A
# milestone is not itself a task, so it has no `status` field to read; its
# state is derived from its member tasks' byStatus counts. Four states,
# ordered as the artefact's Overview sort wants them: deferred first (a
# top-level "shelved" partition, ahead of percentage), then inProgress, todo,
# done. blocked/paused surface as their own milestone-card colour but are not
# part of that four-way partition. Azure is shared with claimed tasks (see
# roadmap-conventions.md), the same way the deferred/blocked/paused/done
# states share their task-status hues: it reads as "live and moving".
#
# The state->CSS-var mapping lives once, in the artefact template's own
# STATE_VAR (JS), not duplicated here: this function only returns the state
# name, so there is exactly one place that maps a state to a colour variable.
# ---------------------------------------------------------------------------
_TIER_CORE = "Core"
_TIER_SUFFIXES = ["Secondary", "Tertiary", "Quaternary", "Quinary"]


def milestone_tier(name):
    """A milestone's release tier from a `(Secondary)`/`(Tertiary)`/…
    suffix on its name, case-insensitive: 0 for no suffix (Core), 1 for
    Secondary, 2 for Tertiary and so on. See roadmap-conventions.md's Tiers
    section: a phase may split into tiers released one after another by
    gate, not by date, and the dashboard reads the suffix to group and
    colour milestones by tier."""
    for i, suffix in enumerate(_TIER_SUFFIXES, start=1):
        if re.search(rf"\({re.escape(suffix)}\)\s*$", name or "", re.IGNORECASE):
            return i
    return 0


def tier_label(tier):
    """The display name of a release tier: `Core` for tier 0, else the
    matching `_TIER_SUFFIXES` entry. The one place the tier vocabulary is
    spelled, so every projection reads core/secondary/tertiary."""
    return _TIER_CORE if tier == 0 else _TIER_SUFFIXES[tier - 1]


def undone_tiers(milestones):
    """The tiers still holding unfinished work, from entries carrying
    `tier`, `total` and `byStatus` (build_stats()'s own milestone shape).
    An empty milestone (total=0) is a data bug flagged separately by
    validation, not a legitimate "still in progress" member; letting it
    hold every later tier deferred forever would hide the real problem
    behind a wrong colour, so it never counts as keeping a tier undone."""
    return {m["tier"] for m in milestones
            if m["total"] and not milestone_all_done(m["byStatus"], m["total"])}


def tier_states(milestones):
    """{tier: state} for every tier present, from the same entries
    undone_tiers() reads. `done` once the tier holds no unfinished work,
    `deferred` while any lower tier still does (the cascade
    milestone_state() applies per milestone), otherwise `underway`."""
    undone = undone_tiers(milestones)
    states = {}
    for tier in sorted({m["tier"] for m in milestones}):
        if tier not in undone:
            states[tier] = "done"
        elif any(lower < tier for lower in undone):
            states[tier] = "deferred"
        else:
            states[tier] = "underway"
    return states


def milestone_all_done(by_status, total):
    """True when a milestone has ≥1 task and every one is done or
    out_of_scope: the "nothing actionable, nothing deferred" reading that
    both milestone_state's rule 1 and the tier cascade in build_stats()
    need. An empty milestone (total=0) is never "done" here; see
    milestone_state's own `empty` rule."""
    if not total:
        return False
    finished = by_status.get("done", 0) + by_status.get("out_of_scope", 0)
    return finished == total


def milestone_all_blocked(by_status, total, in_progress=0):
    """True when a milestone is stuck: work remains, every unfinished task
    (done and out_of_scope set aside) is blocked and no member is claimed
    and in play. However much of it is done, nothing in it can be picked
    up. Only milestone_state()'s `blocked` rule reads this; overview_layout()
    sorts on the resulting `state`, so the tier cascade (which outranks
    stuckness there) governs colour and position alike."""
    unfinished = (total - by_status.get("done", 0)
                  - by_status.get("out_of_scope", 0))
    return (unfinished > 0 and by_status.get("blocked", 0) == unfinished
            and not in_progress)


def milestone_state(by_status, done_pct, total=None, in_progress=0,
                     tier=0, lower_tiers_done=True):
    """One of empty/done/deferred/blocked/inProgress/todo for a milestone,
    given its {status: count} map, completion percentage, (optionally) its
    task total, how many members are claimed and in play, its release tier
    (0 = Core, see milestone_tier()) and whether every milestone in a
    lower tier is fully done (milestone_all_done()). First true rule wins:

    0. no tasks at all -> `empty` (a bug: an empty milestone is never a
       legitimate state, so it is flagged rather than read as `todo`)
    1. every task done/out_of_scope -> `done`
    2. tier >= 1 and a lower tier is not yet fully done -> `deferred`
       (cascade: a Tertiary milestone waits on Secondary too, not only on
       Core)
    3. no actionable member (todo/blocked/paused) left, and >=1 member is
       `deferred` -> `deferred` (a milestone-level gate, needing no tier
       suffix, distinct from the cascade in rule 2. Fires ahead of
       `inProgress` below it: a milestone with one deferred task and nine
       done ones is still "shelved" even though donePct is 90, the same
       deliberate-call-outranks-percentage reading main used before the
       tier rewrite. It does NOT fire while actionable work remains: a
       milestone with five todo tasks and one deferred one is still live
       work to pick up, not a shelved milestone; hiding those five behind
       "deferred" would contradict next-task-group's own ready-set)
    4. stuck (milestone_all_blocked(): work remains, every unfinished task
       is blocked and nobody has a claim in play) -> `blocked`. Done work
       does not soften this: 7 done + 1 blocked reads `blocked`, since
       nothing in the milestone can be picked up
    5. >=1 done task, or a claimed member in play -> `inProgress` (a claim
       on a blocked task keeps the milestone here: someone is on it)
    6. otherwise -> `todo`

    `total` is the task count; 0 (or omitted) reads as empty. Every real
    caller passes it explicitly (build_stats() always knows the count).
    """
    if not total:
        return "empty"
    if milestone_all_done(by_status, total):
        return "done"
    if tier >= 1 and not lower_tiers_done:
        return "deferred"
    actionable = (by_status.get("todo", 0) + by_status.get("blocked", 0)
                  + by_status.get("paused", 0))
    if actionable == 0 and by_status.get("deferred", 0) > 0:
        return "deferred"
    if milestone_all_blocked(by_status, total, in_progress):
        return "blocked"
    if by_status.get("done", 0) > 0 or in_progress > 0:
        return "inProgress"
    return "todo"


_DEV_COLOUR_PALETTE = ["teal", "lime", "magenta", "indigo", "amber", "rose"]


def dev_colour(assignee):
    """Stable colour-family name for an assignee chip, disjoint from every
    status/milestone/gate colour claimed above (green, gray, red, purple,
    cinnamon, yellow, sky, azure; pink is accent-only and never assigned).

    Uses a stable digest rather than Python's builtin hash(): str hashing is
    salted per-process via PYTHONHASHSEED, so builtin hash() would assign a
    different colour to the same assignee across separate render runs and
    break the artefact's byte-determinism guarantee.
    """
    if not assignee:
        return None
    digest = zlib.crc32(assignee.strip().lower().encode("utf-8"))
    return _DEV_COLOUR_PALETTE[digest % len(_DEV_COLOUR_PALETTE)]


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

    for m in phase.get("milestones", []):
        if not m.get("tasks"):
            problems.append(f"{m['id']}: milestone has no tasks")

    known = set(tasks) | set(milestones) | set(gates)
    gate_expected_blocks = {gid: set() for gid in gates}
    for tid, task in tasks.items():
        if task.get("status") not in VALID_STATUSES:
            hint = (" (a claim is the `started` field: run roadmap.py claim)"
                    if task.get("status") == IN_PROGRESS else "")
            problems.append(f"{tid}: invalid status {task.get('status')!r}{hint}")
        if "started" in task and not _is_iso_date(task.get("started")):
            problems.append(
                f"{tid}: started {task.get('started')!r} is not a YYYY-MM-DD date")
        if "ended" in task:
            ended = task.get("ended")
            if not _is_iso_date(ended):
                problems.append(
                    f"{tid}: ended {ended!r} is not a YYYY-MM-DD date")
            elif task.get("status") != "done":
                problems.append(
                    f"{tid}: ended {ended} on a task whose status is "
                    f"{task.get('status')!r}, not done (an end date records "
                    "finished work; remove it when a task is reopened)")
            elif (_is_iso_date(task.get("started"))
                  and ended < task["started"]):
                problems.append(
                    f"{tid}: ended {ended} is before started {task['started']}")
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


def _is_iso_date(value):
    # fromisoformat alone also takes week dates (2026-W39-5) on Python 3.11+
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


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
    # Iterate _STATS_ORDER, not the VALID_STATUSES set directly: set
    # iteration order is hash-order-dependent and salted per-process via
    # PYTHONHASHSEED, so the resulting dict's key order (and therefore the
    # rendered artefact's JSON byte layout) would vary run to run even with
    # identical input, breaking the byte-determinism the render step relies
    # on for clean diffs.
    c = {s: 0 for s in _STATS_ORDER}
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


def _done_pct(done, in_scope, total):
    """donePct for a milestone, tier or phase: done over in_scope, except
    that a set with tasks but none in scope (every one struck out) reads
    100, since nothing in it is left to do. Its state is `done` (see
    milestone_all_done()), so the readout, the progress bar and the sort
    all agree with the colour instead of each patching the same zero. A
    set with no tasks at all stays 0: an empty milestone is a bug (state
    `empty`), never finished work."""
    if total and not in_scope:
        return 100
    return _pct(done, in_scope)


def _in_scope(counts, total):
    """How many tasks are still in play: the total less every out_of_scope
    one. The denominator of every done/total readout and of donePct, so a
    task struck from play never counts as unfinished work. `total` itself
    stays the raw task count (milestone_state() and the ROADMAP_OVERVIEW
    header both need it)."""
    return total - counts.get("out_of_scope", 0)


def _in_progress_count(tasks):
    """Claimed tasks still in play; they are also counted under their own
    status in byStatus, so this is an overlay, never part of the total."""
    return sum(1 for t in tasks
               if display_status(t, t.get("status")) == IN_PROGRESS)


def build_stats(phase):
    all_counts = {s: 0 for s in _STATS_ORDER}  # ordered: see _counts() above
    all_invalid = []
    total = 0
    all_in_progress = 0
    prelim = []
    for m in phase.get("milestones", []):
        tasks = m.get("tasks", [])
        c, invalid = _counts(tasks)
        for s in c:
            all_counts[s] += c[s]
        all_invalid.extend(invalid)
        total += len(tasks)
        in_progress = _in_progress_count(tasks)
        all_in_progress += in_progress
        in_scope = _in_scope(c, len(tasks))
        prelim.append({
            "id": m["id"],
            "name": m.get("name", ""),
            "total": len(tasks),
            "inScope": in_scope,
            "done": c["done"],
            "byStatus": c,
            "inProgress": in_progress,
            "donePct": _done_pct(c["done"], in_scope, len(tasks)),
            "tier": milestone_tier(m.get("name", "")),
        })

    # Tier cascade: a tier counts as "open" only once every non-empty
    # milestone in every earlier tier is done (see undone_tiers() for why an
    # empty one never holds a tier back). milestone_state() computes each
    # milestone's own done-ness standalone, so this pass rolls that up into
    # the one set of tiers with unfinished work, for the cascade check below.
    undone = undone_tiers(prelim)

    milestones = []
    milestones_done = 0
    for m in prelim:
        lower_tiers_done = not any(t < m["tier"] for t in undone)
        state = milestone_state(m["byStatus"], m["donePct"], total=m["total"],
                                in_progress=m["inProgress"], tier=m["tier"],
                                lower_tiers_done=lower_tiers_done)
        if state == "done":
            milestones_done += 1
        milestones.append({
            "id": m["id"], "name": m["name"], "total": m["total"],
            "inScope": m["inScope"],
            "done": m["done"], "byStatus": m["byStatus"],
            "inProgress": m["inProgress"], "donePct": m["donePct"],
            "tier": m["tier"], "state": state,
        })
    in_scope = _in_scope(all_counts, total)
    return {
        "phase": phase.get("name"),
        "total": total,
        "inScope": in_scope,
        "byStatus": all_counts,
        "inProgress": all_in_progress,
        "invalid": all_invalid,
        "donePct": _done_pct(all_counts["done"], in_scope, total),
        "milestonesTotal": len(milestones),
        "milestonesDone": milestones_done,
        "milestones": milestones,
    }


def _human_stats(stats):
    claimed = (f"  ({stats['inProgress']} in progress)"
               if stats.get("inProgress") else "")
    lines = [
        f"{stats['phase']}: {stats['byStatus']['done']}/{stats['inScope']} done "
        f"({stats['donePct']}%)",
        "  " + "  ".join(f"{s}={stats['byStatus'][s]}"
                         for s in _STATS_ORDER if stats['byStatus'][s])
        + claimed,
        "",
    ]
    for m in stats["milestones"]:
        active = "  ".join(f"{s}={m['byStatus'][s]}"
                           for s in _STATS_ORDER if m['byStatus'][s])
        if m.get("inProgress"):
            active += f"  ({m['inProgress']} in progress)"
        lines.append(f"  {m['id']:4} {m['done']}/{m['inScope']:<3} {m['name']}")
        if active:
            lines.append(f"       {active}")
    if stats["invalid"]:
        lines.append("")
        lines.append(f"WARNING: {len(stats['invalid'])} task(s) with invalid "
                     f"status, excluded from byStatus: "
                     + ", ".join(stats["invalid"]))
    return "\n".join(lines)


def _milestone_natural_key(mid):
    return [int(part) if part.isdigit() else part
            for part in re.split(r"(\d+)", str(mid))]


def overview_layout(phase, stats, ready):
    """Sort order and tier grouping for the artefact's Overview/Milestones
    sections, computed once here so the template only renders what this
    says (see roadmap-conventions.md's Milestone sort/tier-group rules).

    Per-milestone: `tier`, `tierLabel` (see tier_label(): "Core" for tier
    0, else the matching suffix) and `devs` (every distinct assignee
    across the milestone's tasks, done ones included, sorted).

    Milestone sort, each layer breaking ties in the one before (donePct
    is measured against in-scope tasks, see _in_scope(); a milestone with
    every task out_of_scope sorts as fully-100%):
      1. partially done (0 < donePct < 100) before fully-0% before stuck
         (milestone_all_blocked(), whatever its donePct) before fully-100%:
         a stuck milestone holds nothing to pick up, so it sorts behind
         every milestone that does and ahead of the finished ones
      2. tier, ascending (Core first)
      3. donePct, descending
      4. milestone id, natural order

    Tier groups (only built when >=1 milestone has tier >= 1; a phase with
    no tiered milestones gets one flat, unwrapped list instead):
      - a tier is "open" once every milestone in every lower tier reads
        `done` (a separate readback of the same tiers-with-unfinished-work
        signal build_stats()'s own cascade already used, kept here because
        this function additionally needs each tier's open/closed flag,
        which milestone_state()'s per-milestone `state` doesn't expose)
      - a group is expanded only when its tier is open AND it contains a
        ready candidate or a claimed in-progress task; a tier that is not
        yet open stays collapsed regardless of what it contains
      - group order: expanded groups first, then groups with any
        not-done milestone, then all-done groups; ties break by tier index
      - each group carries its own `stats` readout (done, inScope,
        donePct, milestonesDone, milestonesTotal), summed from its
        members, the per-tier counterpart of the phase headline
    """
    tasks_by_milestone = {}
    for m in phase.get("milestones", []):
        tasks_by_milestone[m["id"]] = m.get("tasks", [])

    by_id = {m["id"]: m for m in stats["milestones"]}
    enriched = []
    for mid, m in by_id.items():
        # tier comes straight from build_stats(), which already computed it
        # via milestone_tier(); never re-derive it from the name here.
        tier = m["tier"]
        devs = sorted({t.get("assignee") for t in tasks_by_milestone.get(mid, [])
                       if t.get("assignee")})
        enriched.append({**m, "tier": tier,
                         "tierLabel": tier_label(tier),
                         "devs": devs})

    def sort_key(m):
        # donePct already reads 100 for a milestone struck out whole (see
        # _done_pct()), so it sorts with the fully-100% ones unaided.
        pct = m["donePct"]
        # The stuck bucket keys off the state build_stats() settled on,
        # not milestone_all_blocked() directly: milestone_state() lets the
        # tier cascade outrank stuckness, so a Secondary milestone that is
        # blocked while Core still has open work is coloured `deferred`
        # and must sort as deferred too, never behind its 0% siblings.
        if m["state"] == "blocked":
            phase_bucket = 2
        else:
            phase_bucket = 0 if 0 < pct < 100 else (1 if pct == 0 else 3)
        return (phase_bucket, m["tier"], -pct, _milestone_natural_key(m["id"]))

    enriched.sort(key=sort_key)

    if not any(m["tier"] >= 1 for m in enriched):
        return {"tiers": None, "milestones": enriched}

    ready_ids = {c["id"] for c in ready.get("candidates", [])}
    claimed_ids = {c["id"] for c in ready.get("claimed", [])
                   if c.get("display") == IN_PROGRESS}
    active_milestone_ids = set()
    for mid, tasks in tasks_by_milestone.items():
        if any(t["id"] in ready_ids or t["id"] in claimed_ids for t in tasks):
            active_milestone_ids.add(mid)

    tiers_present = sorted({m["tier"] for m in enriched})
    # An empty milestone (state "empty") never blocks its tier's cascade:
    # see the matching note in build_stats(); it is a flagged bug, not
    # unfinished work, so it is excluded here the same way.
    tier_all_done = {t: all(m["state"] in ("done", "empty")
                            for m in enriched if m["tier"] == t)
                     for t in tiers_present}

    def tier_open(t):
        return all(tier_all_done.get(lower, True)
                   for lower in tiers_present if lower < t)

    groups = []
    for t in tiers_present:
        members = [m for m in enriched if m["tier"] == t]
        has_active = any(m["id"] in active_milestone_ids for m in members)
        expanded = tier_open(t) and has_active
        all_done = all(m["state"] == "done" for m in members)
        rank = 0 if expanded else (2 if all_done else 1)
        done = sum(m["done"] for m in members)
        in_scope = sum(m["inScope"] for m in members)
        total = sum(m["total"] for m in members)
        groups.append({
            "tier": t,
            "tierLabel": tier_label(t),
            "expanded": expanded,
            "milestoneIds": [m["id"] for m in members],
            "stats": {
                "done": done,
                "inScope": in_scope,
                "donePct": _done_pct(done, in_scope, total),
                "milestonesDone": sum(1 for m in members
                                      if m["state"] == "done"),
                "milestonesTotal": len(members),
            },
            "_rank": rank,
        })
    groups.sort(key=lambda g: (g["_rank"], g["tier"]))
    for g in groups:
        del g["_rank"]

    return {"tiers": groups, "milestones": enriched}


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
            node = {
                "id": t["id"],
                "kind": "task",
                "milestone": m["id"],
                "status": t.get("status"),
                "description": t.get("description", ""),
                "iterative": bool(t.get("iterative")),
            }
            if is_claimed(t):
                node["started"] = t["started"]
            nodes.append(node)

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
            edge = {"from": sid, "to": mid, "kind": "milestone-complete"}
            if tasks.get(sid, {}).get("softMilestone"):
                edge["soft"] = True
            edges.append(edge)

    return {"phase": phase.get("name"), "nodes": nodes, "edges": edges}


def _mermaid_label(text, reserve=0):
    """Collapse whitespace, cap the length (leaving `reserve` characters for a
    marker appended after) and escape quotes for a Mermaid node label."""
    limit = _LABEL_MAX - reserve
    text = " ".join(str(text).split())
    if len(text) > limit:
        text = text[:limit - 1].rstrip() + "…"
    return text.replace('"', "#quot;")


def _classdef_lines(palette, styles=STATUS_STYLE):
    lines = []
    for cls, st in styles.items():
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


def _live_graph(phase, omit_done=False):
    """The graph mermaid_source() and choose_direction() both draw: full
    build_graph() output plus the same set of node ids to skip (done and
    out_of_scope tasks and the milestones they empty out under omit_done,
    gates left disconnected once those are gone). Kept in one place so the
    two never compute a different notion of "the graph that actually
    renders"."""
    graph = build_graph(phase)
    skipped = set()
    if omit_done:
        milestone_live = {}
        for n in graph["nodes"]:
            if n["kind"] == "task":
                live = n.get("status") not in ("done", "out_of_scope")
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
    live_edges = [e for e in live_edges
                  if e["from"] not in skipped and e["to"] not in skipped]
    return graph, skipped, live_edges


_TIER_NODE_PREFIX = "tier"


def _node_tiers(graph, live_edges):
    """{node id: tier} for every node of a tiered phase, or None when no
    milestone sits in tier >= 1 (an untiered phase draws no subgraph). A
    milestone takes its own tier (milestone_tier()), a task its
    milestone's, and a gate the lowest tier among the nodes it gates: a
    tier's release gate sits with the work it releases, and a gate shared
    across tiers sits with the first of them."""
    tiers = {n["id"]: milestone_tier(n["label"])
             for n in graph["nodes"] if n["kind"] == "milestone"}
    if not any(tiers.values()):
        return None
    for n in graph["nodes"]:
        if n["kind"] == "task":
            tiers[n["id"]] = tiers.get(n["milestone"], 0)
    for n in graph["nodes"]:
        if n["kind"] == "gate":
            gated = [tiers[e["to"]] for e in live_edges
                     if e["from"] == n["id"] and e["to"] in tiers]
            tiers[n["id"]] = min(gated, default=0)
    return tiers


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

    A tiered phase (any milestone in tier >= 1) draws every node inside
    its tier's own subgraph, ascending, each filled by the tier's state
    (TIER_STYLE, tier_states()) and labelled with it, so three tiers never
    read as one undivided mass. An untiered phase emits no subgraph at all
    and its output is unchanged.
    """
    graph, skipped, live_edges = _live_graph(phase, omit_done)
    by_id = {n["id"]: n for n in graph["nodes"]}

    order = {n["id"]: i for i, n in enumerate(graph["nodes"])}
    ids = [n["id"] for n in graph["nodes"] if n["id"] not in skipped]
    topo = _topological_order(ids, order, live_edges)
    topo_idx = {nid: i for i, nid in enumerate(topo)}
    node_tier = _node_tiers(graph, live_edges)

    lines = [f"graph {direction}"]
    lines.extend(_classdef_lines(palette))
    if node_tier:
        lines.extend(_classdef_lines(palette, TIER_STYLE))

    status_members = {}

    def node_line(n):
        if n["kind"] == "milestone":
            return f'\t{n["id"]}["{_mermaid_label(n["id"] + ": " + n["label"])}"]:::mile'
        if n["kind"] == "gate":
            return f'\t{n["id"]}["{_mermaid_label(n["id"] + ": " + n["label"])}"]:::external'
        label = f'{n["id"]}: {n["description"]}'
        if n.get("iterative"):
            label += " ↻"
        status = display_status(n, n.get("status"))
        marker = IN_PROGRESS_MARKER if status == IN_PROGRESS else ""
        label = _mermaid_label(label, reserve=len(marker)) + marker
        cls = STATUS_TO_CLASS.get(status)
        if cls:
            status_members.setdefault(cls, []).append(n["id"])
        return f'\t{n["id"]}["{label}"]'

    tier_members = {}
    if node_tier:
        states = tier_states(build_stats(phase)["milestones"])
        for tier in sorted({node_tier[nid] for nid in topo}):
            state = states.get(tier, "underway")
            lines.append(f'\tsubgraph {_TIER_NODE_PREFIX}{tier}'
                         f'["{tier_label(tier)} · {state}"]')
            lines.extend("\t" + node_line(by_id[nid])
                         for nid in topo if node_tier[nid] == tier)
            lines.append("\tend")
            tier_members.setdefault(TIER_STATE_TO_CLASS[state], []).append(
                f"{_TIER_NODE_PREFIX}{tier}")
    else:
        lines.extend(node_line(by_id[nid]) for nid in topo)

    for e in sorted(live_edges,
                    key=lambda e: (topo_idx.get(e["from"], len(topo)),
                                   topo_idx.get(e["to"], len(topo)))):
        arrow = "-.->" if e.get("soft") else "-->"
        lines.append(f'\t{e["from"]} {arrow} {e["to"]}')

    for cls in ["todo", "inProgress", "blocked", "paused", "deferred", "done",
                "outOfScope"]:
        members = status_members.get(cls)
        if members:
            lines.append(f'\tclass {",".join(sorted(members))} {cls}')
    for cls in TIER_STYLE:
        members = tier_members.get(cls)
        if members:
            lines.append(f'\tclass {",".join(members)} {cls}')

    return "\n".join(lines)


# Estimated on-screen footprint of one Mermaid node in the roadmap artefact's
# diagram shell (IBM Plex Mono 16px, up to _LABEL_MAX-ish characters wrapped
# by mermaid, plus its padding) and the gap the layout engine leaves between
# ranks/nodes. Rough by nature: real layout depends on label length, mermaid
# version and the chosen layout engine (elk vs dagre), so this only needs to
# be in the right ballpark to pick a direction, not to predict exact pixels.
_NODE_WIDTH, _NODE_HEIGHT = 220, 70
_RANK_GAP, _NODE_GAP = 60, 20


def _longest_path_layers(ids, edges):
    """Assign every node the longest-path layer: 0 for a source, otherwise
    one more than the deepest of its predecessors. This is the layering a
    layered graph-drawing algorithm (dagre/elk, sugiyama-style) would use
    for rank assignment, so it is a reasonable proxy for how many ranks the
    real render will need: good enough to pick TD vs LR by, not a promise
    that mermaid's own engine ranks identically."""
    preds = {i: [] for i in ids}
    idset = set(ids)
    for e in edges:
        if e["from"] in idset and e["to"] in idset:
            preds[e["to"]].append(e["from"])
    layer = {}

    def depth(nid, seen):
        if nid in layer:
            return layer[nid]
        if nid in seen or not preds[nid]:
            layer[nid] = 0
            return 0
        seen = seen | {nid}
        layer[nid] = 1 + max((depth(p, seen) for p in preds[nid]), default=-1)
        return layer[nid]

    for nid in ids:
        depth(nid, set())
    return layer


def choose_direction(phase):
    """`TD` or `LR` for the phase's dependency graph, picked deterministically
    from the same live nodes/edges mermaid_source(omit_done=True) draws (see
    roadmap-conventions.md).

    Width-only fit: the diagram shell (`.mermaid-wrap` in the template) has
    no height cap, the SVG renders at natural size and the page simply
    scrolls past a tall diagram, but its width is bounded by the layout
    column (measured against the real template, not estimated). So the
    only real trade-off between directions is which one needs less
    horizontal zoom-out, not a two-axis "which box fits better" guess.

    Layers the live graph by longest path (_longest_path_layers): L layers,
    widest layer W nodes. TD's width is W nodes side by side (node gap
    between them); LR's width is L ranks laid out left to right (rank gap
    between them). Whichever is narrower wins; a tie keeps TD, today's
    fixed default, so an untiered/trivial phase's diagram never changes
    shape from a coin flip.
    """
    graph, skipped, live_edges = _live_graph(phase, omit_done=True)
    ids = [n["id"] for n in graph["nodes"] if n["id"] not in skipped]
    if not ids:
        return "TD"
    layer = _longest_path_layers(ids, live_edges)
    layer_counts = {}
    for nid in ids:
        layer_counts[layer[nid]] = layer_counts.get(layer[nid], 0) + 1
    num_layers = max(layer.values(), default=0) + 1
    widest = max(layer_counts.values(), default=1)

    # TD: siblings within the widest layer sit side by side (node gap).
    td_w = widest * _NODE_WIDTH + max(widest - 1, 0) * _NODE_GAP
    # LR: ranks run left to right (rank gap between them).
    lr_w = num_layers * _NODE_WIDTH + max(num_layers - 1, 0) * _RANK_GAP

    return "LR" if lr_w < td_w else "TD"


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
def resolve_within(phase, milestones=None, tiers=None):
    """The milestone ids a `--milestones` / `--tiers` filter selects, or None
    for the whole phase. `milestones` is a list of ids (`M2`); `tiers` is a
    list of tier words (`core`, `secondary`, …) or the single word `focus`,
    the one tier `tier_states()` calls underway. The two are mutually
    exclusive. Raises RoadmapError on an unknown id or tier, on both being
    given, and on `focus` when no tier is underway."""
    if milestones and tiers:
        raise RoadmapError("milestones and tiers are mutually exclusive")
    entries = build_stats(phase)["milestones"]
    if milestones:
        known = {m["id"].lower(): m["id"] for m in entries}
        unknown = [m for m in milestones if m.lower() not in known]
        if unknown:
            raise RoadmapError(
                f"unknown milestone(s) {', '.join(unknown)}; "
                f"{phase.get('name')} has {', '.join(m['id'] for m in entries)}")
        return {known[m.lower()] for m in milestones}
    if not tiers:
        return None
    states = tier_states(entries)
    words = {tier_label(t).lower(): t for t in states}
    if [t.lower() for t in tiers] == ["focus"]:
        underway = [t for t, state in states.items() if state == "underway"]
        if not underway:
            raise RoadmapError(f"no tier is underway in {phase.get('name')}")
        wanted = set(underway)
    else:
        unknown = [t for t in tiers if t.lower() not in words]
        if unknown:
            raise RoadmapError(
                f"unknown tier(s) {', '.join(unknown)}; "
                f"{phase.get('name')} has {', '.join(sorted(words, key=words.get))}")
        wanted = {words[t.lower()] for t in tiers}
    return {m["id"] for m in entries if m["tier"] in wanted}


def build_ready(phase, within=None, horizon="ready"):
    """Actionable candidates: unclaimed tasks whose effective status is todo,
    annotated with ordering signals so a small model can choose between valid
    options instead of deriving them. Claimed tasks are listed apart under
    `claimed` (someone is already on them), oldest claim first.

    `within` (a set of milestone ids from resolve_within) narrows both lists
    to those milestones. `horizon="open"` widens the candidates to every task
    not done or out of scope, claimed ones included (each carries `status`,
    `display` and `started`), and leaves `claimed` empty."""
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
    milestone_tier_of = {m["id"]: m["tier"] for m in stats["milestones"]}
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
    claimed = []
    for tid, t in tasks.items():
        mid = task_milestone.get(tid)
        if within is not None and mid not in within:
            continue
        tier = milestone_tier_of.get(mid, 0)
        is_open = effective.get(tid) not in ("done", "out_of_scope")
        if horizon == "ready" and is_claimed(t) and is_open:
            claimed.append({
                "id": tid,
                "description": t.get("description", ""),
                "milestone": mid,
                "milestoneName": milestone_name.get(mid, ""),
                "tier": tier,
                "tierLabel": tier_label(tier),
                "status": effective.get(tid),
                "display": display_status(t, effective.get(tid)),
                "started": t["started"],
                "assignee": t.get("assignee", ""),
            })
            continue
        if horizon == "open":
            if not is_open:
                continue
        elif effective.get(tid) != "todo":
            continue
        candidates.append({
            "id": tid,
            "description": t.get("description", ""),
            "milestone": mid,
            "milestoneName": milestone_name.get(mid, ""),
            "tier": tier,
            "tierLabel": tier_label(tier),
            "status": effective.get(tid),
            "display": display_status(t, effective.get(tid)),
            "started": t.get("started", ""),
            "milestoneDonePct": milestone_pct.get(mid, 0),
            "directDependents": len(dependents.get(tid, ())),
            "transitiveUnblocks": len(transitive(tid)),
            "isMilestoneSink": (tid in sinks.get(mid, [])
                                and not t.get("softMilestone")),
            "notes": t.get("notes", ""),
            "assignee": t.get("assignee", ""),
        })
    candidates.sort(key=lambda c: (-c["transitiveUnblocks"],
                                   -c["milestoneDonePct"], c["id"]))
    claimed.sort(key=lambda c: (c["started"], c["id"]))
    return {"phase": phase.get("name"), "candidates": candidates,
            "claimed": claimed}


def _truncate_notes(candidates, limit=200):
    """Cap each candidate's notes field for the --json path.

    build_ready() carries full notes prose because _render_to() reuses the
    same shape for the HTML dashboard, where the full history is the point.
    The AI-consumed --json path only needs enough to justify a pick — Step 1
    of task-suggest reasons over transitiveUnblocks/isMilestoneSink/
    milestoneDonePct, not notes prose — so truncate here rather than at the
    source and regress the dashboard.
    """
    out = []
    for c in candidates:
        c = dict(c)
        notes = c.get("notes", "")
        if len(notes) > limit:
            c["notes"] = notes[:limit].rsplit(" ", 1)[0] + "…"
        out.append(c)
    return out


def ready_groups(candidates):
    """Candidate ids keyed by milestone, by topic and by dev, for the
    --json path.

    next-task-group prints one table per group. Left to count for itself, a
    model drops rows and still reports a full total, so the membership of
    every table is fixed here instead. The topic is the letters between the
    milestone number and the sequence in a task id (`2TI.3` -> `TI`); an id
    that does not fit that shape lands under `other`. The dev key is the
    trimmed `assignee`, or `unassigned` when empty. Groups come out in
    display order (milestones by number, topics alphabetically, devs
    case-insensitive alphabetical with `unassigned` last); ids inside a
    group keep the order of `candidates`.
    """
    by_milestone, by_topic, by_dev = {}, {}, {}
    for c in candidates:
        by_milestone.setdefault(c.get("milestone") or "none", []).append(c["id"])
        match = re.match(r"\d+([A-Za-z]+)\.", c["id"])
        by_topic.setdefault(match.group(1) if match else "other", []).append(c["id"])
        dev = (c.get("assignee") or "").strip() or "unassigned"
        by_dev.setdefault(dev, []).append(c["id"])
    def natural(key):
        return [int(part) if part.isdigit() else part
                for part in re.split(r"(\d+)", key)]
    def dev_key(key):
        return (1, "") if key == "unassigned" else (0, key.lower())

    return {"milestone": {k: by_milestone[k] for k in sorted(by_milestone, key=natural)},
            "topic": {k: by_topic[k] for k in sorted(by_topic)},
            "dev": {k: by_dev[k] for k in sorted(by_dev, key=dev_key)}}


def _csv(value):
    """`M2, M4` -> ['M2', 'M4']; None or empty -> None."""
    items = [v.strip() for v in (value or "").split(",") if v.strip()]
    return items or None


def cmd_ready(args, horizon="ready") -> int:
    try:
        _path, data = load(args.path)
        phase = active_phase(data, args.phase)
        within = resolve_within(phase, _csv(args.milestones), _csv(args.tiers))
        ready = build_ready(phase, within=within, horizon=horizon)
    except RoadmapError as exc:
        print(f"✗ {exc}")
        return 2
    if args.json:
        ready = {**ready, "candidates": _truncate_notes(ready["candidates"]),
                 "groups": ready_groups(ready["candidates"])}
        print(json.dumps(ready, indent="\t"))
        return 0
    noun = "open" if horizon == "open" else "unblocked"
    if not ready["candidates"]:
        print(f"{ready['phase']}: no {noun} tasks.")
        _print_claimed(ready["claimed"])
        return 0
    print(f"{ready['phase']}: {len(ready['candidates'])} {noun} task(s), "
          "highest leverage first")
    for c in ready["candidates"]:
        sink = "  [completes milestone]" if c["isMilestoneSink"] else ""
        who = f"  ({c['assignee']})" if c.get("assignee") else ""
        print(f"  {c['id']:8} unblocks {c['transitiveUnblocks']:<3} "
              f"{c['milestone']} {c['milestoneDonePct']}% done{sink}{who}")
        print(f"           {c['description']}")
    _print_claimed(ready["claimed"])
    return 0


def _print_claimed(claimed):
    if not claimed:
        return
    print(f"claimed: {len(claimed)} task(s)")
    for c in claimed:
        who = f" by {c['assignee']}" if c.get("assignee") else ""
        blocked = "" if c["status"] == "todo" else f" ({c['status']})"
        print(f"  {c['id']:8} since {c['started']}{who}{blocked}")


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


def _project_name(json_path, phase):
    """Optional `project` field on the phase, falling back to the project
    root directory name. See roadmap-conventions.md for the field."""
    explicit = phase.get("project")
    if explicit:
        return explicit
    return project_root(json_path).name


def _dep_kinds(phase):
    """{id: kind} for every task/milestone/gate id, so the artefact can
    colour a dependency chip by what it points at (task status colour,
    milestone sky, gate yellow) without re-deriving the graph in JS."""
    tasks, milestones, gates = build_index(phase)
    kinds = {}
    for tid, t in tasks.items():
        kinds[tid] = {"kind": "task", "status": t.get("status"),
                      "display": display_status(t, t.get("status"))}
    for mid in milestones:
        kinds[mid] = {"kind": "milestone"}
    for gid in gates:
        kinds[gid] = {"kind": "gate"}
    return kinds


def _render_to(json_path, data, phase, out):
    template = _template_path()
    if not template.exists():
        raise RoadmapError(f"render template missing at {template}")
    tasks = []
    assignees = set()
    for m in phase.get("milestones", []):
        for t in m.get("tasks", []):
            assignee = t.get("assignee", "")
            if assignee:
                assignees.add(assignee)
            tasks.append({
                "id": t["id"],
                "description": t.get("description", ""),
                "status": t.get("status"),
                "display": display_status(t, t.get("status")),
                "dependsOn": t.get("dependsOn", []),
                "milestone": m["id"],
                "notes": t.get("notes", ""),
                "assignee": assignee,
                "started": t.get("started", ""),
            })
    stats = build_stats(phase)
    ready = build_ready(phase)
    direction = choose_direction(phase)
    blob = {
        "project": _project_name(json_path, phase),
        "phase": phase.get("name"),
        "generated": datetime.now().isoformat(timespec="seconds"),
        "stats": stats,
        "overview": overview_layout(phase, stats, ready),
        "tasks": tasks,
        "ready": ready,
        "mermaid": mermaid_source(phase, direction=direction,
                                  omit_done=True, palette="vars"),
        "graphDirection": direction,
        "validation": _validate_phase(phase),
        "devColours": {a: dev_colour(a) for a in sorted(assignees)},
        "depKinds": _dep_kinds(phase),
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
# claim / release / end
# ---------------------------------------------------------------------------
TASK_FIELD_ORDER = ["id", "description", "status", "dependsOn",
                    "softDependsOn", "softMilestone", "iterative", "notes",
                    "assignee", "started", "ended", "pr"]


def _set_task_field(task, key, value):
    """Set `key` in place, or insert it where the canonical field order puts
    it, leaving every other field exactly where it already is."""
    if key in task:
        task[key] = value
        return
    rank = TASK_FIELD_ORDER.index(key)
    items = list(task.items())
    at = len(items)
    for i, (k, _v) in enumerate(items):
        if k in TASK_FIELD_ORDER and TASK_FIELD_ORDER.index(k) > rank:
            at = i
            break
    items.insert(at, (key, value))
    task.clear()
    task.update(items)


def _load_for_write(args):
    """(path, data, index, exit code or None) for claim and release, refusing
    what recompute refuses before it writes. `index` is build_index()'s
    (tasks, milestones, gates); its task dicts are the ones inside `data`, so
    editing one edits what gets written."""
    try:
        path, data = load(args.path)
        phase = active_phase(data, args.phase)
    except RoadmapError as exc:
        print(f"✗ {exc}")
        return None, None, None, 2
    if _canonical_text(data) != path.read_text() and not args.reformat:
        print("✗ roadmaps.json is not in canonical form (tab-indented, "
              "ensure_ascii off, trailing newline); a write would reformat "
              "the whole file. Re-run with --reformat to accept that.")
        return None, None, None, 1
    index = build_index(phase)
    if args.id not in index[0]:
        print(f"✗ no task {args.id!r} in '{phase.get('name')}'")
        return None, None, None, 1
    return path, data, index, None


def cmd_claim(args) -> int:
    path, data, index, code = _load_for_write(args)
    if code is not None:
        return code
    tasks, milestones, gates = index
    task = tasks[args.id]
    cycles = find_cycles(tasks, milestones)
    if cycles:
        print("✗ cycle detected; refusing to claim until it is resolved:")
        for cycle in cycles:
            print("  - " + " -> ".join(cycle))
        return 1
    if is_claimed(task):
        who = f" by {task['assignee']}" if task.get("assignee") else ""
        print(f"✗ {args.id} is already claimed{who} (started {task['started']})")
        return 1
    computed = recompute_all(tasks, milestones, gates)
    effective = task.get("status") if is_held(task) else computed.get(args.id)
    if effective != "todo":
        print(f"✗ {args.id} is {effective}, not todo: only a task that is ready "
              "to start can be claimed")
        return 1
    started = args.date or date.today().isoformat()
    if not _is_iso_date(started):
        print(f"✗ --date {started!r} is not a YYYY-MM-DD date")
        return 1
    if args.assignee is not None:
        name = args.assignee.strip()
        current = task.get("assignee", "")
        if not name:
            print("✗ --assignee needs a name")
            return 1
        if current and current.strip().lower() != name.lower() and not args.reassign:
            print(f"✗ {args.id} is assigned to {current}; pass --reassign to "
                  f"hand it to {name}")
            return 1
        if not current or current.strip().lower() != name.lower():
            _set_task_field(task, "assignee", name)
    _set_task_field(task, "started", started)
    _atomic_write(path, _canonical_text(data))
    who = f", assignee {task['assignee']}" if task.get("assignee") else ""
    print(f"✓ claimed {args.id} (started {started}{who})")
    return 0


def cmd_release(args) -> int:
    path, data, index, code = _load_for_write(args)
    if code is not None:
        return code
    task = index[0][args.id]
    if not is_claimed(task):
        print(f"✗ {args.id} is not claimed")
        return 1
    del task["started"]
    if args.unassign:
        task.pop("assignee", None)
    _atomic_write(path, _canonical_text(data))
    print(f"✓ released {args.id}" + (" and cleared its assignee" if args.unassign else ""))
    return 0


def cmd_end(args) -> int:
    path, data, index, code = _load_for_write(args)
    if code is not None:
        return code
    task = index[0][args.id]
    if task.get("status") != "done":
        print(f"✗ {args.id} is {task.get('status')}, not done: only finished "
              "work gets an end date")
        return 1
    if task.get("ended") and not args.force:
        print(f"✗ {args.id} already ended {task['ended']}; pass --force to "
              "overwrite it")
        return 1
    ended = args.date or date.today().isoformat()
    if not _is_iso_date(ended):
        print(f"✗ --date {ended!r} is not a YYYY-MM-DD date")
        return 1
    if _is_iso_date(task.get("started")) and ended < task["started"]:
        print(f"✗ --date {ended} is before {args.id} started {task['started']}")
        return 1
    _set_task_field(task, "ended", ended)
    _atomic_write(path, _canonical_text(data))
    print(f"✓ ended {args.id} ({ended})")
    return 0


def cmd_stamp_ended(args) -> int:
    """Stamp `ended` on the done tasks a branch finished: those that were not
    done at its merge-base with --base, plus those whose `pr` is --pr. A task
    that already has `ended` is never touched."""
    try:
        path, data = load(args.path)
        phase = active_phase(data, args.phase)
    except RoadmapError as exc:
        print(f"✗ {exc}")
        return 2
    if _canonical_text(data) != path.read_text() and not args.reformat:
        print("✗ roadmaps.json is not in canonical form; re-run with "
              "--reformat to accept a whole-file rewrite.")
        return 1
    ended = args.date or date.today().isoformat()
    if not _is_iso_date(ended):
        print(f"✗ --date {ended!r} is not a YYYY-MM-DD date")
        return 1
    git, rel = _git_at_toplevel(path)
    if git is None:
        print("✗ roadmaps.json is not inside a git repository")
        return 1
    base = (git("merge-base", "HEAD", args.base) or "").strip()
    if not base:
        print(f"✗ no merge-base between HEAD and {args.base}")
        return 1
    before = _phase_statuses(git("show", f"{base}:{rel}") or "", phase.get("name"))
    if before is None:
        print(f"✗ cannot read phase {phase.get('name')!r} at the merge-base "
              f"({base[:8]}): the file is missing or unparseable there, or the "
              "phase was renamed; stamp tasks with `end ID` or run "
              "`backfill-ended`")
        return 1
    tasks = build_index(phase)[0]
    chosen = []
    for tid, task in tasks.items():
        if task.get("status") != "done" or task.get("ended"):
            continue
        finished_here = before.get(tid) not in ("done", "out_of_scope")
        if finished_here or (args.pr is not None and task.get("pr") == args.pr):
            if _is_iso_date(task.get("started")) and ended < task["started"]:
                continue
            chosen.append(tid)
    if not args.dry_run:
        for tid in chosen:
            _set_task_field(tasks[tid], "ended", ended)
        if chosen:
            _atomic_write(path, _canonical_text(data))
    if args.json:
        print(json.dumps({"phase": phase.get("name"), "ended": ended,
                          "written": not args.dry_run and bool(chosen),
                          "tasks": chosen}))
        return 0
    verb = "would end" if args.dry_run else "ended"
    print(f"{phase.get('name')}: {verb} {len(chosen)} task(s) on {ended}"
          + (": " + ", ".join(chosen) if chosen else ""))
    return 0


def ended_from_history(versions, today):
    """{task id: (date, sha, basis)} for every task done in the last version.

    `versions` is the roadmap's history oldest first, each a (sha, date,
    {id: status}) triple. A task's end date is the date of the version where
    it last became done: a later reopen resets the clock, and a task that was
    done before it ever reached git is dated by the first version showing it
    (basis `first-seen`). A task done in the final version only because of
    working-tree edits (the sha is empty) is dated `today` (basis
    `uncommitted`). Otherwise the basis is `transition`."""
    became = {}
    seen = set()
    for sha, when, statuses in versions:
        for tid, status in statuses.items():
            if status != "done":
                became.pop(tid, None)
            elif tid not in became:
                basis = ("uncommitted" if not sha
                         else "transition" if tid in seen else "first-seen")
                became[tid] = (when or today, sha, basis)
        seen.update(statuses)
    final = versions[-1][2] if versions else {}
    return {tid: found for tid, found in became.items()
            if final.get(tid) == "done"}


def _phase_statuses(text, phase_name):
    """{task id: status} for the phase named `phase_name` in roadmaps.json
    `text`, or None when the text does not parse or has no such phase."""
    try:
        loaded = json.loads(text)
    except ValueError:
        return None
    for ph in (loaded if isinstance(loaded, list) else [loaded]):
        if isinstance(ph, dict) and ph.get("name") == phase_name:
            return {t["id"]: t.get("status")
                    for m in ph.get("milestones", [])
                    for t in m.get("tasks", []) if "id" in t}
    return None


def _git_at_toplevel(path):
    """(git, rel): a runner for git commands from the repository root that
    holds `path` (stdout, or None on failure), and `path` relative to that
    root. (None, None) when `path` is not in a git repository."""
    import subprocess
    top_dir = [path.parent]

    def git(*argv):
        done = subprocess.run(["git", "-C", str(top_dir[0]), *argv],
                              capture_output=True, text=True)
        return done.stdout if done.returncode == 0 else None

    top = git("rev-parse", "--show-toplevel")
    if top is None:
        return None, None
    top_dir[0] = Path(top.strip())
    return git, path.resolve().relative_to(top_dir[0].resolve()).as_posix()


def _roadmap_versions(path, phase_name):
    """Oldest-first (sha, date, {id: status}) history of one phase from git,
    ending with the working-tree file as ("", "", ...). None when the file
    is not in a git repository."""
    git, rel = _git_at_toplevel(path)
    if git is None:
        return None

    versions = []
    log = git("log", "--first-parent", "--reverse", "--format=%H %cs", "--", rel)
    for line in (log or "").splitlines():
        sha, when = line.split()
        found = _phase_statuses(git("show", f"{sha}:{rel}") or "", phase_name)
        if found is not None:
            versions.append((sha, when, found))
    current = _phase_statuses(path.read_text(), phase_name)
    if current is not None:
        if versions and versions[-1][2] == current:
            return versions
        versions.append(("", "", current))
    return versions


def cmd_backfill_ended(args) -> int:
    try:
        path, data = load(args.path)
        phase = active_phase(data, args.phase)
    except RoadmapError as exc:
        print(f"✗ {exc}")
        return 2
    if _canonical_text(data) != path.read_text() and not args.reformat:
        print("✗ roadmaps.json is not in canonical form; re-run with "
              "--reformat to accept a whole-file rewrite.")
        return 1
    versions = _roadmap_versions(path, phase.get("name"))
    if versions is None:
        print("✗ roadmaps.json is not inside a git repository; there is no "
              "history to read dates from")
        return 1
    found = ended_from_history(versions, date.today().isoformat())
    tasks = build_index(phase)[0]
    rows, skipped = [], []
    for tid, task in tasks.items():
        if task.get("status") != "done" or task.get("ended") or tid not in found:
            continue
        when, sha, basis = found[tid]
        row = {"id": tid, "ended": when, "commit": sha[:7], "basis": basis}
        if _is_iso_date(task.get("started")) and when < task["started"]:
            skipped.append({**row, "started": task["started"]})
            continue
        rows.append(row)
    if not args.dry_run:
        for row in rows:
            _set_task_field(tasks[row["id"]], "ended", row["ended"])
        if rows:
            _atomic_write(path, _canonical_text(data))
    if args.json:
        print(json.dumps({"phase": phase.get("name"), "written": not args.dry_run,
                          "tasks": rows, "skipped": skipped}, indent="\t"))
        return 0
    verb = "would set" if args.dry_run else "set"
    if not rows and not skipped:
        print(f"{phase.get('name')}: every done task already has an end date.")
        return 0
    print(f"{phase.get('name')}: {verb} ended on {len(rows)} task(s)")
    for row in rows:
        note = f" [{row['basis']}]" if row["basis"] != "transition" else ""
        where = f" ({row['commit']})" if row["commit"] else ""
        print(f"  {row['id']:8} {row['ended']}{where}{note}")
    for row in skipped:
        where = f" ({row['commit']})" if row["commit"] else ""
        print(f"  {row['id']:8} {row['ended']}{where} "
              f"[skipped: before started {row['started']}]")
    return 0


def cmd_hook(args) -> int:
    """Claude Code hook entry point. A hook must never fail the session, so
    every error is swallowed and the exit code is always 0."""
    try:
        import _roadmap_hooks
        _roadmap_hooks.run(args.event, sys.stdin, Path(__file__).resolve(),
                           build_ready)
    except Exception:  # noqa: BLE001 - a hook must never break the session
        pass
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
                    help="drop done and out_of_scope tasks and the milestones "
                         "they empty")
    sp.add_argument("--palette", choices=["light", "dark", "vars"],
                    default="light",
                    help="literal light/dark hexes, or CSS custom properties")

    def within_flags(sp):
        sp.add_argument("--json", action="store_true")
        group = sp.add_mutually_exclusive_group()
        group.add_argument("--milestones", default=None,
                           help="comma-separated milestone ids, e.g. M2,M4")
        group.add_argument("--tiers", default=None,
                           help="comma-separated tiers (core,secondary,…) "
                                "or `focus` for the tier now underway")
        return sp

    within_flags(common(sub.add_parser(
        "ready", help="actionable todo candidates")))
    within_flags(common(sub.add_parser(
        "open", help="every task not done or out of scope")))

    sp = common(sub.add_parser("render", help="write the HTML artefact"))
    sp.add_argument("--out", default=None, help="output path override")

    def claim_common(sp):
        # the task id comes first so `claim 2RT.17 path` never reads the id
        # as the path
        sp.add_argument("id", help="task id")
        common(sp)
        sp.add_argument("--reformat", action="store_true",
                        help="allow rewriting a non-canonically-formatted file")
        return sp

    sp = claim_common(sub.add_parser(
        "claim", help="record that someone has started a task"))
    sp.add_argument("--assignee", default=None,
                    help="who is doing it (asked for, never inferred)")
    sp.add_argument("--reassign", action="store_true",
                    help="allow --assignee to replace a different assignee")
    sp.add_argument("--date", default=None,
                    help="start date YYYY-MM-DD (default today)")

    sp = claim_common(sub.add_parser(
        "end", help="record the date a done task finished"))
    sp.add_argument("--date", default=None,
                    help="end date YYYY-MM-DD (default today)")
    sp.add_argument("--force", action="store_true",
                    help="overwrite an existing end date")

    sp = common(sub.add_parser(
        "backfill-ended",
        help="date done tasks that lack `ended` from git history"))
    sp.add_argument("--dry-run", action="store_true", help="preview, no write")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--reformat", action="store_true",
                    help="allow rewriting a non-canonically-formatted file")

    sp = common(sub.add_parser(
        "stamp-ended",
        help="date the done tasks a branch finished, before it merges"))
    sp.add_argument("--base", default="origin/main",
                    help="ref to take the merge-base with (default origin/main)")
    sp.add_argument("--pr", type=int, default=None,
                    help="also stamp done tasks whose `pr` is this number")
    sp.add_argument("--date", default=None,
                    help="end date YYYY-MM-DD (default today)")
    sp.add_argument("--dry-run", action="store_true", help="preview, no write")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--reformat", action="store_true",
                    help="allow rewriting a non-canonically-formatted file")

    sp = claim_common(sub.add_parser("release", help="drop a claim"))
    sp.add_argument("--unassign", action="store_true",
                    help="also clear the assignee")

    sp = sub.add_parser("hook", help="Claude Code hook entry point")
    sp.add_argument("event", choices=["session-start", "post-tool-use"])

    args = parser.parse_args(argv)
    return {
        "detect": cmd_detect,
        "validate": cmd_validate,
        "recompute": cmd_recompute,
        "stats": cmd_stats,
        "graph": cmd_graph,
        "ready": cmd_ready,
        "open": lambda a: cmd_ready(a, horizon="open"),
        "render": cmd_render,
        "claim": cmd_claim,
        "release": cmd_release,
        "end": cmd_end,
        "backfill-ended": cmd_backfill_ended,
        "stamp-ended": cmd_stamp_ended,
        "hook": cmd_hook,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
