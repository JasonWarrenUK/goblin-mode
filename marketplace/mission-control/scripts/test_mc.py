"""Tests for mc.py: the gate matcher, the ledger, authorisation and both hooks.

Run from this directory: python3 -m unittest test_mc

Every test works in a throwaway git repository with its own ledger root and
session registry (MISSION_CONTROL_HOME, CLAUDE_SESSIONS_DIR), so nothing here
touches ~/.claude. Probes that shell out (lsof, psql) are not exercised.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
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
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
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


if __name__ == "__main__":
    unittest.main()
