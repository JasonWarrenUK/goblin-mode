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

    def test_out_of_scope_leaves_done_and_total(self):
        ph = phase([
            {"id": "M1", "name": "mixed", "tasks": [
                task("a", "done"), task("b"), task("c", "out_of_scope")]},
            {"id": "M2", "name": "plain", "tasks": [
                task("d", "done"), task("e", "out_of_scope"),
                task("f", "out_of_scope")]}])
        stats = roadmap.build_stats(ph)
        by_id = {m["id"]: m for m in stats["milestones"]}
        self.assertEqual((by_id["M1"]["done"], by_id["M1"]["inScope"],
                          by_id["M1"]["donePct"]), (1, 2, 50))
        self.assertEqual((by_id["M2"]["done"], by_id["M2"]["inScope"],
                          by_id["M2"]["donePct"]), (1, 1, 100))
        self.assertEqual((stats["byStatus"]["done"], stats["inScope"],
                          stats["donePct"]), (2, 3, 67))
        # total stays raw: the ROADMAP_OVERVIEW header count reads it
        self.assertEqual(stats["total"], 6)
        self.assertEqual(by_id["M1"]["total"], 3)

    def test_milestone_struck_out_whole_has_nothing_in_scope(self):
        ph = phase([
            {"id": "M1", "name": "struck", "tasks": [
                task("a", "out_of_scope"), task("b", "out_of_scope")]},
            {"id": "M2", "name": "zero", "tasks": [task("c")]}])
        stats = roadmap.build_stats(ph)
        struck = stats["milestones"][0]
        # donePct reads 100, not 0/0's 0: the card's progress bar fills to
        # match its `done` colour and the sort needs no special case
        self.assertEqual((struck["inScope"], struck["donePct"],
                          struck["state"]), (0, 100, "done"))
        # nothing left to do, so it sorts after the untouched milestone
        self.assertEqual([m["id"] for m in _layout(ph)["milestones"]],
                         ["M2", "M1"])

    def test_phase_and_tier_struck_out_whole_read_100(self):
        ph = phase([
            {"id": "M1", "name": "struck", "tasks": [task("a", "out_of_scope")]},
            {"id": "M2", "name": "also struck (Secondary)", "tasks": [
                task("b", "out_of_scope")]}])
        stats = roadmap.build_stats(ph)
        self.assertEqual((stats["inScope"], stats["donePct"]), (0, 100))
        tiers = _layout(ph)["tiers"]
        self.assertEqual([g["stats"]["donePct"] for g in tiers], [100, 100])

    def test_empty_milestone_done_pct_stays_zero(self):
        # no tasks at all is a bug (state `empty`), never finished work
        ph = phase([{"id": "M1", "name": "empty", "tasks": []}])
        m = roadmap.build_stats(ph)["milestones"][0]
        self.assertEqual((m["donePct"], m["state"]), (0, "empty"))

    def test_human_stats_print_in_scope_fractions(self):
        ph = phase([{"id": "M1", "name": "mixed", "tasks": [
            task("a", "done"), task("b"), task("c", "out_of_scope")]}])
        text = roadmap._human_stats(roadmap.build_stats(ph))
        self.assertIn("1/2 done (50%)", text)
        self.assertIn("M1   1/2", text)
        self.assertNotIn("/3", text)


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

    def test_blocked_outranks_in_progress_when_nothing_can_be_picked_up(self):
        # Done work does not soften a stuck milestone: every remaining
        # task is blocked, so blocked (rule 4) outranks inProgress (rule 5).
        self.assertEqual(
            roadmap.milestone_state({"done": 2, "blocked": 3}, 40, total=5),
            "blocked")
        self.assertEqual(
            roadmap.milestone_state({"done": 7, "blocked": 1}, 88, total=8),
            "blocked")

    def test_blocked_sets_out_of_scope_tasks_aside(self):
        by_status = {"done": 1, "blocked": 2, "out_of_scope": 1}
        self.assertEqual(
            roadmap.milestone_state(by_status, 33, total=4), "blocked")

    def test_one_actionable_task_keeps_a_milestone_in_progress(self):
        by_status = {"done": 2, "blocked": 3, "todo": 1}
        self.assertEqual(
            roadmap.milestone_state(by_status, 33, total=6), "inProgress")

    def test_a_claim_on_a_blocked_task_keeps_a_milestone_in_progress(self):
        by_status = {"done": 2, "blocked": 3}
        self.assertEqual(
            roadmap.milestone_state(by_status, 40, total=5, in_progress=1),
            "inProgress")

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
        # A Core milestone has no lower tier to wait on: even with
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
    def test_no_suffix_is_core(self):
        self.assertEqual(roadmap.milestone_tier("Search"), 0)
        self.assertEqual(roadmap.milestone_tier(""), 0)

    def test_labels_spell_core_secondary_tertiary(self):
        self.assertEqual([roadmap.tier_label(t) for t in range(3)],
                         ["Core", "Secondary", "Tertiary"])

    def test_layout_labels_never_say_primary(self):
        ph = phase([
            {"id": "M1", "name": "a", "tasks": [task("x")]},
            {"id": "M2", "name": "b (Secondary)", "tasks": [task("y")]}])
        layout = _layout(ph)
        self.assertEqual(
            {g["tier"]: g["tierLabel"] for g in layout["tiers"]},
            {0: "Core", 1: "Secondary"})
        self.assertNotIn("Primary", json.dumps(layout))

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

    def test_sort_puts_a_stuck_milestone_behind_every_actionable_one(self):
        ph = phase([
            {"id": "M1", "name": "stuck", "tasks": [
                task("a", "done"), task("b", "blocked", ["M3"])]},
            {"id": "M2", "name": "zero", "tasks": [task("c")]},
            {"id": "M3", "name": "partial", "tasks": [
                task("d", "done"), task("e")]},
            {"id": "M4", "name": "full", "tasks": [task("f", "done")]},
            {"id": "M5", "name": "stuck at zero", "tasks": [
                task("g", "blocked", ["M3"])]}])
        layout = _layout(ph)
        self.assertEqual([m["id"] for m in layout["milestones"]],
                         ["M3", "M2", "M1", "M5", "M4"])
        by_id = {m["id"]: m["state"] for m in layout["milestones"]}
        self.assertEqual((by_id["M1"], by_id["M5"]), ("blocked", "blocked"))

    def test_sort_reads_state_so_a_tier_deferred_stuck_milestone_sorts_deferred(self):
        # M2 is stuck on its own terms, but the tier cascade colours it
        # `deferred` while Core still has open work; it must sort beside its
        # 0% Secondary sibling (tier, then -pct, then id), not behind it in
        # the stuck bucket. Position follows colour by construction.
        ph = phase([
            {"id": "M1", "name": "core", "tasks": [task("a", "done"), task("b")]},
            {"id": "M2", "name": "stuck (Secondary)", "tasks": [
                task("c", "blocked", ["b"])]},
            {"id": "M3", "name": "zero (Secondary)", "tasks": [task("d")]},
            {"id": "M4", "name": "full", "tasks": [task("e", "done")]}])
        layout = _layout(ph)
        self.assertEqual([m["id"] for m in layout["milestones"]],
                         ["M1", "M2", "M3", "M4"])
        self.assertEqual(layout["milestones"][1]["state"], "deferred")

    def test_sort_keeps_a_claimed_blocked_milestone_with_the_partial_ones(self):
        ph = phase([
            {"id": "M1", "name": "claimed", "tasks": [
                task("a", "done"),
                task("b", "blocked", ["c"], started="2026-09-20")]},
            {"id": "M2", "name": "zero", "tasks": [task("c")]}])
        layout = _layout(ph)
        self.assertEqual([m["id"] for m in layout["milestones"]], ["M1", "M2"])
        self.assertEqual(layout["milestones"][0]["state"], "inProgress")

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

    def test_tier_group_carries_its_own_readout(self):
        ph = phase([
            {"id": "M1", "name": "a", "tasks": [task("p", "done")]},
            {"id": "M2", "name": "b", "tasks": [
                task("q", "done"), task("r"), task("s", "out_of_scope")]},
            {"id": "M3", "name": "c (Secondary)", "tasks": [
                task("t", "blocked", ["M1", "M2"]), task("u", "blocked", ["t"])]}])
        layout = _layout(ph)
        groups = {g["tier"]: g["stats"] for g in layout["tiers"]}
        self.assertEqual(groups[0], {
            "done": 2, "inScope": 3, "donePct": 67,
            "milestonesDone": 1, "milestonesTotal": 2})
        self.assertEqual(groups[1], {
            "done": 0, "inScope": 2, "donePct": 0,
            "milestonesDone": 0, "milestonesTotal": 1})

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

    def test_unblock_split_now_partly_later(self):
        ph = phase([
            {"id": "M1", "name": "m1", "tasks": [
                task("x"),                              # candidate under test
                task("y"),                              # a second prerequisite, still open
                task("only", "blocked", ["x"]),         # waits on x alone: now
                task("both", "blocked", ["x", "y"]),    # also waits on y: partly
                task("deep", "blocked", ["only"]),      # one hop further: later
                task("gone", "done", ["x"])]},          # closed: counted nowhere
            {"id": "M2", "name": "m2", "tasks": [
                task("viaM", "blocked", ["M1"])]}])     # waits on all of M1, so a direct dependent: partly
        by_id = {c["id"]: c for c in roadmap.build_ready(ph)["candidates"]}
        x = by_id["x"]
        self.assertEqual(x["unblocksNow"], 1)           # only
        self.assertEqual(x["unblocksPartly"], 2)        # both, viaM
        self.assertEqual(x["unblocksLater"], 1)         # deep
        self.assertEqual(by_id["y"]["unblocksNow"], 0)
        self.assertEqual(by_id["y"]["unblocksPartly"], 2)

    def test_soft_milestone_member_does_not_unblock_milestone_dependents(self):
        ph = phase([
            {"id": "M1", "name": "m1", "tasks": [
                task("a"),
                {**task("s"), "softMilestone": True}]},
            {"id": "M2", "name": "m2", "tasks": [
                task("n", "blocked", ["M1"]),
                task("k", "blocked", ["n"]),
                task("direct", "blocked", ["s", "M1"])]}])  # lists s itself: still counted
        by_id = {c["id"]: c for c in roadmap.build_ready(ph)["candidates"]}
        s = by_id["s"]
        self.assertEqual((s["unblocksNow"], s["unblocksPartly"], s["unblocksLater"]),
                         (0, 1, 0))                      # direct only
        self.assertEqual(s["transitiveUnblocks"], 1)
        a = by_id["a"]
        self.assertEqual((a["unblocksNow"], a["unblocksPartly"], a["unblocksLater"]),
                         (1, 1, 1))                      # n now, direct partly, k later

    def test_unblock_via_milestone_membership_counts_as_now(self):
        ph = phase([
            {"id": "M1", "name": "m1", "tasks": [task("last")]},
            {"id": "M2", "name": "m2", "tasks": [task("next", "blocked", ["M1"])]}])
        c = roadmap.build_ready(ph)["candidates"][0]
        self.assertEqual((c["unblocksNow"], c["unblocksPartly"], c["unblocksLater"]),
                         (1, 0, 0))

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


