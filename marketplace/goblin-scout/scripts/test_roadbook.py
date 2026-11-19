#!/usr/bin/env python3
"""Fixture tests for goblin-scout's roadbook (_roadbook_core.py + roadbook.py).

Run from this directory: python3 -m unittest test_roadbook -v
Stdlib only. Each test builds a minimal phase dict; file-based behaviour
(detect, recompute writes) uses a TemporaryDirectory shaped like a project
root with .claude/roadbook.json.
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

import roadbook
from _roadbook_core import (
    RoadbookError,
    active_phase,
    build_index,
    display_status,
    find_cycles,
    is_claimed,
    milestone_sinks,
    recompute_all,
    stamp_for,
    unmet_blockers,
)

STAMPED = stamp_for(roadbook.PLUGIN_VERSION)


def task(tid, status="todo", depends=None, soft=None, **extra):
    t = {"id": tid, "description": f"task {tid}", "status": status,
         "dependsOn": depends or []}
    if soft:
        t["softDependsOn"] = soft
    t.update(extra)
    return t


def phase(milestones, gates=None, name="Test Phase", **extra):
    p = {"name": name, "path": "docs/roadbook/TEST.md",
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
        with self.assertRaises(RoadbookError):
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
        with self.assertRaises(RoadbookError):
            active_phase({"roadmaps": [{"path": "docs/x.md"}]})


class MalformedInput(unittest.TestCase):
    def test_missing_task_id_is_roadbook_error(self):
        ph = phase([{"id": "M1", "name": "m",
                     "tasks": [{"description": "no id", "status": "todo"}]}])
        with self.assertRaises(RoadbookError):
            build_index(ph)

    def test_missing_milestone_id_is_roadbook_error(self):
        ph = phase([{"name": "m", "tasks": [task("a")]}])
        with self.assertRaises(RoadbookError):
            build_index(ph)


class GateParity(unittest.TestCase):
    def test_validate_flags_missing_and_extra_blocks(self):
        ph = phase(
            [{"id": "M1", "name": "m", "tasks": [
                task("a", "blocked", ["G1"]), task("b")]}],
            gates=[{"id": "G1", "name": "g", "status": "todo",
                    "blocks": ["b"]}])   # missing a, extra b
        problems = roadbook._validate_phase(ph)
        self.assertTrue(any("blocks[] missing a" in p for p in problems))
        self.assertTrue(any("blocks[] lists b" in p for p in problems))


class Stats(unittest.TestCase):
    def test_invalid_status_reported_not_dropped(self):
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "done"), task("b", "in_progress")]}])
        stats = roadbook.build_stats(ph)
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["invalid"], ["b"])
        self.assertEqual(sum(stats["byStatus"].values()) + len(stats["invalid"]),
                         stats["total"])

    def test_milestone_state_and_completion_counts_added(self):
        ph = phase([
            {"id": "M1", "name": "done", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "live", "tasks": [
                task("b", "done"), task("c", "todo")]}])
        stats = roadbook.build_stats(ph)
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
        stats = roadbook.build_stats(ph)
        by_id = {m["id"]: m for m in stats["milestones"]}
        self.assertEqual((by_id["M1"]["done"], by_id["M1"]["inScope"],
                          by_id["M1"]["donePct"]), (1, 2, 50))
        self.assertEqual((by_id["M2"]["done"], by_id["M2"]["inScope"],
                          by_id["M2"]["donePct"]), (1, 1, 100))
        self.assertEqual((stats["byStatus"]["done"], stats["inScope"],
                          stats["donePct"]), (2, 3, 67))
        # total stays raw: the ROADBOOK_OVERVIEW header count reads it
        self.assertEqual(stats["total"], 6)
        self.assertEqual(by_id["M1"]["total"], 3)

    def test_milestone_struck_out_whole_has_nothing_in_scope(self):
        ph = phase([
            {"id": "M1", "name": "struck", "tasks": [
                task("a", "out_of_scope"), task("b", "out_of_scope")]},
            {"id": "M2", "name": "zero", "tasks": [task("c")]}])
        stats = roadbook.build_stats(ph)
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
        stats = roadbook.build_stats(ph)
        self.assertEqual((stats["inScope"], stats["donePct"]), (0, 100))
        tiers = _layout(ph)["tiers"]
        self.assertEqual([g["stats"]["donePct"] for g in tiers], [100, 100])

    def test_empty_milestone_done_pct_stays_zero(self):
        # no tasks at all is a bug (state `empty`), never finished work
        ph = phase([{"id": "M1", "name": "empty", "tasks": []}])
        m = roadbook.build_stats(ph)["milestones"][0]
        self.assertEqual((m["donePct"], m["state"]), (0, "empty"))

    def test_human_stats_print_in_scope_fractions(self):
        ph = phase([{"id": "M1", "name": "mixed", "tasks": [
            task("a", "done"), task("b"), task("c", "out_of_scope")]}])
        text = roadbook._human_stats(roadbook.build_stats(ph))
        self.assertIn("1/2 done (50%)", text)
        self.assertIn("M1   1/2", text)
        self.assertNotIn("/3", text)


class MilestoneState(unittest.TestCase):
    """Milestone-level derived state (distinct from task status): drives the
    artefact's Overview/Milestones colour and sort (see roadbook-conventions.md
    and library/templates/chart.html). Rule order: empty -> done
    -> deferred (tier cascade) -> deferred (member gate) -> inProgress ->
    blocked -> todo."""

    def test_in_progress_when_partially_done(self):
        self.assertEqual(
            roadbook.milestone_state({"todo": 1, "done": 1}, 50, total=2),
            "inProgress")

    def test_todo_when_nothing_started(self):
        self.assertEqual(
            roadbook.milestone_state({"todo": 2}, 0, total=2), "todo")

    def test_done_when_fully_done(self):
        self.assertEqual(
            roadbook.milestone_state({"done": 2}, 100, total=2), "done")

    def test_all_out_of_scope_is_done(self):
        # Struck-from-play (out_of_scope) still reads as done: nothing
        # actionable remains, whether it finished or was struck out.
        by_status = {"out_of_scope": 3}
        self.assertEqual(roadbook.milestone_state(by_status, 0, total=3), "done")

    def test_empty_milestone_is_flagged(self):
        # Zero tasks is a bug (see _validate_phase), never a legitimate
        # state: it must never read as todo/done and hide the problem.
        self.assertEqual(roadbook.milestone_state({}, 0, total=0), "empty")

    def test_blocked_outranks_in_progress_when_nothing_can_be_picked_up(self):
        # Done work does not soften a stuck milestone: every remaining
        # task is blocked, so blocked (rule 4) outranks inProgress (rule 5).
        self.assertEqual(
            roadbook.milestone_state({"done": 2, "blocked": 3}, 40, total=5),
            "blocked")
        self.assertEqual(
            roadbook.milestone_state({"done": 7, "blocked": 1}, 88, total=8),
            "blocked")

    def test_blocked_sets_out_of_scope_tasks_aside(self):
        by_status = {"done": 1, "blocked": 2, "out_of_scope": 1}
        self.assertEqual(
            roadbook.milestone_state(by_status, 33, total=4), "blocked")

    def test_one_actionable_task_keeps_a_milestone_in_progress(self):
        by_status = {"done": 2, "blocked": 3, "todo": 1}
        self.assertEqual(
            roadbook.milestone_state(by_status, 33, total=6), "inProgress")

    def test_a_claim_on_a_blocked_task_keeps_a_milestone_in_progress(self):
        by_status = {"done": 2, "blocked": 3}
        self.assertEqual(
            roadbook.milestone_state(by_status, 40, total=5, in_progress=1),
            "inProgress")

    def test_blocked_when_every_unfinished_task_is_blocked(self):
        by_status = {"blocked": 2}
        self.assertEqual(
            roadbook.milestone_state(by_status, 0, total=2), "blocked")

    def test_claim_gives_in_progress_even_at_zero_done(self):
        by_status = {"todo": 2}
        self.assertEqual(
            roadbook.milestone_state(by_status, 0, total=2, in_progress=1),
            "inProgress")

    def test_deferred_when_a_lower_tier_is_not_done(self):
        by_status = {"todo": 2}
        self.assertEqual(
            roadbook.milestone_state(by_status, 0, total=2, tier=1,
                                    lower_tiers_done=False),
            "deferred")

    def test_lower_tiers_done_lets_tier_through_to_its_own_rules(self):
        by_status = {"done": 2}
        self.assertEqual(
            roadbook.milestone_state(by_status, 100, total=2, tier=1,
                                    lower_tiers_done=True),
            "done")

    def test_deferred_never_fires_for_tier_zero(self):
        # A Core milestone has no lower tier to wait on: even with
        # lower_tiers_done=False (should never happen for tier 0 in
        # practice) tier>=1 is required for the deferred rule.
        by_status = {"todo": 2}
        self.assertEqual(
            roadbook.milestone_state(by_status, 0, total=2, tier=0,
                                    lower_tiers_done=False),
            "todo")

    def test_member_deferred_fires_without_a_tier(self):
        # A plain, untiered milestone (tier 0) can still shelve via a
        # deferred member; this reading needs no (Secondary)/(Tertiary)
        # suffix, unlike the tier-cascade deferred rule above.
        by_status = {"deferred": 4}
        self.assertEqual(
            roadbook.milestone_state(by_status, 0, total=4), "deferred")

    def test_member_deferred_outranks_done_percentage(self):
        # A milestone with one deferred task and nine done ones is still
        # "shelved" even at donePct 90: the deliberate call outranks
        # percentage, matching the reading main used before the tier
        # rewrite (rule 3 fires ahead of inProgress, rule 4).
        by_status = {"done": 9, "deferred": 1}
        self.assertEqual(
            roadbook.milestone_state(by_status, 90, total=10), "deferred")

    def test_member_deferred_never_fires_while_actionable_work_remains(self):
        # Five todo tasks are still live work to pick up, not a shelved
        # milestone: hiding them behind "deferred" would contradict
        # goblin-scout:survey-waypoints' own ready-set, which still lists them.
        by_status = {"todo": 5, "deferred": 1}
        self.assertEqual(
            roadbook.milestone_state(by_status, 0, total=6), "todo")


class MilestoneTier(unittest.TestCase):
    def test_no_suffix_is_core(self):
        self.assertEqual(roadbook.milestone_tier("Search"), 0)
        self.assertEqual(roadbook.milestone_tier(""), 0)

    def test_labels_spell_core_secondary_tertiary(self):
        self.assertEqual([roadbook.tier_label(t) for t in range(3)],
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
        self.assertEqual(roadbook.milestone_tier("Search (Secondary)"), 1)
        self.assertEqual(roadbook.milestone_tier("Search (Tertiary)"), 2)
        self.assertEqual(roadbook.milestone_tier("Search (Quaternary)"), 3)
        self.assertEqual(roadbook.milestone_tier("Search (Quinary)"), 4)

    def test_case_insensitive(self):
        self.assertEqual(roadbook.milestone_tier("Search (secondary)"), 1)
        self.assertEqual(roadbook.milestone_tier("Search (SECONDARY)"), 1)

    def test_suffix_must_be_trailing(self):
        self.assertEqual(roadbook.milestone_tier("(Secondary) is not this"), 0)


class MilestoneAllDone(unittest.TestCase):
    def test_empty_is_not_done(self):
        self.assertFalse(roadbook.milestone_all_done({}, 0))

    def test_all_done_or_out_of_scope(self):
        self.assertTrue(
            roadbook.milestone_all_done({"done": 1, "out_of_scope": 1}, 2))

    def test_one_actionable_task_is_not_done(self):
        self.assertFalse(
            roadbook.milestone_all_done({"done": 1, "todo": 1}, 2))


class BuildStatsTiers(unittest.TestCase):
    def test_cascade_defers_tertiary_while_secondary_is_open(self):
        ph = phase([
            {"id": "M1", "name": "Core", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "Extra (Secondary)", "tasks": [task("b")]},
            {"id": "M3", "name": "More (Tertiary)", "tasks": [task("c")]}])
        by_id = {m["id"]: m for m in roadbook.build_stats(ph)["milestones"]}
        self.assertEqual(by_id["M1"]["state"], "done")
        self.assertEqual(by_id["M2"]["state"], "todo")
        self.assertEqual(by_id["M3"]["state"], "deferred")

    def test_tertiary_opens_once_secondary_is_done(self):
        ph = phase([
            {"id": "M1", "name": "Core", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "Extra (Secondary)", "tasks": [task("b", "done")]},
            {"id": "M3", "name": "More (Tertiary)", "tasks": [task("c")]}])
        by_id = {m["id"]: m for m in roadbook.build_stats(ph)["milestones"]}
        self.assertEqual(by_id["M3"]["state"], "todo")

    def test_empty_milestone_reported_by_validate(self):
        ph = phase([{"id": "M1", "name": "Empty", "tasks": []}])
        problems = roadbook._validate_phase(ph)
        self.assertIn("M1: milestone has no waypoints", problems)

    def test_empty_milestone_in_an_earlier_tier_never_blocks_the_cascade(self):
        # A bug (empty milestone) must never masquerade as "still in
        # progress" and freeze every later tier deferred forever: only a
        # non-empty, unfinished milestone should hold a tier open.
        ph = phase([
            {"id": "M1", "name": "Core", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "Whoops", "tasks": []},
            {"id": "M3", "name": "Extra (Secondary)", "tasks": [task("b")]}])
        by_id = {m["id"]: m for m in roadbook.build_stats(ph)["milestones"]}
        self.assertEqual(by_id["M2"]["state"], "empty")
        self.assertEqual(by_id["M3"]["state"], "todo")

    def test_milestones_carry_their_own_tier(self):
        # overview_layout() reads tier back from here rather than
        # re-deriving it from the name; a dropped field would silently
        # send it back to milestone_tier() and split the two computations.
        ph = phase([
            {"id": "M1", "name": "Core", "tasks": [task("a")]},
            {"id": "M2", "name": "Extra (Secondary)", "tasks": [task("b")]}])
        by_id = {m["id"]: m for m in roadbook.build_stats(ph)["milestones"]}
        self.assertEqual(by_id["M1"]["tier"], 0)
        self.assertEqual(by_id["M2"]["tier"], 1)


def _layout(ph):
    stats = roadbook.build_stats(ph)
    ready = roadbook.build_ready(ph)
    return roadbook.overview_layout(ph, stats, ready)


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
        self.assertEqual(roadbook.dev_colour("jason"), roadbook.dev_colour("jason"))

    def test_case_and_whitespace_insensitive(self):
        self.assertEqual(roadbook.dev_colour("Jason"), roadbook.dev_colour(" jason "))

    def test_empty_or_none_yields_none(self):
        self.assertIsNone(roadbook.dev_colour(""))
        self.assertIsNone(roadbook.dev_colour(None))

    def test_stable_across_process_hash_seed(self):
        # dev_colour must use a stable digest, not builtin hash(), which is
        # salted per-process via PYTHONHASHSEED; simulate that by asserting
        # the result never depends on the current process's hash seed at all
        # (crc32 doesn't read PYTHONHASHSEED, so this holds trivially once
        # implemented correctly, and would flake under repeated runs with
        # builtin hash()).
        script = ("import sys; sys.path.insert(0, %r); import roadbook; "
                  "print(roadbook.dev_colour('jason'))" % str(Path(__file__).parent))
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
        ready = roadbook.build_ready(ph)
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
        by_id = {c["id"]: c for c in roadbook.build_ready(ph)["candidates"]}
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
        by_id = {c["id"]: c for c in roadbook.build_ready(ph)["candidates"]}
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
        c = roadbook.build_ready(ph)["candidates"][0]
        self.assertEqual((c["unblocksNow"], c["unblocksPartly"], c["unblocksLater"]),
                         (1, 0, 0))

    def test_assignee_projected_when_set_and_empty_when_absent(self):
        ph = phase([{"id": "M1", "name": "m1", "tasks": [
            task("a", assignee="jason"),
            task("b")]}])
        by_id = {c["id"]: c for c in roadbook.build_ready(ph)["candidates"]}
        self.assertEqual(by_id["a"]["assignee"], "jason")
        self.assertEqual(by_id["b"]["assignee"], "")

    def test_groups_cover_every_candidate_once_per_pivot(self):
        ph = phase([
            {"id": "M1", "name": "m1", "tasks": [
                task("1IN.1", assignee="jaz"), task("1UI.2")]},
            {"id": "M2", "name": "m2", "tasks": [
                task("2IN.1", assignee="Jason"), task("odd")]}])
        candidates = roadbook.build_ready(ph)["candidates"]
        groups = roadbook.ready_groups(candidates)
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
        self.assertIsNone(roadbook.resolve_within(self._phase()))

    def test_milestones_narrow_ready_and_claimed(self):
        ph = self._phase()
        within = roadbook.resolve_within(ph, milestones=["m1"])
        ready = roadbook.build_ready(ph, within=within)
        self.assertEqual([c["id"] for c in ready["candidates"]], ["a"])
        self.assertEqual([c["id"] for c in ready["claimed"]], ["c"])

    def test_tier_words_select_every_milestone_in_the_tier(self):
        ph = self._phase()
        self.assertEqual(roadbook.resolve_within(ph, tiers=["core"]), {"M1", "M2"})
        self.assertEqual(roadbook.resolve_within(ph, tiers=["Secondary"]), {"M3"})

    def test_focus_is_the_underway_tier(self):
        ph = self._phase()
        self.assertEqual(roadbook.resolve_within(ph, tiers=["focus"]), {"M1", "M2"})

    def test_focus_moves_up_when_core_is_done(self):
        ph = phase([
            {"id": "M1", "name": "Core", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "More (Secondary)", "tasks": [task("b", "blocked", ["M1"])]}])
        self.assertEqual(roadbook.resolve_within(ph, tiers=["focus"]), {"M2"})

    def test_focus_errors_when_nothing_is_underway(self):
        ph = phase([{"id": "M1", "name": "Core", "tasks": [task("a", "done")]}])
        with self.assertRaises(RoadbookError):
            roadbook.resolve_within(ph, tiers=["focus"])

    def test_unknown_milestone_and_tier_error(self):
        ph = self._phase()
        with self.assertRaisesRegex(RoadbookError, "M9"):
            roadbook.resolve_within(ph, milestones=["M9"])
        with self.assertRaisesRegex(RoadbookError, "tertiary"):
            roadbook.resolve_within(ph, tiers=["tertiary"])

    def test_milestones_and_tiers_are_mutually_exclusive(self):
        with self.assertRaises(RoadbookError):
            roadbook.resolve_within(self._phase(), milestones=["M1"], tiers=["core"])

    def test_candidates_carry_tier(self):
        ph = self._phase()
        opened = roadbook.build_ready(ph, horizon="open")
        by_id = {c["id"]: c for c in opened["candidates"]}
        self.assertEqual(by_id["f"]["tierLabel"], "Secondary")
        self.assertEqual(by_id["a"]["tierLabel"], "Core")

    def test_open_horizon_includes_blocked_and_claimed_but_not_done(self):
        ph = self._phase()
        opened = roadbook.build_ready(ph, horizon="open")
        self.assertEqual({c["id"] for c in opened["candidates"]},
                         {"a", "b", "c", "d", "f"})
        self.assertEqual(opened["claimed"], [])
        by_id = {c["id"]: c for c in opened["candidates"]}
        self.assertEqual(by_id["c"]["display"], "in_progress")
        self.assertEqual(by_id["c"]["started"], "2026-09-25")
        self.assertEqual(by_id["b"]["status"], "blocked")

    def test_open_with_tier_filter(self):
        ph = self._phase()
        within = roadbook.resolve_within(ph, tiers=["secondary"])
        opened = roadbook.build_ready(ph, within=within, horizon="open")
        self.assertEqual([c["id"] for c in opened["candidates"]], ["f"])


class ReadyFilterCli(unittest.TestCase):
    def _project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        jp = Path(tmp.name) / ".claude" / "roadbook.json"
        jp.parent.mkdir()
        data = [phase([
            {"id": "M1", "name": "Core", "tasks": [task("a")]},
            {"id": "M2", "name": "More (Secondary)", "tasks": [task("b")]}])]
        jp.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n")
        return jp

    def _run(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = roadbook.main(list(argv))
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


class MilestoneEdgeReduction(unittest.TestCase):
    def edges(self, ph, kind="milestone-complete"):
        return {(e["from"], e["to"]) for e in roadbook.build_graph(ph)["edges"]
                if e["kind"] == kind}

    def shape(self, soft_sink=False):
        # The CHIRPdb 6HD.5 shape: sink s in M6, sole dependant x in M4,
        # M4 gating g in M6.
        extra = {"softMilestone": True} if soft_sink else {}
        return phase([
            {"id": "M4", "name": "m4", "tasks": [task("x", "blocked", ["s"])]},
            {"id": "M6", "name": "m6", "tasks": [
                task("s", **extra), task("g", "blocked", ["M4"])]}])

    def test_sink_already_reaching_its_milestone_loses_the_edge(self):
        done = self.edges(self.shape())
        self.assertNotIn(("s", "M6"), done)
        self.assertIn(("g", "M6"), done)       # milestone keeps an inbound edge
        self.assertIn(("x", "M4"), done)

    def test_task_edges_are_never_reduced(self):
        ph = phase([{"id": "M1", "name": "m1", "tasks": [
            task("a"), task("b", "blocked", ["a"]),
            task("c", "blocked", ["a", "b"])]}])
        self.assertEqual(self.edges(ph, "task"),
                         {("a", "b"), ("a", "c"), ("b", "c")})

    def test_soft_sink_keeps_its_dotted_edge(self):
        self.assertIn(("s", "M6"), self.edges(self.shape(soft_sink=True)))

    def test_soft_path_does_not_count(self):
        ph = phase([
            {"id": "M4", "name": "m4", "tasks": [task("x", soft=["s"])]},
            {"id": "M6", "name": "m6", "tasks": [
                task("s"), task("g", "blocked", ["M4"])]}])
        self.assertIn(("s", "M6"), self.edges(ph))

    def test_unrelated_sinks_keep_their_edges(self):
        ph = phase([{"id": "M1", "name": "m1", "tasks": [
            task("a"), task("b")]}])
        self.assertEqual(self.edges(ph), {("a", "M1"), ("b", "M1")})


class Mermaid(unittest.TestCase):
    def setUp(self):
        self.ph = phase([
            {"id": "M1", "name": "First", "tasks": [
                task("a", "done"), task("b", "todo", ["a"])]},
            {"id": "M2", "name": "Second", "tasks": [
                task("c", "blocked", ["M1"])]}])

    def test_classdefs_follow_graph_line(self):
        src = roadbook.mermaid_source(self.ph)
        lines = src.splitlines()
        self.assertTrue(lines[0].startswith("graph LR"))
        self.assertTrue(all(l.strip().startswith("classDef")
                            for l in lines[1:1 + len(roadbook.STATUS_STYLE)]))

    def test_status_classes_and_terminal_edges(self):
        src = roadbook.mermaid_source(self.ph)
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
        src = roadbook.mermaid_source(ph, omit_done=True)
        self.assertNotIn('a["', src)
        self.assertNotIn("M1", src)
        self.assertIn('b["', src)

    def test_omit_done_drops_out_of_scope_tasks_and_their_edges(self):
        ph = phase([
            {"id": "M1", "name": "Mixed", "tasks": [
                task("a", "out_of_scope"), task("b", "todo", ["a"])]},
            {"id": "M2", "name": "Next", "tasks": [task("c", "blocked", ["M1"])]}])
        src = roadbook.mermaid_source(ph, omit_done=True)
        self.assertNotIn('a["', src)
        self.assertNotIn("a -->", src)
        self.assertNotIn("class a ", src)
        self.assertIn('b["', src)
        self.assertIn("b --> M1", src)

    def test_omit_done_drops_a_milestone_of_only_out_of_scope_tasks(self):
        ph = phase([
            {"id": "M1", "name": "Struck", "tasks": [task("a", "out_of_scope")]},
            {"id": "M2", "name": "Live", "tasks": [task("b")]}])
        src = roadbook.mermaid_source(ph, omit_done=True)
        self.assertNotIn("M1", src)
        self.assertNotIn('a["', src)
        self.assertIn('b["', src)

    def test_omit_done_drops_a_tier_of_done_and_out_of_scope_whole(self):
        ph = phase([
            {"id": "M1", "name": "Core work", "tasks": [
                task("a", "done"), task("w", "out_of_scope")]},
            {"id": "M2", "name": "More (Secondary)", "tasks": [task("b")]}])
        inside, _ = _subgraphs(roadbook.mermaid_source(ph, omit_done=True))
        self.assertEqual(list(inside), ["tier1"])

    def test_the_full_graph_still_draws_out_of_scope_tasks(self):
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "out_of_scope"), task("b")]}])
        self.assertIn('a["', roadbook.mermaid_source(ph))

    def test_out_of_scope_gets_its_classdef(self):
        ph = phase([{"id": "M1", "name": "m",
                     "tasks": [task("a", "out_of_scope")]}])
        src = roadbook.mermaid_source(ph)
        self.assertIn("classDef outOfScope", src)
        self.assertIn("class a outOfScope", src)

    def test_vars_palette_uses_custom_properties(self):
        src = roadbook.mermaid_source(self.ph, palette="vars")
        self.assertIn("fill:var(--color-todo-bg)", src)

    def test_orphan_gates_are_not_drawn(self):
        ph = phase(
            [{"id": "M1", "name": "m", "tasks": [task("a", "todo", ["G1"])]}],
            gates=[{"id": "G1", "name": "live", "status": "todo",
                    "blocks": ["a"]},
                   {"id": "G2", "name": "resolved", "status": "todo",
                    "blocks": []}])
        src = roadbook.mermaid_source(ph)
        self.assertIn('G1["', src)
        self.assertNotIn('G2["', src)

    def test_soft_edge_renders_dotted(self):
        # a -.-> b is soft-only; c --> d is hard-only, so both arrow forms
        # are asserted against unambiguous pairs.
        ph = phase([{"id": "M1", "name": "m1", "tasks": [
            task("a"), task("b", soft=["a"])]},
            {"id": "M2", "name": "m2", "tasks": [
                task("c"), task("d", "todo", ["c"])]}])
        src = roadbook.mermaid_source(ph)
        self.assertIn("a -.-> b", src)
        self.assertIn("c --> d", src)
        self.assertNotIn("c -.-> d", src)

    def test_nodes_declared_in_topological_order(self):
        src = roadbook.mermaid_source(self.ph)
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
        inside, outside = _subgraphs(roadbook.mermaid_source(self.ph))
        self.assertEqual(outside, [])
        self.assertEqual(list(inside), ["tier0", "tier1", "tier2"])
        self.assertEqual(sorted(inside["tier0"][1]), ["M1", "a", "b"])
        self.assertEqual(sorted(inside["tier2"][1]), ["M3", "e"])

    def test_gate_sits_in_the_lowest_tier_it_gates(self):
        inside, _ = _subgraphs(roadbook.mermaid_source(self.ph))
        self.assertEqual(sorted(inside["tier1"][1]), ["G1", "M2", "c", "d"])

    def test_labels_name_the_tier_and_its_state(self):
        inside, _ = _subgraphs(roadbook.mermaid_source(self.ph))
        self.assertEqual([label for label, _ in inside.values()],
                         ["Core · underway", "Secondary · deferred",
                          "Tertiary · deferred"])

    def test_tier_classes_follow_the_state(self):
        src = roadbook.mermaid_source(self.ph)
        self.assertIn("\tclass tier0 tierUnderway", src)
        self.assertIn("\tclass tier1,tier2 tierDeferred", src)

    def test_classdefs_still_follow_the_graph_line(self):
        lines = roadbook.mermaid_source(self.ph).splitlines()
        count = len(roadbook.STATUS_STYLE) + len(roadbook.TIER_STYLE)
        self.assertTrue(all(l.strip().startswith("classDef")
                            for l in lines[1:1 + count]))
        self.assertTrue(lines[1 + count].strip().startswith("subgraph"))

    def test_edges_come_after_every_subgraph(self):
        lines = roadbook.mermaid_source(self.ph).splitlines()
        last_end = max(i for i, l in enumerate(lines) if l.strip() == "end")
        first_edge = min(i for i, l in enumerate(lines) if "-->" in l)
        self.assertGreater(first_edge, last_end)

    def test_a_finished_tier_reads_done_in_the_full_graph(self):
        ph = phase([
            {"id": "M1", "name": "Core work", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "More (Secondary)", "tasks": [
                task("b", "todo", ["M1"])]}])
        inside, _ = _subgraphs(roadbook.mermaid_source(ph))
        self.assertEqual([label for label, _ in inside.values()],
                         ["Core · done", "Secondary · underway"])
        self.assertIn("\tclass tier0,tier1 tierUnderway",
                      roadbook.mermaid_source(ph))

    def test_omit_done_drops_a_finished_tier_whole(self):
        ph = phase([
            {"id": "M1", "name": "Core work", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "More (Secondary)", "tasks": [task("b")]}])
        inside, outside = _subgraphs(
            roadbook.mermaid_source(ph, omit_done=True))
        self.assertEqual(list(inside), ["tier1"])
        self.assertEqual(outside, [])

    def test_untiered_phase_draws_no_subgraph(self):
        ph = phase([
            {"id": "M1", "name": "First", "tasks": [task("a")]},
            {"id": "M2", "name": "Second", "tasks": [
                task("b", "blocked", ["M1"])]}])
        src = roadbook.mermaid_source(ph)
        self.assertNotIn("subgraph", src)
        self.assertNotIn("classDef tier", src)
        self.assertNotIn("\tend", src)

    def test_vars_palette_names_the_tier_properties(self):
        src = roadbook.mermaid_source(self.ph, palette="vars")
        self.assertIn("fill:var(--color-tier-underway-bg)", src)
        self.assertIn("fill:var(--color-tier-deferred-bg)", src)


class TierStates(unittest.TestCase):
    def _states(self, ph):
        return roadbook.tier_states(roadbook.build_stats(ph)["milestones"])

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
    html = (Path(roadbook.__file__).resolve().parent.parent
            / "templates" / "chart.html").read_text()
    # the page's own <style>, after the one the theme and faces fill at render
    css = next(block for block in html.split("<style>")[1:] if "--color-todo" in block)
    css = css[:css.index("</style>")]
    return [(selector.strip(),
             dict(re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{6});", body)))
            for selector, body in re.findall(r"(:root[^{]*)\{(.*?)\n\t?\}",
                                             css, re.S)]


class TierStyle(unittest.TestCase):
    """The contrast gates a tier background must clear against every node
    it can contain (see the TIER_STYLE comment in roadbook.py), in both the
    light and the dark palette."""

    MODES = [("light", "bg", "stroke"), ("dark", "darkBg", "darkStroke")]

    def _pairs(self):
        for mode, fill, stroke in self.MODES:
            for tier, tier_style in roadbook.TIER_STYLE.items():
                for node, node_style in roadbook.STATUS_STYLE.items():
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
        # the label is the style's text colour: its stroke, except on an
        # inverted node (the milestone's exhibit panel, the gate's slime)
        for (mode, fill, _stroke), text in zip(self.MODES, ("text", "darkText")):
            for node, style in roadbook.STATUS_STYLE.items():
                with self.subTest(mode=mode, node=node):
                    self.assertGreaterEqual(
                        _contrast(style[fill], style[text]), 4.5)

    def test_tier_label_clears_aa_on_its_background(self):
        for mode, fill, stroke in self.MODES:
            for tier, style in roadbook.TIER_STYLE.items():
                with self.subTest(mode=mode, tier=tier):
                    self.assertGreaterEqual(
                        _contrast(style[fill], style[stroke]), 4.5)

    def test_edge_line_clears_three_to_one(self):
        for selector, palette in _template_palettes():
            fill = "bg" if selector == ":root" else "darkBg"
            for tier, style in roadbook.TIER_STYLE.items():
                with self.subTest(selector=selector, tier=tier):
                    self.assertGreaterEqual(
                        _contrast(style[fill], palette["--diagram-line"]), 3)

    def test_backgrounds_reuse_no_node_colour(self):
        node_colours = {style[key] for style in roadbook.STATUS_STYLE.values()
                        for key in ("bg", "stroke", "darkBg", "darkStroke")}
        tier_colours = {style[key] for style in roadbook.TIER_STYLE.values()
                        for key in ("bg", "darkBg")}
        self.assertEqual(tier_colours & node_colours, set())

    def test_template_carries_the_same_colours_as_the_tables(self):
        palettes = _template_palettes()
        self.assertEqual(len(palettes), 3)
        tables = {**roadbook.STATUS_STYLE, **roadbook.TIER_STYLE}
        for selector, palette in palettes:
            fill, stroke, text = (("bg", "stroke", "text") if selector == ":root"
                                  else ("darkBg", "darkStroke", "darkText"))
            for name, style in tables.items():
                with self.subTest(selector=selector, name=name):
                    self.assertEqual(
                        (palette[f"--color-{style['var']}-bg"],
                         palette[f"--color-{style['var']}"],
                         palette[f"--color-{style['var']}-text"]),
                        (style[fill], style[stroke], style.get(text, style[stroke])))


def _theme_tokens():
    """{"light": {token: hex}, "dark": {...}} from the goblin theme CSS the
    plugin carries (templates/chart-theme.css)."""
    css = (Path(roadbook.__file__).resolve().parent.parent
           / "templates" / "chart-theme.css").read_text()
    blocks = re.findall(r"(:root[^{]*)\{(.*?)\n\t?\}", css, re.S)
    light, dark = (dict((k, v.lower()) for k, v in re.findall(
        r"--([\w-]+):\s*(#[0-9A-Fa-f]{6});", body)) for _sel, body in blocks[:2])
    return {"light": light, "dark": dark}


def _mix(a, b, t):
    """t of colour a over colour b, per sRGB channel, rounded: how the
    status table derives its washes from the theme."""
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x * t + y * (1 - t)):02x}" for x, y in zip(pa, pb))


class StatusDerivation(unittest.TestCase):
    """Every colour in STATUS_STYLE and TIER_STYLE is a goblin theme token or
    a declared mix of two, recomputed here from the copied theme CSS, so the
    tables cannot drift from the theme (the recipes are the comments beside
    each entry in roadbook.py, as Jason approved them on 2026-11-18)."""

    WASH = 0.08
    # (style, key): light recipe, dark recipe; a recipe is a token or (a, b, t)
    RECIPES = {
        "todo": {"stroke": ("ink-muted", "ink-muted"), "text": ("ink-muted", "ink-muted"),
                 "bg": (("ink-muted", "slip", .04), ("ink-muted", "surface", .04))},
        "inProgress": {"stroke": ("info", "info"), "text": ("info", "info"),
                       "bg": (("info", "slip", WASH), ("info", "surface", WASH))},
        "blocked": {"stroke": ("danger", "danger"), "text": ("danger", "danger"),
                    "bg": (("danger", "slip", WASH), ("danger", "surface", WASH))},
        "paused": {"stroke": ("accent", "accent"), "text": ("accent", "accent"),
                   "bg": (("accent", "slip", WASH), ("accent", "surface", WASH))},
        "deferred": {"stroke": ("warn", "warn"), "text": ("warn", "warn"),
                     "bg": (("warn", "slip", WASH), ("warn", "surface", WASH))},
        "done": {"stroke": ("ok", "ok"), "text": ("ok", "ok"),
                 "bg": (("ok", "slip", WASH), ("ok", "surface", WASH))},
        "outOfScope": {"stroke": (("ink", "line", .5), ("ink", "line", .5)),
                       "text": (("ink", "line", .5), ("ink", "line", .5)),
                       "bg": ("slip", "surface")},
        "mile": {"stroke": ("exhibit", "exhibit-ink"), "text": ("exhibit-ink", "exhibit-ink"),
                 "bg": ("exhibit", "exhibit")},
        "external": {"stroke": ("on-slime", "slime"), "text": ("on-slime", "on-slime"),
                     "bg": (("slime", "slip", .28), "slime")},
        "tierUnderway": {"stroke": ("ink", "ink"),
                         "bg": (("line", "surface-raised", .25), ("line", "surface-raised", .75))},
        "tierDeferred": {"stroke": ("ink", "card-ink"),
                         "bg": (("card", "slip", .5), ("card", "card-dark", .75))},
    }
    KEYS = {"stroke": ("stroke", "darkStroke"), "text": ("text", "darkText"), "bg": ("bg", "darkBg")}

    def _resolve(self, recipe, tokens):
        if isinstance(recipe, str):
            return tokens[recipe]
        a, b, t = recipe
        return _mix(tokens[a], tokens[b], t)

    def test_every_colour_is_the_theme_or_a_declared_mix_of_it(self):
        tokens = _theme_tokens()
        tables = {**roadbook.STATUS_STYLE, **roadbook.TIER_STYLE}
        self.assertEqual(set(tables), set(self.RECIPES))
        for name, recipes in self.RECIPES.items():
            for part, (light, dark) in recipes.items():
                for mode, recipe, key in (("light", light, self.KEYS[part][0]),
                                          ("dark", dark, self.KEYS[part][1])):
                    with self.subTest(name=name, part=part, mode=mode):
                        self.assertEqual(tables[name][key],
                                         self._resolve(recipe, tokens[mode]))

    def test_the_chips_accent_and_diagram_chrome_are_the_theme_too(self):
        # the template's colours outside the two tables: scout chips, the
        # stamp accent and the route's edge colours, per palette block
        tokens = _theme_tokens()
        chips = dict(zip(roadbook._DEV_COLOUR_PALETTE,
                         ("accent", "accent-2", "info", "warn", "danger")))
        for selector, palette in _template_palettes():
            mode, base = (("light", "slip") if selector == ":root" else ("dark", "surface"))
            t = tokens[mode]
            expected = {"--diagram-line": t["ink-muted"], "--diagram-edge-label-bg": t[base],
                        "--color-primary": t["accent"], "--color-primary-text": t["accent"],
                        "--color-primary-bg": _mix(t["accent"], t[base], self.WASH)}
            for chip, token in chips.items():
                expected[f"--color-dev-{chip}"] = t[token]
                expected[f"--color-dev-{chip}-bg"] = _mix(t[token], t[base], self.WASH)
            for name, value in expected.items():
                with self.subTest(selector=selector, name=name):
                    self.assertEqual(palette[name], value)


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
        self.assertEqual(roadbook.choose_direction(self._chain()), "TD")

    def test_wide_fan_picks_lr(self):
        self.assertEqual(roadbook.choose_direction(self._fan()), "LR")

    def test_deterministic_across_repeated_calls(self):
        ph = self._fan()
        results = {roadbook.choose_direction(ph) for _ in range(5)}
        self.assertEqual(len(results), 1)

    def test_empty_graph_defaults_to_td(self):
        ph = phase([{"id": "M1", "name": "m", "tasks": [task("a", "done")]}])
        self.assertEqual(roadbook.choose_direction(ph), "TD")

    def test_longest_path_layers_assigns_by_depth(self):
        ids = ["a", "b", "c"]
        edges = [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}]
        layers = roadbook._longest_path_layers(ids, edges)
        self.assertEqual(layers, {"a": 0, "b": 1, "c": 2})

    def test_longest_path_layers_takes_the_deepest_predecessor(self):
        # d depends on both a (layer 0) and c (layer 1, via b); its own
        # layer must be one past the deepest predecessor, not the shallowest.
        ids = ["a", "b", "c", "d"]
        edges = [{"from": "a", "to": "b"}, {"from": "b", "to": "c"},
                 {"from": "a", "to": "d"}, {"from": "c", "to": "d"}]
        layers = roadbook._longest_path_layers(ids, edges)
        self.assertEqual(layers["d"], 3)


class FileBased(unittest.TestCase):
    def _project(self, data):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / ".claude").mkdir()
        jp = root / ".claude" / "roadbook.json"
        jp.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n")
        return root, jp

    def test_recompute_writes_atomically_and_only_statuses(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "done"), task("b", "blocked", ["a"])]}])]
        root, jp = self._project(data)
        rc = roadbook.main(["recompute", str(jp)])
        self.assertEqual(rc, 0)
        after = json.loads(jp.read_text())
        self.assertEqual(after[0]["milestones"][0]["tasks"][1]["status"], "todo")

    def test_recompute_refuses_to_reformat(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "done"), task("b", "blocked", ["a"])]}])]
        root, jp = self._project(data)
        jp.write_text(json.dumps(data, indent=2) + "\n")  # space-indented
        rc = roadbook.main(["recompute", str(jp)])
        self.assertEqual(rc, 1)
        self.assertIn("blocked", jp.read_text())  # untouched
        rc = roadbook.main(["recompute", str(jp), "--reformat"])
        self.assertEqual(rc, 0)
        self.assertEqual(
            json.loads(jp.read_text())[0]["milestones"][0]["tasks"][1]["status"],
            "todo")

    def test_recompute_refuses_on_cycle(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "todo", ["b"]), task("b", "todo", ["a"])]}])]
        root, jp = self._project(data)
        self.assertEqual(roadbook.main(["recompute", str(jp)]), 1)

    def test_detect_rich_old_and_missing(self):
        rich = [phase([{"id": "M1", "name": "m", "tasks": [task("a")]}])]
        root, jp = self._project(rich)
        self.assertEqual(roadbook.main(["detect", str(jp)]), 0)

        old = {"roadmaps": [{"path": "docs/roadmaps/mvp.md"}]}
        root2, jp2 = self._project(old)
        self.assertEqual(roadbook.main(["detect", str(jp2)]), 3)

        self.assertEqual(roadbook.main(["detect", "/nonexistent/nowhere"]), 2)

    def test_detect_old_via_md_anchors(self):
        rich = [phase([{"id": "M1", "name": "m", "tasks": [task("a")]}])]
        root, jp = self._project(rich)
        md = root / "docs" / "roadbook"
        md.mkdir(parents=True)
        (md / "TEST.md").write_text('# Old\n<a name="m1-todo"></a>\n')
        self.assertEqual(roadbook.main(["detect", str(jp)]), 3)

    def test_validate_clean_and_dirty(self):
        clean = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "done"), task("b", "todo", ["a"])]}])]
        _root, jp = self._project(clean)
        self.assertEqual(roadbook.main(["validate", str(jp)]), 0)

        dirty = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a"), task("b", "todo", ["a"])]}])]  # b should be blocked
        _root2, jp2 = self._project(dirty)
        self.assertEqual(roadbook.main(["validate", str(jp2)]), 1)

    def test_render_writes_artefact(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "done"), task("b", "todo", ["a"])]}], name="My Phase")]
        root, jp = self._project(data)
        rc = roadbook.main(["render", str(jp)])
        self.assertEqual(rc, 0)
        out = root / "docs" / "artefacts" / "chart-my-phase.html"
        self.assertTrue(out.exists())
        html = out.read_text()
        self.assertIn("My Phase", html)
        self.assertNotIn("%%DATA%%", html)
        self.assertNotIn("%%TITLE%%", html)
        self.assertIn("chart-data", html)

    def test_the_chart_carries_its_theme_and_faces_and_asks_no_font_server(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [task("a")]}], name="My Phase")]
        root, jp = self._project(data)
        self.assertEqual(roadbook.main(["render", str(jp)]), 0)
        html = (root / "docs" / "artefacts" / "chart-my-phase.html").read_text()
        for token in ("%%THEME%%", "%%FONTS%%"):
            self.assertNotIn(token, html)
        self.assertNotIn("fonts.googleapis.com", html)
        self.assertIn("--ink: #1D2718;", html)  # the copied goblin theme
        for family in ("Cabin Sketch", "Special Elite", "IBM Plex Mono",
                       "IBM Plex Sans", "Permanent Marker"):
            with self.subTest(family=family):
                self.assertRegex(html, r"@font-face \{ font-family: '" + family
                                 + r"'; [^}]*src: url\(data:font/woff2;base64,[A-Za-z0-9+/=]{1000,}\)")

    def test_a_phase_named_like_a_placeholder_pulls_nothing_in(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [task("a")]}], name="%%FONTS%%")]
        root, jp = self._project(data)
        out = root / "chart.html"
        self.assertEqual(roadbook.main(["render", str(jp), "--out", str(out)]), 0)
        html = out.read_text()
        self.assertIn("<title>%%FONTS%%", html)
        self.assertEqual(html.count("@font-face {"), 6)

    def test_render_refuses_a_template_without_each_placeholder_once(self):
        template = Path(roadbook.__file__).resolve().parent.parent / "templates" / "chart.html"
        text = template.read_text()
        for token in ("%%THEME%%", "%%FONTS%%", "%%DATA%%"):
            self.assertEqual(text.count(token), 1, token)

    def test_soft_edges_survive_recompute_and_reconsecutive_graph_runs(self):
        # The regression this prevents: hand-authored dotted edges wiped by
        # a subsequent reconcile. softDependsOn must survive `recompute`
        # (which rewrites the file) and `graph --mermaid` must emit the
        # same dotted edge identically across two consecutive calls.
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "done"),
            task("b", "todo", soft=["a"])]}])]
        root, jp = self._project(data)
        self.assertEqual(roadbook.main(["recompute", str(jp)]), 0)
        after = json.loads(jp.read_text())
        self.assertEqual(
            after[0]["milestones"][0]["tasks"][1]["softDependsOn"], ["a"])

        _path, reloaded = roadbook.load(str(jp))
        ph = roadbook.active_phase(reloaded)
        first = roadbook.mermaid_source(ph)
        second = roadbook.mermaid_source(ph)
        self.assertIn("a -.-> b", first)
        self.assertEqual(first, second)

    def test_render_includes_assignee_when_set(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "todo", assignee="jason")]}], name="My Phase")]
        root, jp = self._project(data)
        rc = roadbook.main(["render", str(jp)])
        self.assertEqual(rc, 0)
        out = root / "docs" / "artefacts" / "chart-my-phase.html"
        html = out.read_text()
        self.assertIn("jason", html)  # assignee reaches the embedded data blob

    def _blob(self, out):
        html = out.read_text()
        start = html.find('<script id="chart-data"')
        start = html.find(">", start) + 1
        end = html.find("</script>", start)
        return json.loads(html[start:end])

    def test_render_project_field_explicit_and_fallback(self):
        # Explicit `project` field wins outright.
        explicit = [phase([{"id": "M1", "name": "m", "tasks": [task("a")]}],
                          name="My Phase", project="Iris")]
        root, jp = self._project(explicit)
        roadbook.main(["render", str(jp)])
        out = root / "docs" / "artefacts" / "chart-my-phase.html"
        self.assertEqual(self._blob(out)["project"], "Iris")

        # Absent: falls back to the project root directory name.
        implicit = [phase([{"id": "M1", "name": "m", "tasks": [task("a")]}],
                          name="My Phase")]
        root2, jp2 = self._project(implicit)
        roadbook.main(["render", str(jp2)])
        out2 = root2 / "docs" / "artefacts" / "chart-my-phase.html"
        self.assertEqual(self._blob(out2)["project"], root2.name)

    def test_render_dev_colours_in_blob(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", assignee="ravi"), task("b", assignee="noor"),
            task("c")]}], name="My Phase")]
        root, jp = self._project(data)
        roadbook.main(["render", str(jp)])
        out = root / "docs" / "artefacts" / "chart-my-phase.html"
        blob = self._blob(out)
        self.assertEqual(set(blob["devColours"]), {"ravi", "noor"})
        # two scouts this pair of names hashes apart; a chip is never told by colour alone
        self.assertEqual(blob["devColours"], {"ravi": "biro", "noor": "beetroot"})

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
                [sys.executable, str(Path(roadbook.__file__)), "render",
                 str(jp), "--out", str(out_path)],
                env=env, capture_output=True, text=True, check=True)
            outs.append(out_path.read_text())
        # Strip the one field that legitimately varies (the timestamp).
        stripped = [re.sub(r'"generated": "[^"]*"', '"generated": "X"', o)
                    for o in outs]
        self.assertEqual(stripped[0], stripped[1])


class Claims(unittest.TestCase):
    """A claim is the `started` field; views show it, recompute never reads
    it (see roadbook-conventions.md, Trails)."""

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
        self.assertEqual(roadbook._validate_phase(ph), [])


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
        ready = roadbook.build_ready(self._phase())
        self.assertEqual([c["id"] for c in ready["candidates"]], ["c"])
        self.assertEqual(
            [(c["id"], c["status"], c["display"], c["assignee"], c["started"])
             for c in ready["claimed"]],
            [("a", "todo", "in_progress", "jaz", "2026-09-20"),
             ("e", "todo", "in_progress", "", "2026-09-21")])

    def test_a_claim_on_a_reblocked_task_stays_visible(self):
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("a"), task("b", "blocked", ["a"], started="2026-09-20")]}])
        claim = roadbook.build_ready(ph)["claimed"][0]
        self.assertEqual((claim["status"], claim["display"]), ("blocked", "in_progress"))
        t, m, g = build_index(ph)
        self.assertEqual(recompute_all(t, m, g)["b"], "blocked")

    def test_stats_count_claims_as_an_overlay(self):
        stats = roadbook.build_stats(self._phase())
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
            roadbook.milestone_state({"todo": 2}, 0, total=2, in_progress=1),
            "inProgress")
        self.assertEqual(
            roadbook.milestone_state({"todo": 2}, 0, total=2), "todo")
        self.assertEqual(
            roadbook.milestone_state({"todo": 1, "blocked": 1}, 0, total=2,
                                    in_progress=1),
            "inProgress")

    def test_mermaid_classes_and_marks_claimed_tasks(self):
        src = roadbook.mermaid_source(self._phase())
        self.assertIn("classDef inProgress", src)
        self.assertIn('\ta["a: task a ▸"]', src)
        self.assertIn('\tc["c: task c"]', src)
        self.assertIn("\tclass a,e inProgress", src)

    def test_marker_fits_inside_the_label_limit(self):
        long = "x" * 80
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("a", started="2026-09-20", description=long)]}])
        line = next(l for l in roadbook.mermaid_source(ph).splitlines()
                    if l.startswith('\ta["'))
        label = line[len('\ta["'):-len('"]')]
        self.assertEqual(len(label), roadbook._LABEL_MAX)
        self.assertTrue(label.endswith("… ▸"))

    def test_dependency_chips_get_the_display_status(self):
        kinds = roadbook._dep_kinds(self._phase())
        self.assertEqual(kinds["a"]["display"], "in_progress")
        self.assertEqual(kinds["c"]["display"], "todo")


class ArtefactPath(unittest.TestCase):
    """The per-phase `artefact` key: where render and recompute --render
    write the dashboard, and the `config artefact` command that sets it."""

    def _project(self, data):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name).resolve()  # the CLI prints resolved paths
        (root / ".claude").mkdir()
        jp = root / ".claude" / "roadbook.json"
        jp.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n")
        return root, jp

    @staticmethod
    def _phase(name, milestones, **extra):
        """A phase dict in canonical field order, so a config write's insertion
        point can be asserted against the whole key sequence."""
        p = {"name": name, "path": "docs/roadbook/TEST.md"}
        for key in ("project", "artefact", "archived"):
            if key in extra:
                p[key] = extra[key]
        p["externalGates"] = []
        p["milestones"] = milestones
        return p

    def _data(self, **extra):
        return [self._phase("Tranche 1C: Post-DSG", [{"id": "M1", "name": "m", "tasks": [
            task("a", "done"), task("b", "todo", ["a"])]}], **extra)]

    def _run(self, argv):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = roadbook.main(argv)
        return rc, out.getvalue()

    def test_render_honours_artefact_key(self):
        root, jp = self._project(self._data(artefact="docs/artefacts/chart-t1c.html"))
        rc, out = self._run(["render", str(jp)])
        self.assertEqual(rc, 0)
        self.assertTrue((root / "docs" / "artefacts" / "chart-t1c.html").exists())
        self.assertFalse(
            (root / "docs" / "artefacts" / "chart-tranche-1c-post-dsg.html").exists())

    def test_render_out_flag_beats_artefact_key(self):
        root, jp = self._project(self._data(artefact="docs/artefacts/chart-t1c.html"))
        rc, _ = self._run(["render", str(jp), "--out", str(root / "elsewhere.html")])
        self.assertEqual(rc, 0)
        self.assertTrue((root / "elsewhere.html").exists())
        self.assertFalse((root / "docs" / "artefacts" / "chart-t1c.html").exists())

    def test_recompute_render_refreshes_artefact_key_path(self):
        root, jp = self._project(self._data(artefact="docs/artefacts/chart-t1c.html"))
        custom = root / "docs" / "artefacts" / "chart-t1c.html"
        custom.parent.mkdir(parents=True)
        custom.write_text("stale")
        rc, out = self._run(["recompute", str(jp), "--render"])
        self.assertEqual(rc, 0)
        self.assertIn(f"refreshed chart: {custom}", out)
        self.assertIn("chart-data", custom.read_text())
        self.assertFalse(
            (root / "docs" / "artefacts" / "chart-tranche-1c-post-dsg.html").exists())

    def test_recompute_render_notes_missing_artefact_at_key_path(self):
        root, jp = self._project(self._data(artefact="docs/artefacts/chart-t1c.html"))
        rc, out = self._run(["recompute", str(jp), "--render"])
        self.assertEqual(rc, 0)
        self.assertIn("no chart at", out)
        self.assertIn("chart-t1c.html", out)

    def test_render_phase_accepts_an_archived_phase(self):
        archived = self._phase(
            "Tranche 1B: Pre-DSG",
            [{"id": "M1", "name": "m", "tasks": [task("a", "done")]}],
            artefact="docs/artefacts/chart-t1b.html", archived=True)
        root, jp = self._project([archived, *self._data()])
        rc, _ = self._run(["render", str(jp), "--phase", "Tranche 1B: Pre-DSG"])
        self.assertEqual(rc, 0)
        self.assertTrue((root / "docs" / "artefacts" / "chart-t1b.html").exists())
        # without --phase the active phase is still the one rendered
        rc, out = self._run(["render", str(jp)])
        self.assertEqual(rc, 0)
        self.assertIn("chart-tranche-1c-post-dsg.html", out)
        # and the current-work commands still refuse an archived name
        rc, out = self._run(["ready", str(jp), "--phase", "Tranche 1B: Pre-DSG"])
        self.assertEqual(rc, 2)
        self.assertIn("no active phase named", out)

    def test_render_phase_unknown_name_lists_phases(self):
        _root, jp = self._project(self._data())
        rc, out = self._run(["render", str(jp), "--phase", "Nope"])
        self.assertEqual(rc, 2)
        self.assertIn("no phase named 'Nope'", out)
        self.assertIn("Tranche 1C: Post-DSG", out)

    def test_config_sets_key_in_field_order_and_writes_canonically(self):
        root, jp = self._project(self._data(project="CHIRPdb", archived=False))
        rc, out = self._run(["config", "artefact", "docs/artefacts/chart-t1c.html",
                             str(jp)])
        self.assertEqual(rc, 0, out)
        text = jp.read_text()
        after = json.loads(text)
        self.assertEqual(after[0]["artefact"], "docs/artefacts/chart-t1c.html")
        self.assertEqual(list(after[0]),
                         ["name", "path", "project", "artefact", "min_plugin",
                          "archived", "externalGates", "milestones"])
        self.assertEqual(text, roadbook._canonical_text(after))
        self.assertIn("chart-t1c.html", out)
        self.assertIn("no chart at", out)  # nothing rendered yet
        self.assertIn('render --phase "Tranche 1C: Post-DSG"', out)

    def test_config_notes_a_dashboard_left_at_the_old_path(self):
        root, jp = self._project(self._data())
        self.assertEqual(self._run(["render", str(jp)])[0], 0)
        old = root / "docs" / "artefacts" / "chart-tranche-1c-post-dsg.html"
        self.assertTrue(old.exists())
        rc, out = self._run(["config", "artefact", "docs/artefacts/chart-t1c.html",
                             str(jp)])
        self.assertEqual(rc, 0)
        self.assertIn(f"old path {old}", out)
        self.assertEqual(self._run(["render", str(jp)])[0], 0)
        self.assertTrue((root / "docs" / "artefacts" / "chart-t1c.html").exists())

    def test_config_case_only_change_is_not_an_old_dashboard(self):
        # On a case-insensitive filesystem (macOS default) the slug file and a
        # case variant of it are one file; the note must not tell the user to
        # delete their live dashboard.
        root, jp = self._project(self._data())
        self.assertEqual(self._run(["render", str(jp)])[0], 0)
        old = root / "docs" / "artefacts" / "chart-tranche-1c-post-dsg.html"
        upper = old.with_name("chart-Tranche-1C-Post-DSG.html")
        if not upper.exists():
            self.skipTest("case-sensitive filesystem; nothing to collide")
        rc, out = self._run(["config", "artefact",
                             "docs/artefacts/chart-Tranche-1C-Post-DSG.html",
                             str(jp)])
        self.assertEqual(rc, 0, out)
        self.assertNotIn("old path", out)
        self.assertNotIn("no chart at", out)

    def test_config_clear_removes_key_with_path_in_either_position(self):
        root, jp = self._project(self._data(artefact="docs/artefacts/chart-t1c.html"))
        rc, out = self._run(["config", "artefact", "--clear", str(jp)])
        self.assertEqual(rc, 0, out)
        self.assertNotIn("artefact", json.loads(jp.read_text())[0])
        self.assertIn("chart-tranche-1c-post-dsg.html", out)
        # clearing an absent key is a no-op, not an error
        rc, out = self._run(["config", "artefact", str(jp), "--clear"])
        self.assertEqual(rc, 0)
        self.assertIn("nothing to clear", out)

    def test_config_needs_a_value_or_clear_not_both(self):
        root, jp = self._project(self._data())
        with contextlib.chdir(root):  # no value, roadbook found from the cwd
            rc, out = self._run(["config", "artefact"])
        self.assertEqual(rc, 2)
        self.assertIn("--clear", out)
        rc, _ = self._run(["config", "artefact", "x.html", str(jp), "--clear"])
        self.assertEqual(rc, 2)
        self.assertNotIn("artefact", json.loads(jp.read_text())[0])
        # a value with no roadbook path is a mistyped set, not the roadbook path
        with contextlib.chdir(root):
            rc, out = self._run(["config", "artefact", "docs/x.html", "--clear"])
        self.assertEqual(rc, 2)
        self.assertIn("--clear", out)
        self.assertNotIn("not found", out)

    def test_config_phase_reaches_an_archived_phase(self):
        archived = self._phase(
            "Tranche 1B: Pre-DSG",
            [{"id": "M1", "name": "m", "tasks": [task("a", "done")]}],
            archived=True)
        _root, jp = self._project([archived, *self._data()])
        rc, out = self._run(["config", "artefact", "docs/artefacts/chart-t1b.html",
                             str(jp), "--phase", "Tranche 1B: Pre-DSG"])
        self.assertEqual(rc, 0, out)
        after = json.loads(jp.read_text())
        self.assertEqual(after[0]["artefact"], "docs/artefacts/chart-t1b.html")
        self.assertEqual(list(after[0])[:4], ["name", "path", "artefact", "archived"])
        self.assertNotIn("artefact", after[1])

    def test_config_refuses_bad_paths(self):
        _root, jp = self._project(self._data())
        for bad, why in [("/tmp/roadmap.html", "absolute"),
                         ("../roadmap.html", "leaves the project root"),
                         ("docs/roadmap.md", "does not end in .html")]:
            rc, out = self._run(["config", "artefact", bad, str(jp)])
            self.assertEqual(rc, 1, bad)
            self.assertIn(why, out)
        self.assertNotIn("artefact", json.loads(jp.read_text())[0])

    def test_config_refuses_to_reformat(self):
        _root, jp = self._project(self._data())
        jp.write_text(json.dumps(json.loads(jp.read_text()), indent=2) + "\n")
        rc, out = self._run(["config", "artefact", "docs/a.html", str(jp)])
        self.assertEqual(rc, 1)
        self.assertIn("--reformat", out)
        rc, _ = self._run(["config", "artefact", "docs/a.html", str(jp), "--reformat"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(jp.read_text())[0]["artefact"], "docs/a.html")

    def test_validate_reports_a_hand_edited_bad_artefact(self):
        _root, jp = self._project(self._data(artefact="../escape.html"))
        rc, out = self._run(["validate", str(jp)])
        self.assertEqual(rc, 1)
        self.assertIn("leaves the project root", out)
        self.assertIn("does not end in .html", self._run(
            ["validate", str(self._project(self._data(artefact="docs/x.htm"))[1])])[1])
        rc, out = self._run(["validate", str(self._project(self._data(artefact=""))[1])])
        self.assertEqual(rc, 1)
        self.assertIn("is not a path", out)
        # and render refuses rather than writing outside the project
        rc, out = self._run(["render", str(jp)])
        self.assertEqual(rc, 2)
        self.assertIn("leaves the project root", out)


class ClaimCommand(unittest.TestCase):
    def _project(self, tasks):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        jp = Path(tmp.name) / ".claude" / "roadbook.json"
        jp.parent.mkdir()
        data = [phase([{"id": "M1", "name": "m", "tasks": tasks}],
                     min_plugin=STAMPED)]
        jp.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n")
        return jp

    def _task(self, jp, tid):
        tasks = json.loads(jp.read_text())[0]["milestones"][0]["tasks"]
        return next(t for t in tasks if t["id"] == tid)

    def _run(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = roadbook.main(list(argv))
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
                (["claim", "c"], "already on a trail"),
                (["claim", "a", "--assignee", "Max"], "--reassign"),
                (["claim", "zz"], "no waypoint"),
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
        self.assertTrue(any("not a YYYY-MM-DD date" in p for p in roadbook._validate_phase(ph)))

    def test_release_refuses_an_unclaimed_task(self):
        rc, out = self._run("release", "a", str(self._project([task("a")])))
        self.assertEqual(rc, 1)
        self.assertIn("not on a trail", out)

    def test_validate_checks_started_and_points_at_claims(self):
        ph = phase([{"id": "M1", "name": "m", "tasks": [
            task("a", started="soon"), task("b", "in_progress")]}])
        problems = roadbook._validate_phase(ph)
        self.assertTrue(any("started 'soon'" in p for p in problems))
        self.assertTrue(any("run roadbook.py claim" in p for p in problems))


class StackedClaim(unittest.TestCase):
    """claim takes a blocked task when every unmet blocker is already claimed."""

    def _project(self, milestones, gates=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        jp = Path(tmp.name) / ".claude" / "roadbook.json"
        jp.parent.mkdir()
        data = [phase(milestones, gates, min_plugin=STAMPED)]
        jp.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n")
        return jp

    def _flat(self, tasks, gates=None):
        return self._project([{"id": "M1", "name": "m", "tasks": tasks}], gates)

    def _started(self, jp, tid):
        for m in json.loads(jp.read_text())[0]["milestones"]:
            for t in m["tasks"]:
                if t["id"] == tid:
                    return t.get("started")

    _run = ClaimCommand._run

    def test_claims_a_blocked_task_whose_only_blocker_is_claimed(self):
        jp = self._flat([task("a", started="2026-10-01"), task("b", "blocked", ["a"])])
        rc, out = self._run("claim", "b", str(jp), "--date", "2026-10-02")
        self.assertEqual(rc, 0, out)
        self.assertIn("stacked on a", out)
        self.assertEqual(self._started(jp, "b"), "2026-10-02")

    def test_refuses_and_names_the_unclaimed_blockers(self):
        jp = self._flat([task("a", started="2026-10-01"), task("c"),
                         task("b", "blocked", ["a", "c"])])
        before = jp.read_text()
        rc, out = self._run("claim", "b", str(jp))
        self.assertEqual(rc, 1)
        self.assertIn("not on a trail: c", out)
        self.assertNotIn("not on a trail: a", out)
        self.assertEqual(jp.read_text(), before)

    def test_a_milestone_blocker_needs_each_unfinished_member_claimed(self):
        members = [task("m1", started="2026-10-01"), task("m2", "done"), task("m3")]
        jp = self._project([
            {"id": "M1", "name": "one", "tasks": members},
            {"id": "M2", "name": "two", "tasks": [task("b", "blocked", ["M1"])]}])
        rc, out = self._run("claim", "b", str(jp))
        self.assertEqual(rc, 1)
        self.assertIn("not on a trail: m3", out)
        self.assertNotIn("m2", out)
        members[2]["started"] = "2026-10-01"
        jp = self._project([
            {"id": "M1", "name": "one", "tasks": members},
            {"id": "M2", "name": "two", "tasks": [task("b", "blocked", ["M1"])]}])
        self.assertEqual(self._run("claim", "b", str(jp))[0], 0)

    def test_a_gate_in_dependson_keeps_the_task_unclaimable(self):
        gate = {"id": "G1", "name": "g", "status": "blocked", "blocks": ["b"]}
        jp = self._flat([task("a", started="2026-10-01"),
                         task("b", "blocked", ["a", "G1"])], [gate])
        rc, out = self._run("claim", "b", str(jp))
        self.assertEqual(rc, 1)
        self.assertIn("gate G1", out)

    def test_a_gate_that_lists_the_task_in_blocks_keeps_it_unclaimable(self):
        gate = {"id": "G1", "name": "g", "status": "blocked", "blocks": ["b"]}
        jp = self._flat([task("a", started="2026-10-01"),
                         task("b", "blocked", ["a"])], [gate])
        rc, out = self._run("claim", "b", str(jp))
        self.assertEqual(rc, 1)
        self.assertIn("gate G1", out)

    def test_a_done_gate_still_in_dependson_keeps_the_task_unclaimable(self):
        gate = {"id": "G1", "name": "g", "status": "done", "blocks": ["b"]}
        jp = self._flat([task("a", started="2026-10-01"),
                         task("b", "blocked", ["a", "G1"])], [gate])
        rc, out = self._run("claim", "b", str(jp))
        self.assertEqual(rc, 1)
        self.assertIn("gate G1", out)

    def test_a_done_gate_does_not_hold_the_task(self):
        gate = {"id": "G1", "name": "g", "status": "done", "blocks": ["b"]}
        jp = self._flat([task("a", started="2026-10-01"),
                         task("b", "blocked", ["a"])], [gate])
        self.assertEqual(self._run("claim", "b", str(jp))[0], 0)

    def test_a_paused_blocker_or_held_task_still_refuses(self):
        jp = self._flat([task("a", "paused", ["z"], started="2026-10-01"),
                         task("z", "paused", started="2026-10-01"),
                         task("b", "blocked", ["a"]),
                         task("h", "paused")])
        for tid in ("b", "h"):
            rc, out = self._run("claim", tid, str(jp))
            self.assertEqual(rc, 1, tid)
            self.assertNotIn("stacked", out)

    def test_every_other_refusal_still_applies_to_a_stacked_claim(self):
        jp = self._flat([task("a", started="2026-10-01"),
                         task("b", "blocked", ["a"], assignee="Jaz"),
                         task("c", "blocked", ["a"], started="2026-10-03")])
        for argv, needle in [(["claim", "b", "--assignee", "Max"], "--reassign"),
                             (["claim", "c"], "already on a trail")]:
            rc, out = self._run(argv[0], argv[1], str(jp), *argv[2:])
            self.assertEqual(rc, 1, argv)
            self.assertIn(needle, out, argv)

    def test_a_stacked_claim_releases_byte_identically(self):
        jp = self._flat([task("a", started="2026-10-01"), task("b", "blocked", ["a"])])
        before = jp.read_text()
        self.assertEqual(self._run("claim", "b", str(jp))[0], 0)
        self.assertEqual(self._run("release", "b", str(jp))[0], 0)
        self.assertEqual(jp.read_text(), before)

    def test_unmet_blockers_in_depends_order(self):
        tasks, milestones, gates = build_index(phase(
            [{"id": "M1", "name": "m", "tasks": [
                task("a", "done"), task("c"), task("b", "blocked", ["a", "c", "G1"])]}],
            [{"id": "G1", "name": "g", "status": "blocked", "blocks": []}]))
        self.assertEqual(unmet_blockers("b", tasks, milestones, gates),
                         [("task", "c"), ("gate", "G1")])


class AssignCommand(unittest.TestCase):
    _project = ClaimCommand._project
    _task = ClaimCommand._task
    _run = ClaimCommand._run

    def test_assign_writes_assignee_in_field_order_without_started(self):
        jp = self._project([task("a", notes="n", pr=12)])
        rc, out = self._run("assign", "a", str(jp), "--assignee", "Jaz")
        self.assertEqual(rc, 0)
        self.assertIn("assigned a to Jaz", out)
        self.assertEqual(list(self._task(jp, "a")),
                         ["id", "description", "status", "dependsOn", "notes",
                          "assignee", "pr"])

    def test_assign_replaces_and_reports_the_previous_assignee(self):
        jp = self._project([task("a", assignee="Jaz")])
        rc, out = self._run("assign", "a", str(jp), "--assignee", "Max")
        self.assertEqual(rc, 0)
        self.assertIn("(was Jaz)", out)
        self.assertEqual(self._task(jp, "a")["assignee"], "Max")

    def test_same_name_keeps_its_spelling_and_does_not_rewrite(self):
        jp = self._project([task("a", assignee="Jaz")])
        before = jp.read_text()
        rc, out = self._run("assign", "a", str(jp), "--assignee", "jaz")
        self.assertEqual(rc, 0)
        self.assertIn("already assigned to Jaz", out)
        self.assertEqual(jp.read_text(), before)

    def test_unassign_removes_the_key_and_is_a_no_op_without_one(self):
        jp = self._project([task("a", assignee="Jaz"), task("b")])
        before = jp.read_text()
        self.assertEqual(self._run("assign", "a", str(jp), "--unassign")[0], 0)
        self.assertNotIn("assignee", self._task(jp, "a"))
        after = jp.read_text()
        rc, out = self._run("assign", "b", str(jp), "--unassign")
        self.assertEqual(rc, 0)
        self.assertIn("has no assignee", out)
        self.assertEqual(jp.read_text(), after)
        self.assertNotEqual(after, before)

    def test_assign_works_on_a_claimed_task_and_leaves_started(self):
        jp = self._project([task("a", assignee="Jaz", started="2026-09-01")])
        self.assertEqual(self._run("assign", "a", str(jp), "--assignee", "Max")[0], 0)
        self.assertEqual(self._task(jp, "a")["assignee"], "Max")
        self.assertEqual(self._task(jp, "a")["started"], "2026-09-01")

    def test_assign_then_unassign_is_byte_identical(self):
        jp = self._project([task("a", notes="n", pr=12)])
        before = jp.read_text()
        self._run("assign", "a", str(jp), "--assignee", "Jaz")
        self._run("assign", "a", str(jp), "--unassign")
        self.assertEqual(jp.read_text(), before)

    def test_assign_refusals_leave_the_file_alone(self):
        jp = self._project([task("a")])
        before = jp.read_text()
        for argv, needle in [
                (["assign", "a", "--assignee", "  "], "needs a name"),
                (["assign", "zz", "--assignee", "Max"], "no waypoint")]:
            rc, out = self._run(argv[0], argv[1], str(jp), *argv[2:])
            self.assertEqual(rc, 1, argv)
            self.assertIn(needle, out, argv)
        self.assertEqual(jp.read_text(), before)

    def test_assign_needs_exactly_one_of_assignee_or_unassign(self):
        jp = self._project([task("a")])
        for extra in ([], ["--assignee", "Max", "--unassign"]):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                roadbook.main(["assign", "a", str(jp), *extra])
            self.assertEqual(caught.exception.code, 2)


class EndedField(unittest.TestCase):
    def _problems(self, **fields):
        ph = phase([{"id": "M1", "name": "m", "tasks": [task("a", **fields)]}])
        return roadbook._validate_phase(ph)

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
        self.assertEqual(roadbook.TASK_FIELD_ORDER[-3:], ["started", "ended", "pr"])


class EndCommand(unittest.TestCase):
    def _project(self, tasks):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        jp = Path(tmp.name) / ".claude" / "roadbook.json"
        jp.parent.mkdir()
        data = [phase([{"id": "M1", "name": "m", "tasks": tasks}],
                     min_plugin=STAMPED)]
        jp.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n")
        return jp

    def _task(self, jp, tid):
        tasks = json.loads(jp.read_text())[0]["milestones"][0]["tasks"]
        return next(t for t in tasks if t["id"] == tid)

    def _run(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = roadbook.main(list(argv))
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
        self.assertEqual(self._task(jp, "a")["ended"], roadbook.date.today().isoformat())

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
        found = roadbook.ended_from_history(versions, "2026-10-02")
        self.assertEqual(found, {"a": ("2026-09-10", "s2", "transition")})

    def test_reopened_then_redone_uses_the_latest_finish(self):
        versions = [("s1", "2026-09-01", {"a": "done"}),
                    ("s2", "2026-09-05", {"a": "todo"}),
                    ("s3", "2026-09-09", {"a": "done"})]
        self.assertEqual(roadbook.ended_from_history(versions, "x")["a"][0],
                         "2026-09-09")

    def test_done_on_first_sight_is_flagged_first_seen(self):
        versions = [("s1", "2026-09-01", {"a": "done"}),
                    ("s2", "2026-09-05", {"a": "done", "b": "done"})]
        found = roadbook.ended_from_history(versions, "x")
        self.assertEqual(found["a"], ("2026-09-01", "s1", "first-seen"))
        self.assertEqual(found["b"], ("2026-09-05", "s2", "first-seen"))

    def test_working_tree_only_done_is_dated_today(self):
        versions = [("s1", "2026-09-01", {"a": "todo"}),
                    ("", "", {"a": "done"})]
        self.assertEqual(roadbook.ended_from_history(versions, "2026-10-02")["a"],
                         ("2026-10-02", "", "uncommitted"))

    def test_task_no_longer_done_at_the_end_is_dropped(self):
        versions = [("s1", "2026-09-01", {"a": "done"}),
                    ("s2", "2026-09-05", {"a": "todo"})]
        self.assertEqual(roadbook.ended_from_history(versions, "x"), {})


@unittest.skipUnless(shutil.which("git"), "git not installed")
class GitRoadbook(unittest.TestCase):
    """A temporary repository holding .claude/roadbook.json, with dated
    commits. Helpers only; the test classes below add the cases."""

    def _git(self, *argv, when=None):
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        if when:
            env["GIT_COMMITTER_DATE"] = env["GIT_AUTHOR_DATE"] = f"{when}T12:00:00"
        subprocess.run(["git", "-C", str(self.root), *argv], check=True,
                       capture_output=True, env=env)

    def _write(self, tasks):
        data = [phase([{"id": "M1", "name": "m", "tasks": tasks}],
                     min_plugin=STAMPED)]
        self.jp.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n")

    def _commit(self, tasks, when, message="roadbook"):
        self._write(tasks)
        self._git("add", ".")
        self._git("commit", "-q", "-m", message, when=when)

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.jp = self.root / ".claude" / "roadbook.json"
        self.jp.parent.mkdir()
        self._git("init", "-q", "-b", "main")

    def _run(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = roadbook.main(list(argv))
        return rc, out.getvalue()

    def _tasks(self):
        return {t["id"]: t for t in
                json.loads(self.jp.read_text())[0]["milestones"][0]["tasks"]}


@unittest.skipUnless(shutil.which("git"), "git not installed")
class BackfillEnded(GitRoadbook):
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
        self.assertEqual(self._tasks()["a"]["ended"], roadbook.date.today().isoformat())

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
        jp = Path(tmp.name) / ".claude" / "roadbook.json"
        jp.parent.mkdir()
        data = [phase([{"id": "M1", "name": "m", "tasks": [task("a", "done")]}])]
        jp.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n")
        rc, out = self._run("backfill-ended", str(jp))
        self.assertEqual(rc, 1)
        self.assertIn("git", out)


@unittest.skipUnless(shutil.which("git"), "git not installed")
class StampEnded(GitRoadbook):
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
        self.assertIn("ended 1 waypoint(s) on 2026-10-02: a", out)
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
        self.assertIn("ended 0 waypoint(s)", out)
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
    clone on main and a roadbook with two ready waypoints, one blocked and one
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
        (self.repo / ".claude" / "roadbook.json").write_text(
            json.dumps(data, indent="\t", ensure_ascii=False) + "\n")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-qm", "init")
        self.git(self.repo, "push", "-q", "-u", "origin", "main")
        self.git(self.repo, "remote", "set-head", "origin", "main")

    def git(self, cwd, *args):
        return subprocess.run(["git", "-C", str(cwd), *args], env=self.env,
                              capture_output=True, text=True, check=True).stdout.strip()

    def cli(self, *args, stdin=""):
        return subprocess.run([sys.executable, str(Path(roadbook.__file__)), *args],
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
            self.git(self.repo, "config", "--get", "branch.feat/x.roadbookClaim"), "asked")
        self.assertEqual(self.hook("post-tool-use", self.repo), "")

    def test_session_start_nudges_until_the_branch_claims(self):
        self.git(self.repo, "checkout", "-q", "-b", "feat/x")
        nudge = self.hook("session-start", self.repo)
        self.assertIn("claims no roadbook waypoint", nudge)
        self.assertIn("goblin-scout:start-trail skill", nudge)
        self.assertEqual(self.cli("claim", "b", str(self.repo / ".claude" / "roadbook.json")).returncode, 0)
        self.assertEqual(self.hook("session-start", self.repo).strip(),
                         "Roadbook: branch `feat/x` claims b.")

    def test_a_worktree_claim_targets_the_worktree(self):
        wt = self.root / "wt"
        self.git(self.repo, "worktree", "add", "-q", str(wt), "-b", "feat/y")
        text = self.context(self.hook("post-tool-use", self.repo))
        self.assertIn(f"claim <ID> {wt / '.claude' / 'roadbook.json'}", text)
        self.assertIn(f"git -C {wt} commit", text)
        self.assertNotIn(str(self.repo / ".claude"), text)

    def test_a_decline_silences_the_branch(self):
        self.git(self.repo, "checkout", "-q", "-b", "chore/x")
        self.git(self.repo, "config", "branch.chore/x.roadbookClaim", "none")
        self.assertEqual(self.hook("session-start", self.repo), "")
        self.assertEqual(self.hook("post-tool-use", self.repo), "")

    def test_a_local_copy_of_a_remote_branch_is_not_nudged(self):
        self.git(self.repo, "checkout", "-q", "-b", "feat/remote")
        self.git(self.repo, "push", "-q", "origin", "feat/remote")
        self.git(self.repo, "checkout", "-q", "main")
        self.git(self.repo, "branch", "-q", "-D", "feat/remote")
        self.git(self.repo, "checkout", "-q", "feat/remote")
        self.assertEqual(self.hook("post-tool-use", self.repo), "")

    def test_subagents_and_repos_without_a_roadbook_are_silent(self):
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
        self.assertIn("claims no roadbook waypoint", self.hook("session-start", self.repo))

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
        self.assertIn("claims no roadbook waypoint", self.hook("session-start", self.repo))
        self.assertEqual(self.hook("post-tool-use", self.repo), "")

    def test_bad_input_never_fails_the_hook(self):
        done = self.cli("hook", "post-tool-use", stdin="not json")
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))

    def _legacy_main(self):
        """Rewind main to a roadmap plugin's file: .claude/roadmaps.json."""
        self.git(self.repo, "mv", ".claude/roadbook.json", ".claude/roadmaps.json")
        self.git(self.repo, "commit", "-qm", "a 2.x project")
        self.git(self.repo, "push", "-q", "origin", "main")

    def test_an_unmigrated_project_is_still_nudged(self):
        self._legacy_main()
        self.git(self.repo, "checkout", "-q", "-b", "feat/old")
        self.assertIn("claims no roadbook waypoint", self.hook("session-start", self.repo))

    def test_a_branch_that_migrated_still_compares_with_the_old_file_at_its_base(self):
        self._legacy_main()
        self.git(self.repo, "checkout", "-q", "-b", "feat/moved")
        legacy = self.repo / ".claude" / "roadmaps.json"
        claimed = self.cli("claim", "b", str(legacy))
        self.assertEqual(claimed.returncode, 0, claimed.stdout)
        self.assertFalse(legacy.exists())
        self.assertEqual(self.hook("session-start", self.repo).strip(),
                         "Roadbook: branch `feat/moved` claims b.")

    def test_a_decline_under_the_old_key_still_silences_the_branch(self):
        self.git(self.repo, "checkout", "-q", "-b", "chore/old")
        self.git(self.repo, "config", "branch.chore/old.roadmapClaim", "none")
        self.assertEqual(self.hook("session-start", self.repo), "")
        self.assertEqual(self.hook("post-tool-use", self.repo), "")

    def test_an_old_asked_marker_is_not_asked_again(self):
        self.git(self.repo, "checkout", "-q", "-b", "feat/asked")
        self.git(self.repo, "config", "branch.feat/asked.roadmapClaim", "asked")
        self.assertEqual(self.hook("post-tool-use", self.repo), "")


