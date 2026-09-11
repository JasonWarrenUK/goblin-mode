#!/usr/bin/env python3
"""House-rule breaches in Claude's own terminal output, per day.

Reads the session transcripts under ~/.claude/projects (assistant text
blocks only, no subagent sidechains), runs the HOUSE_RULES patterns from
slop-scan.py over them with the same code masking strict mode uses, and
prints one row per day: messages, words, each rule's count and the total
per thousand words. That rate is the measure of whether the system-prompt
layer is doing its job; a hook can gate a commit message, nothing gates the
chatter except the prompt.

Transcripts get pruned, so `--record` merges each day's row into
library/state/prose-metrics.json and later runs fold that history back in.
The health check (prose-health.py) records on every run.

Usage:
    prose-metrics.py [--since YYYY-MM-DD] [--days N] [--record] [--json]
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
STATE_FILE = CONFIG_DIR / "library" / "state" / "prose-metrics.json"

spec = importlib.util.spec_from_file_location("slop_scan", HERE / "slop-scan.py")
slop_scan = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(slop_scan)

LABELS = [label for label, _ in slop_scan.HOUSE_RULES]
SHORT = {
	"em dash": "emdash",
	"spaced en dash": "endash",
	"Oxford comma": "oxford",
	"-ize / -ization": "ize",
	"American -or": "amer_or",
	"American -er": "amer_er",
	"American usage": "amer_use",
}


def empty_row() -> dict:
	row = {"msgs": 0, "words": 0}
	for label in LABELS:
		row[SHORT[label]] = 0
	return row


def count_text(text: str, row: dict) -> None:
	"""Add one assistant text block's words and house-rule hits to `row`."""
	row["msgs"] += 1
	row["words"] += len(text.split())
	lines = slop_scan.extract_lines(text, ".md", skip_fences=True)
	for label, hits, count in slop_scan.scan_group(lines, slop_scan.HOUSE_RULES, None, mask=True):
		row[SHORT[label]] += count


def scan_transcripts(root: Path, since: str) -> dict[str, dict]:
	"""Per-day rows from every transcript under `root`, days >= `since`."""
	days: dict[str, dict] = defaultdict(empty_row)
	for path in sorted(root.glob("*/*.jsonl")):
		try:
			with path.open(encoding="utf-8", errors="replace") as handle:
				for line in handle:
					try:
						entry = json.loads(line)
					except json.JSONDecodeError:
						continue
					if entry.get("type") != "assistant" or entry.get("isSidechain"):
						continue
					day = str(entry.get("timestamp", ""))[:10]
					if len(day) != 10 or day < since:
						continue
					for block in entry.get("message", {}).get("content", []) or []:
						if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
							count_text(block["text"], days[day])
		except OSError:
			continue
	return dict(days)


def load_state(path: Path) -> dict[str, dict]:
	try:
		return json.loads(path.read_text(encoding="utf-8"))
	except (OSError, json.JSONDecodeError):
		return {}


def merge(history: dict[str, dict], fresh: dict[str, dict]) -> dict[str, dict]:
	"""Fresh transcript rows win for the days they cover; history fills the rest."""
	merged = dict(history)
	for day, row in fresh.items():
		if row["words"] >= merged.get(day, {}).get("words", 0):
			merged[day] = row
	return merged


def house_total(row: dict) -> int:
	return sum(row[SHORT[label]] for label in LABELS)


def per_thousand(row: dict, key: str | None = None) -> float:
	hits = house_total(row) if key is None else row[key]
	return 1000 * hits / row["words"] if row["words"] else 0.0


def render(rows: dict[str, dict]) -> str:
	header = f"{'day':10} {'msgs':>5} {'words':>7} {'emdash':>6} {'oxford':>6} {'ize':>4} {'amer':>5} {'house/1k':>9} {'emdash/1k':>9}"
	out = [header]
	for day in sorted(rows):
		row = rows[day]
		amer = row["amer_or"] + row["amer_er"] + row["amer_use"]
		out.append(
			f"{day:10} {row['msgs']:5} {row['words']:7} {row['emdash'] + row['endash']:6} {row['oxford']:6} "
			f"{row['ize']:4} {amer:5} {per_thousand(row):9.2f} {per_thousand(row, 'emdash'):9.2f}"
		)
	return "\n".join(out)


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--since", help="first day to include (YYYY-MM-DD)")
	parser.add_argument("--days", type=int, default=28, help="window when --since is absent (default 28)")
	parser.add_argument("--record", action="store_true", help="merge today's rows into library/state/prose-metrics.json")
	parser.add_argument("--json", action="store_true", help="emit rows as JSON instead of a table")
	parser.add_argument("--projects", type=Path, default=CONFIG_DIR / "projects", help=argparse.SUPPRESS)
	parser.add_argument("--state", type=Path, default=STATE_FILE, help=argparse.SUPPRESS)
	args = parser.parse_args()

	since = args.since or (dt.date.today() - dt.timedelta(days=args.days)).isoformat()
	fresh = scan_transcripts(args.projects, "0000-00-00" if args.record else since)
	history = load_state(args.state)
	rows = merge(history, fresh)
	if args.record:
		args.state.parent.mkdir(parents=True, exist_ok=True)
		args.state.write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n", encoding="utf-8")
	window = {day: row for day, row in rows.items() if day >= since}
	if args.json:
		print(json.dumps(window, indent=1, sort_keys=True))
	else:
		print(render(window) if window else f"no assistant output found since {since}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
