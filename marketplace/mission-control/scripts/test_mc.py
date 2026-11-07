"""Tests for mc.py: the gate matcher, the ledger, authorisation and both hooks.

Run from this directory: python3 -m unittest test_mc

Every test works in a throwaway git repository with its own ledger root and
session registry (MISSION_CONTROL_HOME, CLAUDE_SESSIONS_DIR), so nothing here
touches ~/.claude. Probes that shell out (lsof, psql) are not exercised.
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
CLI = HERE / "mc.py"
EXAMPLE = HERE.parent / "references" / "mission-control.example.json"


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
        (self.repo / ".claude" / "mission-control.json").write_text(json.dumps(config))
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
            "MISSION_CONTROL_HOME": str(self.ledger_root),
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
        import mc  # noqa: WPS433
        self.mc = mc
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
        self.assertIn("Run search started", out)
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
        self.assertIn("only the coordinator", refused.stdout)
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
        self.assertIn("slots are still held", self.box.mc("end", session="coord-1", expect=1).stdout)
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
        self.assertIn("this worktree is crew A", self.box.hook("session-start", {}, session="crew-9", cwd=variant))

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
        import mc as mc_module
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
        self.assertIn("only the coordinator", refused.stdout)
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
        import mc as mc_module
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
        import mc as mc_module
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
        import mc as mc_module
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
        import mc as mc_module
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

    def _roadmap_repo_with_origin(self, claim_on_branch=True, claim_on_main=False, listed=True):
        """A rich roadmap, a bare origin holding main, and feat/a pushed with (or without) a commit that sets the task's `started`.
        `claim_on_main` puts the claim on main under a sync batch's subject instead; `listed=False` leaves the task out of the roadmap."""
        base = self._roadmap(started="2026-10-27" if claim_on_main else None) if listed else self._roadmap(task="OTHER")
        (self.box.repo / ".claude" / "roadmaps.json").write_text(base)
        git(self.box.repo, "add", ".claude/roadmaps.json")
        git(self.box.repo, "commit", "-q", "-m", "chore(roadmap): sync claims from live branches" if claim_on_main else "chore: roadmap")
        bare = self.box.tmp / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)  # a clone of it checks out main, whatever this machine's init.defaultBranch
        git(self.box.repo, "remote", "add", "origin", str(bare))
        git(self.box.repo, "push", "-q", "-u", "origin", "main")
        git(self.box.worktree, "merge", "-q", "--ff-only", "main")
        if claim_on_branch and listed:
            (self.box.worktree / ".claude" / "roadmaps.json").write_text(self._roadmap(started="2026-10-27"))
            git(self.box.worktree, "add", ".claude/roadmaps.json")
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
        config_path = self.box.repo / ".claude" / "mission-control.json"
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
        import mc as mc_module
        import io
        from contextlib import redirect_stdout
        out = io.StringIO()
        with redirect_stdout(out):
            mc_module.print_reconcile(result)
        self.assertIn("- #231 (10SE.2): merged\n", out.getvalue())
        self.assertNotIn("merged, merged", out.getvalue())

    # retire: reclaiming a finished crew worktree while the run goes on

    def _retire_with(self, fake_sh, *cli):
        """`mc.py retire` in-process, with gh faked and du/lsof answered by the same fake (a non-gh argv returns 1, which lsof treats as 'nothing listed')."""
        sys.path.insert(0, str(HERE))
        import mc as mc_module
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
        self.assertIn("`mc.py retire 10SE.2`", nudge["detail"])
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
        import mc as mc_module
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
        import mc as mc_module
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
        self.assertIn("reads todo on the roadmap at origin/main", stale[0]["detail"])
        self.assertIn("/roadmap:maintain", stale[0]["detail"])
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
            (self.box.repo / ".claude" / "mission-control.local.json").write_text(json.dumps({"collaboration": {"mode": "solo"}}))
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
        import mc as mc_module
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
        self.assertIn("| 10se2 | 10SE.2 | feat/a | briefing · waiting on you |", text)
        self.assertIn("## Waiting on you", text)
        self.assertIn("- 10SE.2 (10se2) sits on a permission prompt or a question in its own window since ", text)
        # the window the user must visit is the first section: ahead of the needs, the crew table and the slots
        self.assertIn("## Needs Jason", text)
        self.assertLess(text.index("## Waiting on you"), text.index("## Needs Jason"))
        self.assertLess(text.index("## Waiting on you"), text.index("| Session |"))
        self.assertLess(text.index("## Waiting on you"), text.index("| Slot |"))
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
        self.assertLess(text.index("## Needs Jason"), text.index("| Session |"))
        self.assertLess(text.index("| Session |"), text.index("| Slot |"))
        self.assertNotIn("## Archive", text)
        # the session goes: its row leaves the crew table for an Archive table at the end, with the state it last reported
        (self.box.sessions / "crew-1.json").unlink()
        text = self.box.mc("status", session="coord-1").stdout
        self.assertNotIn("(gone)", text)
        self.assertIn("## Archive", text)
        self.assertIn("| 10se2 | 10SE.2 | feat/a | gone (briefing) |", text)
        self.assertLess(text.index("| Slot |"), text.index("## Archive"))
        self.assertNotIn("| 10se2 | 10SE.2 | feat/a | briefing |", text, "a gone session is not in the crew table")

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
        self.assertEqual(need["why"], "start crew 10SE.2 in a new terminal window (opus, high: reworks the shared ranking query)")
        self.assertTrue(need["command"].startswith("claude --model opus --effort high --name '10se.2 search ranking' 'Start: you are crew 10SE.2 in run search. Read your brief at "), need["command"])
        self.assertIn("invoke /mission-control:crew and answer its five questions to the coordinator.'", need["command"])
        self.assertNotIn("--plugin-dir", need["command"])
        self.assertIn("## Needs Jason", self.box.mc("status", session="coord-1").stdout)
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
        self.assertEqual(need["why"], "start crew UXR in a new terminal window (the terminal's model)")
        self.assertTrue(need["command"].startswith("claude --plugin-dir /p/mission-control --name 'uxr crew' "), need["command"])
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
        self.assertIn("its launch line is need #2 on the board", unjoined[0]["detail"])

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
        self.assertIn("Re-arm each", hook)
        compacted = self.box.hook("session-start", {"source": "compact"}, session="crew-1")
        self.assertIn("still crew 10SE.2", compacted)
        self.assertIn("Your brief:", compacted)
        # the session goes away with its job open: reconcile names it
        (self.box.sessions / "crew-1.json").unlink()
        result = self._reconcile_with(self._gh({}))
        orphan = [item for item in result["drift"] if item["kind"] == "job-orphaned"]
        self.assertEqual(len(orphan), 1)
        self.assertIn("morning", orphan[0]["detail"])
        self.box.register("crew-1", "10se2", str(self.box.worktree))
        self.box.mc("jobs", "done", "morning", session="crew-1", cwd=self.box.worktree)
        self.assertEqual(json.loads(self.box.mc("jobs", "list", session="crew-1", cwd=self.box.worktree).stdout), [])

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
        self.assertIn("recent decisions: #1 option A", hook)
        listed = self.box.mc("decide", "list", session="coord-1").stdout
        self.assertIn("told 10SE.2", listed)
        # unacknowledged for too long: reconcile says so; an ack clears it
        sys.path.insert(0, str(HERE))
        import mc as mc_module
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
        self.assertIn("only the coordinator", refused.stdout)

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
        self.assertIn("## Running", text)
        self.assertIn("## Needs Jason", text)
        self.assertLess(text.index("## Needs Jason"), text.index("## Running"))
        self.assertNotIn("poetry run poe backfill", text.split("## Running")[1], "a running need shows no command to type")
        context = self.box.hook("session-start", {"source": "resume"}, session="coord-1", cwd=self.box.repo)
        self.assertIn("1 need open", context)
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
        self.assertIn("is done", self.box.mc("needs", "done", "2", "--superseded-by", "1", session="coord-1", expect=1).stdout, "a done need cannot be the successor")
        out = self.box.mc("needs", "done", "2", "--superseded-by", "3", session="coord-1").stdout
        self.assertIn("need #2 superseded by #3", out)
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
        import mc as mc_module
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
        import mc as mc_module
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
            self.assertIn("this worktree is crew 10SE.2", hook, "the hook finds the planned worktree without git")
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
        import mc as mc_module
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
        import mc as mc_module
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
        import mc as mc_module
        self._watching_session(270)
        self._set_watch(270, "watching", 424242)
        real = (mc_module.sh, mc_module.os.kill, mc_module.LEDGER_ROOT, mc_module.SESSIONS_DIR)

        def gone(_pid, _sig):
            raise ProcessLookupError
        mc_module.sh = lambda argv, timeout=8, cwd=None: (0, "python3 mc.py watch")
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
        import mc as mc_module
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
        # a process whose command line reads `mc.py watch`, as a real watcher's does
        victim = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "mc.py", "watch"])
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

    def _set_watch(self, pr, status, pid):
        row_path = list(self.box.ledger_root.glob("*/sessions/crew-1.json"))[0]
        row = json.loads(row_path.read_text())
        row["watch"] = {"pr": pr, "status": status, "pid": pid}
        row_path.write_text(json.dumps(row))

    def test_watch_stop_leaves_a_finished_watch_and_a_foreign_command_line_alone(self):
        self._watching_session(269)
        matching = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "mc.py", "watch"])
        plain = subprocess.Popen(["sleep", "62"])
        try:
            self._set_watch(269, "ended", matching.pid)  # the watcher finished; a recycled pid must not be signalled
            done = self.box.mc("watch", "--stop", "--pr", "269", session="crew-1", cwd=self.box.worktree)
            self.assertIn("nothing to stop", done.stdout)
            self._set_watch(269, "watching", plain.pid)  # a live pid that is not an mc.py watcher
            done = self.box.mc("watch", "--stop", "--pr", "269", session="crew-1", cwd=self.box.worktree)
            self.assertIn("not an mc.py watcher", done.stdout)
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
        self.assertNotIn("approved-unlanded", kinds)

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
        self.assertIn("no PRs on the board", out)
        self.assertEqual(self.box.mc("reconcile", cwd=self.box.tmp, expect=1).returncode, 1, "outside a repo is a refusal")

    def test_the_psql_probes_wait_no_longer_than_the_gh_lookups(self):
        sys.path.insert(0, str(HERE))
        import mc as mc_module
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
        self.assertIn("you hold the local Supabase stack slot", verdict["additionalContext"])

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
        self.assertIn("a human gate", verdict["additionalContext"])

    def test_by_user_on_a_command_line_is_denied(self):
        verdict = self.decision("python3 mc.py grant local-db --to me --by-user")
        self.assertEqual(verdict["permissionDecision"], "deny")

    def test_identity_overrides_on_an_mc_line_are_denied(self):
        for command in [
            "python3 mc.py grant local-db --to me --by",
            "python3 mc.py grant local-db --to me '--by-user'",
            'python3 mc.py grant local-db --to me "--by-user"',
            "python3 mc.py --session coord-1 grant local-db --to me",
            "python3 mc.py --session=coord-1 grant local-db --to me",
            "python3 mc.py --sess coord-1 grant local-db --to me",
            "CLAUDE_CODE_SESSION_ID=coord-1 python3 mc.py grant local-db --to me",
            "export CLAUDE_CODE_SESSION_ID=coord-1; python3 mc.py grant local-db --to me",
            "env CLAUDE_CODE_SESSION_ID=coord-1 python3 mc.py grant local-db --to me",
            "sh -c \"python3 mc.py grant local-db --to me --by-user\"",
        ]:
            self.assertEqual(self.decision(command)["permissionDecision"], "deny", command)

    def test_plain_mc_and_foreign_session_flags_are_not_denied(self):
        self.assertIsNone(self.decision("python3 mc.py status --json"))
        self.assertIsNone(self.decision("git log --session"))

    def test_a_subagent_is_gated_like_its_parent(self):
        command = "cd apps/api && poetry run poe db-reset-local-anyway"
        payload = {"tool_name": "Bash", "tool_input": {"command": command}, "agent_id": "agent-1"}
        verdict = json.loads(self.box.hook("pre-tool-use", payload))["hookSpecificOutput"]
        self.assertEqual(verdict["permissionDecision"], "deny")
        by_user = {"tool_name": "Bash", "tool_input": {"command": "python3 mc.py grant local-db --to me --by-user"}, "agent_id": "agent-1"}
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
        self.assertIn("crew 10SE.2", text)
        self.assertIn("mission control", text)
        self.assertIn(str(brief), text)
        coord = self.box.hook("session-start", {}, session="coord-1", cwd=self.box.repo)
        self.assertIn("coordinates run search", coord)
        self.assertEqual(self.box.hook("session-start", {}, session="x", cwd=self.box.repo), "")


