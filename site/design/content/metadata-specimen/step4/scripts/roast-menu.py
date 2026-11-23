#!/usr/bin/env python3
"""Print the roast skills as a menu, mildest first."""
import re
import sys
from pathlib import Path

HEAT = ["mild", "medium", "scorching"]
REMOVED = {"Agent", "Bash", "Edit", "Write", "NotebookEdit"}


def field(block: str, key: str) -> str:
	m = re.search(rf"^\s*{key}:\s*(.*)$", block, re.MULTILINE)
	return m.group(1).strip() if m else ""


menu, problems = [], []
for path in sorted(Path(".claude/skills").glob("*/SKILL.md")):
	block = path.read_text().split("---")[1]
	if field(block, "family") != "roast":
		continue
	name, heat = field(block, "name"), field(block, "heat")
	removed = set(re.findall(r"\w+", field(block, "disallowed-tools")))
	if field(block, "hands-off") == "true" and not REMOVED <= removed:
		problems.append(f"{name}: hands-off, but Claude keeps {', '.join(sorted(REMOVED - removed))}")
	rank = HEAT.index(heat) if heat in HEAT else len(HEAT)
	menu.append((rank, f"{heat or '?':<10} /{name:<14} {field(block, 'description')}"))

print("\n".join(line for _, line in sorted(menu)))
for problem in problems:
	print(problem, file=sys.stderr)
sys.exit(1 if problems else 0)
