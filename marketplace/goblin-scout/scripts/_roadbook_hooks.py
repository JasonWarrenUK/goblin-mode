#!/usr/bin/env python3
"""Claude Code hooks for trails (claimed waypoints): notice when work starts
on a branch and have Claude offer to claim the waypoint it implements.

Called through `roadbook.py hook EVENT`, which swallows every error, because a
hook must never break a session.

- session-start: on a feature branch that claims nothing, add a context line
  nudging a claim; on one that does, name what it claims.
- post-tool-use: after a git command or Claude's worktree tool, find local
  branches created in the last WINDOW_SECONDS (from their reflogs, so every
  way of creating a branch counts), checked out somewhere and claiming
  nothing, and nudge once per branch.

A branch claims a task when, relative to its merge-base with the default
branch, the task gained a `started` date or became `done`. When that can't be
worked out (no base ref, no merge-base, no roadbook or phase at the base) the
hooks stay silent rather than guess. Claude Code's own subagent worktrees
(branches named worktree-agent-*) are throwaway and never nudged. The only
state is local git config, branch.<name>.roadbookClaim: `asked` (nudged once
already) or `none` (the user said the branch is not roadbook work), read
from branch.<name>.roadmapClaim when a 2.x roadmap plugin set it. A roadbook
is read under its pre-3.0.0 name, .claude/roadmaps.json, wherever it has not
been moved yet, the merge-base included. Stdlib only, Python 3.8+.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import time
from pathlib import Path

from _roadbook_core import (
    LEGACY_ROADBOOK_NAME,
    LOCAL_NAMES,
    ROADBOOK_NAME,
    RoadbookError,
    active_phase,
    build_index,
)

WINDOW_SECONDS = 120
MARKER = "roadbookClaim"
LEGACY_MARKER = "roadmapClaim"
MAX_CANDIDATES = 8
ROADBOOK_RELS = (f".claude/{ROADBOOK_NAME}", f".claude/{LEGACY_ROADBOOK_NAME}")
SUBAGENT_BRANCH = "worktree-agent-"
_CREATED = "branch: Created from "
_REFLOG_LINE = re.compile(
    r"^(?P<old>[0-9a-f]{40,64}) [0-9a-f]{40,64} .* (?P<ts>\d+) [+-]\d{4}\t(?P<msg>.*)$")


def run(event, stream, cli_path, ready_fn):
    """Read the hook payload from `stream` and print this event's output.
    `ready_fn` is roadbook.py's build_ready, passed in to avoid a circular
    import."""
    try:
        payload = json.loads(stream.read() or "{}")
    except ValueError:
        payload = {}
    # A subagent cannot ask the user anything, so it gets no nudge
    if not isinstance(payload, dict) or payload.get("agent_id"):
        return
    cwd = Path(payload.get("cwd") or os.getcwd())
    if event == "session-start":
        text = session_start(cwd, cli_path, ready_fn)
        if text:
            print(text)
    elif event == "post-tool-use":
        text = post_tool_use(cwd, cli_path, ready_fn)
        if text:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PostToolUse", "additionalContext": text}}))


def _git(cwd, *args):
    """stdout of a git command run in `cwd`, stripped; None if it failed."""
    try:
        done = subprocess.run(["git", "-C", str(cwd), *args],
                              capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def base_ref(checkout):
    """The ref a branch is measured against: origin's default branch when it
    is known, else the first of origin/main, origin/master, main, master."""
    head = _git(checkout, "symbolic-ref", "--quiet", "--short",
                "refs/remotes/origin/HEAD")
    # origin/HEAD can dangle (a default branch renamed upstream and pruned),
    # so every candidate must resolve to a commit
    for candidate in ([head] if head else []) + ["origin/main", "origin/master", "main", "master"]:
        if _git(checkout, "rev-parse", "--verify", "--quiet",
                candidate + "^{commit}") is not None:
            return candidate
    return None


def default_branch_name(base):
    return base.split("/", 1)[1] if base.startswith("origin/") else base


def roadbook_rel(checkout):
    """The committed roadbook file of `checkout` relative to its root: the
    roadbook name, or the pre-3.0.0 one when only that exists."""
    for rel in ROADBOOK_RELS:
        if (Path(checkout) / rel).exists():
            return rel
    return ROADBOOK_RELS[0]


def branch_marker(top, branch):
    """The branch's nudge state, `asked` or `none`, or None when unset; a 2.x
    plugin's key still counts, so nobody is nudged again after the rename."""
    for key in (MARKER, LEGACY_MARKER):
        value = _git(top, "config", "--get", f"branch.{branch}.{key}")
        if value is not None:
            return value
    return None