class LegacyFixture(unittest.TestCase):
    """A project directory with a .claude folder and a 2.x-shaped phase list.
    Helpers only; the classes below add the cases."""

    def setUp(self):
        self.addCleanup(setattr, roadbook, "PLUGIN_VERSION", roadbook.PLUGIN_VERSION)
        roadbook.PLUGIN_VERSION = "3.0.0"
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.claude = self.root / ".claude"
        self.claude.mkdir()
        self.legacy = self.claude / "roadmaps.json"
        self.legacy_local = self.claude / "roadmaps.local.json"
        self.new = self.claude / "roadbook.json"
        self.new_local = self.claude / "roadbook.local.json"

    def _phases(self):
        """A live phase on the default chart path, a live phase with its own
        chart path and an archived phase on the default, all saying roadmap
        in values that must survive untouched."""
        return [
            phase([{"id": "M1", "name": "roadmap work", "tasks": [
                task("a", "done", notes="see the roadmap"), task("b", "todo", ["a"])]}],
                name="Phase 1", archived=True, path="docs/roadmaps/TEST.md"),
            phase([{"id": "M2", "name": "m", "tasks": [
                task("c", "done"), task("d", "todo", ["c"], description="roadmap: d")]}],
                name="Phase 2", path="docs/roadmaps/TEST.md"),
        ]

    def _write(self, path, data):
        path.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n")

    def _run(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = roadbook.main(list(argv))
        return rc, out.getvalue(), err.getvalue()

    def _without_migration_marks(self, data, pinned):
        """`data` with the stamp and the pinned chart paths taken off again."""
        for ph in data:
            ph.pop("min_plugin", None)
            if ph.get("name") in pinned:
                ph.pop("artefact")
        return data


class LegacyMigration(LegacyFixture):
    """A roadmap plugin's .claude/roadmaps.json (and the local file beside
    it) under goblin-scout 3.0.0: read as it is, moved to the roadbook names
    on the first write with one line of notice (and a note per local phase
    whose chart moves), no value rewritten, the chart's old default path
    pinned and the 3.0.0 stamp that makes a 2.x plugin refuse the result."""

    def test_an_old_file_is_read_where_it_is(self):
        self._write(self.legacy, self._phases())
        before = self.legacy.read_text()
        rc, out, err = self._run("validate", str(self.root))
        self.assertEqual(rc, 0, out)
        self.assertEqual((self.legacy.read_text(), err), (before, ""))
        self.assertFalse(self.new.exists())
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(self.root)
        self.assertEqual(roadbook.resolve_roadbook_path(), self.legacy)

    def test_the_first_write_moves_the_file_with_one_line_of_notice(self):
        self._write(self.legacy, self._phases())
        rc, out, err = self._run("claim", "d", str(self.legacy), "--date", "2026-11-18")
        self.assertEqual(rc, 0, out)
        self.assertFalse(self.legacy.exists())
        self.assertTrue(self.new.exists())
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertIn(".claude/roadmaps.json", err)
        self.assertIn(".claude/roadbook.json", err)

    def test_no_value_is_rewritten_and_only_the_default_chart_path_is_pinned(self):
        original = self._phases()
        original[1]["artefact"] = "docs/roadmaps/own-chart.html"
        self._write(self.legacy, original)
        self.assertEqual(self._run("claim", "d", str(self.legacy), "--date", "2026-11-18")[0], 0)
        migrated = json.loads(self.new.read_text())
        self.assertEqual(migrated[0]["artefact"], "docs/artefacts/roadmap-phase-1.html")
        self.assertEqual(migrated[1]["artefact"], "docs/roadmaps/own-chart.html")
        expected = self._phases()
        expected[1]["artefact"] = "docs/roadmaps/own-chart.html"
        expected[1]["milestones"][0]["tasks"][1]["started"] = "2026-11-18"
        self.assertEqual(self._without_migration_marks(migrated, {"Phase 1"}), expected)

    def test_a_pinned_chart_renders_where_the_old_default_put_it(self):
        self._write(self.legacy, self._phases())
        self._run("claim", "d", str(self.legacy), "--date", "2026-11-18")
        rc, out, _err = self._run("render", str(self.new), "--phase", "Phase 1")
        self.assertEqual(rc, 0, out)
        self.assertTrue((self.root / "docs" / "artefacts" / "roadmap-phase-1.html").exists())

    def test_an_unmoved_file_renders_where_the_old_default_put_it(self):
        self._write(self.legacy, self._phases())
        rc, out, _err = self._run("render", str(self.legacy))
        self.assertEqual(rc, 0, out)
        self.assertTrue((self.root / "docs" / "artefacts" / "roadmap-phase-2.html").exists())
        self.assertFalse(self.new.exists())

    def test_a_new_roadbook_gets_the_new_default_chart_path(self):
        self._write(self.new, self._phases()[1:])
        rc, out, _err = self._run("render", str(self.new))
        self.assertEqual(rc, 0, out)
        self.assertTrue((self.root / "docs" / "artefacts" / "chart-phase-2.html").exists())
        self.assertNotIn("artefact", json.loads(self.new.read_text())[0])

    def test_the_live_phase_is_stamped_3_0_0_and_a_2_x_plugin_refuses_it(self):
        self._write(self.legacy, self._phases())
        self._run("claim", "d", str(self.legacy), "--date", "2026-11-18")
        migrated = json.loads(self.new.read_text())
        self.assertEqual(migrated[1]["min_plugin"], "3.0.0")
        self.assertNotIn("min_plugin", migrated[0])  # archived, as ever
        before = self.new.read_text()
        roadbook.PLUGIN_VERSION = "2.10.0"
        rc, out, _err = self._run("release", "d", str(self.new))
        self.assertEqual(rc, 2)
        self.assertIn("3.0.0", out)
        self.assertEqual(self.new.read_text(), before)

    def test_the_local_file_moves_with_the_committed_one(self):
        committed = self._phases()
        mirrored = [phase([{"id": "M9", "name": "mirror", "tasks": [task("j1", local=True)]}],
                          name="Jira", source={"kind": "jira", "project": "J"})]
        self._write(self.legacy, committed)
        self._write(self.legacy_local, mirrored)
        rc, out, err = self._run("claim", "j1", str(self.root), "--date", "2026-11-18")
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertFalse(self.legacy.exists() or self.legacy_local.exists())
        local = json.loads(self.new_local.read_text())
        self.assertEqual(local[0]["milestones"][0]["tasks"][0]["started"], "2026-11-18")
        self.assertEqual(local[0]["artefact"], "docs/artefacts/roadmap-jira.html")
        moved = json.loads(self.new.read_text())
        self.assertEqual(self._without_migration_marks(moved, {"Phase 1", "Phase 2"}),
                         self._phases())

    def test_one_fixture_moves_with_one_line_and_a_2x_plugin_refuses_both_files(self):
        self._write(self.legacy, self._phases())
        self._write(self.legacy_local, [phase(
            [{"id": "M9", "name": "mirror", "tasks": [task("j1", local=True)]}],
            name="Jira", source={"kind": "jira", "project": "J"})])
        rc, out, err = self._run("claim", "j1", str(self.root), "--date", "2026-11-18")
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(err.splitlines()), 1, err)
        before = {p: p.read_text() for p in (self.new, self.new_local)}
        roadbook.PLUGIN_VERSION = "2.10.0"
        for target, argv in ((self.new, ("claim", "d")), (self.new_local, ("release", "j1"))):
            with self.subTest(file=target.name):
                rc, out, _err = self._run(*argv, str(target))
                self.assertEqual(rc, 2)
                self.assertIn("3.0.0", out)
        self.assertEqual({p: p.read_text() for p in before}, before)

    def test_a_local_file_moved_alongside_arrives_byte_for_byte(self):
        # space-indented, ASCII-escaped and with no trailing newline: nothing a
        # roadbook writer would produce, and none of it may be rewritten
        self._write(self.legacy, self._phases())
        mirror = [phase([{"id": "M9", "name": "mirror – café", "tasks": [task("j1", local=True)]}],
                        name="Jira", source={"kind": "jira", "project": "J"})]
        original = json.dumps(mirror, indent=2).encode("utf-8")
        self.legacy_local.write_bytes(original)
        rc, out, err = self._run("claim", "d", str(self.legacy), "--date", "2026-11-18")
        self.assertEqual(rc, 0, out)
        self.assertFalse(self.legacy_local.exists())
        self.assertEqual(self.new_local.read_bytes(), original)
        self.assertEqual(len(err.splitlines()), 2, err)  # the move, then the chart note
        self.assertIn(".claude/roadmaps.local.json to .claude/roadbook.local.json", err)

    def test_the_notice_names_each_local_phase_whose_chart_now_renders_elsewhere(self):
        # a local file moved byte for byte carries no chart pin (ruled
        # 2026-11-19), so the notice must not claim every chart keeps its path
        self._write(self.legacy, self._phases())
        mirror = [phase([{"id": "M9", "name": "mirror", "tasks": [task("j1", local=True)]}],
                        name="Jira", source={"kind": "jira", "project": "J"}),
                  phase([{"id": "M8", "name": "own", "tasks": [task("j2", local=True)]}],
                        name="Pinned", artefact="site/pinned.html",
                        source={"kind": "jira", "project": "K"})]
        self._write(self.legacy_local, mirror)
        rc, out, err = self._run("claim", "d", str(self.legacy), "--date", "2026-11-18")
        self.assertEqual(rc, 0, out)
        lines = err.splitlines()
        self.assertEqual(len(lines), 2, err)
        self.assertNotIn("the chart and projections keep their paths", lines[0])
        self.assertIn("every chart but those noted below", lines[0])
        self.assertIn("'Jira'", lines[1])
        self.assertIn("docs/artefacts/chart-jira.html", lines[1])
        self.assertIn("rebind --outputs", lines[1])
        self.assertNotIn("Pinned", err)

    def test_a_write_to_the_local_file_refuses_to_reformat_the_committed_one(self):
        # the review's repro: a two-space roadmaps.json beside a local file,
        # and a claim that writes the local one
        self.legacy.write_text(json.dumps(self._phases(), indent=2) + "\n")
        self._write(self.legacy_local, [phase(
            [{"id": "M9", "name": "mirror", "tasks": [task("j1", local=True)]}],
            name="Jira", source={"kind": "jira", "project": "J"})])
        before = {f: f.read_bytes() for f in (self.legacy, self.legacy_local)}
        rc, out, _err = self._run("claim", "j1", str(self.root), "--date", "2026-11-18")
        self.assertEqual(rc, 2, out)
        self.assertIn(".claude/roadmaps.json is not in canonical form", out)
        self.assertIn("rebind --reformat", out)
        self.assertEqual({f: f.read_bytes() for f in before}, before)
        self.assertFalse(self.new.exists() or self.new_local.exists())
        rc, out, _err = self._run("rebind", str(self.root), "--reformat")
        self.assertEqual(rc, 0, out)
        rc, out, _err = self._run("claim", "j1", str(self.root), "--date", "2026-11-18")
        self.assertEqual(rc, 0, out)

    def test_a_sibling_that_is_not_utf8_still_moves_byte_for_byte(self):
        # round 2's repro: one Latin-1 byte in either sibling must not crash
        # the move; such a file is not a phase array and travels untouched
        mirror = json.dumps([phase([{"id": "M9", "name": "caf\u00e9",
                                     "tasks": [task("j1", local=True)]}],
                                   name="Jira", source={"kind": "jira", "project": "J"})],
                            ensure_ascii=False, indent="\t") + "\n"
        latin = mirror.encode("latin-1")
        for written, odd, odd_target, argv in (
                (self.legacy, self.legacy_local, self.new_local, ("claim", "d")),
                (self.legacy_local, self.legacy, self.new, ("claim", "j1"))):
            with self.subTest(odd=odd.name):
                for f in (self.legacy, self.legacy_local, self.new, self.new_local):
                    f.unlink(missing_ok=True)
                if written == self.legacy:
                    self._write(self.legacy, self._phases())
                else:
                    self.legacy_local.write_text(mirror)
                odd.write_bytes(latin)
                rc, out, _err = self._run(*argv, str(written), "--date", "2026-11-18")
                self.assertEqual(rc, 0, out)
                self.assertEqual(odd_target.read_bytes(), latin)

    def test_a_crlf_committed_file_counts_as_not_canonical(self):
        # read_text() folds CRLF into LF, so the comparison must be on bytes
        canonical = json.dumps(self._phases(), indent="\t", ensure_ascii=False) + "\n"
        self.legacy.write_bytes(canonical.replace("\n", "\r\n").encode("utf-8"))
        self._write(self.legacy_local, [phase(
            [{"id": "M9", "name": "mirror", "tasks": [task("j1", local=True)]}],
            name="Jira", source={"kind": "jira", "project": "J"})])
        before = {f: f.read_bytes() for f in (self.legacy, self.legacy_local)}
        rc, out, _err = self._run("claim", "j1", str(self.root), "--date", "2026-11-18")
        self.assertEqual(rc, 2, out)
        self.assertIn(".claude/roadmaps.json is not in canonical form", out)
        self.assertEqual({f: f.read_bytes() for f in before}, before)

    def test_a_lone_surrogate_in_the_committed_file_refuses_without_a_traceback(self):
        # round 3: the shape JSON.stringify gives a string cut through an
        # emoji; canonical text holds a surrogate UTF-8 cannot encode
        data = self._phases()
        data[1]["milestones"][0]["tasks"][1]["description"] = "cut SURROGATE"
        text = json.dumps(data, indent="\t", ensure_ascii=False) + "\n"
        self.legacy.write_text(text.replace("SURROGATE", "\\ud83d"))
        self._write(self.legacy_local, [phase(
            [{"id": "M9", "name": "mirror", "tasks": [task("j1", local=True)]}],
            name="Jira", source={"kind": "jira", "project": "J"})])
        before = {f: f.read_bytes() for f in (self.legacy, self.legacy_local)}
        rc, out, _err = self._run("claim", "j1", str(self.root), "--date", "2026-11-18")
        self.assertEqual(rc, 2, out)
        self.assertIn(".claude/roadmaps.json is not in canonical form", out)
        self.assertEqual({f: f.read_bytes() for f in before}, before)

    def test_clearing_the_chart_path_on_an_unmoved_file_clears_it(self):
        data = self._phases()
        data[1]["artefact"] = "site/plan.html"
        self._write(self.legacy, data)
        rc, out, _err = self._run("config", "artefact", "--clear", str(self.legacy),
                                  "--phase", "Phase 2")
        self.assertEqual(rc, 0, out)
        moved = json.loads(self.new.read_text())
        self.assertNotIn("artefact", moved[1])  # cleared, as asked
        self.assertEqual(moved[0]["artefact"], "docs/artefacts/roadmap-phase-1.html")

    def test_detect_names_the_file_it_read(self):
        self._write(self.legacy, self._phases())
        _rc, out, _err = self._run("detect", str(self.root))
        self.assertIn("roadmaps.json", out)
        self.assertNotIn("roadbook.json", out)

    def test_a_new_file_beside_an_old_one_wins_and_the_old_one_is_left_alone(self):
        self._write(self.new, self._phases()[1:])
        self._write(self.legacy, self._phases())
        before = self.legacy.read_text()
        rc, out, err = self._run("claim", "d", str(self.root), "--date", "2026-11-18")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.legacy.read_text(), before)
        self.assertIn("roadmaps.json", err)
        self.assertEqual(json.loads(self.new.read_text())[0]["milestones"][0]["tasks"][1]["started"],
                         "2026-11-18")

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_a_moved_local_file_that_git_does_not_ignore_is_named(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / ".gitignore").write_text(".claude/roadmaps.local.json\n")
        self._write(self.legacy_local, [phase(
            [{"id": "M9", "name": "mirror", "tasks": [task("j1", local=True)]}],
            name="Jira", source={"kind": "jira", "project": "J"})])
        rc, out, err = self._run("claim", "j1", str(self.legacy_local), "--date", "2026-11-18")
        self.assertEqual(rc, 0, out)
        self.assertIn(".claude/roadbook.local.json is not ignored by git", err)


