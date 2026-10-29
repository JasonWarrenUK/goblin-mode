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
        self.assertEqual(result["prs"][0]["waiting_on"], "no reviewer requested")

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

    @staticmethod
    def _roadmap(started=None, task="10SE.2"):
        """A rich roadmap listing one task, claimed (`started` set) or not."""
        row = {"id": task, "title": "the task", "status": "todo", "assignee": "Jason"}
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
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
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

    def test_a_claim_that_reached_main_under_another_subject_satisfies_a_merged_pr(self):
        """A sync batch or a `done` batch carries the claim to the trunk; the roadmap's state counts, not the commit subject."""
        self._roadmap_repo_with_origin(claim_on_branch=False, claim_on_main=True)
        git(self.box.repo, "merge", "-q", "--no-ff", "-m", "Merge feat/a", "feat/a")
        git(self.box.repo, "push", "-q", "origin", "main")
        self.box.start()
        self._crew_with_pr("10SE.2", "crew-1", "feat/a", 228, state="done")
        result = self._reconcile_with(self._gh(self._merged(228)))
        self.assertEqual([item["kind"] for item in result["drift"]], [])

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


if __name__ == "__main__":
    unittest.main()