class ReadyFilters(unittest.TestCase):
    """--milestones / --tiers narrowing for `ready` and `open`."""

    def _phase(self):
        return phase([
            {"id": "M1", "name": "Core one", "tasks": [
                task("a"), task("b", "blocked", ["a"]),
                task("c", started="2026-09-25", assignee="Jaz")]},
            {"id": "M2", "name": "Core two", "tasks": [
                task("d"), task("e", "done")]},
            {"id": "M3", "name": "Extras (Secondary)", "tasks": [
                task("f", "blocked", ["M1"])]}])

    def test_within_none_when_no_filter(self):
        self.assertIsNone(roadmap.resolve_within(self._phase()))

    def test_milestones_narrow_ready_and_claimed(self):
        ph = self._phase()
        within = roadmap.resolve_within(ph, milestones=["m1"])
        ready = roadmap.build_ready(ph, within=within)
        self.assertEqual([c["id"] for c in ready["candidates"]], ["a"])
        self.assertEqual([c["id"] for c in ready["claimed"]], ["c"])

    def test_tier_words_select_every_milestone_in_the_tier(self):
        ph = self._phase()
        self.assertEqual(roadmap.resolve_within(ph, tiers=["core"]), {"M1", "M2"})
        self.assertEqual(roadmap.resolve_within(ph, tiers=["Secondary"]), {"M3"})

    def test_focus_is_the_underway_tier(self):
        ph = self._phase()
        self.assertEqual(roadmap.resolve_within(ph, tiers=["focus"]), {"M1", "M2"})

    def test_focus_moves_up_when_core_is_done(self):
        ph = phase([
            {"id": "M1", "name": "Core", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "More (Secondary)", "tasks": [task("b", "blocked", ["M1"])]}])
        self.assertEqual(roadmap.resolve_within(ph, tiers=["focus"]), {"M2"})

    def test_focus_errors_when_nothing_is_underway(self):
        ph = phase([{"id": "M1", "name": "Core", "tasks": [task("a", "done")]}])
        with self.assertRaises(RoadmapError):
            roadmap.resolve_within(ph, tiers=["focus"])

    def test_unknown_milestone_and_tier_error(self):
        ph = self._phase()
        with self.assertRaisesRegex(RoadmapError, "M9"):
            roadmap.resolve_within(ph, milestones=["M9"])
        with self.assertRaisesRegex(RoadmapError, "tertiary"):
            roadmap.resolve_within(ph, tiers=["tertiary"])

    def test_milestones_and_tiers_are_mutually_exclusive(self):
        with self.assertRaises(RoadmapError):
            roadmap.resolve_within(self._phase(), milestones=["M1"], tiers=["core"])

    def test_candidates_carry_tier(self):
        ph = self._phase()
        opened = roadmap.build_ready(ph, horizon="open")
        by_id = {c["id"]: c for c in opened["candidates"]}
        self.assertEqual(by_id["f"]["tierLabel"], "Secondary")
        self.assertEqual(by_id["a"]["tierLabel"], "Core")

    def test_open_horizon_includes_blocked_and_claimed_but_not_done(self):
        ph = self._phase()
        opened = roadmap.build_ready(ph, horizon="open")
        self.assertEqual({c["id"] for c in opened["candidates"]},
                         {"a", "b", "c", "d", "f"})
        self.assertEqual(opened["claimed"], [])
        by_id = {c["id"]: c for c in opened["candidates"]}
        self.assertEqual(by_id["c"]["display"], "in_progress")
        self.assertEqual(by_id["c"]["started"], "2026-09-25")
        self.assertEqual(by_id["b"]["status"], "blocked")

    def test_open_with_tier_filter(self):
        ph = self._phase()
        within = roadmap.resolve_within(ph, tiers=["secondary"])
        opened = roadmap.build_ready(ph, within=within, horizon="open")
        self.assertEqual([c["id"] for c in opened["candidates"]], ["f"])


