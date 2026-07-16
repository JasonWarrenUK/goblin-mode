#!/usr/bin/env python3
"""validate_audit_findings.py — schema gate for the artefact-audit skill.

Validates a findings dataset before any HTML is generated, so a malformed
finding fails fast with a named field instead of rendering wrong. Mirrors the
partition-findings.mjs philosophy: the model never ships unvalidated data.

usage: validate_audit_findings.py <findings.json>
exit codes: 0 valid, 1 invalid (each problem printed), 2 unreadable/not JSON
Requires Python 3.8+, stdlib only.
"""
from __future__ import annotations

import json
import sys

CATEGORIES = {"correction", "issue", "improvement", "enhancement"}
SEVERITIES = {"high", "medium", "low"}
STATUSES = {"to_do", "in_progress", "done"}
CONFIDENCES = {"high", "medium", "low"}
REQUIRED = [
    "id", "title", "category", "severity", "evidence", "file_refs",
    "recommendation", "anchor", "theme", "confidence", "status",
    "outcome_note", "verify_notes",
]
DASHES = "—–―‒"  # em, en, horizontal bar, figure dash


def main(argv):
    if len(argv) != 2:
        print("usage: validate_audit_findings.py <findings.json>", file=sys.stderr)
        return 2
    try:
        data = json.loads(open(argv[1]).read())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"✗ could not load {argv[1]}: {exc}", file=sys.stderr)
        return 2

    problems = []
    findings = data.get("findings")
    if not isinstance(findings, list) or not findings:
        problems.append("findings: missing or empty array")
        findings = []

    seen_ids = set()
    for i, f in enumerate(findings):
        label = f"findings[{i}] (id={f.get('id', '?')})"
        for field in REQUIRED:
            if field not in f:
                problems.append(f"{label}: missing '{field}'")
        if f.get("id") in seen_ids:
            problems.append(f"{label}: duplicate id")
        seen_ids.add(f.get("id"))
        for field, allowed in [("category", CATEGORIES), ("severity", SEVERITIES),
                               ("status", STATUSES), ("confidence", CONFIDENCES)]:
            v = f.get(field)
            if v is not None and v not in allowed:
                problems.append(f"{label}: {field} {v!r} not in {sorted(allowed)}")
        if not isinstance(f.get("file_refs", []), list):
            problems.append(f"{label}: file_refs must be an array")
        for field in ("title", "recommendation", "outcome_note", "verify_notes"):
            text = f.get(field) or ""
            bad = [d for d in DASHES if d in text]
            if bad:
                problems.append(f"{label}: {field} contains a banned dash character")

    for i, r in enumerate(data.get("refuted", [])):
        if not r.get("title") or not r.get("notes"):
            problems.append(f"refuted[{i}]: needs both 'title' and 'notes'")

    counts = data.get("meta", {}).get("counts", {})
    if counts.get("confirmed") not in (None, len(findings)):
        problems.append(
            f"meta.counts.confirmed={counts.get('confirmed')} but there are "
            f"{len(findings)} findings")
    by_sev = counts.get("by_severity") or {}
    for sev in SEVERITIES:
        actual = sum(1 for f in findings if f.get("severity") == sev)
        if sev in by_sev and by_sev[sev] != actual:
            problems.append(
                f"meta.counts.by_severity.{sev}={by_sev[sev]} but actual is {actual}")

    if problems:
        print(f"✗ {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"✓ valid: {len(findings)} findings, {len(data.get('refuted', []))} refuted")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
