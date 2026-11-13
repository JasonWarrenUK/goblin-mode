#!/usr/bin/env python3
"""Mirror a Jira project into a roadmap phase: the read half of `roadmap.py pull`.

A phase whose `source` is `{"kind": "jira", "project": KEY}` is a mirror of
that Jira project. Jira is the source of truth; nothing here writes to it.

What maps to what:

- a fix version becomes a milestone (matched afterwards by the version's id,
  so renaming one in Jira renames the milestone and keeps its `M{N}`);
  issues with no fix version sit in `M0`, "Unscheduled";
- an epic becomes the `topic` of every issue under it, never a task;
- every other issue becomes a task whose id is the Jira key;
- a Blocks link becomes a `dependsOn` edge, and an issue also depends on each
  of its child issues, so a story waits for the tickets it was split into,
  and a child inherits whatever blocks its story, so a split of a blocked
  story is not offered as ready;
- a status in Jira's done category is `done`; every other status is left to
  the dependency graph (`todo` or `blocked`), with `started` set while Jira
  has the issue in progress, which is what makes views show it in progress.

The tracker owns a mirrored task's description, status, edges to other
mirrored tasks, topic, assignee, `started`, `ended` and `tracker`. Everything
else on it survives a pull: `notes`, `pr`, soft edges and any edge to a local
task. A task marked `"local": true` is the user's own and is never rewritten;
when something it depended on leaves Jira the edge moves to its `orphaned`
list and comes back if the issue does.

A mirrored task whose issue leaves Jira is dropped, unless it carries `notes`
or a `pr`: then it is parked, out of scope, in the "Gone from Jira" milestone
so nothing the user wrote is lost. It is theirs to delete. If the issue comes
back, the notes go back onto it.

merge() is pure (issues in, phase mutated, report out) so it is tested without
a network. Stdlib only, Python 3.8+. British spelling throughout.
"""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from _roadmap_core import (
    RoadmapError,
    build_index,
    find_cycles,
    is_held,
    is_local_task,
    recompute_all,
)

ENV_KEYS = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")
FIELDS = ["summary", "status", "issuetype", "parent", "fixVersions",
          "issuelinks", "assignee", "resolutiondate",
          "statuscategorychangedate"]
UNSCHEDULED_ID = "M0"
UNSCHEDULED_NAME = "Unscheduled"
# Where a mirrored task goes when its issue leaves Jira while it still carries
# the user's notes or pr: parked out of scope, never silently dropped.
GONE_ID = "GONE"
GONE_NAME = "Gone from Jira"
GONE_FIELDS = ("notes", "pr")
# What a pull never overwrites on a mirrored task.
KEPT_FIELDS = ("softDependsOn", "softMilestone", "iterative", "notes", "pr")
_PROJECT_KEY = re.compile(r"[A-Z][A-Z0-9_]{1,31}")
_ENV_LINE = re.compile(r"^\s*(?:export\s+)?(JIRA_[A-Z_]+)\s*=\s*(.*?)\s*$")


# ---------------------------------------------------------------------------
# reading Jira
# ---------------------------------------------------------------------------
def credentials(root):
    """JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN from the environment,
    else from `.env.local` or `.env` at the project root."""
    found = {k: os.environ[k] for k in ENV_KEYS if os.environ.get(k)}
    for name in (".env.local", ".env"):
        try:
            lines = (Path(root) / name).read_text().splitlines()
        except OSError:
            continue
        for line in lines:
            match = _ENV_LINE.match(line)
            if match and match.group(1) in ENV_KEYS:
                found.setdefault(match.group(1), match.group(2).strip("\"'"))
    missing = [k for k in ENV_KEYS if not found.get(k)]
    if missing:
        raise RoadmapError(
            f"{', '.join(missing)} not set in the environment or in "
            f"{root}/.env; a pull needs all of {', '.join(ENV_KEYS)}")
    return found


