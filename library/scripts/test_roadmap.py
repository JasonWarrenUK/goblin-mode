#!/usr/bin/env python3
"""Fixture tests for the roadmap system (_roadmap_core.py + roadmap.py).

Run from this directory: python3 -m unittest test_roadmap -v
Stdlib only. Each test builds a minimal phase dict; file-based behaviour
(detect, recompute writes) uses a TemporaryDirectory shaped like a project
root with .claude/roadmaps.json.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import roadmap
from _roadmap_core import (
    RoadmapError,
    active_phase,
    build_index,
    find_cycles,
    milestone_sinks,
    recompute_all,
)


def task(tid, status="todo", depends=None, **extra):
    t = {"id": tid, "description": f"task {tid}", "status": status,
         "dependsOn": depends or []}
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


class Sinks(unittest.TestCase):
    def test_sinks_ignore_cross_milestone_dependents(self):
        ph = phase([
            {"id": "M1", "name": "m1", "tasks": [
                task("a"), task("b", "blocked", ["a"])]},
            {"id": "M2", "name": "m2", "tasks": [task("c", "blocked", ["b"])]}])
        sinks = milestone_sinks(ph)
        self.assertEqual(sinks["M1"], ["b"])   # a feeds b in-milestone
        self.assertEqual(sinks["M2"], ["c"])


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

    def test_nodes_declared_in_topological_order(self):
        src = roadmap.mermaid_source(self.ph)
        lines = src.splitlines()

        def decl(nid):
            return next(i for i, l in enumerate(lines)
                        if l.strip().startswith(f'{nid}["'))
        self.assertLess(decl("a"), decl("b"))   # a --> b
        self.assertLess(decl("b"), decl("M1"))  # sink into milestone
        self.assertLess(decl("M1"), decl("c"))  # milestone as dependency


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

    def test_render_includes_assignee_when_set(self):
        data = [phase([{"id": "M1", "name": "m", "tasks": [
            task("a", "todo", assignee="jason")]}], name="My Phase")]
        root, jp = self._project(data)
        rc = roadmap.main(["render", str(jp)])
        self.assertEqual(rc, 0)
        out = root / "docs" / "artefacts" / "roadmap-my-phase.html"
        html = out.read_text()
        self.assertIn("jason", html)  # assignee reaches the embedded data blob


if __name__ == "__main__":
    unittest.main()
