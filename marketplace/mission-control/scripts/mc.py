#!/usr/bin/env python3
"""mission-control: the ledger CLI behind the pane, the tools, the hooks and the skills.

One run per repository at a time. The ledger is a directory of small JSON
files under ~/.claude/mission-control/<repo slug>/, one file per fact, so two
sessions writing different facts never clobber each other:

  run.json                    the run: name, coordinator, base commit, crew plan,
                              numbered assumptions, the "needs Jason" list
  sessions/<session id>.json  one row per session in the run: task, branch,
                              worktree, state, summary, PR
  slots/<resource>.json       who holds a shared resource, since when, for what
  requests/<resource>__<session id>.json   a pending slot request
  briefs/<task>.md            the brief each crew session reads at its first turn
  log.jsonl                   every event, append-only

The project config is <repo>/.claude/mission-control.json (the example beside
this script documents every key). A caller is identified by CLAUDE_CODE_SESSION_ID,
which Claude Code sets for every Bash child, or by --session when the mod
calls on its own behalf. Writes that steer the run (start, end, grant, revoke,
assumptions, marking a need done, the crew plan) are the coordinator session's
alone; `--by-user` stands for the person typing a /mc command in any session.
The PreToolUse hook refuses `--by-user`, `--session` and a `CLAUDE_CODE_SESSION_ID=`
assignment on a Bash line that runs this script, abbreviations and quoting
included, so the model does not borrow another identity by accident. It is a
guard against accidents: a variable expanded later, a copied script or a
hand-written ledger file get past it, and the ledger files are not protected.

Exit codes: 0 done, 1 refused (the reason on stdout as one `✗` line, or JSON
with `--json`), 2 environment or usage error. Stdlib only, Python 3.9+.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import fnmatch
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

CONFIG_REL = ".claude/mission-control.json"
LEDGER_ROOT = Path(os.environ.get("MISSION_CONTROL_HOME") or (Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "mission-control"))
SESSIONS_DIR = Path(os.environ.get("CLAUDE_SESSIONS_DIR") or (Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "sessions"))
STATES = ("briefing", "working", "in-slot", "pr-ready", "blocked", "waiting-jason", "done")
# the states a release puts back; anything else the slot interrupted was plain work
RESTORED_STATES = ("pr-ready", "blocked", "waiting-jason", "done")
BY_USER = "--by-user"
SEPARATORS = re.compile(r"^[();<>|&\n]+$")
REDIRECT = re.compile(r"^&?[<>]+&?$")
ASSIGNMENT = re.compile(r"^[A-Za-z_]\w*=")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1([^\n]*)\n(.*?)\n[ \t]*\2[ \t]*(?=\n|$)", re.DOTALL)


class Refusal(Exception):
    """A refusal the caller can act on; printed as one line, exit 1."""


# ---------------------------------------------------------------- helpers


def now() -> float:
    return time.time()


def clock(ts: float | None) -> str:
    return time.strftime("%H:%M", time.localtime(ts)) if ts else "?"


def run_git(cwd: str | Path, *args: str) -> str | None:
    try:
        done = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def toplevel(cwd: str | Path) -> Path | None:
    top = run_git(cwd, "rev-parse", "--show-toplevel")
    return Path(top) if top else None


def main_checkout(cwd: str | Path) -> Path | None:
    """The main working tree, the same answer from inside any worktree."""
    common = run_git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(common).parent if common else None


def slug_of(path: Path) -> str:
    return str(path).replace("/", "-")


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n")
    os.replace(tmp, path)


def same_path(a: str | Path, b: str | Path) -> bool:
    """Whether two paths name one file: the filesystem decides, so `Code` and `code` on a case-insensitive volume agree."""
    try:
        return os.path.samefile(a, b)
    except OSError:
        return str(a) == str(b)


def inside(path: str | None, root: str | None) -> bool:
    if not path or not root:
        return False
    try:
        p, r = Path(path).resolve(), Path(root).resolve()
    except OSError:
        return False
    return p == r or r in p.parents or any(same_path(parent, r) for parent in (p, *p.parents) if parent.exists() and r.exists())


# ---------------------------------------------------------------- config


def find_config(cwd: str | Path) -> tuple[Path, dict] | None:
    """The project config: the cwd's checkout first, then the main checkout."""
    for root in (toplevel(cwd), main_checkout(cwd)):
        if root is None:
            continue
        path = root / CONFIG_REL
        if path.is_file():
            data = read_json(path)
            if not isinstance(data, dict):
                raise Refusal(f"{path} does not parse as a JSON object")
            return path, data
    return None


def resources(config: dict) -> dict:
    found = config.get("resources")
    return found if isinstance(found, dict) else {}


# ---------------------------------------------------------------- the live session registry


def registry() -> dict[str, dict]:
    """{session id: row} for every live Claude Code session on this machine."""
    rows = {}
    for path in glob.glob(str(SESSIONS_DIR / "*.json")):
        row = read_json(Path(path))
        if not isinstance(row, dict) or not row.get("sessionId") or not row.get("pid"):
            continue
        try:
            os.kill(int(row["pid"]), 0)
        except (OSError, ValueError):
            continue
        rows[str(row["sessionId"])] = row
    return rows


def caller_session(explicit: str | None) -> str | None:
    return explicit or os.environ.get("CLAUDE_CODE_SESSION_ID") or None


def live_coordinator(recorded: dict) -> dict:
    """The coordinator as the registry has it now.

    A session id outlives a restart, a resume or a /clear; its pid, socket and
    name do not. The id is the identity, so the rest is read live and the
    recorded values are only the fallback for a coordinator that is not running.
    """
    row = registry().get(str(recorded.get("session_id") or ""))
    if not row:
        return recorded
    return {
        **recorded,
        "pid": row.get("pid"),
        "socket": row.get("messagingSocketPath") or recorded.get("socket"),
        "name": row.get("name") or recorded.get("name") or "",
        "status": row.get("status"),
    }


def identity(session_id: str | None) -> dict:
    """What the registry knows about a session: pid, socket, name; empty when not live."""
    row = registry().get(session_id or "", {})
    return {
        "session_id": session_id,
        "pid": row.get("pid"),
        "socket": row.get("messagingSocketPath"),
        "name": row.get("name") or "",
        "cwd": row.get("cwd"),
        "status": row.get("status"),
    }


# ---------------------------------------------------------------- the ledger


class Ledger:
    def __init__(self, main: Path):
        self.main = main
        self.slug = slug_of(main)
        self.dir = LEDGER_ROOT / self.slug

    @property
    def run_path(self) -> Path:
        return self.dir / "run.json"

    def run(self) -> dict | None:
        run = read_json(self.run_path)
        if not isinstance(run, dict) or run.get("ended_at"):
            return None
        run["coordinator"] = live_coordinator(run.get("coordinator") or {})
        return run

    def require_run(self) -> dict:
        run = self.run()
        if run is None:
            raise Refusal(f"no active mission-control run for {self.main}; start one with /mission-control:kickoff or `mc.py start --name <name>`")
        return run

    def save_run(self, run: dict) -> None:
        write_json(self.run_path, run)

    @contextlib.contextmanager
    def locked(self):
        """Hold the run's lock across a read-modify-write of run.json, so two sessions never overwrite each other's change."""
        if not self.dir.is_dir():
            yield  # no run: require_run refuses, and the directory is not made here
            return
        with (self.dir / "run.lock").open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield

    def log(self, event: str, **fields) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        with (self.dir / "log.jsonl").open("a") as fh:
            fh.write(json.dumps({"at": now(), "event": event, **fields}) + "\n")

    # sessions
    def session_path(self, session_id: str) -> Path:
        return self.dir / "sessions" / f"{session_id}.json"

    def sessions(self) -> dict[str, dict]:
        rows = {}
        for path in sorted(glob.glob(str(self.dir / "sessions" / "*.json"))):
            row = read_json(Path(path))
            if isinstance(row, dict) and row.get("session_id"):
                rows[row["session_id"]] = row
        return rows

    def save_session(self, row: dict) -> None:
        write_json(self.session_path(row["session_id"]), row)

    # slots
    def slot_path(self, resource: str) -> Path:
        return self.dir / "slots" / f"{resource}.json"

    def slots(self) -> dict[str, dict]:
        rows = {}
        for path in sorted(glob.glob(str(self.dir / "slots" / "*.json"))):
            row = read_json(Path(path))
            if isinstance(row, dict) and row.get("holder"):
                rows[row["resource"]] = row
        return rows

    # requests
    def request_path(self, resource: str, session_id: str) -> Path:
        return self.dir / "requests" / f"{resource}__{session_id}.json"

    def requests(self) -> list[dict]:
        rows = []
        for path in sorted(glob.glob(str(self.dir / "requests" / "*.json"))):
            row = read_json(Path(path))
            if isinstance(row, dict) and row.get("resource"):
                rows.append(row)
        return sorted(rows, key=lambda r: r.get("at", 0))


def ledger_for(cwd: str | Path) -> Ledger:
    main = main_checkout(cwd)
    if main is None:
        raise Refusal(f"{cwd} is not inside a git repository")
    return Ledger(main)


def is_coordinator(run: dict, session_id: str | None) -> bool:
    return bool(session_id) and run.get("coordinator", {}).get("session_id") == session_id


def authorise(run: dict, session_id: str | None, by_user: bool, what: str) -> str:
    """Who may steer the run: the coordinator session, or the person through /mc."""
    if by_user:
        return "user"
    if is_coordinator(run, session_id):
        return "coordinator"
    name = run.get("coordinator", {}).get("name") or run.get("coordinator", {}).get("session_id", "?")
    raise Refusal(f"only the coordinator session ({name}) can {what}; message mission control, or the person runs /mc in any session")


def crew_for(run: dict, cwd: str | None, session_id: str | None, sessions: dict[str, dict]) -> dict | None:
    """The crew-plan entry a session belongs to: by its registered row first, then by the worktree its cwd is in."""
    row = sessions.get(session_id or "")
    for entry in run.get("crew", []):
        if row and (entry.get("task") == row.get("task") or (entry.get("worktree") and row.get("worktree") and same_path(entry["worktree"], row["worktree"]))):
            return entry
    for entry in run.get("crew", []):
        if inside(cwd, entry.get("worktree")):
            return entry
    return None


# ---------------------------------------------------------------- command parsing and gates


SHELLS = {"sh", "bash", "zsh"}
SHELL_C_FLAG = re.compile(r"-[A-Za-z]*c[A-Za-z]*")
SHELL_DEPTH = 3
SHELL_OPTION_WITH_ARGUMENT = {"-o", "+o", "-O", "+O"}
RUNNERS = {"env", "timeout", "nohup", "time", "command"}
SUBSTITUTION = re.compile(r"\$\(|`|<\(|>\(")


def shell_script(words: list[str]) -> str | None:
    """The string after `-c` (or `-lc` and the like) of an `sh`, `bash` or `zsh` call, else None."""
    if not words or os.path.basename(words[0]) not in SHELLS:
        return None
    index = 1
    while index < len(words):
        word = words[index]
        if word in SHELL_OPTION_WITH_ARGUMENT:
            index += 2
            continue
        if not word.startswith(("-", "+")):
            return None
        if SHELL_C_FLAG.fullmatch(word):
            return words[index + 1] if index + 1 < len(words) else None
        index += 1
    return None


