#!/usr/bin/env python3
"""observations.py: the deterministic half of the web-* observation store.

The live store is a published artefact's `db` collection `observations`,
read with the ArtifactData tool (`list` with `out_dir` saves one JSON per
document). This script turns that directory into the repo's durable record
and answers questions about it, so the skills and the gh pr create guard
judge from exact numbers.

usage:
  observations.py export <docs-dir> --artifact URL --out PATH
	  Assemble <docs-dir>/**/*.json (one document each) into the export
	  file {exported, artifact, entries[]}, sorted by seq. Validates every
	  entry against the store contract in web-conventions SKILL.md.
	  exit 0 written, 1 contract faults (each printed, nothing written),
	  2 unreadable input
  observations.py status <export.json> [--json] [--max-age HOURS]
	  Counts by status and severity, the open entries and the unwaived
	  principles findings. exit 0 when nothing blocks sign-off, 1 when
	  something does (open entries, unwaived check findings or an export
	  older than --max-age), 2 unreadable
  observations.py add <export.json> --entry JSON [--entry JSON ...]
	  Append entries (a principles finding, a failed capture) to an
	  export file that has no live store: design mode. Assigns seq,
	  createdAt and status open. exit 0, 1 contract faults, 2 unreadable

Requires Python 3.8+, stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SEVERITIES = ("blocker", "major", "minor", "nit", "praise")
STATUSES = ("open", "fixed", "declined", "waived")
SOURCES = ("jason", "check", "walkthrough")
AREAS = (
	"layout", "copy", "colour-type", "interaction", "navigation",
	"feedback", "accessibility", "performance", "data",
)
REQUIRED = ("seq", "where", "severity", "title", "status")


def now_iso() -> str:
	return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate(entry: dict, label: str) -> list[str]:
	"""Return the contract faults in one entry, as `label: fault` lines."""
	faults = []
	for key in REQUIRED:
		if key not in entry or entry[key] in ("", None):
			faults.append(f"{label}: missing {key}")
	if not isinstance(entry.get("seq"), int):
		faults.append(f"{label}: seq is not an integer")
	if entry.get("severity") not in SEVERITIES:
		faults.append(f"{label}: severity {entry.get('severity')!r} not in {SEVERITIES}")
	status = entry.get("status")
	if status not in STATUSES:
		faults.append(f"{label}: status {status!r} not in {STATUSES}")
	elif status != "open" and not str(entry.get("resolution", "")).strip():
		faults.append(f"{label}: status {status} without a resolution")
	source = entry.get("source", "jason")
	if source not in SOURCES:
		faults.append(f"{label}: source {source!r} not in {SOURCES}")
	if source == "check" and not isinstance(entry.get("principle"), int):
		faults.append(f"{label}: a check finding needs an integer principle")
	areas = entry.get("areas", [])
	if not isinstance(areas, list):
		faults.append(f"{label}: areas is not a list")
	else:
		for area in areas:
			if area not in AREAS:
				faults.append(f"{label}: area {area!r} not in {AREAS}")
	return faults


def load_documents(docs_dir: Path) -> list[dict]:
	entries = []
	for path in sorted(docs_dir.rglob("*.json")):
		with path.open() as fh:
			body = json.load(fh)
		if not isinstance(body, dict):
			raise ValueError(f"{path}: not a JSON object")
		entry = dict(body)
		entry.setdefault("id", path.stem)
		entries.append(entry)
	return entries


def cmd_export(args: argparse.Namespace) -> int:
	docs_dir = Path(args.docs_dir)
	if not docs_dir.is_dir():
		print(f"not a directory: {docs_dir}", file=sys.stderr)
		return 2
	try:
		entries = load_documents(docs_dir)
	except (ValueError, json.JSONDecodeError) as err:
		print(f"unreadable: {err}", file=sys.stderr)
		return 2
	faults = []
	for entry in entries:
		faults.extend(validate(entry, f"#{entry.get('seq', '?')} ({entry['id']})"))
	seqs = [e.get("seq") for e in entries if isinstance(e.get("seq"), int)]
	if len(seqs) != len(set(seqs)):
		faults.append("duplicate seq values")
	if faults:
		print("\n".join(faults))
		return 1
	entries.sort(key=lambda e: e["seq"])
	export = {"exported": now_iso(), "artifact": args.artifact, "entries": entries}
	out = Path(args.out)
	out.parent.mkdir(parents=True, exist_ok=True)
	with out.open("w") as fh:
		json.dump(export, fh, indent="\t", ensure_ascii=False)
		fh.write("\n")
	print(f"wrote {out}: {len(entries)} entries")
	return 0


def read_export(path: Path) -> dict | None:
	try:
		with path.open() as fh:
			export = json.load(fh)
	except (OSError, json.JSONDecodeError) as err:
		print(f"unreadable: {err}", file=sys.stderr)
		return None
	if not isinstance(export, dict) or not isinstance(export.get("entries"), list):
		print(f"unreadable: {path} is not an export file", file=sys.stderr)
		return None
	return export


def summarise(export: dict, max_age_hours: float | None) -> dict:
	entries = export["entries"]
	by_status = {s: 0 for s in STATUSES}
	by_severity = {s: 0 for s in SEVERITIES}
	for e in entries:
		by_status[e.get("status", "open")] = by_status.get(e.get("status", "open"), 0) + 1
		by_severity[e.get("severity", "minor")] = by_severity.get(e.get("severity", "minor"), 0) + 1
	open_entries = [e for e in entries if e.get("status", "open") == "open"]
	unwaived = [e for e in open_entries if e.get("source") == "check"]
	age_hours = None
	stale = False
	if export.get("exported"):
		try:
			exported = datetime.fromisoformat(export["exported"].replace("Z", "+00:00"))
			age_hours = (datetime.now(timezone.utc) - exported).total_seconds() / 3600
			stale = max_age_hours is not None and age_hours > max_age_hours
		except ValueError:
			stale = max_age_hours is not None
	blocks = []
	if open_entries:
		blocks.append(f"{len(open_entries)} open")
	if unwaived:
		blocks.append(f"{len(unwaived)} unwaived principles findings")
	if stale:
		blocks.append(f"export older than {max_age_hours:g}h")
	return {
		"total": len(entries),
		"by_status": by_status,
		"by_severity": by_severity,
		"open": [{"seq": e.get("seq"), "severity": e.get("severity"), "where": e.get("where"),
				  "title": e.get("title"), "source": e.get("source", "jason"),
				  "principle": e.get("principle")} for e in open_entries],
		"age_hours": None if age_hours is None else round(age_hours, 2),
		"blocks": blocks,
	}


def cmd_status(args: argparse.Namespace) -> int:
	export = read_export(Path(args.export))
	if export is None:
		return 2
	summary = summarise(export, args.max_age)
	if args.json:
		print(json.dumps(summary, indent=2))
	else:
		print(f"{summary['total']} entries: " + ", ".join(
			f"{n} {s}" for s, n in summary["by_status"].items() if n))
		for e in summary["open"]:
			tag = f" [principle {e['principle']}]" if e["source"] == "check" else ""
			print(f"  #{e['seq']} {e['severity']} {e['where']}: {e['title']}{tag}")
		print("blocks sign-off: " + ("; ".join(summary["blocks"]) if summary["blocks"] else "nothing"))
	return 1 if summary["blocks"] else 0


def cmd_add(args: argparse.Namespace) -> int:
	path = Path(args.export)
	if path.exists():
		export = read_export(path)
		if export is None:
			return 2
	else:
		export = {"exported": None, "artifact": None, "entries": []}
	entries = export["entries"]
	next_seq = max((e.get("seq", 0) for e in entries if isinstance(e.get("seq"), int)), default=0) + 1
	new = []
	faults = []
	for raw in args.entry:
		try:
			entry = json.loads(raw)
		except json.JSONDecodeError as err:
			print(f"unreadable entry: {err}", file=sys.stderr)
			return 2
		entry.setdefault("seq", next_seq)
		next_seq = max(next_seq, entry["seq"]) + 1
		entry.setdefault("status", "open")
		entry.setdefault("resolution", "")
		entry.setdefault("areas", [])
		entry.setdefault("createdAt", now_iso())
		entry["updatedAt"] = entry["createdAt"]
		entry.setdefault("id", f"local-{entry['seq']}")
		faults.extend(validate(entry, f"#{entry['seq']}"))
		new.append(entry)
	if faults:
		print("\n".join(faults))
		return 1
	entries.extend(new)
	entries.sort(key=lambda e: e["seq"])
	export["exported"] = now_iso()
	path.parent.mkdir(parents=True, exist_ok=True)
	with path.open("w") as fh:
		json.dump(export, fh, indent="\t", ensure_ascii=False)
		fh.write("\n")
	print(f"added {len(new)} to {path}: {len(entries)} entries")
	return 0


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="observation store: export, status, add")
	sub = parser.add_subparsers(dest="command", required=True)
	p = sub.add_parser("export")
	p.add_argument("docs_dir")
	p.add_argument("--artifact", required=True)
	p.add_argument("--out", required=True)
	p.set_defaults(func=cmd_export)
	p = sub.add_parser("status")
	p.add_argument("export")
	p.add_argument("--json", action="store_true")
	p.add_argument("--max-age", type=float, default=None, help="hours; older exports block")
	p.set_defaults(func=cmd_status)
	p = sub.add_parser("add")
	p.add_argument("export")
	p.add_argument("--entry", action="append", required=True, help="JSON object; repeatable")
	p.set_defaults(func=cmd_add)
	return parser


def main(argv: list[str]) -> int:
	args = build_parser().parse_args(argv)
	return args.func(args)


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