class ReadyFilterCli(unittest.TestCase):
    def _project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        jp = Path(tmp.name) / ".claude" / "roadmaps.json"
        jp.parent.mkdir()
        data = [phase([
            {"id": "M1", "name": "Core", "tasks": [task("a")]},
            {"id": "M2", "name": "More (Secondary)", "tasks": [task("b")]}])]
        jp.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n")
        return jp

    def _run(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = roadmap.main(list(argv))
        return rc, out.getvalue()

    def test_ready_json_milestone_filter(self):
        rc, out = self._run("ready", str(self._project()), "--json", "--milestones", "M2")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual([c["id"] for c in data["candidates"]], ["b"])
        self.assertEqual(data["groups"]["milestone"], {"M2": ["b"]})

    def test_open_json_focus(self):
        rc, out = self._run("open", str(self._project()), "--json", "--tiers", "focus")
        self.assertEqual(rc, 0)
        self.assertEqual([c["id"] for c in json.loads(out)["candidates"]], ["a"])

    def test_invalid_filter_exits_2(self):
        rc, out = self._run("ready", str(self._project()), "--milestones", "M9")
        self.assertEqual(rc, 2)
        self.assertIn("M9", out)


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

    def test_omit_done_drops_out_of_scope_tasks_and_their_edges(self):
        ph = phase([
            {"id": "M1", "name": "Mixed", "tasks": [
                task("a", "out_of_scope"), task("b", "todo", ["a"])]},
            {"id": "M2", "name": "Next", "tasks": [task("c", "blocked", ["M1"])]}])
        src = roadmap.mermaid_source(ph, omit_done=True)
        self.assertNotIn('a["', src)
        self.assertNotIn("a -->", src)
        self.assertNotIn("class a ", src)
        self.assertIn('b["', src)
        self.assertIn("b --> M1", src)

    def test_omit_done_drops_a_milestone_of_only_out_of_scope_tasks(self):
        ph = phase([
            {"id": "M1", "name": "Struck", "tasks": [task("a", "out_of_scope")]},
            {"id": "M2", "name": "Live", "tasks": [task("b")]}])
        src = roadmap.mermaid_source(ph, omit_done=True)
        self.assertNotIn("M1", src)
        self.assertNotIn('a["', src)
        self.assertIn('b["', src)

    def test_omit_done_drops_a_tier_of_done_and_out_of_scope_whole(self):
        ph = phase([
            {"id": "M1", "name": "Core work", "tasks": [
                task("a", "done"), task("w", "out_of_scope")]},
            {"id": "M2", "name": "More (Secondary)", "tasks": [task("b")]}])
        inside, _ = _subgraphs(roadmap.mermaid_source(ph, omit_done=True))
        self.assertEqual(list(inside), ["tier1"])

    def test_the_full_graph_still_draws_out_of_scope_tasks(self):
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "out_of_scope"), task("b")]}])
        self.assertIn('a["', roadmap.mermaid_source(ph))

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