def strip_runners(words: list[str]) -> tuple[list[str], list[str], bool]:
    """Peel `env`, `timeout`, `nohup`, `time` and `command` off the front of a simple command.

    Returns (words, chdir targets, subprocess). The gate patterns are anchored
    at the first word, so a runner in front of a gated command would hide it.
    The targets are the directories `env` runs the command in, read the way
    getopt reads them: `-C` alone or inside a short cluster (`-C dir`,
    `-iCdir`) and any unique prefix of `--chdir` (`--chd dir`, `--c=dir`).
    They are in order and belong to this command alone. `subprocess` is true
    when an `env`, `timeout` or `nohup` was peeled:
    a `cd` behind one of those runs as a program and moves nothing, whereas
    `command cd` and `time cd` move the shell. `command -v` is a lookup, not a
    run, and stays as it is, as does a runner that leaves nothing behind or
    carries `env -S`. Only the leading run of options is read, so a flag meant
    for the inner command never stops the strip.
    """
    chdirs: list[str] = []
    subprocess = False
    for _ in range(SHELL_DEPTH * 2):
        if not words:
            break
        runner = os.path.basename(words[0])
        if runner not in RUNNERS:
            break
        rest = words[1:]
        index = 0
        found: list[str] = []
        if runner == "env":
            give_up = False
            while index < len(rest):
                word = rest[index]
                if word.startswith("--"):
                    name, equals, value = word[2:].partition("=")
                    matches = [option for option in ("ignore-environment", "null", "unset", "chdir", "split-string", "block-signal", "default-signal", "ignore-signal", "list-signal-handling", "debug", "help", "version") if name and option.startswith(name)]
                    option = matches[0] if len(matches) == 1 else name
                    if option == "split-string":
                        give_up = True
                        break
                    if option in {"chdir", "unset"} and not equals:
                        value = rest[index + 1] if index + 1 < len(rest) else ""
                        index += 1
                    if option == "chdir":
                        found.append(value)
                    index += 1
                elif word.startswith("-") and word != "-":
                    for position, letter in enumerate(word[1:], start=1):
                        if letter == "S":
                            give_up = True
                            break
                        if letter in "CuP":
                            value = word[position + 1:]
                            if not value:
                                value = rest[index + 1] if index + 1 < len(rest) else ""
                                index += 1
                            if letter == "C":
                                found.append(value)
                            break
                    if give_up:
                        break
                    index += 1
                elif word == "-" or ASSIGNMENT.match(word):
                    index += 1
                else:
                    break
            if give_up:
                break
        elif runner == "timeout":
            while index < len(rest) and rest[index].startswith("-"):
                word = rest[index]
                index += 1
                if word.startswith("--"):
                    if len(word) > 2 and "=" not in word and ("--signal".startswith(word) or "--kill-after".startswith(word)):
                        index += 1
                else:
                    # a short cluster: the first `s` or `k` takes the rest of the word, or the next word
                    for position, letter in enumerate(word[1:], start=1):
                        if letter in "sk":
                            if position == len(word) - 1:
                                index += 1
                            break
            index += 1  # the duration
        elif runner == "command":
            lookup = False
            while index < len(rest) and rest[index] in {"-p", "-v", "-V", "--"}:
                if rest[index] in {"-v", "-V"}:
                    lookup = True
                    break
                index += 1
            if lookup:
                break
        elif runner in {"time", "nohup"}:
            while index < len(rest) and rest[index] in {"-p", "--"}:
                index += 1
        if index >= len(rest):
            break
        words = rest[index:]
        chdirs.extend(found)
        subprocess = subprocess or runner in {"env", "timeout", "nohup"}
    return words, chdirs, subprocess


def join_cd(previous: str | None, target: str) -> str:
    """The directory a `cd target` lands in, given the cd already in force on the line."""
    if previous is None or os.path.isabs(target) or target.startswith("~") or target == "-" or re.search(r"[$`]", target):
        return target
    if re.search(r"[$`]", previous) or previous == "-":
        return target
    return os.path.normpath(os.path.join(previous, target))


def opaque(command: str) -> bool:
    """True when the line hides commands from the matcher: a substitution, or quoting shlex cannot parse."""
    if SUBSTITUTION.search(command):
        return True
    try:
        list(shlex.shlex(HEREDOC.sub(" ", command), posix=True, punctuation_chars="();<>|&\n"))
    except ValueError:
        return True
    return False


