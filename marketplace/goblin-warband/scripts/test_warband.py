"""Tests for warband.py: the gate matcher, the ledger, authorisation and both hooks.

Run from this directory: python3 -m unittest test_warband

Every test works in a throwaway git repository with its own ledger root and
session registry (GOBLIN_WARBAND_HOME, CLAUDE_SESSIONS_DIR), so nothing here
touches ~/.claude. The module-level guard below also points HOME, CLAUDE_CONFIG_DIR
and both ledger variables at a temporary directory before warband.py is imported,
so a test that forgets its sandbox, or the migration reading its defaults, still
cannot reach the real ledger. Probes that shell out (lsof, psql) are not exercised.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLI = HERE / "warband.py"
EXAMPLE = HERE.parent / "references" / "goblin-warband.example.json"

# Nothing in this suite may resolve a default to the real ~/.claude: every
# fallback warband.py derives (the ledger, the old mission-control ledger the
# migration reads, the session registry) lands under this throwaway home.
REAL_HOME = Path.home()
GUARD_HOME = Path(tempfile.mkdtemp(prefix="warband-guard-"))
os.environ["HOME"] = str(GUARD_HOME)
os.environ["CLAUDE_CONFIG_DIR"] = str(GUARD_HOME / ".claude")
os.environ["GOBLIN_WARBAND_HOME"] = str(GUARD_HOME / ".claude" / "goblin-warband")
os.environ["MISSION_CONTROL_HOME"] = str(GUARD_HOME / ".claude" / "mission-control")
os.environ["CLAUDE_SESSIONS_DIR"] = str(GUARD_HOME / ".claude" / "sessions")


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True)


class Sandbox:
    """A repo with the example config, a worktree, a ledger root and a fake session registry."""

    def __init__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mc-test-"))
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        (self.repo / ".claude").mkdir()
        config = json.loads(EXAMPLE.read_text())
        config.pop("collaboration", None)  # the example states CHIRPdb's mode; the sandbox infers its own (solo, one author)
        (self.repo / ".claude" / "goblin-warband.json").write_text(json.dumps(config))
        (self.repo / "README.md").write_text("x\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "init")
        self.worktree = self.repo / ".claude" / "worktrees" / "crew-a"
        git(self.repo, "worktree", "add", "-q", "-b", "feat/a", str(self.worktree), "main")
        self.ledger_root = self.tmp / "ledger"
        self.sessions = self.tmp / "sessions"
        self.sessions.mkdir()
        self.env = {
            **os.environ,
            "GOBLIN_WARBAND_HOME": str(self.ledger_root),
            "MISSION_CONTROL_HOME": str(self.tmp / "old-ledger"),
            "HOME": str(self.tmp / "home"),
            "CLAUDE_CONFIG_DIR": str(self.tmp / "home" / ".claude"),
            "CLAUDE_SESSIONS_DIR": str(self.sessions),
        }
        self.env.pop("CLAUDE_CODE_SESSION_ID", None)
        self.register("coord-1", "mission control", str(self.repo))
        self.register("crew-1", "10se2", str(self.worktree))

    def register(self, session_id, name, cwd):
        (self.sessions / f"{session_id}.json").write_text(json.dumps({
            "pid": os.getpid(), "sessionId": session_id, "cwd": cwd, "name": name,
            "messagingSocketPath": f"/tmp/cc-socks/{session_id}.sock", "status": "idle",
        }))

    def mc(self, *args, session=None, cwd=None, stdin=None, expect=0):
        env = dict(self.env)
        if session:
            env["CLAUDE_CODE_SESSION_ID"] = session
        done = subprocess.run(
            [sys.executable, "-I", str(CLI), "--cwd", str(cwd or self.repo), *args],
            capture_output=True, text=True, env=env, input=stdin,
        )
        if expect is not None and done.returncode != expect:
            raise AssertionError(f"mc {' '.join(args)} exited {done.returncode}: {done.stdout}{done.stderr}")
        return done

    def start(self):
        return self.mc("start", "--name", "search", session="coord-1")

    def hook(self, event, payload, session="crew-1", cwd=None):
        payload = {"session_id": session, "cwd": str(cwd or self.worktree), **payload}
        done = self.mc("hook", event, session=session, stdin=json.dumps(payload))
        return done.stdout


class GateMatching(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(HERE))
        import warband  # noqa: WPS433
        self.mc = warband
        self.config = json.loads(EXAMPLE.read_text())

    def test_open_browsers_walks_a_playwright_chrome_up_to_its_session(self):
        """The browser whose parent is the playwright-mcp server is traced to the claude pid above it; helpers, strangers and chains that reach no session are skipped."""
        table = "\n".join([
            "  100     1 03:01:52 claude --name 12rt3 overflow menu",
            "  200   100 03:01:50 npm exec @playwright/mcp@latest",
            "  300   200 03:01:48 node /Users/j/.npm/_npx/x/node_modules/.bin/playwright-mcp",
            "  400   300    05:55 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome --disable-field-trial-config --user-data-dir=/Users/j/Library/Caches/ms-playwright/mcp-chrome-2ae1b0c --remote-debugging-pipe",
            "  401   400    05:53 /Applications/Google Chrome.app/Contents/Frameworks/Google Chrome Framework.framework/Helpers/Google Chrome Helper (GPU).app/Contents/MacOS/Google Chrome Helper (GPU) --type=gpu-process",
            "  500     1 20-07:02:25 /Applications/Discord.app/Contents/Frameworks/Electron Framework.framework/Helpers/chrome_crashpad_handler --no-rate-limit",
            "  600   700    01:00 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "  800   801 02:00:00 node /x/.bin/playwright-mcp",
            "  802   800 01:59:00 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome --user-data-dir=/Users/j/Library/Caches/ms-playwright/mcp-chrome-9f0e11d --remote-debugging-pipe",
            "  900   999 00:10:00 npm exec @playwright/mcp@latest --browser firefox",
            "  901   900 00:09:58 node /Users/j/.npm/_npx/x/node_modules/.bin/playwright-mcp --browser firefox",
            "  902   901 00:02:30 /Users/j/Library/Caches/ms-playwright/firefox-1500/firefox/Nightly.app/Contents/MacOS/firefox -no-remote -wait-for-browser -foreground -profile /Users/j/Library/Caches/ms-playwright/mcp-firefox-2ae1b0c -juggler-pipe about:blank",
        ])
        procs = self.mc.parse_process_table(table)
        self.assertEqual(len(procs), 12)
        live = {"crew-3": {"pid": 100}, "coord-1": {"pid": 999}}
        # Chromium's flags are double-dash and Firefox's single-dash; both carry the profile path, and neither may name the browser
        self.assertEqual(self.mc.open_browsers(procs, live), [
            {"session_id": "crew-3", "pid": 400, "etime": "05:55", "browser": "Google Chrome"},
            {"session_id": "coord-1", "pid": 902, "etime": "00:02:30", "browser": "firefox"},
        ])
        self.assertEqual(self.mc.parse_process_table("garbage\n"), [])

    def test_reset_through_poetry_is_gated_as_local_db(self):
        hits = self.mc.gated(self.config, "cd apps/api && poetry run poe db-reset-local-anyway")
        self.assertEqual([h["resource"] for h in hits], ["local-db"])
        self.assertEqual(hits[0]["cd"], "apps/api")
        self.assertEqual(hits[0]["command"], "poe db-reset-local-anyway")

    def test_serve_and_hosted_tasks_are_gated(self):
        self.assertEqual([h["resource"] for h in self.mc.gated(self.config, "poetry run poe serve-local")], ["api-port"])
        self.assertEqual([h["resource"] for h in self.mc.gated(self.config, "poetry run poe smoke-search-hosted --limit 3")], ["hosted"])
        self.assertEqual([h["resource"] for h in self.mc.gated(self.config, "supabase db reset --linked")], ["local-db", "hosted"])

    def test_unrelated_commands_pass(self):
        self.assertEqual(self.mc.gated(self.config, "poetry run poe test && git status"), [])
        self.assertEqual(self.mc.gated(self.config, "echo 'poe serve-local'"), [])
        self.assertEqual(self.mc.gated(self.config, "FOO=1 poetry run poe lint"), [])

    def test_heredoc_body_is_not_a_command(self):
        command = "cat <<'EOF' > note.md\npoetry run poe serve-local\nEOF"
        self.assertEqual(self.mc.gated(self.config, command), [])

    def test_runs_in_follows_cd(self):
        self.assertEqual(self.mc.runs_in("/w", "apps/api"), "/w/apps/api")
        self.assertEqual(self.mc.runs_in("/w", None), "/w")
        self.assertIsNone(self.mc.runs_in("/w", "$DIR"))

    def test_shell_c_wrappers_are_unwrapped(self):
        for command in [
            "sh -c 'poetry run poe db-reset-local-anyway'",
            'bash -c "poetry run poe db-reset-local-anyway"',
            "zsh -c 'poetry run poe db-reset-local-anyway'",
            "bash -lc 'poetry run poe db-reset-local-anyway'",
            "sh -c \"sh -c 'poe db-reset-local-anyway'\"",
        ]:
            self.assertEqual([h["resource"] for h in self.mc.gated(self.config, command)], ["local-db"], command)

    def test_shell_options_with_an_argument_do_not_hide_the_script(self):
        for command in [
            "bash -o pipefail -c 'poetry run poe db-reset-local-anyway'",
            "bash +o pipefail -c 'poe db-reset-local-anyway'",
            "bash -O extglob -c 'poe db-reset-local-anyway'",
            "bash -e -o pipefail -c 'poe db-reset-local-anyway'",
            "bash --norc -c 'poe db-reset-local-anyway'",
        ]:
            self.assertEqual([h["resource"] for h in self.mc.gated(self.config, command)], ["local-db"], command)

    def test_runner_prefixes_do_not_hide_a_gated_command(self):
        for command in [
            "env poetry run poe db-reset-local-anyway",
            "env FOO=1 -u BAR poe db-reset-local-anyway",
            "timeout 60 poe db-reset-local-anyway",
            "timeout -s KILL 60 poe db-reset-local-anyway",
            "nohup poe db-reset-local-anyway",
            "time poe db-reset-local-anyway",
            "command poe db-reset-local-anyway",
            "timeout 60 sh -c 'poe db-reset-local-anyway'",
            "nohup timeout 60 env FOO=1 poe db-reset-local-anyway",
            "command poe db-reset-local-anyway -v",
            "env poe db-reset-local-anyway -S",
            "timeout --signal KILL 60 poe db-reset-local-anyway",
            "timeout --kill-after 5 60 poe db-reset-local-anyway",
            "timeout --signal=KILL 60 poe db-reset-local-anyway",
            "env - poe db-reset-local-anyway",
            "nohup -- poe db-reset-local-anyway",
            "env -C /tmp poe db-reset-local-anyway",
            "env --chdir=/tmp poe db-reset-local-anyway",
            "timeout -vs KILL 60 poe db-reset-local-anyway",
            "timeout --sig KILL 60 poe db-reset-local-anyway",
            "timeout --k 5 60 poe db-reset-local-anyway",
            "timeout -k5s 60 poe db-reset-local-anyway",
            "timeout -vk5s 60 poe db-reset-local-anyway",
            "timeout -sTERM -k10s 60 poe db-reset-local-anyway",
            "env -iC /x poe db-reset-local-anyway",
            "env --chd /x poe db-reset-local-anyway",
            "env -iu FOO poe db-reset-local-anyway",
            "env -P /usr/bin poe db-reset-local-anyway",
        ]:
            self.assertEqual([h["resource"] for h in self.mc.gated(self.config, command)], ["local-db"], command)

    def test_runner_prefixes_on_harmless_commands_stay_ungated(self):
        for command in ["command -v poe", "command -V poe", "env", "timeout 60 echo poe serve-local", "env FOO=1 poe lint", "env -S 'poe db-reset-local-anyway'"]:
            self.assertEqual(self.mc.gated(self.config, command), [], command)

    def test_env_chdir_is_read_as_the_directory_of_its_own_command(self):
        for command in ["env -C /w poe serve-local", "env -C/w poe serve-local", "env --chdir /w poe serve-local", "env --chdir=/w poe serve-local"]:
            self.assertEqual([h["cd"] for h in self.mc.gated(self.config, command)], ["/w"], command)
        self.assertEqual(self.mc.gated(self.config, "cd a && env -C b poe serve-local")[0]["cd"], "a/b")
        # the chdir does not leak onto the command after it
        self.assertEqual([h["cd"] for h in self.mc.gated(self.config, "env -C /w poe serve-local && poe serve-local")], ["/w", None])
        self.assertEqual(self.mc.gated(self.config, "env -C /w sh -c 'poe serve-local'")[0]["cd"], "/w")

    def test_cd_behind_a_program_runner_moves_nothing(self):
        for command in ["cd /r && env cd w && poe serve-local", "cd /r && nohup cd w && poe serve-local", "cd /r && timeout 5 cd w && poe serve-local"]:
            self.assertEqual(self.mc.gated(self.config, command)[0]["cd"], "/r", command)
        for command in ["cd /r && command cd w && poe serve-local", "cd /r && time cd w && poe serve-local"]:
            self.assertEqual(self.mc.gated(self.config, command)[0]["cd"], "/r/w", command)

    def test_shell_c_inner_cd_composes_and_does_not_leak(self):
        hits = self.mc.gated(self.config, "cd sub && sh -c 'cd apps/api && poetry run poe db-reset-local-anyway'")
        self.assertEqual(hits[0]["cd"], "sub/apps/api")
        hits = self.mc.gated(self.config, "sh -c 'cd x && poe serve-local'; poe serve-local")
        self.assertEqual([h["cd"] for h in hits], ["x", None])
        self.assertEqual(self.mc.gated(self.config, "cd a && cd b && poe serve-local")[0]["cd"], "a/b")

    def test_shell_c_text_is_not_a_command(self):
        for command in ["bash -c 'echo poe serve-local'", "bash script.sh", "bash -c", "bash -c 'poetry run poe lint'"]:
            self.assertEqual(self.mc.gated(self.config, command), [], command)

    def test_opaque_lines(self):
        for command in ['poe serve-local "$(git push)"', "poe serve-local `git push`", "poe serve-local && git push 'x"]:
            self.assertTrue(self.mc.opaque(command), command)
        self.assertFalse(self.mc.opaque("cd apps/api && poe serve-local > out.log 2>&1"))


class LedgerFlow(unittest.TestCase):
    def setUp(self):
        self.box = Sandbox()

    def test_start_records_coordinator_and_base(self):
        out = self.box.start().stdout
        self.assertIn("Raid search started", out)
        status = json.loads(self.box.mc("--json", "status").stdout)
        self.assertEqual(status["run"]["coordinator"]["session_id"], "coord-1")
        self.assertEqual(status["run"]["coordinator"]["name"], "mission control")
        self.assertEqual(status["run"]["base"]["branch"], "main")
        self.assertTrue(status["run"]["base"]["commit"])

    def test_coordinator_socket_follows_the_session_id_across_a_restart(self):
        self.box.start()
        before = json.loads(self.box.mc("--json", "status").stdout)["run"]["coordinator"]
        self.assertEqual(before["socket"], "/tmp/cc-socks/coord-1.sock")
        # the same session comes back under another process, another socket and another name
        (self.box.sessions / "coord-1.json").write_text(json.dumps({
            "pid": os.getpid(), "sessionId": "coord-1", "cwd": str(self.box.repo), "name": "mission control (resumed)",
            "messagingSocketPath": "/tmp/cc-socks/99999.sock", "status": "idle",
        }))
        after = json.loads(self.box.mc("--json", "status").stdout)["run"]["coordinator"]
        self.assertEqual(after["session_id"], "coord-1")
        self.assertEqual(after["socket"], "/tmp/cc-socks/99999.sock")
        self.assertEqual(after["name"], "mission control (resumed)")
        # the crew's session-start context names the live socket, not the recorded one
        self.box.mc("crew", "add", "--task", "T", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        text = self.box.hook("session-start", {}, session="crew-9")
        self.assertIn("/tmp/cc-socks/99999.sock", text)
        self.assertNotIn("/tmp/cc-socks/coord-1.sock", text)

    def test_start_puts_an_unpushed_base_on_the_needs_list(self):
        bare = self.box.tmp / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)  # a clone of it checks out main, whatever this machine's init.defaultBranch
        git(self.box.repo, "remote", "add", "origin", str(bare))
        out = self.box.mc("start", "--name", "search", "--base", "main", session="coord-1").stdout
        self.assertIn("WARNING: main is not on origin", out)
        status = json.loads(self.box.mc("--json", "status").stdout)
        self.assertIs(status["run"]["base"]["on_origin"], False)
        self.assertEqual(status["needs"][0]["task"], "kick-off")
        self.assertIn("push -u origin main", status["needs"][0]["command"])
        self.box.mc("end", session="coord-1")
        git(self.box.repo, "push", "-q", "-u", "origin", "main")
        out = self.box.mc("start", "--name", "again", "--base", "main", session="coord-1").stdout
        self.assertNotIn("WARNING", out)
        status = json.loads(self.box.mc("--json", "status").stdout)
        self.assertIs(status["run"]["base"]["on_origin"], True)
        self.assertEqual(status["needs"], [])

    def test_grant_from_a_recorded_attempt_names_the_command_plainly(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "A", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.box.mc("join", session="crew-1", cwd=self.box.worktree)
        self.box.hook("pre-tool-use", {"tool_name": "Bash", "tool_input": {"command": "poetry run poe serve-local"}})
        granted = json.loads(self.box.mc("--json", "grant", "api-port", "--to", "A", session="coord-1").stdout)
        self.assertEqual(granted["what"], "poe serve-local")

    def test_second_start_is_refused(self):
        self.box.start()
        done = self.box.mc("start", "--name", "again", session="coord-1", expect=1)
        self.assertIn("already active", done.stdout)

    def test_join_report_request_grant_release(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        joined = json.loads(self.box.mc("--json", "join", session="crew-1", cwd=self.box.worktree).stdout)
        self.assertEqual(joined["task"], "10SE.2")
        self.assertEqual(joined["branch"], "feat/a")
        self.box.mc("report", "--state", "working", "--summary", "scratch proof done", session="crew-1", cwd=self.box.worktree)
        self.box.mc("request", "local-db", "--minutes", "15", "--what", "one full reset", session="crew-1", cwd=self.box.worktree)
        status = json.loads(self.box.mc("--json", "status").stdout)
        self.assertEqual(status["requests"][0]["task"], "10SE.2")
        # a crew session cannot grant itself
        refused = self.box.mc("grant", "local-db", "--to", "10SE.2", session="crew-1", cwd=self.box.worktree, expect=1)
        self.assertIn("only the chief's session",refused.stdout)
        granted = json.loads(self.box.mc("--json", "grant", "local-db", "--to", "10SE.2", session="coord-1").stdout)
        self.assertEqual(granted["holder"], "crew-1")
        self.assertEqual(granted["what"], "one full reset")
        status = json.loads(self.box.mc("--json", "status").stdout)
        self.assertEqual(status["requests"], [])
        self.assertEqual(status["sessions"][0]["state"], "in-slot")
        # another session cannot release it; the holder can
        self.box.register("crew-2", "10se4", str(self.box.repo))
        self.box.mc("join", "--task", "10SE.4", session="crew-2")
        self.assertEqual(self.box.mc("release", "local-db", session="crew-2", expect=1).returncode, 1)
        self.box.mc("release", "local-db", "--note", "99-assert passed", session="crew-1", cwd=self.box.worktree)
        self.assertEqual(json.loads(self.box.mc("--json", "status").stdout)["slots"], [])

    def test_force_grant_takes_a_held_slot_and_by_user_is_accepted(self):
        self.box.start()
        self.box.mc("join", "--task", "A", session="crew-1", cwd=self.box.worktree)
        self.box.register("crew-2", "b", str(self.box.repo))
        self.box.mc("join", "--task", "B", session="crew-2")
        self.box.mc("grant", "api-port", "--to", "A", session="coord-1")
        refused = self.box.mc("grant", "api-port", "--to", "B", session="coord-1", expect=1)
        self.assertIn("is held by", refused.stdout)
        forced = json.loads(self.box.mc("--json", "grant", "api-port", "--to", "B", "--force", "--by-user", session="crew-2").stdout)
        self.assertEqual(forced["holder"], "crew-2")
        self.assertTrue(forced["forced"])
        self.assertEqual(forced["by"], "user")
        states = {s["task"]: s["state"] for s in json.loads(self.box.mc("--json", "status").stdout)["sessions"]}
        self.assertEqual(states, {"A": "working", "B": "in-slot"})

    def test_flag_abbreviations_are_refused(self):
        self.box.start()
        self.box.mc("join", "--task", "A", session="crew-1", cwd=self.box.worktree)
        refused = self.box.mc("grant", "local-db", "--to", "A", "--by", session="crew-1", cwd=self.box.worktree, expect=2)
        self.assertIn("unrecognized arguments", refused.stderr)
        self.box.mc("--sess", "coord-1", "grant", "local-db", "--to", "A", session="crew-1", cwd=self.box.worktree, expect=2)
        self.assertEqual(json.loads(self.box.mc("--json", "status").stdout)["slots"], [])

    def test_concurrent_needs_and_assumptions_all_survive(self):
        self.box.start()
        self.box.mc("join", "--task", "A", session="crew-1", cwd=self.box.worktree)
        env = {**self.box.env, "CLAUDE_CODE_SESSION_ID": "crew-1"}
        procs = [
            subprocess.Popen([sys.executable, "-I", str(CLI), "--cwd", str(self.box.worktree), "needs", "add", "--why", f"need {i}"],
                             env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for i in range(8)
        ]
        procs.append(subprocess.Popen([sys.executable, "-I", str(CLI), "--cwd", str(self.box.repo), "assume", "set", "--text", "shared"],
                                      env={**self.box.env, "CLAUDE_CODE_SESSION_ID": "coord-1"}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        for proc in procs:
            out, err = proc.communicate()
            self.assertEqual(proc.returncode, 0, out + err)
        status = json.loads(self.box.mc("--json", "status").stdout)
        self.assertEqual(sorted(n["n"] for n in status["needs"]), list(range(1, 9)))
        self.assertEqual(len(status["assumptions"]), 1)

    def test_needs_and_assumptions(self):
        self.box.start()
        self.box.mc("join", "--task", "A", session="crew-1", cwd=self.box.worktree)
        need = json.loads(self.box.mc("--json", "needs", "add", "--why", "type the reset", "--command", "poetry run poe db-reset-local-anyway", session="crew-1", cwd=self.box.worktree).stdout)
        self.assertEqual(need["n"], 1)
        self.assertEqual(Path(need["cwd"]).resolve(), self.box.worktree.resolve())
        self.assertEqual(self.box.mc("needs", "done", "1", session="crew-2", expect=1).returncode, 1)
        self.box.mc("needs", "done", "1", session="coord-1")
        self.assertEqual(json.loads(self.box.mc("--json", "status").stdout)["needs"], [])
        self.box.mc("assume", "set", "--text", "the scan stays exact", session="coord-1")
        self.box.mc("assume", "set", "--n", "1", "--text", "the scan stays exact; total too", session="coord-1")
        out = self.box.mc("assume", "list").stdout
        self.assertIn("1. the scan stays exact; total too (changed", out)
        self.assertEqual(self.box.mc("assume", "set", "--text", "x", session="crew-1", cwd=self.box.worktree, expect=1).returncode, 1)

    def test_end_refuses_while_slots_are_held_then_archives(self):
        self.box.start()
        self.box.mc("join", "--task", "A", session="crew-1", cwd=self.box.worktree)
        self.box.mc("grant", "local-db", "--to", "A", session="coord-1")
        self.assertIn("dibs are still held", self.box.mc("end", session="coord-1", expect=1).stdout)
        self.box.mc("end", "--force", session="coord-1")
        self.assertIsNone(json.loads(self.box.mc("--json", "status").stdout)["run"])
        self.assertTrue(list((self.box.ledger_root / "runs").iterdir()))

    def case_variant_of_worktree(self):
        """The worktree spelt with other capitals, or a skip when this volume tells them apart."""
        variant = self.box.worktree.parent / self.box.worktree.name.upper()
        if not variant.exists():
            self.skipTest("this volume is case-sensitive")
        return variant

    def test_a_cwd_spelt_in_another_case_still_joins_a_planned_worktree(self):
        variant = self.case_variant_of_worktree()
        self.box.start()
        self.box.mc("crew", "add", "--task", "A", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        joined = json.loads(self.box.mc("--json", "join", "--planned", session="crew-1", cwd=variant).stdout)
        self.assertEqual(joined["task"], "A")
        # and a directory outside the plan is turned away rather than joined bare
        self.box.register("crew-2", "elsewhere", str(self.box.repo))
        refused = self.box.mc("join", "--planned", session="crew-2", cwd=self.box.repo, expect=1)
        self.assertIn("not in a planned worktree", refused.stdout)

    def test_session_start_context_finds_the_crew_for_a_cwd_in_another_case(self):
        variant = self.case_variant_of_worktree()
        self.box.start()
        self.box.mc("crew", "add", "--task", "A", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.assertIn("this worktree is raider A", self.box.hook("session-start", {}, session="crew-9", cwd=variant))

    def test_crew_add_writes_the_worktree_in_the_spelling_git_reports(self):
        self.case_variant_of_worktree()
        self.box.start()
        main = Path(json.loads(self.box.mc("--json", "status").stdout)["main_checkout"])
        shouted = main.parent / main.name.upper() / ".claude" / "worktrees" / "crew-a"
        self.box.mc("crew", "add", "--task", "A", "--branch", "feat/a", "--worktree", str(shouted), session="coord-1")
        planned = json.loads(self.box.mc("crew", "list").stdout)[0]["worktree"]
        self.assertEqual(planned, str(main / ".claude" / "worktrees" / "crew-a"))

    def test_crew_add_leaves_a_worktree_alone_when_the_other_spelling_is_a_different_directory(self):
        self.box.start()
        main = Path(json.loads(self.box.mc("--json", "status").stdout)["main_checkout"])
        sibling = main.parent / main.name.upper()
        sibling.mkdir(exist_ok=True)
        if os.path.samefile(sibling, main):
            self.skipTest("this volume is case-insensitive")
        worktree = sibling / ".claude" / "worktrees" / "crew-a"
        worktree.mkdir(parents=True)
        self.box.mc("crew", "add", "--task", "A", "--branch", "feat/a", "--worktree", str(worktree), session="coord-1")
        self.assertEqual(json.loads(self.box.mc("crew", "list").stdout)[0]["worktree"], str(worktree))

    def test_in_main_spelling_rewrites_only_what_the_filesystem_calls_the_same_checkout(self):
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        real_same_path = mc_module.same_path
        try:
            mc_module.same_path = lambda a, b: True
            self.assertEqual(mc_module.in_main_spelling("/CODE/app/wt", "/Code/app"), "/Code/app/wt")
            self.assertEqual(mc_module.in_main_spelling("/elsewhere/wt", "/Code/app"), "/elsewhere/wt")
            mc_module.same_path = lambda a, b: False
            self.assertEqual(mc_module.in_main_spelling("/CODE/app/wt", "/Code/app"), "/CODE/app/wt")
        finally:
            mc_module.same_path = real_same_path

    def test_release_puts_back_the_state_the_slot_interrupted(self):
        self.box.start()
        self.box.mc("join", "--task", "A", session="crew-1", cwd=self.box.worktree)
        self.box.mc("report", "--state", "pr-ready", "--pr", "209", session="crew-1", cwd=self.box.worktree)
        self.box.mc("grant", "api-port", "--to", "A", session="coord-1")
        self.assertEqual(json.loads(self.box.mc("--json", "status").stdout)["sessions"][0]["state"], "in-slot")
        self.box.mc("release", "api-port", session="crew-1", cwd=self.box.worktree)
        row = json.loads(self.box.mc("--json", "status").stdout)["sessions"][0]
        self.assertEqual((row["state"], row["pr"]), ("pr-ready", 209))

    def states(self):
        return {s["task"]: s["state"] for s in json.loads(self.box.mc("--json", "status").stdout)["sessions"]}

    def two_slots_for_a_pr_ready_session(self):
        self.box.start()
        self.box.mc("join", "--task", "A", session="crew-1", cwd=self.box.worktree)
        self.box.mc("report", "--state", "pr-ready", "--pr", "209", session="crew-1", cwd=self.box.worktree)
        self.box.mc("grant", "local-db", "--to", "A", session="coord-1")
        self.box.mc("grant", "api-port", "--to", "A", session="coord-1")

    def test_a_session_holding_two_slots_reads_in_slot_until_the_last_release(self):
        for first, second in (("api-port", "local-db"), ("local-db", "api-port")):
            with self.subTest(first=first):
                self.setUp()
                self.two_slots_for_a_pr_ready_session()
                self.box.mc("release", first, session="crew-1", cwd=self.box.worktree)
                self.assertEqual(self.states(), {"A": "in-slot"})
                self.box.mc("release", second, session="crew-1", cwd=self.box.worktree)
                row = json.loads(self.box.mc("--json", "status").stdout)["sessions"][0]
                self.assertEqual((row["state"], row["pr"]), ("pr-ready", 209))

    def test_a_forced_grant_puts_the_displaced_holder_back_to_what_it_was_doing(self):
        self.box.start()
        self.box.mc("join", "--task", "A", session="crew-1", cwd=self.box.worktree)
        self.box.mc("report", "--state", "pr-ready", session="crew-1", cwd=self.box.worktree)
        self.box.register("crew-2", "b", str(self.box.repo))
        self.box.mc("join", "--task", "B", session="crew-2")
        self.box.mc("grant", "api-port", "--to", "A", session="coord-1")
        self.box.mc("grant", "api-port", "--to", "B", "--force", session="coord-1")
        self.assertEqual(self.states(), {"A": "pr-ready", "B": "in-slot"})

    def test_a_forced_grant_leaves_a_displaced_holder_of_a_second_slot_in_slot(self):
        self.two_slots_for_a_pr_ready_session()
        self.box.register("crew-2", "b", str(self.box.repo))
        self.box.mc("join", "--task", "B", session="crew-2")
        self.box.mc("grant", "api-port", "--to", "B", "--force", session="coord-1")
        self.assertEqual(self.states(), {"A": "in-slot", "B": "in-slot"})
        self.box.mc("release", "local-db", session="crew-1", cwd=self.box.worktree)
        self.assertEqual(self.states(), {"A": "pr-ready", "B": "in-slot"})

    def test_a_forced_grant_to_a_session_already_in_a_slot_keeps_what_it_was_doing_first(self):
        self.box.start()
        self.box.mc("join", "--task", "A", session="crew-1", cwd=self.box.worktree)
        self.box.register("crew-2", "b", str(self.box.repo))
        self.box.mc("join", "--task", "B", session="crew-2")
        self.box.mc("report", "--state", "pr-ready", session="crew-2")
        self.box.mc("grant", "local-db", "--to", "B", session="coord-1")
        self.box.mc("grant", "api-port", "--to", "A", session="coord-1")
        self.box.mc("grant", "api-port", "--to", "B", "--force", session="coord-1")
        self.assertEqual(self.states(), {"A": "working", "B": "in-slot"})
        self.box.mc("release", "api-port", session="crew-2")
        self.assertEqual(self.states(), {"A": "working", "B": "in-slot"})
        self.box.mc("release", "local-db", session="crew-2")
        self.assertEqual(self.states(), {"A": "working", "B": "pr-ready"})

    def test_the_coordinator_can_correct_a_crew_row_and_a_crew_session_cannot(self):
        self.box.start()
        self.box.mc("join", "--task", "A", session="crew-1", cwd=self.box.worktree)
        self.box.mc("report", "--state", "pr-ready", "--pr", "209", session="crew-1", cwd=self.box.worktree)
        self.box.register("crew-2", "b", str(self.box.repo))
        self.box.mc("join", "--task", "B", session="crew-2")
        refused = self.box.mc("report", "--for", "A", "--state", "done", session="crew-2", expect=1)
        self.assertIn("only the chief's session",refused.stdout)
        self.box.mc("report", "--for", "A", "--state", "done", session="coord-1")
        rows = {s["task"]: s["state"] for s in json.loads(self.box.mc("--json", "status").stdout)["sessions"]}
        self.assertEqual(rows, {"A": "done", "B": "briefing"})
        log = [json.loads(line) for line in (self.box.ledger_root / next(self.box.ledger_root.iterdir()).name / "log.jsonl").read_text().splitlines()]
        self.assertEqual([e["by"] for e in log if e["event"] == "report" and e.get("by")], ["coordinator"])

    def test_report_waits_for_the_run_lock_instead_of_racing_a_grant(self):
        import fcntl
        self.box.start()
        self.box.mc("join", "--task", "A", session="crew-1", cwd=self.box.worktree)
        lock_path = next(self.box.ledger_root.iterdir()) / "run.lock"
        with lock_path.open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            proc = subprocess.Popen(
                [sys.executable, "-I", str(CLI), "--cwd", str(self.box.worktree), "report", "--state", "working"],
                env={**self.box.env, "CLAUDE_CODE_SESSION_ID": "crew-1"}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            with self.assertRaises(subprocess.TimeoutExpired):
                proc.communicate(timeout=1)
            fcntl.flock(handle, fcntl.LOCK_UN)
        out, err = proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 0, out + err)

    def test_pr_state_comes_from_gh_and_is_cached(self):
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        ledger = mc_module.Ledger(self.box.repo)
        ledger.dir = self.box.tmp / "pr-ledger"
        ledger.dir.mkdir()
        asked = []
        real_sh = mc_module.sh
        def fake_sh(argv, timeout=8, cwd=None):
            asked.append(argv)
            return 0, "MERGED\n" if argv[3] == "209" else "OPEN\n"
        mc_module.sh = fake_sh
        try:
            self.assertEqual(mc_module.pr_states(ledger, {209, 210}), {209: "MERGED", 210: "OPEN"})
            self.assertEqual(mc_module.pr_states(ledger, {209, 210}), {209: "MERGED", 210: "OPEN"})
            self.assertEqual(len(asked), 2, "the second read comes from the cache")
            mc_module.sh = lambda argv, timeout=8, cwd=None: (1, "no gh")
            self.assertEqual(mc_module.pr_states(ledger, {211}), {})
        finally:
            mc_module.sh = real_sh

    def test_a_hanging_gh_ends_the_pr_lookups_after_one_short_wait(self):
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        ledger = mc_module.Ledger(self.box.repo)
        ledger.dir = self.box.tmp / "pr-hang-ledger"
        ledger.dir.mkdir()
        asked = []
        real_sh = mc_module.sh
        def hanging_sh(argv, timeout=8, cwd=None):
            asked.append((argv[3], timeout))
            return 124, "timed out"
        mc_module.sh = hanging_sh
        try:
            self.assertEqual(mc_module.pr_states(ledger, {301, 302, 303}), {})
            self.assertEqual(len(asked), 1, "the first timeout stops the gh lookups")
            self.assertTrue(all(timeout <= 3 for _, timeout in asked))
            # what was found before the hang survives it, and nothing after is asked
            asked.clear()
            def half_sh(argv, timeout=8, cwd=None):
                asked.append((argv[3], timeout))
                return (0, "OPEN\n") if argv[3] == "301" else (124, "timed out")
            mc_module.sh = half_sh
            self.assertEqual(mc_module.pr_states(ledger, {301, 302, 303}), {301: "OPEN"})
            self.assertEqual([number for number, _ in asked], ["301", "302"])
        finally:
            mc_module.sh = real_sh

    def test_a_hanging_gh_still_reads_the_cached_states_of_later_prs(self):
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        ledger = mc_module.Ledger(self.box.repo)
        ledger.dir = self.box.tmp / "pr-hang-cache-ledger"
        ledger.dir.mkdir()
        mc_module.write_json(ledger.dir / "pr-cache.json", {"311": {"state": "MERGED", "at": mc_module.now()}})
        asked = []
        real_sh = mc_module.sh
        def hanging_sh(argv, timeout=8, cwd=None):
            asked.append(argv[3])
            return 124, "timed out"
        mc_module.sh = hanging_sh
        try:
            # 309 sorts before the cached 311 and hangs; 311 is still answered from disk
            self.assertEqual(mc_module.pr_states(ledger, {309, 311}), {311: "MERGED"})
            self.assertEqual(asked, ["309"])
        finally:
            mc_module.sh = real_sh

    def _crew_with_pr(self, task, session, branch, pr, state="pr-ready"):
        """A crew session in the plan, joined and reporting a PR; the module-level helpers then read the same ledger root."""
        self.box.mc("crew", "add", "--task", task, "--branch", branch, session="coord-1")
        self.box.mc("join", "--task", task, "--branch", branch, session=session)
        self.box.mc("report", "--state", state, "--pr", str(pr), session=session)

    def _reconcile_with(self, fake_sh):
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        real = (mc_module.sh, mc_module.LEDGER_ROOT, mc_module.SESSIONS_DIR)
        mc_module.sh = fake_sh
        mc_module.LEDGER_ROOT = self.box.ledger_root
        mc_module.SESSIONS_DIR = self.box.sessions
        try:
            return mc_module.reconcile(mc_module.ledger_for(self.box.repo))
        finally:
            mc_module.sh, mc_module.LEDGER_ROOT, mc_module.SESSIONS_DIR = real

    @staticmethod
    def _gh(answers):
        def fake_sh(argv, timeout=8, cwd=None):
            if argv[:3] != ["gh", "pr", "view"]:
                return 1, "not gh"
            answer = answers.get(argv[3])
            if answer == "hang":
                return 124, "timed out"
            if answer is None:
                return 1, "no such PR"
            return 0, json.dumps(answer)
        return fake_sh

    def test_reconcile_flags_a_merged_pr_whose_row_is_not_done(self):
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 209)
        result = self._reconcile_with(self._gh({"209": {"state": "MERGED", "reviewDecision": "APPROVED", "reviewRequests": [], "latestReviews": [], "mergedAt": "2026-10-28T10:00:00Z"}}))
        kinds = [item["kind"] for item in result["drift"]]
        self.assertIn("merged-not-done", kinds)
        self.assertEqual(result["prs"], [{"pr": 209, "task": "10SE.2", "state": "MERGED", "waiting_on": "merged"}])
        self.assertNotIn("gone", kinds, "crew-1 is registered and live")

    def test_reconcile_names_the_reviewer_a_pr_waits_on(self):
        self.box.start()
        self.box.register("crew-2", "10se4", str(self.box.repo))
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 210)
        self._crew_with_pr("10SE.4", "crew-2", "feat/b", 211)
        result = self._reconcile_with(self._gh({
            "210": {"state": "OPEN", "reviewDecision": "REVIEW_REQUIRED", "reviewRequests": [{"login": "maxime"}, {"slug": "backend"}], "latestReviews": [], "mergedAt": None},
            "211": {"state": "OPEN", "reviewDecision": "CHANGES_REQUESTED", "reviewRequests": [], "latestReviews": [{"author": {"login": "jess"}, "state": "CHANGES_REQUESTED"}], "mergedAt": None},
        }))
        waits = {pr["pr"]: pr["waiting_on"] for pr in result["prs"]}
        self.assertEqual(waits[210], "waiting on maxime, backend")
        self.assertEqual(waits[211], "changes requested by jess")
        self.assertEqual(result["drift"], [])

    def test_reconcile_asks_for_a_compaction_from_a_live_session_at_70_percent_and_over(self):
        self.box.start()
        self.box.register("crew-2", "10se4", str(self.box.repo))
        self.box.register("crew-3", "10se5", str(self.box.repo))
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 213, state="working")
        self._crew_with_pr("10SE.4", "crew-2", "feat/b", 214, state="working")
        self._crew_with_pr("10SE.5", "crew-3", "feat/c", 215, state="working")
        self.box.mc("report", "--context", "85", session="crew-1")
        self.box.mc("report", "--context", "50", session="crew-2")
        self.box.mc("report", "--context", "70", session="crew-3")
        # renamed after it joined: the line names the window as it is now, not as the row remembers it
        self.box.register("crew-3", "10se5-renamed", str(self.box.repo))
        open_pr = {"state": "OPEN", "reviewDecision": "", "reviewRequests": [], "latestReviews": [], "mergedAt": None}
        result = self._reconcile_with(self._gh({"213": open_pr, "214": open_pr, "215": open_pr}))
        high = {item["task"]: item for item in result["drift"] if item["kind"] == "context-high"}
        self.assertEqual(sorted(high), ["10SE.2", "10SE.5"], "70 is the threshold; 50 is quiet")
        self.assertIn("context 85%", high["10SE.2"]["detail"])
        self.assertIn("only the user can compact it", high["10SE.2"]["detail"])
        self.assertIn("session 10se5-renamed at context 70%", high["10SE.5"]["detail"])

    def test_reconcile_ignores_the_last_context_figure_of_a_gone_or_done_session(self):
        self.box.start()
        self.box.register("crew-2", "10se4", str(self.box.repo))
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 216, state="working")
        self._crew_with_pr("10SE.4", "crew-2", "feat/b", 217, state="working")
        self.box.mc("report", "--context", "90", session="crew-1")
        self.box.mc("report", "--context", "90", session="crew-2")
        self.box.mc("report", "--state", "done", session="crew-2")
        (self.box.sessions / "crew-1.json").unlink()
        open_pr = {"state": "OPEN", "reviewDecision": "", "reviewRequests": [], "latestReviews": [], "mergedAt": None}
        result = self._reconcile_with(self._gh({"216": open_pr, "217": open_pr}))
        kinds = [item["kind"] for item in result["drift"]]
        self.assertNotIn("context-high", kinds)
        self.assertIn("gone", kinds, "the gone line is what covers the dead session")

    def test_status_text_shows_the_context_fill_on_a_live_row(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", session="coord-1")
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1")
        self.assertNotIn("ctx", self.box.mc("status").stdout, "no figure reported yet")
        self.box.mc("report", "--context", "85", session="crew-1")
        self.assertIn("ctx 85%", self.box.mc("status").stdout)

    def test_reconcile_names_a_playwright_browser_a_slotless_session_left_open(self):
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 214, state="working")
        # the sandbox registers every session under the test's own pid; the crew gets a child the test owns, so the chain has one
        # owner and the registry's kill(pid, 0) probe cannot be refused (a detached runner's parent is launchd, which refuses it)
        crew = subprocess.Popen(["sleep", "300"])
        # cleanups run last in, first out: kill, then reap, or the interpreter warns that the child is still running
        self.addCleanup(crew.wait)
        self.addCleanup(crew.kill)
        crew_pid = crew.pid
        row = json.loads((self.box.sessions / "crew-1.json").read_text())
        (self.box.sessions / "crew-1.json").write_text(json.dumps({**row, "pid": crew_pid}))
        table = "\n".join([
            f"{crew_pid} 1 03:01:52 claude --name 10se2",
            f"77001 {crew_pid} 03:01:50 npm exec @playwright/mcp@latest",
            "77002 77001 03:01:48 node /x/node_modules/.bin/playwright-mcp",
            "77003 77002 02:41:09 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome --user-data-dir=/Users/j/Library/Caches/ms-playwright/mcp-chrome-2ae1b0c --remote-debugging-pipe",
        ])
        gh = self._gh({"214": {"state": "OPEN", "reviewDecision": "", "reviewRequests": [], "latestReviews": [], "mergedAt": None}})

        def fake_sh(argv, timeout=8, cwd=None):
            return (0, table) if argv[:1] == ["ps"] else gh(argv, timeout, cwd)

        hit = next(item for item in self._reconcile_with(fake_sh)["drift"] if item["kind"] == "browser-open")
        self.assertEqual((hit["task"], hit["session_id"], hit["pr"]), ("10SE.2", "crew-1", 214))
        self.assertIn("Google Chrome (pid 77003, open 02:41:09) launched by 10se2's Playwright server", hit["detail"])
        self.assertIn("browser_close", hit["detail"])
        # ps unavailable: nothing to say, nothing breaks
        self.assertNotIn("browser-open", [item["kind"] for item in self._reconcile_with(gh)["drift"]])
        # inside a slot the browser is the check in progress, not drift
        self.box.mc("grant", "api-port", "--to", "10SE.2", session="coord-1")
        self.assertNotIn("browser-open", [item["kind"] for item in self._reconcile_with(fake_sh)["drift"]])

    def test_reconcile_flags_a_planned_task_nobody_joined_and_a_session_that_went_away(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.9", "--branch", "feat/z", session="coord-1")
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 212, state="working")
        (self.box.sessions / "crew-1.json").unlink()
        result = self._reconcile_with(self._gh({"212": {"state": "OPEN", "reviewDecision": "", "reviewRequests": [], "latestReviews": [], "mergedAt": None}}))
        by_kind = {item["kind"]: item for item in result["drift"]}
        self.assertEqual(by_kind["unjoined"]["task"], "10SE.9")
        self.assertEqual(by_kind["gone"]["task"], "10SE.2")
        self.assertEqual(by_kind["gone"]["session_id"], "crew-1")
        self.assertEqual(result["prs"][0]["waiting_on"], "solo project; the merge is the user's", "the sandbox has one author and no reviews, so nobody is waited for")

    def test_reconcile_reports_unknown_when_gh_hangs(self):
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 213)
        result = self._reconcile_with(self._gh({"213": "hang"}))
        self.assertEqual(result["prs"], [{"pr": 213, "task": "10SE.2", "state": "UNKNOWN", "waiting_on": "unknown (gh did not answer)"}])
        self.assertEqual([item["kind"] for item in result["drift"]], [])

    def test_reconcile_flags_a_need_left_open_after_its_session_finished(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", session="coord-1")
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1")
        self.box.mc("needs", "add", "--why", "push the branch", "--command", "git push -u origin feat/a", session="crew-1")
        self.box.mc("report", "--state", "done", session="crew-1")
        result = self._reconcile_with(self._gh({}))
        self.assertEqual([item["kind"] for item in result["drift"]], ["need-open-after-done"])
        self.assertIn("its session is done", result["drift"][0]["detail"])

    def test_reconcile_leaves_a_started_need_alone_when_its_session_finished(self):
        # the CHIRPdb backfill: started by the user, still running after the crew session that asked for it is done
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", session="coord-1")
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1")
        self.box.mc("needs", "add", "--why", "run the backfill", "--command", "bun run backfill", session="crew-1")
        self.box.mc("needs", "start", "1", "--note", "bg task abc", session="coord-1")
        self.box.mc("report", "--state", "done", session="crew-1")
        result = self._reconcile_with(self._gh({}))
        self.assertEqual(result["drift"], [], "a started need runs on after its session ends; it closes with the result")
        needs = json.loads(self.box.mc("needs", "list", session="coord-1").stdout)
        self.assertEqual(needs[0]["status"], "started")

    @staticmethod
    def _roadmap(started=None, task="10SE.2", status="todo"):
        """A rich roadmap listing one task, claimed (`started` set) or not."""
        row = {"id": task, "title": "the task", "status": status, "assignee": "Jason"}
        if started:
            row["started"] = started
        return json.dumps([{"name": "t", "path": "", "archived": False, "milestones": [{"id": "M1", "name": "one", "tasks": [row]}]}])

    def _roadmap_repo_with_origin(self, claim_on_branch=True, claim_on_main=False, listed=True, rel=".claude/roadmaps.json"):
        """A rich roadmap, a bare origin holding main, and feat/a pushed with (or without) a commit that sets the task's `started`.
        `claim_on_main` puts the claim on main under a sync batch's subject instead; `listed=False` leaves the task out of the roadmap.
        `rel` is the file it lives in: goblin-scout's .claude/roadbook.json, or the old .claude/roadmaps.json a repo keeps until it migrates."""
        base = self._roadmap(started="2026-10-27" if claim_on_main else None) if listed else self._roadmap(task="OTHER")
        (self.box.repo / rel).write_text(base)
        git(self.box.repo, "add", rel)
        git(self.box.repo, "commit", "-q", "-m", "chore(roadmap): sync claims from live branches" if claim_on_main else "chore: roadmap")
        bare = self.box.tmp / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)  # a clone of it checks out main, whatever this machine's init.defaultBranch
        git(self.box.repo, "remote", "add", "origin", str(bare))
        git(self.box.repo, "push", "-q", "-u", "origin", "main")
        git(self.box.worktree, "merge", "-q", "--ff-only", "main")
        if claim_on_branch and listed:
            (self.box.worktree / rel).write_text(self._roadmap(started="2026-10-27"))
            git(self.box.worktree, "add", rel)
            git(self.box.worktree, "commit", "-q", "-m", "chore(roadmap): 10SE.2 started, dated")
        else:
            (self.box.worktree / "work.txt").write_text("x\n")
            git(self.box.worktree, "add", "work.txt")
            git(self.box.worktree, "commit", "-q", "-m", "feat: work without a claim")
        git(self.box.worktree, "push", "-q", "-u", "origin", "feat/a")

    @staticmethod
    def _open(pr):
        return {str(pr): {"state": "OPEN", "reviewDecision": "", "reviewRequests": [], "latestReviews": [], "mergedAt": None}}

    @staticmethod
    def _merged(pr, base="main"):
        return {str(pr): {"state": "MERGED", "reviewDecision": "APPROVED", "reviewRequests": [], "latestReviews": [], "mergedAt": "2026-10-28T10:00:00Z", "baseRefName": base}}

    def test_a_pr_merged_into_a_non_main_base_is_checked_on_that_base(self):
        self._roadmap_repo_with_origin()
        git(self.box.repo, "branch", "develop", "main")
        git(self.box.repo, "push", "-q", "origin", "develop")
        git(self.box.repo, "checkout", "-q", "develop")
        git(self.box.repo, "merge", "-q", "--no-ff", "-m", "Merge feat/a", "feat/a")
        git(self.box.repo, "push", "-q", "origin", "develop")
        git(self.box.repo, "checkout", "-q", "main")
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 225, state="done")
        result = self._reconcile_with(self._gh(self._merged(225, base="develop")))
        self.assertNotIn("claim-missing", [item["kind"] for item in result["drift"]], "the claim is on origin/develop, where the PR merged")

    def test_a_pr_gh_says_merged_into_main_is_drift_when_the_claim_only_reached_develop(self):
        self._roadmap_repo_with_origin()
        git(self.box.repo, "branch", "develop", "main")
        git(self.box.repo, "checkout", "-q", "develop")
        git(self.box.repo, "merge", "-q", "--no-ff", "-m", "Merge feat/a", "feat/a")
        git(self.box.repo, "push", "-q", "origin", "develop")
        git(self.box.repo, "checkout", "-q", "main")
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 227, state="done")
        result = self._reconcile_with(self._gh(self._merged(227, base="main")))
        missing = [item for item in result["drift"] if item["kind"] == "claim-missing"]
        self.assertEqual(len(missing), 1)
        self.assertIn("on origin/main", missing[0]["detail"])

    def test_the_claim_check_fetches_so_a_merge_made_elsewhere_is_seen(self):
        self._roadmap_repo_with_origin()
        elsewhere = self.box.tmp / "elsewhere"
        subprocess.run(["git", "clone", "-q", str(self.box.tmp / "origin.git"), str(elsewhere)], check=True)
        git(elsewhere, "config", "user.email", "t@example.com")
        git(elsewhere, "config", "user.name", "t")
        git(elsewhere, "merge", "-q", "--no-ff", "-m", "Merge feat/a", "origin/feat/a")
        git(elsewhere, "push", "-q", "origin", "main")
        # this checkout's origin/main still predates the merge
        self.assertNotIn("started", subprocess.run(["git", "-C", str(self.box.repo), "show", "origin/main:.claude/roadmaps.json"], capture_output=True, text=True).stdout)
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 226, state="done")
        result = self._reconcile_with(self._gh(self._merged(226)))
        self.assertNotIn("claim-missing", [item["kind"] for item in result["drift"]])

    def test_an_open_pr_with_its_claim_on_the_branch_is_not_drift(self):
        self._roadmap_repo_with_origin()
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 220)
        result = self._reconcile_with(self._gh(self._open(220)))
        self.assertNotIn("claim-missing", [item["kind"] for item in result["drift"]])

    def test_a_merged_pr_whose_claim_reached_main_is_not_drift(self):
        self._roadmap_repo_with_origin()
        git(self.box.repo, "merge", "-q", "--no-ff", "-m", "Merge feat/a", "feat/a")
        git(self.box.repo, "push", "-q", "origin", "main")
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 221, state="done")
        result = self._reconcile_with(self._gh(self._merged(221)))
        self.assertNotIn("claim-missing", [item["kind"] for item in result["drift"]])

    def test_the_claim_is_read_from_a_goblin_scout_roadbook(self):
        """A repo on goblin-scout keeps .claude/roadbook.json: a claim there satisfies the check and its absence is drift."""
        self._roadmap_repo_with_origin(rel=".claude/roadbook.json")
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 230)
        result = self._reconcile_with(self._gh(self._open(230)))
        self.assertNotIn("claim-missing", [item["kind"] for item in result["drift"]])

    def test_a_missing_claim_in_a_goblin_scout_roadbook_is_drift(self):
        self._roadmap_repo_with_origin(claim_on_branch=False, rel=".claude/roadbook.json")
        git(self.box.repo, "merge", "-q", "--no-ff", "-m", "Merge feat/a", "feat/a")
        git(self.box.repo, "push", "-q", "origin", "main")
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 231, state="done")
        result = self._reconcile_with(self._gh(self._merged(231)))
        self.assertEqual([item["kind"] for item in result["drift"] if item["kind"] == "claim-missing"], ["claim-missing"], "roadbook.json was read")

    def test_a_roadbook_that_does_not_parse_falls_back_to_roadmaps_at_the_ref(self):
        """Review 5981937523: a roadbook.json at a ref that does not parse no longer stops the read of a valid roadmaps.json there."""
        self._roadmap_repo_with_origin()
        (self.box.repo / ".claude" / "roadbook.json").write_text("{ not a roadbook")
        git(self.box.repo, "add", ".claude/roadbook.json")
        git(self.box.repo, "commit", "-q", "-m", "chore: a broken roadbook beside the old one")
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        row = mc_module.roadmap_task(self.box.repo, "10SE.2", "HEAD")
        self.assertIsInstance(row, dict, "the old roadmaps.json is read when the new name does not parse")
        self.assertEqual(row["id"], "10SE.2")

    def test_a_ref_cut_before_the_roadbook_move_is_read_under_the_old_name(self):
        """The main checkout has moved roadmaps.json to roadbook.json, but the refs reconcile reads still carry the old file:
        the old name is read at the ref, so the missing claim is still found."""
        self._roadmap_repo_with_origin(claim_on_branch=False)
        git(self.box.repo, "mv", ".claude/roadmaps.json", ".claude/roadbook.json")
        git(self.box.repo, "commit", "-q", "-m", "chore(roadbook): move to roadbook.json")  # local only: origin/main and origin/feat/a still have roadmaps.json
        self.assertFalse((self.box.repo / ".claude" / "roadmaps.json").exists())
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 232)
        result = self._reconcile_with(self._gh(self._open(232)))
        missing = [item for item in result["drift"] if item["kind"] == "claim-missing"]
        self.assertEqual(len(missing), 1, "origin/feat/a holds only roadmaps.json, and its missing claim is still seen")
        self.assertIn("origin/feat/a", missing[0]["detail"])

    def test_a_merged_pr_with_no_claim_on_main_is_drift(self):
        self._roadmap_repo_with_origin(claim_on_branch=False)
        git(self.box.repo, "merge", "-q", "--no-ff", "-m", "Merge feat/a", "feat/a")
        git(self.box.repo, "push", "-q", "origin", "main")
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 222, state="done")
        result = self._reconcile_with(self._gh(self._merged(222)))
        missing = [item for item in result["drift"] if item["kind"] == "claim-missing"]
        self.assertEqual(len(missing), 1)
        self.assertIn("on origin/main", missing[0]["detail"])
        self.assertEqual(missing[0]["pr"], 222)

    def test_an_open_pr_whose_pushed_branch_has_no_claim_is_drift_naming_the_branch(self):
        self._roadmap_repo_with_origin(claim_on_branch=False)
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 223)
        result = self._reconcile_with(self._gh(self._open(223)))
        missing = [item for item in result["drift"] if item["kind"] == "claim-missing"]
        self.assertEqual(len(missing), 1)
        self.assertIn("on origin/feat/a", missing[0]["detail"])

    def test_trunk_sync_projects_do_not_flag_an_open_pr_for_a_missing_branch_claim(self):
        self._roadmap_repo_with_origin(claim_on_branch=False)
        config_path = self.box.repo / ".claude" / "goblin-warband.json"
        config = json.loads(config_path.read_text())
        config["claims"] = "trunk-sync"
        config_path.write_text(json.dumps(config))
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 223)
        result = self._reconcile_with(self._gh(self._open(223)))
        self.assertNotIn("claim-missing", [item["kind"] for item in result["drift"]])

    def test_a_held_approval_is_named_held_until_released(self):
        self._watching_session(265)
        run_path = list(self.box.ledger_root.glob("*/run.json"))[0]
        run = json.loads(run_path.read_text())
        run.setdefault("pending", []).append({"id": "a2", "n": 1, "kind": "approval", "pr": 265, "text": "t", "session_id": "crew-1", "head": "", "status": "open", "at": 1.0})
        run_path.write_text(json.dumps(run))
        self.box.mc("pending", "hold", "265", "--text", "every review comment first", session="coord-1")
        kinds = [item["kind"] for item in self._reconcile_with(self._gh(self._open(265)))["drift"]]
        self.assertIn("approved-held", kinds)
        self.assertNotIn("approved-unlanded", kinds)
        self.box.mc("pending", "release", "265", session="coord-1")
        kinds = [item["kind"] for item in self._reconcile_with(self._gh(self._open(265)))["drift"]]
        self.assertIn("approved-unlanded", kinds)

    def test_a_claim_that_reached_main_under_another_subject_satisfies_a_merged_pr(self):
        """A sync batch or a `done` batch carries the claim to the trunk; the roadmap's state counts, not the commit subject."""
        self._roadmap_repo_with_origin(claim_on_branch=False, claim_on_main=True)
        git(self.box.repo, "merge", "-q", "--no-ff", "-m", "Merge feat/a", "feat/a")
        git(self.box.repo, "push", "-q", "origin", "main")
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 228, state="done")
        result = self._reconcile_with(self._gh(self._merged(228)))
        self.assertEqual([item["kind"] for item in result["drift"]], ["roadmap-stale"], "the claim is satisfied; only the post-merge roadmap sync remains")

    def test_an_open_branch_without_its_own_claim_is_in_order_once_main_has_the_claim(self):
        """A branch rebased past its claim commit, as the run asks once the trunk carries the claim, is not drift."""
        self._roadmap_repo_with_origin(claim_on_branch=False, claim_on_main=True)
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 229)
        result = self._reconcile_with(self._gh(self._open(229)))
        self.assertEqual([item["kind"] for item in result["drift"]], [])

    def test_an_unlisted_task_is_named_once_and_is_not_claim_drift(self):
        self._roadmap_repo_with_origin(claim_on_branch=False, listed=False)
        self.box.start()
        self._crew_with_pr("UXR", "crew-1", "feat/a", 230)
        result = self._reconcile_with(self._gh(self._open(230)))
        self.assertEqual([item["kind"] for item in result["drift"]], ["unlisted"])
        self.assertIn("no claim expected", result["drift"][0]["detail"])
        self.assertEqual(result["drift"][0]["task"], "UXR")

    def test_a_merged_pr_line_says_merged_once(self):
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 231, state="done")
        result = self._reconcile_with(self._gh(self._merged(231)))
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        import io
        from contextlib import redirect_stdout
        out = io.StringIO()
        with redirect_stdout(out):
            mc_module.print_reconcile(result)
        self.assertIn("- #231 (10SE.2): merged\n", out.getvalue())
        self.assertNotIn("merged, merged", out.getvalue())

    # retire: reclaiming a finished crew worktree while the run goes on

    def _retire_with(self, fake_sh, *cli):
        """`warband.py retire` in-process, with gh faked and du/lsof answered by the same fake (a non-gh argv returns 1, which lsof treats as 'nothing listed')."""
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        real = (mc_module.sh, mc_module.LEDGER_ROOT, mc_module.SESSIONS_DIR)
        mc_module.sh = fake_sh
        mc_module.LEDGER_ROOT = self.box.ledger_root
        mc_module.SESSIONS_DIR = self.box.sessions
        import io
        from contextlib import redirect_stdout
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                code = mc_module.main(["--cwd", str(self.box.repo), "--session", "coord-1", "retire", *cli])
        finally:
            mc_module.sh, mc_module.LEDGER_ROOT, mc_module.SESSIONS_DIR = real
        return code, out.getvalue()

    def _closed_crew(self, pr=240, state="done"):
        """A crew session with a PR, joined from the worktree, reported and then closed (gone from the registry)."""
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        self.box.mc("report", "--state", state, "--pr", str(pr), session="crew-1", cwd=self.box.worktree)
        (self.box.sessions / "crew-1.json").unlink()

    def test_retire_removes_the_worktree_prunes_and_deletes_the_merged_branch(self):
        self._closed_crew()
        git(self.box.repo, "merge", "-q", "--no-ff", "-m", "Merge feat/a", "feat/a")
        code, out = self._retire_with(self._gh(self._merged(240)), "10SE.2")
        self.assertEqual(code, 0, out)
        self.assertIn("retired 10SE.2", out)
        self.assertIn("branch feat/a deleted", out)
        self.assertFalse(self.box.worktree.exists())
        self.assertNotIn("feat/a", subprocess.run(["git", "-C", str(self.box.repo), "branch", "--list", "feat/a"], capture_output=True, text=True).stdout)
        rows = list((self.box.ledger_root).glob("*/sessions/crew-1.json"))
        row = json.loads(rows[0].read_text())
        self.assertEqual(row["retired"]["by"], "coordinator")
        self.assertEqual(Path(row["retired"]["worktree"]).resolve(), self.box.worktree.resolve())
        self.assertTrue(row["retired"]["branch_deleted"])
        log = (rows[0].parent.parent / "log.jsonl").read_text()
        self.assertIn('"event": "retire"', log)

    def test_retire_keeps_a_branch_git_will_not_fast_delete(self):
        """A PR squash-merged on GitHub leaves a local branch `-d` refuses; retire reports that and never forces."""
        self._closed_crew()
        (self.box.worktree / "work.txt").write_text("x\n")
        git(self.box.worktree, "add", "work.txt")
        git(self.box.worktree, "commit", "-q", "-m", "feat: work")
        code, out = self._retire_with(self._gh(self._merged(240)), "10SE.2")
        self.assertEqual(code, 0, out)
        self.assertFalse(self.box.worktree.exists())
        self.assertIn("branch feat/a kept", out)
        self.assertIn("feat/a", subprocess.run(["git", "-C", str(self.box.repo), "branch", "--list", "feat/a"], capture_output=True, text=True).stdout)

    def test_retire_dry_run_changes_nothing(self):
        self._closed_crew()
        code, out = self._retire_with(self._gh(self._merged(240)), "10SE.2", "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("dry run", out)
        self.assertIn("would remove worktree", out)
        self.assertTrue(self.box.worktree.exists())
        rows = list((self.box.ledger_root).glob("*/sessions/crew-1.json"))
        self.assertNotIn("retired", json.loads(rows[0].read_text()))

    def test_retire_refuses_a_live_session_an_unfinished_row_an_open_pr_and_a_dirty_tree(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        self.box.mc("report", "--state", "done", "--pr", "240", session="crew-1", cwd=self.box.worktree)
        code, out = self._retire_with(self._gh(self._merged(240)), "10SE.2")
        self.assertEqual(code, 1)
        self.assertIn("still live", out)
        (self.box.sessions / "crew-1.json").unlink()
        self.box.mc("report", "--for", "10SE.2", "--state", "pr-ready", session="coord-1")
        code, out = self._retire_with(self._gh(self._merged(240)), "10SE.2")
        self.assertEqual(code, 1)
        self.assertIn("not done", out)
        # a different PR number for the open case, since pr_facts caches an answer for a minute
        self.box.mc("report", "--for", "10SE.2", "--state", "done", "--pr", "241", session="coord-1")
        code, out = self._retire_with(self._gh(self._open(241)), "10SE.2")
        self.assertEqual(code, 1)
        self.assertIn("is open on GitHub", out)
        self.box.mc("report", "--for", "10SE.2", "--pr", "240", session="coord-1")
        (self.box.worktree / "scratch.txt").write_text("x\n")
        code, out = self._retire_with(self._gh(self._merged(240)), "10SE.2")
        self.assertEqual(code, 1)
        self.assertIn("is dirty", out)
        self.assertTrue(self.box.worktree.exists())

    def test_retire_refuses_while_an_open_pr_is_stacked_on_the_branch(self):
        self._closed_crew()
        upper = self.box.repo / ".claude" / "worktrees" / "crew-b"
        git(self.box.repo, "worktree", "add", "-q", "-b", "feat/b", str(upper), "feat/a")
        self.box.register("crew-2", "10se3", str(upper))
        self.box.mc("crew", "add", "--task", "10SE.3", "--branch", "feat/b", "--worktree", str(upper), session="coord-1")
        self.box.mc("join", "--task", "10SE.3", "--branch", "feat/b", session="crew-2", cwd=upper)
        self.box.mc("report", "--state", "pr-ready", "--pr", "241", session="crew-2", cwd=upper)
        answers = {**self._merged(240), **self._open(241)}
        answers["241"]["baseRefName"] = "feat/a"
        code, out = self._retire_with(self._gh(answers), "10SE.2")
        self.assertEqual(code, 1)
        self.assertIn("#241 (10SE.3) is based on feat/a", out)
        self.assertTrue(self.box.worktree.exists())

    def test_retire_refuses_while_something_runs_in_the_worktree_and_lists_the_kill_as_a_need(self):
        self._closed_crew()
        gh = self._gh(self._merged(240))

        def fake_sh(argv, timeout=8, cwd=None):
            if argv[:2] == ["lsof", "-d"]:
                return 0, f"p4242\ncnode\nn{self.box.worktree}/apps/api\np1\nclaunchd\nn/\n"
            return gh(argv, timeout, cwd)

        code, out = self._retire_with(fake_sh, "10SE.2")
        self.assertEqual(code, 1)
        self.assertIn("4242 (node)", out)
        self.assertIn("`kill 4242`", out)
        self.assertTrue(self.box.worktree.exists())
        needs = json.loads(self.box.mc("needs", "list", session="coord-1").stdout)
        self.assertEqual(needs[-1]["command"], "kill 4242")
        self.assertEqual(needs[-1]["task"], "10SE.2")

    def test_retire_asks_gh_afresh_rather_than_trusting_a_cached_open_state(self):
        """A merge made a moment ago: reconcile cached the PR as open, retire must still see it merged."""
        self._closed_crew()
        self._reconcile_with(self._gh(self._open(240)))  # fills pr-facts.json with OPEN, well inside the cache window
        code, out = self._retire_with(self._gh(self._merged(240)), "10SE.2")
        self.assertEqual(code, 0, out)
        self.assertFalse(self.box.worktree.exists())

    def test_retire_twice_says_when_it_was_retired(self):
        self._closed_crew()
        self._retire_with(self._gh(self._merged(240)), "10SE.2")
        code, out = self._retire_with(self._gh(self._merged(240)), "10SE.2")
        self.assertEqual(code, 1)
        self.assertIn("was retired at", out)

    def test_reconcile_nudges_a_merged_done_row_whose_worktree_lingers(self):
        self._closed_crew()
        result = self._reconcile_with(self._gh(self._merged(240)))
        kinds = [item["kind"] for item in result["drift"]]
        self.assertIn("unretired", kinds)
        nudge = next(item for item in result["drift"] if item["kind"] == "unretired")
        self.assertIn("`warband.py retire 10SE.2`", nudge["detail"])
        self.assertIn("worktree still present", nudge["detail"])
        # retired, the nudge goes
        self._retire_with(self._gh(self._merged(240)), "10SE.2")
        result = self._reconcile_with(self._gh(self._merged(240)))
        self.assertNotIn("unretired", [item["kind"] for item in result["drift"]])

    def test_reconcile_does_not_nudge_a_fresh_merge(self):
        self._closed_crew()
        fresh = self._merged(240)
        fresh["240"]["mergedAt"] = "2999-01-01T00:00:00Z"
        result = self._reconcile_with(self._gh(fresh))
        self.assertNotIn("unretired", [item["kind"] for item in result["drift"]])

    # classify and watch: the project's mode and the PR watcher

    def _module(self, fake_sh):
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        real = (mc_module.sh, mc_module.LEDGER_ROOT, mc_module.SESSIONS_DIR)
        mc_module.sh = fake_sh
        mc_module.LEDGER_ROOT = self.box.ledger_root
        mc_module.SESSIONS_DIR = self.box.sessions
        return mc_module, real

    @staticmethod
    def _restore(mc_module, real):
        mc_module.sh, mc_module.LEDGER_ROOT, mc_module.SESSIONS_DIR = real

    @staticmethod
    def _gh_list(prs):
        def fake_sh(argv, timeout=8, cwd=None):
            if argv[:3] == ["gh", "pr", "list"]:
                return 0, json.dumps(prs)
            return 1, "not gh"
        return fake_sh

    def test_classify_reads_solo_from_one_author_and_no_reviews(self):
        mc_module, real = self._module(self._gh_list([{"number": 1, "author": {"login": "t"}, "reviews": []}]))
        try:
            result = mc_module.classify(self.box.repo, None)
        finally:
            self._restore(mc_module, real)
        self.assertEqual(result["mode"], "solo")
        self.assertEqual(result["source"], "inferred")
        self.assertIsNone(result["hours"])
        self.assertEqual(result["authors"], ["t"])

    def test_classify_reads_collaborative_from_a_second_author_or_a_review_by_another(self):
        git(self.box.repo, "commit", "-q", "--allow-empty", "-m", "x", "--author", "Other <o@example.com>")
        git(self.box.repo, "commit", "-q", "--allow-empty", "-m", "bot", "--author", "dependabot[bot] <bot@users.noreply.github.com>")
        mc_module, real = self._module(self._gh_list([]))
        try:
            by_authors = mc_module.classify(self.box.repo, None)
            git(self.box.repo, "reset", "-q", "--hard", "HEAD~2")
            reviewed = [{"number": 1, "author": {"login": "t"}, "reviews": [{"author": {"login": "jaz"}, "state": "APPROVED", "submittedAt": "2026-10-28T10:30:00Z"}]}]
            mc_module.sh = self._gh_list(reviewed)
            by_review = mc_module.classify(self.box.repo, None)
        finally:
            self._restore(mc_module, real)
        self.assertEqual(by_authors["mode"], "collaborative")
        self.assertEqual(sorted(by_authors["authors"]), ["Other", "t"], "the bot is not an author")
        self.assertEqual(by_review["mode"], "collaborative")
        self.assertEqual(by_review["reviewed_by_others"], 1)
        self.assertEqual(by_review["hours"]["days"], [0, 1, 2, 3, 4], "one review is too few to infer hours, so the weekday default stands")

    def test_classify_ignores_a_review_by_a_github_app_whose_login_lost_its_bot_suffix(self):
        """goblin-mode read as collaborative on 17 November 2026: `gh pr list` reported `graphify-labs[bot]` as `graphify-labs`,
        so the name check passed it as a person. GraphQL's `__typename` Bot is what tells the account apart, and one aliased
        query answers for every reviewed PR, so a team repo does not pay one gh call per PR."""
        reviewed = [
            {"number": 71, "author": {"login": "t"}, "reviews": [{"author": {"login": "graphify-labs"}, "state": "COMMENTED", "submittedAt": "2026-11-15T09:55:37Z"}]},
            {"number": 72, "author": {"login": "t"}, "reviews": [{"author": {"login": "jaz"}, "state": "APPROVED", "submittedAt": "2026-11-15T10:55:37Z"}]},
        ]
        graphql = {"data": {"repository": {
            "p71": {"reviews": {"nodes": [{"author": {"__typename": "Bot", "login": "graphify-labs"}}]}},
            "p72": {"reviews": {"nodes": [{"author": {"__typename": "User", "login": "jaz"}}]}},
        }}}
        calls = []

        def fake_sh(argv, timeout=8, cwd=None):
            if argv[:3] == ["gh", "pr", "list"]:
                return 0, json.dumps(reviewed)
            if argv[:3] == ["gh", "api", "graphql"]:
                calls.append(argv)
                return 0, json.dumps(graphql)
            return 1, "not gh"

        mc_module, real = self._module(fake_sh)
        try:
            as_bot = mc_module.classify(self.box.repo, None)
            one_call_for_two_prs = len(calls)
            solo_sample = [reviewed[0]]
            reviewed[:] = solo_sample
            only_bot = mc_module.classify(self.box.repo, None)
            reviewed[:] = [
                {"number": 71, "author": {"login": "t"}, "reviews": [{"author": {"login": "graphify-labs"}, "state": "COMMENTED", "submittedAt": "2026-11-15T09:55:37Z"}]},
                {"number": 72, "author": {"login": "t"}, "reviews": [{"author": {"login": "jaz"}, "state": "APPROVED", "submittedAt": "2026-11-15T10:55:37Z"}]},
            ]
            graphql["data"]["repository"]["p72"]["reviews"]["nodes"][0]["author"]["__typename"] = "Bot"
            graphql["data"]["repository"]["p71"]["reviews"]["nodes"][0]["author"]["__typename"] = "User"
            as_user = mc_module.classify(self.box.repo, None)
            mc_module.sh = lambda argv, timeout=8, cwd=None: (0, json.dumps(reviewed)) if argv[:3] == ["gh", "pr", "list"] else (1, "graphql down")
            lookup_failed = mc_module.classify(self.box.repo, None)
        finally:
            self._restore(mc_module, real)
        self.assertEqual(one_call_for_two_prs, 1, "two reviewed PRs share one aliased query")
        self.assertEqual((as_bot["mode"], as_bot["reviewed_by_others"]), ("collaborative", 1), "jaz is a user on PR 72, so only PR 71 drops out")
        self.assertEqual((only_bot["mode"], only_bot["reviewed_by_others"]), ("solo", 0))
        self.assertEqual((as_user["mode"], as_user["reviewed_by_others"]), ("collaborative", 1), "PR 71 is now a user and PR 72 a bot")
        self.assertEqual(lookup_failed["mode"], "collaborative", "an unanswered type lookup keeps the old reading rather than guessing")
        self.assertEqual(lookup_failed["reviewed_by_others"], 2)

    def test_one_unresolvable_pull_request_costs_only_its_own_answer_in_the_bot_lookup(self):
        """gh exits 1 when any alias resolves to null, with the other aliases' data still on stdout and its own error line after it.
        PR 71 is a bot and must still drop out when PR 72 cannot be resolved; PR 72 stays counted as a person."""
        reviewed = [
            {"number": 71, "author": {"login": "t"}, "reviews": [{"author": {"login": "graphify-labs"}, "state": "COMMENTED", "submittedAt": "2026-11-15T09:55:37Z"}]},
            {"number": 72, "author": {"login": "t"}, "reviews": [{"author": {"login": "jaz"}, "state": "APPROVED", "submittedAt": "2026-11-15T10:55:37Z"}]},
        ]
        partial = {"data": {"repository": {"p71": {"reviews": {"nodes": [{"author": {"__typename": "Bot", "login": "graphify-labs"}}]}}, "p72": None}},
                   "errors": [{"type": "NOT_FOUND", "path": ["repository", "p72"], "message": "Could not resolve to a PullRequest with the number of 72."}]}

        queries = []

        def fake_sh(argv, timeout=8, cwd=None):
            if argv[:3] == ["gh", "pr", "list"]:
                return 0, json.dumps(reviewed)
            if argv[:3] == ["gh", "api", "graphql"]:
                queries.append(next(a for a in argv if a.startswith("query=")))
                return 1, json.dumps(partial) + "gh: Could not resolve to a PullRequest with the number of 72."
            return 1, "not gh"

        mc_module, real = self._module(fake_sh)
        try:
            result = mc_module.classify(self.box.repo, None)
            bots = mc_module.gh_bot_reviewers(self.box.repo, [71, 72, True, None, "73"])
        finally:
            self._restore(mc_module, real)
        self.assertEqual((result["mode"], result["reviewed_by_others"]), ("collaborative", 1), "PR 71 drops out; PR 72 keeps its reviewer")
        self.assertEqual(bots, {71: {"graphify-labs"}}, "an unresolved alias is absent, and a bool or a string is never a PR number")
        self.assertIn("p71:", queries[-1])
        self.assertIn("p72:", queries[-1])
        for never in ("pTrue", "p73", "pNone"):
            self.assertNotIn(never, queries[-1], "a bool, a string and None are left out of the query, not sent for GraphQL to refuse")

    def test_a_bot_author_node_without_a_login_is_skipped_rather_than_raised_on(self):
        """A deleted account comes back with a null login, and a malformed node may lack the key; neither may escape into classify."""
        graphql = {"data": {"repository": {"p71": {"reviews": {"nodes": [
            {"author": {"__typename": "Bot", "login": None}},
            {"author": {"__typename": "Bot"}},
            {"author": None},
            {"author": {"__typename": "Bot", "login": "graphify-labs"}},
        ]}}}}}
        mc_module, real = self._module(lambda argv, timeout=8, cwd=None: (0, json.dumps(graphql)))
        try:
            bots = mc_module.gh_bot_reviewers(self.box.repo, [71])
        finally:
            self._restore(mc_module, real)
        self.assertEqual(bots, {71: {"graphify-labs"}})

    def test_the_bot_lookup_sends_a_literal_repository_name_as_a_string_while_git_is_broken(self):
        """`-F` turns `2048`, `true` and `null` into JSON types, which GraphQL then refuses for a `String!`; only gh's own
        `{owner}` and `{repo}` placeholders need `-F`, so a slug read from the config file goes through `-f`."""
        seen = []

        def fake_sh(argv, timeout=8, cwd=None):
            seen.append(argv)
            return 1, "graphql down"

        mc_module, real = self._module(fake_sh)
        real_problem, real_remote = mc_module.git_problem, mc_module.remote_repo
        try:
            mc_module.git_problem = lambda: "git is not working"
            mc_module.remote_repo = lambda main: "x/2048"
            mc_module.gh_bot_reviewers(self.box.repo, [71])
            literal = seen[-1]
            mc_module.git_problem = lambda: None
            mc_module.gh_bot_reviewers(self.box.repo, [71])
            placeholders = seen[-1]
        finally:
            mc_module.git_problem, mc_module.remote_repo = real_problem, real_remote
            self._restore(mc_module, real)
        self.assertIn("name=2048", literal)
        self.assertEqual(literal[literal.index("name=2048") - 1], "-f")
        self.assertEqual(literal[literal.index("owner=x") - 1], "-f")
        self.assertEqual(placeholders[placeholders.index("owner={owner}") - 1], "-F")
        self.assertEqual(placeholders[placeholders.index("name={repo}") - 1], "-F")

    def test_classify_merges_one_person_under_two_addresses_or_two_spellings_and_ignores_a_claude_coauthor(self):
        """goblin-mode read as collaborative on 30 October 2026: Jason under two emails plus Claude's noreply address made three authors.
        The mirror case, one email under two spellings of the name, chains through the shared address to the same person."""
        git(self.box.repo, "commit", "-q", "--allow-empty", "-m", "work", "--author", "t <t-at-work@example.com>")
        git(self.box.repo, "commit", "-q", "--allow-empty", "-m", "web", "--author", "T. Tester <t-at-work@example.com>")
        git(self.box.repo, "commit", "-q", "--allow-empty", "-m", "web again", "--author", "T. Tester <t@example.com>")
        git(self.box.repo, "commit", "-q", "--allow-empty", "-m", "assisted", "--author", "Claude <noreply@anthropic.com>")
        mc_module, real = self._module(self._gh_list([]))
        try:
            result = mc_module.classify(self.box.repo, None)
            authors = mc_module.git_authors(self.box.repo)
        finally:
            self._restore(mc_module, real)
        self.assertEqual(result["mode"], "solo")
        self.assertEqual(result["authors"], ["T. Tester"], "one person, named the way they commit most often")
        self.assertEqual(authors[0]["commits"], 4, "the init commit and the three new ones")

    def test_git_authors_keeps_two_people_apart(self):
        git(self.box.repo, "commit", "-q", "--allow-empty", "-m", "theirs", "--author", "Other <o@example.com>")
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        self.assertEqual(sorted(a["name"] for a in mc_module.git_authors(self.box.repo)), ["Other", "t"])

    def test_reconcile_nudges_roadmap_maintain_once_a_crew_pr_merges(self):
        """The merge landed the work; the roadmap on the trunk still reads todo until /roadmap:maintain runs."""
        self._roadmap_repo_with_origin(claim_on_branch=False, claim_on_main=True)
        git(self.box.repo, "merge", "-q", "--no-ff", "-m", "Merge feat/a", "feat/a")
        git(self.box.repo, "push", "-q", "origin", "main")
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 270, state="done")
        result = self._reconcile_with(self._gh(self._merged(270)))
        stale = [item for item in result["drift"] if item["kind"] == "roadmap-stale"]
        self.assertEqual(len(stale), 1)
        self.assertIn("reads todo on the roadbook at origin/main", stale[0]["detail"])
        self.assertIn("/goblin-scout:tend-roadbook", stale[0]["detail"])
        # maintain ran and the trunk says done: the nudge goes
        (self.box.repo / ".claude" / "roadmaps.json").write_text(self._roadmap(started="2026-10-27", status="done"))
        git(self.box.repo, "commit", "-q", "-am", "chore(roadmap): 10SE.2 done")
        git(self.box.repo, "push", "-q", "origin", "main")
        result = self._reconcile_with(self._gh(self._merged(270)))
        self.assertNotIn("roadmap-stale", [item["kind"] for item in result["drift"]])

    def test_classify_takes_the_stated_answer_and_notes_a_disagreement(self):
        config = {"collaboration": {"mode": "collaborative", "hours": {"start": "08:30", "end": "17:00", "days": "mon-thu"}}}
        mc_module, real = self._module(self._gh_list([]))
        try:
            stated = mc_module.classify(self.box.repo, config)
            (self.box.repo / ".claude" / "goblin-warband.local.json").write_text(json.dumps({"collaboration": {"mode": "solo"}}))
            local = mc_module.classify(self.box.repo, config)
        finally:
            self._restore(mc_module, real)
        self.assertEqual(stated["mode"], "collaborative")
        self.assertEqual(stated["source"], "config")
        self.assertEqual(stated["hours"], {"start": "08:30", "end": "17:00", "days": [0, 1, 2, 3]})
        self.assertTrue(any("history alone reads solo" in line for line in stated["evidence"]))
        self.assertEqual(local["mode"], "solo")
        self.assertEqual(local["source"], "local config")

    def test_helpers_window_and_snapshot_changes(self):
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        hours = {"start": "09:00", "end": "18:00", "days": [0, 1, 2, 3, 4]}
        import calendar
        # a Wednesday at 10:00 and at 22:00 local
        wed = calendar.timegm(time.strptime("2026-10-28 00:00", "%Y-%m-%d %H:%M")) + time.timezone
        lt = time.localtime(wed)
        wed = wed - (lt.tm_hour * 3600 + lt.tm_min * 60)
        self.assertTrue(mc_module.in_window(hours, wed + 10 * 3600))
        self.assertFalse(mc_module.in_window(hours, wed + 22 * 3600))
        self.assertTrue(mc_module.in_window(None, wed + 22 * 3600))
        opens = mc_module.window_opens(hours, wed + 22 * 3600)
        self.assertEqual(time.localtime(opens).tm_hour, 9)
        self.assertTrue(mc_module.in_window(hours, opens))
        before = {"state": "OPEN", "decision": "", "reviews": [], "comments": 0, "review_comments": 0, "checks": {"ci": "in_progress"}}
        after = {"state": "OPEN", "decision": "CHANGES_REQUESTED", "reviews": [{"login": "jaz", "state": "CHANGES_REQUESTED", "at": "t"}], "comments": 1, "review_comments": 3, "checks": {"ci": "success", "lint": "failure"}}
        changes = mc_module.snapshot_changes(before, after)
        self.assertEqual(changes, ["review decision none -> CHANGES_REQUESTED", "review by jaz: changes requested", "3 new review comments", "1 new comment", "check ci: in_progress -> success", "check lint: new -> failure"])
        self.assertEqual(mc_module.snapshot_changes(after, after), [])
        self.assertEqual(mc_module.parse_days("mon-fri"), [0, 1, 2, 3, 4])
        self.assertEqual(mc_module.parse_days(["sat", "sun"]), [5, 6])
        self.assertEqual(mc_module.parse_days("fri-mon"), [0, 4, 5, 6])

    @staticmethod
    def _gh_watch(views, review_comments=""):
        """gh answers `pr view` from a queue of snapshots (the last repeats) and the paginated review-comment ids, one per line."""
        queue = list(views)

        def fake_sh(argv, timeout=8, cwd=None):
            if argv[:3] == ["gh", "pr", "view"]:
                view = queue.pop(0) if len(queue) > 1 else queue[0]
                return 0, json.dumps(view)
            if argv[:2] == ["gh", "api"]:
                return 0, review_comments
            if argv[:3] == ["gh", "pr", "list"]:
                return 0, "[]"
            return 1, "not gh"
        return fake_sh

    def _watch(self, fake_sh, *cli, session="crew-1"):
        mc_module, real = self._module(fake_sh)
        import io
        from contextlib import redirect_stdout
        out = io.StringIO()
        os.environ["CLAUDE_CODE_SESSION_ID"] = session
        try:
            with redirect_stdout(out):
                try:
                    code = mc_module.main(["--cwd", str(self.box.worktree), "watch", "--interval", "0.01", *cli])
                except SystemExit as exited:  # a signalled watcher exits 128 plus the signal after its `finally` has said so
                    code = exited.code
        finally:
            os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
            self._restore(mc_module, real)
        return code, out.getvalue()

    @staticmethod
    def _view(state="OPEN", decision="", reviews=(), checks=(), comments=0):
        return {"state": state, "reviewDecision": decision, "reviews": list(reviews), "comments": [{}] * comments,
                "statusCheckRollup": [{"name": n, "status": "COMPLETED", "conclusion": c} for n, c in checks], "mergedAt": None, "url": "u", "title": "t"}

    def test_watch_takes_a_baseline_then_exits_on_the_first_change_and_records_it(self):
        self.box.start()
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        self.box.mc("report", "--state", "pr-ready", "--pr", "250", session="crew-1", cwd=self.box.worktree)
        views = [self._view(checks=[("ci", "SUCCESS")]), self._view(checks=[("ci", "SUCCESS")]), self._view(checks=[("ci", "SUCCESS")], reviews=[{"author": {"login": "jaz"}, "state": "APPROVED", "submittedAt": "x"}], decision="APPROVED")]
        code, out = self._watch(self._gh_watch(views))
        self.assertEqual(code, 0, out)
        self.assertIn("#250 changed (review decision none -> APPROVED; review by jaz: approved)", out)
        rows = list(self.box.ledger_root.glob("*/sessions/crew-1.json"))
        watch = json.loads(rows[0].read_text())["watch"]
        self.assertEqual(watch["pr"], 250)
        self.assertEqual(watch["status"], "changed")
        self.assertEqual(watch["seen"]["decision"], "APPROVED")
        # the next watch starts from what it last saw, so the same change is not reported twice
        code, out = self._watch(self._gh_watch([views[-1], views[-1], self._view(state="MERGED", decision="APPROVED", checks=[("ci", "SUCCESS")], reviews=views[-1]["reviews"])]))
        self.assertEqual(code, 0, out)
        self.assertIn("state OPEN -> MERGED", out)
        self.assertIn("watch ended", out)
        self.assertNotIn("review by jaz", out)

    def test_watch_on_a_solo_project_with_no_checks_declines_and_once_prints_the_pr(self):
        self.box.start()
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        self.box.mc("report", "--state", "pr-ready", "--pr", "251", session="crew-1", cwd=self.box.worktree)
        code, out = self._watch(self._gh_watch([self._view()]))
        self.assertEqual(code, 0, out)
        self.assertIn("solo project and no checks", out)
        code, out = self._watch(self._gh_watch([self._view(checks=[("ci", "SUCCESS")])]), "--once", "--pr", "252")
        self.assertEqual(code, 0, out)
        self.assertIn("#252: open, decision none, no reviews, 0 comments, 0 review comments, 1 check: success", out)

    def test_watch_holds_a_review_outside_the_team_hours_and_still_exits_on_a_merge(self):
        self.box.start()
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        self.box.mc("report", "--state", "pr-ready", "--pr", "253", session="crew-1", cwd=self.box.worktree)
        run_path = next(self.box.ledger_root.glob("*/run.json"))
        run = json.loads(run_path.read_text())
        # a window that is never open: start and end coincide, so no minute of any day satisfies start <= now < end
        # (a 00:00 to 00:01 window was open for the one minute a suite running across midnight polled in, on 5 November 2026)
        run["collaboration"] = {"mode": "collaborative", "hours": {"start": "00:00", "end": "00:00", "days": [0, 1, 2, 3, 4, 5, 6]}}
        run_path.write_text(json.dumps(run))
        reviewed = self._view(reviews=[{"author": {"login": "jaz"}, "state": "COMMENTED", "submittedAt": "x"}])
        code, out = self._watch(self._gh_watch([self._view(), reviewed, reviewed]), "--max-minutes", "0.001")
        self.assertEqual(code, 0, out)
        self.assertIn("holding until the team's hours open", out)
        self.assertIn("review by jaz: commented", out)
        rows = list(self.box.ledger_root.glob("*/sessions/crew-1.json"))
        watch = json.loads(rows[0].read_text())["watch"]
        self.assertEqual((watch["status"], watch["pid"]), ("idle", None), "the process has exited, so the board must not count a watcher")
        self.assertIn("review by jaz: commented", "; ".join(watch["last_change"]), "the held change is kept for the coordinator")
        merged = self._view(state="MERGED", reviews=reviewed["reviews"])
        code, out = self._watch(self._gh_watch([reviewed, merged, merged]))
        self.assertEqual(code, 0, out)
        self.assertIn("watch ended", out)

    def test_start_records_the_classification_and_a_flag_overrides_it(self):
        self.box.start()
        run = json.loads(next(self.box.ledger_root.glob("*/run.json")).read_text())
        self.assertEqual(run["collaboration"]["mode"], "solo")
        self.assertEqual(run["collaboration"]["authors"], ["t"])
        self.box.mc("end", session="coord-1")
        self.box.mc("start", "--name", "two", "--collaboration", "collaborative", session="coord-1")
        run = json.loads(next(self.box.ledger_root.glob("*/run.json")).read_text())
        self.assertEqual(run["collaboration"]["mode"], "collaborative")
        self.assertEqual(run["collaboration"]["source"], "flag")
        self.assertEqual(run["collaboration"]["hours"]["start"], "09:00")
        said = self.box.mc("classify", session="coord-1").stdout
        self.assertTrue(said.startswith("collaborative (flag); team hours: 09:00 to 18:00"), said)

    def test_reconcile_says_solo_where_no_reviewer_is_named(self):
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 254)
        result = self._reconcile_with(self._gh(self._open(254)))
        self.assertEqual(result["prs"][0]["waiting_on"], "solo project; the merge is the user's")

    # session continuity: /clear rebinds, fresh crew adopts, scheduled state and decisions live in the ledger

    def _run_json(self):
        return json.loads(next(self.box.ledger_root.glob("*/run.json")).read_text())

    def test_a_cleared_coordinator_is_offered_as_a_rebind_and_adopts_from_its_own_process(self):
        self.box.start()
        # /clear: same pid and socket, new session id; the old row is gone from the registry
        (self.box.sessions / "coord-1.json").unlink()
        self.box.register("coord-2", "mission control", str(self.box.repo))
        (self.box.sessions / "coord-2.json").write_text(json.dumps({**json.loads((self.box.sessions / "coord-2.json").read_text()), "messagingSocketPath": "/tmp/cc-socks/coord-1.sock"}))
        status = json.loads(self.box.mc("--json", "status", session="coord-2").stdout)
        self.assertEqual(status["run"]["coordinator"]["rebind_candidate"]["session_id"], "coord-2")
        self.assertEqual(self.box.mc("assume", "set", "--text", "x", session="coord-2", expect=1).returncode, 1, "nothing coordinator-only works until the rebind")
        hook = self.box.hook("session-start", {}, session="coord-2", cwd=self.box.repo)
        self.assertIn("now runs as coord-2", hook)
        self.assertIn("adopt coordinator", hook)
        self.box.mc("adopt", "coordinator", session="coord-2")
        run = self._run_json()
        self.assertEqual(run["coordinator"]["session_id"], "coord-2")
        self.assertEqual(run["coordinator"]["adopted_from"], "coord-1")
        self.assertEqual(run["coordinator"]["adopted_by"], "same process")
        self.box.mc("assume", "set", "--text", "x", session="coord-2")
        result = self._reconcile_with(self._gh({}))
        self.assertNotIn("coordinator-rebind", [item["kind"] for item in result["drift"]])

    def test_a_fresh_coordinator_process_is_adopted_only_by_the_user(self):
        self.box.start()
        (self.box.sessions / "coord-1.json").unlink()
        self.box.register("coord-9", "mission control", str(self.box.repo))
        refused = self.box.mc("adopt", "coordinator", session="coord-9", expect=1)
        self.assertIn("adopted by the user", refused.stdout)
        self.box.mc("adopt", "coordinator", "--by-user", session="coord-9")
        self.assertEqual(self._run_json()["coordinator"]["adopted_by"], "user")

    def test_a_live_coordinator_cannot_be_adopted_away_without_the_user(self):
        self.box.start()
        self.box.register("coord-9", "other", str(self.box.repo))
        refused = self.box.mc("adopt", "coordinator", session="coord-9", expect=1)
        self.assertIn("is live", refused.stdout)

    def test_a_fresh_crew_session_in_a_planned_worktree_adopts_the_old_row_and_its_slot(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.box.mc("join", "--planned", session="crew-1", cwd=self.box.worktree)
        self.box.mc("report", "--state", "pr-ready", "--pr", "260", "--summary", "nearly there", session="crew-1", cwd=self.box.worktree)
        self.box.mc("request", "local-db", "--minutes", "5", session="crew-1", cwd=self.box.worktree)
        self.box.mc("grant", "local-db", "--to", "10SE.2", session="coord-1")
        self.box.mc("needs", "add", "--why", "push it", session="crew-1", cwd=self.box.worktree)
        # the session closes and a fresh one starts in the same worktree
        (self.box.sessions / "crew-1.json").unlink()
        self.box.register("crew-7", "10se2", str(self.box.worktree))
        joined = self.box.mc("join", "--planned", session="crew-7", cwd=self.box.worktree).stdout
        self.assertIn("adopted 10SE.2's row from session crew-1", joined)
        sessions = {p.name: json.loads(p.read_text()) for p in next(self.box.ledger_root.glob("*/sessions")).glob("*.json")}
        self.assertEqual(list(sessions), ["crew-7.json"], "one row, not a second briefing one")
        row = sessions["crew-7.json"]
        self.assertEqual((row["state"], row["pr"], row["summary"], row["adopted_from"]), ("in-slot", 260, "nearly there", "crew-1"))
        self.assertTrue((next(self.box.ledger_root.glob("*/sessions")) / "crew-1.json.adopted").exists())
        status = json.loads(self.box.mc("--json", "status", session="coord-1").stdout)
        self.assertEqual(status["slots"][0]["holder"], "crew-7")
        self.assertEqual(status["needs"][0]["session_id"], "crew-7")
        self.assertIn('"event": "adopt"', (next(self.box.ledger_root.glob("*/log.jsonl"))).read_text())

    def _crew_with_morning_cron_then_gone(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.box.mc("join", "--planned", session="crew-1", cwd=self.box.worktree)
        self.box.mc("jobs", "add", "--kind", "cron", "--spec", "0 9 * * *", "--id", "morning", "--prompt", "stand up", session="crew-1", cwd=self.box.worktree)
        (self.box.sessions / "crew-1.json").unlink()

    def test_a_crew_session_in_a_fresh_process_adopting_the_old_row_is_told_to_re_arm_its_jobs(self):
        self._crew_with_morning_cron_then_gone()
        self.box.register("crew-7", "10se2", str(self.box.worktree))
        # the start hook runs before the session has a row, so it must name the jobs the row will carry
        hook = self.box.hook("session-start", {"source": "startup"}, session="crew-7", cwd=self.box.worktree)
        self.assertIn("cron morning (0 9 * * *: stand up)", hook)
        joined = self.box.mc("join", "--planned", session="crew-7", cwd=self.box.worktree).stdout
        self.assertIn("adopted 10SE.2's row from session crew-1", joined)
        self.assertIn("10SE.2's previous session (crew-1) had, which died with its process", joined)
        self.assertIn("Re-arm each", joined)
        self.assertNotIn("this session had", joined, "the adopting session never had the work")

    def test_adopt_crew_in_a_fresh_process_is_told_to_re_arm_and_json_carries_the_line(self):
        self._crew_with_morning_cron_then_gone()
        self.box.register("crew-7", "10se2", str(self.box.worktree))
        adopted = json.loads(self.box.mc("--json", "adopt", "crew", session="crew-7", cwd=self.box.worktree).stdout)
        self.assertIn("cron morning (0 9 * * *: stand up)", adopted["rearm"])
        row = json.loads(next(self.box.ledger_root.glob("*/sessions/crew-7.json")).read_text())
        self.assertNotIn("rearm", row, "the line is printed, never stored")

    def test_a_cleared_crew_session_keeps_its_crons_and_is_not_told_to_re_arm(self):
        self._crew_with_morning_cron_then_gone()
        # /clear: a new session id on the same process and socket
        self.box.register("crew-2", "10se2", str(self.box.worktree))
        path = self.box.sessions / "crew-2.json"
        path.write_text(json.dumps({**json.loads(path.read_text()), "messagingSocketPath": "/tmp/cc-socks/crew-1.sock"}))
        hook = self.box.hook("session-start", {"source": "startup"}, session="crew-2", cwd=self.box.worktree)
        self.assertNotIn("Re-arm each", hook)
        joined = self.box.mc("join", "--planned", session="crew-2", cwd=self.box.worktree).stdout
        self.assertIn("adopted 10SE.2's row from session crew-1", joined)
        self.assertNotIn("Re-arm each", joined)

    def test_a_resume_in_a_new_process_then_a_clear_does_not_re_arm_what_the_resume_already_did(self):
        self._crew_with_morning_cron_then_gone()
        # the user resumes the same session id in a new process, whose socket differs; the resume hook names the job
        self.box.register("crew-1", "10se2", str(self.box.worktree))
        path = self.box.sessions / "crew-1.json"
        path.write_text(json.dumps({**json.loads(path.read_text()), "messagingSocketPath": "/tmp/cc-socks/process-b.sock"}))
        resumed = self.box.hook("session-start", {"source": "resume"}, session="crew-1", cwd=self.box.worktree)
        self.assertIn("read CronList first", resumed)
        self.assertEqual(self._row()["socket"], "/tmp/cc-socks/process-b.sock", "the row follows the process the session now runs in")
        # /clear in process B: a new id, the same process and socket
        path.unlink()
        self.box.register("crew-2", "10se2", str(self.box.worktree))
        cleared = self.box.sessions / "crew-2.json"
        cleared.write_text(json.dumps({**json.loads(cleared.read_text()), "messagingSocketPath": "/tmp/cc-socks/process-b.sock"}))
        self.assertNotIn("Re-arm each", self.box.hook("session-start", {"source": "startup"}, session="crew-2", cwd=self.box.worktree))
        joined = self.box.mc("join", "--planned", session="crew-2", cwd=self.box.worktree).stdout
        self.assertIn("adopted 10SE.2's row from session crew-1", joined)
        self.assertNotIn("Re-arm each", joined, "the cron was re-armed in process B and is still there")

    def test_join_makes_a_fresh_row_when_the_old_session_is_still_live(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.box.mc("join", "--planned", session="crew-1", cwd=self.box.worktree)
        self.box.register("crew-8", "second", str(self.box.worktree))
        self.box.mc("join", "--planned", session="crew-8", cwd=self.box.worktree)
        names = sorted(p.name for p in next(self.box.ledger_root.glob("*/sessions")).glob("*.json"))
        self.assertEqual(names, ["crew-1.json", "crew-8.json"])

    def test_a_session_sat_on_a_prompt_reads_waiting_on_you(self):
        """The registry marks a session `waiting` on a permission prompt or an AskUserQuestion; the board says so, since nothing the session reported does."""
        self.box.start()
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        text = self.box.mc("status", session="coord-1").stdout
        self.assertNotIn("Waiting on you", text)
        self.box.mc("needs", "add", "--why", "push the branch", "--command", "git push -u origin feat/a", session="crew-1", cwd=self.box.worktree)
        row = json.loads((self.box.sessions / "crew-1.json").read_text())
        (self.box.sessions / "crew-1.json").write_text(json.dumps({**row, "status": "waiting", "statusUpdatedAt": 1793826386060}))
        text = self.box.mc("status", session="coord-1").stdout
        self.assertIn("| 10se2 | 10SE.2 | feat/a | reading orders · waiting on you |", text)
        self.assertIn("## Waiting on you", text)
        self.assertIn("- 10SE.2 (10se2) sits on a permission prompt or a question in its own window since ", text)
        # the window the user must visit is the first section: ahead of the needs, the crew table and the slots
        self.assertIn("## Tribute owed", text)
        self.assertLess(text.index("## Waiting on you"), text.index("## Tribute owed"))
        self.assertLess(text.index("## Waiting on you"), text.index("| Session |"))
        self.assertLess(text.index("## Waiting on you"), text.index("| Dibs |"))
        status = json.loads(self.box.mc("--json", "status", session="coord-1").stdout)
        self.assertEqual((status["sessions"][0]["live_status"], status["sessions"][0]["live_since"]), ("waiting", 1793826386.06))

    def test_the_text_board_reads_in_the_boards_order_and_archives_sessions_that_are_over(self):
        self.box.start()
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        self.box.mc("needs", "add", "--why", "push the branch", "--command", "git push -u origin feat/a", session="crew-1", cwd=self.box.worktree)
        self.box.mc("needs", "add", "--why", "approve the PR description in this session", session="crew-1", cwd=self.box.worktree)
        text = self.box.mc("status", session="coord-1").stdout
        # the line to type comes first, the why beneath it; a need with no line keeps its why on the row
        line = f"1. [10SE.2] `cd {self.box.worktree.resolve()} && git push -u origin feat/a`\n   push the branch\n"
        self.assertIn(line, text)
        self.assertIn("2. [10SE.2] approve the PR description in this session (in ", text)
        # a checkout under a path with a space: the cd is quoted, so the pasted line reaches the command
        self.box.mc("needs", "add", "--why", "start it", "--command", "claude --model opus", "--cwd-hint", "/Users/j/Documents/My App/.claude/worktrees/b", session="crew-1", cwd=self.box.worktree)
        self.assertIn("3. [10SE.2] `cd '/Users/j/Documents/My App/.claude/worktrees/b' && claude --model opus`\n   start it\n", self.box.mc("status", session="coord-1").stdout)
        # what the user has to type comes first, then the crew, then the machine
        self.assertLess(text.index("## Tribute owed"), text.index("| Session |"))
        self.assertLess(text.index("| Session |"), text.index("| Dibs |"))
        self.assertNotIn("## Archive", text)
        # the session goes: its row leaves the crew table for an Archive table at the end, with the state it last reported
        (self.box.sessions / "crew-1.json").unlink()
        text = self.box.mc("status", session="coord-1").stdout
        self.assertNotIn("(gone)", text)
        self.assertIn("## Archive", text)
        self.assertIn("| 10se2 | 10SE.2 | feat/a | gone (reading orders) |", text)
        self.assertLess(text.index("| Dibs |"), text.index("## Archive"))
        self.assertNotIn("| 10se2 | 10SE.2 | feat/a | reading orders |", text, "a gone session is not in the raiders' table")

    # the launch line: kick-off used to print it in chat; now crew add puts it on the needs list, and the join closes it

    def test_crew_add_puts_the_launch_line_on_the_needs_list_and_the_join_closes_it(self):
        self.box.start()
        added = json.loads(self.box.mc("--json", "crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree),
                                       "--model", "opus", "--effort", "high", "--name", "10se.2 search ranking", "--reason", "reworks the shared ranking query", session="coord-1").stdout)
        self.assertEqual((added["model"], added["effort"], added["name"], added["launch_need"]), ("opus", "high", "10se.2 search ranking", 1))
        status = json.loads(self.box.mc("--json", "status", session="coord-1").stdout)
        need = status["needs"][0]
        self.assertEqual((need["kind"], need["task"], need["session_id"], need["status"]), ("launch", "10SE.2", "coord-1", "open"))
        self.assertEqual(Path(need["cwd"]).resolve(), self.box.worktree.resolve(), "the line runs from the worktree, so the board prints cd there first")
        self.assertEqual(need["why"], "start raider 10SE.2 in a new terminal window (opus, high: reworks the shared ranking query)")
        self.assertTrue(need["command"].startswith("claude --model opus --effort high --name '10se.2 search ranking' 'Start: you are raider 10SE.2 in raid search. Read your orders at "), need["command"])
        self.assertIn("invoke /goblin-warband:join-raid and answer its five questions to the chief.'", need["command"])
        self.assertNotIn("--plugin-dir", need["command"])
        self.assertIn("## Tribute owed", self.box.mc("status", session="coord-1").stdout)
        # the session starts in the worktree: the line was typed, so the need closes by itself
        self.box.mc("join", "--planned", session="crew-1", cwd=self.box.worktree)
        self.assertEqual(json.loads(self.box.mc("--json", "status", session="coord-1").stdout)["needs"], [])
        run = json.loads(next(self.box.ledger_root.glob("*/run.json")).read_text())
        self.assertEqual((run["needs"][0]["status"], run["needs"][0]["note"]), ("done", "joined as session crew-1"))
        self.assertEqual(run["crew"][0]["model"], "opus")

    def test_a_launch_line_without_a_model_says_so_and_a_plugin_dir_is_added_when_asked(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "UXR", "--branch", "feat/a", "--worktree", str(self.box.worktree), "--plugin-dir", "/p/mission-control", session="coord-1")
        need = json.loads(self.box.mc("--json", "status", session="coord-1").stdout)["needs"][0]
        self.assertEqual(need["why"], "start raider UXR in a new terminal window (the terminal's model)")
        self.assertTrue(need["command"].startswith("claude --plugin-dir /p/mission-control --name 'uxr raider' "), need["command"])
        # no worktree, no line to type yet
        out = self.box.mc("crew", "add", "--task", "B", "--branch", "feat/b", session="coord-1").stdout
        self.assertIn("no worktree, so no launch line", out)
        self.assertEqual(len(json.loads(self.box.mc("--json", "status", session="coord-1").stdout)["needs"]), 1)

    def test_a_second_crew_add_for_the_task_supersedes_its_launch_need(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), "--model", "sonnet", session="coord-1")
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), "--model", "opus", "--effort", "high", session="coord-1")
        run = json.loads(next(self.box.ledger_root.glob("*/run.json")).read_text())
        self.assertEqual([(n["n"], n["status"], n.get("superseded_by"), n.get("supersedes")) for n in run["needs"]], [(1, "done", 2, None), (2, "open", None, 1)])
        self.assertIn("--model opus --effort high", run["needs"][1]["command"])
        self.assertEqual(len(run["crew"]), 1)
        # reconcile names the line while nobody has joined
        result = self._reconcile_with(self._gh({}))
        unjoined = [item for item in result["drift"] if item["kind"] == "unjoined"]
        self.assertEqual(len(unjoined), 1)
        self.assertIn("its launch line is tribute #2 on the slate", unjoined[0]["detail"])

    def test_re_adding_a_task_whose_session_is_live_edits_the_plan_and_raises_no_launch_need(self):
        # found on PR 59's review: a migration timestamp assigned after the session had joined left a launch need open for a session that was running
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), "--model", "sonnet", session="coord-1")
        self.box.mc("join", "--planned", session="crew-1", cwd=self.box.worktree)
        out = self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), "--model", "sonnet", "--migration", "20261104120000", session="coord-1").stdout
        self.assertIn("its session is live, so no launch line", out)
        self.assertEqual(json.loads(self.box.mc("--json", "status", session="coord-1").stdout)["needs"], [])
        plan = json.loads(self.box.mc("crew", "list", session="coord-1").stdout)
        self.assertEqual((len(plan), plan[0]["migration"]), (1, "20261104120000"))
        added = json.loads(self.box.mc("--json", "crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1").stdout)
        self.assertIsNone(added["launch_need"])
        log = next(self.box.ledger_root.glob("*/log.jsonl")).read_text()
        self.assertIn('"by": "join"', log, "the join closed the first line")

    def test_re_adding_a_task_without_its_worktree_closes_the_stale_launch_line(self):
        # by hand only (kick-off always passes the worktree), but the board and the plan must not disagree
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", session="coord-1")
        self.assertEqual(json.loads(self.box.mc("--json", "status", session="coord-1").stdout)["needs"], [])
        run = json.loads(next(self.box.ledger_root.glob("*/run.json")).read_text())
        self.assertEqual((run["needs"][0]["status"], run["needs"][0]["note"]), ("done", "plan edited with no worktree; no line to type"))
        self.assertIn('"by": "crew-add"', next(self.box.ledger_root.glob("*/log.jsonl")).read_text())

    def test_every_value_on_the_launch_line_is_quoted(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), "--model", "opus", "--effort", "high", "--plugin-dir", "/Users/j/Library/Application Support/mission-control", session="coord-1")
        command = json.loads(self.box.mc("--json", "status", session="coord-1").stdout)["needs"][0]["command"]
        self.assertIn("--plugin-dir '/Users/j/Library/Application Support/mission-control'", command)
        self.assertIn("--model opus --effort high", command, "a bare word needs no quotes and gets none")
        self.assertEqual(shlex.split(command)[shlex.split(command).index("--plugin-dir") + 1], "/Users/j/Library/Application Support/mission-control")

    def test_a_crew_session_adopting_the_old_row_closes_the_launch_need_too(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), "--model", "sonnet", session="coord-1")
        self.box.mc("join", "--planned", session="crew-1", cwd=self.box.worktree)
        # the plan is re-added (a new launch line) after the first session closed; the next session adopts the row and closes it
        (self.box.sessions / "crew-1.json").unlink()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), "--model", "opus", session="coord-1")
        self.assertEqual(len(json.loads(self.box.mc("--json", "status", session="coord-1").stdout)["needs"]), 1)
        self.box.register("crew-7", "10se2", str(self.box.worktree))
        self.assertIn("adopted 10SE.2's row", self.box.mc("join", "--planned", session="crew-7", cwd=self.box.worktree).stdout)
        self.assertEqual(json.loads(self.box.mc("--json", "status", session="coord-1").stdout)["needs"], [])

    def test_jobs_are_kept_in_the_ledger_and_a_resume_is_told_to_re_arm_them(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.box.mc("join", "--planned", session="crew-1", cwd=self.box.worktree)
        self.box.mc("jobs", "add", "--kind", "cron", "--spec", "0 9 * * 1-5", "--prompt", "check the PR", "--reason", "morning check", "--id", "morning", session="crew-1", cwd=self.box.worktree)
        listed = json.loads(self.box.mc("jobs", "list", session="crew-1", cwd=self.box.worktree).stdout)
        self.assertEqual([j["id"] for j in listed], ["morning"])
        hook = self.box.hook("session-start", {"source": "resume"}, session="crew-1")
        self.assertIn("cron morning (0 9 * * 1-5: check the PR)", hook)
        self.assertIn("read CronList first", hook)
        self.assertNotIn("Re-arm each", hook, "a resume restores a cron by itself, so a blind re-arm would fire it twice")
        compacted = self.box.hook("session-start", {"source": "compact"}, session="crew-1")
        self.assertIn("still raider 10SE.2", compacted)
        self.assertIn("Your orders:", compacted)
        self.assertNotIn("Re-arm each", compacted, "a compaction keeps the process and its cron")
        # the session goes away with its job open: reconcile names it
        (self.box.sessions / "crew-1.json").unlink()
        result = self._reconcile_with(self._gh({}))
        orphan = [item for item in result["drift"] if item["kind"] == "job-orphaned"]
        self.assertEqual(len(orphan), 1)
        self.assertIn("morning", orphan[0]["detail"])
        self.box.register("crew-1", "10se2", str(self.box.worktree))
        self.box.mc("jobs", "done", "morning", session="crew-1", cwd=self.box.worktree)
        self.assertEqual(json.loads(self.box.mc("jobs", "list", session="crew-1", cwd=self.box.worktree).stdout), [])

    def _crew_with_job_then_closed(self, job="watch-240"):
        """A crew session that recorded a job, reported done with PR #240 and closed with the job still open."""
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        self.box.mc("jobs", "add", "--kind", "watch", "--spec", "PR #240", "--id", job, session="crew-1", cwd=self.box.worktree)
        self.box.mc("report", "--state", "done", "--pr", "240", session="crew-1", cwd=self.box.worktree)
        (self.box.sessions / "crew-1.json").unlink()

    def _row(self, session="crew-1"):
        return json.loads(next(self.box.ledger_root.glob(f"*/sessions/{session}.json")).read_text())

    def _orphans(self):
        return [item for item in self._reconcile_with(self._gh(self._merged(240)))["drift"] if item["kind"] == "job-orphaned"]

    def test_retire_closes_the_jobs_on_the_row_it_retires(self):
        self._crew_with_job_then_closed()
        self.assertEqual(len(self._orphans()), 1, "before the retire the open watch on a closed session is drift")
        git(self.box.repo, "merge", "-q", "--no-ff", "-m", "Merge feat/a", "feat/a")
        code, out = self._retire_with(self._gh(self._merged(240)), "10SE.2")
        self.assertEqual(code, 0, out)
        job = self._row()["jobs"][0]
        self.assertEqual((job["id"], job["status"], job["note"]), ("watch-240", "done", "retired by coordinator"))
        self.assertEqual(self._orphans(), [])
        log = next(self.box.ledger_root.glob("*/log.jsonl")).read_text()
        self.assertIn('"event": "job-done"', log)

    def test_a_row_retired_with_a_job_still_open_is_not_drift(self):
        # a row retired by a version whose retire left jobs alone
        self._crew_with_job_then_closed()
        path = next(self.box.ledger_root.glob("*/sessions/crew-1.json"))
        row = json.loads(path.read_text())
        row["retired"] = {"at": row["updated_at"], "by": "coordinator"}
        path.write_text(json.dumps(row))
        self.assertEqual(self._orphans(), [])

    def test_the_coordinator_or_the_user_closes_a_job_whose_session_is_gone(self):
        self._crew_with_job_then_closed()
        self.box.register("crew-2", "bystander", str(self.box.repo))
        refused = self.box.mc("jobs", "done", "watch-240", session="crew-2", expect=None)
        self.assertNotEqual(refused.returncode, 0, "a session that is neither the owner nor the coordinator closes nothing")
        done = self.box.mc("jobs", "done", "watch-240", session="coord-1")
        self.assertIn("it was 10SE.2's, whose session is gone", done.stdout)
        job = self._row()["jobs"][0]
        self.assertEqual((job["status"], job["note"]), ("done", "closed by coordinator: its session is gone"))
        self.assertEqual(self._orphans(), [])
        # the person, from a session that is not the coordinator
        row_path = next(self.box.ledger_root.glob("*/sessions/crew-1.json"))
        row = json.loads(row_path.read_text())
        row["jobs"].append({"id": "nightly", "kind": "cron", "spec": "0 2 * * *", "status": "open"})
        row_path.write_text(json.dumps(row))
        self.box.mc("jobs", "done", "nightly", "--by-user", session="crew-2")
        self.assertEqual(self._row()["jobs"][1]["note"], "closed by user: its session is gone")

    def test_the_user_closes_the_job_of_a_coordinator_that_is_gone(self):
        self.box.start()
        self.box.mc("jobs", "add", "--kind", "cron", "--spec", "*/30 * * * *", "--id", "wake", session="coord-1")
        refused = self.box.mc("jobs", "done", "wake", "--by-user", session="crew-1", cwd=self.box.worktree, expect=None)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("belongs to the chief, whose session is live", refused.stdout + refused.stderr)
        (self.box.sessions / "coord-1.json").unlink()
        done = self.box.mc("jobs", "done", "wake", "--by-user", session="crew-1", cwd=self.box.worktree)
        self.assertIn("it was the chief's, whose session is gone", done.stdout)
        job = json.loads(next(self.box.ledger_root.glob("*/run.json")).read_text())["jobs"][0]
        self.assertEqual((job["status"], job["note"]), ("done", "closed by user: its session is gone"))
        again = self.box.mc("jobs", "done", "wake", "--by-user", session="crew-1", cwd=self.box.worktree, expect=None)
        self.assertNotEqual(again.returncode, 0)
        self.assertIn("job wake is already done", again.stdout + again.stderr, "a finished job on run.json is found for the person too")

    def test_a_job_id_open_on_two_gone_rows_is_refused_and_neither_is_closed(self):
        self._crew_with_job_then_closed()
        twin = {**self._row(), "session_id": "crew-9", "task": "10SE.3"}
        next(self.box.ledger_root.glob("*/sessions/crew-1.json")).with_name("crew-9.json").write_text(json.dumps(twin))
        refused = self.box.mc("jobs", "done", "watch-240", session="coord-1", expect=None)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("open on 2 rows whose sessions are gone", refused.stdout + refused.stderr)
        self.assertEqual([self._row(s)["jobs"][0]["status"] for s in ("crew-1", "crew-9")], ["open", "open"])

    def test_the_coordinators_own_job_does_not_shadow_a_gone_sessions_job_with_the_same_id(self):
        self._crew_with_job_then_closed(job="poll")
        self.box.mc("jobs", "add", "--kind", "cron", "--spec", "0 9 * * *", "--id", "poll", session="coord-1")
        own = self.box.mc("jobs", "done", "poll", session="coord-1")
        self.assertEqual(own.stdout.strip(), "job poll done", "its own open job is closed first")
        self.assertEqual(self._row()["jobs"][0]["status"], "open")
        # the coordinator's is now done; the same id reaches the gone session's
        gone = self.box.mc("jobs", "done", "poll", session="coord-1")
        self.assertIn("it was 10SE.2's, whose session is gone", gone.stdout)
        self.assertEqual(self._row()["jobs"][0]["status"], "done")
        nothing = self.box.mc("jobs", "done", "poll", session="coord-1", expect=None)
        self.assertNotEqual(nothing.returncode, 0, "with nothing open under that id, done says so and does not report success")
        self.assertIn("job poll is already done", nothing.stdout + nothing.stderr)
        self.assertNotIn("jobs list", nothing.stdout + nothing.stderr, "the coordinator's own list would not show a gone session's job")

    def test_a_repeated_done_is_refused_as_already_done_and_leaves_the_job_alone(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.box.mc("join", "--planned", session="crew-1", cwd=self.box.worktree)
        self.box.mc("jobs", "add", "--kind", "cron", "--spec", "0 9 * * *", "--id", "morning", session="crew-1", cwd=self.box.worktree)
        self.box.mc("jobs", "done", "morning", session="crew-1", cwd=self.box.worktree)
        closed_at = self._row()["jobs"][0]["done_at"]
        again = self.box.mc("jobs", "done", "morning", session="crew-1", cwd=self.box.worktree, expect=None)
        self.assertNotEqual(again.returncode, 0)
        self.assertIn("job morning is already done", again.stdout + again.stderr)
        self.assertEqual(self._row()["jobs"][0]["done_at"], closed_at)
        log = next(self.box.ledger_root.glob("*/log.jsonl")).read_text()
        self.assertEqual(log.count('"event": "job-done"'), 1, "the repeat logs nothing")
        typo = self.box.mc("jobs", "done", "mourning", session="crew-1", cwd=self.box.worktree, expect=None)
        self.assertIn("no job mourning on this session", typo.stdout + typo.stderr)

    def test_a_missing_job_id_is_not_found_on_the_run_for_the_coordinator_and_the_person(self):
        self.box.start()
        for who in (["--by-user"], []):
            session = "crew-1" if who else "coord-1"
            missing = self.box.mc("jobs", "done", "zz", *who, session=session, cwd=self.box.worktree if who else None, expect=None)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("no job zz on any session in this raid", missing.stdout + missing.stderr)
            self.assertNotIn("jobs list", missing.stdout + missing.stderr, "their own list would not show it")

    def test_a_gone_row_with_no_task_is_named_by_its_session_and_not_as_the_coordinator(self):
        self.box.start()
        self.box.register("crew-5", "unplanned", str(self.box.repo))
        self.box.mc("join", "--branch", "feat/z", session="crew-5")
        self.assertEqual(self._row("crew-5")["task"], "")
        self.box.mc("jobs", "add", "--kind", "watch", "--spec", "PR 250", "--id", "watch-250", session="crew-5")
        (self.box.sessions / "crew-5.json").unlink()
        done = self.box.mc("jobs", "done", "watch-250", session="coord-1")
        self.assertIn("it was crew-5's, whose session is gone", done.stdout)
        self.assertNotIn("the chief's", done.stdout)

    def test_a_fresh_coordinator_adopted_by_the_user_is_told_to_re_arm_the_runs_jobs(self):
        self.box.start()
        self.box.mc("jobs", "add", "--kind", "cron", "--id", "wake", "--spec", "*/30 9-17 * * 1-5", "--prompt", "Mission control wake", session="coord-1")
        (self.box.sessions / "coord-1.json").unlink()
        self.box.register("coord-2", "mission control 2", str(self.box.repo))
        adopted = self.box.mc("adopt", "coordinator", "--by-user", session="coord-2")
        self.assertIn("this session is now the chief of raid search", adopted.stdout)
        self.assertIn("cron wake (*/30 9-17 * * 1-5: Mission control wake)", adopted.stdout)
        self.assertIn("Re-arm each", adopted.stdout)
        self.assertIn("the raid's previous chief (coord-1) had, which died with its process", adopted.stdout)
        self.assertNotIn("this session had", adopted.stdout, "the adopting session never had the work")

    def test_adopting_from_a_live_coordinator_says_its_crons_still_fire_and_json_carries_the_line(self):
        self.box.start()
        self.box.mc("jobs", "add", "--kind", "cron", "--id", "wake", "--spec", "*/30 9-17 * * 1-5", "--prompt", "Mission control wake", session="coord-1")
        self.box.register("coord-2", "mission control 2", str(self.box.repo))
        adopted = json.loads(self.box.mc("--json", "adopt", "coordinator", "--by-user", session="coord-2").stdout)
        self.assertEqual(adopted["session_id"], "coord-2")
        self.assertIn("cron wake (*/30 9-17 * * 1-5: Mission control wake)", adopted["rearm"])
        self.assertIn("still live", adopted["rearm"])
        self.assertNotIn("died with", adopted["rearm"], "the old process and its cron are still running")
        run = json.loads(next(self.box.ledger_root.glob("*/run.json")).read_text())
        self.assertNotIn("rearm", run["coordinator"], "the line is printed, never stored")

    def test_adopting_from_a_cleared_coordinator_whose_process_lives_on_says_it_is_still_live(self):
        self.box.start()
        self.box.mc("jobs", "add", "--kind", "cron", "--id", "wake", "--spec", "*/30 9-17 * * 1-5", session="coord-1")
        # /clear in the old coordinator: its id leaves the registry, its process and socket carry on under a new one
        (self.box.sessions / "coord-1.json").unlink()
        self.box.register("coord-1b", "mission control", str(self.box.repo))
        (self.box.sessions / "coord-1b.json").write_text(json.dumps({**json.loads((self.box.sessions / "coord-1b.json").read_text()), "messagingSocketPath": "/tmp/cc-socks/coord-1.sock"}))
        self.box.register("coord-2", "mission control 2", str(self.box.repo))
        adopted = self.box.mc("adopt", "coordinator", "--by-user", session="coord-2")
        self.assertIn("still live", adopted.stdout)
        self.assertNotIn("died with", adopted.stdout)

    def test_a_live_sessions_job_is_its_own_to_close(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.box.mc("join", "--planned", session="crew-1", cwd=self.box.worktree)
        self.box.mc("jobs", "add", "--kind", "cron", "--spec", "0 9 * * *", "--id", "morning", session="crew-1", cwd=self.box.worktree)
        refused = self.box.mc("jobs", "done", "morning", session="coord-1", expect=None)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("whose session is live", refused.stdout + refused.stderr)
        self.assertEqual(self._row()["jobs"][0]["status"], "open")

    def test_the_coordinator_records_its_own_jobs_on_the_run_and_a_resume_re_arms_them(self):
        self.box.start()
        self.box.mc("jobs", "add", "--kind", "cron", "--id", "wake", "--spec", "*/30 9-17 * * 1-5", "--prompt", "Mission control wake", "--reason", "wake for crew messages", session="coord-1")
        listed = json.loads(self.box.mc("jobs", "list", session="coord-1").stdout)
        self.assertEqual([(j["id"], j["task"], j["session_id"]) for j in listed], [("wake", "coordinator", "coord-1")])
        run = json.loads(next(self.box.ledger_root.glob("*/run.json")).read_text())
        self.assertEqual(run["jobs"][0]["id"], "wake")
        resumed = self.box.hook("session-start", {"source": "resume"}, session="coord-1", cwd=self.box.repo)
        self.assertIn("cron wake (*/30 9-17 * * 1-5: Mission control wake)", resumed)
        self.assertIn("read CronList first", resumed)
        self.assertNotIn("Re-arm each", resumed, "Claude Code restores a cron on --resume, so creating it again fires it twice")
        self.assertNotIn("Scheduled work", self.box.hook("session-start", {"source": "compact"}, session="coord-1", cwd=self.box.repo), "a compaction keeps the process and its cron")
        self.assertEqual(json.loads(self.box.mc("jobs", "list", session="crew-1", cwd=self.box.worktree).stdout), [], "a crew session's list is its own row")
        self.box.mc("jobs", "done", "wake", session="coord-1")
        self.assertEqual(json.loads(self.box.mc("jobs", "list", session="coord-1").stdout), [])
        self.assertNotIn("Scheduled work", self.box.hook("session-start", {"source": "resume"}, session="coord-1", cwd=self.box.repo))

    def test_a_dozen_long_jobs_cannot_push_the_resume_context_past_the_hook_cap(self):
        self.box.start()
        for n in range(12):
            self.box.mc("jobs", "add", "--kind", "monitor", "--id", f"tail-{n}", "--spec", f"spec{n}-" + "s" * 400, "--prompt", f"prompt{n}-" + "p" * 400, session="coord-1")
        resumed = self.box.hook("session-start", {"source": "resume"}, session="coord-1", cwd=self.box.repo)
        self.assertNotIn("p" * 300, resumed, "a prompt is clipped, not printed whole")
        self.assertNotIn("s" * 300, resumed, "a spec is clipped, not printed whole")
        self.assertIn("prompt11-", resumed, "every job is still named")
        self.assertIn("jobs list", resumed, "the clipped text is one command away")
        self.assertLess(len(resumed), 5000, "twelve long jobs leave the rest of the context its room under the 10,000 character hook cap")

    def test_a_short_job_prints_whole_and_says_nothing_about_a_clip(self):
        self.box.start()
        self.box.mc("jobs", "add", "--kind", "cron", "--id", "wake", "--spec", "*/30 9-17 * * 1-5", "--prompt", "Mission control wake", session="coord-1")
        resumed = self.box.hook("session-start", {"source": "resume"}, session="coord-1", cwd=self.box.repo)
        self.assertIn("cron wake (*/30 9-17 * * 1-5: Mission control wake)", resumed)
        self.assertNotIn("jobs list", resumed)

    def test_a_resume_re_arms_a_monitor_and_a_watch_but_only_checks_a_cron(self):
        self.box.start()
        self.box.mc("jobs", "add", "--kind", "cron", "--id", "wake", "--spec", "*/30 * * * *", session="coord-1")
        self.box.mc("jobs", "add", "--kind", "monitor", "--id", "tail", "--spec", "build output", session="coord-1")
        self.box.mc("jobs", "add", "--kind", "watch", "--id", "watch-9", "--spec", "PR 9", session="coord-1")
        resumed = self.box.hook("session-start", {"source": "resume"}, session="coord-1", cwd=self.box.repo)
        self.assertIn("read CronList first", resumed)
        self.assertIn("Re-arm each Monitor or watch", resumed, "these died with the process")
        self.assertIn("monitor tail (build output)", resumed)
        # with no cron on the list there is nothing to check
        self.box.mc("jobs", "done", "wake", session="coord-1")
        later = self.box.hook("session-start", {"source": "resume"}, session="coord-1", cwd=self.box.repo)
        self.assertNotIn("CronList", later)
        self.assertIn("Re-arm each Monitor or watch", later)

    def _add_pending(self, *items):
        run_path = next(self.box.ledger_root.glob("*/run.json"))
        run = json.loads(run_path.read_text())
        run.setdefault("pending", []).extend(items)
        run_path.write_text(json.dumps(run))

    def test_a_compacted_coordinator_reads_a_held_approval_as_held_and_a_decision_with_its_subject(self):
        self.box.start()
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        self._add_pending(
            {"id": "a1", "n": 1, "kind": "approval", "pr": 242, "text": "PR #242 approved by max; landing is authorised and waits on the coordinator", "status": "open", "at": 1.0},
            {"id": "a2", "n": 2, "kind": "approval", "pr": 243, "text": "PR #243 approved by max; landing is authorised and waits on the coordinator", "status": "open", "at": 2.0},
        )
        self.box.mc("pending", "hold", "242", "--text", "lands once #240 is approved", session="coord-1")
        self.box.mc("decide", "add", "--text", "No rerequest.", "--about", "re-requesting review on #242", "--told", "10SE.2", session="coord-1")
        hook = self.box.hook("session-start", {"source": "compact"}, session="coord-1", cwd=self.box.repo)
        self.assertIn("#1 PR #242 approved and held, not to land yet: lands once #240 is approved", hook)
        self.assertNotIn("PR #242 approved by max; landing is authorised", hook, "a held approval must not read as one to land")
        self.assertIn("#2 PR #243 approved by max; landing is authorised", hook)
        self.assertIn("#1 No rerequest. (about re-requesting review on #242)", hook)

    def test_a_long_decision_is_cut_before_its_subject_not_through_it(self):
        self.box.start()
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        self.box.mc("decide", "add", "--text", "y" * 700, "--about", "the merge order", "--told", "10SE.2", session="coord-1")
        hook = self.box.hook("session-start", {"source": "compact"}, session="coord-1", cwd=self.box.repo)
        self.assertIn("… (about the merge order)", hook, "the subject is what makes a clipped decision usable")
        self.assertNotIn("y" * 601, hook)

    def test_the_start_context_stays_under_the_hook_output_cap_and_keeps_its_last_sentence(self):
        self.box.start()
        self._add_pending(*[{"id": f"t{n}", "n": n, "kind": "thread", "text": f"thread {n} " + "x" * 1100, "status": "open", "at": float(n)} for n in range(1, 21)])
        self.box.mc("jobs", "add", "--kind", "cron", "--id", "wake", "--spec", "*/30 9-17 * * 1-5", "--prompt", "Mission control wake", "--reason", "wake", session="coord-1")
        hook = self.box.hook("session-start", {"source": "resume"}, session="coord-1", cwd=self.box.repo)
        self.assertLess(len(hook), 10_000, "past 10,000 characters the harness shows the model a 2,000-character preview")
        self.assertIn("#1 thread 1 ", hook)
        self.assertRegex(hook, r"and \d+ more in `warband\.py pending list`")
        self.assertIn("Run reconcile before saying where things stand.", hook)
        self.assertIn("read CronList first", hook)

    def test_the_pre_compact_hook_tells_the_summary_what_only_the_conversation_holds(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.box.mc("join", "--planned", session="crew-1", cwd=self.box.worktree)
        coordinator = self.box.hook("pre-compact", {"trigger": "manual", "custom_instructions": None}, session="coord-1", cwd=self.box.repo)
        self.assertIn("is the chief of goblin-warband raid", coordinator)
        self.assertIn("not yet answered", coordinator)
        self.assertIn("freeze or hold still in force", coordinator)
        self.assertLess(len(coordinator), 10_000)
        crew = self.box.hook("pre-compact", {"trigger": "auto"}, session="crew-1", cwd=self.box.worktree)
        self.assertIn("raider 10SE.2", crew)
        self.assertIn("its orders are", crew)
        self.assertEqual(self.box.hook("pre-compact", {"trigger": "manual"}, session="stranger", cwd=self.box.repo), "", "a session outside the run gets no instructions")

    def test_a_crew_below_high_effort_launches_with_its_subagents_raised_to_high(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), "--model", "sonnet", "--effort", "medium", session="coord-1")
        need = json.loads(self.box.mc("--json", "status", session="coord-1").stdout)["needs"][0]
        self.assertTrue(need["command"].startswith("CLAUDE_CODE_SUBAGENT_EFFORT=high claude --model sonnet --effort medium --name "), need["command"])
        for effort in ("high", "xhigh", None):
            flags = ["--effort", effort] if effort else []
            self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), "--model", "opus", *flags, session="coord-1")
            need = json.loads(self.box.mc("--json", "status", session="coord-1").stdout)["needs"][0]
            self.assertTrue(need["command"].startswith("claude --model opus "), f"{effort}: {need['command']}")

    def test_the_watch_keeps_its_own_job_entry(self):
        self.box.start()
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        self.box.mc("report", "--state", "pr-ready", "--pr", "261", session="crew-1", cwd=self.box.worktree)
        self._watch(self._gh_watch([self._view(checks=[("ci", "SUCCESS")]), self._view(checks=[("ci", "SUCCESS")]), self._view(checks=[("ci", "FAILURE")])]))
        jobs = json.loads(self.box.mc("jobs", "list", session="crew-1", cwd=self.box.worktree).stdout)
        self.assertEqual([(j["id"], j["kind"], j["status"]) for j in jobs], [("watch-261", "watch", "open")])
        merged = self._view(state="MERGED", checks=[("ci", "FAILURE")])
        self._watch(self._gh_watch([self._view(checks=[("ci", "FAILURE")]), merged, merged]))
        self.assertEqual(json.loads(self.box.mc("jobs", "list", session="crew-1", cwd=self.box.worktree).stdout), [], "ended watch is done")

    def test_pending_and_decisions_survive_in_the_ledger_and_reach_a_resumed_coordinator(self):
        self.box.start()
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        self.box.mc("pending", "add", "10SE.2", "--kind", "approval", "--text", "PR description sent back with two changes", session="coord-1")
        self.box.mc("decide", "add", "--text", "option A: the short-record fragments keep the old endpoint", "--about", "10SE.6 finding 3", "--told", "10SE.2", session="coord-1")
        hook = self.box.hook("session-start", {"source": "resume"}, session="coord-1", cwd=self.box.repo)
        self.assertIn("pending: #1 PR description sent back with two changes", hook)
        self.assertIn("recent rulings: #1 option A", hook)
        listed = self.box.mc("decide", "list", session="coord-1").stdout
        self.assertIn("told 10SE.2", listed)
        # unacknowledged for too long: reconcile says so; an ack clears it
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        real = mc_module.DECISION_ACK_SECONDS
        mc_module.DECISION_ACK_SECONDS = -1
        try:
            result = self._reconcile_with(self._gh({}))
            self.assertIn("decision-unacknowledged", [item["kind"] for item in result["drift"]])
            self.box.mc("decide", "ack", "1", session="crew-1", cwd=self.box.worktree)
            result = self._reconcile_with(self._gh({}))
            self.assertNotIn("decision-unacknowledged", [item["kind"] for item in result["drift"]])
        finally:
            mc_module.DECISION_ACK_SECONDS = real
        self.box.mc("pending", "done", "1", "--text", "approved", session="coord-1")
        self.assertEqual(json.loads(self.box.mc("pending", "list", session="coord-1").stdout), [])
        refused = self.box.mc("decide", "add", "--text", "x", session="crew-1", cwd=self.box.worktree, expect=1)
        self.assertIn("only the chief's session",refused.stdout)

    def test_a_measurement_need_names_its_session_and_done_carries_the_result(self):
        self.box.start()
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        self.box.mc("needs", "add", "--why", "run the cold-cache spike on hosted and paste the timings", "--kind", "measurement", "--for", "10SE.2", "--command", "poetry run poe spike-hosted", session="coord-1")
        status = json.loads(self.box.mc("--json", "status", session="coord-1").stdout)
        self.assertEqual((status["needs"][0]["kind"], status["needs"][0]["for"], status["needs"][0]["for_task"]), ("measurement", "crew-1", "10SE.2"))
        out = Path(self.box.tmp / "timings.txt")
        out.write_text("p50 120ms\np95 410ms\n")
        done = json.loads(self.box.mc("--json", "needs", "done", "1", "--result", f"@{out}", "--by-user", session="coord-1").stdout)
        self.assertEqual(done["forward_to"], "crew-1")
        self.assertEqual(done["result"], "p50 120ms\np95 410ms")
        long_why = "w" * 900
        self.box.mc("needs", "add", "--why", long_why, session="crew-1", cwd=self.box.worktree)
        needs = json.loads(self.box.mc("needs", "list", session="coord-1").stdout)
        self.assertEqual(len(needs[-1]["why"]), 900, "a why is no longer cut at 240 characters")

    def test_a_hosted_need_is_typed_from_the_main_checkout_not_the_crews_worktree(self):
        # 3 November 2026: the need named the crew's worktree, and all eight hosted calls failed with LegacyProjectNotLinkedError
        self.box.start()
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        (self.box.worktree / "apps" / "api").mkdir(parents=True)
        hosted = "supabase db query --linked 'select 1'"
        asked = json.loads(self.box.mc("--json", "needs", "add", "--why", "read the plan on hosted", "--command", hosted, "--cwd-hint", str(self.box.worktree / "apps" / "api"), session="crew-1", cwd=self.box.worktree).stdout)
        self.assertEqual(Path(asked["cwd"]).resolve(), (self.box.repo / "apps" / "api").resolve(), "the same place in the linked tree")
        self.assertEqual(Path(asked["cwd_moved_from"]).resolve(), (self.box.worktree / "apps" / "api").resolve())
        default = json.loads(self.box.mc("--json", "needs", "add", "--why", "read the plan on hosted", "--command", "poetry run poe spike-hosted", session="crew-1", cwd=self.box.worktree).stdout)
        self.assertEqual(Path(default["cwd"]).resolve(), self.box.repo.resolve(), "no hint: the worktree default is moved too")
        said = self.box.mc("needs", "add", "--why", "x", "--command", hosted, session="crew-1", cwd=self.box.worktree).stdout
        self.assertIn("moved from", said)

    def test_a_need_that_is_not_hosted_keeps_its_directory(self):
        self.box.start()
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        kept = json.loads(self.box.mc("--json", "needs", "add", "--why", "push it", "--command", "git push -u origin feat/a", session="crew-1", cwd=self.box.worktree).stdout)
        self.assertEqual(Path(kept["cwd"]).resolve(), self.box.worktree.resolve())
        self.assertNotIn("cwd_moved_from", kept)
        # a hosted command already aimed at the main checkout, or at a directory outside any repo, is left alone
        for place in (self.box.repo, self.box.tmp):
            again = json.loads(self.box.mc("--json", "needs", "add", "--why", "read hosted", "--command", "poe spike-hosted", "--cwd-hint", str(place), session="crew-1", cwd=self.box.worktree).stdout)
            self.assertEqual(again["cwd"], str(place))
            self.assertNotIn("cwd_moved_from", again)

    def test_a_started_need_leaves_the_needs_count_and_closes_with_its_result(self):
        # the CHIRPdb run: a four-hour hosted backfill the user had typed sat in the same bucket as needs they had not touched
        self.box.start()
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        self.box.mc("needs", "add", "--why", "run the embeddings backfill on hosted and paste the count", "--kind", "measurement", "--for", "10SE.2", "--command", "poetry run poe backfill", session="coord-1")
        self.box.mc("needs", "add", "--why", "push the branch", "--command", "git push -u origin feat/a", session="crew-1", cwd=self.box.worktree)
        self.assertEqual(self.box.mc("needs", "start", "1", session="crew-2", expect=1).returncode, 1, "another session may not mark it started")
        started = json.loads(self.box.mc("--json", "needs", "start", "1", "--note", "background task b7; 10SE.2 watches it", "--by-user", session="coord-1").stdout)
        self.assertEqual((started["status"], started["note"]), ("started", "background task b7; 10SE.2 watches it"))
        self.assertGreater(started["started_at"], 0)
        status = json.loads(self.box.mc("--json", "status", session="coord-1").stdout)
        self.assertEqual([(n["n"], n["status"]) for n in status["needs"]], [(1, "started"), (2, "open")], "a started need stays on the list, apart from the open ones")
        text = self.box.mc("status", session="coord-1").stdout
        self.assertIn("## Tribute agreed", text)
        self.assertIn("## Tribute owed", text)
        self.assertLess(text.index("## Tribute owed"), text.index("## Tribute agreed"))
        self.assertNotIn("poetry run poe backfill", text.split("## Tribute agreed")[1], "a running need shows no command to type")
        context = self.box.hook("session-start", {"source": "resume"}, session="coord-1", cwd=self.box.repo)
        self.assertIn("1 tribute owed", context)
        self.assertIn("running for the user: #1 since", context)
        again = json.loads(self.box.mc("--json", "needs", "start", "1", "--note", "10SE.2 watches it", session="coord-1").stdout)
        self.assertEqual((again["started_at"], again["note"]), (started["started_at"], "10SE.2 watches it"), "starting again only updates the note; the first start time stays")
        done = json.loads(self.box.mc("--json", "needs", "done", "1", "--result", "48112 rows", "--by-user", session="coord-1").stdout)
        self.assertEqual((done["status"], done["forward_to"], done["result"]), ("done", "crew-1", "48112 rows"))
        self.assertEqual(self.box.mc("needs", "start", "1", session="coord-1", expect=1).returncode, 1, "a done need cannot be started")

    def test_a_reissued_need_closes_the_one_it_supersedes_with_the_link(self):
        self.box.start()
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        self.box.mc("needs", "add", "--why", "run the backfill", "--command", "poetry run poe backfill", session="crew-1", cwd=self.box.worktree)
        self.assertEqual(self.box.mc("needs", "add", "--why", "x", "--supersedes", "9", session="crew-1", cwd=self.box.worktree, expect=1).returncode, 1)
        out = self.box.mc("needs", "add", "--why", "run the backfill with the dependency installed", "--command", "poetry install && poetry run poe backfill", "--supersedes", "1", session="crew-1", cwd=self.box.worktree).stdout
        self.assertIn("(supersedes #1)", out)
        needs = json.loads(self.box.mc("needs", "list", session="coord-1").stdout)
        self.assertEqual((needs[0]["status"], needs[0]["superseded_by"], needs[1]["supersedes"], needs[1]["status"]), ("done", 2, 1, "open"))
        self.assertEqual([n["n"] for n in json.loads(self.box.mc("--json", "status", session="coord-1").stdout)["needs"]], [2])
        # the other direction: the successor already exists, so done names it
        self.box.mc("needs", "add", "--why", "third try", session="crew-1", cwd=self.box.worktree)
        self.assertEqual(self.box.mc("needs", "done", "2", "--superseded-by", "9", session="coord-1", expect=1).returncode, 1)
        self.assertIn("cannot supersede itself", self.box.mc("needs", "done", "2", "--superseded-by", "2", session="coord-1", expect=1).stdout)
        self.assertIn("is paid", self.box.mc("needs", "done", "2", "--superseded-by", "1", session="coord-1", expect=1).stdout, "a done need cannot be the successor")
        out = self.box.mc("needs", "done", "2", "--superseded-by", "3", session="coord-1").stdout
        self.assertIn("tribute #2 superseded by #3", out)
        needs = json.loads(self.box.mc("needs", "list", session="coord-1").stdout)
        self.assertEqual((needs[1]["status"], needs[1]["superseded_by"]), ("done", 3))
        self.assertEqual(needs[2]["supersedes"], 2, "the done path writes the back-link too")
        self.assertEqual(needs[1]["supersedes"], 1, "a successor that already re-issues one need keeps that link")
        # each link flag belongs to one action; on the wrong one it is refused, and nothing is written
        before = self.box.mc("needs", "list", session="coord-1").stdout
        self.assertIn("--superseded-by belongs on needs done", self.box.mc("needs", "add", "--why", "x", "--superseded-by", "3", session="crew-1", cwd=self.box.worktree, expect=1).stdout)
        self.assertIn("--supersedes belongs on needs add", self.box.mc("needs", "done", "3", "--supersedes", "2", session="coord-1", expect=1).stdout)
        self.assertIn("--supersedes belongs on needs add", self.box.mc("needs", "start", "3", "--supersedes", "2", session="coord-1", expect=1).stdout)
        self.assertIn("--note belongs on needs start", self.box.mc("needs", "done", "3", "--note", "x", session="coord-1", expect=1).stdout)
        self.assertIn("--note belongs on needs start", self.box.mc("needs", "add", "--why", "x", "--note", "n", session="crew-1", cwd=self.box.worktree, expect=1).stdout)
        self.assertIn("--result belongs on needs done", self.box.mc("needs", "start", "3", "--result", "48112 rows", session="coord-1", expect=1).stdout, "start typed where done was meant does not drop the paste")
        self.assertEqual(self.box.mc("needs", "list", session="coord-1").stdout, before)
        events = [json.loads(line) for line in next(self.box.ledger_root.glob("*/log.jsonl")).read_text().splitlines()]
        self.assertEqual([e["by"] for e in events if e.get("event") == "need-superseded"], [2, 3])
        kinds = [(e["event"], e.get("n")) for e in events if e["event"] in ("need", "need-superseded")]
        self.assertLess(kinds.index(("need", 2)), kinds.index(("need-superseded", 1)), "the reissue is logged before the need it closes")
        # a need the user already closed keeps its close time when a later attempt names it
        self.box.mc("needs", "done", "3", session="coord-1")
        closed_at = json.loads(self.box.mc("needs", "list", session="coord-1").stdout)[2]["done_at"]
        time.sleep(0.05)
        self.box.mc("needs", "add", "--why", "fourth try", "--supersedes", "3", session="crew-1", cwd=self.box.worktree)
        third = json.loads(self.box.mc("needs", "list", session="coord-1").stdout)[2]
        self.assertEqual((third["done_at"], third["superseded_by"]), (closed_at, 4))
        # a need already superseded is not re-pointed by either path
        self.assertIn("already superseded by #4", self.box.mc("needs", "add", "--why", "fifth", "--supersedes", "3", session="crew-1", cwd=self.box.worktree, expect=1).stdout)
        self.assertIn("already superseded by #4", self.box.mc("needs", "done", "3", "--superseded-by", "4", session="coord-1", expect=1).stdout)
        # a second plain done (closed first, the result pasted later) keeps the first close time
        time.sleep(0.05)
        later = json.loads(self.box.mc("--json", "needs", "done", "3", "--result", "the paste", "--by-user", session="coord-1").stdout)
        self.assertEqual((later["done_at"], later["result"]), (closed_at, "the paste"))

    def test_a_reissue_keeps_the_old_needs_kind_recipient_and_directory_but_not_its_command(self):
        # a measurement re-issued the way coordinate 3a writes it used to come back as a plain action for the coordinator
        self.box.start()
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        self.box.mc("needs", "add", "--why", "run the backfill and paste the count", "--kind", "measurement", "--for", "10SE.2", "--cwd-hint", "/x/apps/api", "--command", "poetry run poe backfill", session="coord-1")
        again = json.loads(self.box.mc("--json", "needs", "add", "--why", "run it with the dependency installed", "--supersedes", "1", session="coord-1").stdout)
        self.assertEqual((again["kind"], again["for"], again["for_task"], again["cwd"], again["command"]), ("measurement", "crew-1", "10SE.2", "/x/apps/api", ""))
        done = json.loads(self.box.mc("--json", "needs", "done", "2", "--result", "48112 rows", "--by-user", session="coord-1").stdout)
        self.assertEqual(done["forward_to"], "crew-1", "the result still goes to the session that wanted it")
        third = json.loads(self.box.mc("--json", "needs", "add", "--why", "third", "--kind", "action", "--cwd-hint", "/other", "--command", "x", "--supersedes", "2", session="coord-1").stdout)
        self.assertEqual((third["kind"], third["cwd"], third["command"], third["for"]), ("action", "/other", "x", "crew-1"), "an explicit flag wins; the recipient carries")
        # the session a measurement is for may re-issue it, the way the crew skill says; any other session is still refused
        self.box.mc("join", "--task", "10SE.3", "--branch", "feat/b", session="crew-2", cwd=self.box.worktree)
        self.box.mc("needs", "add", "--why", "run the spike and paste the timings", "--kind", "measurement", "--for", "10SE.2", "--command", "poe spike", session="coord-1")
        self.assertEqual(self.box.mc("needs", "add", "--why", "x", "--supersedes", "4", session="crew-2", cwd=self.box.worktree, expect=1).returncode, 1)
        mine = json.loads(self.box.mc("--json", "needs", "add", "--why", "run the spike with the index built", "--command", "poe build-index && poe spike", "--supersedes", "4", session="crew-1", cwd=self.box.worktree).stdout)
        self.assertEqual((mine["supersedes"], mine["for"], mine["kind"]), (4, "crew-1", "measurement"))
        # the coordinator has no session row, so a crew need it re-issues keeps the crew's task tag on the board
        self.box.mc("needs", "add", "--why", "push the branch", "--command", "git push -u origin feat/a", session="crew-1", cwd=self.box.worktree)
        reissued = json.loads(self.box.mc("--json", "needs", "add", "--why", "push it after the rebase", "--command", "git push -f", "--supersedes", "6", session="coord-1").stdout)
        self.assertEqual(reissued["task"], "10SE.2")

    def test_a_grant_to_the_holder_extends_the_slot_without_force(self):
        self.box.start()
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        self.box.mc("grant", "local-db", "--to", "10SE.2", "--minutes", "10", session="coord-1")
        before = json.loads(self.box.mc("--json", "status", session="coord-1").stdout)["slots"][0]["until"]
        out = self.box.mc("grant", "local-db", "--to", "10SE.2", "--minutes", "20", session="coord-1").stdout
        self.assertIn("extended", out)
        after = json.loads(self.box.mc("--json", "status", session="coord-1").stdout)["slots"][0]
        self.assertGreater(after["until"], before + 19 * 60)
        self.assertEqual(after["holder"], "crew-1")
        self.assertIn('"event": "extend"', next(self.box.ledger_root.glob("*/log.jsonl")).read_text())
        # the holder asks for more time the way the crew skill says, with a request; the extension answers it, so the request leaves the board,
        # and a grant with no minutes of its own takes the request's rather than the default 15 (the request is gone by then)
        self.box.mc("request", "local-db", "--minutes", "20", "--what", "more time for the second reset", session="crew-1", cwd=self.box.worktree)
        self.assertEqual(len(json.loads(self.box.mc("--json", "status", session="coord-1").stdout)["requests"]), 1)
        before = after["until"]
        self.box.mc("grant", "local-db", "--to", "10SE.2", session="coord-1")
        status = json.loads(self.box.mc("--json", "status", session="coord-1").stdout)
        self.assertEqual(status["requests"], [], "16ID.1's request sat an hour after its extension and release in November 2026")
        self.assertGreater(status["slots"][0]["until"], before + 19 * 60)
        # a request still open at the release goes with the slot
        self.box.mc("request", "local-db", "--minutes", "5", "--what", "one more", session="crew-1", cwd=self.box.worktree)
        self.box.mc("release", "local-db", session="crew-1", cwd=self.box.worktree)
        self.assertEqual(json.loads(self.box.mc("--json", "status", session="coord-1").stdout)["requests"], [])

    def test_an_unlisted_crew_task_is_planned_as_such_and_the_claim_check_skips_it(self):
        self._roadmap_repo_with_origin(claim_on_branch=False, listed=False)
        self.box.start()
        self.box.mc("crew", "add", "--task", "UXR", "--branch", "feat/a", "--unlisted", session="coord-1")
        self.assertTrue(json.loads(self.box.mc("crew", "list", session="coord-1").stdout)[0]["unlisted"])
        self.box.mc("join", "--task", "UXR", "--branch", "feat/a", session="crew-1")
        self.box.mc("report", "--state", "pr-ready", "--pr", "262", session="crew-1")
        result = self._reconcile_with(self._gh(self._open(262)))
        self.assertEqual([item["kind"] for item in result["drift"]], [], "neither claim-missing nor the unlisted note: the plan says so")

    # the ledger without git: a macOS update removed the Command Line Tools on 30 October 2026 and every command refused

    def test_the_checkout_and_the_remote_are_found_without_running_git(self):
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        git(self.box.repo, "remote", "add", "origin", "https://github.com/Someone/a-repo.git")
        # the walk itself, asked by name: toplevel and main_checkout go through git while it works
        root, common = mc_module.git_dir_of(self.box.worktree)
        self.assertEqual(root, self.box.worktree.resolve())
        self.assertEqual(common, (self.box.repo / ".git").resolve(), "a linked worktree's .git file names the common dir")
        self.assertEqual(common.parent, self.box.repo.resolve(), "whose parent is the main checkout")
        root, common = mc_module.git_dir_of(self.box.repo / ".claude")
        self.assertEqual((root, common), (self.box.repo.resolve(), (self.box.repo / ".git").resolve()))
        self.assertIsNone(mc_module.git_dir_of(self.box.tmp))
        self.assertEqual(mc_module.main_checkout(self.box.worktree), self.box.repo.resolve())
        self.assertEqual(mc_module.remote_repo(self.box.repo), "Someone/a-repo")
        self.assertEqual(mc_module.remote_repo(self.box.worktree), "Someone/a-repo")
        mc_module._GIT_PROBLEM.clear()
        self.assertEqual(mc_module.gh_repo_args(self.box.worktree), [], "while git works, gh makes its own choice of repository")
        self.assertEqual(mc_module.gh_api_repo(self.box.worktree), "{owner}/{repo}")
        git(self.box.repo, "remote", "set-url", "origin", "git@github.com:Someone/a-repo.git")
        self.assertEqual(mc_module.remote_repo(self.box.repo), "Someone/a-repo", "the ssh form parses too")
        # a fork-shaped checkout: the remote chosen is the one gh would choose
        git(self.box.repo, "remote", "add", "upstream", "https://github.com/Org/the-real-one.git")
        self.assertEqual(mc_module.remote_repo(self.box.repo), "Org/the-real-one", "upstream beats origin, as it does for gh")
        git(self.box.repo, "remote", "add", "github", "https://github.com/Other/mirror.git")
        self.assertEqual(mc_module.remote_repo(self.box.repo), "Org/the-real-one", "upstream beats github")
        git(self.box.repo, "config", "remote.origin.gh-resolved", "base")
        self.assertEqual(mc_module.remote_repo(self.box.repo), "Someone/a-repo", "the remote gh repo set-default marked wins over everything")
        # the base is not a remote at all (a fork clone whose parent was picked): gh writes the base's owner/repo as the marker
        git(self.box.repo, "config", "remote.origin.gh-resolved", "Org/the-parent")
        self.assertEqual(mc_module.remote_repo(self.box.repo), "Org/the-parent", "a spelt-out marker names the base itself")
        git(self.box.repo, "config", "--unset", "remote.origin.gh-resolved")
        git(self.box.repo, "remote", "remove", "upstream")
        self.assertEqual(mc_module.remote_repo(self.box.repo), "Other/mirror", "github beats origin")
        # a second section for one remote merges with the first, as git reads it; a key at column one still parses
        with (self.box.repo / ".git" / "config").open("a") as config:
            config.write('[remote "github"]\ngh-resolved = base\n')
        self.assertEqual(mc_module.remote_repo(self.box.repo), "Other/mirror", "the url from the first section and the marker from the second belong to one remote")
        # a comment line inside a section does not end it: the marker after it still counts
        git(self.box.repo, "config", "--unset", "remote.github.gh-resolved")
        git(self.box.repo, "remote", "set-url", "origin", "https://github.com/Someone/a-repo.git")
        with (self.box.repo / ".git" / "config").open("a") as config:
            config.write('[remote "origin"]\n\t# chosen by hand\n\tgh-resolved = base\n')
        self.assertEqual(mc_module.remote_repo(self.box.repo), "Someone/a-repo", "the marker after a comment line is read")
        # a lone remote under a name gh does not rank is still the one gh takes when it cannot prompt
        (self.box.repo / ".git" / "config").write_text('[core]\n\tbare = false\n[remote "fork"]\n\turl = https://github.com/A/b.git\n\tfetch = +refs/heads/*:refs/remotes/fork/*\n')
        self.assertEqual(mc_module.remote_repo(self.box.repo), "A/b", "an unranked remote is taken ahead of none")
        (self.box.repo / ".git" / "config").write_text('[core]\n\tbare = false\n[remote "origin"]\n\turl = https://example.org/not/github.git\n')
        self.assertIsNone(mc_module.remote_repo(self.box.repo), "a remote that is not on GitHub names nothing")

    def test_a_path_typed_in_another_case_maps_to_the_canonical_ledger_while_git_works(self):
        """git's spelling of the checkout is what the ledger slug is built from; the .git walk returns the path as typed, so it is the fallback, never the first answer."""
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        swapped = Path(str(self.box.repo).swapcase())
        if not swapped.is_dir():
            self.skipTest("this volume is case-sensitive, so the other spelling is a different directory")
        self.assertEqual(mc_module.main_checkout(swapped), self.box.repo.resolve())
        self.assertEqual(mc_module.slug_of(mc_module.main_checkout(swapped)), mc_module.slug_of(self.box.repo.resolve()))

    def test_the_ledger_board_needs_and_slots_work_while_git_is_a_stub(self):
        """Apple's git stub prints an xcode-select prompt and exits 1; the run on disk is intact and every ledger command still answers."""
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.box.mc("join", "--planned", session="crew-1", cwd=self.box.worktree)
        stub = self.box.tmp / "stub"
        stub.mkdir()
        (stub / "git").write_text("#!/bin/sh\necho 'xcode-select: note: no developer tools were found at /Applications/Xcode.app' >&2\nexit 1\n")
        (stub / "git").chmod(0o755)
        (stub / "xcode-select").write_text("#!/bin/sh\nexit 2\n")
        (stub / "xcode-select").chmod(0o755)
        real = self.box.env["PATH"]
        self.box.env["PATH"] = f"{stub}:{real}"
        try:
            status = json.loads(self.box.mc("--json", "status", session="coord-1").stdout)
            self.assertIsNotNone(status["run"], "the run is read from the ledger, not from git")
            self.assertIn("git is not working", status["git_problem"])
            self.assertIn("xcode-select --install", status["git_problem"])
            self.assertEqual([s["task"] for s in status["sessions"]], ["10SE.2"])
            self.box.mc("needs", "add", "--why", "run xcode-select --install", "--command", "xcode-select --install", session="crew-1", cwd=self.box.worktree)
            self.box.mc("request", "local-db", "--minutes", "5", "--what", "reset", session="crew-1", cwd=self.box.worktree)
            self.box.mc("grant", "local-db", "--to", "10SE.2", session="coord-1")
            self.box.mc("report", "--state", "working", "--summary", "carrying on", session="crew-1", cwd=self.box.worktree)
            text = self.box.mc("status", session="coord-1").stdout
            self.assertTrue(text.startswith("WARNING: git is not working"), text[:80])
            self.assertIn("| local-db |", text)
            hook = self.box.hook("session-start", {}, session="crew-1")
            self.assertIn("this worktree is raider 10SE.2", hook, "the hook finds the planned worktree without git")
            self.box.mc("report", "--state", "done", "--pr", "280", session="crew-1", cwd=self.box.worktree)
            (self.box.sessions / "crew-1.json").unlink()
            refused = self.box.mc("retire", "10SE.2", session="coord-1", expect=1).stdout
            self.assertIn("retire needs git", refused)
            self.assertIn("xcode-select --install", refused)
            self.box.env["PATH"] = f"{stub}:{real}"
            mc_module, real_sh = self._module(self._gh(self._merged(280)))
            mc_module._GIT_PROBLEM.clear()
            os.environ["PATH"] = f"{stub}:{real}"
            try:
                result = mc_module.reconcile(mc_module.ledger_for(self.box.repo))
            finally:
                os.environ["PATH"] = real
                mc_module._GIT_PROBLEM.clear()
                self._restore(mc_module, real_sh)
            kinds = [item["kind"] for item in result["drift"]]
            self.assertIn("git-unavailable", kinds)
            self.assertNotIn("claim-missing", kinds, "the claim check waits for git instead of falling over")
            # with git broken, gh is told the repository outright, from the config file
            git_path = f"{stub}:{real}"
            os.environ["PATH"] = git_path
            try:
                mc_module._GIT_PROBLEM.clear()
                self.assertEqual(mc_module.gh_repo_args(self.box.repo), [], "no GitHub remote on file yet")
                with (self.box.repo / ".git" / "config").open("a") as config:
                    config.write('[remote "origin"]\n\turl = https://github.com/Someone/a-repo.git\n')
                self.assertEqual(mc_module.gh_repo_args(self.box.repo), ["--repo", "Someone/a-repo"])
                self.assertEqual(mc_module.gh_api_repo(self.box.repo), "Someone/a-repo")
            finally:
                os.environ["PATH"] = real
                mc_module._GIT_PROBLEM.clear()
        finally:
            self.box.env["PATH"] = real

    def test_a_task_id_shared_with_a_ghost_row_resolves_to_the_row_still_working(self):
        """17SE.1 on 3 November 2026: a stray session joined the worktree, closed and was marked done; retire and grant then refused the task id as ambiguous."""
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        self.box.start()
        self.box.mc("crew", "add", "--task", "17SE.1", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.box.mc("join", "--planned", session="crew-1", cwd=self.box.worktree)
        # a stray session starts in the same worktree while the real one is live, so it gets a row of its own, then closes
        self.box.register("ghost", "stray", str(self.box.worktree))
        self.box.mc("join", "--planned", session="ghost", cwd=self.box.worktree)
        (self.box.sessions / "ghost.json").unlink()
        self.box.mc("report", "--for", "ghost", "--state", "done", session="coord-1")
        mc_module.SESSIONS_DIR = self.box.sessions
        try:
            sessions = {p.stem: json.loads(p.read_text()) for p in next(self.box.ledger_root.glob("*/sessions")).glob("*.json")}
            self.assertEqual(mc_module.resolve_session("17SE.1", sessions), "crew-1", "the done ghost is passed over")
            # a real tie: two rows still working, and the refusal names each with its state and worktree
            self.box.register("crew-2", "second", str(self.box.repo))
            sessions["crew-2"] = {**sessions["crew-1"], "session_id": "crew-2", "worktree": str(self.box.repo)}
            with self.assertRaises(mc_module.Refusal) as refused:
                mc_module.resolve_session("17SE.1", sessions)
            self.assertIn("crew-1 (", str(refused.exception))
            self.assertIn("crew-2 (", str(refused.exception))
            self.assertIn("name the one you mean by its id", str(refused.exception))
            # both still working, the PR-bearing session gone and the other live in its worktree: the live one can hear a grant, so it wins
            (self.box.sessions / "crew-1.json").unlink()
            sessions["crew-1"]["pr"] = 301
            self.assertEqual(mc_module.resolve_session("17SE.1", sessions), "crew-2", "the live owner is taken before the PR-bearing row")
            sessions["crew-1"]["pr"] = None
            self.box.register("crew-1", "17se1", str(self.box.worktree))
        finally:
            mc_module.SESSIONS_DIR = Path(os.environ.get("CLAUDE_SESSIONS_DIR", str(mc_module.SESSIONS_DIR)))
        # the CLI paths that hit it on the live run
        out = self.box.mc("grant", "local-db", "--to", "17SE.1", session="coord-1").stdout
        self.assertIn("granted to 17SE.1", out)
        # retire's shape: the real row is done too, and the ghost has no PR; the task id still names the real row
        self.box.mc("release", "local-db", session="crew-1", cwd=self.box.worktree)
        self.box.mc("report", "--state", "done", "--pr", "300", session="crew-1", cwd=self.box.worktree)
        (self.box.sessions / "crew-1.json").unlink()
        sessions = {p.stem: json.loads(p.read_text()) for p in next(self.box.ledger_root.glob("*/sessions")).glob("*.json")}
        self.assertEqual({s["state"] for s in sessions.values()}, {"done"})
        mc_module.SESSIONS_DIR = self.box.sessions
        try:
            self.assertEqual(mc_module.resolve_session("17SE.1", sessions), "crew-1", "the PR-bearing row is the one that did the work")
        finally:
            mc_module.SESSIONS_DIR = Path(os.environ.get("CLAUDE_SESSIONS_DIR", str(mc_module.SESSIONS_DIR)))
        refused = self.box.mc("retire", "17SE.1", "--dry-run", session="coord-1", expect=None)
        self.assertNotIn("matches several sessions", refused.stdout, "retire resolves the task; whatever it then says is about the row itself")

    def test_an_approval_the_watcher_sees_is_pending_until_the_pr_lands(self):
        self.box.start()
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        self.box.mc("report", "--state", "pr-ready", "--pr", "290", session="crew-1", cwd=self.box.worktree)
        approved = self._view(reviews=[{"author": {"login": "maxitect"}, "state": "APPROVED", "submittedAt": "x"}], decision="APPROVED", checks=[("ci", "SUCCESS")])
        code, out = self._watch(self._gh_watch([self._view(checks=[("ci", "SUCCESS")]), self._view(checks=[("ci", "SUCCESS")]), approved]))
        self.assertEqual(code, 0, out)
        pending = json.loads(self.box.mc("pending", "list", session="coord-1").stdout)
        self.assertEqual([(p["kind"], p["pr"]) for p in pending], [("approval", 290)])
        self.assertIn("approved by maxitect", pending[0]["text"])
        result = self._reconcile_with(self._gh(self._open(290)))
        unlanded = [item for item in result["drift"] if item["kind"] == "approved-unlanded"]
        self.assertEqual(len(unlanded), 1)
        self.assertIn("`/pr-land 290`", unlanded[0]["detail"])
        # the merge closes it without anyone marking it done
        result = self._reconcile_with(self._gh(self._merged(291)))  # a different number keeps the facts cache out of the way
        self.box.mc("report", "--state", "done", "--pr", "291", session="crew-1", cwd=self.box.worktree)
        pending = json.loads(self.box.mc("pending", "list", session="coord-1").stdout)
        self.assertEqual(len(pending), 1, "the item is for 290, which is still open")
        merged_290 = self._merged(290)
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        mc_module.PR_CACHE_SECONDS, real_cache = 0, mc_module.PR_CACHE_SECONDS
        try:
            self.box.mc("report", "--state", "done", "--pr", "290", session="crew-1", cwd=self.box.worktree)
            result = self._reconcile_with(self._gh(merged_290))
        finally:
            mc_module.PR_CACHE_SECONDS = real_cache
        self.assertNotIn("approved-unlanded", [item["kind"] for item in result["drift"]])
        self.assertEqual(json.loads(self.box.mc("pending", "list", session="coord-1").stdout), [], "closed by the merge")

    def _watching_session(self, pr):
        self.box.start()
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1", cwd=self.box.worktree)
        self.box.mc("report", "--state", "pr-ready", "--pr", str(pr), session="crew-1", cwd=self.box.worktree)

    def _crew_watch_record(self):
        return json.loads(list(self.box.ledger_root.glob("*/sessions/crew-1.json"))[0].read_text())["watch"]

    def test_a_signalled_watcher_records_the_signal_and_says_so(self):
        import signal
        self._watching_session(260)
        checks = [("ci", "SUCCESS")]
        base = self._gh_watch([self._view(checks=checks)])

        def killing_sh(argv, timeout=8, cwd=None):
            if argv[:3] == ["gh", "pr", "view"] and getattr(killing_sh, "calls", 0) >= 1:
                os.kill(os.getpid(), signal.SIGTERM)
            if argv[:3] == ["gh", "pr", "view"]:
                killing_sh.calls = getattr(killing_sh, "calls", 0) + 1
            return base(argv, timeout, cwd)
        before = signal.getsignal(signal.SIGTERM)
        code, out = self._watch(killing_sh)
        self.assertEqual(code, 128 + signal.SIGTERM)
        self.assertIn("something outside it ended the process", out)
        self.assertIs(signal.getsignal(signal.SIGTERM), before, "the handler is put back once the watch returns")
        watch = self._crew_watch_record()
        self.assertEqual((watch["status"], watch["signal"], watch["pid"]), ("killed", int(signal.SIGTERM), None))

    def test_a_watcher_stopped_on_request_says_not_to_re_arm(self):
        import signal
        self._watching_session(267)
        base = self._gh_watch([self._view(checks=[("ci", "SUCCESS")])])

        def stopping_sh(argv, timeout=8, cwd=None):
            if argv[:3] == ["gh", "pr", "view"] and getattr(stopping_sh, "calls", 0) >= 1:
                # what `watch --stop` does: mark the row, then signal
                row_path = list(self.box.ledger_root.glob("*/sessions/crew-1.json"))[0]
                row = json.loads(row_path.read_text())
                row["watch"]["stopping"] = True
                row_path.write_text(json.dumps(row))
                os.kill(os.getpid(), signal.SIGTERM)
            if argv[:3] == ["gh", "pr", "view"]:
                stopping_sh.calls = getattr(stopping_sh, "calls", 0) + 1
            return base(argv, timeout, cwd)
        code, out = self._watch(stopping_sh)
        self.assertEqual(code, 128 + signal.SIGTERM)
        self.assertIn("do not re-arm", out)
        self.assertNotIn("Re-arm the watch", out)
        self.assertEqual(self._crew_watch_record()["status"], "stopped")

    def test_watch_stop_clears_its_marker_when_the_watcher_had_already_exited(self):
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        self._watching_session(270)
        self._set_watch(270, "watching", 424242)
        real = (mc_module.sh, mc_module.os.kill, mc_module.LEDGER_ROOT, mc_module.SESSIONS_DIR)

        def gone(_pid, _sig):
            raise ProcessLookupError
        mc_module.sh = lambda argv, timeout=8, cwd=None: (0, "python3 warband.py watch")
        mc_module.os.kill = gone
        mc_module.LEDGER_ROOT, mc_module.SESSIONS_DIR = self.box.ledger_root, self.box.sessions
        try:
            ledger = mc_module.ledger_for(self.box.repo)
            code = mc_module.stop_watch(ledger, ledger.sessions()["crew-1"], 270)
        finally:
            mc_module.sh, mc_module.os.kill, mc_module.LEDGER_ROOT, mc_module.SESSIONS_DIR = real
        self.assertEqual(code, 0)
        self.assertNotIn("stopping", self._crew_watch_record(), "a marker nothing will read is not left behind")

    def test_a_stopping_marker_from_an_earlier_watcher_is_not_inherited(self):
        import signal
        self._watching_session(271)
        row_path = list(self.box.ledger_root.glob("*/sessions/crew-1.json"))[0]
        row = json.loads(row_path.read_text())
        row["watch"] = {"pr": 271, "status": "idle", "pid": None, "stopping": True, "seen": None}
        row_path.write_text(json.dumps(row))
        base = self._gh_watch([self._view(checks=[("ci", "SUCCESS")])])

        def killing_sh(argv, timeout=8, cwd=None):
            if argv[:3] == ["gh", "pr", "view"] and getattr(killing_sh, "calls", 0) >= 1:
                os.kill(os.getpid(), signal.SIGTERM)
            if argv[:3] == ["gh", "pr", "view"]:
                killing_sh.calls = getattr(killing_sh, "calls", 0) + 1
            return base(argv, timeout, cwd)
        code, out = self._watch(killing_sh)
        self.assertEqual(code, 128 + signal.SIGTERM)
        self.assertIn("Re-arm the watch", out, "an outside kill is still an outside kill")
        self.assertEqual(self._crew_watch_record()["status"], "killed")

    def test_a_signal_that_lands_while_the_ledger_lock_is_held_does_not_hang_the_watcher(self):
        import fcntl
        import signal
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        self._watching_session(268)
        real_save, calls = mc_module.Ledger.save_session, {"n": 0}

        def signalling_save(ledger, row):
            calls["n"] += 1
            if calls["n"] == 2:  # the record just before the poll loop, made while the lock is held
                os.kill(os.getpid(), signal.SIGTERM)
            return real_save(ledger, row)

        def too_slow(_number, _frame):
            raise AssertionError("the handler waited on the ledger lock its own process holds")
        mc_module.Ledger.save_session = signalling_save
        old_alarm = signal.signal(signal.SIGALRM, too_slow)
        signal.alarm(5)
        try:
            code, _out = self._watch(self._gh_watch([self._view(checks=[("ci", "SUCCESS")])]))
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_alarm)
            mc_module.Ledger.save_session = real_save
        self.assertEqual(code, 128 + signal.SIGTERM)
        with list(self.box.ledger_root.glob("*/run.lock"))[0].open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)  # raises if the watcher still holds it

    def test_a_watcher_that_returned_leaves_no_pid_and_no_watch_dead(self):
        self._watching_session(266)
        code, _out = self._watch(self._gh_watch([self._view(checks=[("ci", "SUCCESS")])]), "--once")
        self.assertEqual(code, 0)
        self.assertIsNone(self._crew_watch_record()["pid"])
        code, out = self._watch(self._gh_watch([self._view(checks=[("ci", "SUCCESS")])]), "--max-minutes", "0.0001")
        self.assertEqual(code, 0, out)
        self.assertIn("re-arm the watch", out)
        watch = self._crew_watch_record()
        self.assertEqual((watch["status"], watch["pid"]), ("idle", None))
        self.assertNotIn("watch-dead", [item["kind"] for item in self._reconcile_with(self._gh(self._open(266)))["drift"]])

    def test_watch_stop_refuses_a_session_with_no_watcher_of_its_own(self):
        self._watching_session(261)
        done = self.box.mc("watch", "--stop", "--pr", "261", session="crew-1", cwd=self.box.worktree, expect=None)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("no watcher recorded", done.stdout + done.stderr)

    def test_watch_stop_signals_only_the_pid_on_the_callers_own_row(self):
        self._watching_session(262)
        # a process whose command line reads `warband.py watch`, as a real watcher's does
        victim = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "warband.py", "watch"])
        bystander = subprocess.Popen(["sleep", "61"])
        try:
            self._set_watch(262, "watching", victim.pid)
            done = self.box.mc("watch", "--stop", "--pr", "262", session="crew-1", cwd=self.box.worktree)
            self.assertIn(f"pid {victim.pid}", done.stdout)
            victim.wait(timeout=5)
            self.assertIsNone(bystander.poll(), "another process is untouched")
            self.assertTrue(self._crew_watch_record()["stopping"], "the row says the stop was meant")
        finally:
            for proc in (victim, bystander):
                proc.kill()
                proc.wait()

    def test_watch_stop_stops_a_watcher_the_old_cli_started(self):
        """Review 5981937523: a watcher started as `mc.py watch` before the rename is still a watcher."""
        self._watching_session(263)
        old = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "mc.py", "watch", "--pr", "263"])
        try:
            self._set_watch(263, "watching", old.pid)
            done = self.box.mc("watch", "--stop", "--pr", "263", session="crew-1", cwd=self.box.worktree)
            self.assertNotIn("nothing to stop", done.stdout)
            self.assertIn(f"pid {old.pid}", done.stdout)
            old.wait(timeout=5)
        finally:
            old.kill()
            old.wait()

    def _set_watch(self, pr, status, pid):
        row_path = list(self.box.ledger_root.glob("*/sessions/crew-1.json"))[0]
        row = json.loads(row_path.read_text())
        row["watch"] = {"pr": pr, "status": status, "pid": pid}
        row_path.write_text(json.dumps(row))

    def test_watch_stop_leaves_a_finished_watch_and_a_foreign_command_line_alone(self):
        self._watching_session(269)
        matching = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "warband.py", "watch"])
        plain = subprocess.Popen(["sleep", "62"])
        try:
            self._set_watch(269, "ended", matching.pid)  # the watcher finished; a recycled pid must not be signalled
            done = self.box.mc("watch", "--stop", "--pr", "269", session="crew-1", cwd=self.box.worktree)
            self.assertIn("nothing to stop", done.stdout)
            self._set_watch(269, "watching", plain.pid)  # a live pid that is not a warband.py watcher
            done = self.box.mc("watch", "--stop", "--pr", "269", session="crew-1", cwd=self.box.worktree)
            self.assertIn("not a warband.py watcher", done.stdout)
            time.sleep(0.3)
            self.assertIsNone(matching.poll())
            self.assertIsNone(plain.poll())
        finally:
            for proc in (matching, plain):
                proc.kill()
                proc.wait()

    def test_reconcile_names_a_watcher_that_reads_watching_but_has_died(self):
        self._watching_session(263)
        gone = subprocess.Popen(["true"])
        gone.wait()
        row_path = list(self.box.ledger_root.glob("*/sessions/crew-1.json"))[0]
        row = json.loads(row_path.read_text())
        row["watch"] = {"pr": 263, "status": "watching", "pid": gone.pid}
        row_path.write_text(json.dumps(row))
        result = self._reconcile_with(self._gh(self._open(263)))
        dead = [item for item in result["drift"] if item["kind"] == "watch-dead"]
        self.assertEqual(len(dead), 1)
        self.assertIn(f"pid {gone.pid}", dead[0]["detail"])

    def test_an_approval_given_on_an_older_head_is_not_called_authorised(self):
        self._watching_session(264)
        run_path = list(self.box.ledger_root.glob("*/run.json"))[0]
        run = json.loads(run_path.read_text())
        run.setdefault("pending", []).append({"id": "a1", "n": 1, "kind": "approval", "pr": 264, "text": "t", "session_id": "crew-1", "head": "aaaaaaa1111", "status": "open", "at": 1.0})
        run_path.write_text(json.dumps(run))
        answer = self._open(264)
        answer["264"]["headRefOid"] = "bbbbbbb2222"
        result = self._reconcile_with(self._gh(answer))
        kinds = [item["kind"] for item in result["drift"]]
        self.assertIn("approved-stale", kinds)
        # no re-approval, so the note keeps the watcher's time for the recorded head
        self.assertRegex(next(item["detail"] for item in result["drift"] if item["kind"] == "approved-stale"), r"last approved at .+ on aaaaaaa and the head is now bbbbbbb")
        self.assertNotIn("approved-unlanded", kinds)

    def test_an_approval_renewed_at_the_new_head_is_not_called_stale(self):
        self._watching_session(264)
        run_path = list(self.box.ledger_root.glob("*/run.json"))[0]
        run = json.loads(run_path.read_text())
        run.setdefault("pending", []).append({"id": "a1", "n": 1, "kind": "approval", "pr": 264, "text": "t", "session_id": "crew-1", "head": "aaaaaaa1111", "status": "open", "at": 1.0})
        run_path.write_text(json.dumps(run))
        answer = self._open(264)
        answer["264"]["headRefOid"] = "bbbbbbb2222"
        answer["264"]["reviews"] = [{"author": {"login": "maxitect"}, "state": "APPROVED", "commit": {"oid": "bbbbbbb2222"}, "submittedAt": "2026-11-16T11:00:00Z"}]
        result = self._reconcile_with(self._gh(answer))
        kinds = [item["kind"] for item in result["drift"]]
        self.assertNotIn("approved-stale", kinds)
        self.assertIn("approved-unlanded", kinds)

    def test_a_stale_note_after_a_re_approval_names_the_commit_last_approved(self):
        # approved at a, re-approved at b, pushed to c: the diff owed a look starts at b, and the watcher's time belongs to a
        self._watching_session(264)
        run_path = list(self.box.ledger_root.glob("*/run.json"))[0]
        run = json.loads(run_path.read_text())
        run.setdefault("pending", []).append({"id": "a1", "n": 1, "kind": "approval", "pr": 264, "text": "t", "session_id": "crew-1", "head": "aaaaaaa1111", "status": "open", "at": 1.0})
        run_path.write_text(json.dumps(run))
        answer = self._open(264)
        answer["264"]["headRefOid"] = "ccccccc3333"
        answer["264"]["reviews"] = [{"author": {"login": "maxitect"}, "state": "APPROVED", "commit": {"oid": "bbbbbbb2222"}, "submittedAt": "2026-11-16T11:00:00Z"}]
        stale = [item for item in self._reconcile_with(self._gh(answer))["drift"] if item["kind"] == "approved-stale"]
        self.assertEqual(len(stale), 1)
        self.assertIn("last approved on bbbbbbb and the head is now ccccccc", stale[0]["detail"])

    def test_reconcile_fetches_the_pr_a_hold_waits_on(self):
        self._watching_session(264)
        ledger_dir = list(self.box.ledger_root.glob("*/run.json"))[0].parent
        (ledger_dir / "prs").mkdir(exist_ok=True)
        (ledger_dir / "prs" / "264.json").write_text(json.dumps({"number": 264, "task": "10SE.2", "hold": {"reason": "after #500", "lifts_on": [{"pr": 500}]}}))
        self._reconcile_with(self._gh({**self._open(264), **self._merged(500)}))
        cache = json.loads((ledger_dir / "pr-facts.json").read_text())
        self.assertEqual(cache["500"]["facts"]["state"], "MERGED")

    def test_an_approval_whose_hold_has_lifted_reads_as_unlanded_not_held(self):
        self._watching_session(264)
        ledger_dir = list(self.box.ledger_root.glob("*/run.json"))[0].parent
        run = json.loads((ledger_dir / "run.json").read_text())
        run.setdefault("pending", []).append({"id": "a1", "n": 1, "kind": "approval", "pr": 264, "text": "t", "session_id": "crew-1", "head": "", "status": "open", "at": 1.0})
        (ledger_dir / "run.json").write_text(json.dumps(run))
        (ledger_dir / "prs").mkdir(exist_ok=True)
        (ledger_dir / "prs" / "264.json").write_text(json.dumps({"number": 264, "task": "10SE.2", "hold": {"reason": "after #500", "lifts_on": [{"pr": 500}]}}))
        held = [item["kind"] for item in self._reconcile_with(self._gh({**self._open(264), **self._open(500)}))["drift"]]
        self.assertIn("approved-held", held)
        (ledger_dir / "pr-facts.json").unlink()  # #500 has merged since; the cached OPEN would otherwise stand for a minute
        lifted =[item["kind"] for item in self._reconcile_with(self._gh({**self._open(264), **self._merged(500)}))["drift"]]
        self.assertNotIn("approved-held", lifted)
        self.assertIn("approved-unlanded", lifted)

    def test_the_claim_check_stays_silent_without_a_roadmap(self):
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 224, state="done")
        result = self._reconcile_with(self._gh(self._merged(224)))
        self.assertEqual([item["kind"] for item in result["drift"]], [])

    def test_reconcile_cli_prints_nothing_to_reconcile_for_a_quiet_run(self):
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", session="coord-1")
        self.box.mc("join", "--task", "10SE.2", "--branch", "feat/a", session="crew-1")
        out = self.box.mc("reconcile").stdout
        self.assertIn("nothing to reconcile", out)
        self.assertIn("no PRs on the slate", out)
        self.assertEqual(self.box.mc("reconcile", cwd=self.box.tmp, expect=1).returncode, 1, "outside a repo is a refusal")

    def test_the_psql_probes_wait_no_longer_than_the_gh_lookups(self):
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        timeouts = []
        real_sh = mc_module.sh
        def recording_sh(argv, timeout=8, cwd=None):
            timeouts.append((argv[0], timeout))
            return 1, "down"
        mc_module.sh = recording_sh
        try:
            spec = {"probe": {"pg_activity": {"dsn": "postgres://x"}, "migrations": {"dsn": "postgres://x"}}}
            mc_module.probe_resource("local-db", spec)
        finally:
            mc_module.sh = real_sh
        self.assertEqual([name for name, _ in timeouts], ["psql", "psql"])
        self.assertTrue(all(timeout <= 3 for _, timeout in timeouts))


