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