def _subgraphs(src):
    """{subgraph id: (label, [node ids declared inside])} from Mermaid
    source, plus the ids of any node declared outside every subgraph."""
    inside, outside, current = {}, [], None
    for line in src.splitlines():
        text = line.strip()
        opened = re.match(r'subgraph (\w+)\["(.*)"\]$', text)
        node = re.match(r'([\w.]+)\["', text)
        if opened:
            current = opened.group(1)
            inside[current] = (opened.group(2), [])
        elif text == "end":
            current = None
        elif node and current:
            inside[current][1].append(node.group(1))
        elif node:
            outside.append(node.group(1))
    return inside, outside


class MermaidTiers(unittest.TestCase):
    def setUp(self):
        self.ph = phase(
            [{"id": "M1", "name": "Core work", "tasks": [
                task("a", "done"), task("b", "todo", ["a"])]},
             {"id": "M2", "name": "More (Secondary)", "tasks": [
                 task("c", "deferred", ["M1", "G1"]),
                 task("d", "blocked", ["c"])]},
             {"id": "M3", "name": "Last (Tertiary)", "tasks": [
                 task("e", "deferred", ["M2", "G1"])]}],
            gates=[{"id": "G1", "name": "release", "status": "external",
                    "imposes": "deferred", "blocks": ["c", "e"]}])

    def test_every_node_sits_inside_its_tier(self):
        inside, outside = _subgraphs(roadmap.mermaid_source(self.ph))
        self.assertEqual(outside, [])
        self.assertEqual(list(inside), ["tier0", "tier1", "tier2"])
        self.assertEqual(sorted(inside["tier0"][1]), ["M1", "a", "b"])
        self.assertEqual(sorted(inside["tier2"][1]), ["M3", "e"])

    def test_gate_sits_in_the_lowest_tier_it_gates(self):
        inside, _ = _subgraphs(roadmap.mermaid_source(self.ph))
        self.assertEqual(sorted(inside["tier1"][1]), ["G1", "M2", "c", "d"])

    def test_labels_name_the_tier_and_its_state(self):
        inside, _ = _subgraphs(roadmap.mermaid_source(self.ph))
        self.assertEqual([label for label, _ in inside.values()],
                         ["Core · underway", "Secondary · deferred",
                          "Tertiary · deferred"])

    def test_tier_classes_follow_the_state(self):
        src = roadmap.mermaid_source(self.ph)
        self.assertIn("\tclass tier0 tierUnderway", src)
        self.assertIn("\tclass tier1,tier2 tierDeferred", src)

    def test_classdefs_still_follow_the_graph_line(self):
        lines = roadmap.mermaid_source(self.ph).splitlines()
        count = len(roadmap.STATUS_STYLE) + len(roadmap.TIER_STYLE)
        self.assertTrue(all(l.strip().startswith("classDef")
                            for l in lines[1:1 + count]))
        self.assertTrue(lines[1 + count].strip().startswith("subgraph"))

    def test_edges_come_after_every_subgraph(self):
        lines = roadmap.mermaid_source(self.ph).splitlines()
        last_end = max(i for i, l in enumerate(lines) if l.strip() == "end")
        first_edge = min(i for i, l in enumerate(lines) if "-->" in l)
        self.assertGreater(first_edge, last_end)

    def test_a_finished_tier_reads_done_in_the_full_graph(self):
        ph = phase([
            {"id": "M1", "name": "Core work", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "More (Secondary)", "tasks": [
                task("b", "todo", ["M1"])]}])
        inside, _ = _subgraphs(roadmap.mermaid_source(ph))
        self.assertEqual([label for label, _ in inside.values()],
                         ["Core · done", "Secondary · underway"])
        self.assertIn("\tclass tier0,tier1 tierUnderway",
                      roadmap.mermaid_source(ph))

    def test_omit_done_drops_a_finished_tier_whole(self):
        ph = phase([
            {"id": "M1", "name": "Core work", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "More (Secondary)", "tasks": [task("b")]}])
        inside, outside = _subgraphs(
            roadmap.mermaid_source(ph, omit_done=True))
        self.assertEqual(list(inside), ["tier1"])
        self.assertEqual(outside, [])

    def test_untiered_phase_draws_no_subgraph(self):
        ph = phase([
            {"id": "M1", "name": "First", "tasks": [task("a")]},
            {"id": "M2", "name": "Second", "tasks": [
                task("b", "blocked", ["M1"])]}])
        src = roadmap.mermaid_source(ph)
        self.assertNotIn("subgraph", src)
        self.assertNotIn("classDef tier", src)
        self.assertNotIn("\tend", src)

    def test_vars_palette_names_the_tier_properties(self):
        src = roadmap.mermaid_source(self.ph, palette="vars")
        self.assertIn("fill:var(--color-tier-underway-bg)", src)
        self.assertIn("fill:var(--color-tier-deferred-bg)", src)