class Hooks(unittest.TestCase):
    def setUp(self):
        self.box = Sandbox()
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.box.mc("join", session="crew-1", cwd=self.box.worktree)

    def decision(self, command, **kw):
        out = self.box.hook("pre-tool-use", {"tool_name": "Bash", "tool_input": {"command": command}}, **kw)
        return json.loads(out)["hookSpecificOutput"] if out.strip() else None

    def test_a_gated_command_started_through_monitor_is_denied_like_a_bash_one(self):
        # Claude Code 2.1.314 runs hooks that match Bash on the Monitor tool's shell commands; its input carries the same `command` key
        out = self.box.hook("pre-tool-use", {"tool_name": "Monitor", "tool_input": {"command": "cd apps/api && poetry run poe db-reset-local-anyway", "description": "reset", "timeout_ms": 300000}})
        verdict = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(verdict["permissionDecision"], "deny")
        self.assertIn("free, but not granted to you", verdict["permissionDecisionReason"])
        # a WebSocket watch has no shell command, so there is nothing to gate
        self.assertEqual(self.box.hook("pre-tool-use", {"tool_name": "Monitor", "tool_input": {"ws": {"url": "wss://example.com/stream"}, "description": "events", "timeout_ms": 300000}}).strip(), "")

    def test_gated_command_without_slot_is_denied_and_recorded(self):
        verdict = self.decision("cd apps/api && poetry run poe db-reset-local-anyway")
        self.assertEqual(verdict["permissionDecision"], "deny")
        self.assertIn("free, but not granted to you", verdict["permissionDecisionReason"])
        status = json.loads(self.box.mc("--json", "status").stdout)
        self.assertEqual(status["requests"][0]["resource"], "local-db")
        self.assertEqual(status["requests"][0]["session_id"], "crew-1")

    def test_held_slot_in_own_worktree_passes_with_context(self):
        self.box.mc("grant", "local-db", "--to", "10SE.2", session="coord-1")
        verdict = self.decision("cd apps/api && poetry run poe db-reset-local-anyway")
        self.assertNotIn("permissionDecision", verdict)
        self.assertIn("you hold the dibs on the local Supabase stack", verdict["additionalContext"])

    def test_held_slot_from_another_directory_is_denied(self):
        self.box.mc("grant", "local-db", "--to", "10SE.2", session="coord-1")
        verdict = self.decision("poetry run poe db-reset-local-anyway", cwd=self.box.repo)
        self.assertEqual(verdict["permissionDecision"], "deny")
        self.assertIn("this command would run in", verdict["permissionDecisionReason"])

    def test_held_slot_moved_out_of_the_worktree_by_a_runner_is_denied(self):
        self.box.mc("grant", "local-db", "--to", "10SE.2", session="coord-1")
        gated = "poetry run poe db-reset-local-anyway"
        repo, worktree = self.box.repo, self.box.worktree
        relative = worktree.relative_to(repo)
        cases = [
            (f"env -C {repo} {gated}", worktree),
            (f"env -C{repo} {gated}", worktree),
            (f"env --chdir {repo} {gated}", worktree),
            (f"env --chdir={repo} {gated}", worktree),
            (f"env -iC{repo} {gated}", worktree),
            (f"env -0C{repo} {gated}", worktree),
            (f"env --c={repo} {gated}", worktree),
            (f"env --chd {repo} {gated}", worktree),
            (f"env -C {repo} sh -c '{gated}'", worktree),
            (f"env -C {worktree} {gated} && {gated}", repo),
            (f"command cd {repo} && {gated}", worktree),
            (f"cd {repo} && env cd {relative} && {gated}", worktree),
            (f"cd {repo} && nohup cd {relative} && {gated}", worktree),
        ]
        for command, cwd in cases:
            checked = json.loads(self.box.mc("check", "--command", command, session="crew-1", cwd=cwd).stdout)
            self.assertEqual(checked["decision"], "deny", command)
            self.assertFalse(checked["covered"], command)

    def test_runner_chdir_inside_the_worktree_stays_covered(self):
        self.box.mc("grant", "local-db", "--to", "10SE.2", session="coord-1")
        gated = "poetry run poe db-reset-local-anyway"
        for command in [f"env -C {self.box.worktree} {gated}", f"env -C apps/api {gated}", f"env --chdir=apps/api {gated}", f"env -iC{self.box.worktree} {gated}", f"env -i -C apps/api {gated}", f"env --chd=apps/api {gated}"]:
            checked = json.loads(self.box.mc("check", "--command", command, session="crew-1", cwd=self.box.worktree).stdout)
            self.assertTrue(checked["covered"], command)

    def test_runner_chdir_without_a_slot_is_denied(self):
        for command in ["env -C /elsewhere poetry run poe db-reset-local-anyway", "env --chdir=/elsewhere poetry run poe db-reset-local-anyway"]:
            self.assertEqual(self.decision(command)["permissionDecision"], "deny", command)

    def test_check_reports_coverage_for_the_mod(self):
        before = json.loads(self.box.mc("check", "--command", "cd apps/api && poetry run poe db-reset-local-anyway", session="crew-1", cwd=self.box.worktree).stdout)
        self.assertFalse(before["covered"])
        self.assertEqual(before["decision"], "deny")
        self.box.mc("grant", "local-db", "--to", "10SE.2", session="coord-1")
        after = json.loads(self.box.mc("check", "--command", "cd apps/api && poetry run poe db-reset-local-anyway", session="crew-1", cwd=self.box.worktree).stdout)
        self.assertTrue(after["covered"])
        self.assertEqual(after["resources"], ["local-db"])
        hosted = json.loads(self.box.mc("check", "--command", "poetry run poe smoke-search-hosted", session="crew-1", cwd=self.box.worktree).stdout)
        self.assertFalse(hosted["covered"])
        plain = json.loads(self.box.mc("check", "--command", "git status", session="crew-1", cwd=self.box.worktree).stdout)
        self.assertFalse(plain["covered"])
        self.assertIsNone(plain["decision"])

    def test_human_gate_adds_context_only(self):
        verdict = self.decision("poetry run poe smoke-search-hosted")
        self.assertNotIn("permissionDecision", verdict)
        self.assertIn("a taboo", verdict["additionalContext"])

    def test_by_user_on_a_command_line_is_denied(self):
        verdict = self.decision("python3 warband.py grant local-db --to me --by-user")
        self.assertEqual(verdict["permissionDecision"], "deny")

    def test_identity_overrides_on_an_mc_line_are_denied(self):
        for command in [
            "python3 warband.py grant local-db --to me --by",
            "python3 warband.py grant local-db --to me '--by-user'",
            'python3 warband.py grant local-db --to me "--by-user"',
            "python3 warband.py --session coord-1 grant local-db --to me",
            "python3 warband.py --session=coord-1 grant local-db --to me",
            "python3 warband.py --sess coord-1 grant local-db --to me",
            "CLAUDE_CODE_SESSION_ID=coord-1 python3 warband.py grant local-db --to me",
            "export CLAUDE_CODE_SESSION_ID=coord-1; python3 warband.py grant local-db --to me",
            "env CLAUDE_CODE_SESSION_ID=coord-1 python3 warband.py grant local-db --to me",
            "sh -c \"python3 warband.py grant local-db --to me --by-user\"",
        ]:
            self.assertEqual(self.decision(command)["permissionDecision"], "deny", command)

    def test_identity_overrides_on_the_old_mission_control_cli_are_denied(self):
        """Review 5976730930: while a raid is carried on from the old ledger, the cached 0.13.1 mc.py writes to the same root,
        so the guard holds for its name too."""
        old_cli = "/home/u/.claude/plugins/cache/goblin-mode/mission-control/0.13.1/scripts/mc.py"
        for command in [
            f"python3 {old_cli} grant local-db --to me --by-user",
            f"python3 {old_cli} --session coord-1 grant local-db --to me",
            f"CLAUDE_CODE_SESSION_ID=coord-1 python3 {old_cli} grant local-db --to me",
            "python3 mc.py grant local-db --to me --by-user",
        ]:
            self.assertEqual(self.decision(command)["permissionDecision"], "deny", command)
        self.assertIsNone(self.decision(f"python3 {old_cli} status --json"))

    def test_plain_mc_and_foreign_session_flags_are_not_denied(self):
        self.assertIsNone(self.decision("python3 warband.py status --json"))
        self.assertIsNone(self.decision("git log --session"))

    def test_a_subagent_is_gated_like_its_parent(self):
        command = "cd apps/api && poetry run poe db-reset-local-anyway"
        payload = {"tool_name": "Bash", "tool_input": {"command": command}, "agent_id": "agent-1"}
        verdict = json.loads(self.box.hook("pre-tool-use", payload))["hookSpecificOutput"]
        self.assertEqual(verdict["permissionDecision"], "deny")
        by_user = {"tool_name": "Bash", "tool_input": {"command": "python3 warband.py grant local-db --to me --by-user"}, "agent_id": "agent-1"}
        self.assertEqual(json.loads(self.box.hook("pre-tool-use", by_user))["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(self.box.hook("session-start", {"agent_id": "agent-1"}, session="crew-9"), "")

    def test_shell_wrapped_gated_command_is_denied_without_a_slot(self):
        self.assertEqual(self.decision("sh -c 'poetry run poe db-reset-local-anyway'")["permissionDecision"], "deny")

    def test_check_compound_and_substituted_lines_are_not_covered(self):
        self.box.mc("grant", "local-db", "--to", "10SE.2", session="coord-1")
        gated = "poetry run poe db-reset-local-anyway"
        for command in [
            f"cd apps/api && {gated} && git push --force origin main",
            f"{gated} ; rm -rf x",
            f"{gated} || true",
            f"echo hi | {gated}",
            f'{gated} "$(git push --force)"',
            f"{gated} `git push`",
            f"{gated} && git push 'unbalanced",
        ]:
            checked = json.loads(self.box.mc("check", "--command", command, session="crew-1", cwd=self.box.worktree).stdout)
            self.assertFalse(checked["covered"], command)
            self.assertIsNone(checked["decision"], command)

    def test_check_plain_gated_forms_stay_covered(self):
        self.box.mc("grant", "local-db", "--to", "10SE.2", session="coord-1")
        gated = "poetry run poe db-reset-local-anyway"
        for command in [gated, f"cd apps/api && {gated}", f"FOO=1 {gated}", f"{gated} > out.log 2>&1", f"{gated} && {gated}", f"sh -c '{gated}'"]:
            checked = json.loads(self.box.mc("check", "--command", command, session="crew-1", cwd=self.box.worktree).stdout)
            self.assertTrue(checked["covered"], command)

    def test_unrelated_and_no_run_are_silent(self):
        self.assertIsNone(self.decision("git status"))
        self.box.mc("end", session="coord-1")
        self.assertIsNone(self.decision("poetry run poe db-reset-local-anyway"))

    def test_session_start_names_the_brief_and_the_coordinator(self):
        (self.box.ledger_root / self.box.ledger_root.iterdir().__next__().name / "briefs").mkdir(parents=True, exist_ok=True)
        brief = Path(json.loads(self.box.mc("crew", "list").stdout)[0]["brief"])
        brief.parent.mkdir(parents=True, exist_ok=True)
        brief.write_text("# brief\n")
        text = self.box.hook("session-start", {}, session="crew-9")
        self.assertIn("raider 10SE.2", text)
        self.assertIn("mission control", text)
        self.assertIn(str(brief), text)
        coord = self.box.hook("session-start", {}, session="coord-1", cwd=self.box.repo)
        self.assertIn("is the chief of raid search", coord)
        self.assertEqual(self.box.hook("session-start", {}, session="x", cwd=self.box.repo), "")


class PushGate(unittest.TestCase):
    """`git push` is refused until `warband.py gate` has recorded green for the commit; no run is needed."""

    def setUp(self):
        self.box = Sandbox()
        self.repo = self.box.repo
        # the sandbox's worktree directory sits inside the repo and would count as untracked noise to the gate
        with open(self.repo / ".git" / "info" / "exclude", "a") as handle:
            handle.write("/.claude/worktrees/\n")

    def set_gate(self, commands, exempt=None):
        path = self.repo / ".claude" / "goblin-warband.json"
        config = json.loads(path.read_text())
        config["commands"] = commands
        config["push_gate"] = {"commands": list(commands), "exempt": exempt or []}
        path.write_text(json.dumps(config))
        git(self.repo, "commit", "-qam", "gate config")

    def verdict(self, command):
        out = self.box.hook("pre-tool-use", {"tool_name": "Bash", "tool_input": {"command": command}}, session="coord-1", cwd=self.repo)
        return json.loads(out)["hookSpecificOutput"] if out.strip() else None

    def refused(self, command="git push origin main"):
        verdict = self.verdict(command)
        return verdict["permissionDecisionReason"] if verdict and verdict.get("permissionDecision") == "deny" else None

    def head(self):
        return subprocess.run(["git", "-C", str(self.repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()

    def test_a_repo_without_push_gate_pushes_freely(self):
        path = self.repo / ".claude" / "goblin-warband.json"
        config = json.loads(path.read_text())
        config.pop("push_gate", None)  # the example config the sandbox copies opts in
        path.write_text(json.dumps(config))
        git(self.repo, "commit", "-qam", "no gate")
        self.assertIsNone(self.refused())

    def test_a_push_without_a_record_is_refused_and_names_the_command(self):
        self.set_gate({"test": "true"})
        reason = self.refused()
        self.assertIn("no green record", reason)
        self.assertIn("warband.py gate", reason)

    def test_green_gate_lets_the_push_through_until_the_next_commit(self):
        self.set_gate({"test": "true", "lint": "true"})
        done = self.box.mc("gate", cwd=self.repo)
        self.assertIn("push gate green", done.stdout)
        self.assertIsNone(self.refused())
        (self.repo / "README.md").write_text("changed\n")
        git(self.repo, "commit", "-qam", "next")
        self.assertIn("no green record", self.refused())

    def test_red_gate_refuses_names_the_failing_step_and_stops_there(self):
        self.set_gate({"test": "false", "lint": "touch ran-lint"})
        done = self.box.mc("gate", cwd=self.repo, expect=1)
        self.assertIn("push gate red", done.stdout)
        self.assertFalse((self.repo / "ran-lint").exists(), "steps after a failure do not run")
        self.assertIn("was red", self.refused())
        self.assertIn("(test)", self.refused())

    def test_a_push_while_the_gate_runs_is_refused(self):
        self.set_gate({"test": "true"})
        folder = self.repo / ".git" / "goblin-warband" / "gate"
        folder.mkdir(parents=True)
        (folder / f"{self.head()}.running").write_text(json.dumps({"pid": os.getpid()}))
        self.assertIn("still running", self.refused())

    def test_a_dead_lock_does_not_block(self):
        self.set_gate({"test": "true"})
        self.box.mc("gate", cwd=self.repo)
        folder = self.repo / ".git" / "goblin-warband" / "gate"
        (folder / f"{self.head()}.running").write_text(json.dumps({"pid": 99999999}))
        self.assertIsNone(self.refused())

    def test_the_gate_refuses_to_run_over_uncommitted_changes(self):
        self.set_gate({"test": "true"})
        (self.repo / "README.md").write_text("dirty\n")
        done = self.box.mc("gate", cwd=self.repo, expect=1)
        self.assertIn("uncommitted", done.stdout)

    def test_a_key_the_commands_block_lacks_is_refused_not_skipped(self):
        path = self.repo / ".claude" / "goblin-warband.json"
        config = json.loads(path.read_text())
        config["commands"] = {"test": "true"}
        config["push_gate"] = ["test", "typecheck"]
        path.write_text(json.dumps(config))
        git(self.repo, "commit", "-qam", "gate config")
        self.assertIn("typecheck", self.refused())
        self.assertIn("typecheck", self.box.mc("gate", cwd=self.repo, expect=1).stdout)

    def test_dry_runs_tags_and_deletions_carry_no_tip(self):
        self.set_gate({"test": "true"})
        git(self.repo, "tag", "v1.0.0")
        for command in ("git push --dry-run origin main", "git push origin v1.0.0", "git push origin refs/tags/v1.0.0", "git push --tags", "git push origin :old-branch", "git push origin --delete old-branch"):
            self.assertIsNone(self.refused(command), command)
        self.assertIn("no green record", self.refused("git push origin main"))

    def test_every_spelling_of_the_push_is_seen(self):
        self.set_gate({"test": "true"})
        for command in ("git push", "git -C . push origin main", "cd . && git push -u origin HEAD", "git push --force-with-lease origin main", "echo ok; git push origin main", "bash -c 'git push origin main'"):
            self.assertIn("no green record", self.refused(command) or "", command)

    def test_docs_only_changes_are_exempt_when_the_config_says_so(self):
        origin = self.box.tmp / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
        git(self.repo, "remote", "add", "origin", str(origin))
        self.set_gate({"test": "true"}, exempt=["*.md", "docs/*"])
        git(self.repo, "push", "-q", "-u", "origin", "main")
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "note.md").write_text("n\n")
        git(self.repo, "add", "docs")  # not -A: the sandbox's worktree directory sits inside the repo
        git(self.repo, "commit", "-qm", "docs")
        self.assertIsNone(self.refused())
        (self.repo / "code.py").write_text("x = 1\n")
        git(self.repo, "add", "code.py")
        git(self.repo, "commit", "-qm", "code")
        self.assertIn("no green record", self.refused())

    def test_tags_do_not_excuse_a_branch_listed_beside_them(self):
        # PR 62 review: `--tags` pushes the listed refspecs as well, so only a bare `--tags` carries no branch tip
        self.set_gate({"test": "true"})
        for command in ("git push --tags origin main", "git push origin main --tags"):
            self.assertIn("no green record", self.refused(command) or "", command)
        for command in ("git push --tags", "git push --tags origin"):
            self.assertIsNone(self.refused(command), command)

    def test_the_exempt_shortcut_holds_only_for_the_upstream_branch(self):
        # re-review of PR 62: a docs-only diff against the upstream says nothing about a different destination branch
        origin = self.box.tmp / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
        git(self.repo, "remote", "add", "origin", str(origin))
        self.set_gate({"test": "true"}, exempt=["*.md", "docs/*"])
        git(self.repo, "push", "-q", "-u", "origin", "main")
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "note.md").write_text("n\n")
        git(self.repo, "add", "docs")
        git(self.repo, "commit", "-qm", "docs")
        for command in ("git push", "git push origin", "git push origin main", "git push origin HEAD:main", "git push origin HEAD:refs/heads/main"):
            self.assertIsNone(self.refused(command), command)
        for command in ("git push origin HEAD:other", "git push origin HEAD:refs/heads/other"):
            self.assertIn("no green record", self.refused(command) or "", command)

    def with_origin(self):
        origin = self.box.tmp / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
        git(self.repo, "remote", "add", "origin", str(origin))
        self.set_gate({"test": "true"}, exempt=["*.md", "docs/*"])
        git(self.repo, "push", "-q", "-u", "origin", "main")
        git(self.repo, "remote", "set-head", "origin", "main")

    def test_a_bare_branch_name_and_a_second_remote_are_not_exempt(self):
        # re-review of PR 62: `push origin other` sends to `other`, and `upstream` is not the remote that was diffed against
        self.with_origin()
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "note.md").write_text("n\n")
        git(self.repo, "add", "docs")
        git(self.repo, "commit", "-qm", "docs")
        git(self.repo, "branch", "other")
        for command in ("git push origin other", "git push upstream HEAD:main", "git push upstream main"):
            self.assertIn("no green record", self.refused(command) or "", command)
        for command in ("git push origin main", "git push origin HEAD", "git push origin +main", "git push origin main:main"):
            self.assertIsNone(self.refused(command), command)

    def test_the_remote_named_by_repo_counts_as_the_remote(self):
        # re-review of PR 62: `--repo` names the remote when no positional does
        self.with_origin()
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "note.md").write_text("n\n")
        git(self.repo, "add", "docs")
        git(self.repo, "commit", "-qm", "docs")
        for command in ("git push --repo upstream", "git push --repo=upstream"):
            self.assertIn("no green record", self.refused(command) or "", command)
        for command in ("git push --repo origin", "git push --repo=origin"):
            self.assertIsNone(self.refused(command), command)

    def test_a_configured_push_remote_is_not_the_base_remote(self):
        # re-review of PR 62: a bare push goes to branch.<name>.pushRemote, which the diff against the upstream says nothing about
        self.with_origin()
        fork = self.box.tmp / "fork.git"
        subprocess.run(["git", "init", "-q", "--bare", str(fork)], check=True)
        git(self.repo, "remote", "add", "fork", str(fork))
        git(self.repo, "push", "-q", "fork", "main")
        git(self.repo, "fetch", "-q", "fork")
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "note.md").write_text("n\n")
        git(self.repo, "add", "docs")
        git(self.repo, "commit", "-qm", "docs")
        self.assertIsNone(self.refused("git push"))
        git(self.repo, "config", "branch.main.pushRemote", "fork")
        for command in ("git push", "git push --force-with-lease"):
            self.assertIn("no green record", self.refused(command) or "", command)
        self.assertIsNone(self.refused("git push origin main"))

    def test_a_remote_whose_name_holds_a_slash_is_still_the_base_remote(self):
        # re-review of PR 62: the upstream reads `team/fork/main`, whose remote is `team/fork`
        self.with_origin()
        git(self.repo, "remote", "rename", "origin", "team/fork")
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "note.md").write_text("n\n")
        git(self.repo, "add", "docs")
        git(self.repo, "commit", "-qm", "docs")
        self.assertIsNone(self.refused("git push team/fork main"))
        self.assertIn("no green record", self.refused("git push other main") or "")

    def test_docs_straight_to_main_from_a_detached_worktree_is_exempt(self):
        # re-review of PR 62: the doc-changelog recipe pushes HEAD:main from a detached worktree with no upstream
        self.with_origin()
        detached = self.box.tmp / "docs-main"
        git(self.repo, "worktree", "add", "-q", "--detach", str(detached), "origin/main")
        (detached / "CHANGELOG.md").write_text("notes\n")
        git(detached, "add", "CHANGELOG.md")
        git(detached, "commit", "-qm", "docs")
        verdict = self.box.hook("pre-tool-use", {"tool_name": "Bash", "tool_input": {"command": "git push origin HEAD:main"}}, session="coord-1", cwd=detached)
        self.assertEqual(verdict.strip(), "")
        refused = self.box.hook("pre-tool-use", {"tool_name": "Bash", "tool_input": {"command": "git push origin HEAD:other"}}, session="coord-1", cwd=detached)
        self.assertIn("no green record", refused)

    def test_a_green_record_from_a_shorter_gate_does_not_count(self):
        # re-review of PR 62: the config is untracked and shared, so a key added to it changes no sha
        self.set_gate({"test": "true"})
        self.box.mc("gate", cwd=self.repo)
        self.assertIsNone(self.refused())
        path = self.repo / ".claude" / "goblin-warband.json"
        git(self.repo, "update-index", "--assume-unchanged", ".claude/goblin-warband.json")  # the real config is untracked
        config = json.loads(path.read_text())
        config["commands"]["lint"] = "true"
        config["push_gate"]["commands"].append("lint")
        path.write_text(json.dumps(config))
        reason = self.refused()
        self.assertIn("lint", reason)
        self.assertIn("warband.py gate", reason)
        self.box.mc("gate", cwd=self.repo)
        self.assertIsNone(self.refused())

    def test_a_tag_pushed_as_a_branch_is_gated(self):
        # re-review of PR 62: a tag's commit sent to refs/heads/ is a branch tip like any other
        self.set_gate({"test": "true"})
        git(self.repo, "tag", "v1.0.0")
        for command in ("git push origin v1.0.0:refs/heads/x", "git push origin refs/tags/v1.0.0:refs/heads/x"):
            self.assertIn("no green record", self.refused(command) or "", command)
        for command in ("git push origin v1.0.0", "git push origin v1.0.0:refs/tags/v1.0.0", "git push origin refs/tags/v1.0.0"):
            self.assertIsNone(self.refused(command), command)

    def test_the_record_read_is_the_one_for_the_commit_the_refspec_names(self):
        # PR 62 review: a green main must not carry a push of a branch that was never gated
        self.set_gate({"test": "true"})
        git(self.repo, "branch", "feat/other")
        git(self.repo, "checkout", "-q", "feat/other")
        (self.repo / "x.txt").write_text("x\n")
        git(self.repo, "add", "x.txt")
        git(self.repo, "commit", "-qm", "other work")
        other = self.head()
        git(self.repo, "checkout", "-q", "main")
        self.box.mc("gate", cwd=self.repo)  # green for main only
        self.assertIsNone(self.refused("git push origin main"))
        self.assertIsNone(self.refused("git push origin HEAD:refs/heads/x"))
        for command in ("git push origin feat/other", "git push origin +feat/other:refs/heads/x", "git push origin main feat/other", "git push --tags origin feat/other"):
            self.assertIn(other[:8], self.refused(command) or "", command)
        self.assertIsNone(self.refused("git push origin :feat/other"))

    def test_the_gate_refuses_over_untracked_files_and_names_them(self):
        # PR 62 review: a suite can import a file the commit lacks, and the record would still read green
        self.set_gate({"test": "true"})
        (self.repo / "helper.py").write_text("X = 1\n")
        done = self.box.mc("gate", cwd=self.repo, expect=1)
        self.assertIn("untracked", done.stdout)
        self.assertIn("helper.py", done.stdout)
        self.assertIn("push gate green", self.box.mc("gate", "--allow-untracked", cwd=self.repo).stdout)

    def test_the_gate_cli_json_record_names_the_commit(self):
        self.set_gate({"test": "true"})
        record = json.loads(self.box.mc("--json", "gate", cwd=self.repo).stdout)
        self.assertEqual(record["sha"], self.head())
        self.assertEqual(record["result"], "green")
        self.assertEqual([step["key"] for step in record["steps"]], ["test"])