def simple_commands(command: str, cd_target: str | None = None, depth: int = 0) -> list[tuple[list[str], str | None]]:
    """Each simple command of a shell line as (words, cd target seen before it or None).

    Heredoc bodies are lifted out first; redirects and leading VAR=value words
    are dropped. The cd target is the directory the earlier `cd`s on the line
    lead to, so a guard can tell where a command runs. The script of an
    `sh -c` / `bash -c` / `zsh -c` call is read as a line of its own, from the
    cd in force at the call, to a depth of three.
    """
    heredocs: list[str] = []

    def lift(match):
        heredocs.append(match.group(4))
        return " __HEREDOC_%d__ %s" % (len(heredocs) - 1, match.group(3))

    text = HEREDOC.sub(lift, command)
    lexer = shlex.shlex(text, posix=True, punctuation_chars="();<>|&\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    segments: list[list[str]] = []
    words: list[str] = []
    skip_target = False
    try:
        for token in lexer:
            if REDIRECT.match(token) or re.fullmatch(r"\d*[<>]+&?\d*", token):
                skip_target = True
            elif SEPARATORS.match(token):
                skip_target = False
                if words:
                    segments.append(words)
                words = []
            elif skip_target:
                skip_target = False
            else:
                words.append(token)
    except ValueError:
        # unbalanced quoting: fall back to whitespace words, one segment
        segments = [command.split()]
        words = []
    if words:
        segments.append(words)
    out = []
    for seg in segments:
        while seg and ASSIGNMENT.match(seg[0]):
            seg = seg[1:]
        seg, chdirs, subprocess = strip_runners(seg)
        while seg and ASSIGNMENT.match(seg[0]):
            seg = seg[1:]
        if not seg:
            continue
        if seg[0] == "cd":
            if not subprocess:
                cd_target = join_cd(cd_target, seg[1] if len(seg) > 1 else "~")
            continue
        # `env -C dir` moves this command (and any script it runs) and nothing after it
        run_target = cd_target
        for target in chdirs:
            run_target = join_cd(run_target, target)
        script = shell_script(seg) if depth < SHELL_DEPTH else None
        if script is not None:
            out.extend(simple_commands(script, run_target, depth + 1))
            continue
        out.append((seg, run_target))
    return out


def normalise(words: list[str]) -> list[str]:
    """`poetry run poe x` reads as `poe x`; `python -m poethepoet x` likewise."""
    if words[:2] == ["poetry", "run"]:
        words = words[2:]
    if words[:3] == ["python", "-m", "poethepoet"] or words[:3] == ["python3", "-m", "poethepoet"]:
        words = ["poe"] + words[3:]
    return words


def gate_matches(pattern: str, words: list[str]) -> bool:
    """A gate pattern is a glob over the command's words joined by spaces, anchored at the start."""
    joined = " ".join(words)
    return fnmatch.fnmatchcase(joined, pattern) or fnmatch.fnmatchcase(joined, pattern + " *")


def gated(config: dict, command: str) -> list[dict]:
    """Every (resource, simple command, cd target) a shell line touches, in order."""
    hits = []
    for words, cd_target in simple_commands(command):
        words = normalise(words)
        for name, spec in resources(config).items():
            gates = spec.get("gate") if isinstance(spec, dict) else None
            if not isinstance(gates, list):
                continue
            if any(isinstance(g, str) and gate_matches(g, words) for g in gates):
                hits.append({"resource": name, "command": " ".join(words), "cd": cd_target})
    return hits


def runs_in(cwd: str | None, cd_target: str | None) -> str | None:
    if cd_target is None:
        return cwd
    if cwd is None or re.search(r"[$`]", cd_target) or cd_target == "-":
        return None
    return os.path.normpath(os.path.join(cwd, os.path.expanduser(cd_target)))


# ---------------------------------------------------------------- probes


def sh(argv: list[str], timeout: int = 8, cwd: str | Path | None = None) -> tuple[int, str]:
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    except FileNotFoundError:
        return 127, f"{argv[0]} not installed"
    except subprocess.SubprocessError as error:
        return 124, str(error)
    return done.returncode, (done.stdout + done.stderr).strip()


# two psql probes plus the gh lookups share the mod's 20-second limit on `status --probe`
PSQL_PROBE_SECONDS = 3


def probe_resource(name: str, spec: dict) -> dict:
    """What the machine says about a resource right now; never trusts a message."""
    probe = spec.get("probe") if isinstance(spec, dict) else None
    result = {"resource": name, "busy": False, "checks": []}
    if not isinstance(probe, dict):
        result["checks"].append({"kind": "none", "detail": "no probe configured"})
        return result
    for port in probe.get("ports", []) or []:
        code, out = sh(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"])
        lines = [line for line in out.splitlines()[1:] if line.strip()] if code == 0 else []
        busy = bool(lines)
        result["checks"].append({"kind": "port", "port": port, "busy": busy, "detail": lines[0][:120] if lines else "free"})
        result["busy"] |= busy
    pattern = probe.get("pgrep")
    if isinstance(pattern, str) and pattern:
        code, out = sh(["pgrep", "-fl", pattern])
        procs = [line for line in out.splitlines() if line.strip() and "pgrep" not in line] if code == 0 else []
        result["checks"].append({"kind": "process", "pattern": pattern, "busy": bool(procs), "detail": procs[0][:120] if procs else "none"})
        result["busy"] |= bool(procs)
    activity = probe.get("pg_activity")
    if isinstance(activity, dict) and activity.get("dsn"):
        ignore = ",".join("'%s'" % u for u in activity.get("ignore_users", []) or []) or "''"
        idle = ",".join("'%s'" % u for u in activity.get("ignore_idle_users", []) or []) or "''"
        query = (
            "select count(*) from pg_stat_activity where datname=%s and backend_type='client backend' "
            "and usename not in (%s) and not (usename in (%s) and state='idle') and pid<>pg_backend_pid()"
            % ("'%s'" % activity.get("database", "postgres"), ignore, idle)
        )
        code, out = sh(["psql", activity["dsn"], "-Atc", query], timeout=PSQL_PROBE_SECONDS)
        if code == 0 and out.strip().isdigit():
            clients = int(out.strip())
            result["checks"].append({"kind": "pg_activity", "busy": clients > 0, "detail": f"{clients} client connection(s)"})
            result["busy"] |= clients > 0
        else:
            result["checks"].append({"kind": "pg_activity", "busy": False, "detail": f"unreachable: {out[:100] or 'no output'}"})
    migrations = probe.get("migrations")
    if isinstance(migrations, dict) and migrations.get("dsn"):
        table = migrations.get("table", "supabase_migrations.schema_migrations")
        code, out = sh(["psql", migrations["dsn"], "-Atc", f"select coalesce(max(version),'none') from {table}"], timeout=PSQL_PROBE_SECONDS)
        result["checks"].append({"kind": "migrations", "busy": False, "detail": f"latest applied: {out.strip()[:40]}" if code == 0 else f"unreachable: {out[:100]}"})
    return result


# ---------------------------------------------------------------- status


PR_CACHE_SECONDS = 60
PR_LOOKUP_SECONDS = 3


def pr_states(ledger: Ledger, numbers: set[int]) -> dict[int, str]:
    """GitHub's word on each PR (OPEN, MERGED, CLOSED), cached so a 15-second board does not ask every tick; a PR gh cannot read is left out, and once a lookup hangs the rest skip gh and answer from the cache alone."""
    cache_path = ledger.dir / "pr-cache.json"
    cache = read_json(cache_path, {}) or {}
    found: dict[int, str] = {}
    changed = False
    hanging = False
    for number in sorted(numbers):
        hit = cache.get(str(number)) or {}
        if hit.get("state") and now() - hit.get("at", 0) < PR_CACHE_SECONDS:
            found[number] = hit["state"]
            continue
        if hanging:
            continue  # gh is hanging, so the rest would too; the next tick retries
        code, out = sh(["gh", "pr", "view", str(number), "--json", "state", "-q", ".state"], timeout=PR_LOOKUP_SECONDS, cwd=ledger.main)
        if code == 124:
            hanging = True
            continue
        state = out.strip().upper()
        if code == 0 and state in ("OPEN", "MERGED", "CLOSED"):
            found[number] = state
            cache[str(number)] = {"state": state, "at": now()}
            changed = True
    if changed and ledger.dir.is_dir():
        write_json(cache_path, cache)
    return found


PR_FACT_FIELDS = "state,reviewDecision,reviewRequests,latestReviews,mergedAt,baseRefName"


def normalise_pr_facts(raw: dict) -> dict:
    """The few facts reconcile needs from `gh pr view --json`, in one flat shape: a requested reviewer is a login or a team slug, and the latest reviews are split by their verdict."""
    requested = []
    for item in raw.get("reviewRequests") or []:
        if isinstance(item, dict):
            who = item.get("login") or item.get("slug") or item.get("name")
            if who:
                requested.append(str(who))
    by_state: dict[str, list[str]] = {"CHANGES_REQUESTED": [], "APPROVED": []}
    for review in raw.get("latestReviews") or []:
        if not isinstance(review, dict):
            continue
        state = str(review.get("state") or "").upper()
        login = (review.get("author") or {}).get("login") if isinstance(review.get("author"), dict) else None
        if state in by_state and login:
            by_state[state].append(str(login))
    return {
        "state": str(raw.get("state") or "").upper(),
        "review_decision": str(raw.get("reviewDecision") or "").upper(),
        "requested": requested,
        "changes_requested_by": by_state["CHANGES_REQUESTED"],
        "approved_by": by_state["APPROVED"],
        "merged_at": raw.get("mergedAt"),
        "base": str(raw.get("baseRefName") or ""),
    }


def pr_facts(ledger: Ledger, numbers: set[int], fresh: set[int] | None = None) -> dict[int, dict]:
    """What GitHub says about each PR beyond its state: who it waits on. Cached and hang-guarded like pr_states, in its own file; a PR gh cannot read is left out. A number in `fresh` is asked of gh whatever the cache holds: a decision that removes something (retire) is not taken on a minute-old answer."""
    cache_path = ledger.dir / "pr-facts.json"
    cache = read_json(cache_path, {}) or {}
    found: dict[int, dict] = {}
    changed = False
    hanging = False
    for number in sorted(numbers):
        hit = cache.get(str(number)) or {}
        if number not in (fresh or set()) and isinstance(hit.get("facts"), dict) and now() - hit.get("at", 0) < PR_CACHE_SECONDS:
            found[number] = hit["facts"]
            continue
        if hanging:
            continue
        code, out = sh(["gh", "pr", "view", str(number), "--json", PR_FACT_FIELDS], timeout=PR_LOOKUP_SECONDS, cwd=ledger.main)
        if code == 124:
            hanging = True
            continue
        if code != 0:
            continue
        try:
            raw = json.loads(out)
        except ValueError:
            continue
        if not isinstance(raw, dict):
            continue
        facts = normalise_pr_facts(raw)
        if facts["state"] not in ("OPEN", "MERGED", "CLOSED"):
            continue
        found[number] = facts
        cache[str(number)] = {"facts": facts, "at": now()}
        changed = True
    if changed and ledger.dir.is_dir():
        write_json(cache_path, cache)
    return found


# how long a merged task's worktree may sit before reconcile nudges the coordinator to retire it
RETIRE_NUDGE_SECONDS = 60 * 60


def merged_at(facts: dict | None) -> float | None:
    """When GitHub says the PR merged, as a timestamp; None when it has not or the date is unreadable."""
    raw = (facts or {}).get("merged_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def waiting_on(facts: dict | None, mode: str | None = None) -> str:
    """Who a PR waits on, in the words the board may repeat; never a guess at the user. On a solo project nobody is waited for: the merge is the user's."""
    if not facts:
        return "unknown (gh did not answer)"
    if facts["state"] == "MERGED":
        return "merged"
    if facts["state"] == "CLOSED":
        return "closed"
    if facts["requested"]:
        return "waiting on " + ", ".join(facts["requested"])
    if facts["changes_requested_by"]:
        return "changes requested by " + ", ".join(facts["changes_requested_by"])
    if facts["review_decision"] == "APPROVED" or facts["approved_by"]:
        return "approved; the merge is the user's"
    if mode == "solo":
        return "solo project; the merge is the user's"
    return "no reviewer requested"


def roadmap_claim(main: Path, task: str, ref: str = "origin/main") -> bool | str | None:
    """What the roadmap at a ref says about a task's claim: True when the task carries `started` there, False when it is listed without one,
    "unlisted" when the task is not in that roadmap at all, None when the repo has no rich roadmap, the ref does not resolve or the file there is not a roadmap.
    The state is what counts, never which commit carried it: a claim reaches the trunk through roadmap:claim, a sync batch or a `done` batch alike, and a branch rebased past its own claim commit is in order once the trunk has the claim."""
    if not (main / ".claude" / "roadmaps.json").is_file():
        return None
    if run_git(main, "rev-parse", "--verify", "--quiet", ref) is None:
        return None
    raw = run_git(main, "show", f"{ref}:.claude/roadmaps.json")
    if raw is None:
        return None
    try:
        phases = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(phases, list):
        return None
    for phase in phases:
        for milestone in (phase.get("milestones") or []) if isinstance(phase, dict) else []:
            for row in (milestone.get("tasks") or []) if isinstance(milestone, dict) else []:
                if isinstance(row, dict) and row.get("id") == task:
                    return bool(row.get("started"))
    return "unlisted"


def reconcile(ledger: Ledger) -> dict:
    """The ledger against ground truth: the live registry, GitHub's word on each PR and the branches on origin (a merged PR's base, an open PR's branch). Reports drift; changes nothing."""
    run = ledger.require_run()
    live = registry()
    sessions = ledger.sessions()
    drift: list[dict] = []

    def note(kind: str, detail: str, task: str = "", session_id: str = "", pr: int | None = None) -> None:
        drift.append({"kind": kind, "task": task, "session_id": session_id, "pr": pr, "detail": detail})

    for sid, row in sessions.items():
        if sid not in live and row.get("state") != "done":
            note("gone", f"session {row.get('name') or sid[:8]} is no longer running but its row reads {row.get('state')}", row.get("task", ""), sid, row.get("pr"))
    joined_tasks = {row.get("task") for row in sessions.values()}
    for entry in run.get("crew", []):
        task = entry.get("task", "")
        if task and task not in joined_tasks:
            note("unjoined", f"crew task {task} is in the plan but no session has joined the ledger for it", task)

    numbers = {int(row["pr"]) for row in sessions.values() if row.get("pr")}
    facts = pr_facts(ledger, numbers)
    prs = []
    for sid, row in sorted(sessions.items(), key=lambda item: int(item[1].get("pr") or 0)):
        if not row.get("pr"):
            continue
        number = int(row["pr"])
        fact = facts.get(number)
        prs.append({"pr": number, "task": row.get("task", ""), "state": (fact or {}).get("state") or "UNKNOWN", "waiting_on": waiting_on(fact, (run.get("collaboration") or {}).get("mode"))})
        if fact and fact["state"] in ("MERGED", "CLOSED") and row.get("state") != "done":
            note(f"{fact['state'].lower()}-not-done", f"PR #{number} is {fact['state'].lower()} on GitHub but the row reads {row.get('state')}", row.get("task", ""), sid, number)
        # a finished worktree holds its dependencies for nothing; after a while the coordinator is nudged to retire it
        landed = merged_at(fact) if fact and fact["state"] == "MERGED" else None
        if landed is not None and row.get("state") == "done" and not row.get("retired") and sid not in live and now() - landed > RETIRE_NUDGE_SECONDS:
            worktree = row.get("worktree") or ""
            if worktree and Path(worktree).is_dir() and not same_path(worktree, ledger.main):
                note("unretired", f"done since {clock(landed)}, worktree still present; `mc.py retire {row.get('task') or sid[:8]}`", row.get("task", ""), sid, number)

    for need in run.get("needs", []):
        if need.get("status") == "done":
            continue
        row = sessions.get(need.get("session_id") or "", {})
        merged = row.get("pr") and (facts.get(int(row["pr"])) or {}).get("state") == "MERGED"
        if row.get("state") == "done" or merged:
            why = "its session is done" if row.get("state") == "done" else f"its PR #{row.get('pr')} is merged"
            note("need-open-after-done", f"need #{need.get('n')} ({need.get('why', '')[:60]}) is still open but {why}", need.get("task", ""), need.get("session_id", ""), row.get("pr"))

    # The claim is read from the roadmap itself, at the ref where it ought to be: a merged PR's own
    # base (the run's trunk, or the parent layer of a stack) and, for an open PR, the trunk first and
    # then the PR's branch, since a branch that dropped its claim commit once the trunk carried the
    # claim is in order. A task the roadmap does not list cannot carry a claim, so it is named once
    # and not counted as drift. The remote-tracking refs are only as fresh as the last fetch, and a
    # merge the user made on GitHub minutes ago is the common case, so fetch once first; a fetch that
    # fails leaves the stale refs to answer, as before.
    by_task = {row.get("task"): row for row in sessions.values() if row.get("task")}
    trunk = run.get("base", {}).get("branch") or "main"
    if (ledger.main / ".claude" / "roadmaps.json").is_file() and any(by_task.get(e.get("task"), {}).get("pr") for e in run.get("crew", [])):
        run_git(ledger.main, "fetch", "--quiet", "origin")
    for entry in run.get("crew", []):
        task = entry.get("task", "")
        row = by_task.get(task, {})
        if not task or not row.get("pr"):
            continue
        fact = facts.get(int(row["pr"]))
        if not fact:
            continue
        if fact["state"] == "MERGED":
            base = fact.get("base") or trunk
            claim = roadmap_claim(ledger.main, task, f"origin/{base}")
            if claim == "unlisted":
                note("unlisted", f"not in the roadmap on origin/{base}, no claim expected", task, row.get("session_id", ""), int(row["pr"]))
            elif claim is False:
                note("claim-missing", f"the roadmap on origin/{base} has no claim (`started`) for {task}, though PR #{row['pr']} is merged there", task, row.get("session_id", ""), int(row["pr"]))
        elif fact["state"] == "OPEN":
            branch = row.get("branch") or entry.get("branch") or ""
            on_trunk = roadmap_claim(ledger.main, task, f"origin/{trunk}")
            if on_trunk is True or not branch:
                continue
            on_branch = roadmap_claim(ledger.main, task, f"origin/{branch}")
            if on_branch is True:
                continue
            if on_trunk is None and on_branch is None:
                continue
            if on_trunk in ("unlisted", None) and on_branch in ("unlisted", None):
                note("unlisted", f"not in the roadmap on origin/{trunk} or origin/{branch}, no claim expected", task, row.get("session_id", ""), int(row["pr"]))
            else:
                note("claim-missing", f"neither the roadmap on origin/{trunk} nor the one on origin/{branch} has a claim (`started`) for {task}", task, row.get("session_id", ""), int(row["pr"]))

    return {"run": run.get("name"), "drift": drift, "prs": prs, "at": now()}


def print_reconcile(result: dict) -> None:
    print("## Drift")
    print()
    if not result["drift"]:
        print("nothing to reconcile")
    for item in result["drift"]:
        print(f"- {item.get('task') or item.get('session_id', '')[:8] or 'run'}: {item['detail']}")
    print()
    print("## PRs")
    print()
    if not result["prs"]:
        print("no PRs on the board")
    for pr in result["prs"]:
        state = pr["state"].lower()
        tail = "" if pr["waiting_on"] == state else f", {pr['waiting_on']}"
        print(f"- #{pr['pr']} ({pr['task']}): {state}{tail}")


def status_of(ledger: Ledger, config: dict | None, with_probes: bool) -> dict:
    run = ledger.run()
    live = registry()
    sessions = []
    for sid, row in ledger.sessions().items():
        reg = live.get(sid, {})
        sessions.append({
            **row,
            "live": bool(reg),
            "name": reg.get("name") or row.get("name") or "",
            "socket": reg.get("messagingSocketPath") or row.get("socket"),
            "live_status": reg.get("status"),
            "live_cwd": reg.get("cwd"),
        })
    slots = ledger.slots()
    for slot in slots.values():
        holder = ledger.sessions().get(slot.get("holder", ""), {})
        slot["holder_task"] = holder.get("task", "")
        slot["holder_name"] = live.get(slot.get("holder", ""), {}).get("name") or holder.get("name", "")
        slot["overdue"] = bool(slot.get("until")) and now() > slot["until"]
    requests = ledger.requests()
    for req in requests:
        who = ledger.sessions().get(req.get("session_id", ""), {})
        req["task"] = who.get("task", "")
        req["name"] = live.get(req.get("session_id", ""), {}).get("name") or who.get("name", "")
    out = {
        "slug": ledger.slug,
        "ledger_dir": str(ledger.dir),
        "main_checkout": str(ledger.main),
        "config": bool(config),
        "run": run,
        "sessions": sessions,
        "slots": list(slots.values()),
        "requests": requests,
        "needs": [n for n in (run or {}).get("needs", []) if n.get("status") != "done"] if run else [],
        "assumptions": (run or {}).get("assumptions", []) if run else [],
        "at": now(),
    }
    if with_probes and run:
        states = pr_states(ledger, {int(s["pr"]) for s in sessions if s.get("pr")})
        for s in sessions:
            if s.get("pr") and int(s["pr"]) in states:
                s["pr_state"] = states[int(s["pr"])]
    if with_probes and config:
        out["probes"] = [probe_resource(name, spec) for name, spec in resources(config).items() if not (isinstance(spec, dict) and spec.get("human_gate"))]
    return out


def print_status(status: dict) -> None:
    run = status["run"]
    if not run:
        print(f"No active run for {status['main_checkout']}.")
        return
    coord = run.get("coordinator", {})
    print(f"# Run {run['name']} · since {clock(run.get('started_at'))} · base {run.get('base', {}).get('branch', '?')}@{str(run.get('base', {}).get('commit', '?'))[:8]} · coordinator {coord.get('name') or coord.get('session_id', '?')} · PR approval: {run.get('pr_approval', 'user')}")
    print()
    print("| Session | Task | Branch | State | Summary | PR |")
    print("|---|---|---|---|---|---|")
    for s in status["sessions"]:
        live = "" if s.get("live") else " (gone)"
        print(f"| {s.get('name') or s['session_id'][:8]}{live} | {s.get('task', '')} | {s.get('branch', '')} | {s.get('state', '')} | {s.get('summary', '')} | {s.get('pr') or ''}{' ' + s['pr_state'].lower() if s.get('pr_state') and s['pr_state'] != 'OPEN' else ''} |")
    print()
    print("| Slot | Holder | Since | Until | What |")
    print("|---|---|---|---|---|")
    for slot in status["slots"]:
        flag = " overdue" if slot.get("overdue") else ""
        print(f"| {slot['resource']} | {slot.get('holder_task') or slot.get('holder_name') or slot['holder'][:8]} | {clock(slot.get('granted_at'))} | {clock(slot.get('until'))}{flag} | {slot.get('what', '')} |")
    if status["requests"]:
        print()
        print("| Request | From | Minutes | What |")
        print("|---|---|---|---|")
        for req in status["requests"]:
            print(f"| {req['resource']} | {req.get('task') or req.get('name') or req['session_id'][:8]} | {req.get('minutes', '?')} | {req.get('what', '')} |")
    if status["needs"]:
        print()
        print("## Needs Jason")
        print()
        for n in status["needs"]:
            where = f" (in {n['cwd']})" if n.get("cwd") else ""
            print(f"{n['n']}. [{n.get('task') or n.get('session_id', '')[:8]}] {n['why']}{where}")
            if n.get("command"):
                print(f"   `{n['command']}`")
    for probe in status.get("probes", []) or []:
        checks = "; ".join(f"{c['kind']}: {c.get('detail', '')}" for c in probe["checks"])
        print(f"probe {probe['resource']}: {'BUSY' if probe['busy'] else 'free'} ({checks})")


# ---------------------------------------------------------------- collaboration

# A project is solo or collaborative; the answer is stated in the config (or the gitignored local
# config beside it) or inferred from the last 90 days of history and the reviews on merged PRs.
# The run record carries one answer so every brief, skill and watcher reads the same one.
LOCAL_CONFIG_REL = ".claude/mission-control.local.json"
AUTHOR_WINDOW_DAYS = 90
REVIEW_SAMPLE = 30
BOT_MARKERS = ("[bot]", "dependabot", "renovate", "github-actions", "actions@github.com", "noreply@github.com", "copilot")
DAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DEFAULT_TEAM_HOURS = {"start": "09:00", "end": "18:00", "days": [0, 1, 2, 3, 4]}


def is_bot(name: str, email: str = "") -> bool:
    text = f"{name} {email}".lower()
    return any(marker in text for marker in BOT_MARKERS)


def git_authors(main: Path, days: int = AUTHOR_WINDOW_DAYS) -> list[dict]:
    """Distinct human authors on the checked-out history in the window, by email, most commits first."""
    out = run_git(main, "log", f"--since={days}.days", "--format=%an\t%ae")
    counts: dict[str, dict] = {}
    for line in (out or "").splitlines():
        name, _, email = line.partition("\t")
        if not name or is_bot(name, email):
            continue
        key = email.strip().lower() or name.strip().lower()
        row = counts.setdefault(key, {"name": name.strip(), "email": email.strip(), "commits": 0})
        row["commits"] += 1
    return sorted(counts.values(), key=lambda r: -r["commits"])


def gh_merged_reviews(main: Path) -> tuple[list[dict], bool]:
    """The last merged PRs with who reviewed each, other than its author; (rows, whether gh answered)."""
    code, out = sh(["gh", "pr", "list", "--state", "merged", "--limit", str(REVIEW_SAMPLE), "--json", "number,author,reviews"], timeout=PR_LOOKUP_SECONDS, cwd=main)
    if code != 0:
        return [], False
    try:
        raw = json.loads(out)
    except ValueError:
        return [], False
    rows = []
    for pr in raw if isinstance(raw, list) else []:
        if not isinstance(pr, dict):
            continue
        author = str((pr.get("author") or {}).get("login") or "")
        others = []
        for review in pr.get("reviews") or []:
            if not isinstance(review, dict):
                continue
            login = str((review.get("author") or {}).get("login") or "")
            if not login or login == author or is_bot(login):
                continue
            others.append({"login": login, "state": str(review.get("state") or ""), "at": review.get("submittedAt")})
        rows.append({"number": pr.get("number"), "author": author, "others": others})
    return rows, True


def parse_days(value) -> list[int]:
    """Weekdays as Monday=0 ints, from ints, names (`mon`) or a range (`mon-fri`)."""
    if isinstance(value, str):
        value = [v.strip() for v in value.split(",")]
    days: set[int] = set()
    for item in value or []:
        if isinstance(item, int) and 0 <= item <= 6:
            days.add(item)
        elif isinstance(item, str):
            text = item.strip().lower()[:3]
            if "-" in item:
                first, _, last = item.lower().partition("-")
                a, b = DAY_NAMES.index(first.strip()[:3]), DAY_NAMES.index(last.strip()[:3])
                days.update(range(a, b + 1) if a <= b else list(range(a, 7)) + list(range(0, b + 1)))
            elif text in DAY_NAMES:
                days.add(DAY_NAMES.index(text))
    return sorted(days)


def normalise_hours(stated) -> dict | None:
    """A stated team-hours block as {start, end, days}; None when it is not one."""
    if not isinstance(stated, dict):
        return None
    start, end = str(stated.get("start") or "09:00"), str(stated.get("end") or "18:00")
    if not re.fullmatch(r"\d{2}:\d{2}", start) or not re.fullmatch(r"\d{2}:\d{2}", end):
        return None
    days = parse_days(stated.get("days")) if stated.get("days") is not None else DEFAULT_TEAM_HOURS["days"]
    return {"start": start, "end": end, "days": days or DEFAULT_TEAM_HOURS["days"]}


def hours_from_reviews(times: list[float]) -> dict | None:
    """Team hours inferred from when other people reviewed, in this machine's local time, padded an hour each side; None under three samples."""
    stamps = [time.localtime(t) for t in times if t]
    if len(stamps) < 3:
        return None
    first = min(lt.tm_hour for lt in stamps)
    last = max(lt.tm_hour for lt in stamps)
    days = sorted({lt.tm_wday for lt in stamps}) or DEFAULT_TEAM_HOURS["days"]
    return {"start": f"{max(0, first - 1):02d}:00", "end": f"{min(23, last + 2):02d}:00", "days": days, "from_reviews": len(stamps)}


def iso_ts(raw) -> float | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def classify(main: Path, config: dict | None) -> dict:
    """Solo or collaborative, with the evidence: the stated answer wins when there is one and the history is read to confirm it."""
    local = read_json(main / LOCAL_CONFIG_REL, {}) or {}
    stated, source = None, "inferred"
    if isinstance(local, dict) and isinstance(local.get("collaboration"), dict):
        stated, source = local["collaboration"], "local config"
    elif isinstance((config or {}).get("collaboration"), dict):
        stated, source = (config or {})["collaboration"], "config"
    authors = git_authors(main)
    prs, answered = gh_merged_reviews(main)
    reviewed = [p for p in prs if p["others"]]
    review_times = [iso_ts(o["at"]) for p in reviewed for o in p["others"]]
    inferred = "collaborative" if len(authors) >= 2 or reviewed else "solo"
    evidence = [
        f"{len(authors)} human author{'s' if len(authors) != 1 else ''} in the last {AUTHOR_WINDOW_DAYS} days" + (": " + ", ".join(a["name"] for a in authors[:6]) if authors else ""),
        (f"{len(reviewed)} of the last {len(prs)} merged PRs reviewed by someone other than their author" if answered else "gh could not list merged PRs, so reviews are unknown"),
    ]
    mode = inferred
    stated_mode = str((stated or {}).get("mode") or "").lower()
    if stated_mode in ("solo", "collaborative"):
        mode = stated_mode
        evidence.append(f"{source} says {mode}" + ("" if mode == inferred else f"; the history alone reads {inferred}"))
    else:
        source = "inferred"
    hours = normalise_hours((stated or {}).get("hours")) if stated else None
    if hours is None and mode == "collaborative":
        hours = hours_from_reviews([t for t in review_times if t]) or dict(DEFAULT_TEAM_HOURS)
        hours_word = "from the timestamps of the reviews by others" if hours.get("from_reviews") else "defaulted to 09:00 to 18:00, Monday to Friday"
        evidence.append(f"team hours {hours_word}; set collaboration.hours in the config to state them")
    if mode == "solo":
        hours = None
    return {
        "mode": mode, "source": source, "inferred": inferred, "authors": [a["name"] for a in authors], "reviewed_by_others": len(reviewed),
        "prs_sampled": len(prs), "gh_answered": answered, "hours": hours, "timezone": time.strftime("%Z"), "evidence": evidence, "at": now(),
    }


def minutes_of(hhmm: str) -> int:
    hours, _, minutes = hhmm.partition(":")
    return int(hours) * 60 + int(minutes)


def in_window(hours: dict | None, at: float) -> bool:
    """Whether a reviewer could plausibly answer at this moment: no hours means always."""
    if not hours:
        return True
    lt = time.localtime(at)
    if lt.tm_wday not in hours.get("days", DEFAULT_TEAM_HOURS["days"]):
        return False
    return minutes_of(hours["start"]) <= lt.tm_hour * 60 + lt.tm_min < minutes_of(hours["end"])


def window_opens(hours: dict | None, at: float) -> float:
    """The next moment the window is open, this one included."""
    if in_window(hours, at):
        return at
    probe = at - (at % 60)
    for _ in range(8 * 24 * 60):
        probe += 60
        if in_window(hours, probe):
            return probe
    return at


def print_classification(result: dict) -> None:
    hours = result.get("hours")
    window = f"{hours['start']} to {hours['end']} on {', '.join(DAY_NAMES[d] for d in hours['days'])} ({result.get('timezone')})" if hours else "none: nobody to wait for"
    print(f"{result['mode']} ({result['source']}); team hours: {window}")
    for line in result.get("evidence", []):
        print(f"- {line}")


# ---------------------------------------------------------------- PR watching

WATCH_FIELDS = "state,reviewDecision,reviews,comments,statusCheckRollup,mergedAt,url,title"
WATCH_FAILURES_TOLERATED = 3


def check_word(entry: dict) -> str:
    """One word for a check run or status context, as pr-land reads them."""
    if entry.get("status") and str(entry.get("status")).upper() != "COMPLETED":
        return str(entry["status"]).lower()
    return str(entry.get("conclusion") or entry.get("state") or "unknown").lower()


def pr_snapshot(main: Path, number: int) -> dict | None:
    """What the watcher compares between polls: state, decision, the reviews by login, comment counts and each check's word. None when gh did not answer."""
    code, out = sh(["gh", "pr", "view", str(number), "--json", WATCH_FIELDS], timeout=PR_LOOKUP_SECONDS, cwd=main)
    if code != 0:
        return None
    try:
        raw = json.loads(out)
    except ValueError:
        return None
    if not isinstance(raw, dict):
        return None
    reviews = []
    for review in raw.get("reviews") or []:
        if isinstance(review, dict):
            reviews.append({"login": str((review.get("author") or {}).get("login") or "?"), "state": str(review.get("state") or ""), "at": review.get("submittedAt")})
    checks = {}
    for entry in raw.get("statusCheckRollup") or []:
        if isinstance(entry, dict):
            checks[str(entry.get("name") or entry.get("context") or entry.get("workflowName") or "check")] = check_word(entry)
    code, out = sh(["gh", "api", f"repos/{{owner}}/{{repo}}/pulls/{number}/comments", "--jq", "length"], timeout=PR_LOOKUP_SECONDS, cwd=main)
    review_comments = int(out.strip()) if code == 0 and out.strip().isdigit() else None
    return {
        "state": str(raw.get("state") or "").upper(),
        "decision": str(raw.get("reviewDecision") or ""),
        "reviews": reviews,
        "comments": len(raw.get("comments") or []),
        "review_comments": review_comments,
        "checks": checks,
        "merged_at": raw.get("mergedAt"),
        "url": str(raw.get("url") or ""),
        "title": str(raw.get("title") or ""),
        "at": now(),
    }


def snapshot_changes(before: dict, after: dict) -> list[str]:
    """What changed between two snapshots, one line each, in the words the crew session will repeat."""
    lines = []
    if before.get("state") != after.get("state"):
        lines.append(f"state {before.get('state') or '?'} -> {after.get('state')}")
    if before.get("decision") != after.get("decision"):
        lines.append(f"review decision {before.get('decision') or 'none'} -> {after.get('decision') or 'none'}")
    seen = {(r["login"], r["state"], r.get("at")) for r in before.get("reviews", [])}
    for review in after.get("reviews", []):
        if (review["login"], review["state"], review.get("at")) not in seen:
            lines.append(f"review by {review['login']}: {review['state'].lower().replace('_', ' ')}")
    for key, label in (("review_comments", "review comment"), ("comments", "comment")):
        was, is_ = before.get(key), after.get(key)
        if isinstance(was, int) and isinstance(is_, int) and is_ > was:
            lines.append(f"{is_ - was} new {label}{'s' if is_ - was != 1 else ''}")
    for name, word in after.get("checks", {}).items():
        old = before.get("checks", {}).get(name)
        if old != word:
            lines.append(f"check {name}: {old or 'new'} -> {word}")
    return lines


def terminal(snapshot: dict | None) -> bool:
    return bool(snapshot) and snapshot.get("state") in ("MERGED", "CLOSED")


def summarise_snapshot(snapshot: dict) -> str:
    checks = snapshot.get("checks") or {}
    words = sorted(set(checks.values()))
    check_text = f"{len(checks)} check{'s' if len(checks) != 1 else ''}: {', '.join(words)}" if checks else "no checks"
    reviews = ", ".join(f"{r['login']} {r['state'].lower().replace('_', ' ')}" for r in snapshot.get("reviews", [])) or "no reviews"
    return f"{snapshot.get('state', '?').lower()}, decision {snapshot.get('decision') or 'none'}, {reviews}, {snapshot.get('comments', 0)} comments, {snapshot.get('review_comments') if snapshot.get('review_comments') is not None else '?'} review comments, {check_text}"


# ---------------------------------------------------------------- commands


def cmd_detect(args) -> int:
    found = find_config(args.cwd)
    if not found:
        print(f"✗ no {CONFIG_REL} above {args.cwd}")
        return 2
    print(found[0])
    return 0


def cmd_init(args) -> int:
    root = toplevel(args.cwd) or Path(args.cwd)
    target = root / CONFIG_REL
    if target.exists() and not args.force:
        raise Refusal(f"{target} exists; pass --force to overwrite it")
    example = Path(__file__).resolve().parent.parent / "references" / "mission-control.example.json"
    data = read_json(example, {})
    data["project"] = root.name
    data["resources"] = {}
    data["commands"] = {}
    data["conventions"] = ["CLAUDE.md"]
    data["facts"] = []
    data["human_gates"] = ["hosted reads", "hosted credentials", "hosted writes", "merges", "anything irreversible"]
    data.pop("migrations", None)
    write_json(target, data)
    print(target)
    return 0


def cmd_start(args) -> int:
    ledger = ledger_for(args.cwd)
    if ledger.run():
        raise Refusal(f"a run is already active for {ledger.main} ({ledger.run()['name']}); end it first")
    session_id = caller_session(args.session)
    if not session_id:
        raise Refusal("the coordinator session is unknown: run this from a Claude Code session, or pass --session")
    who = identity(session_id)
    base_branch = args.base or (run_git(ledger.main, "symbolic-ref", "--short", "refs/remotes/origin/HEAD") or "origin/main").split("/", 1)[-1]
    run_git(ledger.main, "fetch", "origin", base_branch)
    commit = run_git(ledger.main, "rev-parse", f"origin/{base_branch}") or run_git(ledger.main, "rev-parse", base_branch) or ""
    # A PR cannot target a branch origin has never seen; the first run found out at the push.
    has_origin = run_git(ledger.main, "remote", "get-url", "origin") is not None
    on_origin = None if not has_origin else bool(run_git(ledger.main, "ls-remote", "--exit-code", "--heads", "origin", base_branch))
    if ledger.dir.exists():
        archive = ledger.dir.parent / "runs" / f"{time.strftime('%Y%m%d-%H%M')}-{ledger.slug}"
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(ledger.dir), str(archive))
    found = find_config(args.cwd)
    collaboration = classify(ledger.main, found[1] if found else None)
    if args.collaboration:
        collaboration["mode"] = args.collaboration
        collaboration["source"] = "flag"
        collaboration["evidence"].append(f"--collaboration {args.collaboration} on start" + ("" if args.collaboration == collaboration["inferred"] else f"; the history alone reads {collaboration['inferred']}"))
        if args.collaboration == "solo":
            collaboration["hours"] = None
        elif not collaboration.get("hours"):
            collaboration["hours"] = dict(DEFAULT_TEAM_HOURS)
    run = {
        "name": args.name,
        "repo_root": str(ledger.main),
        "slug": ledger.slug,
        "started_at": now(),
        "coordinator": who,
        "base": {"branch": base_branch, "commit": commit, "on_origin": on_origin},
        "pr_approval": args.pr_approval,
        "collaboration": collaboration,
        "crew": [],
        "assumptions": [],
        "needs": [],
        "ended_at": None,
    }
    warning = ""
    if on_origin is False:
        push = f"git -C {ledger.main} push -u origin {base_branch}"
        run["needs"].append({"id": uuid.uuid4().hex[:8], "n": 1, "session_id": session_id, "task": "kick-off",
                             "why": f"{base_branch} is not on origin, so no PR can target it until it is pushed (publishes its commits)",
                             "command": push, "cwd": str(ledger.main), "status": "open", "at": now()})
        warning = f"\nWARNING: {base_branch} is not on origin. PRs cannot target it until the user pushes it; it is need #1 on the board: `{push}`."
    ledger.save_run(run)
    (ledger.dir / "briefs").mkdir(parents=True, exist_ok=True)
    ledger.log("start", name=args.name, coordinator=who, base=run["base"])
    print(json.dumps(run, indent=2) if args.json else f"Run {args.name} started; coordinator {who.get('name') or session_id}; base {base_branch}@{commit[:8]}; {collaboration['mode']} project ({collaboration['source']}); ledger {ledger.dir}{warning}")
    return 0


def cmd_end(args) -> int:
    ledger = ledger_for(args.cwd)
    run = ledger.require_run()
    authorise(run, caller_session(args.session), args.by_user, "end the run")
    if ledger.slots() and not args.force:
        raise Refusal("slots are still held: " + ", ".join(f"{r} by {s.get('holder', '')[:8]}" for r, s in ledger.slots().items()) + "; revoke them or pass --force")
    run["ended_at"] = now()
    ledger.save_run(run)
    ledger.log("end", name=run["name"])
    archive = ledger.dir.parent / "runs" / f"{time.strftime('%Y%m%d-%H%M')}-{re.sub(r'[^A-Za-z0-9._-]+', '-', run['name'])}"
    archive.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(ledger.dir), str(archive))
    print(f"Run {run['name']} ended; ledger archived to {archive}")
    return 0


def worktree_bytes(path: Path) -> int | None:
    """What a worktree holds on disk, dependencies included; None when du cannot say."""
    code, out = sh(["du", "-sk", str(path)], timeout=60)
    if code != 0:
        return None
    try:
        return int(out.split()[0]) * 1024
    except (IndexError, ValueError):
        return None


def human_bytes(count: int | None) -> str:
    if count is None:
        return "size unknown"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(count)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.0f} {unit}" if unit in ("B", "KB") else f"{size:.1f} {unit}"
        size /= 1024
    return f"{count} B"


