#!/usr/bin/env python3
"""Tests for phases mirrored from Jira (_roadmap_jira.py, `roadmap.py pull`
and the gating a `source` switches on).

Run from this directory: python3 -m unittest test_roadmap_jira -v
Stdlib only; no test touches the network. The old suite in test_roadmap.py
covers every phase without a source and must keep passing unchanged.
"""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import _roadmap_hooks
import _roadmap_jira as jira
import roadmap
from _roadmap_core import build_index, resolve_roadmap_path

ORDER = roadmap.TASK_FIELD_ORDER
VERSIONS = {
    "R1": {"id": "100", "name": "Release 1", "startDate": "2026-11-16",
           "releaseDate": "2026-12-18"},
    "R2": {"id": "200", "name": "Release 2", "startDate": "2027-01-04",
           "releaseDate": "2027-01-29"},
}


def raw(key, summary="", kind="Story", level=0, category="new", status=None,
        parent=None, version=None, blocked_by=(), assignee=None,
        changed="2026-11-17T09:00:00.000+0000", resolved=None):
    """One issue in the shape Jira's search returns."""
    names = {"new": "To Do", "indeterminate": "In Progress", "done": "Done"}
    return {"key": key, "fields": {
        "summary": summary or f"summary of {key}",
        "issuetype": {"name": kind, "hierarchyLevel": level},
        "status": {"name": status or names[category],
                   "statusCategory": {"key": category}},
        "parent": {"key": parent} if parent else None,
        "fixVersions": [VERSIONS[version]] if version else [],
        "issuelinks": [{"type": {"name": "Blocks"}, "inwardIssue": {"key": b}}
                       for b in blocked_by],
        "assignee": {"displayName": assignee} if assignee else None,
        "statuscategorychangedate": changed,
        "resolutiondate": resolved,
    }}


def board():
    return [
        raw("T-1", "Ask a question", kind="Epic", level=1),
        raw("T-2", "Stream the answer", parent="T-1", version="R1"),
        raw("T-3", "Count with filters", parent="T-1", version="R1",
            blocked_by=["T-2"]),
        raw("T-4", "Search report text", parent="T-1", version="R2",
            blocked_by=["T-3"]),
    ]


def empty_phase():
    return {"name": "Tranche 2", "source": {"kind": "jira", "project": "T"},
            "externalGates": [], "milestones": []}


def pull(phase, issues):
    return jira.merge(phase, [jira.normalise(i) for i in issues], ORDER)


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = roadmap.main(list(argv))
    return code, out.getvalue()


class Mapping(unittest.TestCase):
    def setUp(self):
        self.phase = empty_phase()
        self.report = pull(self.phase, board())
        self.tasks = build_index(self.phase)[0]

    def test_versions_become_milestones_in_release_order(self):
        self.assertEqual(
            [(m["id"], m["name"], [t["id"] for t in m["tasks"]])
             for m in self.phase["milestones"]],
            [("M1", "Release 1", ["T-2", "T-3"]), ("M2", "Release 2", ["T-4"])])

    def test_an_epic_is_a_topic_and_never_a_task(self):
        self.assertNotIn("T-1", self.tasks)
        self.assertEqual({t["topic"] for t in self.tasks.values()},
                         {"Ask a question"})

    def test_blocks_links_become_edges_and_statuses_follow(self):
        self.assertEqual(self.tasks["T-3"]["dependsOn"], ["T-2"])
        self.assertEqual(
            {tid: t["status"] for tid, t in self.tasks.items()},
            {"T-2": "todo", "T-3": "blocked", "T-4": "blocked"})

    def test_the_result_validates(self):
        self.assertEqual(roadmap._validate_phase(self.phase), [])

    def test_first_pull_reports_everything_as_added(self):
        self.assertEqual(len(self.report["added"]), 3)
        self.assertEqual(self.report["drift"], [])

    def test_a_second_pull_changes_nothing(self):
        before = json.dumps(self.phase)
        report = pull(self.phase, board())
        self.assertEqual(json.dumps(self.phase), before)
        self.assertFalse(report["added"] or report["changed"] or report["removed"])

    def test_no_fix_version_lands_in_unscheduled(self):
        phase = empty_phase()
        pull(phase, board() + [raw("T-9", parent="T-1")])
        self.assertEqual(
            [(m["id"], m["name"]) for m in phase["milestones"]][-1],
            ("M0", "Unscheduled"))

    def test_a_child_ticket_holds_its_story_and_shares_its_release(self):
        phase = empty_phase()
        pull(phase, board() + [raw("T-7", kind="Subtask", parent="T-2")])
        tasks = build_index(phase)[0]
        self.assertEqual(tasks["T-2"]["dependsOn"], ["T-7"])
        self.assertEqual(tasks["T-2"]["status"], "blocked")
        self.assertEqual(tasks["T-7"]["topic"], "Ask a question")
        self.assertIn("T-7", [t["id"] for t in phase["milestones"][0]["tasks"]])


    def test_a_split_of_a_blocked_story_is_not_ready(self):
        phase = empty_phase()
        pull(phase, board() + [raw("T-8", kind="Subtask", parent="T-3")])
        tasks = build_index(phase)[0]
        self.assertEqual(tasks["T-8"]["dependsOn"], ["T-2"])
        self.assertEqual(tasks["T-8"]["status"], "blocked")
        self.assertEqual(roadmap._validate_phase(phase), [])

    def test_a_gate_added_by_hand_survives_and_holds_its_tasks(self):
        phase = empty_phase()
        pull(phase, board())
        phase["externalGates"] = [{
            "id": "G1", "name": "Six countries chosen", "status": "pending",
            "blocks": ["T-2"]}]
        build_index(phase)[0]["T-2"]["dependsOn"].append("G1")
        pull(phase, board())
        task = build_index(phase)[0]["T-2"]
        self.assertEqual(task["dependsOn"], ["G1"])
        self.assertEqual(task["status"], "blocked")
        self.assertEqual(roadmap._validate_phase(phase), [])