def fetch_issues(source, creds, opener=urllib.request.urlopen):
    """Every issue of the source's project, as Jira's search returns them."""
    project = str(source.get("project", ""))
    if not _PROJECT_KEY.fullmatch(project):
        raise RoadmapError(f"source project {project!r} is not a Jira project key")
    jql = source.get("jql") or f'project = "{project}" ORDER BY key'
    auth = base64.b64encode(
        f"{creds['JIRA_EMAIL']}:{creds['JIRA_API_TOKEN']}".encode()).decode()
    url = creds["JIRA_BASE_URL"].rstrip("/") + "/rest/api/3/search/jql"
    issues, token = [], None
    while True:
        body = {"jql": jql, "maxResults": 100, "fields": FIELDS}
        if token:
            body["nextPageToken"] = token
        request = urllib.request.Request(
            url, data=json.dumps(body).encode(),
            headers={"Authorization": "Basic " + auth,
                     "Accept": "application/json",
                     "Content-Type": "application/json"})
        try:
            with opener(request, timeout=30) as response:
                page = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:200].decode("utf-8", "replace")
            raise RoadmapError(f"Jira answered {exc.code} to the search: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise RoadmapError(f"could not read Jira: {exc}") from exc
        issues.extend(page.get("issues", []))
        token = page.get("nextPageToken")
        if not token:
            return issues


def _day(stamp):
    """`2026-11-10T09:30:00.000+0000` -> `2026-11-10`; anything else -> None."""
    text = str(stamp or "")[:10]
    return text if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) else None


def normalise(raw):
    """One search-result issue as the flat dict merge() reads."""
    fields = raw.get("fields") or {}
    issue_type = fields.get("issuetype") or {}
    status = fields.get("status") or {}
    blocked_by = []
    for link in fields.get("issuelinks") or []:
        blocker = link.get("inwardIssue")
        if blocker and (link.get("type") or {}).get("name") == "Blocks":
            blocked_by.append(blocker["key"])
    return {
        "key": raw["key"],
        "type": issue_type.get("name", ""),
        "epic": (issue_type.get("hierarchyLevel") or 0) >= 1,
        "summary": (fields.get("summary") or "").strip(),
        "status": status.get("name", ""),
        "category": (status.get("statusCategory") or {}).get("key", "new"),
        "parent": (fields.get("parent") or {}).get("key"),
        "versions": [
            {"id": str(v.get("id", "")), "name": v.get("name", ""),
             "start": v.get("startDate") or "", "release": v.get("releaseDate") or ""}
            for v in fields.get("fixVersions") or []],
        "blocked_by": blocked_by,
        "assignee": ((fields.get("assignee") or {}).get("displayName") or "").strip(),
        "changed": _day(fields.get("statuscategorychangedate")),
        "resolved": _day(fields.get("resolutiondate")),
    }


# ---------------------------------------------------------------------------
# merging into the phase
# ---------------------------------------------------------------------------
def _natural(key):
    return [int(part) if part.isdigit() else part
            for part in re.split(r"(\d+)", str(key))]


def _version_order(version):
    return (version["release"] or "9999", version["start"] or "9999", version["name"])


def _ordered(task, order):
    known = [k for k in order if k in task]
    return {k: task[k] for k in known + [k for k in task if k not in order]}


def _milestone_number(mid):
    match = re.fullmatch(r"M(\d+)", str(mid))
    return int(match.group(1)) if match else 0


