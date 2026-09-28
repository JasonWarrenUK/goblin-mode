#!/usr/bin/env python3
"""Fixture tests for the roadmap system (_roadmap_core.py + roadmap.py).

Run from this directory: python3 -m unittest test_roadmap -v
Stdlib only. Each test builds a minimal phase dict; file-based behaviour
(detect, recompute writes) uses a TemporaryDirectory shaped like a project
root with .claude/roadmaps.json.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import roadmap
from _roadmap_core import (
    RoadmapError,
    active_phase,
    build_index,
    display_status,
    find_cycles,
    is_claimed,
    milestone_sinks,
    recompute_all,
)


def task(tid, status="todo", depends=None, soft=None, **extra):
    t = {"id": tid, "description": f"task {tid}", "status": status,
         "dependsOn": depends or []}
    if soft:
        t["softDependsOn"] = soft
    t.update(extra)
    return t


def phase(milestones, gates=None, name="Test Phase", **extra):
    p = {"name": name, "path": "docs/roadmaps/TEST.md",
         "externalGates": gates or [], "milestones": milestones}
    p.update(extra)
    return p


class RecomputePrecedence(unittest.TestCase):
    def compute(self, ph):
        return recompute_all(*build_index(ph))

    def test_done_deps_yield_todo(self):
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "done"), task("b", "blocked", ["a"])]}])
        self.assertEqual(self.compute(ph)["b"], "todo")

    def test_not_done_dep_blocks(self):
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("a"), task("b", "todo", ["a"])]}])
        self.assertEqual(self.compute(ph)["b"], "blocked")

    def test_precedence_deferred_beats_paused_beats_blocked(self):
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("p", "paused"),          # root-seeded, held
            task("d", "deferred"),        # root-seeded, held
            task("t"),                    # plain todo dep
            task("x", "todo", ["p", "t"]),
            task("y", "todo", ["p", "d"])]}])
        computed = self.compute(ph)
        self.assertEqual(computed["x"], "paused")
        self.assertEqual(computed["y"], "deferred")

    def test_out_of_scope_dep_is_satisfied(self):
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "out_of_scope"), task("b", "blocked", ["a"])]}])
        self.assertEqual(self.compute(ph)["b"], "todo")

    def test_held_seeds_not_recomputed(self):
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "done"),
            task("root_paused", "paused"),
            task("dep_paused", "paused", ["a"])]}])  # has deps => recomputable
        computed = self.compute(ph)
        self.assertEqual(computed["root_paused"], "paused")  # held as authored
        self.assertEqual(computed["dep_paused"], "todo")     # dep done => todo

    def test_milestone_dependency_propagates(self):
        ph = phase([
            {"id": "M1", "name": "m1", "tasks": [task("a")]},
            {"id": "M2", "name": "m2", "tasks": [task("b", "todo", ["M1"])]}])
        self.assertEqual(self.compute(ph)["b"], "blocked")

    def test_gate_imposes(self):
        ph = phase(
            [{"id": "M1", "name": "m", "tasks": [task("a", "todo", ["G1"])]}],
            gates=[{"id": "G1", "name": "g", "status": "todo",
                    "imposes": "paused", "blocks": ["a"]}])
        self.assertEqual(self.compute(ph)["a"], "paused")

    def test_bad_gate_imposes_degrades_to_blocked(self):
        ph = phase(
            [{"id": "M1", "name": "m", "tasks": [task("a", "todo", ["G1"])]}],
            gates=[{"id": "G1", "name": "g", "status": "todo",
                    "imposes": "nonsense", "blocks": ["a"]}])
        self.assertEqual(self.compute(ph)["a"], "blocked")

    def test_soft_dep_imposes_no_status(self):
        # b's only inbound edge is soft; it must stay todo, never blocked.
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("a"), task("b", "todo", soft=["a"])]}])
        self.assertEqual(self.compute(ph)["b"], "todo")


class Cycles(unittest.TestCase):
    def test_task_cycle_detected(self):
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "todo", ["b"]), task("b", "todo", ["a"])]}])
        tasks, milestones, _ = build_index(ph)
        cycles = find_cycles(tasks, milestones)
        self.assertEqual(len(cycles), 1)

    def test_milestone_level_cycle_detected(self):
        # a depends on M2; M2's member b depends on a: a -> M2 -> b -> a
        ph = phase([
            {"id": "M1", "name": "m1", "tasks": [task("a", "todo", ["M2"])]},
            {"id": "M2", "name": "m2", "tasks": [task("b", "todo", ["a"])]}])
        tasks, milestones, _ = build_index(ph)
        cycles = find_cycles(tasks, milestones)
        self.assertTrue(cycles, "milestone-level cycle should be detected")
        self.assertTrue(any("M2" in c for c in cycles))

    def test_acyclic_graph_is_clean(self):
        ph = phase([
            {"id": "M1", "name": "m1", "tasks": [
                task("a"), task("b", "blocked", ["a"])]},
            {"id": "M2", "name": "m2", "tasks": [task("c", "blocked", ["M1"])]}])
        tasks, milestones, _ = build_index(ph)
        self.assertEqual(find_cycles(tasks, milestones), [])

    def test_soft_cycle_is_not_a_cycle(self):
        # a --> b (hard) closed by b -.-> a (soft): find_cycles must ignore
        # softDependsOn entirely, since find_cycles only reads dependsOn.
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "todo", ["b"]), task("b", soft=["a"])]}])
        tasks, milestones, _ = build_index(ph)
        self.assertEqual(find_cycles(tasks, milestones), [])


class Sinks(unittest.TestCase):
    def test_sinks_ignore_cross_milestone_dependents(self):
        ph = phase([
            {"id": "M1", "name": "m1", "tasks": [
                task("a"), task("b", "blocked", ["a"])]},
            {"id": "M2", "name": "m2", "tasks": [task("c", "blocked", ["b"])]}])
        sinks = milestone_sinks(ph)
        self.assertEqual(sinks["M1"], ["b"])   # a feeds b in-milestone
        self.assertEqual(sinks["M2"], ["c"])

    def test_sinks_ignore_soft_dependents(self):
        # b's only in-milestone dependent (a) is soft, not hard: a stays a
        # sink. milestone_sinks reads dependsOn only.
        ph = phase([{"id": "M1", "name": "m1", "tasks": [
            task("a"), task("b", soft=["a"])]}])
        sinks = milestone_sinks(ph)
        self.assertEqual(sinks["M1"], ["a", "b"])


class ActivePhase(unittest.TestCase):
    def test_multiple_active_phases_raise(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [task("a")]}], name="P1"),
                phase([{"id": "M1", "name": "m", "tasks": [task("a")]}], name="P2")]
        with self.assertRaises(RoadmapError):
            active_phase(data)

    def test_selector_disambiguates(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [task("a")]}], name="P1"),
                phase([{"id": "M1", "name": "m", "tasks": [task("a")]}], name="P2")]
        self.assertEqual(active_phase(data, "P1")["name"], "P1")

    def test_archived_phases_skipped(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [task("a")]}],
                      name="P1", archived=True),
                phase([{"id": "M1", "name": "m", "tasks": [task("a")]}], name="P2")]
        self.assertEqual(active_phase(data)["name"], "P2")

    def test_pointer_registry_rejected(self):
        with self.assertRaises(RoadmapError):
            active_phase({"roadmaps": [{"path": "docs/x.md"}]})


class MalformedInput(unittest.TestCase):
    def test_missing_task_id_is_roadmap_error(self):
        ph = phase([{"id": "M1", "name": "m",
                     "tasks": [{"description": "no id", "status": "todo"}]}])
        with self.assertRaises(RoadmapError):
            build_index(ph)

    def test_missing_milestone_id_is_roadmap_error(self):
        ph = phase([{"name": "m", "tasks": [task("a")]}])
        with self.assertRaises(RoadmapError):
            build_index(ph)


class GateParity(unittest.TestCase):
    def test_validate_flags_missing_and_extra_blocks(self):
        ph = phase(
            [{"id": "M1", "name": "m", "tasks": [
                task("a", "blocked", ["G1"]), task("b")]}],
            gates=[{"id": "G1", "name": "g", "status": "todo",
                    "blocks": ["b"]}])   # missing a, extra b
        problems = roadmap._validate_phase(ph)
        self.assertTrue(any("blocks[] missing a" in p for p in problems))
        self.assertTrue(any("blocks[] lists b" in p for p in problems))


class Stats(unittest.TestCase):
    def test_invalid_status_reported_not_dropped(self):
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "done"), task("b", "in_progress")]}])
        stats = roadmap.build_stats(ph)
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["invalid"], ["b"])
        self.assertEqual(sum(stats["byStatus"].values()) + len(stats["invalid"]),
                         stats["total"])

    def test_milestone_state_and_completion_counts_added(self):
        ph = phase([
            {"id": "M1", "name": "done", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "live", "tasks": [
                task("b", "done"), task("c", "todo")]}])
        stats = roadmap.build_stats(ph)
        by_id = {m["id"]: m for m in stats["milestones"]}
        self.assertEqual(by_id["M1"]["state"], "done")
        self.assertEqual(by_id["M2"]["state"], "inProgress")
        self.assertEqual(stats["milestonesTotal"], 2)
        self.assertEqual(stats["milestonesDone"], 1)


class MilestoneState(unittest.TestCase):
    """Milestone-level derived state (distinct from task status): drives the
    artefact's Overview/Milestones colour and sort (see roadmap-conventions.md
    and library/templates/roadmap-artefact.html). Rule order: empty -> done
    -> deferred (tier cascade) -> deferred (member gate) -> inProgress ->
    blocked -> todo."""

    def test_in_progress_when_partially_done(self):
        self.assertEqual(
            roadmap.milestone_state({"todo": 1, "done": 1}, 50, total=2),
            "inProgress")

    def test_todo_when_nothing_started(self):
        self.assertEqual(
            roadmap.milestone_state({"todo": 2}, 0, total=2), "todo")

    def test_done_when_fully_done(self):
        self.assertEqual(
            roadmap.milestone_state({"done": 2}, 100, total=2), "done")

    def test_all_out_of_scope_is_done(self):
        # Struck-from-play (out_of_scope) still reads as done: nothing
        # actionable remains, whether it finished or was struck out.
        by_status = {"out_of_scope": 3}
        self.assertEqual(roadmap.milestone_state(by_status, 0, total=3), "done")

    def test_empty_milestone_is_flagged(self):
        # Zero tasks is a bug (see _validate_phase), never a legitimate
        # state: it must never read as todo/done and hide the problem.
        self.assertEqual(roadmap.milestone_state({}, 0, total=0), "empty")

    def test_in_progress_outranks_all_blocked(self):
        # Some done work with the rest blocked still reads as live and
        # moving, not stuck: inProgress (rule 4) outranks blocked (rule 5).
        by_status = {"done": 2, "blocked": 3}
        self.assertEqual(
            roadmap.milestone_state(by_status, 40, total=5), "inProgress")

    def test_blocked_when_every_unfinished_task_is_blocked(self):
        by_status = {"blocked": 2}
        self.assertEqual(
            roadmap.milestone_state(by_status, 0, total=2), "blocked")

    def test_claim_gives_in_progress_even_at_zero_done(self):
        by_status = {"todo": 2}
        self.assertEqual(
            roadmap.milestone_state(by_status, 0, total=2, in_progress=1),
            "inProgress")

    def test_deferred_when_a_lower_tier_is_not_done(self):
        by_status = {"todo": 2}
        self.assertEqual(
            roadmap.milestone_state(by_status, 0, total=2, tier=1,
                                    lower_tiers_done=False),
            "deferred")

    def test_lower_tiers_done_lets_tier_through_to_its_own_rules(self):
        by_status = {"done": 2}
        self.assertEqual(
            roadmap.milestone_state(by_status, 100, total=2, tier=1,
                                    lower_tiers_done=True),
            "done")

    def test_deferred_never_fires_for_tier_zero(self):
        # A Primary milestone has no lower tier to wait on: even with
        # lower_tiers_done=False (should never happen for tier 0 in
        # practice) tier>=1 is required for the deferred rule.
        by_status = {"todo": 2}
        self.assertEqual(
            roadmap.milestone_state(by_status, 0, total=2, tier=0,
                                    lower_tiers_done=False),
            "todo")

    def test_member_deferred_fires_without_a_tier(self):
        # A plain, untiered milestone (tier 0) can still shelve via a
        # deferred member; this reading needs no (Secondary)/(Tertiary)
        # suffix, unlike the tier-cascade deferred rule above.
        by_status = {"deferred": 4}
        self.assertEqual(
            roadmap.milestone_state(by_status, 0, total=4), "deferred")

    def test_member_deferred_outranks_done_percentage(self):
        # A milestone with one deferred task and nine done ones is still
        # "shelved" even at donePct 90: the deliberate call outranks
        # percentage, matching the reading main used before the tier
        # rewrite (rule 3 fires ahead of inProgress, rule 4).
        by_status = {"done": 9, "deferred": 1}
        self.assertEqual(
            roadmap.milestone_state(by_status, 90, total=10), "deferred")

    def test_member_deferred_never_fires_while_actionable_work_remains(self):
        # Five todo tasks are still live work to pick up, not a shelved
        # milestone: hiding them behind "deferred" would contradict
        # next-task-group's own ready-set, which still lists them.
        by_status = {"todo": 5, "deferred": 1}
        self.assertEqual(
            roadmap.milestone_state(by_status, 0, total=6), "todo")


class MilestoneTier(unittest.TestCase):
    def test_no_suffix_is_primary(self):
        self.assertEqual(roadmap.milestone_tier("Search"), 0)
        self.assertEqual(roadmap.milestone_tier(""), 0)

    def test_suffixes_in_order(self):
        self.assertEqual(roadmap.milestone_tier("Search (Secondary)"), 1)
        self.assertEqual(roadmap.milestone_tier("Search (Tertiary)"), 2)
        self.assertEqual(roadmap.milestone_tier("Search (Quaternary)"), 3)
        self.assertEqual(roadmap.milestone_tier("Search (Quinary)"), 4)

    def test_case_insensitive(self):
        self.assertEqual(roadmap.milestone_tier("Search (secondary)"), 1)
        self.assertEqual(roadmap.milestone_tier("Search (SECONDARY)"), 1)

    def test_suffix_must_be_trailing(self):
        self.assertEqual(roadmap.milestone_tier("(Secondary) is not this"), 0)


class MilestoneAllDone(unittest.TestCase):
    def test_empty_is_not_done(self):
        self.assertFalse(roadmap.milestone_all_done({}, 0))

    def test_all_done_or_out_of_scope(self):
        self.assertTrue(
            roadmap.milestone_all_done({"done": 1, "out_of_scope": 1}, 2))

    def test_one_actionable_task_is_not_done(self):
        self.assertFalse(
            roadmap.milestone_all_done({"done": 1, "todo": 1}, 2))


class BuildStatsTiers(unittest.TestCase):
    def test_cascade_defers_tertiary_while_secondary_is_open(self):
        ph = phase([
            {"id": "M1", "name": "Core", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "Extra (Secondary)", "tasks": [task("b")]},
            {"id": "M3", "name": "More (Tertiary)", "tasks": [task("c")]}])
        by_id = {m["id"]: m for m in roadmap.build_stats(ph)["milestones"]}
        self.assertEqual(by_id["M1"]["state"], "done")
        self.assertEqual(by_id["M2"]["state"], "todo")
        self.assertEqual(by_id["M3"]["state"], "deferred")

    def test_tertiary_opens_once_secondary_is_done(self):
        ph = phase([
            {"id": "M1", "name": "Core", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "Extra (Secondary)", "tasks": [task("b", "done")]},
            {"id": "M3", "name": "More (Tertiary)", "tasks": [task("c")]}])
        by_id = {m["id"]: m for m in roadmap.build_stats(ph)["milestones"]}
        self.assertEqual(by_id["M3"]["state"], "todo")

    def test_empty_milestone_reported_by_validate(self):
        ph = phase([{"id": "M1", "name": "Empty", "tasks": []}])
        problems = roadmap._validate_phase(ph)
        self.assertIn("M1: milestone has no tasks", problems)

    def test_empty_milestone_in_an_earlier_tier_never_blocks_the_cascade(self):
        # A bug (empty milestone) must never masquerade as "still in
        # progress" and freeze every later tier deferred forever: only a
        # non-empty, unfinished milestone should hold a tier open.
        ph = phase([
            {"id": "M1", "name": "Core", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "Whoops", "tasks": []},
            {"id": "M3", "name": "Extra (Secondary)", "tasks": [task("b")]}])
        by_id = {m["id"]: m for m in roadmap.build_stats(ph)["milestones"]}
        self.assertEqual(by_id["M2"]["state"], "empty")
        self.assertEqual(by_id["M3"]["state"], "todo")

    def test_milestones_carry_their_own_tier(self):
        # overview_layout() reads tier back from here rather than
        # re-deriving it from the name; a dropped field would silently
        # send it back to milestone_tier() and split the two computations.
        ph = phase([
            {"id": "M1", "name": "Core", "tasks": [task("a")]},
            {"id": "M2", "name": "Extra (Secondary)", "tasks": [task("b")]}])
        by_id = {m["id"]: m for m in roadmap.build_stats(ph)["milestones"]}
        self.assertEqual(by_id["M1"]["tier"], 0)
        self.assertEqual(by_id["M2"]["tier"], 1)


def _layout(ph):
    stats = roadmap.build_stats(ph)
    ready = roadmap.build_ready(ph)
    return roadmap.overview_layout(ph, stats, ready)


class OverviewLayout(unittest.TestCase):
    def test_flat_when_no_tiers(self):
        ph = phase([
            {"id": "M1", "name": "m1", "tasks": [task("a")]},
            {"id": "M2", "name": "m2", "tasks": [task("b", "done")]}])
        layout = _layout(ph)
        self.assertIsNone(layout["tiers"])
        self.assertEqual([m["id"] for m in layout["milestones"]], ["M1", "M2"])

    def test_sort_partial_then_zero_then_full_pct(self):
        ph = phase([
            {"id": "M1", "name": "full", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "zero", "tasks": [task("b")]},
            {"id": "M3", "name": "partial", "tasks": [
                task("c", "done"), task("d")]}])
        layout = _layout(ph)
        self.assertEqual([m["id"] for m in layout["milestones"]],
                         ["M3", "M2", "M1"])

    def test_sort_ties_break_by_tier_then_pct_then_id(self):
        ph = phase([
            {"id": "M2", "name": "b (Secondary)", "tasks": [task("x")]},
            {"id": "M1", "name": "a", "tasks": [task("y")]},
            {"id": "M10", "name": "c", "tasks": [task("z", "done"), task("w")]}])
        layout = _layout(ph)
        # M10 (partial, tier 0) first; then M1/M2 (0%): tier 0 before tier 1
        self.assertEqual([m["id"] for m in layout["milestones"]],
                         ["M10", "M1", "M2"])

    def test_sort_natural_milestone_id_order(self):
        ph = phase([
            {"id": "M10", "name": "ten", "tasks": [task("a")]},
            {"id": "M2", "name": "two", "tasks": [task("b")]}])
        layout = _layout(ph)
        self.assertEqual([m["id"] for m in layout["milestones"]], ["M2", "M10"])

    def test_devs_sorted_distinct_including_done_tasks(self):
        ph = phase([{"id": "M1", "name": "m1", "tasks": [
            task("a", "done", assignee="jaz"),
            task("b", assignee="Jason"),
            task("c", assignee="jaz")]}])
        layout = _layout(ph)
        self.assertEqual(layout["milestones"][0]["devs"], ["Jason", "jaz"])

    def test_tier_group_expanded_only_when_open_and_active(self):
        ph = phase([
            {"id": "M1", "name": "Core", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "Extra (Secondary)", "tasks": [task("b")]}])
        layout = _layout(ph)
        groups = {g["tier"]: g for g in layout["tiers"]}
        self.assertTrue(groups[1]["expanded"])  # open (M1 done) + b is ready

    def test_tier_group_collapsed_when_not_yet_open_even_with_ready_task(self):
        ph = phase([
            {"id": "M1", "name": "Core", "tasks": [task("a")]},
            {"id": "M2", "name": "Extra (Secondary)", "tasks": [
                task("b", "todo", depends=[])]}])
        layout = _layout(ph)
        groups = {g["tier"]: g for g in layout["tiers"]}
        self.assertFalse(groups[1]["expanded"])

    def test_empty_milestone_never_blocks_a_later_tier_from_opening(self):
        # Regression: an empty (bugged) tier-0 milestone must not read as
        # "still unfinished" and permanently keep tier 1 collapsed/deferred.
        ph = phase([
            {"id": "M1", "name": "Core", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "Whoops", "tasks": []},
            {"id": "M3", "name": "Extra (Secondary)", "tasks": [task("b")]}])
        layout = _layout(ph)
        groups = {g["tier"]: g for g in layout["tiers"]}
        self.assertTrue(groups[1]["expanded"])

    def test_tier_group_order_expanded_then_open_then_done(self):
        ph = phase([
            {"id": "M1", "name": "Core", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "Live (Secondary)", "tasks": [task("b")]},
            {"id": "M3", "name": "Done (Tertiary)", "tasks": [task("c", "done", depends=["M2"])]}])
        layout = _layout(ph)
        self.assertEqual([g["tier"] for g in layout["tiers"]], [1, 0, 2])

    def test_milestone_ids_within_group_follow_the_sort_order(self):
        ph = phase([
            {"id": "M1", "name": "a (Secondary)", "tasks": [task("x")]},
            {"id": "M2", "name": "b (Secondary)", "tasks": [
                task("y", "done"), task("z")]}])
        layout = _layout(ph)
        group = layout["tiers"][0]
        self.assertEqual(group["milestoneIds"], ["M2", "M1"])


class DevColour(unittest.TestCase):
    def test_stable_across_calls(self):
        self.assertEqual(roadmap.dev_colour("jason"), roadmap.dev_colour("jason"))

    def test_case_and_whitespace_insensitive(self):
        self.assertEqual(roadmap.dev_colour("Jason"), roadmap.dev_colour(" jason "))

    def test_empty_or_none_yields_none(self):
        self.assertIsNone(roadmap.dev_colour(""))
        self.assertIsNone(roadmap.dev_colour(None))

    def test_stable_across_process_hash_seed(self):
        # dev_colour must use a stable digest, not builtin hash(), which is
        # salted per-process via PYTHONHASHSEED; simulate that by asserting
        # the result never depends on the current process's hash seed at all
        # (crc32 doesn't read PYTHONHASHSEED, so this holds trivially once
        # implemented correctly, and would flake under repeated runs with
        # builtin hash()).
        script = ("import sys; sys.path.insert(0, %r); import roadmap; "
                  "print(roadmap.dev_colour('jason'))" % str(Path(__file__).parent))
        results = set()
        for seed in ("1", "99999"):
            out = subprocess.run(
                [sys.executable, "-c", script],
                env={**os.environ, "PYTHONHASHSEED": seed},
                capture_output=True, text=True, check=True)
            results.add(out.stdout.strip())
        self.assertEqual(len(results), 1, f"colour varied across hash seeds: {results}")


class Ready(unittest.TestCase):
    def test_candidates_and_signals(self):
        ph = phase([
            {"id": "M1", "name": "m1", "tasks": [
                task("a"),                         # ready, unblocks b and c
                task("b", "blocked", ["a"])]},
            {"id": "M2", "name": "m2", "tasks": [
                task("c", "blocked", ["M1"]),
                task("d")]}])                      # ready, unblocks nothing
        ready = roadmap.build_ready(ph)
        ids = [c["id"] for c in ready["candidates"]]
        self.assertEqual(set(ids), {"a", "d"})
        by_id = {c["id"]: c for c in ready["candidates"]}
        # a unblocks b directly and c through M1 membership
        self.assertEqual(by_id["a"]["transitiveUnblocks"], 2)
        self.assertEqual(by_id["d"]["transitiveUnblocks"], 0)
        self.assertEqual(ids[0], "a")  # highest leverage first
        self.assertTrue(by_id["d"]["isMilestoneSink"])

    def test_assignee_projected_when_set_and_empty_when_absent(self):
        ph = phase([{"id": "M1", "name": "m1", "tasks": [
            task("a", assignee="jason"),
            task("b")]}])
        by_id = {c["id"]: c for c in roadmap.build_ready(ph)["candidates"]}
        self.assertEqual(by_id["a"]["assignee"], "jason")
        self.assertEqual(by_id["b"]["assignee"], "")

    def test_groups_cover_every_candidate_once_per_pivot(self):
        ph = phase([
            {"id": "M1", "name": "m1", "tasks": [
                task("1IN.1", assignee="jaz"), task("1UI.2")]},
            {"id": "M2", "name": "m2", "tasks": [
                task("2IN.1", assignee="Jason"), task("odd")]}])
        candidates = roadmap.build_ready(ph)["candidates"]
        groups = roadmap.ready_groups(candidates)
        self.assertEqual(groups["milestone"],
                         {"M1": ["1IN.1", "1UI.2"], "M2": ["2IN.1", "odd"]})
        self.assertEqual(groups["topic"],
                         {"IN": ["1IN.1", "2IN.1"], "UI": ["1UI.2"], "other": ["odd"]})
        self.assertEqual(list(groups["topic"]), ["IN", "UI", "other"])
        self.assertEqual(groups["dev"],
                         {"jaz": ["1IN.1"], "Jason": ["2IN.1"],
                          "unassigned": ["1UI.2", "odd"]})
        self.assertEqual(list(groups["dev"]), ["Jason", "jaz", "unassigned"])
        for pivot in groups.values():
            flat = [tid for ids in pivot.values() for tid in ids]
            self.assertEqual(sorted(flat), sorted(c["id"] for c in candidates))


class Mermaid(unittest.TestCase):
    def setUp(self):
        self.ph = phase([
            {"id": "M1", "name": "First", "tasks": [
                task("a", "done"), task("b", "todo", ["a"])]},
            {"id": "M2", "name": "Second", "tasks": [
                task("c", "blocked", ["M1"])]}])

    def test_classdefs_follow_graph_line(self):
        src = roadmap.mermaid_source(self.ph)
        lines = src.splitlines()
        self.assertTrue(lines[0].startswith("graph LR"))
        self.assertTrue(all(l.strip().startswith("classDef")
                            for l in lines[1:1 + len(roadmap.STATUS_STYLE)]))

    def test_status_classes_and_terminal_edges(self):
        src = roadmap.mermaid_source(self.ph)
        self.assertIn("class a done", src)
        self.assertIn("class b todo", src)
        self.assertIn("class c blocked", src)
        self.assertIn("b --> M1", src)      # sink into milestone (terminal)
        self.assertIn("M1 --> c", src)      # milestone as dependency
        self.assertNotIn("M1 --> b", src)   # no entry edges

    def test_omit_done_drops_tasks_and_spent_milestones(self):
        ph = phase([
            {"id": "M1", "name": "Spent", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "Live", "tasks": [task("b", "blocked", ["M1"])]}])
        src = roadmap.mermaid_source(ph, omit_done=True)
        self.assertNotIn('a["', src)
        self.assertNotIn("M1", src)
        self.assertIn('b["', src)

    def test_out_of_scope_gets_its_classdef(self):
        ph = phase([{"id": "M1", "name": "m",
                     "tasks": [task("a", "out_of_scope")]}])
        src = roadmap.mermaid_source(ph)
        self.assertIn("classDef outOfScope", src)
        self.assertIn("class a outOfScope", src)

    def test_vars_palette_uses_custom_properties(self):
        src = roadmap.mermaid_source(self.ph, palette="vars")
        self.assertIn("fill:var(--color-todo-bg)", src)

    def test_orphan_gates_are_not_drawn(self):
        ph = phase(
            [{"id": "M1", "name": "m", "tasks": [task("a", "todo", ["G1"])]}],
            gates=[{"id": "G1", "name": "live", "status": "todo",
                    "blocks": ["a"]},
                   {"id": "G2", "name": "resolved", "status": "todo",
                    "blocks": []}])
        src = roadmap.mermaid_source(ph)
        self.assertIn('G1["', src)
        self.assertNotIn('G2["', src)

    def test_soft_edge_renders_dotted(self):
        # a -.-> b is soft-only; c --> d is hard-only, so both arrow forms
        # are asserted against unambiguous pairs.
        ph = phase([{"id": "M1", "name": "m1", "tasks": [
            task("a"), task("b", soft=["a"])]},
            {"id": "M2", "name": "m2", "tasks": [
                task("c"), task("d", "todo", ["c"])]}])
        src = roadmap.mermaid_source(ph)
        self.assertIn("a -.-> b", src)
        self.assertIn("c --> d", src)
        self.assertNotIn("c -.-> d", src)

    def test_nodes_declared_in_topological_order(self):
        src = roadmap.mermaid_source(self.ph)
        lines = src.splitlines()

        def decl(nid):
            return next(i for i, l in enumerate(lines)
                        if l.strip().startswith(f'{nid}["'))
        self.assertLess(decl("a"), decl("b"))   # a --> b
        self.assertLess(decl("b"), decl("M1"))  # sink into milestone
        self.assertLess(decl("M1"), decl("c"))  # milestone as dependency


class GraphDirection(unittest.TestCase):
    """choose_direction() picks by estimated width only: the artefact's
    diagram shell has no height cap (the page scrolls past a tall diagram)
    but its width is bounded by the layout column, measured against the
    real template rather than assumed. A long thin chain is narrow in TD
    (one node wide) and would sprawl sideways in LR (every layer end to
    end), so it picks TD; a wide fan is the mirror case and picks LR."""

    def _chain(self, depth=12):
        tasks = [task("t0")]
        for i in range(1, depth):
            tasks.append(task(f"t{i}", depends=[f"t{i - 1}"]))
        return phase([{"id": "M1", "name": "chain", "tasks": tasks}])

    def _fan(self, width=15):
        tasks = [task("root")]
        for i in range(width):
            tasks.append(task(f"c{i}", depends=["root"]))
        return phase([{"id": "M1", "name": "fan", "tasks": tasks}])

    def test_long_thin_chain_picks_td(self):
        self.assertEqual(roadmap.choose_direction(self._chain()), "TD")

    def test_wide_fan_picks_lr(self):
        self.assertEqual(roadmap.choose_direction(self._fan()), "LR")

    def test_deterministic_across_repeated_calls(self):
        ph = self._fan()
        results = {roadmap.choose_direction(ph) for _ in range(5)}
        self.assertEqual(len(results), 1)

    def test_empty_graph_defaults_to_td(self):
        ph = phase([{"id": "M1", "name": "m", "tasks": [task("a", "done")]}])
        self.assertEqual(roadmap.choose_direction(ph), "TD")

    def test_longest_path_layers_assigns_by_depth(self):
        ids = ["a", "b", "c"]
        edges = [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}]
        layers = roadmap._longest_path_layers(ids, edges)
        self.assertEqual(layers, {"a": 0, "b": 1, "c": 2})

    def test_longest_path_layers_takes_the_deepest_predecessor(self):
        # d depends on both a (layer 0) and c (layer 1, via b); its own
        # layer must be one past the deepest predecessor, not the shallowest.
        ids = ["a", "b", "c", "d"]
        edges = [{"from": "a", "to": "b"}, {"from": "b", "to": "c"},
                 {"from": "a", "to": "d"}, {"from": "c", "to": "d"}]
        layers = roadmap._longest_path_layers(ids, edges)
        self.assertEqual(layers["d"], 3)


class FileBased(unittest.TestCase):
    def _project(self, data):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / ".claude").mkdir()
        jp = root / ".claude" / "roadmaps.json"
        jp.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n")
        return root, jp

    def test_recompute_writes_atomically_and_only_statuses(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "done"), task("b", "blocked", ["a"])]}])]
        root, jp = self._project(data)
        rc = roadmap.main(["recompute", str(jp)])
        self.assertEqual(rc, 0)
        after = json.loads(jp.read_text())
        self.assertEqual(after[0]["milestones"][0]["tasks"][1]["status"], "todo")

    def test_recompute_refuses_to_reformat(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "done"), task("b", "blocked", ["a"])]}])]
        root, jp = self._project(data)
        jp.write_text(json.dumps(data, indent=2) + "\n")  # space-indented
        rc = roadmap.main(["recompute", str(jp)])
        self.assertEqual(rc, 1)
        self.assertIn("blocked", jp.read_text())  # untouched
        rc = roadmap.main(["recompute", str(jp), "--reformat"])
        self.assertEqual(rc, 0)
        self.assertEqual(
            json.loads(jp.read_text())[0]["milestones"][0]["tasks"][1]["status"],
            "todo")

    def test_recompute_refuses_on_cycle(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "todo", ["b"]), task("b", "todo", ["a"])]}])]
        root, jp = self._project(data)
        self.assertEqual(roadmap.main(["recompute", str(jp)]), 1)

    def test_detect_rich_old_and_missing(self):
        rich = [phase([{"id": "M1", "name": "m", "tasks": [task("a")]}])]
        root, jp = self._project(rich)
        self.assertEqual(roadmap.main(["detect", str(jp)]), 0)

        old = {"roadmaps": [{"path": "docs/roadmaps/mvp.md"}]}
        root2, jp2 = self._project(old)
        self.assertEqual(roadmap.main(["detect", str(jp2)]), 3)

        self.assertEqual(roadmap.main(["detect", "/nonexistent/nowhere"]), 2)

    def test_detect_old_via_md_anchors(self):
        rich = [phase([{"id": "M1", "name": "m", "tasks": [task("a")]}])]
        root, jp = self._project(rich)
        md = root / "docs" / "roadmaps"
        md.mkdir(parents=True)
        (md / "TEST.md").write_text('# Old\n<a name="m1-todo"></a>\n')
        self.assertEqual(roadmap.main(["detect", str(jp)]), 3)

    def test_validate_clean_and_dirty(self):
        clean = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "done"), task("b", "todo", ["a"])]}])]
        _root, jp = self._project(clean)
        self.assertEqual(roadmap.main(["validate", str(jp)]), 0)

        dirty = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a"), task("b", "todo", ["a"])]}])]  # b should be blocked
        _root2, jp2 = self._project(dirty)
        self.assertEqual(roadmap.main(["validate", str(jp2)]), 1)

    def test_render_writes_artefact(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "done"), task("b", "todo", ["a"])]}], name="My Phase")]
        root, jp = self._project(data)
        rc = roadmap.main(["render", str(jp)])
        self.assertEqual(rc, 0)
        out = root / "docs" / "artefacts" / "roadmap-my-phase.html"
        self.assertTrue(out.exists())
        html = out.read_text()
        self.assertIn("My Phase", html)
        self.assertNotIn("%%DATA%%", html)
        self.assertNotIn("%%TITLE%%", html)
        self.assertIn("roadmap-data", html)

    def test_soft_edges_survive_recompute_and_reconsecutive_graph_runs(self):
        # The regression this prevents: hand-authored dotted edges wiped by
        # a subsequent reconcile. softDependsOn must survive `recompute`
        # (which rewrites the file) and `graph --mermaid` must emit the
        # same dotted edge identically across two consecutive calls.
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "done"),
            task("b", "todo", soft=["a"])]}])]
        root, jp = self._project(data)
        self.assertEqual(roadmap.main(["recompute", str(jp)]), 0)
        after = json.loads(jp.read_text())
        self.assertEqual(
            after[0]["milestones"][0]["tasks"][1]["softDependsOn"], ["a"])

        _path, reloaded = roadmap.load(str(jp))
        ph = roadmap.active_phase(reloaded)
        first = roadmap.mermaid_source(ph)
        second = roadmap.mermaid_source(ph)
        self.assertIn("a -.-> b", first)
        self.assertEqual(first, second)

    def test_render_includes_assignee_when_set(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "todo", assignee="jason")]}], name="My Phase")]
        root, jp = self._project(data)
        rc = roadmap.main(["render", str(jp)])
        self.assertEqual(rc, 0)
        out = root / "docs" / "artefacts" / "roadmap-my-phase.html"
        html = out.read_text()
        self.assertIn("jason", html)  # assignee reaches the embedded data blob

    def _blob(self, out):
        html = out.read_text()
        start = html.find('<script id="roadmap-data"')
        start = html.find(">", start) + 1
        end = html.find("</script>", start)
        return json.loads(html[start:end])

    def test_render_project_field_explicit_and_fallback(self):
        # Explicit `project` field wins outright.
        explicit = [phase([{"id": "M1", "name": "m", "tasks": [task("a")]}],
                          name="My Phase", project="Iris")]
        root, jp = self._project(explicit)
        roadmap.main(["render", str(jp)])
        out = root / "docs" / "artefacts" / "roadmap-my-phase.html"
        self.assertEqual(self._blob(out)["project"], "Iris")

        # Absent: falls back to the project root directory name.
        implicit = [phase([{"id": "M1", "name": "m", "tasks": [task("a")]}],
                          name="My Phase")]
        root2, jp2 = self._project(implicit)
        roadmap.main(["render", str(jp2)])
        out2 = root2 / "docs" / "artefacts" / "roadmap-my-phase.html"
        self.assertEqual(self._blob(out2)["project"], root2.name)

    def test_render_dev_colours_in_blob(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", assignee="jason"), task("b", assignee="jaz"),
            task("c")]}], name="My Phase")]
        root, jp = self._project(data)
        roadmap.main(["render", str(jp)])
        out = root / "docs" / "artefacts" / "roadmap-my-phase.html"
        blob = self._blob(out)
        self.assertEqual(set(blob["devColours"]), {"jason", "jaz"})
        self.assertNotEqual(blob["devColours"]["jason"], blob["devColours"]["jaz"])

    def test_render_is_byte_deterministic_across_hash_seeds(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "done", assignee="jason"),
            task("b", "todo", ["a"], assignee="jaz")]}], name="My Phase")]
        root, jp = self._project(data)
        outs = []
        for seed in ("1", "99999"):
            out_path = root / f"out-{seed}.html"
            env = {**os.environ, "PYTHONHASHSEED": seed}
            subprocess.run(
                [sys.executable, str(Path(roadmap.__file__)), "render",
                 str(jp), "--out", str(out_path)],
                env=env, capture_output=True, text=True, check=True)
            outs.append(out_path.read_text())
        # Strip the one field that legitimately varies (the timestamp).
        stripped = [re.sub(r'"generated": "[^"]*"', '"generated": "X"', o)
                    for o in outs]
        self.assertEqual(stripped[0], stripped[1])


class Claims(unittest.TestCase):
    """A claim is the `started` field; views show it, recompute never reads
    it (see roadmap-conventions.md, Claims)."""

    def test_display_status_table(self):
        claimed = {"started": "2026-09-25"}
        for status, shown in [("todo", "in_progress"), ("blocked", "in_progress"),
                              ("paused", "paused"), ("deferred", "deferred"),
                              ("done", "done"), ("out_of_scope", "out_of_scope")]:
            self.assertEqual(display_status(claimed, status), shown)
            self.assertEqual(display_status({}, status), status)

    def test_an_empty_started_is_no_claim(self):
        self.assertFalse(is_claimed({"started": ""}))
        self.assertTrue(is_claimed({"started": "2026-09-25"}))

    def test_a_claim_changes_no_status(self):
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("a", started="2026-09-25"), task("b", "blocked", ["a"])]}])
        t, m, g = build_index(ph)
        self.assertEqual(recompute_all(t, m, g), {"a": "todo", "b": "blocked"})
        self.assertEqual(roadmap._validate_phase(ph), [])


class ClaimViews(unittest.TestCase):
    def _phase(self):
        return phase([
            {"id": "M1", "name": "m1", "tasks": [
                task("a", started="2026-09-20", assignee="jaz"),
                task("b", "blocked", ["a"]),
                task("c")]},
            {"id": "M2", "name": "m2", "tasks": [
                task("d", "done"), task("e", started="2026-09-21")]}])

    def test_ready_leaves_claims_out_and_lists_them_oldest_first(self):
        ready = roadmap.build_ready(self._phase())
        self.assertEqual([c["id"] for c in ready["candidates"]], ["c"])
        self.assertEqual(
            [(c["id"], c["status"], c["display"], c["assignee"], c["started"])
             for c in ready["claimed"]],
            [("a", "todo", "in_progress", "jaz", "2026-09-20"),
             ("e", "todo", "in_progress", "", "2026-09-21")])

    def test_a_claim_on_a_reblocked_task_stays_visible(self):
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("a"), task("b", "blocked", ["a"], started="2026-09-20")]}])
        claim = roadmap.build_ready(ph)["claimed"][0]
        self.assertEqual((claim["status"], claim["display"]), ("blocked", "in_progress"))
        t, m, g = build_index(ph)
        self.assertEqual(recompute_all(t, m, g)["b"], "blocked")

    def test_stats_count_claims_as_an_overlay(self):
        stats = roadmap.build_stats(self._phase())
        self.assertEqual(stats["inProgress"], 2)
        self.assertEqual(sum(stats["byStatus"].values()), stats["total"])
        by_id = {m["id"]: m for m in stats["milestones"]}
        self.assertEqual(by_id["M1"]["inProgress"], 1)
        # a is claimed (in_progress) and b/c aren't all blocked, so the
        # claim wins: inProgress outranks "all unfinished tasks blocked".
        self.assertEqual(by_id["M1"]["state"], "inProgress")
        self.assertEqual(by_id["M2"]["state"], "inProgress")

    def test_a_claim_starts_a_milestone_at_zero_percent(self):
        self.assertEqual(
            roadmap.milestone_state({"todo": 2}, 0, total=2, in_progress=1),
            "inProgress")
        self.assertEqual(
            roadmap.milestone_state({"todo": 2}, 0, total=2), "todo")
        self.assertEqual(
            roadmap.milestone_state({"todo": 1, "blocked": 1}, 0, total=2,
                                    in_progress=1),
            "inProgress")

    def test_mermaid_classes_and_marks_claimed_tasks(self):
        src = roadmap.mermaid_source(self._phase())
        self.assertIn("classDef inProgress", src)
        self.assertIn('\ta["a: task a ▸"]', src)
        self.assertIn('\tc["c: task c"]', src)
        self.assertIn("\tclass a,e inProgress", src)

    def test_marker_fits_inside_the_label_limit(self):
        long = "x" * 80
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("a", started="2026-09-20", description=long)]}])
        line = next(l for l in roadmap.mermaid_source(ph).splitlines()
                    if l.startswith('\ta["'))
        label = line[len('\ta["'):-len('"]')]
        self.assertEqual(len(label), roadmap._LABEL_MAX)
        self.assertTrue(label.endswith("… ▸"))

    def test_dependency_chips_get_the_display_status(self):
        kinds = roadmap._dep_kinds(self._phase())
        self.assertEqual(kinds["a"]["display"], "in_progress")
        self.assertEqual(kinds["c"]["display"], "todo")


class ClaimCommand(unittest.TestCase):
    def _project(self, tasks):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        jp = Path(tmp.name) / ".claude" / "roadmaps.json"
        jp.parent.mkdir()
        data = [phase([{"id": "M1", "name": "m", "tasks": tasks}])]
        jp.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n")
        return jp

    def _task(self, jp, tid):
        tasks = json.loads(jp.read_text())[0]["milestones"][0]["tasks"]
        return next(t for t in tasks if t["id"] == tid)

    def _run(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = roadmap.main(list(argv))
        return rc, out.getvalue()

    def test_claim_writes_started_in_field_order(self):
        jp = self._project([task("a", notes="n", pr=12)])
        rc, _ = self._run("claim", "a", str(jp), "--date", "2026-09-25",
                          "--assignee", "Jaz")
        self.assertEqual(rc, 0)
        self.assertEqual(list(self._task(jp, "a")),
                         ["id", "description", "status", "dependsOn", "notes",
                          "assignee", "started", "pr"])
        self.assertEqual(self._task(jp, "a")["started"], "2026-09-25")

    def test_claim_then_release_is_byte_identical(self):
        jp = self._project([task("a", notes="n", pr=12), task("b", "blocked", ["a"])])
        before = jp.read_text()
        self.assertEqual(self._run("claim", "a", str(jp))[0], 0)
        self.assertNotEqual(jp.read_text(), before)
        self.assertEqual(self._run("release", "a", str(jp))[0], 0)
        self.assertEqual(jp.read_text(), before)

    def test_release_unassign_undoes_a_claim_that_assigned(self):
        jp = self._project([task("a")])
        before = jp.read_text()
        self._run("claim", "a", str(jp), "--assignee", "Max")
        self._run("release", "a", str(jp), "--unassign")
        self.assertEqual(jp.read_text(), before)

    def test_claim_refusals_leave_the_file_alone(self):
        jp = self._project([task("a", assignee="Jaz"), task("b", "blocked", ["a"]),
                            task("c", started="2026-09-01")])
        before = jp.read_text()
        for argv, needle in [
                (["claim", "b"], "blocked, not todo"),
                (["claim", "c"], "already claimed"),
                (["claim", "a", "--assignee", "Max"], "--reassign"),
                (["claim", "zz"], "no task"),
                (["claim", "a", "--date", "25/09/2026"], "YYYY-MM-DD")]:
            rc, out = self._run(argv[0], argv[1], str(jp), *argv[2:])
            self.assertEqual(rc, 1, argv)
            self.assertIn(needle, out, argv)
        self.assertEqual(jp.read_text(), before)

    def test_same_name_keeps_its_spelling_and_reassign_replaces(self):
        jp = self._project([task("a", assignee="Jaz")])
        self.assertEqual(self._run("claim", "a", str(jp), "--assignee", "jaz")[0], 0)
        self.assertEqual(self._task(jp, "a")["assignee"], "Jaz")
        self._run("release", "a", str(jp))
        self.assertEqual(
            self._run("claim", "a", str(jp), "--assignee", "Max", "--reassign")[0], 0)
        self.assertEqual(self._task(jp, "a")["assignee"], "Max")

    def test_claim_refuses_cycles_and_non_canonical_files(self):
        jp = self._project([task("a", "todo", ["b"]), task("b", "todo", ["a"])])
        self.assertEqual(self._run("claim", "a", str(jp))[0], 1)
        jp2 = self._project([task("a")])
        jp2.write_text(json.dumps(json.loads(jp2.read_text()), indent=2) + "\n")
        self.assertEqual(self._run("claim", "a", str(jp2))[0], 1)
        self.assertEqual(self._run("claim", "a", str(jp2), "--reformat")[0], 0)

    def test_claim_and_validate_refuse_a_week_date(self):
        rc, out = self._run("claim", "a", str(self._project([task("a")])), "--date", "2026-W39-5")
        self.assertEqual(rc, 1)
        self.assertIn("YYYY-MM-DD", out)
        ph = phase([{"id": "M1", "name": "m", "tasks": [task("a", started="2026-W39-5")]}])
        self.assertTrue(any("not a YYYY-MM-DD date" in p for p in roadmap._validate_phase(ph)))

    def test_release_refuses_an_unclaimed_task(self):
        rc, out = self._run("release", "a", str(self._project([task("a")])))
        self.assertEqual(rc, 1)
        self.assertIn("not claimed", out)

    def test_validate_checks_started_and_points_at_claims(self):
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("a", started="soon"), task("b", "in_progress")]}])
        problems = roadmap._validate_phase(ph)
        self.assertTrue(any("started 'soon'" in p for p in problems))
        self.assertTrue(any("run roadmap.py claim" in p for p in problems))


@unittest.skipUnless(shutil.which("git"), "git not installed")
class Hooks(unittest.TestCase):
    """The hook entry points against real repositories: a bare origin, a
    clone on main and a roadmap with two ready tasks, one blocked and one
    done (a done task is what a wrong base would misread as a claim)."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        # HOME and no system config keep the machine's git config out of it
        self.env = {**os.environ, "HOME": str(self.root), "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        self.git(self.root, "init", "-q", "--bare", "origin.git")
        self.git(self.root, "clone", "-q", "origin.git", "repo")
        self.repo = self.root / "repo"
        self.git(self.repo, "checkout", "-q", "-b", "main")
        (self.repo / ".claude").mkdir()
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", assignee="Jaz"), task("b"), task("c", "blocked", ["a"]),
            task("d", "done")]}])]
        (self.repo / ".claude" / "roadmaps.json").write_text(
            json.dumps(data, indent="\t", ensure_ascii=False) + "\n")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-qm", "init")
        self.git(self.repo, "push", "-q", "-u", "origin", "main")
        self.git(self.repo, "remote", "set-head", "origin", "main")

    def git(self, cwd, *args):
        return subprocess.run(["git", "-C", str(cwd), *args], env=self.env,
                              capture_output=True, text=True, check=True).stdout.strip()

    def cli(self, *args, stdin=""):
        return subprocess.run([sys.executable, str(Path(roadmap.__file__)), *args],
                              input=stdin, env=self.env, cwd=self.root,
                              capture_output=True, text=True)

    def hook(self, event, cwd, **extra):
        done = self.cli("hook", event, stdin=json.dumps({"cwd": str(cwd), **extra}))
        self.assertEqual((done.returncode, done.stderr), (0, ""))
        return done.stdout

    def context(self, out):
        return json.loads(out)["hookSpecificOutput"]["additionalContext"]

    def test_the_default_branch_is_silent(self):
        self.assertEqual(self.hook("session-start", self.repo), "")

    def test_a_new_branch_is_nudged_once(self):
        self.git(self.repo, "checkout", "-q", "-b", "feat/x")
        text = self.context(self.hook("post-tool-use", self.repo))
        self.assertIn("branch `feat/x`", text)
        self.assertIn("a task a (Jaz); b task b.", text)
        self.assertNotIn("c task c", text)
        self.assertEqual(
            self.git(self.repo, "config", "--get", "branch.feat/x.roadmapClaim"), "asked")
        self.assertEqual(self.hook("post-tool-use", self.repo), "")

    def test_session_start_nudges_until_the_branch_claims(self):
        self.git(self.repo, "checkout", "-q", "-b", "feat/x")
        self.assertIn("claims no roadmap task", self.hook("session-start", self.repo))
        self.assertEqual(self.cli("claim", "b", str(self.repo / ".claude" / "roadmaps.json")).returncode, 0)
        self.assertEqual(self.hook("session-start", self.repo).strip(),
                         "Roadmap: branch `feat/x` claims b.")

    def test_a_worktree_claim_targets_the_worktree(self):
        wt = self.root / "wt"
        self.git(self.repo, "worktree", "add", "-q", str(wt), "-b", "feat/y")
        text = self.context(self.hook("post-tool-use", self.repo))
        self.assertIn(f"claim <ID> {wt / '.claude' / 'roadmaps.json'}", text)
        self.assertIn(f"git -C {wt} commit", text)
        self.assertNotIn(str(self.repo / ".claude"), text)

    def test_a_decline_silences_the_branch(self):
        self.git(self.repo, "checkout", "-q", "-b", "chore/x")
        self.git(self.repo, "config", "branch.chore/x.roadmapClaim", "none")
        self.assertEqual(self.hook("session-start", self.repo), "")
        self.assertEqual(self.hook("post-tool-use", self.repo), "")

    def test_a_local_copy_of_a_remote_branch_is_not_nudged(self):
        self.git(self.repo, "checkout", "-q", "-b", "feat/remote")
        self.git(self.repo, "push", "-q", "origin", "feat/remote")
        self.git(self.repo, "checkout", "-q", "main")
        self.git(self.repo, "branch", "-q", "-D", "feat/remote")
        self.git(self.repo, "checkout", "-q", "feat/remote")
        self.assertEqual(self.hook("post-tool-use", self.repo), "")

    def test_subagents_and_repos_without_a_roadmap_are_silent(self):
        self.git(self.repo, "checkout", "-q", "-b", "feat/z")
        self.assertEqual(self.hook("post-tool-use", self.repo, agent_id="a1"), "")
        plain = self.root / "plain"
        self.git(self.root, "init", "-q", "plain")
        self.git(plain, "commit", "-q", "--allow-empty", "-m", "x")
        self.git(plain, "checkout", "-q", "-b", "feat/q")
        self.assertEqual(self.hook("post-tool-use", plain), "")
        self.assertEqual(self.hook("session-start", plain), "")

    def test_a_dangling_origin_head_falls_back_to_main(self):
        self.git(self.repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/gone")
        self.assertEqual(self.hook("session-start", self.repo), "")
        self.git(self.repo, "checkout", "-q", "-b", "feat/x")
        self.assertIn("claims no roadmap task", self.hook("session-start", self.repo))

    def test_no_merge_base_is_silent_not_a_false_claim(self):
        self.git(self.repo, "checkout", "-q", "--orphan", "feat/orphan")
        self.git(self.repo, "commit", "-qm", "unrelated history")
        self.assertEqual(self.hook("session-start", self.repo), "")
        self.assertEqual(self.hook("post-tool-use", self.repo), "")

    def test_claude_code_subagent_worktrees_are_not_nudged(self):
        wt = self.root / "agent-wt"
        self.git(self.repo, "worktree", "add", "-q", "--no-track", "-B",
                 "worktree-agent-a1b2c3", str(wt), "origin/main")
        self.assertEqual(self.hook("post-tool-use", self.repo), "")
        self.assertEqual(self.hook("session-start", wt), "")

    def test_a_session_start_nudge_is_not_repeated_by_the_next_git_command(self):
        self.git(self.repo, "checkout", "-q", "-b", "feat/fresh")
        self.assertIn("claims no roadmap task", self.hook("session-start", self.repo))
        self.assertEqual(self.hook("post-tool-use", self.repo), "")

    def test_bad_input_never_fails_the_hook(self):
        done = self.cli("hook", "post-tool-use", stdin="not json")
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))


if __name__ == "__main__":
    unittest.main()