class TierStates(unittest.TestCase):
    def _states(self, ph):
        return roadmap.tier_states(roadmap.build_stats(ph)["milestones"])

    def test_deferred_while_a_lower_tier_is_unfinished(self):
        ph = phase([
            {"id": "M1", "name": "a", "tasks": [task("x")]},
            {"id": "M2", "name": "b (Secondary)", "tasks": [task("y")]},
            {"id": "M3", "name": "c (Tertiary)", "tasks": [task("z")]}])
        self.assertEqual(self._states(ph),
                         {0: "underway", 1: "deferred", 2: "deferred"})

    def test_underway_once_every_lower_tier_is_done(self):
        ph = phase([
            {"id": "M1", "name": "a", "tasks": [
                task("x", "done"), task("w", "out_of_scope")]},
            {"id": "M2", "name": "b (Secondary)", "tasks": [task("y")]},
            {"id": "M3", "name": "c (Tertiary)", "tasks": [task("z")]}])
        self.assertEqual(self._states(ph),
                         {0: "done", 1: "underway", 2: "deferred"})

    def test_an_empty_milestone_never_holds_a_tier_back(self):
        ph = phase([
            {"id": "M1", "name": "a", "tasks": [task("x", "done")]},
            {"id": "M2", "name": "whoops", "tasks": []},
            {"id": "M3", "name": "b (Secondary)", "tasks": [task("y")]}])
        self.assertEqual(self._states(ph), {0: "done", 1: "underway"})


