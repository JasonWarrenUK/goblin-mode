#!/usr/bin/env python3
"""roadbook.py — single CLI for goblin-scout's rich phase-array roadbook.

Replaces the former five sibling scripts (detect_format, validate_roadbook,
recompute_roadbook, roadbook_stats, roadbook_graph) with one entry point and a
shared argument parser. Graph logic lives in _roadbook_core.py; this file owns
presentation (Mermaid, HTML render) and the subcommand plumbing.

Usage: roadbook.py SUBCOMMAND [PATH] [--phase NAME] [flags]

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
  render     deterministic HTML chart from template      [--out PATH]
  config     KEY VALUE: set a per-phase option; `artefact` is where render
             writes the dashboard, relative to the project root
                                                        [--clear --reformat]
  claim      ID: record that someone has started a task [--assignee NAME
                                                         --reassign --date]
  assign     ID: set or clear an assignee, no claim     [--assignee NAME
                                                         | --unassign]
  release    ID: drop a claim                           [--unassign]
  end        ID: record when a done task finished       [--date --force]
  backfill-ended  date done tasks lacking `ended` from git history
                                                        [--dry-run --json]
  stamp-ended date the done tasks a branch finished     [--base --pr --date
                                                         --dry-run --json]
  pull       refresh a phase mirrored from Jira, read-only: Jira's tasks are
             rewritten, tasks marked local are left alone
                                                        [--project KEY --name
                                                         --issues FILE
                                                         --allow-removals --dry-run]
  hook       EVENT: Claude Code hook entry point (session-start,
             post-tool-use); reads the hook JSON on stdin, always exits 0

PATH is optional everywhere (after ID for claim and release); without it the
roadbook is located by walking up from the cwd. --phase selects one phase by
name when several are active (without it, multiple active phases are an
error — never a silent guess).

All subcommands exit 2 when the roadbook cannot be located or parsed.
Requires Python 3.8+, stdlib only. British spelling throughout.
"""
from __future__ import annotations

import argparse
import copy
import heapq
import json
import os
import re
import sys
import tempfile
import zlib
from datetime import date, datetime
from pathlib import Path

from _roadbook_core import (
    IMPOSABLE_STATUSES,
    IN_PROGRESS,
    PLUGIN_VERSION,
    SOURCE_KEY,
    SOURCE_KINDS,
    STAMP_KEY,
    VALID_STATUSES,
    RoadbookError,
    active_phase,
    build_index,
    display_status,
    find_cycles,
    is_claimed,
    LEGACY_LOCAL_ROADBOOK_NAME,
    LEGACY_NAMES,
    LEGACY_ROADBOOK_NAME,
    LOCAL_NAMES,
    LOCAL_ROADBOOK_NAME,
    ROADBOOK_NAME,
    is_held,
    is_mirrored,
    _phases,
    load,
    milestone_sinks,
    named_phase,
    newer_than_running,
    phase_source,
    recompute_all,
    resolve_roadbook_path,
    stamp_for,
    unmet_blockers,
)

