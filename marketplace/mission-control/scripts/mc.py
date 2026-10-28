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
    """GitHub's word on each PR (OPEN, MERGED, CLOSED), cached so a 15-second board does not ask every tick; a PR gh cannot read is left out, and a lookup that hangs ends the pass."""
    cache_path = ledger.dir / "pr-cache.json"
    cache = read_json(cache_path, {}) or {}
    found: dict[int, str] = {}
    changed = False
    for number in sorted(numbers):
        hit = cache.get(str(number)) or {}
        if hit.get("state") and now() - hit.get("at", 0) < PR_CACHE_SECONDS:
            found[number] = hit["state"]
            continue
        code, out = sh(["gh", "pr", "view", str(number), "--json", "state", "-q", ".state"], timeout=PR_LOOKUP_SECONDS, cwd=ledger.main)
        if code == 124:
            break  # gh is hanging, so the rest would too; the next tick retries
        state = out.strip().upper()
        if code == 0 and state in ("OPEN", "MERGED", "CLOSED"):
            found[number] = state
            cache[str(number)] = {"state": state, "at": now()}
            changed = True
    if changed and ledger.dir.is_dir():
        write_json(cache_path, cache)
    return found


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
    run = {
        "name": args.name,
        "repo_root": str(ledger.main),
        "slug": ledger.slug,
        "started_at": now(),
        "coordinator": who,
        "base": {"branch": base_branch, "commit": commit, "on_origin": on_origin},
        "pr_approval": args.pr_approval,
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
    print(json.dumps(run, indent=2) if args.json else f"Run {args.name} started; coordinator {who.get('name') or session_id}; base {base_branch}@{commit[:8]}; ledger {ledger.dir}{warning}")
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
    return (
        f"Mission control: this worktree is crew {plan['task']} ({plan.get('branch')}) in run {run['name']}, started by the user with /mission-control:kickoff. "
        f"The coordinator is the session named \"{coord.get('name') or 'mission control'}\" (socket {coord.get('socket') or '?'}); its messages arrive as cross-session messages from that socket and carry the user's instructions on sequencing, shared code and shared resources. "
        + (f"Read your brief first: {brief}. " if has_brief else "No brief has been written yet; the coordinator will message you. ")
        + "Then invoke /mission-control:crew for how to report, request a slot and what stays with the user."
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
    sp = sub.add_parser("end", help="end the run and archive the ledger")
    sp.add_argument("--force", action="store_true")
    sp.add_argument(BY_USER, dest="by_user", action="store_true")
    sp = sub.add_parser("status", help="the board as text, or --json")
    sp.add_argument("--probe", action="store_true", help="also probe each resource on the machine")
    sp = sub.add_parser("probe", help="what the machine says about a resource")
    sp.add_argument("resource", nargs="?")
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
    "detect": cmd_detect, "init": cmd_init, "start": cmd_start, "end": cmd_end, "status": cmd_status, "probe": cmd_probe,
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