def load_roadbook(checkout):
    """The active phase of the roadbook at the root of `checkout`, or None.
    None too when the checkout holds a local roadbook file: that is a phase
    mirrored from a tracker, where work is assigned in the tracker and a
    branch claims nothing."""
    if any((Path(checkout) / ".claude" / name).exists() for name in LOCAL_NAMES):
        return None
    try:
        return active_phase(json.loads(
            (Path(checkout) / roadbook_rel(checkout)).read_text()))
    except (OSError, ValueError, RoadbookError):
        return None


def branch_claims(checkout, base, phase):
    """Ids of the waypoints the branch checked out in `checkout` claims:
    tasks that gained `started`, or became done, since the merge-base with
    `base`. Uncommitted edits count, since the working-tree roadbook is
    compared. None when there is no base to compare with: no base ref, no
    merge-base (a shallow clone, unrelated history) or no roadbook or phase
    there. The merge-base may predate the move from roadmaps.json."""
    tasks, _milestones, _gates = build_index(phase)
    merge_base = _git(checkout, "merge-base", "HEAD", base) if base else None
    text = None
    for rel in ROADBOOK_RELS if merge_base else ():
        text = _git(checkout, "show", f"{merge_base}:{rel}")
        if text:
            break
    if not text:
        return None
    try:
        data = json.loads(text)
        phases = data if isinstance(data, list) else [data]
        same = [p for p in phases
                if isinstance(p, dict) and p.get("name") == phase.get("name")]
        if not same:
            return None
        before = build_index(same[-1])[0]
    except (ValueError, RoadbookError):
        return None
    claimed = []
    for tid, task in tasks.items():
        was = before.get(tid, {})
        started = bool(task.get("started")) and not was.get("started")
        finished = (task.get("status") == "done"
                    and was.get("status") not in ("done", "out_of_scope"))
        if started or finished:
            claimed.append(tid)
    return claimed


def recent_branches(common_dir, now):
    """(branch, source) for each local branch whose reflog starts with a
    creation entry newer than WINDOW_SECONDS; `source` is what it was created
    from, as the reflog words it."""
    root = Path(common_dir) / "logs" / "refs" / "heads"
    found = []
    if not root.is_dir():
        return found
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            with path.open(encoding="utf-8", errors="replace") as fh:
                first = fh.readline().rstrip("\n")
        except OSError:
            continue
        match = _REFLOG_LINE.match(first)
        if not match or set(match.group("old")) != {"0"}:
            continue
        message = match.group("msg")
        if not message.startswith(_CREATED):
            continue
        if now - int(match.group("ts")) > WINDOW_SECONDS:
            continue
        found.append((path.relative_to(root).as_posix(), message[len(_CREATED):]))
    return found


def worktrees(checkout):
    """{branch: path} for every branch checked out in some worktree."""
    listing = _git(checkout, "worktree", "list", "--porcelain") or ""
    result = {}
    path = None
    for line in listing.splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):]
        elif line.startswith("branch refs/heads/") and path:
            result[line[len("branch refs/heads/"):]] = path
    return result