class PushGate(unittest.TestCase):
    """`git push` is refused until `mc.py gate` has recorded green for the commit; no run is needed."""

    def setUp(self):
        self.box = Sandbox()
        self.repo = self.box.repo
        # the sandbox's worktree directory sits inside the repo and would count as untracked noise to the gate
        with open(self.repo / ".git" / "info" / "exclude", "a") as handle:
            handle.write("/.claude/worktrees/\n")

    def set_gate(self, commands, exempt=None):
        path = self.repo / ".claude" / "mission-control.json"
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
        path = self.repo / ".claude" / "mission-control.json"
        config = json.loads(path.read_text())
        config.pop("push_gate", None)  # the example config the sandbox copies opts in
        path.write_text(json.dumps(config))
        git(self.repo, "commit", "-qam", "no gate")
        self.assertIsNone(self.refused())

    def test_a_push_without_a_record_is_refused_and_names_the_command(self):
        self.set_gate({"test": "true"})
        reason = self.refused()
        self.assertIn("no green record", reason)
        self.assertIn("mc.py gate", reason)

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
        folder = self.repo / ".git" / "mission-control" / "gate"
        folder.mkdir(parents=True)
        (folder / f"{self.head()}.running").write_text(json.dumps({"pid": os.getpid()}))
        self.assertIn("still running", self.refused())

    def test_a_dead_lock_does_not_block(self):
        self.set_gate({"test": "true"})
        self.box.mc("gate", cwd=self.repo)
        folder = self.repo / ".git" / "mission-control" / "gate"
        (folder / f"{self.head()}.running").write_text(json.dumps({"pid": 99999999}))
        self.assertIsNone(self.refused())

    def test_the_gate_refuses_to_run_over_uncommitted_changes(self):
        self.set_gate({"test": "true"})
        (self.repo / "README.md").write_text("dirty\n")
        done = self.box.mc("gate", cwd=self.repo, expect=1)
        self.assertIn("uncommitted", done.stdout)

    def test_a_key_the_commands_block_lacks_is_refused_not_skipped(self):
        path = self.repo / ".claude" / "mission-control.json"
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
        path = self.repo / ".claude" / "mission-control.json"
        git(self.repo, "update-index", "--assume-unchanged", ".claude/mission-control.json")  # the real config is untracked
        config = json.loads(path.read_text())
        config["commands"]["lint"] = "true"
        config["push_gate"]["commands"].append("lint")
        path.write_text(json.dumps(config))
        reason = self.refused()
        self.assertIn("lint", reason)
        self.assertIn("mc.py gate", reason)
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


if __name__ == "__main__":
    unittest.main()
