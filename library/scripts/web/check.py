#!/usr/bin/env python3
"""check.py: the mechanical half of the web principles check.

Each subcommand tests one principle from skills/web-conventions/principles.md
and prints findings; `--json` prints them as entries in the observation
store contract (source check, principle N) so the web-check skill can add
them with observations.py. Judgement (principles 1, 2, 3, 5, 11 and the
other half of 4, 6, 8, 10) belongs to the web-principles agent.

usage:
  check.py export EXPORT.json [--max-age HOURS]          principle 7
      Every non-open entry has a resolution; the export is not stale.
  check.py coverage SHOTS_DIR --routes R[,R] --devices D[,D]   principle 8
      Every route captured on every device, by the capture naming rule
      <device>-<route>[-<specifier>].<ext>; with one device the prefix
      is absent.
  check.py classes --source DIR --library CSS[,CSS] [--product CSS[,CSS]]   principle 9
      Class names the product's own CSS defines that the library's CSS
      also defines (a collision), plus names used in the source that the
      library defines and the product does not (a dependence worth
      knowing). --product defaults to every .css under --source.
  check.py tokens WIREFRAME.html --product CSS[,CSS]      principle 6
      Custom properties the wireframe declares that the product's CSS
      does not; callout badges without an explain item and the reverse.
  check.py brief SCOPE.md                                 principle 10
      The copy brief section is filled: no bracketed placeholders left.

exit 0 no findings, 1 findings printed, 2 unreadable input.
Requires Python 3.8+, stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CLASS_DEF = re.compile(r"\.(-?[_a-zA-Z][\w-]*)")
CLASS_ATTR = re.compile(r"""\bclass\s*=\s*(?:"([^"]*)"|'([^']*)'|\{`([^`]*)`\})""")
CLASS_DIRECTIVE = re.compile(r"\bclass:([\w-]+)")
CUSTOM_PROP = re.compile(r"--([\w-]+)\s*:")
CALLOUT_BADGE = re.compile(r"""<span[^>]*class="[^"]*\bco\b[^"]*"[^>]*>\s*(\d+)\s*</span>""")
EXPLAIN_ITEM = re.compile(r"""<li[^>]*>\s*<span[^>]*class="[^"]*\bco\b[^"]*"[^>]*>\s*(\d+)\s*</span>""")
PLACEHOLDER = re.compile(r"\[[^\]]+\]")
SOURCE_EXT = {".svelte", ".html", ".jsx", ".tsx", ".vue", ".astro"}


def finding(principle: int, where: str, title: str, detail: str = "") -> dict:
	return {"principle": principle, "where": where, "title": title, "detail": detail,
			"severity": "major", "source": "check", "areas": []}


def emit(findings: list[dict], as_json: bool) -> int:
	if as_json:
		print(json.dumps(findings, indent=2))
	else:
		for f in findings:
			print(f"principle {f['principle']} · {f['where']}: {f['title']}" + (f"\n    {f['detail']}" if f["detail"] else ""))
		if not findings:
			print("no findings")
	return 1 if findings else 0


def read_text(path: Path) -> str:
	return path.read_text(encoding="utf-8")


def split_paths(value: str) -> list[Path]:
	return [Path(p.strip()) for p in value.split(",") if p.strip()]


# principle 7

def cmd_export(args: argparse.Namespace) -> int:
	path = Path(args.export)
	try:
		export = json.loads(read_text(path))
	except (OSError, json.JSONDecodeError) as err:
		print(f"unreadable: {err}", file=sys.stderr)
		return 2
	entries = export.get("entries") if isinstance(export, dict) else None
	if not isinstance(entries, list):
		print(f"unreadable: {path} is not an export file", file=sys.stderr)
		return 2
	findings = []
	for e in entries:
		if e.get("status", "open") != "open" and not str(e.get("resolution", "")).strip():
			findings.append(finding(7, f"#{e.get('seq')}", f"{e.get('status')} without a resolution line"))
	if args.max_age is not None:
		exported = export.get("exported")
		try:
			stamp = datetime.fromisoformat(str(exported).replace("Z", "+00:00"))
			age = (datetime.now(timezone.utc) - stamp).total_seconds() / 3600
			if age > args.max_age:
				findings.append(finding(7, str(path), f"export is {age:.1f}h old, older than {args.max_age:g}h", "a pass that has not exported is not finished"))
		except (TypeError, ValueError):
			findings.append(finding(7, str(path), "export carries no exported timestamp"))
	return emit(findings, args.json)