def worktree_processes(path: Path) -> list[dict] | None:
    """Every process whose working directory is in the worktree (a dev server left running, a watcher, a shell), by lsof; None when lsof cannot answer. Own process and parent excluded."""
    code, out = sh(["lsof", "-d", "cwd", "-Fpcn"], timeout=20)
    if code not in (0, 1):  # lsof exits 1 when some process could not be read, with the rest still listed
        return None
    mine = {os.getpid(), os.getppid()}
    found: list[dict] = []
    pid, cmd = 0, ""
    for line in out.splitlines():
        if line.startswith("p"):
            pid, cmd = int(line[1:] or 0), ""
        elif line.startswith("c"):
            cmd = line[1:]
        elif line.startswith("n") and pid not in mine and inside(line[1:], str(path)):
            found.append({"pid": pid, "command": cmd})
    return found


def cmd_retire(args) -> int:
    ledger = ledger_for(args.cwd)
    with ledger.locked():
        return retire_locked(args, ledger)


def retire_locked(args, ledger: Ledger) -> int:
    """Reclaim a finished crew session's worktree while the run goes on: only once the session has closed, its row is done, its PR has landed, the tree is clean, nothing runs in it, no slot is held and no open PR is based on its branch. Removes the worktree, prunes, deletes the branch with `-d` only, and records the retirement on the row."""
    run = ledger.require_run()
    caller = caller_session(args.session)
    by = authorise(run, caller, args.by_user, "retire a crew worktree")
    sessions = ledger.sessions()
    session_id = resolve_session(args.ref, sessions)
    row = sessions[session_id]
    label = row.get("task") or row.get("branch") or session_id[:8]
    if row.get("retired"):
        raise Refusal(f"{label} was retired at {clock(row['retired'].get('at'))}")
    if session_id in registry():
        raise Refusal(f"{label}'s session is still live; it closes first, then retire")
    if row.get("state") != "done":
        raise Refusal(f"{label}'s row reads {row.get('state')}, not done")
    if not row.get("pr"):
        raise Refusal(f"{label} has no PR on its row; retire reclaims a worktree whose PR has landed")
    numbers = {int(r["pr"]) for r in sessions.values() if r.get("pr")}
    # this PR's state is asked of gh now, never read from the cache: a merge made a moment ago is the common case
    facts = pr_facts(ledger, numbers, fresh={int(row["pr"])})
    fact = facts.get(int(row["pr"]))
    if not fact:
        raise Refusal(f"gh could not say what state PR #{row['pr']} is in; retire needs it merged or closed")
    if fact["state"] not in ("MERGED", "CLOSED"):
        raise Refusal(f"PR #{row['pr']} is {fact['state'].lower()} on GitHub; retire needs it merged or closed")
    branch = row.get("branch") or ""
    stacked = [f"#{n} ({(next((r.get('task') for r in sessions.values() if str(r.get('pr')) == str(n)), '') or '?')})" for n, f in facts.items() if f["state"] == "OPEN" and branch and f.get("base") == branch]
    if stacked:
        raise Refusal(f"open PR {', '.join(stacked)} is based on {branch}; the branch stays until it lands")
    held = [r for r, s in ledger.slots().items() if s.get("holder") == session_id]
    if held:
        raise Refusal(f"{label} still holds {', '.join(held)}; release first")
    worktree = Path(row.get("worktree") or "")
    if not row.get("worktree") or not worktree.is_dir():
        raise Refusal(f"{label}'s worktree {worktree or '(none recorded)'} is not on disk; nothing to retire" + ("" if not branch else f" (the branch {branch} may still want `git branch -d`)"))
    if same_path(worktree, ledger.main):
        raise Refusal(f"{label}'s worktree is the main checkout; never retired")
    dirty = run_git(worktree, "status", "--porcelain")
    if dirty is None:
        raise Refusal(f"{worktree} is not a git worktree git can read")
    if dirty:
        raise Refusal(f"{worktree} is dirty ({len(dirty.splitlines())} paths); commit, stash or discard first, then retire")
    running = worktree_processes(worktree)
    size = worktree_bytes(worktree)
    if running:
        kills = " ".join(str(p["pid"]) for p in running)
        listed = ", ".join(f"{p['pid']} ({p['command'] or '?'})" for p in running)
        if not args.dry_run:
            needs = run.setdefault("needs", [])
            n = 1 + max([x.get("n", 0) for x in needs] or [0])
            need = {"id": uuid.uuid4().hex[:8], "n": n, "session_id": session_id, "task": row.get("task", ""),
                    "why": f"processes still run in {label}'s worktree ({listed}); retire removes it once they are gone",
                    "command": f"kill {kills}", "cwd": str(ledger.main), "status": "open", "at": now()}
            needs.append(need)
            ledger.save_run(run)
            ledger.log("need", **need)
        raise Refusal(f"processes still run in {worktree}: {listed}; `kill {kills}` first" + ("" if args.dry_run else f" (need #{need['n']})"))
    if running is None:
        print(f"note: lsof could not list processes, so nothing is known about what runs in {worktree}")
    merged = f"{fact['state'].lower()} via #{row['pr']}" + (f" into {fact['base']}" if fact.get("base") else "")
    if args.dry_run:
        print(f"retire {label} (dry run): would remove worktree {worktree} ({human_bytes(size)}), `git worktree prune`, then `git branch -d {branch}` ({merged})")
        return 0
    removed = run_git(ledger.main, "worktree", "remove", str(worktree))
    if removed is None:
        raise Refusal(f"git refused to remove {worktree}; it is left as it was")
    run_git(ledger.main, "worktree", "prune")
    branch_deleted = bool(branch) and run_git(ledger.main, "branch", "-d", branch) is not None
    row["retired"] = {"at": now(), "by": by, "worktree": str(worktree), "bytes_freed": size, "branch_deleted": branch_deleted}
    row["updated_at"] = now()
    ledger.save_session(row)
    ledger.log("retire", session_id=session_id, task=row.get("task", ""), branch=branch, worktree=str(worktree), bytes_freed=size, branch_deleted=branch_deleted, by=by)
    branch_word = f"branch {branch} deleted" if branch_deleted else (f"branch {branch} kept: `git branch -d` refused it (not fully merged here; `git branch -D` is the user's call)" if branch else "no branch recorded")
    print(json.dumps(row) if args.json else f"retired {label}: worktree {worktree} removed ({human_bytes(size)} freed), {branch_word}; {merged}")
    return 0


