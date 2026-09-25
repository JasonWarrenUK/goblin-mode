#!/usr/bin/env python3
"""Claude Code hooks for roadmap claims: notice when work starts on a branch
and have Claude offer to claim the task it implements.

Called through `roadmap.py hook EVENT`, which swallows every error, because a
hook must never break a session.

- session-start: on a feature branch that claims nothing, add a context line
  nudging a claim; on one that does, name what it claims.
- post-tool-use: after a git command or Claude's worktree tool, find local
  branches created in the last WINDOW_SECONDS (from their reflogs, so every
  way of creating a branch counts), checked out somewhere and claiming
  nothing, and nudge once per branch.

A branch claims a task when, relative to its merge-base with the default
branch, the task gained a `started` date or became `done`. When that can't be
worked out (no base ref, no merge-base, no roadmap or phase at the base) the
hooks stay silent rather than guess. Claude Code's own subagent worktrees
(branches named worktree-agent-*) are throwaway and never nudged. The only
state is local git config, branch.<name>.roadmapClaim: `asked` (nudged once
already) or `none` (the user said the branch is not roadmap work). Stdlib
only, Python 3.8+.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import time
from pathlib import Path

from _roadmap_core import RoadmapError, active_phase, build_index

WINDOW_SECONDS = 120
MARKER = "roadmapClaim"
MAX_CANDIDATES = 8
ROADMAP = ".claude/roadmaps.json"
SUBAGENT_BRANCH = "worktree-agent-"
_CREATED = "branch: Created from "
_REFLOG_LINE = re.compile(
    r"^(?P<old>[0-9a-f]{40,64}) [0-9a-f]{40,64} .* (?P<ts>\d+) [+-]\d{4}\t(?P<msg>.*)$")


def run(event, stream, cli_path, ready_fn):
    """Read the hook payload from `stream` and print this event's output.
    `ready_fn` is roadmap.py's build_ready, passed in to avoid a circular
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


def load_roadmap(checkout):
    """The active phase of the roadmap at the root of `checkout`, or None."""
    try:
        return active_phase(json.loads((Path(checkout) / ROADMAP).read_text()))
    except (OSError, ValueError, RoadmapError):
        return None


def branch_claims(checkout, base, phase):
    """Ids of the tasks the branch checked out in `checkout` claims: tasks
    that gained `started`, or became done, since the merge-base with `base`.
    Uncommitted edits count, since the working-tree roadmap is compared.
    None when there is no base to compare with: no base ref, no merge-base
    (a shallow clone, unrelated history) or no roadmap or phase there."""
    tasks, _milestones, _gates = build_index(phase)
    merge_base = _git(checkout, "merge-base", "HEAD", base) if base else None
    text = _git(checkout, "show", f"{merge_base}:{ROADMAP}") if merge_base else None
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
    except (ValueError, RoadmapError):
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
    if _git(top, "config", "--get", f"branch.{branch}.{MARKER}") == "none":
        return ""
    phase = load_roadmap(top)
    if phase is None or branch.startswith(SUBAGENT_BRANCH):
        return ""
    claims = branch_claims(top, base, phase)
    if claims is None:
        return ""
    if claims:
        return f"Roadmap: branch `{branch}` claims {', '.join(claims)}."
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
        if _git(top, "config", "--get", f"branch.{branch}.{MARKER}") is not None:
            continue
        # A local copy of an existing remote branch is someone's work already
        if source in (f"origin/{branch}", f"refs/remotes/origin/{branch}"):
            continue
        if checkouts is None:
            checkouts = worktrees(top)
        checkout = checkouts.get(branch)
        phase = load_roadmap(checkout) if checkout else None
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
    roadmap = q(str(checkout / ROADMAP))
    return (
        f"Roadmap: branch `{branch}` (checkout {checkout}) claims no roadmap "
        "task yet. If its work is one of these ready tasks, ask the user once, "
        "in a single question, whether it is one of them, who is doing it "
        "(offer the task's assignee if it has one; never guess a name) and "
        "whether to push the branch so the team sees the claim: "
        + "; ".join(_candidate(c) for c in ready) + ".\n"
        f"To claim: python3 {cli} claim <ID> {roadmap} [--assignee <name>], "
        f"then git -C {at} commit -m \"chore(roadmap): claim <ID>\" -- {ROADMAP} "
        "(ask first if that file already has other uncommitted changes), then "
        f"git -C {at} push -u origin {q(branch)} only if they agreed.\n"
        f"If it is not roadmap work, run git -C {at} config "
        f"{q(f'branch.{branch}.{MARKER}')} none so nobody asks again. If the "
        "user has already approved working on a specific task in this "
        "session, claim that task without asking. If you cannot ask the user, "
        "do nothing."
    )
