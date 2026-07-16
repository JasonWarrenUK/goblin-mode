#!/usr/bin/env python3
"""config_permit.py — deterministic half of the config-permit skill.

Appends a permission rule to `permissions.allow` at the chosen scope. Editing
settings JSON by hand is the failure surface this replaces: the script
dedupes, preserves formatting (and comments, for the JSONC global file) and
runs the sync hook, so a permission grant is one command with clear exits.

usage: config_permit.py <global|project> <rule ...>
  global   ~/.claude/settings.local.jsonc (comment-preserving text insertion),
           then runs ~/.claude/hooks/settings-sync.sh
  project  .claude/settings.local.json in the cwd's project (created if absent)

The rule may contain spaces; everything after the scope is joined verbatim.

exit codes: 0 = added (or already present — says which), 2 = error, nothing
written. Requires Python 3.8+, stdlib only.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

GLOBAL_JSONC = Path.home() / ".claude" / "settings.local.jsonc"
SYNC_HOOK = Path.home() / ".claude" / "hooks" / "settings-sync.sh"


def fail(msg):
    print(f"✗ {msg}", file=sys.stderr)
    return 2


def add_project(rule):
    path = Path.cwd() / ".claude" / "settings.local.json"
    if path.exists():
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            return fail(f"{path} is not valid JSON: {exc}")
    else:
        data = {}
    allow = data.setdefault("permissions", {}).setdefault("allow", [])
    if rule in allow:
        print(f"already present in {path}: {rule}")
        return 0
    allow.append(rule)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"added to {path} (project scope): {rule}")
    return 0


def add_global(rule):
    if not GLOBAL_JSONC.exists():
        return fail(f"{GLOBAL_JSONC} not found")
    text = GLOBAL_JSONC.read_text()
    needle = json.dumps(rule)
    if needle in text:
        print(f"already present in {GLOBAL_JSONC}: {rule}")
        return 0
    # Comment-preserving insertion: put the rule on a new line directly after
    # the `"allow": [` opener, matching the indentation of the line below it.
    m = re.search(r'("allow"\s*:\s*\[)([ \t]*\n([ \t]*))?', text)
    if not m:
        return fail(
            f'could not find a `"allow": [` array in {GLOBAL_JSONC} — '
            "add the rule manually")
    if m.group(2):  # multi-line array: insert as first element
        indent = m.group(3)
        insert_at = m.end(1)
        text = text[:insert_at] + f"\n{indent}{needle}," + text[insert_at:]
    else:  # single-line array `"allow": [...]`
        insert_at = m.end(1)
        rest = text[insert_at:].lstrip()
        sep = "" if rest.startswith("]") else ", "
        text = text[:insert_at] + needle + sep + text[insert_at:].lstrip(" ")
    GLOBAL_JSONC.write_text(text)
    print(f"added to {GLOBAL_JSONC} (global scope): {rule}")
    if SYNC_HOOK.exists():
        result = subprocess.run([str(SYNC_HOOK)], capture_output=True, text=True)
        if result.returncode != 0:
            return fail(f"settings-sync.sh failed: {result.stderr.strip()}")
        print("synced to settings.local.json")
    else:
        print(f"note: {SYNC_HOOK} not found — sync skipped")
    return 0


def main(argv):
    if len(argv) < 3 or argv[1] not in ("global", "project"):
        return fail("usage: config_permit.py <global|project> <rule ...>")
    rule = " ".join(argv[2:])
    return add_project(rule) if argv[1] == "project" else add_global(rule)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