def cmd_status(args) -> int:
    ledger = ledger_for(args.cwd)
    found = find_config(args.cwd)
    status = status_of(ledger, found[1] if found else None, args.probe)
    status["config_path"] = str(found[0]) if found else None
    if args.json:
        print(json.dumps(status))
    else:
        print_status(status)
    return 0


def cmd_probe(args) -> int:
    found = find_config(args.cwd)
    if not found:
        raise Refusal(f"no {CONFIG_REL} above {args.cwd}")
    names = [args.resource] if args.resource else list(resources(found[1]))
    out = []
    for name in names:
        spec = resources(found[1]).get(name)
        if spec is None:
            raise Refusal(f"no resource named {name}; configured: {', '.join(resources(found[1]))}")
        out.append(probe_resource(name, spec))
    if args.json:
        print(json.dumps(out))
    else:
        for probe in out:
            print(f"{probe['resource']}: {'BUSY' if probe['busy'] else 'free'}")
            for check in probe["checks"]:
                print(f"  {check['kind']}: {check.get('detail', '')}")
    return 0


def cmd_reconcile(args) -> int:
    ledger = ledger_for(args.cwd)
    result = reconcile(ledger)
    if args.json:
        print(json.dumps(result))
    else:
        print_reconcile(result)
    return 0