# principle 8

def parse_capture(name: str, devices: list[str]) -> tuple[str | None, str, str | None]:
	"""(device, route, specifier) from a capture file stem under the naming rule."""
	parts = name.split("-")
	device = None
	if len(devices) > 1 and parts and parts[0] in devices:
		device = parts.pop(0)
	if not parts:
		return device, "", None
	route = parts.pop(0)
	specifier = "-".join(parts) or None
	return device, route, specifier


def cmd_coverage(args: argparse.Namespace) -> int:
	shots = Path(args.shots_dir)
	if not shots.is_dir():
		print(f"not a directory: {shots}", file=sys.stderr)
		return 2
	routes = [r.strip() for r in args.routes.split(",") if r.strip()]
	devices = [d.strip() for d in args.devices.split(",") if d.strip()]
	if not routes or not devices:
		print("routes and devices must both be given", file=sys.stderr)
		return 2
	seen: dict[tuple[str | None, str], int] = {}
	unknown = []
	for path in sorted(shots.iterdir()):
		if not path.is_file() or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
			continue
		device, route, _ = parse_capture(path.stem, devices)
		if route not in routes or (len(devices) > 1 and device is None):
			unknown.append(path.name)
			continue
		seen[(device, route)] = seen.get((device, route), 0) + 1
	findings = []
	for route in routes:
		for device in (devices if len(devices) > 1 else [None]):
			if (device, route) not in seen:
				where = f"{device}-{route}" if device else route
				findings.append(finding(8, where, "no capture for this route on this device"))
	for name in unknown:
		findings.append(finding(8, name, "capture does not follow the naming rule or names an unknown route", "expected <device>-<route>[-<specifier>] with the declared devices and routes"))
	return emit(findings, args.json)


# principle 9

def defined_classes(css_paths: list[Path]) -> dict[str, Path]:
	out: dict[str, Path] = {}
	for path in css_paths:
		text = read_text(path)
		text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
		# selectors are what precedes each `{`; drop declaration blocks
		for selector in re.findall(r"([^{}]+)\{", text):
			if ":" in selector and selector.strip().startswith("@"):
				continue
			for name in CLASS_DEF.findall(selector):
				out.setdefault(name, path)
	return out


def used_classes(source_dir: Path) -> dict[str, Path]:
	out: dict[str, Path] = {}
	for path in sorted(source_dir.rglob("*")):
		if path.suffix not in SOURCE_EXT or "node_modules" in path.parts:
			continue
		text = read_text(path)
		for match in CLASS_ATTR.finditer(text):
			value = next(g for g in match.groups() if g is not None)
			for name in re.split(r"[\s{}]+", value):
				if re.fullmatch(r"-?[_a-zA-Z][\w-]*", name or ""):
					out.setdefault(name, path)
		for name in CLASS_DIRECTIVE.findall(text):
			out.setdefault(name, path)
	return out


def expand_css(paths: list[Path]) -> list[Path]:
	files = []
	for p in paths:
		if p.is_dir():
			files.extend(sorted(f for f in p.rglob("*.css") if "node_modules" not in f.parts))
		elif p.exists():
			files.append(p)
	return files


def cmd_classes(args: argparse.Namespace) -> int:
	source = Path(args.source)
	if not source.is_dir():
		print(f"not a directory: {source}", file=sys.stderr)
		return 2
	library_files = expand_css(split_paths(args.library))
	if not library_files:
		print("no library CSS found", file=sys.stderr)
		return 2
	product_files = expand_css(split_paths(args.product)) if args.product else expand_css([source])
	library = defined_classes(library_files)
	product = defined_classes(product_files)
	used = used_classes(source)
	findings = []
	for name in sorted(set(product) & set(library)):
		findings.append(finding(9, str(product[name]), f".{name} is defined by the product and by the UI library ({library[name].name})", "rename the product's class or scope it; the library's rule may win and show as a stray dot or a blank column"))
	for name in sorted((set(used) & set(library)) - set(product)):
		findings.append({**finding(9, str(used[name]), f".{name} comes from the UI library only", "fine while intended; listed so a library upgrade that renames it is caught"), "severity": "nit"})
	return emit(findings, args.json)