def session_start(cwd, cli_path, ready_fn):
    top = _git(cwd, "rev-parse", "--show-toplevel")
    branch = _git(top, "symbolic-ref", "--quiet", "--short", "HEAD") if top else None
    if not branch:
        return ""
    base = base_ref(top)
    if base is None or branch == default_branch_name(base):
        return ""
    if branch_marker(top, branch) == "none":
        return ""
    phase = load_roadbook(top)
    if phase is None or branch.startswith(SUBAGENT_BRANCH):
        return ""
    claims = branch_claims(top, base, phase)
    if claims is None:
        return ""
    if claims:
        return f"Roadbook: branch `{branch}` claims {', '.join(claims)}."
    text = nudge(branch, Path(top), phase, cli_path, ready_fn)
    if text:
        # so the first git command of the session doesn't nudge it again
        _git(top, "config", f"branch.{branch}.{MARKER}", "asked")
    return text


def post_tool_use(cwd, cli_path, ready_fn):
    top = _git(cwd, "rev-parse", "--show-toplevel")
    common = _git(top, "rev-parse", "--git-common-dir") if top else None
    if not common:
        return ""
    common_dir = Path(common) if os.path.isabs(common) else Path(top) / common
    texts = []
    checkouts = None
    for branch, source in recent_branches(common_dir, time.time()):
        if branch.startswith(SUBAGENT_BRANCH):
            continue
        if branch_marker(top, branch) is not None:
            continue
        # A local copy of an existing remote branch is someone's work already
        if source in (f"origin/{branch}", f"refs/remotes/origin/{branch}"):
            continue
        if checkouts is None:
            checkouts = worktrees(top)
        checkout = checkouts.get(branch)
        phase = load_roadbook(checkout) if checkout else None
        if phase is None:
            continue
        base = base_ref(checkout)
        if base is None or branch == default_branch_name(base):
            continue
        if branch_claims(checkout, base, phase) != []:
            continue
        text = nudge(branch, Path(checkout), phase, cli_path, ready_fn)
        if text:
            _git(checkout, "config", f"branch.{branch}.{MARKER}", "asked")
            texts.append(text)
    return "\n\n".join(texts)


def _candidate(c):
    headline = c["description"].split(": ", 1)[0]
    if len(headline) > 60:
        headline = headline[:59].rstrip() + "…"
    who = f" ({c['assignee']})" if c.get("assignee") else ""
    return f"{c['id']} {headline}{who}"


def nudge(branch, checkout, phase, cli_path, ready_fn):
    """The context that has Claude offer a claim; empty when nothing is ready
    to claim."""
    ready = ready_fn(phase)["candidates"][:MAX_CANDIDATES]
    if not ready:
        return ""
    q = shlex.quote
    at = q(str(checkout))
    cli = q(str(cli_path))
    rel = roadbook_rel(checkout)
    roadbook = q(str(checkout / rel))
    if rel == ROADBOOK_RELS[0]:
        commit = f"git -C {at} commit -m \"chore(roadbook): claim <ID>\" -- {rel}"
    else:
        # the claim is the first write, which moves the file to its roadbook name
        commit = (f"git -C {at} add {ROADBOOK_RELS[0]} && git -C {at} commit -m "
                  f"\"chore(roadbook): claim <ID>\" -- {rel} {ROADBOOK_RELS[0]}")
    return (
        f"Roadbook: branch `{branch}` (checkout {checkout}) claims no roadbook "
        "waypoint yet. If its work is one of these ready waypoints, ask the "
        "user once, in a single question, whether it is one of them, which "
        "scout is doing it (offer the waypoint's assignee if it has one; never "
        "guess a name) and whether to push the branch so the team sees the "
        "trail: " + "; ".join(_candidate(c) for c in ready) + ".\n"
        f"To claim: python3 {cli} claim <ID> {roadbook} [--assignee <name>], "
        f"then {commit} "
        "(ask first if that file already has other uncommitted changes), then "
        f"git -C {at} push -u origin {q(branch)} only if they agreed. The "
        "goblin-scout:start-trail skill runs this whole flow.\n"
        f"If it is not roadbook work, run git -C {at} config "
        f"{q(f'branch.{branch}.{MARKER}')} none so nobody asks again. If the "
        "user has already approved working on a specific task in this "
        "session, claim that task without asking. If you cannot ask the user, "
        "do nothing."
    )