class RebindCommand(LegacyFixture):
    """`rebind`: the move from roadmaps.json by hand, and with --outputs the
    chart, the projections and the prose overview moved to the roadbook's
    default names too, on request only."""

    def _outputs(self):
        """The 2.x outputs of _phases() on disk where a 2.x plugin put them."""
        written = [
            "docs/artefacts/roadmap-phase-1.html", "docs/artefacts/roadmap-phase-2.html",
            "docs/roadmaps/TEST.md", "docs/reports/ROADMAP_OVERVIEW.md"]
        for rel in written:
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(rel)
        return written

    def test_rebind_moves_the_file_and_pins_like_a_first_write(self):
        self._write(self.legacy, self._phases())
        rc, out, err = self._run("rebind", str(self.root))
        self.assertEqual(rc, 0, out)
        self.assertFalse(self.legacy.exists())
        migrated = json.loads(self.new.read_text())
        self.assertEqual(migrated[1]["artefact"], "docs/artefacts/roadmap-phase-2.html")
        self.assertEqual(len(err.splitlines()), 1, err)

    def test_rebind_on_a_roadbook_has_nothing_to_do(self):
        self._write(self.new, self._phases())
        before = self.new.read_text()
        rc, out, _err = self._run("rebind", str(self.root))
        self.assertEqual(rc, 0, out)
        self.assertIn("nothing to rebind", out)
        self.assertEqual(self.new.read_text(), before)

    def test_outputs_move_to_the_new_default_names(self):
        self._write(self.legacy, self._phases())
        self._outputs()
        rc, out, _err = self._run("rebind", str(self.root), "--outputs")
        self.assertEqual(rc, 0, out)
        migrated = json.loads(self.new.read_text())
        self.assertTrue(all("artefact" not in p for p in migrated))
        self.assertTrue(all(p["path"] == "docs/roadbook/TEST.md" for p in migrated))
        for old, new in (("docs/artefacts/roadmap-phase-1.html", "docs/artefacts/chart-phase-1.html"),
                         ("docs/artefacts/roadmap-phase-2.html", "docs/artefacts/chart-phase-2.html"),
                         ("docs/roadmaps/TEST.md", "docs/roadbook/TEST.md"),
                         ("docs/reports/ROADMAP_OVERVIEW.md", "docs/reports/ROADBOOK_OVERVIEW.md")):
            self.assertFalse((self.root / old).exists(), old)
            self.assertEqual((self.root / new).read_text(), old)
        expected = self._phases()
        for ph in expected:
            ph["path"] = "docs/roadbook/TEST.md"
        self.assertEqual(self._without_migration_marks(migrated, set()), expected)

    def test_outputs_leave_a_path_the_project_chose_alone(self):
        data = self._phases()
        data[1]["artefact"] = "site/plan.html"
        data[1]["path"] = "planning/PHASE2.md"
        self._write(self.new, data)
        self._outputs()
        rc, out, _err = self._run("rebind", str(self.root), "--outputs")
        self.assertEqual(rc, 0, out)
        after = json.loads(self.new.read_text())
        self.assertEqual((after[1]["artefact"], after[1]["path"]), ("site/plan.html", "planning/PHASE2.md"))
        self.assertEqual(after[0]["path"], "docs/roadbook/TEST.md")

    def test_dry_run_lists_the_moves_and_changes_nothing(self):
        self._write(self.legacy, self._phases())
        written = self._outputs()
        before = self.legacy.read_text()
        rc, out, err = self._run("rebind", str(self.root), "--outputs", "--dry-run")
        self.assertEqual(rc, 0, out)
        self.assertEqual((self.legacy.read_text(), err), (before, ""))
        self.assertTrue(all((self.root / rel).exists() for rel in written))
        self.assertIn("docs/reports/ROADMAP_OVERVIEW.md -> docs/reports/ROADBOOK_OVERVIEW.md", out)
        self.assertIn(".claude/roadmaps.json -> .claude/roadbook.json", out)

    def test_a_target_already_there_refuses_before_anything_moves(self):
        self._write(self.legacy, self._phases())
        self._outputs()
        (self.root / "docs" / "roadbook").mkdir(parents=True)
        (self.root / "docs" / "roadbook" / "TEST.md").write_text("mine")
        before = self.legacy.read_text()
        rc, out, _err = self._run("rebind", str(self.root), "--outputs")
        self.assertEqual(rc, 1)
        self.assertIn("docs/roadbook/TEST.md already exists", out)
        self.assertEqual(self.legacy.read_text(), before)
        self.assertTrue((self.root / "docs" / "roadmaps" / "TEST.md").exists())

    def _mirror(self):
        """A 2.x local file: a Jira mirror with its own chart and projection."""
        return [phase([{"id": "M9", "name": "mirror", "tasks": [task("j1", local=True)]}],
                      name="Jira", path="docs/roadmaps/JIRA.md",
                      source={"kind": "jira", "project": "J"})]

    def test_a_local_file_beside_the_old_one_is_planned_and_moved_with_it(self):
        self._write(self.legacy, self._phases())
        self._write(self.legacy_local, self._mirror())
        self._outputs()
        for rel in ("docs/artefacts/roadmap-jira.html", "docs/roadmaps/JIRA.md"):
            (self.root / rel).write_text(rel)
        rc, out, _err = self._run("rebind", str(self.root), "--outputs", "--dry-run")
        self.assertEqual(rc, 0, out)
        for line in (".claude/roadmaps.json -> .claude/roadbook.json",
                     ".claude/roadmaps.local.json -> .claude/roadbook.local.json",
                     "docs/artefacts/roadmap-phase-2.html -> docs/artefacts/chart-phase-2.html",
                     "docs/artefacts/roadmap-jira.html -> docs/artefacts/chart-jira.html",
                     "docs/roadmaps/TEST.md -> docs/roadbook/TEST.md",
                     "docs/roadmaps/JIRA.md -> docs/roadbook/JIRA.md"):
            self.assertIn(line, out)
        rc, out, _err = self._run("rebind", str(self.root), "--outputs")
        self.assertEqual(rc, 0, out)
        committed = json.loads(self.new.read_text())
        local = json.loads(self.new_local.read_text())
        self.assertTrue(all("artefact" not in p for p in committed + local))
        self.assertEqual([p["path"] for p in committed], ["docs/roadbook/TEST.md"] * 2)
        self.assertEqual(local[0]["path"], "docs/roadbook/JIRA.md")
        for rel in ("docs/artefacts/chart-phase-2.html", "docs/artefacts/chart-jira.html",
                    "docs/roadbook/TEST.md", "docs/roadbook/JIRA.md"):
            self.assertTrue((self.root / rel).exists(), rel)
        self.assertFalse(self.legacy.exists() or self.legacy_local.exists())

    def _moved_with_a_left_chart(self):
        """Both 2.x files moved by a first write on the committed one, so the
        local file arrived byte for byte with no chart pin, and the mirror's
        2.x chart still on disk at its old default name."""
        self._write(self.legacy, self._phases())
        self._write(self.legacy_local, self._mirror())
        old_chart = self.root / "docs/artefacts/roadmap-jira.html"
        old_chart.parent.mkdir(parents=True, exist_ok=True)
        old_chart.write_text("2.x chart")
        rc, out, _err = self._run("claim", "d", str(self.legacy), "--date", "2026-11-18")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("artefact", json.loads(self.new_local.read_text())[0])
        return old_chart

    def test_outputs_find_a_local_phase_chart_left_at_the_2x_default(self):
        old_chart = self._moved_with_a_left_chart()
        rc, out, _err = self._run("rebind", str(self.root), "--outputs", "--dry-run")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("nothing to rebind", out)
        self.assertIn("docs/artefacts/roadmap-jira.html -> docs/artefacts/chart-jira.html", out)
        rc, out, _err = self._run("rebind", str(self.root), "--outputs")
        self.assertEqual(rc, 0, out)
        self.assertFalse(old_chart.exists())
        self.assertEqual((self.root / "docs/artefacts/chart-jira.html").read_text(), "2.x chart")
        self.assertNotIn("artefact", json.loads(self.new_local.read_text())[0])

    def test_a_left_chart_beside_a_new_one_is_named_stale_and_left(self):
        old_chart = self._moved_with_a_left_chart()
        new_chart = self.root / "docs/artefacts/chart-jira.html"
        new_chart.write_text("3.0 chart")
        for argv in (("rebind", str(self.root), "--outputs", "--dry-run"),
                     ("rebind", str(self.root), "--outputs")):
            with self.subTest(argv=argv):
                rc, out, _err = self._run(*argv)
                self.assertEqual(rc, 0, out)
                self.assertNotIn("already exists", out)
                self.assertIn("stale", out)
                self.assertIn("docs/artefacts/roadmap-jira.html", out)
                self.assertEqual((old_chart.read_text(), new_chart.read_text()),
                                 ("2.x chart", "3.0 chart"))

    def test_a_chart_another_phase_names_is_never_taken_for_a_2x_default(self):
        # round 2's repro: Alpha renders to the file that would be Beta's 2.x
        # default; Beta has no artefact. That file is Alpha's, not stale.
        data = [phase([{"id": "M1", "name": "a", "tasks": [task("a1")]}], name="Alpha",
                      artefact="docs/artefacts/roadmap-beta.html"),
                phase([{"id": "M2", "name": "b", "tasks": [task("b1")]}], name="Beta")]
        self._write(self.new, data)
        alpha_chart = self.root / "docs/artefacts/roadmap-beta.html"
        alpha_chart.parent.mkdir(parents=True)
        alpha_chart.write_text("Alpha's chart")
        rc, out, _err = self._run("rebind", str(self.root), "--outputs", "--dry-run")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("roadmap-beta.html", out)
        (self.root / "docs/artefacts/chart-beta.html").write_text("Beta's chart")
        for argv in (("rebind", str(self.root), "--outputs", "--dry-run"),
                     ("rebind", str(self.root), "--outputs")):
            with self.subTest(argv=argv):
                rc, out, _err = self._run(*argv)
                self.assertEqual(rc, 0, out)
                self.assertNotIn("roadmap-beta.html", out)
                self.assertEqual(alpha_chart.read_text(), "Alpha's chart")

    def test_an_unmoved_file_never_takes_another_phase_chart_either(self):
        # the same file under the 2.x name, where a phase with no artefact
        # falls back to the 2.x default without looking at the disk
        data = [phase([{"id": "M1", "name": "a", "tasks": [task("a1")]}], name="Alpha",
                      artefact="docs/artefacts/roadmap-beta.html"),
                phase([{"id": "M2", "name": "b", "tasks": [task("b1")]}], name="Beta")]
        self._write(self.legacy, data)
        alpha_chart = self.root / "docs/artefacts/roadmap-beta.html"
        alpha_chart.parent.mkdir(parents=True)
        alpha_chart.write_text("Alpha's chart")
        rc, out, _err = self._run("rebind", str(self.root), "--outputs")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("roadmap-beta.html", out)
        self.assertEqual(alpha_chart.read_text(), "Alpha's chart")
        self.assertEqual(json.loads(self.new.read_text())[0]["artefact"],
                         "docs/artefacts/roadmap-beta.html")

    def test_a_newer_stamp_on_either_file_refuses_before_anything_is_written(self):
        data = self._phases()
        self._write(self.new, data)
        newer = self._mirror()
        newer[0]["min_plugin"] = "9.0.0"
        self._write(self.legacy_local, newer)
        self._outputs()
        before = (self.new.read_text(), self.legacy_local.read_text())
        for argv in (("rebind", str(self.root), "--outputs", "--dry-run"),
                     ("rebind", str(self.root), "--outputs")):
            with self.subTest(argv=argv):
                rc, out, _err = self._run(*argv)
                self.assertEqual(rc, 2, out)
                self.assertIn("9.0.0", out)
                self.assertEqual((self.new.read_text(), self.legacy_local.read_text()), before)
                self.assertTrue((self.root / "docs" / "roadmaps" / "TEST.md").exists())

    def test_a_non_canonical_file_needs_reformat_before_rebind_rewrites_it(self):
        self.legacy.write_text(json.dumps(self._phases(), indent=2) + "\n")
        before = self.legacy.read_text()
        rc, out, _err = self._run("rebind", str(self.root))
        self.assertEqual(rc, 1, out)
        self.assertIn("roadmaps.json is not in canonical form", out)
        self.assertEqual(self.legacy.read_text(), before)
        rc, out, _err = self._run("rebind", str(self.root), "--reformat")
        self.assertEqual(rc, 0, out)
        self.assertTrue(self.new.exists())

    def test_a_crlf_file_needs_reformat_before_rebind_rewrites_it(self):
        canonical = json.dumps(self._phases(), indent="\t", ensure_ascii=False) + "\n"
        self.legacy.write_bytes(canonical.replace("\n", "\r\n").encode("utf-8"))
        before = self.legacy.read_bytes()
        rc, out, _err = self._run("rebind", str(self.root))
        self.assertEqual(rc, 1, out)
        self.assertIn("roadmaps.json is not in canonical form", out)
        self.assertEqual(self.legacy.read_bytes(), before)
        rc, out, _err = self._run("rebind", str(self.root), "--reformat")
        self.assertEqual(rc, 0, out)
        self.assertNotIn(b"\r", self.new.read_bytes())

    def test_a_named_old_file_beside_a_roadbook_refuses_in_the_dry_run_too(self):
        # round 3: the dry run said "would move" where the real run refused
        self._write(self.new, self._phases()[1:])
        self._write(self.legacy, self._phases())
        before = (self.new.read_text(), self.legacy.read_text())
        for argv in (("rebind", str(self.legacy), "--dry-run"), ("rebind", str(self.legacy))):
            with self.subTest(argv=argv):
                rc, out, _err = self._run(*argv)
                self.assertEqual(rc, 2, out)
                self.assertIn(".claude/roadbook.json already exists beside .claude/roadmaps.json", out)
                self.assertEqual((self.new.read_text(), self.legacy.read_text()), before)

    def test_a_pointer_registry_is_named_as_the_file_it_is(self):
        self.legacy.write_text(json.dumps({"roadmaps": [{"path": "docs/roadmaps/mvp.md"}]}) + "\n")
        rc, out, _err = self._run("rebind", str(self.root))
        self.assertEqual(rc, 2)
        self.assertIn("roadmaps.json is an old-format pointer registry", out)
        self.assertNotIn("run goblin-scout:rebind-roadbook first", out)

    def test_rebind_without_outputs_moves_and_pins_both_files(self):
        self._write(self.legacy, self._phases())
        self._write(self.legacy_local, self._mirror())
        rc, out, _err = self._run("rebind", str(self.root), "--dry-run")
        self.assertIn(".claude/roadmaps.json -> .claude/roadbook.json", out)
        self.assertIn(".claude/roadmaps.local.json -> .claude/roadbook.local.json", out)
        rc, out, _err = self._run("rebind", str(self.root))
        self.assertEqual(rc, 0, out)
        self.assertEqual(json.loads(self.new_local.read_text())[0]["artefact"],
                         "docs/artefacts/roadmap-jira.html")
        self.assertEqual(json.loads(self.new.read_text())[1]["artefact"],
                         "docs/artefacts/roadmap-phase-2.html")

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_tracked_outputs_are_moved_with_git(self):
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        git = lambda *a: subprocess.run(["git", "-C", str(self.root), *a], check=True,
                                        capture_output=True, text=True, env=env).stdout
        git("init", "-q")
        self._write(self.legacy, self._phases())
        self._outputs()
        git("add", ".")
        git("commit", "-qm", "a 2.x project")
        rc, out, _err = self._run("rebind", str(self.root), "--outputs")
        self.assertEqual(rc, 0, out)
        staged = git("diff", "--cached", "--name-status", "-M")
        self.assertIn("docs/roadmaps/TEST.md\tdocs/roadbook/TEST.md", staged)
        self.assertIn("docs/reports/ROADMAP_OVERVIEW.md\tdocs/reports/ROADBOOK_OVERVIEW.md", staged)