# principle 6

def cmd_tokens(args: argparse.Namespace) -> int:
	wireframe = Path(args.wireframe)
	try:
		page = read_text(wireframe)
	except OSError as err:
		print(f"unreadable: {err}", file=sys.stderr)
		return 2
	product_files = expand_css(split_paths(args.product))
	if not product_files:
		print("no product CSS found", file=sys.stderr)
		return 2
	product_props = set()
	for path in product_files:
		product_props.update(CUSTOM_PROP.findall(read_text(path)))
	style = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", page, flags=re.S))
	root_blocks = re.findall(r":root[^{]*\{(.*?)\}", style, flags=re.S)
	wireframe_props = set()
	for block in root_blocks:
		wireframe_props.update(CUSTOM_PROP.findall(block))
	findings = []
	foreign = sorted(p for p in wireframe_props if p not in product_props and not p.startswith(("callout", "mono", "annot")))
	if not wireframe_props:
		findings.append(finding(6, wireframe.name, "no :root custom properties: the wireframe is not drawn in tokens"))
	elif foreign:
		findings.append(finding(6, wireframe.name, f"{len(foreign)} custom properties the product's CSS does not define", ", ".join(f"--{p}" for p in foreign[:12])))
	badges = CALLOUT_BADGE.findall(page)
	explain_badges = EXPLAIN_ITEM.findall(page)
	explained = set(explain_badges)
	# every explain item carries a badge too, so a number has a mock badge
	# only when it occurs more often than it is explained
	numbers = {n for n in badges if badges.count(n) > explain_badges.count(n)}
	for n in sorted(numbers - explained, key=int):
		findings.append(finding(6, wireframe.name, f"callout {n} has no explain item"))
	for n in sorted(explained - numbers, key=int):
		findings.append(finding(6, wireframe.name, f"explain item {n} has no badge in the mock"))
	if not badges:
		findings.append(finding(6, wireframe.name, "no numbered callouts"))
	return emit(findings, args.json)


# principle 10

def cmd_brief(args: argparse.Namespace) -> int:
	scope = Path(args.scope)
	try:
		text = read_text(scope)
	except OSError as err:
		print(f"unreadable: {err}", file=sys.stderr)
		return 2
	match = re.search(r"^## .*[Cc]opy brief.*?$\n(.*?)(?=^## |\Z)", text, flags=re.S | re.M)
	findings = []
	if not match:
		findings.append(finding(10, scope.name, "no copy brief section"))
	else:
		body = match.group(1)
		left = PLACEHOLDER.findall(body)
		if left:
			findings.append(finding(10, scope.name, f"copy brief still holds {len(left)} placeholders", "; ".join(left[:4])))
		rows = [line for line in body.splitlines() if line.startswith("|") and not set(line.strip()) <= set("|-: ")]
		cells = [c.strip() for line in rows[1:] for c in line.strip("|").split("|")[1:]]
		if rows and not any(cells):
			findings.append(finding(10, scope.name, "copy brief table is empty"))
	return emit(findings, args.json)


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="mechanical principles checks")
	parser.add_argument("--json", action="store_true", help="print findings as store entries")
	sub = parser.add_subparsers(dest="command", required=True)
	p = sub.add_parser("export"); p.add_argument("export"); p.add_argument("--max-age", type=float, default=None); p.set_defaults(func=cmd_export)
	p = sub.add_parser("coverage"); p.add_argument("shots_dir"); p.add_argument("--routes", required=True); p.add_argument("--devices", required=True); p.set_defaults(func=cmd_coverage)
	p = sub.add_parser("classes"); p.add_argument("--source", required=True); p.add_argument("--library", required=True); p.add_argument("--product", default=None); p.set_defaults(func=cmd_classes)
	p = sub.add_parser("tokens"); p.add_argument("wireframe"); p.add_argument("--product", required=True); p.set_defaults(func=cmd_tokens)
	p = sub.add_parser("brief"); p.add_argument("scope"); p.set_defaults(func=cmd_brief)
	return parser


def main(argv: list[str]) -> int:
	args = build_parser().parse_args(argv)
	return args.func(args)


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