def cmd_classify(args) -> int:
    """Solo or collaborative, from the config or the history; the run record's copy when a run is active and --fresh is not passed."""
    ledger = ledger_for(args.cwd)
    found = find_config(args.cwd)
    run = ledger.run()
    result = (run or {}).get("collaboration") if run and not args.fresh else None
    if not isinstance(result, dict):
        result = classify(ledger.main, found[1] if found else None)
    if args.json:
        print(json.dumps(result))
    else:
        print_classification(result)
    return 0


def cmd_watch(args) -> int:
    """Watch one PR until something changes, then say what and exit: the crew session runs this in the background and is woken by the exit.
    Outside the team's hours on a collaborative project a change that is not a merge or close is held until the window opens; on a solo project there is no window."""
    ledger = ledger_for(args.cwd)
    run = ledger.run()
    found = find_config(args.cwd)
    collab = (run or {}).get("collaboration") if run else None
    if not isinstance(collab, dict):
        collab = classify(ledger.main, found[1] if found else None)
    hours = collab.get("hours") if collab.get("mode") == "collaborative" else None
    session_id = caller_session(None)
    row = ledger.sessions().get(session_id or "", {}) if run else {}
    number = args.pr or (int(row["pr"]) if row.get("pr") else None)
    if not number:
        raise Refusal("which PR? pass the number, or report it first with mc_report")

    def record(status: str, seen: dict | None, changes: list[str]) -> None:
        if not run or not row:
            return
        with ledger.locked():
            fresh = ledger.sessions().get(row["session_id"])
            if not fresh:
                return
            fresh["watch"] = {"pr": number, "since": (fresh.get("watch") or {}).get("since") or now(), "status": status, "checked_at": now(), "seen": seen, "last_change": changes or (fresh.get("watch") or {}).get("last_change") or []}
            ledger.save_session(fresh)
        ledger.log("watch", session_id=row["session_id"], pr=number, status=status, changes=changes)

    previous = (row.get("watch") or {}) if row else {}
    seen = previous.get("seen") if previous.get("pr") == number and isinstance(previous.get("seen"), dict) else None
    if seen is None:
        seen = pr_snapshot(ledger.main, number)
        if seen is None:
            raise Refusal(f"gh could not read PR #{number}; nothing to watch")
        record("watching", seen, [])
        if args.once:
            print(f"#{number}: {summarise_snapshot(seen)}")
            return 0
        if terminal(seen):
            print(f"#{number} is already {seen['state'].lower()}; nothing to watch")
            record("ended", seen, [])
            return 0
        if collab.get("mode") == "solo" and not seen.get("checks"):
            print(f"#{number}: solo project and no checks, so nothing will change by itself; the merge is the user's. Not watching.")
            record("ended", seen, [])
            return 0
    elif args.once:
        print(f"#{number}: {summarise_snapshot(seen)} (as last seen)")
        return 0
    interval = max(1.0, float(args.interval))
    deadline = now() + float(args.max_minutes) * 60
    failures = 0
    held: list[str] = []
    while True:
        time.sleep(interval)
        current = pr_snapshot(ledger.main, number)
        if current is None:
            failures += 1
            if failures >= WATCH_FAILURES_TOLERATED:
                print(f"#{number}: gh did not answer {failures} polls running; the watch stops here, re-arm when gh is back")
                record("stalled", seen, [])
                return 2
            continue
        failures = 0
        changes = snapshot_changes(seen, current)
        if changes:
            if terminal(current) or in_window(hours, now()):
                record("changed", current, changes)
                print(f"#{number} changed ({'; '.join(changes)}). Now: {summarise_snapshot(current)}")
                if terminal(current):
                    print(f"watch ended: PR #{number} is {current['state'].lower()}; do not re-arm")
                    record("ended", current, changes)
                return 0
            if changes != held:
                held = changes
                record("holding", seen, changes)
        if now() >= deadline:
            if held:
                record("holding", seen, held)
                print(f"#{number}: holding until the team's hours open at {clock(window_opens(hours, now()))} ({'; '.join(held)}); re-arm the watch")
            else:
                record("watching", current, [])
                print(f"#{number}: no change in {args.max_minutes} minutes; re-arm the watch")
            return 0


def cmd_crew(args) -> int:
    ledger = ledger_for(args.cwd)
    with ledger.locked():
        return crew_locked(args, ledger)


def in_main_spelling(worktree: str, main_path: str) -> str:
    """The spelling git reports for the checkout wins, so a `Code`/`code` typo does not split one path in two; on a case-sensitive volume, where the two spellings are different directories, the path is left alone."""
    if worktree.lower().startswith(main_path.lower() + "/") and same_path(worktree[:len(main_path)], main_path):
        return main_path + worktree[len(main_path):]
    return worktree


def crew_locked(args, ledger: Ledger) -> int:
    run = ledger.require_run()
    if args.action == "list":
        print(json.dumps(run.get("crew", []), indent=2))
        return 0
    authorise(run, caller_session(args.session), args.by_user, "edit the crew plan")
    if not args.task or not args.branch:
        raise Refusal("crew add needs --task and --branch")
    worktree = os.path.abspath(args.worktree) if args.worktree else None
    if worktree:
        worktree = in_main_spelling(worktree, str(ledger.main))
    entry = {"task": args.task, "branch": args.branch, "worktree": worktree, "brief": str(ledger.dir / "briefs" / f"{args.task}.md"), "migration": args.migration}
    run["crew"] = [c for c in run.get("crew", []) if c.get("task") != args.task] + [entry]
    ledger.save_run(run)
    ledger.log("crew", **entry)
    print(json.dumps(entry) if args.json else f"crew {args.task}: {args.branch} in {worktree or '(no worktree yet)'}; brief at {entry['brief']}")
    return 0


def cmd_join(args) -> int:
    ledger = ledger_for(args.cwd)
    with ledger.locked():
        return join_locked(args, ledger)


def join_locked(args, ledger: Ledger) -> int:
    run = ledger.require_run()
    session_id = caller_session(args.session)
    if not session_id:
        raise Refusal("no session id: run from a Claude Code session or pass --session")
    who = identity(session_id)
    cwd = os.path.abspath(args.cwd)
    plan = crew_for(run, cwd, session_id, ledger.sessions())
    if args.planned and plan is None:
        raise Refusal("not in a planned worktree")
    task = args.task or (plan or {}).get("task") or ""
    branch = args.branch or run_git(cwd, "branch", "--show-current") or (plan or {}).get("branch") or ""
    worktree = str(toplevel(cwd) or cwd)
    row = ledger.sessions().get(session_id, {})
    row.update({
        "session_id": session_id,
        "task": task,
        "branch": branch,
        "worktree": worktree,
        "state": row.get("state") or "briefing",
        "summary": row.get("summary", ""),
        "pr": row.get("pr"),
        "name": who.get("name", ""),
        "socket": who.get("socket"),
        "joined_at": row.get("joined_at") or now(),
        "updated_at": now(),
    })
    ledger.save_session(row)
    ledger.log("join", session_id=session_id, task=task, branch=branch)
    print(json.dumps(row) if args.json else f"joined run {run['name']} as {task or branch or session_id[:8]} ({worktree})")
    return 0


def cmd_report(args) -> int:
    ledger = ledger_for(args.cwd)
    with ledger.locked():
        return report_locked(args, ledger)


def report_locked(args, ledger: Ledger) -> int:
    run = ledger.require_run()
    caller = caller_session(args.session)
    if not caller:
        raise Refusal("no session id: run from a Claude Code session or pass --session")
    session_id = caller
    by = None
    if args.for_session:
        # the coordinator (or the person) corrects a crew row that the crew session cannot or did not
        by = authorise(run, caller, args.by_user, "report for another session")
        session_id = resolve_session(args.for_session, ledger.sessions())
    row = ledger.sessions().get(session_id)
    if row is None:
        raise Refusal("this session has not joined the run; run `mc.py join` first (the mod does it at its first turn)")
    if args.state:
        if args.state not in STATES:
            raise Refusal(f"state must be one of {', '.join(STATES)}")
        row["state"] = args.state
    if args.summary is not None:
        row["summary"] = args.summary.strip()[:160]
    if args.pr is not None:
        row["pr"] = args.pr or None
    if args.branch:
        row["branch"] = args.branch
    row["updated_at"] = now()
    ledger.save_session(row)
    ledger.log("report", session_id=session_id, state=row.get("state"), summary=row.get("summary"), pr=row.get("pr"), **({"by": by} if by else {}))
    print(json.dumps(row) if args.json else f"{row.get('task') or session_id[:8]}: {row.get('state')} · {row.get('summary', '')}")
    return 0