class Statuses(unittest.TestCase):
    def test_in_progress_sets_started_and_done_sets_ended(self):
        phase = empty_phase()
        issues = board()
        issues[1] = raw("T-2", parent="T-1", version="R1", category="done",
                        assignee="Max", resolved="2026-11-18T10:00:00.000+0000")
        issues[2] = raw("T-3", parent="T-1", version="R1", blocked_by=["T-2"],
                        category="indeterminate", status="In Review",
                        changed="2026-11-19T08:00:00.000+0000")
        pull(phase, issues)
        tasks = build_index(phase)[0]
        self.assertEqual(tasks["T-2"]["status"], "done")
        self.assertEqual(tasks["T-2"]["ended"], "2026-11-18")
        self.assertEqual(tasks["T-2"]["assignee"], "Max")
        self.assertEqual(tasks["T-3"]["status"], "todo")
        self.assertEqual(tasks["T-3"]["started"], "2026-11-19")
        self.assertEqual(tasks["T-3"]["tracker"]["status"], "In Review")
        self.assertEqual(roadmap._validate_phase(phase), [])

    def test_a_reopened_issue_loses_its_dates(self):
        phase = empty_phase()
        issues = board()
        issues[1] = raw("T-2", "Stream the answer", parent="T-1",
                        version="R1", category="done",
                        resolved="2026-11-18T10:00:00.000+0000")
        pull(phase, issues)
        report = pull(phase, board())
        task = build_index(phase)[0]["T-2"]
        self.assertNotIn("ended", task)
        self.assertNotIn("started", task)
        self.assertIn("T-2: Done -> To Do", report["changed"])

    def test_in_progress_behind_an_open_blocker_is_reported(self):
        phase = empty_phase()
        issues = board()
        issues[2] = raw("T-3", parent="T-1", version="R1", blocked_by=["T-2"],
                        category="indeterminate")
        report = pull(phase, issues)
        self.assertEqual(
            report["drift"],
            ["T-3 is In Progress in Jira while T-2 still blocks it"])

    def test_a_cycle_writes_nothing(self):
        phase = empty_phase()
        issues = board()
        issues[1] = raw("T-2", parent="T-1", version="R1", blocked_by=["T-3"])
        with self.assertRaises(roadmap.RoadmapError):
            pull(phase, issues)
        self.assertEqual(phase["milestones"], [])