class PrRecords(unittest.TestCase):
    """The per-PR ledger file and the derived who-moves-next rules."""

    def setUp(self):
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        self.mc = mc_module

    @staticmethod
    def fact(head_branch, base="main", **over):
        return {"state": "OPEN", "review_decision": "", "requested": [], "changes_requested_by": [], "approved_by": [], "base": base,
                "head": "h-" + head_branch, "head_branch": head_branch, "mergeable": "MERGEABLE", "draft": False, "checks": "good", **over}

    def who(self, number, facts, prs=None, needs=None, migrations=None):
        return self.mc.who_moves_next(number, prs or {}, facts, {}, needs or [], migrations)

    def test_approved_green_mergeable_is_the_users_merge(self):
        facts = {1: self.fact("a", review_decision="APPROVED")}
        self.assertEqual(self.who(1, facts)["kind"], "jason")

    def test_a_layer_inherits_the_lowest_unlanded_layer(self):
        facts = {271: self.fact("t1", requested=["max"]), 273: self.fact("t2", base="t1", review_decision="APPROVED")}
        out = self.who(273, facts)
        self.assertEqual(out["kind"], "reviewer")
        self.assertIn("lands after #271", out["why"])

    def test_an_approval_at_an_older_head_owes_a_fresh_look_not_a_merge(self):
        prs = {272: {"number": 272, "task": "MAIU", "approval": {"head": "h-old", "at": 0}}}
        facts = {272: self.fact("ie", review_decision="APPROVED", approved_by=["maxitect"])}
        out = self.who(272, facts, prs)
        self.assertEqual((out["kind"], out["actor"]), ("reviewer", "maxitect"))
        self.assertIn("fresh look", out["why"])
        prs[272]["approval"]["head"] = "h-ie"
        self.assertEqual(self.who(272, facts, prs)["kind"], "jason")

    def test_a_re_approval_at_the_new_head_is_not_owed_a_fresh_look(self):
        # approved at h-old, pushed to h-ie, approved again at h-ie: GitHub's decision never left APPROVED, so the record still says h-old
        prs = {272: {"number": 272, "task": "MAIU", "approval": {"head": "h-old", "at": 0}}}
        facts = {272: self.fact("ie", review_decision="APPROVED", approved_by=["maxitect"], approved_heads=["h-ie"])}
        self.assertEqual(self.who(272, facts, prs)["kind"], "jason")
        facts[272]["approved_heads"] = ["h-old"]
        out = self.who(272, facts, prs)
        self.assertEqual(out["kind"], "reviewer")
        self.assertIn("fresh look", out["why"])

    def test_a_fresh_look_after_a_re_approval_names_the_commit_last_approved(self):
        # approved at h-old, re-approved at h-mid, pushed to h-ie: the reviewer last saw h-mid
        prs = {272: {"number": 272, "task": "MAIU", "approval": {"head": "h-old", "at": 0}}}
        facts = {272: self.fact("ie", review_decision="APPROVED", approved_by=["maxitect"], approved_heads=["h-mid", "h-old"])}
        self.assertTrue(self.who(272, facts, prs)["why"].startswith("approved at h-mid, head now"))

    def test_normalise_reads_the_head_each_standing_approval_sat_on(self):
        def review(login, state, oid, at):
            return {"author": {"login": login}, "state": state, "commit": {"oid": oid}, "submittedAt": at}
        raw = {"headRefOid": "B", "reviews": [review("m", "APPROVED", "A", "2026-11-16T10:00:00Z"), review("m", "APPROVED", "B", "2026-11-16T11:00:00Z"),
                                               review("n", "COMMENTED", "B", "2026-11-16T12:00:00Z")]}
        self.assertEqual(self.mc.normalise_pr_facts(raw)["approved_heads"], ["B"])
        # a later comment does not withdraw an approval; a later change request does
        raw["reviews"].append(review("m", "COMMENTED", "B", "2026-11-16T13:00:00Z"))
        self.assertEqual(self.mc.normalise_pr_facts(raw)["approved_heads"], ["B"])
        raw["reviews"].append(review("m", "CHANGES_REQUESTED", "B", "2026-11-16T14:00:00Z"))
        self.assertEqual(self.mc.normalise_pr_facts(raw)["approved_heads"], [])
        # newest first, so a message about the last approval reads the head of the list
        ordered = {"reviews": [review("p", "APPROVED", "C", "2026-11-16T09:00:00Z"), review("q", "APPROVED", "D", "2026-11-16T15:00:00Z")]}
        self.assertEqual(self.mc.normalise_pr_facts(ordered)["approved_heads"], ["D", "C"])
        # gh leaves the oid empty where it cannot say; an empty one is no head
        self.assertEqual(self.mc.normalise_pr_facts({"reviews": [review("m", "APPROVED", "", "2026-11-16T10:00:00Z")]})["approved_heads"], [])

    def test_a_recorded_hold_wins_until_what_lifts_it_merges(self):
        prs = {260: {"number": 260, "hold": {"reason": "migration order", "lifts_on": [{"pr": 271}]}}}
        facts = {260: self.fact("b", review_decision="APPROVED"), 271: self.fact("t1")}
        self.assertEqual(self.who(260, facts, prs)["kind"], "hold")
        facts[271]["state"] = "MERGED"
        self.assertEqual(self.who(260, facts, prs)["kind"], "jason")

    def test_a_hold_with_no_lift_condition_never_lifts_and_says_so(self):
        prs = {5: {"number": 5, "hold": {"reason": "after New Zealand", "lifts_on": []}}}
        out = self.who(5, {5: self.fact("x", review_decision="APPROVED")}, prs)
        self.assertEqual(out["kind"], "hold")
        self.assertIn("lift condition not recorded", out["why"])

    def test_an_earlier_migration_in_another_stack_is_a_restamp_cost_not_a_block(self):
        facts = {272: self.fact("ie", review_decision="APPROVED"), 271: self.fact("nz"), 273: self.fact("nz2", base="nz")}
        out = self.who(272, facts, migrations={272: "20261116113625", 271: "20261114120000", 273: "20261114120000"})
        self.assertEqual(out["kind"], "jason")
        self.assertEqual(out["cost"], "landing this first makes #271, #273 restamp")

    def test_a_migration_in_the_same_stack_is_not_another_stacks_business(self):
        facts = {1: self.fact("a", review_decision="APPROVED", requested=[]), 2: self.fact("b", base="a", review_decision="APPROVED")}
        facts[1]["state"] = "MERGED"
        out = self.who(2, facts, migrations={1: "20261101000000", 2: "20261102000000"})
        self.assertEqual(out["kind"], "jason")
        self.assertNotIn("cost", out)

    def test_an_unreadable_migration_scan_says_the_cost_is_unknown(self):
        out = self.who(1, {1: self.fact("a", review_decision="APPROVED")}, migrations={1: None})
        self.assertEqual(out["kind"], "jason")
        self.assertIn("unknown", out["cost"])

    def test_an_open_need_for_the_pr_is_the_users(self):
        needs = [{"n": 9, "pr": 1, "why": "compact TAIC", "status": "open"}]
        self.assertEqual(self.who(1, {1: self.fact("a", requested=["max"])}, needs=needs)["kind"], "jason")

    def test_checks_changes_and_review_order(self):
        self.assertEqual(self.who(1, {1: self.fact("a", checks="bad", review_decision="APPROVED")})["kind"], "ci")
        crew = {1: {"number": 1, "task": "T"}}
        self.assertEqual(self.who(1, {1: self.fact("a", changes_requested_by=["max"])}, crew)["kind"], "session")
        self.assertEqual(self.who(1, {1: self.fact("a", requested=["max"])}, crew)["actor"], "max")
        conflicted = self.who(1, {1: self.fact("a", mergeable="CONFLICTING", requested=["max"])}, crew)
        self.assertEqual((conflicted["kind"], conflicted["actor"]), ("session", "T"))
        outside = self.who(1, {1: self.fact("a", author="maxitect")}, {1: {"number": 1, "task": None, "pinned": True}})
        self.assertEqual((outside["kind"], outside["actor"]), ("author", "maxitect"))

    def test_a_layer_still_owing_its_own_review_shows_the_reviewer_not_the_hold_below(self):
        prs = {260: {"number": 260, "task": "BSU", "hold": {"reason": "after New Zealand", "lifts_on": []}}, 279: {"number": 279, "task": "BSU"}}
        facts = {260: self.fact("b0", review_decision="APPROVED"), 279: self.fact("b1", base="b0", requested=["maxitect"])}
        out = self.who(279, facts, prs)
        self.assertEqual((out["kind"], out["actor"]), ("reviewer", "maxitect"))
        facts[279].update(review_decision="APPROVED", requested=[])
        self.assertEqual(self.who(279, facts, prs)["kind"], "hold")

    def test_migration_stamp_and_rollup_word(self):
        self.assertEqual(self.mc.lowest_migration(["supabase/migrations/20261115100000_x.sql", "20261101000000_y.sql", "README.md"]), "20261101000000")
        self.assertEqual(self.mc.rollup_word([{"conclusion": "SUCCESS"}, {"status": "IN_PROGRESS"}]), "wait")
        self.assertEqual(self.mc.rollup_word([{"conclusion": "FAILURE"}]), "bad")
        self.assertEqual(self.mc.rollup_word(None), "good")