def cmd_request(args) -> int:
    ledger = ledger_for(args.cwd)
    run = ledger.require_run()
    found = find_config(args.cwd)
    if found and args.resource not in resources(found[1]):
        raise Refusal(f"no resource named {args.resource}; configured: {', '.join(resources(found[1]))}")
    session_id = caller_session(args.session)
    if not session_id:
        raise Refusal("no session id")
    spec = resources(found[1]).get(args.resource, {}) if found else {}
    if isinstance(spec, dict) and spec.get("human_gate"):
        note = " It is a human gate: the window is announced by mission control and the command is Jason's to type."
    else:
        note = ""
    req = {"resource": args.resource, "session_id": session_id, "minutes": args.minutes, "what": (args.what or "").strip()[:240], "at": now(), "command": args.command}
    write_json(ledger.request_path(args.resource, session_id), req)
    ledger.log("request", **req)
    holder = ledger.slots().get(args.resource)
    held = f" Currently held by {holder.get('holder', '')[:8]} until {clock(holder.get('until'))}." if holder else " Currently free."
    print(json.dumps(req) if args.json else f"slot request recorded: {args.resource} for {args.minutes or '?'} min.{held}{note} Mission control grants by message; do not run the command before the grant arrives.")
    return 0


def cmd_grant(args) -> int:
    ledger = ledger_for(args.cwd)
    with ledger.locked():
        return grant_locked(args, ledger)


def holds_a_slot(ledger: Ledger, session_id: str) -> bool:
    """Whether a session still holds any slot; a row reads `in-slot` until its last one goes."""
    return any(held.get("holder") == session_id for held in ledger.slots().values())


def grant_locked(args, ledger: Ledger) -> int:
    run = ledger.require_run()
    by = authorise(run, caller_session(args.session), args.by_user, "grant a slot")
    found = find_config(args.cwd)
    if found and args.resource not in resources(found[1]):
        raise Refusal(f"no resource named {args.resource}; configured: {', '.join(resources(found[1]))}")
    sessions = ledger.sessions()
    target = resolve_session(args.to, sessions)
    holder = ledger.slots().get(args.resource)
    if holder and holder.get("holder") != target and not args.force:
        raise Refusal(f"{args.resource} is held by {holder.get('holder_task') or holder.get('holder', '')[:8]} since {clock(holder.get('granted_at'))}; wait for the release or pass --force to override")
    request = read_json(ledger.request_path(args.resource, target), {}) or {}
    minutes = args.minutes or request.get("minutes") or 15
    # a request the hook recorded from a refused attempt reads `attempted: <command>`; the slot's purpose is the command
    if isinstance(request.get("what"), str) and request["what"].startswith("attempted: "):
        request["what"] = request["what"][len("attempted: "):]
    slot = {
        "resource": args.resource,
        "holder": target,
        "granted_at": now(),
        "until": now() + 60 * float(minutes),
        "what": (args.what or request.get("what") or "").strip()[:240],
        "note": (args.note or "").strip()[:240],
        "by": by,
        "forced": bool(holder and holder.get("holder") != target),
    }
    row = sessions.get(target)
    # what the holder was doing before the slot, so the release puts it back instead of forcing `working`
    prior = (row or {}).get("state")
    if row and prior == "in-slot":
        # already in another slot (or this one): the state before the first of them is the one to restore
        prior = next((held.get("prior_state") for held in ledger.slots().values() if held.get("holder") == target and held.get("prior_state")), None)
    slot["prior_state"] = prior if prior in RESTORED_STATES else "working"
    write_json(ledger.slot_path(args.resource), slot)
    path = ledger.request_path(args.resource, target)
    if path.exists():
        path.unlink()
    if row:
        row["state"] = "in-slot"
        row["updated_at"] = now()
        ledger.save_session(row)
    # a forced grant displaces the old holder, whose row must stop reading in-slot
    displaced = sessions.get((holder or {}).get("holder", ""))
    if slot["forced"] and displaced and displaced.get("state") == "in-slot" and not holds_a_slot(ledger, holder["holder"]):
        displaced["state"] = holder.get("prior_state") or "working"
        displaced["updated_at"] = now()
        ledger.save_session(displaced)
    ledger.log("grant", **slot)
    print(json.dumps(slot) if args.json else f"{args.resource} granted to {(row or {}).get('task') or target[:8]} until {clock(slot['until'])}" + (" (forced)" if slot["forced"] else ""))
    return 0


def cmd_release(args) -> int:
    ledger = ledger_for(args.cwd)
    with ledger.locked():
        return release_locked(args, ledger)


def release_locked(args, ledger: Ledger) -> int:
    run = ledger.require_run()
    session_id = caller_session(args.session)
    slot = ledger.slots().get(args.resource)
    if not slot:
        raise Refusal(f"{args.resource} is not held")
    if slot.get("holder") != session_id:
        authorise(run, session_id, args.by_user, f"release {args.resource} held by another session")
    ledger.slot_path(args.resource).unlink(missing_ok=True)
    row = ledger.sessions().get(slot["holder"])
    if row and row.get("state") == "in-slot" and not holds_a_slot(ledger, slot["holder"]):
        row["state"] = slot.get("prior_state") or "working"
        row["updated_at"] = now()
        ledger.save_session(row)
    ledger.log("release", resource=args.resource, holder=slot["holder"], note=(args.note or "")[:240], by=session_id)
    print(json.dumps({"released": args.resource}) if args.json else f"{args.resource} released" + (f": {args.note}" if args.note else ""))
    return 0


def cmd_needs(args) -> int:
    ledger = ledger_for(args.cwd)
    with ledger.locked():
        return needs_locked(args, ledger)


def needs_locked(args, ledger: Ledger) -> int:
    run = ledger.require_run()
    session_id = caller_session(args.session)
    needs = run.setdefault("needs", [])
    if args.action == "list":
        print(json.dumps(needs, indent=2))
        return 0
    if args.action == "add":
        if not args.why:
            raise Refusal("needs add wants --why, and --command with --cwd when there is a command to type")
        row = ledger.sessions().get(session_id or "", {})
        n = 1 + max([x.get("n", 0) for x in needs] or [0])
        need = {"id": uuid.uuid4().hex[:8], "n": n, "session_id": session_id, "task": row.get("task", ""), "why": args.why.strip()[:240],
                "command": (args.command or "").strip(), "cwd": args.cwd_hint or row.get("worktree") or "", "status": "open", "at": now()}
        needs.append(need)
        ledger.save_run(run)
        ledger.log("need", **need)
        print(json.dumps(need) if args.json else f"needs Jason #{n}: {need['why']}" + (f" · `{need['command']}`" if need["command"] else ""))
        return 0
    # done
    target = next((x for x in needs if str(x.get("n")) == str(args.ref) or x.get("id") == args.ref), None)
    if target is None:
        raise Refusal(f"no open need {args.ref}")
    if target.get("session_id") != session_id:
        authorise(run, session_id, args.by_user, "mark another session's need done")
    target["status"] = "done"
    target["done_at"] = now()
    ledger.save_run(run)
    ledger.log("need-done", id=target["id"], n=target["n"])
    print(f"need #{target['n']} done")
    return 0


def cmd_assume(args) -> int:
    ledger = ledger_for(args.cwd)
    with ledger.locked():
        return assume_locked(args, ledger)


def assume_locked(args, ledger: Ledger) -> int:
    run = ledger.require_run()
    assumptions = run.setdefault("assumptions", [])
    if args.action == "list":
        for a in assumptions:
            flag = f" (changed {clock(a.get('changed_at'))})" if a.get("changed_at") else ""
            print(f"{a['n']}. {a['text']}{flag}")
        return 0
    authorise(run, caller_session(args.session), args.by_user, "change a shared assumption")
    if not args.text:
        raise Refusal("assume set needs text")
    n = int(args.n) if args.n else 1 + max([a.get("n", 0) for a in assumptions] or [0])
    existing = next((a for a in assumptions if a.get("n") == n), None)
    if existing:
        existing.update({"text": args.text.strip(), "changed_at": now(), "previous": existing.get("text")})
    else:
        assumptions.append({"n": n, "text": args.text.strip(), "at": now()})
        assumptions.sort(key=lambda a: a["n"])
    ledger.save_run(run)
    ledger.log("assume", n=n, text=args.text.strip(), changed=bool(existing))
    print(f"assumption {n} {'changed' if existing else 'set'}: {args.text.strip()}")
    return 0


def resolve_session(ref: str, sessions: dict[str, dict]) -> str:
    """A session by id, id prefix, task id or registry name; refuses an ambiguous or unknown one."""
    if ref in sessions:
        return ref
    live = registry()
    hits = {sid for sid, row in sessions.items()
            if sid.startswith(ref) or (row.get("task") or "").lower() == ref.lower() or (row.get("branch") or "") == ref}
    hits |= {sid for sid, row in live.items() if (row.get("name") or "").lower() == ref.lower() and sid in sessions}
    if len(hits) == 1:
        return hits.pop()
    if not hits:
        known = ", ".join(f"{row.get('task') or sid[:8]}" for sid, row in sessions.items()) or "none joined yet"
        raise Refusal(f"no session matches {ref}; joined sessions: {known}")
    raise Refusal(f"{ref} matches several sessions: {', '.join(sorted(hits))}")


# ---------------------------------------------------------------- hooks


def hook_output(decision: str | None, reason: str | None, context: str | None) -> dict:
    out: dict = {"hookEventName": "PreToolUse"}
    if decision:
        out["permissionDecision"] = decision
        out["permissionDecisionReason"] = reason or ""
    if context:
        out["additionalContext"] = context
    return {"hookSpecificOutput": out}


OVERRIDE_FLAGS = (BY_USER, "--session")
SESSION_ENV = "CLAUDE_CODE_SESSION_ID"


def overrides_identity(command: str, depth: int = 0) -> bool:
    """True when a line that runs mc.py passes a flag or variable that changes who the CLI takes the caller to be.

    Reads the line as shlex tokens, so quoting, `env` and `export` forms and an
    abbreviated flag (`--by`, `--sess`) are seen; a quoted script is read the
    same way, three levels down. A best-effort check on accidents: a variable
    expanded later, a copied script or a hand-written ledger file get past it.
    """
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars="();<>|&\n")
        lexer.whitespace = " \t\r"
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    if any(os.path.basename(token) == "mc.py" for token in tokens):
        for token in tokens:
            name = token.split("=", 1)[0]
            if token.startswith(SESSION_ENV + "=") or token == SESSION_ENV:
                return True
            if name.startswith("--") and len(name) > 2 and any(flag.startswith(name) for flag in OVERRIDE_FLAGS):
                return True
    if depth < SHELL_DEPTH:
        return any(overrides_identity(token, depth + 1) for token in tokens if re.search(r"\s", token))
    return False