# ---------------------------------------------------------------------------
# Canonical status→colour table, derived from the goblin theme
# (templates/chart-theme.css, copied from .claude/themes/goblin-html.json).
# Every colour is a theme token or a mix of two, written beside it as
# mix(a, b, t): t of token a over token b in sRGB; test_roadbook.py's
# StatusDerivation recomputes each one from the copied CSS, so the table
# cannot drift from the theme. The single source of truth for every
# projection: PHASE.md Mermaid (literal hexes: GitHub cannot resolve CSS
# vars), the chart template (semantic vars, carried in its <style>) and the
# conventions reference at references/roadbook-conventions.md, which
# documents it in prose. Semantics, as Jason approved them on 2026-11-18:
# done moss (ok), todo faded ink, inProgress ballpoint (info; a waypoint on
# a trail, a display class and never a stored status), blocked rust
# (danger), paused beetroot (accent), deferred ochre (warn), out_of_scope
# ink half into line, dotted, milestone the exhibit panel (dark fill, pale
# ink), gate the slime highlighter. Light fills are 8% washes over the
# pale slip, dark ones 8% over the dark sheet. A node's label is its `text`
# colour, which is its stroke except where the node is inverted (milestone,
# gate). Every text/fill pair clears AA (4.5:1) in light and dark.
# ---------------------------------------------------------------------------
STATUS_STYLE = {
    "todo": {  # stroke ink-muted; fill mix(ink-muted, slip, .04) / mix(ink-muted, surface, .04)
        "var": "todo", "bg": "#f5f6f0", "stroke": "#4b5a3c", "text": "#4b5a3c",
        "darkBg": "#272b1f", "darkStroke": "#a3ad8c", "darkText": "#a3ad8c", "extra": "",
    },
    "inProgress": {  # info; fill mix(info, slip, .08) / mix(info, surface, .08)
        "var": "in-progress", "bg": "#ebefef", "stroke": "#2d5a8c", "text": "#2d5a8c",
        "darkBg": "#2b312a", "darkStroke": "#8db4e8", "darkText": "#8db4e8", "extra": "",
    },
    "blocked": {  # danger; fill mix(danger, slip, .08) / mix(danger, surface, .08)
        "var": "blocked", "bg": "#f5ece7", "stroke": "#a3361f", "text": "#a3361f",
        "darkBg": "#342e20", "darkStroke": "#ff8a6b", "darkText": "#ff8a6b",
        "extra": "stroke-width:2px",
    },
    "paused": {  # accent; fill mix(accent, slip, .08) / mix(accent, surface, .08)
        "var": "paused", "bg": "#f3eaea", "stroke": "#8c1d4c", "text": "#8c1d4c",
        "darkBg": "#342e26", "darkStroke": "#ff86b4", "darkText": "#ff86b4",
        "extra": "stroke-dasharray:4 3",
    },
    "deferred": {  # warn; fill mix(warn, slip, .08) / mix(warn, surface, .08)
        "var": "deferred", "bg": "#f3efe4", "stroke": "#8a5a00", "text": "#8a5a00",
        "darkBg": "#31301e", "darkStroke": "#e0a84a", "darkText": "#e0a84a",
        "extra": "stroke-dasharray:2 4,font-style:italic",
    },
    "done": {  # ok; fill mix(ok, slip, .08) / mix(ok, surface, .08)
        "var": "done", "bg": "#edf0e6", "stroke": "#3c6a1c", "text": "#3c6a1c",
        "darkBg": "#2d3420", "darkStroke": "#a6d46a", "darkText": "#a6d46a", "extra": "",
    },
    # Ink half into line: the faintest ink that still clears 4.5:1 on its own
    # fill and 3:1 on both tier backgrounds. Close to todo's faded ink, so the
    # dotted border (and the struck label in waypoint lists) tells them apart.
    "outOfScope": {  # stroke mix(ink, line, .5); fill slip / surface
        "var": "out-of-scope", "bg": "#fcfcf8", "stroke": "#686e57", "text": "#686e57",
        "darkBg": "#22261a", "darkStroke": "#969d82", "darkText": "#969d82",
        "extra": "stroke-dasharray:2 2",
    },
    "mile": {  # fill exhibit, text exhibit-ink; stroke exhibit / exhibit-ink
        "var": "milestone", "bg": "#1d2718", "stroke": "#1d2718", "text": "#e7e9cf",
        "darkBg": "#0a0c07", "darkStroke": "#e3e8cc", "darkText": "#e3e8cc",
        "extra": "font-weight:bold",
    },
    # Solid slime sits at a tier background's own luminance in light, so the
    # light gate is a pale slime wash with an ink border; dark keeps it solid.
    "external": {  # light fill mix(slime, slip, .28), ink; dark fill slime, on-slime
        "var": "gate", "bg": "#e9f1c0", "stroke": "#1d2718", "text": "#1d2718",
        "darkBg": "#c5e13e", "darkStroke": "#c5e13e", "darkText": "#1d2718",
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
# name, same shape as STATUS_STYLE, and derived from the theme the same way.
# Two backgrounds, chosen by the tier's state (tier_states()): the raised
# sheet for a tier that is underway, cardboard with a dashed border for one
# still deferred behind a lower tier. Neither is a node colour. Both sit
# between the near-white node fills (near-black in dark) and the strokes
# that carry the hue. Gates every pair must clear, in light and dark alike
# (test_roadbook.py's TierStyle enforces them):
#   - 3:1 or better against every node stroke and the diagram's edge line
#   - 1.35:1 or better against every node fill
#   - 4.5:1 or better for the tier's own label (its stroke colour)
# The dashed border and the state named in the subgraph label carry the
# tier's state without colour.
# ---------------------------------------------------------------------------
TIER_STYLE = {
    "tierUnderway": {  # mix(line, surface-raised, .25) / (.75); label ink
        "var": "tier-underway", "bg": "#cbcfac", "stroke": "#1d2718",
        "darkBg": "#434a32", "darkStroke": "#e3e8cc", "extra": "",
    },
    "tierDeferred": {  # mix(card, slip, .5) / mix(card, card-dark, .75); label ink / card-ink
        "var": "tier-deferred", "bg": "#d8c4a8", "stroke": "#1d2718",
        "darkBg": "#5a4225", "darkStroke": "#f2e8d0",
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
# part of that four-way partition. Ballpoint is shared with trails (see
# roadbook-conventions.md), the same way the deferred/blocked/paused/done
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
    Secondary, 2 for Tertiary and so on. See roadbook-conventions.md's Tiers
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


def redundant_cross_tier_edges(phase):
    """[(task_id, dep_id, dep_milestone_id, dep_tier, via_id)] for every `dependsOn`
    entry naming a *task* in a lower release tier that the task already
    requires through another of its own entries: a milestone requires
    every hard member, a task requires everything in its `dependsOn`. A
    tertiary task listing `10SE.4` next to `M10` is the shape this catches;
    the milestone already carries the edge, so the task edge adds nothing
    and breaks the tier pattern (roadbook-conventions.md, Tiers). Milestone
    entries are never reported, since `["M1", "M6", "8RT.9"]` is the
    pattern itself even when `8RT.9` carries M1 and M6 too; nor is a
    lower-tier task nothing else reaches, which may be a deliberate
    fast-track. Empty for an untiered phase."""
    tasks, milestones, _gates = build_index(phase)
    task_tier, task_milestone, milestone_tier_of = {}, {}, {}
    for m in phase.get("milestones", []):
        milestone_tier_of[m["id"]] = milestone_tier(m.get("name", ""))
        for t in m.get("tasks", []):
            task_tier[t["id"]] = milestone_tier_of[m["id"]]
            task_milestone[t["id"]] = m["id"]
    if not any(milestone_tier_of.values()):
        return []
    hard_members = {mid: [t for t in members
                          if not tasks.get(t, {}).get("softMilestone")]
                    for mid, members in milestones.items()}

    def reachable(start):
        seen, stack = set(), [start]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            if node in tasks:
                stack.extend(tasks[node].get("dependsOn", []))
            elif node in hard_members:
                stack.extend(hard_members[node])
        return seen

    found = []
    for tid, task in tasks.items():
        deps = task.get("dependsOn", [])
        for dep in deps:
            if dep not in tasks or task_tier[dep] >= task_tier[tid]:
                continue
            via = next((other for other in deps
                        if other != dep and dep in reachable(other)), None)
            if via is not None:
                found.append((tid, dep, task_milestone[dep], task_tier[dep], via))
    return found


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
       "deferred" would contradict goblin-scout:survey-waypoints' own ready-set)
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


_DEV_COLOUR_PALETTE = ["beetroot", "moss", "biro", "ochre", "rust"]


def dev_colour(assignee):
    """Stable colour-family name for a scout's chip: one of the theme's five
    inks (accent, accent-2, info, warn, danger), as Jason approved on
    2026-11-18. They are the status inks too, so a chip is told from a
    status by its shape (a named pill), never by colour alone.

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
    """The project root a roadbook belongs to. roadbook.json conventionally
    lives at <root>/.claude/roadbook.json; when it lives elsewhere, treat its
    own directory as the root rather than blindly taking parent.parent."""
    p = Path(json_path).resolve()
    return p.parent.parent if p.parent.name == ".claude" else p.parent


# ---------------------------------------------------------------------------
# detect
# ---------------------------------------------------------------------------
_ANCHOR_RE = re.compile(r'<a name="m\d|#m\d+-(?:doing|todo|blocked|done)')


def _md_paths(data, json_path):
    """Every .md path referenced by the roadbook json, resolved from its root."""
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
    except RoadbookError as exc:
        print(f"✗ {exc}")
        return 2

    if isinstance(data, dict) and "roadmaps" in data:
        print(f"old: {path.name} is a pointer registry, not a phase array")
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

    print(f"rich: phase-array {path.name}, no old-format markers")
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
            problems.append(f"{m['id']}: milestone has no waypoints")

    problems.extend(_artefact_problems(phase))

    if SOURCE_KEY in phase:
        source = phase[SOURCE_KEY]
        kind = source.get("kind") if isinstance(source, dict) else None
        if kind not in SOURCE_KINDS:
            problems.append(
                f"source: kind {kind!r} is not one of "
                f"{{{', '.join(sorted(SOURCE_KINDS))}}}")
        elif not source.get("project"):
            problems.append("source: a jira source needs a 'project' key")

    known = set(tasks) | set(milestones) | set(gates)
    gate_expected_blocks = {gid: set() for gid in gates}
    for tid, task in tasks.items():
        if task.get("status") not in VALID_STATUSES:
            hint = (" (a claim is the `started` field: run roadbook.py claim)"
                    if task.get("status") == IN_PROGRESS else "")
            problems.append(f"{tid}: invalid status {task.get('status')!r}{hint}")
        if "local" in task and task["local"] is not True:
            problems.append(
                f"{tid}: local {task['local']!r} must be true or absent")
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
                    f"{tid}: ended {ended} on a waypoint whose status is "
                    f"{task.get('status')!r}, not done (an end date records "
                    "finished work; remove it when a waypoint is reopened)")
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
                f"gate {gid}: blocks[] missing {missing} (waypoint depends on gate)")
        for extra in sorted(declared - expected):
            problems.append(
                f"gate {gid}: blocks[] lists {extra} but it does not depend on {gid}")

    for tid, dep, dep_milestone, dep_tier, via in redundant_cross_tier_edges(phase):
        problems.append(
            f"{tid}: dependsOn {dep!r} sits in {dep_milestone} "
            f"({tier_label(dep_tier)}), already required through {via}; "
            f"a tier reaches a lower tier by milestone, so drop the edge "
            f"and name {dep} in notes instead")

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
    except RoadbookError as exc:
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
          f"{len(tasks)} waypoints, {len(milestones)} milestones, {len(gates)} gates.")
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


def _refuse_if_stamped_newer(data):
    """Raise when any phase was last written by a newer plugin than this one."""
    for phase in _phases(data):
        stamp = phase.get(STAMP_KEY)
        if newer_than_running(stamp, PLUGIN_VERSION):
            raise RoadbookError(
                f"phase {phase.get('name')!r} was written by plugin version "
                f"{stamp}; this is {PLUGIN_VERSION}. Update the plugin before "
                "writing, so nothing a newer version produced is undone.")


def _stamp_live_phases(data):
    """Stamp each live phase with the running plugin's major.minor."""
    stamp = stamp_for(PLUGIN_VERSION)
    if stamp:
        for phase in _phases(data):
            if phase.get("archived"):
                continue
            held = phase.get(STAMP_KEY)
            # A missing or unparsable stamp is repaired; only a lower one is raised.
            if stamp_for(held) is None or newer_than_running(stamp, held):
                _set_phase_field(phase, STAMP_KEY, stamp)


def _write_roadbook(path, data, pin=True, unpinned=(), siblings=True):
    """Write roadbook.json after the version check, stamping each live phase
    with the running plugin's major.minor. The one writer for the roadbook
    file. Returns the path written, which is not `path` when `path` was a
    pre-3.0.0 file: that first write moves it (_migrate_legacy). `pin` False
    leaves the chart paths of `data` as they are, for `rebind --outputs`;
    `unpinned` names phases of `data` not to pin (one whose chart path the
    write itself clears); `siblings` False moves this file alone, for
    `rebind`, which moves each file itself."""
    _refuse_if_stamped_newer(data)
    path = Path(path)
    if path.name in LEGACY_NAMES:
        return _migrate_legacy(path, data, pin, unpinned, siblings)
    _stamp_live_phases(data)
    _atomic_write(path, _canonical_text(data))
    _note_legacy_beside(path)
    return path


def _shown(path):
    """`.claude/NAME` for a file in a .claude directory, else the full path."""
    return f".claude/{path.name}" if path.parent.name == ".claude" else str(path)


def _note_legacy_beside(path):
    """One stderr line when a pre-3.0.0 file still sits beside the roadbook
    just written: the roadbook wins and the old file is never touched."""
    for old, new in LEGACY_NAMES.items():
        stale = path.parent / old
        if path.name == new and stale.exists():
            print(f"note: {_shown(stale)} is still here beside {_shown(path)}; "
                  f"goblin-scout reads {path.name} and leaves {old} alone, so "
                  "delete it once nothing needs it", file=sys.stderr)


def _pin_legacy_chart(data, unpinned=()):
    """Give every phase with no `artefact` the path a 2.x plugin rendered its
    chart to, so a migrated project's chart stays where it was; a new
    roadbook takes the new default (_default_render_path). A phase in
    `unpinned` (by identity) is left without one."""
    for phase in _phases(data):
        if any(phase is skip for skip in unpinned):
            continue
        if isinstance(phase, dict) and ARTEFACT_KEY not in phase:
            _set_phase_field(phase, ARTEFACT_KEY, _legacy_render_rel(phase))


def _migrate_legacy(path, data, pin=True, unpinned=(), siblings=True):
    """Move a roadmap plugin's .claude/roadmaps.json, and the local file
    beside it, to the roadbook names on the first write by 3.0.0. No value
    is rewritten: each phase is stamped (so a 2.x plugin refuses the file),
    a phase rendering to the old default chart path has that path pinned in
    `artefact`, and the file being written carries its own change. A local
    file moved alongside travels byte for byte instead, untouched. One line
    of notice on stderr, plus one when git would now track a local file it
    ignored under the old name. Returns the new path of `path`."""
    folder = path.parent
    plan = []
    unpinned_charts = []  # (target, phase) moved byte for byte with no chart path
    for old, new in LEGACY_NAMES.items():
        source, target = folder / old, folder / new
        if source != path and (not siblings or not source.exists()):
            continue
        if target.exists():
            if source == path:
                raise RoadbookError(
                    f"{_shown(target)} already exists beside {_shown(source)}; "
                    f"write to {target.name}, the one goblin-scout reads")
            continue  # a stale old file beside the live one: left alone
        if source == path:
            content = data
        else:
            try:
                raw = source.read_bytes()
                content = json.loads(raw.decode("utf-8"))  # not UTF-8 is a ValueError too
                _phases(content)
            except (ValueError, RoadbookError):
                content = None  # not a phase array: moved byte for byte
        if content is not None:
            _refuse_if_stamped_newer(content)
            if (source != path and source.name not in LOCAL_NAMES
                    and _canonical_text(content).encode("utf-8") != raw):
                # every other write refuses to reformat a file wholesale; this
                # one would do it to a file the caller never named. Bytes,
                # since read_text() would fold CRLF into LF and hide it
                raise RoadbookError(
                    f"{_shown(source)} is not in canonical form (tab-indented, "
                    "ensure_ascii off, trailing newline), and this write would "
                    f"move it to {_shown(target)} reformatted, which hides the "
                    "move from git's rename detection; nothing was written. "
                    "Run `roadbook.py rebind --reformat` to move both files "
                    "and accept the reformat, then run this again")
            if source != path and source.name in LOCAL_NAMES:
                # Ruled 2026-11-19: a local file moved alongside the one being
                # written travels byte for byte. Nobody asked for it to be
                # rewritten, so it keeps its own form; rebind --reformat is
                # the one way to have it reformatted. It carries no chart
                # pin either, so the notice names each chart that moves.
                unpinned_charts.extend(
                    (target, phase) for phase in _phases(content)
                    if isinstance(phase, dict) and ARTEFACT_KEY not in phase)
                content = None
        if content is not None:
            if pin or source != path:
                _pin_legacy_chart(content, unpinned if source == path else ())
            _stamp_live_phases(content)
        plan.append((source, target, content))
    for source, target, content in plan:
        if content is None:
            os.replace(source, target)
        else:
            _atomic_write(target, _canonical_text(content))
    for source, target, content in plan:
        if content is not None:
            source.unlink()
    moves = " and ".join(f"{_shown(s)} to {_shown(t)}" for s, t, _c in plan)
    if not pin:
        outputs = "the outputs move as rebind lists them"
    elif unpinned_charts:
        outputs = "the projections, and every chart but those noted below, keep their paths"
    else:
        outputs = "the chart and projections keep their paths"
    print(f"goblin-scout {PLUGIN_VERSION} moved {moves}; no value was "
          f"rewritten, {outputs} and a 2.x plugin (when it was called "
          "roadmap) now refuses the file. Commit the move.",
          file=sys.stderr)
    for target, phase in unpinned_charts:
        root = project_root(target)
        now = _default_render_path(target, phase).relative_to(root).as_posix()
        print(f"note: phase {phase.get('name')!r} in {_shown(target)} has no "
              f"chart path, so its chart now renders to {now}; "
              f"`roadbook.py rebind --outputs` moves a 2.x chart at "
              f"{_legacy_render_rel(phase)} there", file=sys.stderr)
    for source, target, _content in plan:
        if target.name not in LOCAL_NAMES:
            continue
        git, rel = _git_at_toplevel(target)
        if git is None:
            continue
        old_rel = str(Path(rel).with_name(source.name))
        if (git("check-ignore", "-q", old_rel) is not None
                and git("check-ignore", "-q", rel) is None):
            print(f"note: {rel} is not ignored by git, though {old_rel} "
                  "was; add it to .gitignore", file=sys.stderr)
    return folder / LEGACY_NAMES[path.name]


_ARTEFACT_VERSION_RE = re.compile(r'"pluginVersion": "([^"]*)"')


def _refuse_if_artefact_newer(out):
    """Raise when the dashboard already at `out` came from a newer plugin."""
    try:
        existing = Path(out).read_text()
    except (OSError, UnicodeDecodeError):
        return
    found = _ARTEFACT_VERSION_RE.search(existing)
    if found and newer_than_running(found.group(1), PLUGIN_VERSION):
        raise RoadbookError(
            f"{out} was rendered by plugin version {found.group(1)}; this is "
            f"{PLUGIN_VERSION}. Update the plugin before rendering over it.")


def cmd_recompute(args) -> int:
    try:
        path, data = load(args.path)
        phase = active_phase(data, args.phase)
    except RoadbookError as exc:
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
            print(f"✗ {path.name} is not in canonical form (tab-indented, "
                  "ensure_ascii off, trailing newline); a write would reformat "
                  "the whole file, not just statuses. Re-run with --reformat "
                  "to accept that, or normalise the file first.")
            return 1
        for tid, _old, new in changes:
            tasks[tid]["status"] = new
        path = _write_roadbook(path, data)

    if changes:
        verb = "would change" if args.check else "changed"
        print(f"{verb} {len(changes)} status(es):")
        for tid, old, new in changes:
            print(f"  {tid}: {old} -> {new}")
    else:
        print("no status changes.")

    if args.render and not args.check:
        try:
            out = _render_path(path, phase)
        except RoadbookError as exc:
            print(f"✗ {exc}")
            return 1
        if out.exists():
            _render_to(path, data, phase, out)
            print(f"refreshed chart: {out}")
        else:
            print(f"note: no chart at {out}; run `roadbook.py render` to create one")
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
        lines.append(f"WARNING: {len(stats['invalid'])} waypoint(s) with invalid "
                     f"status, excluded from byStatus: "
                     + ", ".join(stats["invalid"]))
    return "\n".join(lines)


def _milestone_natural_key(mid):
    return [int(part) if part.isdigit() else part
            for part in re.split(r"(\d+)", str(mid))]


def overview_layout(phase, stats, ready):
    """Sort order and tier grouping for the artefact's Overview/Milestones
    sections, computed once here so the template only renders what this
    says (see roadbook-conventions.md's Milestone sort/tier-group rules).

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
    except RoadbookError as exc:
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

    return {"phase": phase.get("name"), "nodes": nodes,
            "edges": _reduce_milestone_edges(edges)}


def _reduce_milestone_edges(edges):
    """Drop each hard milestone-complete edge whose milestone is already
    reachable from its sink through the other hard edges (a transitive
    reduction). Task edges come from authored dependsOn and are never
    touched; soft edges neither count as paths nor get dropped."""
    out = {}
    for e in edges:
        if not e.get("soft"):
            out.setdefault(e["from"], []).append(e["to"])

    def reaches(source, target, skip):
        seen, stack = set(), [source]
        while stack:
            node = stack.pop()
            for nxt in out.get(node, []):
                if (node, nxt) == skip or nxt in seen:
                    continue
                if nxt == target:
                    return True
                seen.add(nxt)
                stack.append(nxt)
        return False

    kept = []
    for e in edges:
        if e["kind"] == "milestone-complete" and not e.get("soft"):
            if reaches(e["from"], e["to"], (e["from"], e["to"])):
                out[e["from"]].remove(e["to"])
                continue
        kept.append(e)
    return kept


def _mermaid_label(text, reserve=0):
    """Collapse whitespace, cap the length (leaving `reserve` characters for a
    marker appended after) and escape quotes for a Mermaid node label."""
    limit = _LABEL_MAX - reserve
    text = " ".join(str(text).split())
    if len(text) > limit:
        text = text[:limit - 1].rstrip() + "…"
    return text.replace('"', "#quot;")


def _classdef_lines(palette, styles=STATUS_STYLE):
    """One classDef per style. The label takes the style's `text` colour,
    which is its stroke unless the node is inverted (a tier has none)."""
    lines = []
    for cls, st in styles.items():
        if palette == "vars":
            bg = f"var(--color-{st['var']}-bg)"
            stroke = f"var(--color-{st['var']})"
            text = f"var(--color-{st['var']}-text)" if "text" in st else stroke
        elif palette == "dark":
            bg, stroke = st["darkBg"], st["darkStroke"]
            text = st.get("darkText", stroke)
        else:
            bg, stroke = st["bg"], st["stroke"]
            text = st.get("text", stroke)
        parts = [f"fill:{bg}", f"stroke:{stroke}", f"color:{text}"]
        if st["extra"]:
            parts.append(st["extra"])
        lines.append(f"\tclassDef {cls} {','.join(parts)}")
    return lines


def _topological_order(ids, order, edges):
    """Stable Kahn's algorithm: among the ready nodes, always emit the one
    that appears first in the roadbook. Any cycle remainder (invalid, but the
    diagram should still draw) is appended in roadbook order."""
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
    remainder in roadbook order) and never impose status, block a milestone
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


# Estimated on-screen footprint of one Mermaid node in the chart's
# diagram shell (IBM Plex Sans 16px, up to _LABEL_MAX-ish characters wrapped
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
    roadbook-conventions.md).

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
    except RoadbookError as exc:
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
    exclusive. Raises RoadbookError on an unknown id or tier, on both being
    given, and on `focus` when no tier is underway."""
    if milestones and tiers:
        raise RoadbookError("milestones and tiers are mutually exclusive")
    entries = build_stats(phase)["milestones"]
    if milestones:
        known = {m["id"].lower(): m["id"] for m in entries}
        unknown = [m for m in milestones if m.lower() not in known]
        if unknown:
            raise RoadbookError(
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
            raise RoadbookError(f"no tier is underway in {phase.get('name')}")
        wanted = set(underway)
    else:
        unknown = [t for t in tiers if t.lower() not in words]
        if unknown:
            raise RoadbookError(
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
    # its milestone reaches tasks that depend on the milestone). A soft member
    # never gates its milestone, so completing it unblocks nothing that way.
    dependents = {tid: set() for tid in tasks}
    for tid, t in tasks.items():
        for dep in t.get("dependsOn", []):
            if dep in tasks:
                dependents[dep].add(tid)
            elif dep in milestones:
                for member in milestones[dep]:
                    if member in dependents and not tasks[member].get("softMilestone"):
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

    def unblock_split(tid):
        """(now, partly, later) counts of open tasks downstream of `tid`.

        now: direct dependents that become todo the moment `tid` is done
        (found by recomputing with `tid` marked done, so gates and milestone
        membership behave as everywhere else). partly: the other direct
        dependents, which still wait on something else. later: transitive
        dependents that are not direct. Closed tasks count nowhere."""
        def is_open(other):
            return effective.get(other) not in ("done", "out_of_scope")
        direct = {d for d in dependents.get(tid, ()) if is_open(d)}
        after = recompute_all({**tasks, tid: {**tasks[tid], "status": "done"}},
                              milestones, gates)
        now = {d for d in direct
               if not is_held(tasks[d]) and after.get(d) == "todo"}
        later = {d for d in transitive(tid) if is_open(d)} - direct
        return len(now), len(direct) - len(now), len(later)

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
        unblocks_now, unblocks_partly, unblocks_later = unblock_split(tid)
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
            "unblocksNow": unblocks_now,
            "unblocksPartly": unblocks_partly,
            "unblocksLater": unblocks_later,
            "isMilestoneSink": (tid in sinks.get(mid, [])
                                and not t.get("softMilestone")),
            "notes": t.get("notes", ""),
            "assignee": t.get("assignee", ""),
        })
        if t.get("topic"):
            candidates[-1]["topic"] = t["topic"]
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

    goblin-scout:survey-waypoints prints one table per group. Left to count for itself, a
    model drops rows and still reports a full total, so the membership of
    every table is fixed here instead. The topic is the task's own `topic`
    when it has one (a mirrored task carries its epic there), else the letters
    between the milestone number and the sequence in its id (`2TI.3` -> `TI`);
    an id that does not fit that shape lands under `other`. The dev key is the
    trimmed `assignee`, or `unassigned` when empty. Groups come out in
    display order (milestones by number, topics alphabetically, devs
    case-insensitive alphabetical with `unassigned` last); ids inside a
    group keep the order of `candidates`.
    """
    by_milestone, by_topic, by_dev = {}, {}, {}
    for c in candidates:
        by_milestone.setdefault(c.get("milestone") or "none", []).append(c["id"])
        match = re.match(r"\d+([A-Za-z]+)\.", c["id"])
        topic = c.get("topic") or (match.group(1) if match else "other")
        by_topic.setdefault(topic, []).append(c["id"])
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
    except RoadbookError as exc:
        print(f"✗ {exc}")
        return 2
    if args.json:
        ready = {**ready, "candidates": _truncate_notes(ready["candidates"]),
                 "groups": ready_groups(ready["candidates"])}
        print(json.dumps(ready, indent="\t"))
        return 0
    noun = "open" if horizon == "open" else "unblocked"
    if not ready["candidates"]:
        print(f"{ready['phase']}: no {noun} waypoints.")
        _print_claimed(ready["claimed"])
        return 0
    print(f"{ready['phase']}: {len(ready['candidates'])} {noun} waypoint(s), "
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
    print(f"on a trail: {len(claimed)} waypoint(s)")
    for c in claimed:
        who = f" by {c['assignee']}" if c.get("assignee") else ""
        blocked = "" if c["status"] == "todo" else f" ({c['status']})"
        print(f"  {c['id']:8} since {c['started']}{who}{blocked}")


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------
def _template_path():
    return Path(__file__).resolve().parent.parent / "templates" / "chart.html"


# The faces the chart sets its type in, embedded so a chart opened offline
# looks as it should and asks no font server for anything: (family, weight,
# file under templates/fonts/). Latin subsets of the @fontsource 5.3.0
# packages; Cabin Sketch and IBM Plex are OFL-1.1, Special Elite and
# Permanent Marker Apache-2.0, each licence beside its file.
CHART_FACES = [
    ("Cabin Sketch", 700, "cabin-sketch-latin-700-normal.woff2"),
    ("Special Elite", 400, "special-elite-latin-400-normal.woff2"),
    ("IBM Plex Mono", 400, "ibm-plex-mono-latin-400-normal.woff2"),
    ("IBM Plex Sans", 400, "ibm-plex-sans-latin-400-normal.woff2"),
    ("IBM Plex Sans", 600, "ibm-plex-sans-latin-600-normal.woff2"),
    ("Permanent Marker", 400, "permanent-marker-latin-400-normal.woff2"),
]


def _chart_theme_css():
    """The goblin theme's custom properties (templates/chart-theme.css)."""
    return (Path(__file__).resolve().parent.parent / "templates"
            / "chart-theme.css").read_text()


def _chart_font_faces():
    """One @font-face rule per embedded face, each file inlined as base64."""
    import base64
    fonts = Path(__file__).resolve().parent.parent / "templates" / "fonts"
    rules = []
    for family, weight, name in CHART_FACES:
        data = base64.b64encode((fonts / name).read_bytes()).decode("ascii")
        rules.append(f"@font-face {{ font-family: '{family}'; font-style: normal; "
                     f"font-weight: {weight}; font-display: swap; "
                     f"src: url(data:font/woff2;base64,{data}) format('woff2'); }}")
    return "\n".join(rules)


def _slug(name, fallback="roadbook"):
    return re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-") or fallback


def _default_render_path(json_path, phase):
    return (project_root(json_path) / "docs" / "artefacts"
            / f"chart-{_slug(phase.get('name'))}.html")


def _legacy_render_rel(phase):
    """Where a 2.x roadmap plugin rendered a phase with no `artefact`,
    relative to the project root: what a migrated phase is pinned to."""
    return f"docs/artefacts/roadmap-{_slug(phase.get('name'), 'roadmap')}.html"


ARTEFACT_KEY = "artefact"


def _artefact_problems(phase):
    """Discrepancies in a phase's optional `artefact` key: the dashboard path
    that render and recompute --render write, relative to the project root.
    Absent is fine (the slug default applies); present means a non-empty
    relative .html path that stays inside the project."""
    if ARTEFACT_KEY not in phase:
        return []
    value = phase.get(ARTEFACT_KEY)
    if not isinstance(value, str) or not value.strip():
        return [f"artefact: {value!r} is not a path"]
    problems = []
    if Path(value).is_absolute():
        problems.append(
            f"artefact: {value!r} is absolute; give a path relative to the "
            "project root")
    if ".." in Path(value).parts:
        problems.append(f"artefact: {value!r} leaves the project root")
    if not value.lower().endswith(".html"):
        problems.append(f"artefact: {value!r} does not end in .html")
    return problems


def _render_path(json_path, phase, override=None):
    """Where a phase's dashboard goes: `--out` > the phase's `artefact` key
    (relative to the project root) > docs/artefacts/chart-{slug}.html, or
    the 2.x default for a file not yet moved from roadmaps.json, which is
    where the migration will pin it. The one resolver, so render and
    recompute --render cannot disagree."""
    if override:
        return Path(override)
    problems = _artefact_problems(phase)
    if problems:
        raise RoadbookError("; ".join(problems))
    custom = phase.get(ARTEFACT_KEY)
    if custom:
        return project_root(json_path) / custom
    if Path(json_path).name in LEGACY_NAMES:
        return project_root(json_path) / _legacy_render_rel(phase)
    return _default_render_path(json_path, phase)


def _phase_for(data, selector=None):
    """The phase a render or config acts on: the one named by --phase, archived
    or not, else the single active phase."""
    return named_phase(data, selector) if selector else active_phase(data)


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
        raise RoadbookError(
            f"template header comment must contain exactly one comment-close "
            f"sequence before <html>, found {closes} in {template}: a stray "
            "close in the prose spills the page. Reword so the comment holds "
            "no raw close sequence except its own terminator.")


def _project_name(json_path, phase):
    """Optional `project` field on the phase, falling back to the project
    root directory name. See roadbook-conventions.md for the field."""
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
    _refuse_if_stamped_newer(data)
    template = _template_path()
    if not template.exists():
        raise RoadbookError(f"render template missing at {template}")
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
        "pluginVersion": PLUGIN_VERSION,
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
    for token in ("%%THEME%%", "%%FONTS%%", "%%DATA%%"):
        if template_html.count(token) != 1:
            raise RoadbookError(
                f"template must contain exactly one {token} placeholder; found "
                f"{template_html.count(token)} in {template}")
    _assert_header_comment_clean(template_html, template)
    # The fixed pieces go in first, so a phase name that happens to read
    # %%FONTS%% or %%THEME%% stays text and never pulls a blob in after it.
    html = (template_html
            .replace("%%THEME%%", _chart_theme_css())
            .replace("%%FONTS%%", _chart_font_faces())
            .replace("%%TITLE%%", str(phase.get("name") or "Roadbook"))
            .replace("%%DATA%%", payload))
    _refuse_if_artefact_newer(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(out, html)


def cmd_render(args) -> int:
    try:
        path, data = load(args.path)
        phase = _phase_for(data, args.phase)
        out = _render_path(path, phase, args.out)
        _render_to(path, data, phase, out)
    except RoadbookError as exc:
        print(f"✗ {exc}")
        return 2
    print(f"wrote {out}")
    return 0


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------
PHASE_FIELD_ORDER = ["name", "path", "project", SOURCE_KEY, ARTEFACT_KEY,
                     STAMP_KEY, "archived", "externalGates", "milestones"]


def cmd_config(args) -> int:
    if (args.clear and args.value and not args.path
            and not args.value.lower().endswith(".html")):
        # `config artefact --clear ROADBOOK.json`: both positionals are
        # optional, so argparse has read the roadbook path as the value.
        # A value that looks like a dashboard path is a mistyped set, left
        # for the guard below rather than read as the roadbook path.
        args.path, args.value = args.value, None
    if args.clear == bool(args.value):
        print("✗ give a value to set, or --clear to remove the key")
        return 2
    try:
        path, data = load(args.path)
        phase = _phase_for(data, args.phase)
    except RoadbookError as exc:
        print(f"✗ {exc}")
        return 2
    if _canonical_text(data) != path.read_text() and not args.reformat:
        print(f"✗ {path.name} is not in canonical form (tab-indented, "
              "ensure_ascii off, trailing newline); a write would reformat "
              "the whole file. Re-run with --reformat to accept that.")
        return 1
    name = phase.get("name")
    before = (None if _artefact_problems(phase)
              else _render_path(path, phase))
    if args.clear:
        if ARTEFACT_KEY not in phase:
            print(f"no artefact key on '{name}'; nothing to clear")
            return 0
        del phase[ARTEFACT_KEY]
    else:
        problems = _artefact_problems({ARTEFACT_KEY: args.value})
        if problems:
            print(f"✗ refusing to set artefact on '{name}':")
            for p in problems:
                print(f"  - {p}")
            return 1
        _set_phase_field(phase, ARTEFACT_KEY, args.value)
    # a cleared phase on a file not yet moved must stay cleared, not be pinned
    path = _write_roadbook(path, data, unpinned=(phase,) if args.clear else ())
    after = _render_path(path, phase)
    verb = "cleared artefact on" if args.clear else "set artefact on"
    print(f"{verb} '{name}'; the chart path is now {after}")
    # On a case-insensitive filesystem a case-only change leaves one file
    # under two names, so the "old" dashboard is the live one: no note.
    if (before and before != after and before.exists()
            and not (after.exists() and os.path.samefile(before, after))):
        print(f"note: a chart still exists at the old path {before}; "
              "nothing refreshes it any more, so delete it")
    if not after.exists():
        print(f"note: no chart at {after} yet; run `roadbook.py render"
              f" --phase \"{name}\"` to create it")
    return 0


# ---------------------------------------------------------------------------
# claim / release / end
# ---------------------------------------------------------------------------
TASK_FIELD_ORDER = ["id", "description", "status", "dependsOn",
                    "softDependsOn", "softMilestone", "iterative", "topic",
                    "local", "tracker", "orphaned", "notes", "assignee",
                    "started", "ended", "pr"]


def _set_field(obj, key, value, order):
    """Set `key` in place, or insert it where the canonical field `order` puts
    it, leaving every other field exactly where it already is."""
    if key in obj:
        obj[key] = value
        return
    rank = order.index(key)
    items = list(obj.items())
    at = len(items)
    for i, (k, _v) in enumerate(items):
        if k in order and order.index(k) > rank:
            at = i
            break
    items.insert(at, (key, value))
    obj.clear()
    obj.update(items)


def _set_task_field(task, key, value):
    _set_field(task, key, value, TASK_FIELD_ORDER)


def _set_phase_field(phase, key, value):
    _set_field(phase, key, value, PHASE_FIELD_ORDER)


def _load_for_write(args):
    """(path, data, index, exit code or None) for claim and release, refusing
    what recompute refuses before it writes. `index` is build_index()'s
    (tasks, milestones, gates); its task dicts are the ones inside `data`, so
    editing one edits what gets written."""
    try:
        path, data = load(args.path)
        phase = active_phase(data, args.phase)
    except RoadbookError as exc:
        print(f"✗ {exc}")
        return None, None, None, 2
    if _canonical_text(data) != path.read_text() and not args.reformat:
        print(f"✗ {path.name} is not in canonical form (tab-indented, "
              "ensure_ascii off, trailing newline); a write would reformat "
              "the whole file. Re-run with --reformat to accept that.")
        return None, None, None, 1
    index = build_index(phase)
    if args.id not in index[0]:
        print(f"✗ no waypoint {args.id!r} in '{phase.get('name')}'")
        return None, None, None, 1
    if is_mirrored(phase, index[0][args.id]):
        print(f"✗ {args.id} is mirrored from {_source_label(phase)}: its "
              "status, dates and assignee are set there and arrive with "
              "`roadbook.py pull`. Only a waypoint marked local can be changed here.")
        return None, None, None, 1
    return path, data, index, None


def _source_label(phase):
    source = phase_source(phase) or {}
    return f"{str(source.get('kind', '')).capitalize()} {source.get('project', '')}".strip()


def _refuse_history_dates(phase, command):
    """stamp-ended and backfill-ended read the roadbook file's git history; a
    mirrored phase lives outside git and takes its dates from the tracker."""
    if phase_source(phase) is None:
        return False
    print(f"✗ '{phase.get('name')}' is mirrored from {_source_label(phase)}: "
          f"end dates arrive with `roadbook.py pull`, so {command} has nothing "
          "to do. Date a local waypoint with `roadbook.py end ID`.")
    return True


def cmd_claim(args) -> int:
    path, data, index, code = _load_for_write(args)
    if code is not None:
        return code
    tasks, milestones, gates = index
    task = tasks[args.id]
    cycles = find_cycles(tasks, milestones)
    if cycles:
        print("✗ cycle detected; refusing to start a trail until it is resolved:")
        for cycle in cycles:
            print("  - " + " -> ".join(cycle))
        return 1
    if is_claimed(task):
        who = f" by {task['assignee']}" if task.get("assignee") else ""
        print(f"✗ {args.id} is already on a trail{who} (started {task['started']})")
        return 1
    computed = recompute_all(tasks, milestones, gates)
    effective = task.get("status") if is_held(task) else computed.get(args.id)
    stacked_on = []
    if effective != "todo":
        # A task held only by dependencies can still be claimed when the work
        # is stacked on the work that unblocks it: every unmet blocker carries
        # `started` in this file. A gate can never be claimed, so it refuses.
        unclaimed = []
        unmet = []
        if effective == "blocked" and not is_held(task):
            unmet = unmet_blockers(args.id, tasks, milestones, gates)
            stacked_on = [ident for kind, ident in unmet
                          if kind == "task" and is_claimed(tasks[ident])]
            unclaimed = [f"gate {ident}" if kind == "gate" else ident
                         for kind, ident in unmet
                         if kind == "gate" or not is_claimed(tasks[ident])]
        if not unmet or unclaimed:
            hint = ("only a waypoint that is ready to start can take a trail"
                    if not unclaimed else
                    "it can take a trail once every blocker is on one (a gate "
                    "cannot be); not on a trail: " + ", ".join(unclaimed))
            print(f"✗ {args.id} is {effective}, not todo: {hint}")
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
    _write_roadbook(path, data)
    who = f", assignee {task['assignee']}" if task.get("assignee") else ""
    stacked = f", stacked on {', '.join(stacked_on)}" if stacked_on else ""
    print(f"✓ {args.id} is on a trail (started {started}{who}{stacked})")
    return 0


def cmd_assign(args) -> int:
    path, data, index, code = _load_for_write(args)
    if code is not None:
        return code
    task = index[0][args.id]
    current = task.get("assignee", "")
    if args.unassign:
        if not current:
            print(f"✓ {args.id} has no assignee")
            return 0
        del task["assignee"]
        _write_roadbook(path, data)
        print(f"✓ cleared {args.id}'s assignee (was {current})")
        return 0
    name = args.assignee.strip()
    if not name:
        print("✗ --assignee needs a name")
        return 1
    if current and current.strip().lower() == name.lower():
        print(f"✓ {args.id} already assigned to {current}")
        return 0
    _set_task_field(task, "assignee", name)
    _write_roadbook(path, data)
    was = f" (was {current})" if current else ""
    print(f"✓ assigned {args.id} to {name}{was}")
    return 0


def cmd_release(args) -> int:
    path, data, index, code = _load_for_write(args)
    if code is not None:
        return code
    task = index[0][args.id]
    if not is_claimed(task):
        print(f"✗ {args.id} is not on a trail")
        return 1
    del task["started"]
    if args.unassign:
        task.pop("assignee", None)
    _write_roadbook(path, data)
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
    _write_roadbook(path, data)
    print(f"✓ ended {args.id} ({ended})")
    return 0


def cmd_stamp_ended(args) -> int:
    """Stamp `ended` on the done tasks a branch finished: those that were not
    done at its merge-base with --base, plus those whose `pr` is --pr. A task
    that already has `ended` is never touched."""
    try:
        path, data = load(args.path)
        phase = active_phase(data, args.phase)
    except RoadbookError as exc:
        print(f"✗ {exc}")
        return 2
    if _refuse_history_dates(phase, "stamp-ended"):
        return 1
    if _canonical_text(data) != path.read_text() and not args.reformat:
        print(f"✗ {path.name} is not in canonical form; re-run with "
              "--reformat to accept a whole-file rewrite.")
        return 1
    ended = args.date or date.today().isoformat()
    if not _is_iso_date(ended):
        print(f"✗ --date {ended!r} is not a YYYY-MM-DD date")
        return 1
    git, rel = _git_at_toplevel(path)
    if git is None:
        print(f"✗ {path.name} is not inside a git repository")
        return 1
    base = (git("merge-base", "HEAD", args.base) or "").strip()
    if not base:
        print(f"✗ no merge-base between HEAD and {args.base}")
        return 1
    before = _phase_statuses(_show_at(git, base, rel) or "", phase.get("name"))
    if before is None:
        print(f"✗ cannot read phase {phase.get('name')!r} at the merge-base "
              f"({base[:8]}): the file is missing or unparseable there, or the "
              "phase was renamed; stamp waypoints with `end ID` or run "
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
            _write_roadbook(path, data)
    if args.json:
        print(json.dumps({"phase": phase.get("name"), "ended": ended,
                          "written": not args.dry_run and bool(chosen),
                          "tasks": chosen}))
        return 0
    verb = "would end" if args.dry_run else "ended"
    print(f"{phase.get('name')}: {verb} {len(chosen)} waypoint(s) on {ended}"
          + (": " + ", ".join(chosen) if chosen else ""))
    return 0


def ended_from_history(versions, today):
    """{task id: (date, sha, basis)} for every task done in the last version.

    `versions` is the roadbook's history oldest first, each a (sha, date,
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
    """{task id: status} for the phase named `phase_name` in roadbook.json
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


def _rels_through_the_move(rel):
    """`rel` and, for a roadbook file, the pre-3.0.0 name it had before the
    move: history from before goblin-scout is still this file's history."""
    old = {new: old for old, new in LEGACY_NAMES.items()}.get(Path(rel).name)
    return [rel, str(Path(rel).with_name(old))] if old else [rel]


def _show_at(git, ref, rel):
    """The file's text at `ref`, under its roadbook name or, before the move,
    its old one; None when neither is there."""
    for name in _rels_through_the_move(rel):
        text = git("show", f"{ref}:{name}")
        if text is not None:
            return text
    return None


def _roadbook_versions(path, phase_name):
    """Oldest-first (sha, date, {id: status}) history of one phase from git,
    ending with the working-tree file as ("", "", ...). None when the file
    is not in a git repository."""
    git, rel = _git_at_toplevel(path)
    if git is None:
        return None

    versions = []
    log = git("log", "--first-parent", "--reverse", "--format=%H %cs", "--",
              *_rels_through_the_move(rel))
    for line in (log or "").splitlines():
        sha, when = line.split()
        found = _phase_statuses(_show_at(git, sha, rel) or "", phase_name)
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
    except RoadbookError as exc:
        print(f"✗ {exc}")
        return 2
    if _refuse_history_dates(phase, "backfill-ended"):
        return 1
    if _canonical_text(data) != path.read_text() and not args.reformat:
        print(f"✗ {path.name} is not in canonical form; re-run with "
              "--reformat to accept a whole-file rewrite.")
        return 1
    versions = _roadbook_versions(path, phase.get("name"))
    if versions is None:
        print(f"✗ {path.name} is not inside a git repository; there is no "
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
            _write_roadbook(path, data)
    if args.json:
        print(json.dumps({"phase": phase.get("name"), "written": not args.dry_run,
                          "tasks": rows, "skipped": skipped}, indent="\t"))
        return 0
    verb = "would set" if args.dry_run else "set"
    if not rows and not skipped:
        print(f"{phase.get('name')}: every done waypoint already has an end date.")
        return 0
    print(f"{phase.get('name')}: {verb} ended on {len(rows)} waypoint(s)")
    for row in rows:
        note = f" [{row['basis']}]" if row["basis"] != "transition" else ""
        where = f" ({row['commit']})" if row["commit"] else ""
        print(f"  {row['id']:8} {row['ended']}{where}{note}")
    for row in skipped:
        where = f" ({row['commit']})" if row["commit"] else ""
        print(f"  {row['id']:8} {row['ended']}{where} "
              f"[skipped: before started {row['started']}]")
    return 0


# ---------------------------------------------------------------------------
# pull
# ---------------------------------------------------------------------------
def _pull_target(args):
    """(path, data, phase) for `pull`: the live mirrored phase, or a new one
    when --project names a Jira project nothing here mirrors yet. A new phase
    goes into the local roadbook file, created beside the committed one."""
    # Only a file that cannot be found starts a new one. A file that exists
    # but does not parse is the user's work, so its error is let through
    # rather than replaced by a fresh file.
    try:
        resolve_roadbook_path(args.path)
    except RoadbookError:
        if not args.project:
            raise
        path, data = None, []
    else:
        path, data = load(args.path)
    phases = _phases(data) if data else []
    live = [p for p in phases
            if phase_source(p) and not p.get("archived")
            and (not args.phase or p.get("name") == args.phase)
            and (not args.project or phase_source(p).get("project") == args.project)]
    if len(live) > 1:
        names = ", ".join(repr(p.get("name")) for p in live)
        raise RoadbookError(f"{len(live)} mirrored phases ({names}); pick one with --phase")
    if live:
        return path, data, live[0]
    if not args.project:
        raise RoadbookError(
            "no mirrored phase here; start one with "
            "`roadbook.py pull --project KEY [--name NAME]`")
    name = args.name or args.phase or args.project
    if any(p.get("name") == name for p in phases):
        raise RoadbookError(f"a phase named {name!r} already exists; pass another --name")
    phase = {"name": name,
             SOURCE_KEY: {"kind": "jira", "project": args.project},
             "externalGates": [], "milestones": []}
    if path is not None and path.name in LOCAL_NAMES:
        data = phases + [phase]
        return path, data, phase
    if path is not None:
        root = project_root(path)
    else:
        start = Path(args.path).expanduser() if args.path else Path.cwd()
        git, _rel = _git_at_toplevel(start / LOCAL_ROADBOOK_NAME)
        top = (git("rev-parse", "--show-toplevel") or "").strip() if git else ""
        root = Path(top) if top else start
    return root / ".claude" / LOCAL_ROADBOOK_NAME, [phase], phase


# Where a 2.x roadmap plugin's skills put a projection and the prose overview
# by default, and where a roadbook's go: what `rebind --outputs` moves.
LEGACY_PROJECTION_DIR = "docs/roadmaps/"
PROJECTION_DIR = "docs/roadbook/"
LEGACY_OVERVIEW = "docs/reports/ROADMAP_OVERVIEW.md"
OVERVIEW = "docs/reports/ROADBOOK_OVERVIEW.md"


def _move_file(source, target):
    """Move one file, with `git mv` when git tracks it, so the move lands
    in the next commit as a rename."""
    target.parent.mkdir(parents=True, exist_ok=True)
    git, rel = _git_at_toplevel(source)
    if git is not None and git("ls-files", "--error-unmatch", rel) is not None:
        target_rel = target.resolve().relative_to(
            source.resolve().parents[len(Path(rel).parts) - 1]).as_posix()
        if git("mv", rel, target_rel) is not None:
            return
    os.replace(source, target)


def _rebind_files(path):
    """Every roadbook file of the project `path` belongs to, committed first:
    for each of the committed and the local file, the roadbook name, else the
    2.x name, when one exists. `path` itself is always among them."""
    folder = path.parent
    files = []
    for new, old in ((ROADBOOK_NAME, LEGACY_ROADBOOK_NAME), (LOCAL_ROADBOOK_NAME, LEGACY_LOCAL_ROADBOOK_NAME)):
        for name in (new, old):
            if (folder / name).exists():
                files.append(folder / name)
                break
    return files if path in files else [path]


def _rebind_outputs(path, data, root, claimed=frozenset()):
    """(moves, stale) for the phases in `data`: a (source, target) for each
    2.x default output, each phase updated to the roadbook's names as it
    goes, and each 2.x chart left beside the chart that replaced it.
    `claimed` holds every chart path a phase in either file names in
    `artefact`; such a file is that phase's own chart, never a 2.x default."""
    moves, stale = [], []
    for phase in _phases(data):
        if not isinstance(phase, dict):
            continue
        # an unmoved file's phase with no `artefact` renders to the 2.x default too
        legacy_chart = _legacy_render_rel(phase)
        if ARTEFACT_KEY not in phase and os.path.normpath(legacy_chart) in claimed:
            pass  # another phase's own chart: neither moved nor named stale
        elif phase.get(ARTEFACT_KEY, legacy_chart if path.name in LEGACY_NAMES else None) == legacy_chart:
            moves.append((root / legacy_chart, _default_render_path(path, phase)))
            phase.pop(ARTEFACT_KEY, None)
        elif ARTEFACT_KEY not in phase and (root / legacy_chart).exists():
            # a local file moved byte for byte carries no chart pin, so its
            # 2.x chart is still at the old default; one already rendered
            # to the new name makes the old file stale, and rebind never deletes
            current = _default_render_path(path, phase)
            if current.exists():
                stale.append((root / legacy_chart, current))
            else:
                moves.append((root / legacy_chart, current))
        projection = phase.get("path")
        if isinstance(projection, str) and projection.startswith(LEGACY_PROJECTION_DIR):
            new = PROJECTION_DIR + projection[len(LEGACY_PROJECTION_DIR):]
            _set_phase_field(phase, "path", new)
            moves.append((root / projection, root / new))
    return moves, stale


def cmd_rebind(args) -> int:
    """Move a 2.x .claude/roadmaps.json (and the roadmaps.local.json beside
    it) to the roadbook names now, as the first write would, and with
    --outputs move the chart, the projections and the prose overview of
    every phase in both files from the 2.x default names to the roadbook's.
    A path the project chose itself is left where it is. What --dry-run
    lists is exactly what runs."""
    try:
        path, _data = load(args.path)
        files = []
        noncanonical = set()  # read before --outputs changes anything in memory
        for each in _rebind_files(path):
            data = json.loads(each.read_text())
            if isinstance(data, dict) and "roadmaps" in data and "milestones" not in data:
                print(f"✗ {each.name} is an old-format pointer registry, not a "
                      "phase array; rebind moves phase arrays only. Convert it "
                      "with goblin-scout:rebind-roadbook's single-file conversion.")
                return 2
            # every file is checked before any is written, the dry run
            # included, so a refusal never leaves the project half moved
            _refuse_if_stamped_newer(data)
            if _canonical_text(data) != each.read_text():
                noncanonical.add(each)
            files.append((each, data))
    except (ValueError, RoadbookError) as exc:
        print(f"✗ {exc}")
        return 2
    root = project_root(path)
    moves = []  # (source, target) project files, deduplicated
    stale = []  # (left, current): a 2.x chart beside the one that replaced it
    if args.outputs:
        # read before _rebind_outputs pops any `artefact` it moves
        claimed = {os.path.normpath(ph[ARTEFACT_KEY]) for _each, data in files
                   for ph in _phases(data)
                   if isinstance(ph, dict) and isinstance(ph.get(ARTEFACT_KEY), str)}
        for each, data in files:
            found, left = _rebind_outputs(each, data, root, claimed)
            moves.extend(found)
            stale.extend(left)
        moves.append((root / LEGACY_OVERVIEW, root / OVERVIEW))
        seen = set()
        moves = [(s, t) for s, t in moves
                 if s.exists() and s not in seen and not seen.add(s)]
    shown = lambda p: p.relative_to(root).as_posix()
    renamed = [each for each, _data in files if each.name in LEGACY_NAMES]
    plan = [f"{_shown(each)} -> .claude/{LEGACY_NAMES[each.name]}" for each in renamed] \
        + [f"{shown(s)} -> {shown(t)}" for s, t in moves]
    left_lines = [f"{shown(left)} is stale: {shown(current)} is the chart now; "
                  "delete it once nothing links to it" for left, current in stale]
    if not plan:
        if left_lines:
            print("nothing to move; left as it is:")
            for line in left_lines:
                print(f"  {line}")
            return 0
        print("nothing to rebind: the roadbook and its outputs already use "
              "the roadbook names")
        return 0
    for _source, target in moves:
        if target.exists():
            print(f"✗ {shown(target)} already exists; nothing moved")
            return 1
    for each, data in files:
        if (each in renamed or args.outputs) and each in noncanonical and not args.reformat:
            print(f"✗ {each.name} is not in canonical form (tab-indented, "
                  "ensure_ascii off, trailing newline); rebind would reformat "
                  "the whole file, which hides the move from git's rename "
                  "detection. Re-run with --reformat to accept that.")
            return 1
    if args.dry_run:
        print("would move:")
        for line in plan:
            print(f"  {line}")
        for line in left_lines:
            print(f"  {line}")
        return 0
    for each, data in files:
        if each in renamed or args.outputs:
            _write_roadbook(each, data, pin=not args.outputs, siblings=False)
    for source, target in moves:
        _move_file(source, target)
    print("moved:")
    for line in plan:
        print(f"  {line}")
    for line in left_lines:
        print(f"  {line}")
    if moves:
        print("note: links elsewhere in the project still name the old "
              "paths; search for them before committing the move")
    return 0


# A pull that removes more than half of at least this many mirrored waypoints is
# refused unless --allow-removals is passed.
SHRINK_FLOOR = 4


def cmd_pull(args) -> int:
    import _roadbook_jira as jira
    path, data, phase = _pull_target(args)
    source = phase_source(phase)
    if source.get("kind") != "jira":
        print(f"✗ source kind {source.get('kind')!r} cannot be pulled")
        return 1
    if args.issues:
        try:
            raw = json.loads(Path(args.issues).read_text())
        except (OSError, ValueError) as exc:
            print(f"✗ could not read --issues {args.issues}: {exc}")
            return 2
        raw = raw.get("issues", []) if isinstance(raw, dict) else raw
    else:
        raw = jira.fetch_issues(source, jira.credentials(project_root(path)))
    issues = [jira.normalise(i) for i in raw]
    if all(issue["epic"] for issue in issues):
        # Nothing but epics (or nothing at all) is not a mirror: merging it
        # would drop every mirrored task and strand local ones in M0.
        query = f" (jql: {source['jql']})" if source.get("jql") else ""
        print(f"✗ Jira project {source.get('project')}{query} returned no "
              "tasks; nothing written. If the project really is empty now, "
              "delete the phase from the local roadbook file to start again")
        return 1
    trial = copy.deepcopy(phase)
    report = jira.merge(trial, issues, TASK_FIELD_ORDER)
    dropped, previous = len(report["removed"]), report["previous"]
    shrink = None
    if previous >= SHRINK_FLOOR and dropped * 2 > previous \
            and not getattr(args, "allow_removals", False):
        # A truncated answer (a narrowed jql, a lost permission, a failed
        # page) looks like a project that lost most of its tasks. Tasks come
        # back on the next full pull, but a local task whose milestone
        # emptied stays in M0, so the write needs an explicit say-so.
        shrink = (f"this pull would remove {dropped} of {previous} mirrored "
                  "tasks; pass --allow-removals if Jira really lost them")
        if not args.dry_run:
            print(f"✗ {shrink}; nothing written (`--dry-run` lists the "
                  "waypoints)")
            return 1
    phase.clear()
    phase.update(trial)
    if not args.dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path = _write_roadbook(path, data)
    for line in jira.describe(report, phase.get("name"), args.dry_run):
        print(line)
    if shrink:
        print(f"note: a real pull would be refused: {shrink}")
    if not args.dry_run:
        git, rel = _git_at_toplevel(path)
        if git is not None and git("check-ignore", "-q", rel) is None:
            print(f"note: {rel} is not ignored by git. It is a mirror of "
                  f"Jira plus your own waypoints; add `{rel}` to .gitignore "
                  "unless the team has agreed to share it.")
    return 0


def cmd_hook(args) -> int:
    """Claude Code hook entry point. A hook must never fail the session, so
    every error is swallowed and the exit code is always 0."""
    try:
        import _roadbook_hooks
        _roadbook_hooks.run(args.event, sys.stdin, Path(__file__).resolve(),
                           build_ready)
    except Exception:  # noqa: BLE001 - a hook must never break the session
        pass
    return 0


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="roadbook.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("path", nargs="?", default=None,
                        help="roadbook.json path or project dir (optional)")
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
                    help="refresh an existing chart after writing")

    sp = common(sub.add_parser("stats", help="status counts"))
    sp.add_argument("--json", action="store_true")

    sp = common(sub.add_parser("graph", help="dependency graph"))
    sp.add_argument("--json", action="store_true",
                    help="JSON output (the default)")
    sp.add_argument("--mermaid", action="store_true",
                    help="complete Mermaid source incl. classDefs")
    sp.add_argument("--direction", choices=["LR", "TD"], default="LR")
    sp.add_argument("--omit-done", action="store_true",
                    help="drop done and out_of_scope waypoints and the milestones "
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
        "open", help="every waypoint not done or out of scope")))

    sp = common(sub.add_parser("render", help="write the HTML chart"))
    sp.add_argument("--out", default=None, help="output path override")

    sp = sub.add_parser(
        "config", help="set a per-phase option in roadbook.json")
    sp.add_argument("key", choices=[ARTEFACT_KEY],
                    help="artefact: where render writes the chart, "
                         "relative to the project root")
    sp.add_argument("value", nargs="?", default=None,
                    help="the value to set (omit with --clear)")
    common(sp)
    sp.add_argument("--clear", action="store_true",
                    help="remove the key, restoring the default")
    sp.add_argument("--reformat", action="store_true",
                    help="allow rewriting a non-canonically-formatted file")

    def claim_common(sp):
        # the task id comes first so `claim 2RT.17 path` never reads the id
        # as the path
        sp.add_argument("id", help="waypoint id")
        common(sp)
        sp.add_argument("--reformat", action="store_true",
                        help="allow rewriting a non-canonically-formatted file")
        return sp

    sp = claim_common(sub.add_parser(
        "claim", help="start a trail: record that a scout has started a waypoint"))
    sp.add_argument("--assignee", default=None,
                    help="who is doing it (asked for, never inferred)")
    sp.add_argument("--reassign", action="store_true",
                    help="allow --assignee to replace a different assignee")
    sp.add_argument("--date", default=None,
                    help="start date YYYY-MM-DD (default today)")

    sp = claim_common(sub.add_parser(
        "assign", help="set or clear which scout will take a waypoint, without starting it"))
    who = sp.add_mutually_exclusive_group(required=True)
    who.add_argument("--assignee", default=None,
                     help="who will do it (asked for, never inferred)")
    who.add_argument("--unassign", action="store_true",
                     help="clear the assignee")

    sp = claim_common(sub.add_parser(
        "end", help="record the date a done waypoint finished"))
    sp.add_argument("--date", default=None,
                    help="end date YYYY-MM-DD (default today)")
    sp.add_argument("--force", action="store_true",
                    help="overwrite an existing end date")

    sp = common(sub.add_parser(
        "backfill-ended",
        help="date done waypoints that lack `ended` from git history"))
    sp.add_argument("--dry-run", action="store_true", help="preview, no write")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--reformat", action="store_true",
                    help="allow rewriting a non-canonically-formatted file")

    sp = common(sub.add_parser(
        "stamp-ended",
        help="date the done waypoints a branch finished, before it merges"))
    sp.add_argument("--base", default="origin/main",
                    help="ref to take the merge-base with (default origin/main)")
    sp.add_argument("--pr", type=int, default=None,
                    help="also stamp done waypoints whose `pr` is this number")
    sp.add_argument("--date", default=None,
                    help="end date YYYY-MM-DD (default today)")
    sp.add_argument("--dry-run", action="store_true", help="preview, no write")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--reformat", action="store_true",
                    help="allow rewriting a non-canonically-formatted file")

    sp = claim_common(sub.add_parser("release", help="drop a trail without finishing it"))
    sp.add_argument("--unassign", action="store_true",
                    help="also clear the assignee")

    sp = common(sub.add_parser(
        "pull", help="refresh a mirrored phase from its tracker (read-only)"))
    sp.add_argument("--project", default=None,
                    help="Jira project key; starts a mirrored phase when "
                         "nothing here mirrors that project yet")
    sp.add_argument("--name", default=None,
                    help="name for a phase --project creates (default: the key)")
    sp.add_argument("--issues", default=None,
                    help="read issues from a saved Jira search response "
                         "instead of calling Jira")
    sp.add_argument("--allow-removals", action="store_true",
                    help="write a pull that removes more than half of the "
                         "mirrored waypoints (refused by default)")
    sp.add_argument("--dry-run", action="store_true", help="preview, no write")

    sp = common(sub.add_parser(
        "rebind",
        help="move a 2.x roadmaps.json to roadbook.json now, without waiting "
             "for the first write"))
    sp.add_argument("--outputs", action="store_true",
                    help="also move the chart, the projections and the prose "
                         "overview from their 2.x default names to the "
                         "roadbook's")
    sp.add_argument("--reformat", action="store_true",
                    help="allow rewriting a non-canonically-formatted file")
    sp.add_argument("--dry-run", action="store_true", help="preview, no write")

    sp = sub.add_parser("hook", help="Claude Code hook entry point")
    sp.add_argument("event", choices=["session-start", "post-tool-use"])

    args = parser.parse_args(argv)
    commands = {
        "detect": cmd_detect,
        "validate": cmd_validate,
        "recompute": cmd_recompute,
        "stats": cmd_stats,
        "graph": cmd_graph,
        "ready": cmd_ready,
        "open": lambda a: cmd_ready(a, horizon="open"),
        "render": cmd_render,
        "config": cmd_config,
        "claim": cmd_claim,
        "assign": cmd_assign,
        "release": cmd_release,
        "end": cmd_end,
        "backfill-ended": cmd_backfill_ended,
        "stamp-ended": cmd_stamp_ended,
        "pull": cmd_pull,
        "rebind": cmd_rebind,
        "hook": cmd_hook,
    }
    try:
        return commands[args.cmd](args)
    except RoadbookError as exc:
        print(f"✗ {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