class LocalWork(unittest.TestCase):
    def setUp(self):
        self.phase = empty_phase()
        pull(self.phase, board())
        first = self.phase["milestones"][0]
        first["tasks"][0]["notes"] = "branch feat/stream-answers"
        first["tasks"][0]["pr"] = 212
        first["tasks"].append({
            "id": "L1", "description": "Spike the streaming transport",
            "status": "todo", "dependsOn": [], "local": True})
        first["tasks"][1]["dependsOn"].append("L1")
        self.phase["milestones"][1]["tasks"].append({
            "id": "L2", "description": "Tidy the search fixtures",
            "status": "blocked", "dependsOn": ["T-4"], "local": True})

    def test_notes_and_pr_survive_a_pull(self):
        pull(self.phase, board())
        task = build_index(self.phase)[0]["T-2"]
        self.assertEqual((task["notes"], task["pr"]),
                         ("branch feat/stream-answers", 212))

    def test_local_tasks_and_edges_to_them_survive(self):
        report = pull(self.phase, board())
        tasks = build_index(self.phase)[0]
        self.assertEqual(tasks["L1"]["description"], "Spike the streaming transport")
        self.assertEqual(tasks["T-3"]["dependsOn"], ["T-2", "L1"])
        self.assertEqual(report["local"], 2)
        self.assertEqual(roadmap._validate_phase(self.phase), [])

    def test_a_vanished_issue_orphans_the_edge_and_keeps_the_task(self):
        report = pull(self.phase, board()[:3])
        tasks = build_index(self.phase)[0]
        self.assertEqual(tasks["L2"]["dependsOn"], [])
        self.assertEqual(tasks["L2"]["orphaned"], ["T-4"])
        self.assertEqual(tasks["L2"]["status"], "todo")
        self.assertTrue(any(line.startswith("T-4") for line in report["removed"]))
        self.assertTrue(any("L2" in line for line in report["orphans"]))
        self.assertEqual(roadmap._validate_phase(self.phase), [])

    def test_the_edge_returns_with_the_issue(self):
        pull(self.phase, board()[:3])
        pull(self.phase, board())
        task = build_index(self.phase)[0]["L2"]
        self.assertEqual(task["dependsOn"], ["T-4"])
        self.assertNotIn("orphaned", task)

    def test_a_vanished_issue_with_notes_is_parked_not_dropped(self):
        report = pull(self.phase, board()[:1] + board()[2:])
        tasks = build_index(self.phase)[0]
        parked = tasks["T-2"]
        self.assertEqual((parked["status"], parked["notes"], parked["pr"]),
                         ("out_of_scope", "branch feat/stream-answers", 212))
        self.assertTrue(parked["local"])
        self.assertEqual(self.phase["milestones"][-1]["id"], "GONE")
        self.assertEqual(tasks["T-3"]["dependsOn"], ["L1"])
        self.assertTrue(any("parked" in line for line in report["removed"]))
        self.assertEqual(roadmap._validate_phase(self.phase), [])
        again = pull(self.phase, board()[:1] + board()[2:])
        self.assertEqual(again["removed"], [])
        self.assertIn("T-2", build_index(self.phase)[0])

    def test_a_parked_issue_that_returns_takes_its_notes_back(self):
        pull(self.phase, board()[:1] + board()[2:])
        pull(self.phase, board())
        task = build_index(self.phase)[0]["T-2"]
        self.assertEqual((task["status"], task["notes"], task["pr"]),
                         ("todo", "branch feat/stream-answers", 212))
        self.assertNotIn("local", task)
        self.assertNotIn("GONE", [m["id"] for m in self.phase["milestones"]])
        self.assertEqual(roadmap._validate_phase(self.phase), [])

    def test_a_vanished_issue_without_notes_is_dropped(self):
        pull(self.phase, board()[:3])
        self.assertNotIn("T-4", build_index(self.phase)[0])
        self.assertNotIn("GONE", [m["id"] for m in self.phase["milestones"]])

    def test_a_parked_task_renders_and_counts_out_of_scope(self):
        pull(self.phase, board()[:1] + board()[2:])
        stats = roadmap.build_stats(self.phase)
        self.assertEqual(stats["total"], 5)
        roadmap.mermaid_source(self.phase)
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / ".claude").mkdir()
            path = Path(root) / ".claude" / "roadmaps.local.json"
            path.write_text(roadmap._canonical_text([self.phase]))
            code, out = run("render", root, "--out", str(Path(root) / "d.html"))
            self.assertEqual(code, 0, out)

    def test_a_renamed_version_keeps_its_milestone_id(self):
        issues = board()
        issues[3]["fields"]["fixVersions"] = [dict(VERSIONS["R2"], name="Release 2b")]
        pull(self.phase, issues)
        self.assertEqual(
            [(m["id"], m["name"]) for m in self.phase["milestones"]],
            [("M1", "Release 1"), ("M2", "Release 2b")])