def assess(payload: dict) -> dict:
    """What mission control says about a Bash command: the verdict and whether a held slot covers it.

    A gated command needs the slot held by this session and must run inside
    the holder's worktree. Without the slot the refusal says who holds it and
    how to ask; the attempt is recorded as a request so the board shows it.
    `covered` is true only when the whole line is gated commands this session
    holds (a `cd`, a `VAR=` prefix and a redirect aside), each runs in its
    worktree and is marked `approve_in_slot`: the mod's tool.check hook answers
    `allow` over the project's `ask` on that alone.
    """
    out = {"decision": None, "reason": None, "context": None, "covered": False, "resources": []}
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command:
        return out
    cwd = payload.get("cwd") or os.getcwd()
    session_id = payload.get("session_id")
    if overrides_identity(command):
        return {**out, "decision": "deny", "reason": f"`{BY_USER}` stands for the person typing /mc, and `--session` or `{SESSION_ENV}=` on an mc.py line would make a session someone else; a session passes none of them. Ask mission control, or the person runs /mc."}
    try:
        ledger = ledger_for(cwd)
    except Refusal:
        return out
    run = ledger.run()
    if run is None:
        return out
    found = find_config(cwd)
    if not found:
        return out
    config = found[1]
    hits = gated(config, command)
    if not hits:
        return out
    out["resources"] = sorted({h["resource"] for h in hits})
    slots = ledger.slots()
    sessions = ledger.sessions()
    me = sessions.get(session_id or "", {})
    contexts = []
    covered = True
    for hit in hits:
        spec = resources(config).get(hit["resource"], {})
        label = spec.get("label", hit["resource"])
        if spec.get("human_gate"):
            covered = False
            contexts.append(f"mission-control: `{hit['command']}` touches {label}, a human gate. Ask mission control for the window and give Jason the exact command to type; never run it from this session.")
            continue
        where = runs_in(cwd, hit["cd"])
        slot = slots.get(hit["resource"])
        if slot and slot.get("holder") == session_id:
            worktree = me.get("worktree")
            if worktree and where is not None and not inside(where, worktree):
                return {**out, "decision": "deny", "reason": f"You hold the {label} slot for {worktree}, and this command would run in {where}. Run it from your own worktree (`cd {worktree}` first, as its own command)."}
            if where is None:
                return {**out, "decision": "ask", "reason": f"You hold the {label} slot, and the command's directory cannot be read from the line. Run the cd as its own command, then the task."}
            covered &= bool(spec.get("approve_in_slot"))
            contexts.append(f"mission-control: you hold the {label} slot until {clock(slot.get('until'))}; release it with mc_slot when done, with results.")
            continue
        holder = f"held by {sessions.get(slot['holder'], {}).get('task') or slot['holder'][:8]} until {clock(slot.get('until'))}" if slot else "free, but not granted to you"
        req = {"resource": hit["resource"], "session_id": session_id, "minutes": None, "what": f"attempted: {hit['command']}"[:240], "at": now(), "command": hit["command"]}
        if session_id and not ledger.request_path(hit["resource"], session_id).exists():
            write_json(ledger.request_path(hit["resource"], session_id), req)
            ledger.log("attempt", **req)
        return {**out, "decision": "deny", "reason": (
            f"`{hit['command']}` touches the {label}, a shared resource of mission-control run {run['name']}: {holder}. "
            f"Request a slot (mc_slot with the resource, what you will run and the minutes), wait for the grant message, then run it from your worktree. "
            f"The attempt is on the board as a request.")}
    # A line is covered only when every simple command on it is one of the gated hits: `G && git push` is not, and
    # neither is a line that hides commands in a substitution or in quoting shlex cannot read.
    whole_line = {" ".join(normalise(words)) for words, _ in simple_commands(command)} <= {h["command"] for h in hits} and not opaque(command)
    out["covered"] = covered and bool(contexts) and whole_line
    out["context"] = " ".join(contexts) or None
    return out


def guard(payload: dict) -> dict | None:
    """The PreToolUse hook output for a Bash command, or None when nothing applies."""
    verdict = assess(payload)
    if verdict["decision"] is None and not verdict["context"]:
        return None
    return hook_output(verdict["decision"], verdict["reason"], verdict["context"])


def cmd_check(args) -> int:
    """The mod's question: does a held slot cover this command, and what would the hook say."""
    payload = {"tool_input": {"command": args.command}, "cwd": os.path.abspath(args.cwd), "session_id": caller_session(args.session)}
    print(json.dumps(assess(payload)))
    return 0


def session_start_context(payload: dict) -> str:
    """One paragraph for a session that starts inside a run's worktree or as its coordinator."""
    cwd = payload.get("cwd") or os.getcwd()
    session_id = payload.get("session_id")
    try:
        ledger = ledger_for(cwd)
    except Refusal:
        return ""
    run = ledger.run()
    if run is None:
        return ""
    coord = run.get("coordinator", {})
    if is_coordinator(run, session_id):
        return (f"Mission control: this session coordinates run {run['name']} ({len(run.get('crew', []))} crew). "
                f"Invoke /mission-control:coordinate for the protocol; /mc opens the board.")
    plan = crew_for(run, cwd, session_id, ledger.sessions())
    if plan is None:
        return ""
    brief = plan.get("brief") or ""
    has_brief = bool(brief) and Path(brief).is_file()
    collab = run.get("collaboration") or {}
    hours = collab.get("hours")
    mode_line = (
        f"The project is {collab['mode']} ({collab.get('source', '?')}): "
        + (f"reviewers answer {hours['start']} to {hours['end']} on {', '.join(DAY_NAMES[d] for d in hours['days'])} ({collab.get('timezone', 'local')}), and the PR watch holds outside those hours. " if hours else "nobody is waited for, the merge is the user's and the PR watch covers checks and state only. ")
        if collab.get("mode") else ""
    )
    return (
        f"Mission control: this worktree is crew {plan['task']} ({plan.get('branch')}) in run {run['name']}, started by the user with /mission-control:kickoff. "
        f"The coordinator is the session named \"{coord.get('name') or 'mission control'}\" (socket {coord.get('socket') or '?'}); its messages arrive as cross-session messages from that socket and carry the user's instructions on sequencing, shared code and shared resources. "
        + (f"Read your brief first: {brief}. " if has_brief else "No brief has been written yet; the coordinator will message you. ")
        + mode_line
        + "Then invoke /mission-control:crew for how to report, request a slot, watch your PR once it exists and what stays with the user."
    )


def cmd_hook(args) -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        return 0
    # A subagent does not get its parent's crew brief, but its Bash calls are the parent's: the gate applies to them.
    if args.event == "session-start" and payload.get("agent_id"):
        return 0
    try:
        if args.event == "pre-tool-use":
            out = guard(payload)
            if out:
                json.dump(out, sys.stdout)
        elif args.event == "session-start":
            text = session_start_context(payload)
            if text:
                print(text)
    except Exception as error:  # a hook never breaks a session
        print(f"mission-control hook error: {error}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------- main


class StrictParser(argparse.ArgumentParser):
    """No flag abbreviations: `--by` must not reach `--by-user`. Subparsers are built from type(self), so they inherit this."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("allow_abbrev", False)
        super().__init__(*args, **kwargs)


def build_parser() -> argparse.ArgumentParser:
    parser = StrictParser(prog="mc.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--cwd", default=os.getcwd(), help="the directory to act from (default: the current one)")
    parser.add_argument("--session", help="act as this session id (the mod passes its own; a Bash child needs none)")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("detect", help="print the project config path; exit 2 when there is none")
    sp = sub.add_parser("init", help="write a starter .claude/mission-control.json")
    sp.add_argument("--force", action="store_true")
    sp = sub.add_parser("start", help="start a run with this session as coordinator")
    sp.add_argument("--name", required=True)
    sp.add_argument("--base", help="the trunk branch (default: origin's HEAD)")
    sp.add_argument("--pr-approval", dest="pr_approval", choices=["user", "coordinator"], default="user",
                    help="who approves a crew session's PR description before pr-create pushes: the user in each session (default), or the coordinator")
    sp.add_argument("--collaboration", choices=["solo", "collaborative"], help="state the project's mode instead of taking the config's or the inferred one")
    sp.add_argument("--small-model-ok", dest="small_model_ok", action="store_true", help="the mod refuses a start from a haiku or sonnet session; this flag says the user means it")
    sp = sub.add_parser("end", help="end the run and archive the ledger")
    sp.add_argument("--force", action="store_true")
    sp.add_argument(BY_USER, dest="by_user", action="store_true")
    sp = sub.add_parser("status", help="the board as text, or --json")
    sp.add_argument("--probe", action="store_true", help="also probe each resource on the machine")
    sp = sub.add_parser("probe", help="what the machine says about a resource")
    sp.add_argument("resource", nargs="?")
    sub.add_parser("reconcile", help="diff the ledger against the live registry, GitHub and the branches on origin (a merged PR's base, an open PR's branch); print what drifted and who each PR waits on")
    sp = sub.add_parser("classify", help="solo or collaborative: the run record's answer, else the config's, else inferred from 90 days of authors and the reviews on merged PRs")
    sp.add_argument("--fresh", action="store_true", help="recompute even while a run holds an answer")
    sp = sub.add_parser("watch", help="watch a PR in the background until something changes (reviews, comments, checks, state), print what and exit; held outside the team's hours on a collaborative project unless merged or closed")
    sp.add_argument("--pr", type=int, help="the PR number (default: this session's row)")
    sp.add_argument("--interval", type=float, default=300, help="seconds between polls (default 300)")
    sp.add_argument("--max-minutes", dest="max_minutes", type=float, default=720, help="give up and ask to be re-armed after this long (default 720)")
    sp.add_argument("--once", action="store_true", help="print the PR as it stands and exit")
    sp = sub.add_parser("retire", help="reclaim a finished crew session's worktree mid-run: session closed, row done, PR landed, tree clean, nothing running in it; removes it, prunes, deletes the branch with -d only (coordinator or --by-user)")
    sp.add_argument("ref", help="the session: id, prefix, task, branch or name")
    sp.add_argument("--dry-run", dest="dry_run", action="store_true", help="print what would go and the disk it holds; change nothing")
    sp.add_argument(BY_USER, dest="by_user", action="store_true")
    sp = sub.add_parser("crew", help="the crew plan: add a task's branch, worktree and brief path, or list")
    sp.add_argument("action", choices=["add", "list"])
    sp.add_argument("--task")
    sp.add_argument("--branch")
    sp.add_argument("--worktree")
    sp.add_argument("--migration", help="the migration timestamp assigned to this task, if any")
    sp.add_argument(BY_USER, dest="by_user", action="store_true")
    sp = sub.add_parser("join", help="register this session in the run")
    sp.add_argument("--task")
    sp.add_argument("--branch")
    sp.add_argument("--planned", action="store_true", help="refuse unless the cwd is in a worktree the crew plan names")
    sp = sub.add_parser("report", help="update this session's row")
    sp.add_argument("--for", dest="for_session", help="update another session's row (coordinator or --by-user): id, prefix, task, branch or name")
    sp.add_argument(BY_USER, dest="by_user", action="store_true")
    sp.add_argument("--state", choices=STATES)
    sp.add_argument("--summary")
    sp.add_argument("--pr", type=int)
    sp.add_argument("--branch")
    sp = sub.add_parser("request", help="ask for a resource slot")
    sp.add_argument("resource")
    sp.add_argument("--minutes", type=float)
    sp.add_argument("--what")
    sp.add_argument("--command")
    sp = sub.add_parser("grant", help="give a session a slot (coordinator or --by-user)")
    sp.add_argument("resource")
    sp.add_argument("--to", required=True, help="session id, id prefix, task id, branch or session name")
    sp.add_argument("--minutes", type=float)
    sp.add_argument("--what")
    sp.add_argument("--note")
    sp.add_argument("--force", action="store_true", help="take the slot from its holder")
    sp.add_argument(BY_USER, dest="by_user", action="store_true")
    sp = sub.add_parser("release", help="release a slot: the holder, the coordinator or --by-user")
    sp.add_argument("resource")
    sp.add_argument("--note")
    sp.add_argument(BY_USER, dest="by_user", action="store_true")
    sp = sub.add_parser("needs", help="the needs-Jason list: add, done, list")
    sp.add_argument("action", choices=["add", "done", "list"])
    sp.add_argument("ref", nargs="?", help="for done: the item number or id")
    sp.add_argument("--why")
    sp.add_argument("--command")
    sp.add_argument("--cwd-hint", dest="cwd_hint", help="where the command must be typed")
    sp.add_argument(BY_USER, dest="by_user", action="store_true")
    sp = sub.add_parser("assume", help="numbered shared assumptions: set, list")
    sp.add_argument("action", choices=["set", "list"])
    sp.add_argument("--n", help="the number to set or change; default: the next")
    sp.add_argument("--text")
    sp.add_argument(BY_USER, dest="by_user", action="store_true")
    sp = sub.add_parser("check", help="what the guard would say about a Bash command, and whether a held slot covers it (JSON)")
    sp.add_argument("--command", required=True)
    sp = sub.add_parser("hook", help="Claude Code hook entry point; reads the payload on stdin")
    sp.add_argument("event", choices=["pre-tool-use", "session-start"])
    return parser


COMMANDS = {
    "detect": cmd_detect, "init": cmd_init, "start": cmd_start, "end": cmd_end, "status": cmd_status, "probe": cmd_probe, "reconcile": cmd_reconcile, "retire": cmd_retire, "classify": cmd_classify, "watch": cmd_watch,
    "crew": cmd_crew, "join": cmd_join, "report": cmd_report, "request": cmd_request, "grant": cmd_grant, "release": cmd_release,
    "needs": cmd_needs, "assume": cmd_assume, "check": cmd_check, "hook": cmd_hook,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return COMMANDS[args.cmd](args)
    except Refusal as refusal:
        if getattr(args, "json", False):
            print(json.dumps({"error": str(refusal)}))
        else:
            print(f"✗ {refusal}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
