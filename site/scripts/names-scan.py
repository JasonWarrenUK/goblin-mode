#!/usr/bin/env python3
"""No real person other than Jason is named anywhere the site publishes.

Run from the repository root before asking for a PR to be approved; it must
print nothing but its summary line and exit 0:

    python3 -I site/scripts/names-scan.py

It reads the real names from the dossier slugs in the main checkout's
library/profiles/dossier/ and checks every file git tracks under site/ (the
source, the tests, the scripts and the whole design record) and every built
page. CSS and scripts are stripped first: `max-width` and `Math.max` are not
people.

It cannot run in CI. The names it looks for are the private dossier itself,
which is gitignored and never leaves this machine, so a CI copy would either
hold no names and pass vacuously or need the names published to look for
them. The scan refuses to pass with no names, so it is run by hand before a
PR and its output quoted in the PR's Verification section.
"""

import pathlib
import re
import subprocess
import sys

DOSSIER = pathlib.Path.home() / ".claude" / "library" / "profiles" / "dossier"
SUFFIXES = (".html", ".svelte", ".ts", ".md", ".json", ".py", ".js", ".css", ".zsh", ".yml", ".txt")
SKIP_DIRS = {"generated", "_app", "node_modules"}


def scanned() -> list[pathlib.Path]:
    """Every file git tracks under site/, then every built page."""
    tracked = subprocess.run(["git", "ls-files", "-z", "--", "site"], capture_output=True, text=True, check=True).stdout.split("\0")
    built = sorted(pathlib.Path("site/build").rglob("*")) if pathlib.Path("site/build").exists() else []
    return [path for path in [pathlib.Path(p) for p in tracked if p] + built if path.is_file() and path.suffix in SUFFIXES and not SKIP_DIRS & set(path.parts)]

names = sorted(p.stem for p in DOSSIER.glob("*.md") if p.stem.lower() not in ("readme", "jason"))
if not names:
    sys.exit(f"names-scan: no dossier slugs under {DOSSIER}; refusing to pass with nothing to look for")


def text_of(path: pathlib.Path) -> str:
    body = path.read_text(errors="ignore")
    if path.suffix in (".html", ".svelte"):
        body = re.sub(r"<(style|script)\b.*?</\1>", "", body, flags=re.S | re.I)
    # Code is not prose: an effort level shown as <code>max</code> or `max`,
    # and a method call such as Math.max(...), are not people.
    body = re.sub(r"<code\b[^>]*>.*?</code>", " ", body, flags=re.S | re.I)
    body = re.sub(r"`[^`\n]*`", " ", body)
    body = re.sub(r"\.\w+\s*\(", " (", body)
    if path.suffix in (".css", ".js"):
        # a stylesheet or script is all property and function names, hyphenated or called
        body = re.sub(r"\b\w+(?:-\w+)+\b|\b\w+\s*\(", " ", body)
    return body


hits = 0
files = 0
for path in scanned():
    files += 1
    body = text_of(path)
    for name in names:
        for match in re.finditer(r"\b" + re.escape(name) + r"\b", body, re.I):
            hits += 1
            print(f"{path}: {match.group(0)!r} at char {match.start()}")

print(f"names-scan: {len(names)} names checked across {files} files, {hits} hits", file=sys.stderr)
sys.exit(1 if hits else 0)