class PrCommand(unittest.TestCase):
    def setUp(self):
        self.box = Sandbox()
        self.box.start()
        self.box.mc("crew", "add", "--task", "T", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")

    def test_add_pin_hold_release_round_trip(self):
        self.box.mc("prs", "pin", "286", "--group", "Outside the run", session="coord-1")
        self.box.mc("prs", "add", "271", "--task", "T", session="coord-1")
        self.box.mc("prs", "hold", "271", "--text", "after New Zealand", "--lifts-on-pr", "270", session="coord-1")
        rows = {r["number"]: r for r in json.loads(self.box.mc("--json", "prs", "list").stdout)}
        self.assertTrue(rows[286]["pinned"])
        self.assertEqual(rows[286]["group"], "Outside the run")
        self.assertEqual(rows[271]["task"], "T")
        self.assertEqual(rows[271]["hold"]["lifts_on"], [{"pr": 270}])
        self.box.mc("prs", "release", "271", session="coord-1")
        self.assertNotIn("hold", json.loads(self.box.mc("--json", "prs", "list").stdout)[1])

    def test_a_crew_session_adds_its_own_pr_but_cannot_hold_one(self):
        self.box.mc("join", session="crew-1", cwd=self.box.worktree)
        self.box.mc("prs", "add", "5", session="crew-1", cwd=self.box.worktree)
        self.assertEqual(json.loads(self.box.mc("--json", "prs", "list").stdout)[0]["task"], "T")
        done = self.box.mc("prs", "hold", "5", "--text", "x", session="crew-1", cwd=self.box.worktree, expect=1)
        self.assertIn("only the chief's session",done.stdout)

    def test_an_unknown_task_is_refused(self):
        done = self.box.mc("prs", "add", "5", "--task", "NOPE", session="coord-1", expect=1)
        self.assertIn("not in the raiders' plan", done.stdout)


class PrAttribution(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        self.mc = mc_module
        self.run = {"crew": [{"task": "BSU", "branch": "feat/bsu-corpus-survey"}, {"task": "TAIC", "branch": "feat/taic-metadata-profile"},
                             {"task": "GPT6", "branch": "feat/pipeline-gpt-6-luna"}]}

    def listing(self, *rows):
        return [{"number": n, "headRefName": h, "baseRefName": b} for n, h, b in rows]

    def test_branch_key_base_chain_and_session_rows(self):
        listing = self.listing((260, "feat/bsu-corpus-survey", "main"), (279, "feat/bsu-acquisition", "feat/bsu-corpus-survey"),
                               (273, "feat/taic-record-prompts", "feat/taic-metadata-profile"), (300, "feat/odd-name", "feat/taic-record-prompts"),
                               (283, "fix/reread-pages-with-no-row", "main"), (286, "feat/blue-green-deploy", "main"))
        sessions = {"s": {"task": "GPT6", "pr": 283}}
        found = self.mc.attribute_prs(self.run, sessions, {}, listing)
        self.assertEqual(found, {260: "BSU", 279: "BSU", 273: "TAIC", 300: "TAIC", 283: "GPT6"})

    def test_a_recorded_pr_is_left_alone_and_a_closed_one_is_not_claimed(self):
        listing = self.listing((279, "feat/bsu-acquisition", "main"))
        sessions = {"s": {"task": "BSU", "pr": 250}}
        self.assertEqual(self.mc.attribute_prs(self.run, sessions, {279: {"number": 279, "task": None}}, listing), {})

    def test_a_key_two_tasks_share_claims_nothing(self):
        run = {"crew": [{"task": "A", "branch": "feat/x-one"}, {"task": "B", "branch": "feat/x-two"}]}
        self.assertEqual(self.mc.attribute_prs(run, {}, {}, self.listing((1, "feat/x-three", "main"))), {})

    def test_a_held_approval_reads_its_hold_from_the_pr_file(self):
        item = {"n": 3, "kind": "approval", "pr": 260, "text": "PR #260 approved"}
        line = self.mc.pending_line(self.mc.with_pr_hold(item, {260: {"number": 260, "hold": {"reason": "after New Zealand", "lifts_on": [{"pr": 271}]}}}))
        self.assertIn("held", line)
        self.assertIn("#271 lands", line)

    def test_a_lifted_hold_no_longer_reads_as_held_in_the_start_context(self):
        item = {"n": 3, "kind": "approval", "pr": 260, "text": "PR #260 approved"}
        prs = {260: {"number": 260, "hold": {"reason": "after New Zealand", "lifts_on": [{"pr": 271}]}}}
        self.assertIn("held", self.mc.pending_line(self.mc.with_pr_hold(item, prs, {271: "OPEN"}, set())))
        self.assertEqual(self.mc.pending_line(self.mc.with_pr_hold(item, prs, {271: "MERGED"}, set())), "#3 PR #260 approved")


class PendingHoldMovesToPr(unittest.TestCase):
    def test_pending_hold_and_release_write_the_pr_file(self):
        box = Sandbox()
        box.start()
        run_path = box.ledger_root / next(p.name for p in box.ledger_root.iterdir()) / "run.json"
        run = json.loads(run_path.read_text())
        run["pending"] = [{"id": "x", "n": 1, "kind": "approval", "pr": 42, "text": "PR #42 approved", "status": "open", "at": 0}]
        run_path.write_text(json.dumps(run))
        box.mc("pending", "hold", "42", "--text", "after #41", session="coord-1")
        rows = json.loads(box.mc("--json", "prs", "list").stdout)
        self.assertEqual(rows[0]["hold"]["reason"], "after #41")
        self.assertNotIn("hold", json.loads(run_path.read_text())["pending"][0])
        box.mc("pending", "release", "42", session="coord-1")
        self.assertNotIn("hold", json.loads(box.mc("--json", "prs", "list").stdout)[0])

    def test_reconcile_moves_an_old_hold_and_approval_head_onto_the_pr_record_without_gh(self):
        box = Sandbox()
        box.start()
        run_path = box.ledger_root / next(p.name for p in box.ledger_root.iterdir()) / "run.json"
        run = json.loads(run_path.read_text())
        run["pending"] = [{"id": "x", "n": 1, "kind": "approval", "pr": 260, "head": "a1afe13", "hold": "Germany after New Zealand", "text": "approved", "status": "open", "at": 5}]
        run_path.write_text(json.dumps(run))
        box.mc("reconcile", session="coord-1")
        row = json.loads(box.mc("--json", "prs", "list").stdout)[0]
        self.assertEqual(row["approval"]["head"], "a1afe13")
        self.assertEqual(row["hold"]["reason"], "Germany after New Zealand")
        self.assertNotIn("hold", json.loads(run_path.read_text())["pending"][0])


class WaitingAndQuestions(unittest.TestCase):
    def setUp(self):
        self.box = Sandbox()
        self.box.start()
        self.box.mc("crew", "add", "--task", "T", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.box.mc("join", session="crew-1", cwd=self.box.worktree)

    def run_json(self):
        root = self.box.ledger_root / next(p.name for p in self.box.ledger_root.iterdir())
        return root, json.loads((root / "run.json").read_text())

    def test_waiting_names_what_it_waits_on(self):
        done = self.box.mc("report", "--state", "waiting", session="crew-1", cwd=self.box.worktree, expect=1)
        self.assertIn("--on", done.stdout)
        row = json.loads(self.box.mc("--json", "report", "--state", "waiting", "--on", "reviewer:maxitect", session="crew-1", cwd=self.box.worktree).stdout)
        self.assertEqual(row["waiting_on"], "reviewer:maxitect")
        row = json.loads(self.box.mc("--json", "report", "--state", "working", session="crew-1", cwd=self.box.worktree).stdout)
        self.assertNotIn("waiting_on", row)

    def test_a_question_carries_its_pr_and_refuses_a_command(self):
        need = json.loads(self.box.mc("--json", "needs", "add", "--kind", "question", "--why", "Land Germany before New Zealand?", "--pr", "260", session="coord-1").stdout)
        self.assertEqual((need["kind"], need["pr"], need["command"]), ("question", 260, ""))
        done = self.box.mc("needs", "add", "--kind", "question", "--why", "x", "--command", "ls", session="coord-1", expect=1)
        self.assertIn("no command", done.stdout)
        closed = json.loads(self.box.mc("--json", "needs", "done", str(need["n"]), "--result", "yes", "--by-user").stdout)
        self.assertEqual(closed["forward_to"], "coord-1")

    def test_reconcile_raises_and_closes_a_compaction_need(self):
        self.box.mc("report", "--context", "82", session="crew-1", cwd=self.box.worktree)
        self.box.mc("reconcile", session="coord-1")
        self.box.mc("reconcile", session="coord-1")
        _, run = self.run_json()
        compact = [n for n in run["needs"] if str(n.get("auto", "")).startswith("compact:")]
        self.assertEqual(len(compact), 1)
        self.assertEqual(compact[0]["status"], "open")
        self.box.mc("report", "--context", "20", session="crew-1", cwd=self.box.worktree)
        self.box.mc("reconcile", session="coord-1")
        _, run = self.run_json()
        self.assertEqual([n["status"] for n in run["needs"] if str(n.get("auto", "")).startswith("compact:")], ["done"])

    def test_a_permission_prompt_is_a_need_until_answered(self):
        reg = self.box.sessions / "crew-1.json"
        row = json.loads(reg.read_text())
        reg.write_text(json.dumps({**row, "status": "waiting"}))
        self.box.mc("reconcile", session="coord-1")
        _, run = self.run_json()
        prompt = [n for n in run["needs"] if str(n.get("auto", "")).startswith("prompt:")]
        self.assertEqual([n["status"] for n in prompt], ["open"])
        self.box.mc("report", "--state", "waiting-jason", session="crew-1", cwd=self.box.worktree)
        out = json.loads(self.box.mc("--json", "reconcile", session="coord-1").stdout)
        self.assertNotIn("waiting-jason-without-need", [d["kind"] for d in out["drift"]])
        reg.write_text(json.dumps({**row, "status": "busy"}))
        self.box.mc("reconcile", session="coord-1")
        _, run = self.run_json()
        self.assertEqual([n["status"] for n in run["needs"] if str(n.get("auto", "")).startswith("prompt:")], ["done"])

    def test_waiting_jason_without_a_need_is_drift(self):
        self.box.mc("report", "--state", "waiting-jason", session="crew-1", cwd=self.box.worktree)
        out = json.loads(self.box.mc("--json", "reconcile", session="coord-1").stdout)
        self.assertIn("waiting-jason-without-need", [d["kind"] for d in out["drift"]])
        self.box.mc("needs", "add", "--why", "run the read", "--command", "ls", session="crew-1", cwd=self.box.worktree)
        out = json.loads(self.box.mc("--json", "reconcile", session="coord-1").stdout)
        self.assertNotIn("waiting-jason-without-need", [d["kind"] for d in out["drift"]])


class Dashboard(unittest.TestCase):
    def setUp(self):
        self.box = Sandbox()
        self.box.start()
        self.box.mc("crew", "add", "--task", "T", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.dir = self.box.ledger_root / next(p.name for p in self.box.ledger_root.iterdir())

    def seed_facts(self, **facts):
        cache = {n.lstrip("n"): {"facts": f, "at": time.time()} for n, f in facts.items()}
        (self.dir / "pr-facts.json").write_text(json.dumps(cache))

    def test_a_ledger_write_redraws_the_page_from_the_cache_alone(self):
        base = {"state": "OPEN", "review_decision": "APPROVED", "requested": [], "changes_requested_by": [], "approved_by": ["max"], "base": "main",
                "head": "abc", "head_branch": "feat/a", "mergeable": "MERGEABLE", "draft": False, "checks": "good", "title": "<b>Ship</b> it", "author": "jw"}
        self.seed_facts(n7=base)
        self.box.mc("prs", "add", "7", "--task", "T", session="coord-1")
        page = (self.dir / "dashboard.html").read_text()
        self.assertIn("#7", page)
        self.assertIn("&lt;b&gt;Ship&lt;/b&gt; it", page)
        self.assertIn("the merge is yours", page)
        self.assertNotIn("http", page.split("<body>")[0].replace("http-equiv", ""))  # nothing loads from the network
        out = json.loads(self.box.mc("--json", "dashboard").stdout)
        self.assertEqual(out["totals"]["ready"], 1)
        self.assertEqual([m["number"] for m in out["mine"]], [7])

    def test_a_note_disappears_once_the_head_moves(self):
        base = {"state": "OPEN", "review_decision": "", "requested": ["max"], "changes_requested_by": [], "approved_by": [], "base": "main",
                "head": "abc", "head_branch": "feat/a", "mergeable": "MERGEABLE", "draft": False, "checks": "good", "title": "t", "author": "jw"}
        self.seed_facts(n7=base)
        self.box.mc("prs", "add", "7", "--task", "T", session="coord-1")
        self.box.mc("prs", "note", "7", "--text", "MAIU brings the findings after compaction", session="coord-1")
        self.assertIn("MAIU brings the findings", (self.dir / "dashboard.html").read_text())
        self.seed_facts(n7={**base, "head": "def"})
        self.box.mc("dashboard")
        self.assertNotIn("MAIU brings the findings", (self.dir / "dashboard.html").read_text())

    def test_status_carries_the_prs_block_and_crew_add_takes_a_group(self):
        self.box.mc("crew", "add", "--task", "T", "--branch", "feat/a", "--worktree", str(self.box.worktree), "--group", "New Zealand", session="coord-1")
        base = {"state": "OPEN", "review_decision": "APPROVED", "requested": [], "changes_requested_by": [], "approved_by": ["max"], "base": "main",
                "head": "abc", "head_branch": "feat/a", "mergeable": "MERGEABLE", "draft": False, "checks": "good", "title": "t", "author": "jw"}
        self.seed_facts(n7=base)
        self.box.mc("prs", "add", "7", "--task", "T", session="coord-1")
        status = json.loads(self.box.mc("--json", "status").stdout)
        self.assertEqual(status["prs"]["mine"][0]["number"], 7)
        self.assertIn('<span class="name">New Zealand</span>', (self.dir / "dashboard.html").read_text())

    def test_a_question_shows_on_its_prs_line(self):
        base = {"state": "OPEN", "review_decision": "", "requested": ["max"], "changes_requested_by": [], "approved_by": [], "base": "main",
                "head": "abc", "head_branch": "feat/a", "mergeable": "MERGEABLE", "draft": False, "checks": "good", "title": "t", "author": "jw"}
        self.seed_facts(n7=base)
        self.box.mc("prs", "add", "7", "--task", "T", session="coord-1")
        self.box.mc("needs", "add", "--kind", "question", "--why", "Germany before New Zealand?", "--pr", "7", session="coord-1")
        out = json.loads(self.box.mc("--json", "dashboard").stdout)
        self.assertEqual(out["totals"]["questions"], 1)
        self.assertIn("Germany before New Zealand?", (self.dir / "dashboard.html").read_text())

    READY = {"state": "OPEN", "review_decision": "APPROVED", "requested": [], "changes_requested_by": [], "approved_by": ["max"], "base": "main",
             "head": "abc", "head_branch": "feat/a", "mergeable": "MERGEABLE", "draft": False, "checks": "good", "title": "t", "author": "jw"}

    def test_a_hold_lifts_once_the_pr_it_waits_on_merges_from_outside_the_run(self):
        self.seed_facts(n272=self.READY, n500={**self.READY, "state": "MERGED", "head_branch": "colleague/x", "head": "zzz"})
        self.box.mc("prs", "add", "272", "--task", "T", session="coord-1")
        self.box.mc("prs", "hold", "272", "--text", "after the auth change", "--lifts-on-pr", "500", session="coord-1")
        out = json.loads(self.box.mc("--json", "dashboard").stdout)
        self.assertEqual(out["totals"]["held"], 0)
        self.assertEqual([m["number"] for m in out["mine"]], [272])
        self.assertEqual(out["totals"]["open"], 1, "the PR a hold waits on is read, never drawn as a row")

    def test_the_pr_a_hold_waits_on_is_never_taken_for_a_layer_below_another_row(self):
        # #11 is based on the colleague's branch; #500 is that branch's PR, read only because #10's hold names it
        self.seed_facts(n10=self.READY, n11={**self.READY, "head": "def", "head_branch": "feat/b", "base": "colleague/x"},
                        n500={**self.READY, "head": "zzz", "head_branch": "colleague/x"})
        self.box.mc("prs", "add", "10", "--task", "T", session="coord-1")
        self.box.mc("prs", "add", "11", "--task", "T", session="coord-1")
        self.box.mc("prs", "hold", "10", "--text", "after the auth change", "--lifts-on-pr", "500", session="coord-1")
        out = json.loads(self.box.mc("--json", "dashboard").stdout)
        self.assertEqual([m["number"] for m in out["mine"]], [11])
        self.assertEqual(out["mine"][0]["why"], "approved, checks green, mergeable; the merge is yours")

    def test_the_page_summary_and_status_agree_on_what_is_yours(self):
        # #8 sits on #7; both are ready, so #8 only lands after #7 and is the same action as #7
        self.seed_facts(n7=self.READY, n8={**self.READY, "head": "def", "head_branch": "feat/b", "base": "feat/a"})
        self.box.mc("prs", "add", "7", "--task", "T", session="coord-1")
        self.box.mc("prs", "add", "8", "--task", "T", session="coord-1")
        page = json.loads(self.box.mc("--json", "dashboard").stdout)
        status = json.loads(self.box.mc("--json", "status").stdout)
        self.assertEqual([m["number"] for m in page["mine"]], [7])
        self.assertEqual(page["mine"], status["prs"]["mine"])

    def test_the_spoils_page_is_a_war_table_with_tallies_and_its_own_faces(self):
        self.seed_facts(n7=self.READY, n8={**self.READY, "head": "def", "head_branch": "feat/b", "base": "feat/a"})
        self.box.mc("prs", "add", "7", "--task", "T", session="coord-1")
        self.box.mc("prs", "add", "8", "--task", "T", session="coord-1")
        page = (self.dir / "dashboard.html").read_text()
        self.assertIn("<h1>Spoils of search</h1>", page)
        self.assertIn('<div class="table">', page)
        self.assertEqual(page.count('<li class="card'), 2)
        self.assertIn('class="card layer depth-1"', page, "#8 waits on #7 and sits in under it")
        self.assertIn("font-family: 'Cabin Sketch'", page)
        self.assertIn("src: url(data:font/woff2;base64,", page)
        head = page.split("<body>")[0]
        self.assertNotIn("http", head.replace("http-equiv", ""), "the faces are inlined, nothing loads from the network")
        self.assertIn('<span class="sr">2</span> open', page, "the count is read aloud")
        self.assertNotIn('<b>2</b>', page, "a count is drawn in tally marks alone, with no numeral beside it")
        self.assertNotIn('class="count"', page)
        self.assertIn(".sr { position: absolute", page, "the read-aloud numeral is hidden from sight")

    def test_a_pr_from_outside_the_raid_is_shown_in_the_warbands_words_and_stored_in_the_old(self):
        self.seed_facts(n286={**self.READY, "head": "x86", "head_branch": "feat/x"})
        self.box.mc("prs", "pin", "286", session="coord-1")
        page = (self.dir / "dashboard.html").read_text()
        self.assertIn('<span class="name">Outside the raid</span>', page)
        rows = {r["number"]: r for r in json.loads(self.box.mc("--json", "prs", "list").stdout)}
        self.assertEqual(rows[286]["group"], "Outside the run", "the stored group keeps its word")

    def test_the_checks_word_is_escaped_on_the_page(self):
        """Review 5981937523: the one value that reached the page unescaped. Only rollup_word writes it, but a hand-edited
        pr-facts.json can put anything there."""
        base = {"state": "OPEN", "review_decision": "", "requested": [], "changes_requested_by": [], "approved_by": [], "base": "main",
                "head": "abc", "head_branch": "feat/a", "mergeable": "MERGEABLE", "draft": False, "checks": '"><img src=x onerror=alert(1)>', "title": "t", "author": "jw"}
        self.seed_facts(n8=base)
        self.box.mc("prs", "add", "8", "--task", "T", session="coord-1")
        page = (self.dir / "dashboard.html").read_text()
        self.assertNotIn("<img", page)
        self.assertNotIn("onerror=alert", page.replace("onerror=alert(1)&gt;", ""))

    def test_every_card_reads_at_4_5_to_1_in_both_themes(self):
        """Review 5981937523: a stacked card's ink on its darker card, and the small text, at WCAG AA for body text in light
        and dark. Ratios are worked out from the theme's tokens; no opacity thins the ink on a card."""
        import re
        theme = (HERE.parent / "templates" / "dashboard-theme.css").read_text()
        css = (HERE.parent / "templates" / "dashboard.css").read_text()
        light = dict(re.findall(r"\t(--[\w-]+): (#[0-9A-Fa-f]{6});", theme.split("@media")[0]))
        # review 5983944140: the page takes dark from prefers-color-scheme as well as from data-theme; both blocks are read
        # and must agree, so a test of one is a test of both
        scheme = dict(re.findall(r"\t+(--[\w-]+): (#[0-9A-Fa-f]{6});", theme.split("@media (prefers-color-scheme: dark)")[1].split(':root[data-theme="dark"]')[0]))
        dark = dict(re.findall(r"\t+(--[\w-]+): (#[0-9A-Fa-f]{6});", theme.split(':root[data-theme="dark"]')[1]))
        self.assertTrue(scheme and dark)
        self.assertEqual(scheme, dark, "the prefers-color-scheme block and the data-theme block set the same dark tokens")
        dark = {**light, **dark}

        def lum(hex_colour):
            parts = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            parts = [p / 12.92 if p <= 0.03928 else ((p + 0.055) / 1.055) ** 2.4 for p in parts]
            return 0.2126 * parts[0] + 0.7152 * parts[1] + 0.0722 * parts[2]

        def ratio(a, b):
            high, low = sorted((lum(a), lum(b)), reverse=True)
            return (high + 0.05) / (low + 0.05)

        def colour_of(selector):
            rule = re.search(re.escape(selector) + r" \{([^}]*)\}", css).group(1)
            found = re.search(r"(?<![\w-])color: var\((--[\w-]+)\)", rule)
            return found.group(1) if found else None

        card_ink, layer_ink = colour_of(".card"), colour_of(".card.layer") or colour_of(".card")
        tribute_ink = colour_of(".tributes li")
        tribute_ground = re.search(r"\.tributes li \{[^}]*background: var\((--[\w-]+)\)", css).group(1)
        for tokens in (light, dark):
            self.assertGreaterEqual(ratio(tokens[card_ink], tokens["--card"]), 4.5)
            self.assertGreaterEqual(ratio(tokens[layer_ink], tokens["--card-dark"]), 4.5)
            # an agreed tribute is a tribute slip drawn at full ink: its ratio is the slip's
            self.assertGreaterEqual(ratio(tokens[colour_of(".tributes .agreed") or tribute_ink], tokens[tribute_ground]), 4.5)
        for selector in (".meta", ".num .waits", ".note small", ".tributes .agreed"):
            rule = re.search(re.escape(selector) + r" \{([^}]*)\}", css).group(1)
            self.assertNotIn("opacity", rule, f"{selector} thins its ink below the ratio")

    def test_tally_marks_group_in_fives_and_stop_at_the_cap(self):
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        self.assertEqual(mc_module.tally_html(0), "")
        seven = mc_module.tally_html(7)
        self.assertEqual(seven.count('class="five"'), 1)
        self.assertEqual(seven.count("<i></i>"), 4 + 2)
        self.assertIn('aria-hidden="true"', seven)
        many = mc_module.tally_html(40)
        self.assertEqual(many.count('class="five"'), mc_module.TALLY_CAP // 5)
        self.assertIn('class="more"', many)
        self.assertEqual(mc_module.count_html(7), seven + '<span class="sr">7</span>', "marks for the eye, the number for a screen reader")
        self.assertEqual(mc_module.count_html(0), '<span class="sr">0</span>')

    def test_the_page_components_take_every_colour_from_the_theme(self):
        components = (HERE.parent / "templates" / "dashboard.css").read_text()
        import re
        self.assertEqual(re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", components), [], "no colour literal outside the copied theme")
        theme = (HERE.parent / "templates" / "dashboard-theme.css").read_text()
        for token in ("--desk", "--card", "--card-dark", "--tape", "--slip", "--font-marker", "--wonk"):
            self.assertIn(f"\t{token}:", theme)


class MoveFromMissionControl(unittest.TestCase):
    """The first command moves the old config and the old ledger root, archived raids included, with one line of notice;
    a live raid in the old ledger refuses the move and says why. Fixtures are written by the CLI itself, pointed at the old root."""

    def setUp(self):
        self.box = Sandbox()
        self.old = self.box.tmp / "old-ledger"
        self.new = self.box.ledger_root
        self.assertEqual(self.box.env["MISSION_CONTROL_HOME"], str(self.old))
        self.assertFalse(self.new.exists())

    def as_old_plugin(self, *args):
        """Run the CLI with its ledger at the old root and no old root of its own, as the mission-control plugin did."""
        env = {**self.box.env, "GOBLIN_WARBAND_HOME": str(self.old)}
        env.pop("MISSION_CONTROL_HOME")
        env["CLAUDE_CODE_SESSION_ID"] = "coord-1"
        done = subprocess.run([sys.executable, "-I", str(CLI), "--cwd", str(self.box.repo), *args], capture_output=True, text=True, env=env)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def old_world(self, live, tracked=False):
        """Two archived raids, a second project's ledger with no raid, the old config and local config; a live raid when asked.
        The config is git-ignored by a rule that covers both names (as this repository's `/.claude/*` does) unless `tracked`,
        where it is committed under its old name."""
        for name in ("first", "second"):
            self.as_old_plugin("start", "--name", name)
            self.as_old_plugin("end", "--force")
        other = self.old / "-elsewhere-app"
        other.mkdir(parents=True)
        (other / "log.jsonl").write_text("{}\n")
        if live:
            self.as_old_plugin("start", "--name", "search")
        claude = self.box.repo / ".claude"
        git(self.box.repo, "mv", ".claude/goblin-warband.json", ".claude/mission-control.json")
        if not tracked:
            git(self.box.repo, "rm", "-q", "--cached", ".claude/mission-control.json")
            with open(self.box.repo / ".git" / "info" / "exclude", "a") as handle:
                handle.write("/.claude/*.json\n")
        git(self.box.repo, "commit", "-qm", "the config under its old name")
        (claude / "mission-control.local.json").write_text(json.dumps({"collaboration": {"mode": "solo"}}))
        self.assertEqual(len(list((self.old / "runs").iterdir())), 2)

    def test_a_config_git_tracks_stays_under_its_old_name_and_the_tree_stays_clean(self):
        """A committed config is never renamed underneath git: that would dirty every checkout and hold every push behind a
        commit nobody was told to make. It is read from its old name and the slate says how to rename it."""
        self.old_world(live=False, tracked=True)
        status = json.loads(self.box.mc("--json", "status").stdout)
        self.assertTrue((self.box.repo / ".claude" / "mission-control.json").is_file())
        self.assertFalse((self.box.repo / ".claude" / "goblin-warband.json").exists())
        porcelain = subprocess.run(["git", "-C", str(self.box.repo), "status", "--porcelain", "--", ".claude/mission-control.json", ".claude/goblin-warband.json"], capture_output=True, text=True).stdout
        self.assertEqual(porcelain, "", "git sees no change to the config")
        self.assertTrue(status["config"])
        self.assertIn("git mv .claude/mission-control.json .claude/goblin-warband.json", status.get("config_note", ""))
        self.assertIn("once no session still runs mission-control", status["config_note"], "a committed rename leaves no link, so it waits")
        self.assertFalse(self.old.exists(), "the ledger still moved")

    def test_init_refuses_beside_a_config_read_from_its_old_name(self):
        """Review 5981937523: a starter written beside the old-named config is read first and shadows it, and the gates go."""
        self.old_world(live=False, tracked=True)
        done = self.box.mc("init", expect=1)
        said = done.stdout + done.stderr
        self.assertIn("mission-control.json", said)
        self.assertIn("--force", said)
        # review 5983523136: renaming it by hand takes the gates from a session still on 0.13.1, so the refusal never says to
        refusal = next(line for line in said.splitlines() if "mission-control.json is this repository's config" in line)
        self.assertNotIn("rename", refusal.lower())
        self.assertIn("leave it where it is while any session still runs mission-control", refusal)
        # review 5983944140: in this world (committed) the move never takes the file, so the refusal does not say it will
        self.assertIn("where git ignores both names", refusal)
        self.assertIn("/read-slate says what to do", refusal)
        self.assertFalse((self.box.repo / ".claude" / "goblin-warband.json").exists(), "no starter shadows the real config")

    def test_a_config_ignored_only_by_its_old_name_stays_put(self):
        """An ignore rule that names the old file alone would leave the new name untracked in the tree: the config stays."""
        self.old_world(live=False)
        exclude = self.box.repo / ".git" / "info" / "exclude"
        exclude.write_text(exclude.read_text().replace("/.claude/*.json\n", "/.claude/mission-control.json\n/.claude/mission-control.local.json\n"))
        status = json.loads(self.box.mc("--json", "status").stdout)
        self.assertTrue((self.box.repo / ".claude" / "mission-control.json").is_file())
        self.assertIn("ignore rule", status.get("config_note", ""))
        # the rename it prints leaves a link at the old name, as the move does, so a session still on 0.13.1 keeps its gate
        self.assertIn("ln -s goblin-warband.json .claude/mission-control.json", status["config_note"])

    def test_a_raid_whose_repository_has_gone_does_not_hold_the_move_back(self):
        """A live raid in the old ledger whose repo_root no longer exists can never be ended there; it is not carried on and the move goes ahead."""
        self.old_world(live=False)
        gone = self.old / "-scratch-gone"
        gone.mkdir()
        (gone / "run.json").write_text(json.dumps({"name": "scratch", "repo_root": str(self.box.tmp / "deleted-repo"), "started_at": 1}))
        status = json.loads(self.box.mc("--json", "status").stdout)
        self.assertNotIn("carrying", status)
        self.assertFalse(self.old.exists())
        self.assertTrue((self.new / "-scratch-gone" / "run.json").is_file(), "it moved with the rest, untouched")

    def test_a_text_status_that_makes_the_move_says_so_once(self):
        self.old_world(live=False)
        done = self.box.mc("status")
        self.assertEqual((done.stdout + done.stderr).count("goblin-warband: moved"), 1)

    def test_a_move_that_fails_leaves_the_gates_working(self):
        """An OSError mid-move (a read-only home, a lock that cannot be made) never becomes a traceback that fails a hook open."""
        self.old_world(live=False)
        self.new.parent.mkdir(parents=True, exist_ok=True)
        (self.new.parent / ".goblin-warband-move.lock").mkdir()  # the lock file cannot be opened: the move raises OSError
        out = self.box.hook("pre-tool-use", {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}}, session="coord-1", cwd=self.box.repo)
        verdict = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(verdict["permissionDecision"], "deny", "the push gate still rules from the old config")
        done = self.box.mc("status")
        self.assertNotIn("Traceback", done.stderr)
        self.assertIn("could not move", done.stderr)

    def test_the_first_command_moves_the_config_and_the_ledger_with_one_line_of_notice(self):
        self.old_world(live=False)
        done = self.box.mc("--json", "status")
        notice = [line for line in done.stderr.splitlines() if line.strip()]
        self.assertEqual(len(notice), 1, done.stderr)
        self.assertTrue(notice[0].startswith("goblin-warband: moved the ledger "), notice[0])
        self.assertIn("(2 archived raids)", notice[0])
        self.assertIn("goblin-warband.json", notice[0])
        self.assertFalse(self.old.exists(), "the old root moved whole")
        self.assertEqual(len(list((self.new / "runs").iterdir())), 2, "archived raids came with it")
        self.assertTrue((self.new / "-elsewhere-app" / "log.jsonl").is_file(), "another project's ledger came with it")
        claude = self.box.repo / ".claude"
        # review 5978864222: the old names stay as relative links, so a session still on 0.13.1 keeps its push gate until restarted
        for old, new in (("mission-control.json", "goblin-warband.json"), ("mission-control.local.json", "goblin-warband.local.json")):
            self.assertTrue((claude / old).is_symlink(), old)
            self.assertEqual(os.readlink(claude / old), new)
            self.assertFalse((claude / new).is_symlink(), f"{new} is the real file")
        self.assertIn("push_gate", json.loads((claude / "mission-control.json").read_text()), "a 0.13.1 read of the old name still finds the gate")
        self.assertIn("links", notice[0], "the notice says the old names stay as links")
        self.assertTrue((claude / "goblin-warband.json").is_file())
        self.assertEqual(json.loads((claude / "goblin-warband.local.json").read_text()), {"collaboration": {"mode": "solo"}})
        self.assertTrue(json.loads(done.stdout)["config"], "the command that moved the config then read it")
        self.assertEqual(Path(json.loads(done.stdout)["config_path"]).resolve(), (claude / "goblin-warband.json").resolve())
        self.assertEqual(Path(json.loads(done.stdout)["config_path"]).name, "goblin-warband.json", "the new name is the one read")
        again = self.box.mc("--json", "status")
        self.assertNotIn("goblin-warband: moved", again.stderr, "the move happens once; the link is never taken for an old config")
        self.assertTrue((claude / "mission-control.json").is_symlink())
        self.assertNotIn("config_note", json.loads(again.stdout))

    def tree(self, root):
        return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.name != "run.lock")

    def test_a_live_old_raid_is_carried_on_from_the_old_ledger_and_nothing_moves(self):
        """Ruling 23: the raid carries on from the old ledger and the old config names, says so in one line, and nothing moves."""
        self.old_world(live=True)
        archived = sorted(p.name for p in (self.old / "runs").iterdir())
        done = self.box.mc("--json", "status")
        status = json.loads(done.stdout)
        self.assertEqual(status["run"]["name"], "search", "the live raid is the one the new CLI reads")
        self.assertTrue(status["config"], "the old config name is read")
        self.assertIn(str(self.old), status.get("carrying", ""))
        self.assertIn("moves to", status["carrying"])
        self.assertFalse(self.new.exists(), "no second root is started")
        self.assertEqual(sorted(p.name for p in (self.old / "runs").iterdir()), archived)
        self.assertTrue((self.box.repo / ".claude" / "mission-control.json").is_file(), "the config stays with the live raid")
        self.assertFalse((self.box.repo / ".claude" / "goblin-warband.json").exists())
        self.assertIn("carrying on", self.box.mc("status").stdout.splitlines()[0], "read-slate says so in one line")
        # review 5981937523: the config is at its old name because nothing moves mid-raid, so no note blames the ignore
        # rule or prints a rename that would take the link (and the gate) from a session still on 0.13.1
        self.assertNotIn("config_note", status)
        self.assertNotIn("mv .claude", self.box.mc("status").stdout)

    def test_a_live_old_raid_keeps_the_dibs_gate_shut_from_the_old_root(self):
        self.old_world(live=True)
        self.as_old_plugin("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree))
        self.box.mc("join", session="crew-1", cwd=self.box.worktree)
        out = self.box.hook("pre-tool-use", {"tool_name": "Bash", "tool_input": {"command": "cd apps/api && poetry run poe db-reset-local-anyway"}})
        verdict = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(verdict["permissionDecision"], "deny")
        self.assertIn("free, but not granted to you", verdict["permissionDecisionReason"])
        requests = list((next(p for p in self.old.iterdir() if (p / "run.json").is_file()) / "requests").iterdir())
        self.assertEqual(len(requests), 1, "the dibs called landed in the old ledger")
        self.assertFalse(self.new.exists())

    def test_a_live_old_raid_keeps_the_push_gate_shut_from_the_old_config(self):
        self.old_world(live=True)
        self.assertIn("push_gate", json.loads((self.box.repo / ".claude" / "mission-control.json").read_text()), "the example config opts in")
        out = self.box.hook("pre-tool-use", {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}}, session="coord-1", cwd=self.box.repo)
        verdict = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(verdict["permissionDecision"], "deny")
        self.assertIn("no green record", verdict["permissionDecisionReason"])

    def test_a_raid_started_while_an_old_one_is_live_goes_to_the_old_ledger_too(self):
        self.old_world(live=True)
        other = self.box.tmp / "other"
        other.mkdir()
        git(other, "init", "-q", "-b", "main")
        git(other, "config", "user.email", "t@example.com")
        git(other, "config", "user.name", "t")
        (other / ".claude").mkdir()
        (other / ".claude" / "goblin-warband.json").write_text(json.dumps({k: v for k, v in json.loads(EXAMPLE.read_text()).items() if k != "collaboration"}))
        (other / "README.md").write_text("x\n")
        git(other, "add", "-A")
        git(other, "commit", "-q", "-m", "init")
        self.box.register("coord-2", "other chief", str(other))
        before = self.tree(self.old)
        self.box.mc("start", "--name", "second", session="coord-2", cwd=other)
        self.assertFalse(self.new.exists(), "state is never split across two roots")
        started = [p for p in self.tree(self.old) if p.endswith("run.json") and p not in before]
        self.assertEqual(len(started), 1, started)
        self.assertEqual(len([p for p in self.old.glob("*/run.json") if p.parent.name != "runs"]), 2, "two live raids in the old ledger")

    def test_the_move_happens_once_on_the_first_command_after_the_last_old_raid_ends(self):
        self.old_world(live=True)
        self.box.mc("status")
        self.assertTrue(self.old.is_dir())
        ended = self.box.mc("end", "--force", session="coord-1")
        self.assertNotIn("goblin-warband: moved", ended.stderr, "the command that ends the raid does not move it")
        self.assertTrue(self.old.is_dir())
        self.assertEqual(len(list((self.old / "runs").iterdir())), 3, "the ended raid was archived in the old ledger")
        env = dict(self.box.env)
        procs = [subprocess.Popen([sys.executable, "-I", str(CLI), "--cwd", str(self.box.repo), "--json", "status"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
                 for _ in range(4)]
        results = [p.communicate() + (p.returncode,) for p in procs]
        self.assertEqual([code for _, _, code in results], [0] * 4, [err for _, err, _ in results])
        self.assertEqual(sum("goblin-warband: moved" in err for _, err, _ in results), 1, "moved exactly once, under the lock")
        self.assertFalse(self.old.exists())
        self.assertEqual(len(list((self.new / "runs").iterdir())), 3)
        self.assertTrue((self.box.repo / ".claude" / "goblin-warband.json").is_file())
        self.assertNotIn("carrying", json.loads(self.box.mc("--json", "status").stdout))

    def test_a_hook_during_a_live_old_raid_reads_the_raid_from_the_old_ledger(self):
        self.old_world(live=True)
        out = self.box.hook("session-start", {"source": "startup"}, session="coord-1", cwd=self.box.repo)
        self.assertIn("search", out, "the chief's start context names the carried raid")
        self.assertFalse(self.new.exists())

    def test_an_existing_new_ledger_is_never_overwritten(self):
        self.old_world(live=False)
        self.new.mkdir(parents=True)
        (self.new / "marker").write_text("x")
        done = self.box.mc("--json", "status")
        self.assertTrue((self.old / "runs").is_dir(), "the old root stays when the new one exists")
        self.assertTrue((self.new / "marker").is_file())
        self.assertNotIn("the ledger", done.stderr, "only the config moved")
        self.assertIn("goblin-warband.json", done.stderr)

    def test_a_move_a_hook_made_is_told_by_the_next_status_once(self):
        """A hook that moves the ledger at session start cannot be heard (its stderr reaches no one), so the notice waits in the
        new ledger for the first status, which the mod reads as its first refresh and toasts."""
        self.old_world(live=False)
        done = self.box.mc("hook", "session-start", session="crew-1", stdin=json.dumps({"session_id": "crew-1", "cwd": str(self.box.worktree), "source": "startup"}))
        self.assertEqual(done.returncode, 0)
        self.assertFalse(self.old.exists())
        first = json.loads(self.box.mc("--json", "status").stdout)
        self.assertTrue(first.get("notice", "").startswith("goblin-warband: moved the ledger "), first.get("notice"))
        self.assertNotIn("notice", json.loads(self.box.mc("--json", "status").stdout), "told once")

    def test_sessions_starting_together_move_the_ledger_once_and_none_of_them_breaks(self):
        self.old_world(live=False)
        env = dict(self.box.env)
        procs = [subprocess.Popen([sys.executable, "-I", str(CLI), "--cwd", str(self.box.repo), "--json", "status"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
                 for _ in range(6)]
        results = [p.communicate() + (p.returncode,) for p in procs]
        self.assertEqual([code for _, _, code in results], [0] * 6, [err for _, err, _ in results])
        self.assertFalse(any("Traceback" in err for _, err, _ in results))
        self.assertEqual(sum("goblin-warband: moved" in err for _, err, _ in results), 1, "one process moved it")
        self.assertFalse(self.old.exists())
        self.assertEqual(len(list((self.new / "runs").iterdir())), 2)
        self.assertFalse((self.new / "mission-control").exists(), "nothing was moved inside the new root")

    def test_a_live_raid_that_turns_up_in_the_old_ledger_after_the_move_is_never_carried_on(self):
        """Review 5976730930: once the new root exists it is the ledger, whatever appears in the old one later (a session still
        on the cached mission-control 0.13.1 starting a raid, or a start racing the move). The stray raid is named in one line
        and never read, and the raids under the new root keep their dibs gate."""
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.box.mc("join", session="crew-1", cwd=self.box.worktree)
        reset = {"tool_name": "Bash", "tool_input": {"command": "cd apps/api && poetry run poe db-reset-local-anyway"}}
        self.assertEqual(json.loads(self.box.hook("pre-tool-use", reset))["hookSpecificOutput"]["permissionDecision"], "deny")
        stray = self.old / "-elsewhere-app"
        stray.mkdir(parents=True)
        (stray / "run.json").write_text(json.dumps({"name": "stray", "repo_root": str(self.box.tmp), "started_at": 1}))
        status = json.loads(self.box.mc("--json", "status").stdout)
        self.assertEqual((status.get("run") or {}).get("name"), "search", "the new root's raid is still the one read")
        self.assertNotIn("carrying", status)
        self.assertIn(str(self.old), status.get("old_ledger_note", ""))
        self.assertIn("stray", status["old_ledger_note"])
        verdict = json.loads(self.box.hook("pre-tool-use", reset))["hookSpecificOutput"]
        self.assertEqual(verdict["permissionDecision"], "deny", "the dibs gate still rules from the new root")
        self.assertTrue((stray / "run.json").is_file(), "nothing in the old root is moved or touched")
        self.assertIn(status["old_ledger_note"], self.box.mc("status").stdout, "read-slate says it in one line")
        # review 5983944140: a restarted session never reads the old folder, so the note names a command this CLI can run, and
        # never offers delete for a folder that holds a live raid
        self.assertIn("end --old-ledger", status["old_ledger_note"])
        self.assertNotIn("delete", status["old_ledger_note"])

    def test_end_old_ledger_archives_a_stray_raid_this_cli_never_reads(self):
        """Review 5983944140: the head can finish the job itself, so ending a stray raid never depends on a session still on
        mission-control. Its files are archived under the old folder's runs/, and the note then offers the folder's removal."""
        self.box.start()
        own = self.old / self.new.joinpath(next(p.name for p in self.new.iterdir() if (p / "run.json").is_file())).name
        own.mkdir(parents=True)
        (own / "run.json").write_text(json.dumps({"name": "stray", "repo_root": str(self.box.repo), "started_at": 1, "coordinator": {"session_id": "old-chief"}}))
        (own / "log.jsonl").write_text("{}\n")
        done = self.box.mc("end", "--old-ledger", "--by-user")
        self.assertIn("stray", done.stdout)
        self.assertFalse((own / "run.json").exists(), "the stray raid is no longer live")
        archived = list((self.old / "runs").iterdir())
        self.assertEqual(len(archived), 1)
        self.assertTrue((archived[0] / "run.json").is_file() and (archived[0] / "log.jsonl").is_file(), "its files kept, archived")
        status = json.loads(self.box.mc("--json", "status").stdout)
        self.assertEqual((status.get("run") or {}).get("name"), "search", "the new root's raid is untouched")
        self.assertIn("move or delete that folder by hand", status.get("old_ledger_note", ""))
        self.box.mc("end", "--old-ledger", "--by-user", expect=1)  # nothing live left there

    def _stray_beside_a_live_new_raid(self):
        """A live raid under the new root and a stray live one for the same repository under the old root."""
        self.box.start()
        slug = next(p.name for p in self.new.iterdir() if (p / "run.json").is_file())
        own = self.old / slug
        own.mkdir(parents=True)
        (own / "run.json").write_text(json.dumps({"name": "stray", "repo_root": str(self.box.repo), "started_at": 1, "coordinator": {"session_id": "old-chief"}}))
        return own

    def tree_of(self, root):
        return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file() and p.name not in ("run.lock",)}

    def test_end_old_ledger_never_touches_the_new_ledger(self):
        own = self._stray_beside_a_live_new_raid()
        slug = own.name
        before = self.tree_of(self.new)
        self.box.mc("end", "--old-ledger", "--by-user")
        self.assertEqual(self.tree_of(self.new), before, "no file under the new root changed, its log included")
        self.assertFalse(list(self.new.glob("runs/*")), "nothing was archived under the new root")
        self.assertTrue((self.new / slug / "run.json").is_file(), "both roots were live; the new one still is")

    def test_end_old_ledger_answers_only_the_chief_or_the_person(self):
        own = self._stray_beside_a_live_new_raid()
        self.box.register("someone", "a bystander", str(self.box.repo))
        done = self.box.mc("end", "--old-ledger", session="someone", expect=1)
        self.assertIn("only the chief's session", done.stdout + done.stderr)
        self.assertTrue((own / "run.json").is_file(), "refused, so the stray raid is still live and unarchived")
        self.box.mc("end", "--old-ledger", session="old-chief")  # the stray raid's own chief may, as for any end
        self.assertFalse((own / "run.json").exists())

    def test_end_old_ledger_refuses_with_no_old_root_or_no_live_raid_there(self):
        self.box.start()
        done = self.box.mc("end", "--old-ledger", "--by-user", expect=1)
        self.assertIn("no old mission-control ledger", done.stdout + done.stderr)
        slug = next(p.name for p in self.new.iterdir() if (p / "run.json").is_file())
        (self.old / slug).mkdir(parents=True)
        (self.old / slug / "run.json").write_text(json.dumps({"name": "over", "repo_root": str(self.box.repo), "started_at": 1, "ended_at": 2}))
        done = self.box.mc("end", "--old-ledger", "--by-user", expect=1)
        self.assertTrue((self.old / slug / "run.json").is_file(), "an ended raid there is left alone")
        self.assertFalse((self.old / "runs").exists())
        self.assertTrue(json.loads(self.box.mc("--json", "status").stdout).get("run"), "the new root's raid is untouched")

    def test_a_pending_config_move_never_carries_on_from_an_old_ledger_beside_the_new_one(self):
        """Review 5978367037: the re-check under the move lock carried on from any live old raid whenever a config move was
        pending, so a checkout still holding an ignored old-named config (the ordinary state of a second repository after the
        first one moved the ledger) flipped back. Only a ledger that is about to move is re-checked."""
        self.box.start()
        self.box.mc("crew", "add", "--task", "10SE.2", "--branch", "feat/a", "--worktree", str(self.box.worktree), session="coord-1")
        self.box.mc("join", session="crew-1", cwd=self.box.worktree)
        reset = {"tool_name": "Bash", "tool_input": {"command": "cd apps/api && poetry run poe db-reset-local-anyway"}}
        stray = self.old / "-elsewhere-app"
        stray.mkdir(parents=True)
        (stray / "run.json").write_text(json.dumps({"name": "stray", "repo_root": str(self.box.tmp), "started_at": 1}))
        with open(self.box.repo / ".git" / "info" / "exclude", "a") as handle:
            handle.write("/.claude/*.json\n")
        (self.box.repo / ".claude" / "mission-control.local.json").write_text(json.dumps({"collaboration": {"mode": "solo"}}))
        status = json.loads(self.box.mc("--json", "status").stdout)
        self.assertEqual((status.get("run") or {}).get("name"), "search", "the new root's raid is still the one read")
        self.assertNotIn("carrying", status)
        self.assertIn("stray", status.get("old_ledger_note", ""))
        self.assertTrue((self.box.repo / ".claude" / "goblin-warband.local.json").is_file(), "the pending config moved")
        self.assertTrue((self.box.repo / ".claude" / "mission-control.local.json").is_symlink(), "the old name stays as a link")
        verdict = json.loads(self.box.hook("pre-tool-use", reset))["hookSpecificOutput"]
        self.assertEqual(verdict["permissionDecision"], "deny", "the dibs gate still rules from the new root")
        self.assertTrue((stray / "run.json").is_file())

    def test_a_link_the_person_made_at_the_old_name_moves_once_with_no_wrong_note(self):
        """Review 5979400434: a hand-made link at the old name (to a shared file, or a worktree's link to the main checkout's
        config) moves like any file and leaves the move's own link; it is never skipped for good with a config_note blaming
        the ignore rule."""
        self.old_world(live=False)
        claude = self.box.repo / ".claude"
        shared = self.box.tmp / "shared-config.json"
        (claude / "mission-control.json").rename(shared)
        (claude / "mission-control.json").symlink_to(shared)
        first = self.box.mc("--json", "status")
        self.assertIn("goblin-warband: moved", first.stderr)
        self.assertNotIn("config_note", json.loads(first.stdout))
        self.assertEqual(os.readlink(claude / "mission-control.json"), "goblin-warband.json", "the move's own link")
        self.assertEqual((claude / "goblin-warband.json").resolve(), shared.resolve(), "the person's link now sits at the new name")
        again = self.box.mc("--json", "status")
        self.assertNotIn("goblin-warband: moved", again.stderr)
        self.assertNotIn("config_note", json.loads(again.stdout))

    def test_a_link_that_cannot_be_made_warns_and_the_move_still_lands(self):
        """Review 5978864222: the link is for sessions not yet restarted; one the filesystem refuses (permissions) says so in
        the notice and never fails the move."""
        from unittest import mock
        import warband as mc_module
        root = self.box.tmp / "linkless"
        (root / ".claude").mkdir(parents=True)
        old_path, new_path = root / ".claude" / "mission-control.json", root / ".claude" / "goblin-warband.json"
        old_path.write_text(json.dumps({"push_gate": {}}))
        with mock.patch.object(mc_module.os, "symlink", side_effect=PermissionError("denied")):
            notice = mc_module.move_from_mission_control(None, self.box.tmp / "no-ledger", False, [(old_path, new_path)])
        self.assertTrue(new_path.is_file())
        self.assertFalse(old_path.exists() or old_path.is_symlink())
        self.assertIn("could not leave a link", notice)
        self.assertIn("restart", notice)

    def test_an_old_ledger_beside_the_new_one_is_named_even_with_no_live_raid(self):
        self.old_world(live=False)
        self.new.mkdir(parents=True)
        status = json.loads(self.box.mc("--json", "status").stdout)
        self.assertIn(str(self.old), status.get("old_ledger_note", ""))
        self.assertTrue((self.old / "runs").is_dir())

    def test_a_sandbox_never_reads_the_default_old_ledger(self):
        """With GOBLIN_WARBAND_HOME set and no MISSION_CONTROL_HOME, nothing derived from HOME or CLAUDE_CONFIG_DIR is moved."""
        default_old = self.box.tmp / "home" / ".claude" / "mission-control"
        (default_old / "runs" / "old").mkdir(parents=True)
        env = dict(self.box.env)
        env.pop("MISSION_CONTROL_HOME")
        done = subprocess.run([sys.executable, "-I", str(CLI), "--cwd", str(self.box.repo), "status"], capture_output=True, text=True, env=env)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue((default_old / "runs" / "old").is_dir())
        self.assertNotIn("goblin-warband: moved", done.stderr)


class StateWords(unittest.TestCase):
    """The stored states keep their words; the CLI and the mod show the same new ones, from one table each held to the other."""

    def test_the_cli_and_the_mod_show_each_state_in_the_same_words(self):
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        source = (HERE.parent / "hooks" / "register.tsx").read_text()
        block = source.split("export const STATE_WORDS: Record<string, string> = {", 1)[1].split("}", 1)[0]
        import re
        mod = {key: value for key, value in re.findall(r"'?([a-z-]+)'?: '([^']+)'", block)}
        self.assertEqual(mod, mc_module.STATE_WORDS)
        self.assertEqual(set(mc_module.STATES) | {"retired", "gone"}, set(mc_module.STATE_WORDS))

    def test_the_text_slate_shows_the_new_words_and_the_ledger_keeps_the_old(self):
        box = Sandbox()
        box.start()
        box.mc("join", session="crew-1", cwd=box.worktree)
        box.mc("report", "--state", "working", session="crew-1", cwd=box.worktree)
        text = box.mc("status").stdout
        self.assertIn("| raiding |", text)
        self.assertIn("# Raid search", text)
        self.assertIn("chief mission control", text)
        rows = json.loads(box.mc("--json", "status").stdout)["sessions"]
        self.assertIn("working", [r.get("state") for r in rows], "the ledger stores working")


class RealLedgerUntouched(unittest.TestCase):
    """The suite's own guard: the real ledger roots are never the ones the module resolves."""

    def test_the_module_resolves_no_real_ledger(self):
        sys.path.insert(0, str(HERE))
        import warband as mc_module
        real = REAL_HOME / ".claude"
        self.assertFalse(str(mc_module.LEDGER_ROOT).startswith(str(real)), mc_module.LEDGER_ROOT)
        old = mc_module.old_ledger_root()
        self.assertTrue(old is None or not str(old).startswith(str(real)), old)


if __name__ == "__main__":
    unittest.main()