@unittest.skipUnless(shutil.which("git"), "git not installed")
class LegacyHistory(GitRoadbook):
    """History read across the move: a base or an older commit that still
    holds .claude/roadmaps.json is read under that name."""

    def setUp(self):
        super().setUp()
        self.legacy = self.root / ".claude" / "roadmaps.json"

    def _commit_legacy(self, tasks, when):
        self._write(tasks)
        self.jp.rename(self.legacy)
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "roadmap", when=when)

    def _move(self, tasks, when):
        self._git("mv", ".claude/roadmaps.json", ".claude/roadbook.json")
        self._commit(tasks, when, "move to the roadbook")

    def test_stamp_ended_reads_the_old_file_at_the_merge_base(self):
        self._commit_legacy([task("a"), task("b", "done")], "2026-09-01")
        self._git("branch", "base")
        self._git("checkout", "-q", "-b", "feat/x")
        self._move([task("a", "done"), task("b", "done")], "2026-09-05")
        rc, out = self._run("stamp-ended", str(self.jp), "--base", "base",
                            "--date", "2026-10-02")
        self.assertEqual(rc, 0, out)
        self.assertIn("ended 1 waypoint(s) on 2026-10-02: a", out)

    def test_backfill_ended_dates_from_commits_before_the_move(self):
        self._commit_legacy([task("a"), task("b")], "2026-09-01")
        self._commit_legacy([task("a", "done"), task("b")], "2026-09-10")
        self._move([task("a", "done"), task("b", "done")], "2026-09-20")
        rc, out = self._run("backfill-ended", str(self.jp), "--json")
        self.assertEqual(rc, 0, out)
        rows = {r["id"]: r for r in json.loads(out)["tasks"]}
        self.assertEqual(rows["a"]["ended"], "2026-09-10")
        self.assertEqual(rows["b"]["ended"], "2026-09-20")