def merge(phase, issues, field_order):
    """Rewrite the phase's mirrored tasks from `issues` (normalise() output),
    leaving local tasks and local milestones in place, then recompute every
    status. Returns the report; raises RoadmapError on a dependency cycle,
    before anything in `phase` has changed."""
    old_milestones = phase.get("milestones") or []
    old_tasks, old_home = {}, {}
    for milestone in old_milestones:
        for task in milestone.get("tasks", []):
            old_tasks[task["id"]] = task
            old_home[task["id"]] = milestone["id"]
    local = {tid: t for tid, t in old_tasks.items() if is_local_task(t)}

    by_key = {i["key"]: i for i in issues}
    epics = {k for k, i in by_key.items() if i["epic"]}
    work = {k: i for k, i in by_key.items() if not i["epic"]}
    # Parked tasks: an issue that came back takes its notes with it; one that
    # has just gone, with notes or a pr on it, is parked now.
    was_parked = {tid for tid, t in local.items()
                  if (t.get("tracker") or {}).get("gone")}
    for tid in was_parked & set(work):
        del local[tid]
    newly_parked = []
    for tid, was in old_tasks.items():
        if is_local_task(was) or tid in work:
            continue
        if not any(was.get(f) for f in GONE_FIELDS):
            continue
        parked = {"id": tid, "description": was.get("description", ""),
                  "status": "out_of_scope", "dependsOn": [], "local": True,
                  "tracker": {"status": GONE_NAME, "gone": True,
                              "type": (was.get("tracker") or {}).get("type", "")}}
        for field in GONE_FIELDS:
            if was.get(field):
                parked[field] = was[field]
        local[tid] = _ordered(parked, field_order)
        old_home[tid] = GONE_ID
        newly_parked.append(tid)
    parked_ids = (was_parked - set(work)) | set(newly_parked)
    clash = sorted(set(work) & set(local), key=_natural)
    if clash:
        raise RoadmapError(
            f"local task id(s) {', '.join(clash)} are also Jira keys; rename "
            "the local task(s)")

    def topic_of(key):
        seen = set()
        while key and key not in seen:
            seen.add(key)
            parent = by_key.get(key, {}).get("parent")
            if parent in epics:
                return by_key[parent]["summary"]
            key = parent
        return ""

    def version_of(key):
        seen = set()
        while key in work and key not in seen:
            seen.add(key)
            versions = sorted(work[key]["versions"], key=_version_order)
            if versions:
                return versions[0]
            key = work[key]["parent"]
        return None

    def inherited_blockers(key):
        """What blocks the issue, and what blocks the story it is a split of:
        a sub-task is not ready while its story still waits on another."""
        blockers, seen = [], set()
        while key in work and key not in seen:
            seen.add(key)
            blockers.extend(work[key]["blocked_by"])
            key = work[key]["parent"]
        return [b for b in blockers if b not in seen]

    children = {}
    for key, issue in work.items():
        if issue["parent"] in work:
            children.setdefault(issue["parent"], []).append(key)

    # Milestones: one per fix version in use, keeping the id it already has.
    held_ids = {(m.get("tracker") or {}).get("version"): m["id"]
                for m in old_milestones if "tracker" in m}
    versions, members = {}, {}
    for key in work:
        version = version_of(key)
        vid = version["id"] if version else ""
        if version:
            versions[vid] = version
        members.setdefault(vid, []).append(key)
    local_milestones = [m for m in old_milestones if "tracker" not in m]
    if newly_parked and GONE_ID not in {m["id"] for m in local_milestones}:
        local_milestones.append({"id": GONE_ID, "name": GONE_NAME, "tasks": []})
    taken = {m["id"] for m in local_milestones} | set(held_ids.values())
    next_number = max([_milestone_number(mid) for mid in taken] + [0]) + 1
    milestone_of_version = {}
    for vid in sorted(versions, key=lambda v: _version_order(versions[v])):
        if vid in held_ids:
            milestone_of_version[vid] = held_ids[vid]
        else:
            milestone_of_version[vid] = f"M{next_number}"
            next_number += 1
    milestone_of_version[""] = held_ids.get("", UNSCHEDULED_ID)

    report = {"added": [], "removed": [], "changed": [], "drift": [],
              "orphans": [], "warnings": []}

    # Mirrored tasks.
    surviving = set(work) | set(local) | {m["id"] for m in local_milestones} \
        | {g.get("id") for g in phase.get("externalGates", [])}
    surviving -= parked_ids
    local_targets = surviving - set(work)
    new_tasks, home = {}, {}
    for key in sorted(work, key=_natural):
        issue = work[key]
        was = old_tasks.get(key, {})
        done = issue["category"] == "done"
        depends = sorted({b for b in inherited_blockers(key) if b in work and b != key}
                         | set(children.get(key, [])), key=_natural)
        depends += [d for d in was.get("dependsOn", [])
                    if d in local_targets and d not in depends]
        task = {"id": key, "description": issue["summary"],
                "status": "done" if done else "todo", "dependsOn": depends}
        for field in KEPT_FIELDS:
            if field in was:
                task[field] = was[field]
        if "softDependsOn" in task:
            kept = [d for d in task["softDependsOn"] if d in surviving]
            dropped = [d for d in task["softDependsOn"] if d not in surviving]
            if dropped:
                report["warnings"].append(
                    f"{key}: soft dependency on {', '.join(dropped)} dropped, "
                    "no longer in Jira")
            if kept:
                task["softDependsOn"] = kept
            else:
                del task["softDependsOn"]
        topic = topic_of(key)
        if topic:
            task["topic"] = topic
        task["tracker"] = {"status": issue["status"], "type": issue["type"]}
        if issue["assignee"]:
            task["assignee"] = issue["assignee"]
        ended = None
        if done:
            ended = (was.get("ended") if was.get("status") == "done" else None) \
                or issue["resolved"] or issue["changed"]
        if issue["category"] == "indeterminate":
            started = was.get("started") or issue["changed"]
        else:
            started = was.get("started") if done else None
        if started and not (ended and ended < started):
            task["started"] = started
        if ended:
            task["ended"] = ended
        new_tasks[key] = _ordered(task, field_order)
        version = version_of(key)
        home[key] = milestone_of_version[version["id"] if version else ""]

    # Local tasks stay where they are; a lost milestone sends them to M0.
    tracker_milestones = set(milestone_of_version.values())
    for tid, task in local.items():
        target = old_home[tid]
        if target not in tracker_milestones and target not in {m["id"] for m in local_milestones}:
            report["orphans"].append(
                f"{tid}: its milestone {target} left Jira; moved to "
                f"{milestone_of_version['']} ({UNSCHEDULED_NAME})")
            target = milestone_of_version[""]
        home[tid] = target

    all_ids = set(new_tasks) | set(local)
    all_milestones = {home[tid] for tid in all_ids} | {m["id"] for m in local_milestones}
    reachable = (all_ids | all_milestones
                 | {g.get("id") for g in phase.get("externalGates", [])}) - parked_ids
    local_edits = {}
    for tid, task in local.items():
        depends = list(task.get("dependsOn", []))
        orphaned = list(task.get("orphaned", []))
        back = [d for d in orphaned if d in reachable]
        gone = [d for d in depends if d not in reachable]
        if not back and not gone and not orphaned and \
                all(d in reachable for d in task.get("softDependsOn", [])):
            continue
        depends = [d for d in depends if d in reachable] + [d for d in back if d not in depends]
        orphaned = [d for d in orphaned if d not in reachable] + gone
        edited = dict(task)
        edited["dependsOn"] = depends
        if orphaned:
            edited["orphaned"] = orphaned
            report["orphans"].append(
                f"{tid}: depended on {', '.join(orphaned)}, no longer in Jira")
        else:
            edited.pop("orphaned", None)
        soft = [d for d in edited.get("softDependsOn", []) if d in reachable]
        if "softDependsOn" in edited and len(soft) != len(edited["softDependsOn"]):
            report["warnings"].append(f"{tid}: a soft dependency left Jira and was dropped")
            if soft:
                edited["softDependsOn"] = soft
            else:
                del edited["softDependsOn"]
        if back:
            report["changed"].append(f"{tid}: {', '.join(back)} is back in Jira; edge restored")
        local_edits[tid] = _ordered(edited, field_order)

    final_tasks = {**new_tasks, **{tid: local_edits.get(tid, t) for tid, t in local.items()}}

    # Assemble the milestone list: tracker milestones in version order, then
    # Unscheduled, then the user's own milestones.
    def members_of(mid):
        mirrored = [final_tasks[k] for k in sorted(new_tasks, key=_natural) if home[k] == mid]
        mine = [final_tasks[tid] for tid in local if home[tid] == mid]
        return mirrored + mine

    old_by_id = {m["id"]: m for m in old_milestones}
    assembled = []
    for vid in sorted(versions, key=lambda v: _version_order(versions[v])) + [""]:
        mid = milestone_of_version[vid]
        tasks = members_of(mid)
        if not tasks:
            continue
        previous = old_by_id.get(mid, {})
        milestone = {"id": mid,
                     "name": versions[vid]["name"] if vid else UNSCHEDULED_NAME}
        if previous.get("goal"):
            milestone["goal"] = previous["goal"]
        milestone["tracker"] = {"version": vid}
        milestone["tasks"] = tasks
        assembled.append(milestone)
    for milestone in local_milestones:
        kept = dict(milestone)
        kept["tasks"] = members_of(milestone["id"])
        if kept["tasks"] or milestone["id"] != GONE_ID:
            assembled.append(kept)

    candidate = dict(phase)
    candidate["milestones"] = assembled
    tasks, milestones, gates = build_index(candidate)
    cycles = find_cycles(tasks, milestones)
    if cycles:
        raise RoadmapError(
            "the Jira links and parent/child tickets form a cycle, so nothing "
            "was written: " + "; ".join(" -> ".join(c) for c in cycles))
    computed = recompute_all(tasks, milestones, gates)
    for tid, task in tasks.items():
        if not is_held(task):
            task["status"] = computed[tid]

    # Report what moved, against what the file held before.
    for key in sorted(new_tasks, key=_natural):
        task, was = tasks[key], old_tasks.get(key)
        if was is None or is_local_task(was):
            report["added"].append(f"{key} {task['description']}")
            continue
        notes = []
        if was.get("description") != task["description"]:
            notes.append("renamed")
        if (was.get("tracker") or {}).get("status") != task["tracker"]["status"]:
            notes.append(f"{(was.get('tracker') or {}).get('status', '?')} -> "
                         f"{task['tracker']['status']}")
        elif was.get("status") != task["status"]:
            notes.append(f"{was.get('status')} -> {task['status']}")
        if was.get("assignee", "") != task.get("assignee", ""):
            notes.append(f"assignee {was.get('assignee') or 'none'} -> "
                         f"{task.get('assignee') or 'none'}")
        if old_home.get(key) != home[key]:
            notes.append(f"{old_home.get(key)} -> {home[key]}")
        if sorted(was.get("dependsOn", [])) != sorted(task["dependsOn"]):
            notes.append("dependencies changed")
        if notes:
            report["changed"].append(f"{key}: {', '.join(notes)}")
    for tid in sorted(newly_parked, key=_natural):
        report["removed"].append(
            f"{tid} {old_tasks[tid].get('description', '')} (parked in "
            f"'{GONE_NAME}' with its {' and '.join(f for f in GONE_FIELDS if old_tasks[tid].get(f))})")
    for tid in sorted(set(old_tasks) - set(local) - set(new_tasks), key=_natural):
        was = old_tasks[tid]
        kept = [f for f in ("notes", "pr") if was.get(f)]
        report["removed"].append(
            f"{tid} {was.get('description', '')}"
            + (f" (its {' and '.join(kept)} went with it)" if kept else ""))

    for key in sorted(new_tasks, key=_natural):
        task = tasks[key]
        open_blockers = [d for d in task["dependsOn"]
                         if d in tasks and tasks[d]["status"] not in ("done", "out_of_scope")]
        if not open_blockers:
            continue
        if work[key]["category"] == "indeterminate":
            report["drift"].append(
                f"{key} is {work[key]['status']} in Jira while "
                f"{', '.join(open_blockers)} still blocks it")
        elif work[key]["category"] == "done":
            report["drift"].append(
                f"{key} is {work[key]['status']} in Jira before "
                f"{', '.join(open_blockers)}, which it depends on")

    phase["milestones"] = assembled
    report["tasks"] = len(new_tasks)
    report["local"] = len(local)
    report["milestones"] = len(assembled)
    return report


def describe(report, phase_name, dry_run):
    """The lines `pull` prints for a report."""
    verb = "would mirror" if dry_run else "mirrored"
    lines = [f"✓ {verb} {report['tasks']} Jira task(s) into '{phase_name}' "
             f"across {report['milestones']} milestone(s); "
             f"{report['local']} local task(s) untouched"]
    for title, key in (("added", "added"), ("gone from Jira", "removed"),
                       ("changed", "changed"), ("Jira and the graph disagree", "drift"),
                       ("local tasks that lost something", "orphans"),
                       ("warnings", "warnings")):
        if report[key]:
            lines.append(f"{title} ({len(report[key])}):")
            lines.extend(f"  - {entry}" for entry in report[key])
    if not any(report[k] for k in ("added", "removed", "changed")):
        lines.append("nothing changed in Jira since the last pull")
    return lines