def _luminance(colour):
    channels = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
              for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(one, other):
    hi, lo = sorted((_luminance(one), _luminance(other)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _template_palettes():
    """[(selector, {custom property: hex})] for each theme block of the
    artefact template: the light root and its two dark counterparts."""
    html = (Path(roadmap.__file__).resolve().parent.parent
            / "templates" / "roadmap-artefact.html").read_text()
    css = html[html.index("<style>"):html.index("</style>")]
    return [(selector.strip(),
             dict(re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{6});", body)))
            for selector, body in re.findall(r"(:root[^{]*)\{(.*?)\n\t?\}",
                                             css, re.S)]


class TierStyle(unittest.TestCase):
    """The contrast gates a tier background must clear against every node
    it can contain (see the TIER_STYLE comment in roadmap.py), in both the
    light and the dark palette."""

    MODES = [("light", "bg", "stroke"), ("dark", "darkBg", "darkStroke")]

    def _pairs(self):
        for mode, fill, stroke in self.MODES:
            for tier, tier_style in roadmap.TIER_STYLE.items():
                for node, node_style in roadmap.STATUS_STYLE.items():
                    yield (mode, tier, node, tier_style[fill],
                           node_style[fill], node_style[stroke])

    def test_every_node_stroke_clears_three_to_one(self):
        for mode, tier, node, background, _fill, stroke in self._pairs():
            with self.subTest(mode=mode, tier=tier, node=node):
                self.assertGreaterEqual(_contrast(background, stroke), 3)

    def test_every_node_fill_stands_off_the_background(self):
        for mode, tier, node, background, fill, _stroke in self._pairs():
            with self.subTest(mode=mode, tier=tier, node=node):
                self.assertGreaterEqual(_contrast(background, fill), 1.35)

    def test_every_node_label_still_clears_aa_on_its_own_fill(self):
        for mode, fill, stroke in self.MODES:
            for node, style in roadmap.STATUS_STYLE.items():
                with self.subTest(mode=mode, node=node):
                    self.assertGreaterEqual(
                        _contrast(style[fill], style[stroke]), 4.5)

    def test_tier_label_clears_aa_on_its_background(self):
        for mode, fill, stroke in self.MODES:
            for tier, style in roadmap.TIER_STYLE.items():
                with self.subTest(mode=mode, tier=tier):
                    self.assertGreaterEqual(
                        _contrast(style[fill], style[stroke]), 4.5)

    def test_edge_line_clears_three_to_one(self):
        for selector, palette in _template_palettes():
            fill = "bg" if selector == ":root" else "darkBg"
            for tier, style in roadmap.TIER_STYLE.items():
                with self.subTest(selector=selector, tier=tier):
                    self.assertGreaterEqual(
                        _contrast(style[fill], palette["--diagram-line"]), 3)

    def test_backgrounds_reuse_no_node_colour(self):
        node_colours = {style[key] for style in roadmap.STATUS_STYLE.values()
                        for key in ("bg", "stroke", "darkBg", "darkStroke")}
        tier_colours = {style[key] for style in roadmap.TIER_STYLE.values()
                        for key in ("bg", "darkBg")}
        self.assertEqual(tier_colours & node_colours, set())

    def test_template_carries_the_same_colours_as_the_tables(self):
        palettes = _template_palettes()
        self.assertEqual(len(palettes), 3)
        tables = {**roadmap.STATUS_STYLE, **roadmap.TIER_STYLE}
        for selector, palette in palettes:
            fill, stroke = (("bg", "stroke") if selector == ":root"
                            else ("darkBg", "darkStroke"))
            for name, style in tables.items():
                with self.subTest(selector=selector, name=name):
                    self.assertEqual(
                        (palette[f"--color-{style['var']}-bg"],
                         palette[f"--color-{style['var']}"]),
                        (style[fill], style[stroke]))


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


class EndedField(unittest.TestCase):
    def _problems(self, **fields):
        ph = phase([{"id": "M1", "name": "m", "tasks": [task("a", **fields)]}])
        return roadmap._validate_phase(ph)

    def test_valid_ended_on_done_is_clean(self):
        self.assertEqual(self._problems(status="done", started="2026-09-25",
                                        ended="2026-10-02"), [])

    def test_ended_must_be_an_iso_date(self):
        self.assertTrue(any("ended 'soon'" in p for p in
                            self._problems(status="done", ended="soon")))

    def test_ended_on_a_task_that_is_not_done_is_a_problem(self):
        problems = self._problems(status="todo", ended="2026-10-02")
        self.assertTrue(any("not done" in p for p in problems))

    def test_ended_before_started_is_a_problem(self):
        problems = self._problems(status="done", started="2026-10-02",
                                  ended="2026-09-25")
        self.assertTrue(any("before started" in p for p in problems))

    def test_ended_sits_between_started_and_pr(self):
        self.assertEqual(roadmap.TASK_FIELD_ORDER[-3:], ["started", "ended", "pr"])


class EndCommand(unittest.TestCase):
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

    def test_end_writes_ended_in_field_order(self):
        jp = self._project([task("a", "done", started="2026-09-25", pr=12)])
        rc, _ = self._run("end", "a", str(jp), "--date", "2026-10-02")
        self.assertEqual(rc, 0)
        self.assertEqual(list(self._task(jp, "a")),
                         ["id", "description", "status", "dependsOn",
                          "started", "ended", "pr"])
        self.assertEqual(self._task(jp, "a")["ended"], "2026-10-02")

    def test_end_defaults_to_today(self):
        jp = self._project([task("a", "done")])
        self.assertEqual(self._run("end", "a", str(jp))[0], 0)
        self.assertEqual(self._task(jp, "a")["ended"], roadmap.date.today().isoformat())

    def test_end_refuses_a_task_that_is_not_done(self):
        jp = self._project([task("a")])
        before = jp.read_text()
        rc, out = self._run("end", "a", str(jp))
        self.assertEqual(rc, 1)
        self.assertIn("not done", out)
        self.assertEqual(jp.read_text(), before)

    def test_end_refuses_to_overwrite_without_force(self):
        jp = self._project([task("a", "done", ended="2026-09-30")])
        self.assertEqual(self._run("end", "a", str(jp), "--date", "2026-10-02")[0], 1)
        self.assertEqual(self._task(jp, "a")["ended"], "2026-09-30")
        self.assertEqual(self._run("end", "a", str(jp), "--date", "2026-10-02",
                                   "--force")[0], 0)
        self.assertEqual(self._task(jp, "a")["ended"], "2026-10-02")

    def test_end_rejects_a_bad_date_and_a_date_before_started(self):
        jp = self._project([task("a", "done", started="2026-10-01")])
        self.assertEqual(self._run("end", "a", str(jp), "--date", "tomorrow")[0], 1)
        self.assertEqual(self._run("end", "a", str(jp), "--date", "2026-09-01")[0], 1)
        self.assertNotIn("ended", self._task(jp, "a"))


class EndedFromHistory(unittest.TestCase):
    def test_date_is_the_version_where_the_task_became_done(self):
        versions = [("s1", "2026-09-01", {"a": "todo"}),
                    ("s2", "2026-09-10", {"a": "done"}),
                    ("s3", "2026-09-20", {"a": "done", "b": "todo"})]
        found = roadmap.ended_from_history(versions, "2026-10-02")
        self.assertEqual(found, {"a": ("2026-09-10", "s2", "transition")})

    def test_reopened_then_redone_uses_the_latest_finish(self):
        versions = [("s1", "2026-09-01", {"a": "done"}),
                    ("s2", "2026-09-05", {"a": "todo"}),
                    ("s3", "2026-09-09", {"a": "done"})]
        self.assertEqual(roadmap.ended_from_history(versions, "x")["a"][0],
                         "2026-09-09")

    def test_done_on_first_sight_is_flagged_first_seen(self):
        versions = [("s1", "2026-09-01", {"a": "done"}),
                    ("s2", "2026-09-05", {"a": "done", "b": "done"})]
        found = roadmap.ended_from_history(versions, "x")
        self.assertEqual(found["a"], ("2026-09-01", "s1", "first-seen"))
        self.assertEqual(found["b"], ("2026-09-05", "s2", "first-seen"))

    def test_working_tree_only_done_is_dated_today(self):
        versions = [("s1", "2026-09-01", {"a": "todo"}),
                    ("", "", {"a": "done"})]
        self.assertEqual(roadmap.ended_from_history(versions, "2026-10-02")["a"],
                         ("2026-10-02", "", "uncommitted"))

    def test_task_no_longer_done_at_the_end_is_dropped(self):
        versions = [("s1", "2026-09-01", {"a": "done"}),
                    ("s2", "2026-09-05", {"a": "todo"})]
        self.assertEqual(roadmap.ended_from_history(versions, "x"), {})


@unittest.skipUnless(shutil.which("git"), "git not installed")
class GitRoadmap(unittest.TestCase):
    """A temporary repository holding .claude/roadmaps.json, with dated
    commits. Helpers only; the test classes below add the cases."""

    def _git(self, *argv, when=None):
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        if when:
            env["GIT_COMMITTER_DATE"] = env["GIT_AUTHOR_DATE"] = f"{when}T12:00:00"
        subprocess.run(["git", "-C", str(self.root), *argv], check=True,
                       capture_output=True, env=env)

    def _write(self, tasks):
        data = [phase([{"id": "M1", "name": "m", "tasks": tasks}])]
        self.jp.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n")

    def _commit(self, tasks, when, message="roadmap"):
        self._write(tasks)
        self._git("add", ".")
        self._git("commit", "-q", "-m", message, when=when)

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.jp = self.root / ".claude" / "roadmaps.json"
        self.jp.parent.mkdir()
        self._git("init", "-q", "-b", "main")

    def _run(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = roadmap.main(list(argv))
        return rc, out.getvalue()

    def _tasks(self):
        return {t["id"]: t for t in
                json.loads(self.jp.read_text())[0]["milestones"][0]["tasks"]}


@unittest.skipUnless(shutil.which("git"), "git not installed")
class BackfillEnded(GitRoadmap):
    """backfill-ended against a real repository with dated commits."""

    def test_dates_come_from_the_commit_where_each_task_became_done(self):
        self._commit([task("a"), task("b"), task("c", "done")], "2026-09-01")
        self._commit([task("a", "done"), task("b"), task("c", "done")], "2026-09-10")
        self._commit([task("a", "done"), task("b", "done"), task("c", "done")],
                     "2026-09-20")
        rc, out = self._run("backfill-ended", str(self.jp), "--json")
        self.assertEqual(rc, 0)
        rows = {r["id"]: r for r in json.loads(out)["tasks"]}
        self.assertEqual(rows["a"]["ended"], "2026-09-10")
        self.assertEqual(rows["b"]["ended"], "2026-09-20")
        self.assertEqual((rows["c"]["ended"], rows["c"]["basis"]),
                         ("2026-09-01", "first-seen"))
        self.assertEqual(self._tasks()["a"]["ended"], "2026-09-10")

    def test_dry_run_writes_nothing(self):
        self._commit([task("a", "done")], "2026-09-01")
        before = self.jp.read_text()
        rc, out = self._run("backfill-ended", str(self.jp), "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("would set", out)
        self.assertEqual(self.jp.read_text(), before)

    def test_existing_ended_is_left_alone(self):
        self._commit([task("a", "done", ended="2026-09-30")], "2026-09-01")
        rc, out = self._run("backfill-ended", str(self.jp))
        self.assertEqual(rc, 0)
        self.assertIn("already has an end date", out)
        self.assertEqual(self._tasks()["a"]["ended"], "2026-09-30")

    def test_uncommitted_done_is_dated_today(self):
        self._commit([task("a")], "2026-09-01")
        self._write([task("a", "done")])
        rc, _ = self._run("backfill-ended", str(self.jp))
        self.assertEqual(rc, 0)
        self.assertEqual(self._tasks()["a"]["ended"], roadmap.date.today().isoformat())

    def _commit_done_before_started(self):
        self._commit([task("a", started="2026-09-15")], "2026-09-01")
        self._commit([task("a", "done", started="2026-09-15")], "2026-09-10")

    def test_date_before_started_is_skipped_and_reported(self):
        self._commit_done_before_started()
        rc, out = self._run("backfill-ended", str(self.jp), "--json")
        self.assertEqual(rc, 0)
        report = json.loads(out)
        self.assertEqual(report["tasks"], [])
        self.assertEqual((report["skipped"][0]["id"], report["skipped"][0]["started"]),
                         ("a", "2026-09-15"))
        self.assertNotIn("ended", self._tasks()["a"])
        self.assertEqual(self._run("validate", str(self.jp))[0], 0)

    def test_skipped_rows_show_in_the_text_preview(self):
        self._commit_done_before_started()
        rc, out = self._run("backfill-ended", str(self.jp), "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("skipped: before started 2026-09-15", out)
        self.assertNotIn("already has an end date", out)

    def test_uncommitted_done_before_a_future_started_is_skipped(self):
        self._commit([task("a", started="2026-12-01")], "2026-09-01")
        self._write([task("a", "done", started="2026-12-01")])
        rc, out = self._run("backfill-ended", str(self.jp), "--json")
        self.assertEqual(rc, 0)
        report = json.loads(out)
        self.assertEqual((report["tasks"], report["skipped"][0]["basis"]),
                         ([], "uncommitted"))
        self.assertNotIn("ended", self._tasks()["a"])

    def test_outside_a_repository_is_an_error(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        jp = Path(tmp.name) / ".claude" / "roadmaps.json"
        jp.parent.mkdir()
        data = [phase([{"id": "M1", "name": "m", "tasks": [task("a", "done")]}])]
        jp.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n")
        rc, out = self._run("backfill-ended", str(jp))
        self.assertEqual(rc, 1)
        self.assertIn("git", out)


@unittest.skipUnless(shutil.which("git"), "git not installed")
class StampEnded(GitRoadmap):
    """stamp-ended: the done tasks a branch finished, for pr-land."""

    def setUp(self):
        super().setUp()
        self._commit([task("a"), task("b", "done"), task("c"), task("d")],
                     "2026-09-01")
        self._git("branch", "base")
        self._git("checkout", "-q", "-b", "feat/x")

    def _stamp(self, *extra):
        return self._run("stamp-ended", str(self.jp), "--base", "base",
                         "--date", "2026-10-02", *extra)

    def test_stamps_only_what_the_branch_finished(self):
        self._commit([task("a", "done"), task("b", "done"), task("c"), task("d")],
                     "2026-09-05")
        rc, out = self._stamp()
        self.assertEqual(rc, 0)
        self.assertIn("ended 1 task(s) on 2026-10-02: a", out)
        tasks = self._tasks()
        self.assertEqual(tasks["a"]["ended"], "2026-10-02")
        self.assertNotIn("ended", tasks["b"])  # done before the branch
        self.assertNotIn("ended", tasks["c"])

    def test_pr_number_also_stamps_a_task_done_before_the_branch(self):
        self._commit([task("a"), task("b", "done", pr=7), task("c"), task("d")],
                     "2026-09-05")
        rc, out = self._stamp("--pr", "7")
        self.assertEqual(rc, 0)
        self.assertEqual(self._tasks()["b"]["ended"], "2026-10-02")

    def test_existing_ended_is_never_overwritten(self):
        self._commit([task("a", "done", ended="2026-09-30"), task("b", "done"),
                      task("c"), task("d")], "2026-09-05")
        self._stamp()
        self.assertEqual(self._tasks()["a"]["ended"], "2026-09-30")

    def test_dry_run_and_json(self):
        self._commit([task("a", "done"), task("b", "done"), task("c"), task("d")],
                     "2026-09-05")
        before = self.jp.read_text()
        rc, out = self._stamp("--dry-run", "--json")
        self.assertEqual(rc, 0)
        report = json.loads(out)
        self.assertEqual((report["tasks"], report["written"]), (["a"], False))
        self.assertEqual(self.jp.read_text(), before)

    def test_nothing_finished_writes_nothing(self):
        before = self.jp.read_text()
        rc, out = self._stamp()
        self.assertEqual(rc, 0)
        self.assertIn("ended 0 task(s)", out)
        self.assertEqual(self.jp.read_text(), before)

    def test_unknown_base_is_an_error(self):
        rc, out = self._run("stamp-ended", str(self.jp), "--base", "nope")
        self.assertEqual(rc, 1)
        self.assertIn("merge-base", out)

    def _rebase_onto(self, mutate_base):
        """Rewrite `base` with `mutate_base`, then branch feat/y from it."""
        self._git("checkout", "-q", "base")
        mutate_base()
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "base", when="2026-09-02")
        self._git("checkout", "-q", "-b", "feat/y")
        self.jp.parent.mkdir(exist_ok=True)

    def _assert_refuses_to_stamp(self):
        self._commit([task("a", "done"), task("b", "done"), task("c"), task("d")],
                     "2026-09-05")
        before = self.jp.read_text()
        rc, out = self._stamp()
        self.assertEqual(rc, 1)
        self.assertIn("cannot read phase", out)
        self.assertEqual(self.jp.read_text(), before)

    def test_renamed_phase_is_an_error_not_a_blanket_stamp(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "done"), task("b", "done"), task("c"), task("d")]}],
            name="Launch")]
        self.jp.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n")
        self._git("add", ".")
        self._git("commit", "-q", "-m", "rename phase", when="2026-09-05")
        before = self.jp.read_text()
        rc, out = self._stamp()
        self.assertEqual(rc, 1)
        self.assertIn("'Launch'", out)
        self.assertEqual(self.jp.read_text(), before)

    def test_unparseable_base_is_an_error(self):
        self._rebase_onto(lambda: self.jp.write_text("{ not json"))
        self._assert_refuses_to_stamp()

    def test_missing_base_file_is_an_error(self):
        self._rebase_onto(lambda: shutil.rmtree(self.jp.parent))
        self._assert_refuses_to_stamp()

    def test_task_new_to_a_readable_base_is_still_stamped(self):
        self._commit([task("a"), task("b", "done"), task("c"), task("d"),
                      task("e", "done")], "2026-09-05")
        rc, _ = self._stamp()
        self.assertEqual(rc, 0)
        tasks = self._tasks()
        self.assertEqual(tasks["e"]["ended"], "2026-10-02")
        self.assertNotIn("ended", tasks["b"])


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
        nudge = self.hook("session-start", self.repo)
        self.assertIn("claims no roadmap task", nudge)
        self.assertIn("roadmap-claim skill", nudge)
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