class Cli(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.root = Path(self.dir.name)
        (self.root / ".claude").mkdir()
        self.committed = self.root / ".claude" / "roadmaps.json"
        self.committed.write_text(roadmap._canonical_text([{
            "name": "Tranche 1", "externalGates": [], "milestones": [{
                "id": "M1", "name": "One", "tasks": [{
                    "id": "1A.1", "description": "old-style task",
                    "status": "todo", "dependsOn": []}]}]}]))
        self.issues = self.root / "issues.json"
        self.issues.write_text(json.dumps({"issues": board()}))
        self.local = self.root / ".claude" / "roadmaps.local.json"

    def start(self):
        return run("pull", str(self.root), "--project", "T", "--name",
                   "Tranche 2", "--issues", str(self.issues))

    def test_pull_creates_the_local_file_and_leaves_the_committed_one(self):
        before = self.committed.read_text()
        code, out = self.start()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.committed.read_text(), before)
        data = json.loads(self.local.read_text())
        self.assertEqual(data[0]["source"], {"kind": "jira", "project": "T"})
        self.assertEqual(resolve_roadmap_path(str(self.root)), self.local)

    def test_dry_run_writes_nothing(self):
        code, out = run("pull", str(self.root), "--project", "T",
                        "--issues", str(self.issues), "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertFalse(self.local.exists())
        self.assertIn("would mirror 3", out)

    def test_pull_without_a_mirror_or_a_project_is_refused(self):
        with self.assertRaises(roadmap.RoadmapError):
            roadmap.cmd_pull(roadmap.argparse.Namespace(
                path=str(self.root), phase=None, project=None, name=None,
                issues=str(self.issues), dry_run=False))

    def test_mirrored_tasks_refuse_claim_assign_release_and_end(self):
        self.start()
        for argv in (["claim", "T-2"], ["assign", "T-2", "--assignee", "Jason"],
                     ["release", "T-2"], ["end", "T-2"]):
            code, out = run(*argv, str(self.root))
            self.assertEqual(code, 1, argv)
            self.assertIn("mirrored from Jira T", out)

    def test_a_local_task_is_claimed_and_ended_as_usual(self):
        self.start()
        data = json.loads(self.local.read_text())
        data[0]["milestones"][0]["tasks"].append({
            "id": "L1", "description": "mine", "status": "todo",
            "dependsOn": [], "local": True})
        self.local.write_text(roadmap._canonical_text(data))
        code, out = run("claim", "L1", str(self.root), "--assignee", "Jason")
        self.assertEqual(code, 0, out)
        self.assertEqual(run("validate", str(self.root))[0], 0)

    def test_history_dating_is_refused_on_a_mirror(self):
        self.start()
        for command in ("stamp-ended", "backfill-ended"):
            code, out = run(command, str(self.root))
            self.assertEqual(code, 1)
            self.assertIn("arrive with `roadmap.py pull`", out)

    def test_ready_groups_by_epic(self):
        self.start()
        code, out = run("ready", str(self.root), "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["groups"]["topic"],
                         {"Ask a question": ["T-2"]})

    def test_the_committed_roadmap_is_still_reachable_by_path(self):
        self.start()
        code, out = run("ready", str(self.committed))
        self.assertEqual(code, 0)
        self.assertIn("1A.1", out)

    def test_hooks_stay_silent_beside_a_mirror(self):
        self.assertIsNotNone(_roadmap_hooks.load_roadmap(self.root))
        self.start()
        self.assertIsNone(_roadmap_hooks.load_roadmap(self.root))

    def test_a_bad_source_fails_validate(self):
        self.start()
        data = json.loads(self.local.read_text())
        data[0]["source"] = {"kind": "trello"}
        self.local.write_text(roadmap._canonical_text(data))
        code, out = run("validate", str(self.root))
        self.assertEqual(code, 1)
        self.assertIn("source: kind 'trello'", out)


class Reading(unittest.TestCase):
    def test_credentials_come_from_the_project_env_file(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, ".env").write_text(
                'JIRA_BASE_URL=https://example.test\nexport JIRA_EMAIL="a@b.c"\n'
                "JIRA_API_TOKEN='t0ken'\nOTHER=1\n")
            with unittest.mock.patch.dict("os.environ", {}, clear=True):
                found = jira.credentials(root)
        self.assertEqual(found, {"JIRA_BASE_URL": "https://example.test",
                                 "JIRA_EMAIL": "a@b.c", "JIRA_API_TOKEN": "t0ken"})

    def test_missing_credentials_name_what_is_missing(self):
        with tempfile.TemporaryDirectory() as root:
            with unittest.mock.patch.dict("os.environ", {}, clear=True):
                with self.assertRaisesRegex(roadmap.RoadmapError, "JIRA_EMAIL"):
                    jira.credentials(root)

    def test_a_project_key_that_could_break_the_query_is_refused(self):
        with self.assertRaises(roadmap.RoadmapError):
            jira.fetch_issues({"project": 'T" OR 1=1'}, {})

    def test_fetch_follows_pages(self):
        pages = [{"issues": board()[:2], "nextPageToken": "next"},
                 {"issues": board()[2:]}]
        sent = []

        @contextlib.contextmanager
        def opener(request, timeout):
            sent.append(json.loads(request.data))
            yield io.BytesIO(json.dumps(pages[len(sent) - 1]).encode())

        creds = {"JIRA_BASE_URL": "https://example.test", "JIRA_EMAIL": "a",
                 "JIRA_API_TOKEN": "b"}
        issues = jira.fetch_issues({"project": "TST"}, creds, opener)
        self.assertEqual([i["key"] for i in issues], ["T-1", "T-2", "T-3", "T-4"])
        self.assertEqual(sent[1]["nextPageToken"], "next")


if __name__ == "__main__":
    unittest.main()