class VersionStamp(unittest.TestCase):
    """`min_plugin` on a phase and `pluginVersion` in a dashboard: a plugin
    older than either refuses to write over what a newer one produced."""

    RUNNING = "2.7.0"

    def setUp(self):
        self.addCleanup(setattr, roadbook, "PLUGIN_VERSION", roadbook.PLUGIN_VERSION)
        roadbook.PLUGIN_VERSION = self.RUNNING

    def _project(self, stored="blocked", started=None, **extra):
        """`stored` is b's status on disk; "blocked" makes recompute write.
        `started` claims b, which `release` needs before it will write."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name).resolve()
        (root / ".claude").mkdir()
        jp = root / ".claude" / "roadbook.json"
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "done"), task("b", stored, ["a"],
                                                  **({"started": started} if started else {}))]}],
                       **extra)]
        jp.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n")
        return root, jp

    def _run(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = roadbook.main(list(argv))
        return rc, out.getvalue()

    def test_a_write_stamps_the_live_phase_with_the_running_version(self):
        _root, jp = self._project()
        self.assertEqual(self._run("recompute", str(jp))[0], 0)
        self.assertEqual(json.loads(jp.read_text())[0]["min_plugin"], self.RUNNING)

    def test_the_stamp_sits_before_the_milestones(self):
        _root, jp = self._project()
        self._run("recompute", str(jp))
        keys = list(json.loads(jp.read_text())[0])
        self.assertLess(keys.index("min_plugin"), keys.index("externalGates"))

    def test_an_older_plugin_refuses_to_write_and_leaves_the_file_alone(self):
        _root, jp = self._project(min_plugin="2.8.0")
        before = jp.read_text()
        rc, out = self._run("recompute", str(jp))
        self.assertEqual(rc, 2)
        self.assertIn("2.8.0", out)
        self.assertEqual(jp.read_text(), before)

    def test_every_write_command_honours_the_stamp(self):
        # Each command is given a project where nothing else would refuse it,
        # so exit 2 can only be the stamp (other refusals exit 1).
        for argv, started in ((["claim", "b"], None),
                              (["release", "b"], "2026-10-01"),
                              (["end", "a"], None)):
            with self.subTest(argv=argv):
                _root, jp = self._project(started=started, min_plugin="2.8.0")
                before = jp.read_text()
                rc, _out = self._run(argv[0], argv[1], str(jp))
                self.assertEqual(rc, 2)
                self.assertEqual(jp.read_text(), before)

    def test_render_refuses_a_file_stamped_by_a_newer_plugin(self):
        root, jp = self._project(min_plugin="2.8.0")
        rc, _out = self._run("render", str(jp))
        self.assertEqual(rc, 2)
        self.assertFalse((root / "docs" / "artefacts").exists())

    def test_render_refuses_to_overwrite_a_newer_dashboard(self):
        root, jp = self._project()
        out = root / "dash.html"
        out.write_text('{"pluginVersion": "2.8.0"}')
        rc, _msg = self._run("render", str(jp), "--out", str(out))
        self.assertEqual(rc, 2)
        self.assertEqual(out.read_text(), '{"pluginVersion": "2.8.0"}')

    def test_render_overwrites_an_older_or_unstamped_dashboard(self):
        root, jp = self._project()
        for existing in ('{"pluginVersion": "2.6.0"}', "<html>pre-2.7</html>"):
            with self.subTest(existing=existing):
                out = root / "dash.html"
                out.write_text(existing)
                self.assertEqual(self._run("render", str(jp), "--out", str(out))[0], 0)
                self.assertIn('"pluginVersion": "2.7.0"', out.read_text())

    def test_reads_still_work_on_a_newer_file(self):
        _root, jp = self._project(stored="todo", min_plugin="2.8.0")
        self.assertEqual(self._run("validate", str(jp))[0], 0)
        self.assertEqual(self._run("recompute", "--check", str(jp))[0], 0)

    def test_a_patch_release_leaves_the_stamp_alone(self):
        _root, jp = self._project(min_plugin="2.7.0")
        roadbook.PLUGIN_VERSION = "2.7.3"
        self.assertEqual(self._run("recompute", str(jp))[0], 0)
        self.assertEqual(json.loads(jp.read_text())[0]["min_plugin"], "2.7.0")

    def test_a_newer_minor_raises_the_stamp(self):
        _root, jp = self._project(min_plugin="2.7.0")
        roadbook.PLUGIN_VERSION = "2.9.1"
        self.assertEqual(self._run("recompute", str(jp))[0], 0)
        self.assertEqual(json.loads(jp.read_text())[0]["min_plugin"], "2.9.0")

    def test_an_unreadable_stamp_never_blocks_and_is_repaired(self):
        for stamp in ("banana", "2.7", ""):
            with self.subTest(stamp=stamp):
                _root, jp = self._project(min_plugin=stamp)
                self.assertEqual(self._run("recompute", str(jp))[0], 0)
                self.assertEqual(json.loads(jp.read_text())[0]["min_plugin"], self.RUNNING)


class CrossTierEdges(unittest.TestCase):
    """validate flags a dependsOn entry naming a lower-tier task the task
    already requires through another entry (a milestone, or a task that
    reaches it): the tier pattern reaches a lower tier by milestone."""

    @staticmethod
    def _tiered(tertiary_deps, **extra):
        return phase([
            {"id": "M1", "name": "Core", "tasks": [task("1A.1", "done")]},
            {"id": "M10", "name": "Search (Secondary)", "tasks": [
                task("10SE.3", "todo", ["M1"]),
                task("10SE.4", "todo", ["M1"]),
                task("10SE.5", "blocked", ["10SE.3"])]},
            {"id": "M13", "name": "Search (Tertiary)", "tasks": [
                task("13SE.1", "blocked", ["M10"]),
                task("13SE.5", "blocked", tertiary_deps, **extra)]}])

    @staticmethod
    def _flagged(ph):
        return [p for p in roadbook._validate_phase(ph) if "sits in" in p]

    def test_lower_tier_task_next_to_its_milestone_is_flagged(self):
        found = roadbook.redundant_cross_tier_edges(
            self._tiered(["M10", "10SE.4"]))
        self.assertEqual(found, [("13SE.5", "10SE.4", "M10", 1, "M10")])
        problems = self._flagged(self._tiered(["M10", "10SE.4"]))
        self.assertEqual(len(problems), 1)
        self.assertIn("13SE.5: dependsOn '10SE.4' sits in M10 (Secondary), "
                      "already required through M10", problems[0])
        self.assertIn("name 10SE.4 in notes", problems[0])

    def test_reached_through_a_lower_tier_task_names_that_task(self):
        found = roadbook.redundant_cross_tier_edges(
            self._tiered(["10SE.5", "10SE.3"]))
        self.assertEqual(found, [("13SE.5", "10SE.3", "M10", 1, "10SE.5")])

    def test_uncovered_lower_tier_task_edge_stays_authored(self):
        self.assertEqual(
            roadbook.redundant_cross_tier_edges(self._tiered(["10SE.4"])), [])

    def test_milestone_entries_are_never_flagged(self):
        # ["M1", "M10", "13SE.1"] reaches M10 twice, but that is the tier
        # pattern itself, as 8RT.10 ["M1", "M6", "8RT.9"] is in CHIRPdb.
        ph = self._tiered(["M1", "M10", "13SE.1"])
        self.assertEqual(roadbook.redundant_cross_tier_edges(ph), [])
        self.assertEqual(self._flagged(ph), [])

    def test_same_tier_task_edges_are_never_flagged(self):
        ph = phase([
            {"id": "M10", "name": "Search (Secondary)", "tasks": [
                task("10SE.3", "todo"),
                task("10SE.5", "blocked", ["10SE.3"]),
                task("10SE.6", "blocked", ["10SE.5", "10SE.3"])]}])
        self.assertEqual(roadbook.redundant_cross_tier_edges(ph), [])

    def test_untiered_phase_is_never_checked(self):
        ph = phase([
            {"id": "M1", "name": "Core", "tasks": [task("a", "done")]},
            {"id": "M2", "name": "More", "tasks": [
                task("b", "todo", ["M1", "a"])]}])
        self.assertEqual(roadbook.redundant_cross_tier_edges(ph), [])

    def test_soft_member_is_not_reached_through_its_milestone(self):
        ph = phase([
            {"id": "M1", "name": "Core", "tasks": [
                task("a", "done"), task("s", "todo", softMilestone=True)]},
            {"id": "M2", "name": "More (Secondary)", "tasks": [
                task("b", "todo", ["M1", "s"])]}])
        self.assertEqual(roadbook.redundant_cross_tier_edges(ph), [])

    def test_soft_member_reached_through_a_hard_member(self):
        # M1 cannot finish before hard h, and h waits on soft s, so the
        # milestone does cover s after all and the task edge is redundant.
        ph = phase([
            {"id": "M1", "name": "Core", "tasks": [
                task("h", "todo", ["s"]), task("s", "todo", softMilestone=True)]},
            {"id": "M2", "name": "More (Secondary)", "tasks": [
                task("b", "todo", ["M1", "s"])]}])
        self.assertEqual(roadbook.redundant_cross_tier_edges(ph),
                         [("b", "s", "M1", 0, "M1")])

    def test_soft_member_reached_transitively(self):
        # The walk follows dependsOn through any task: hard h waits on
        # soft t, t waits on soft s, so M1 covers s two hops away.
        ph = phase([
            {"id": "M1", "name": "Core", "tasks": [
                task("h", "todo", ["t"]),
                task("t", "todo", ["s"], softMilestone=True),
                task("s", "todo", softMilestone=True)]},
            {"id": "M2", "name": "More (Secondary)", "tasks": [
                task("b", "todo", ["M1", "s"])]}])
        self.assertEqual(roadbook.redundant_cross_tier_edges(ph),
                         [("b", "s", "M1", 0, "M1")])

    def test_soft_member_reached_through_another_gate_milestone(self):
        # Hard 7.1 in M7 waits on soft s in M10, so M7 covers s even
        # though M10 (s's own milestone) is not in the gate at all.
        ph = phase([
            {"id": "M7", "name": "A", "tasks": [task("7.1", "todo", ["s"])]},
            {"id": "M10", "name": "C", "tasks": [
                task("10.1", "todo"), task("s", "todo", softMilestone=True)]},
            {"id": "M13", "name": "D (Secondary)", "tasks": [
                task("b", "todo", ["M7", "s"])]}])
        self.assertEqual(roadbook.redundant_cross_tier_edges(ph),
                         [("b", "s", "M10", 0, "M7")])

    def test_validate_cli_reports_the_edge(self):
        with tempfile.TemporaryDirectory() as td:
            jp = Path(td) / ".claude" / "roadbook.json"
            jp.parent.mkdir()
            jp.write_text(json.dumps([self._tiered(["M10", "10SE.4"])]))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = roadbook.main(["validate", str(jp)])
            self.assertEqual(rc, 1)
            self.assertIn("13SE.5: dependsOn '10SE.4' sits in M10", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
