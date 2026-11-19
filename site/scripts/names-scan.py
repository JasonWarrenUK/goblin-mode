#!/usr/bin/env python3
"""No real person other than Jason is named anywhere the site publishes.

Run from the repository root before asking for a PR to be approved; it must
print nothing but its summary line and exit 0:

    python3 -I site/scripts/names-scan.py

It reads the real names from the dossier slugs in the main checkout's
library/profiles/dossier/ (gitignored, so absent in CI and in a fresh clone;
the scan refuses to pass vacuously when it finds none) and checks the text of
the site's source and of the built pages. CSS and scripts are stripped first:
`max-width` and `Math.max` are not people.
"""

import pathlib
import re
import sys

DOSSIER = pathlib.Path.home() / ".claude" / "library" / "profiles" / "dossier"
ROOTS = [pathlib.Path("site/src"), pathlib.Path("site/build")]
SKIP_DIRS = {"generated", "_app"}

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
    return body


hits = 0
files = 0
for root in ROOTS:
    if not root.exists():
        continue
    for path in root.rglob("*"):
        if not path.is_file() or SKIP_DIRS & set(path.parts) or path.suffix not in (".html", ".svelte", ".ts", ".md", ".json"):
            continue
        files += 1
        body = text_of(path)
        for name in names:
            for match in re.finditer(r"\b" + re.escape(name) + r"\b", body, re.I):
                hits += 1
                print(f"{path}: {match.group(0)!r} at char {match.start()}")

print(f"names-scan: {len(names)} names checked across {files} files, {hits} hits", file=sys.stderr)
sys.exit(1 if hits else 0)
