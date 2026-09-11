#!/usr/bin/env python3
"""Mechanical evidence pass for /red-doc, and the house-rule gate behind it.

Counts the tells that a human reviewer can verify by grep: house-rule
breaches, rhetorical defaults, first-person density, hedge boilerplate,
LLM lexicon, borrowed weight, numeral-style inconsistency and verbatim
self-repetition.

Every count here is evidence a sceptic can reproduce. Nothing in report
mode decides whether a passage is bad; it locates candidates and the
reviewer reads them. `--strict` is the one mode that decides: house rules
only, one hit per line, exit 1 on any hit. It backs the commit-msg git hook
and the pre-approval scan in the prose-producing skills.

Usage:
    slop-scan.py TARGET [TARGET...] [--top N] [--shingle N] [--house-only]
    slop-scan.py --strict TARGET [TARGET...]
    ... | slop-scan.py --strict -

TARGET is a file, or `-` for stdin. Accepts .md, .html, .txt. HTML is
stripped of script/style blocks and tags line by line, so reported line
numbers match the source file.

Strict mode skips fenced code blocks, Markdown blockquotes and lines shaped
like this scanner's own output (`L<n> <rule>: …`), and, per line, masks
inline code, URLs, email addresses, identifier-shaped tokens (two or more
segments joined by - _ . / : or backslash) and double-quoted spans (straight
or curly; an unbalanced quote masks to the end of its own line and no
further) before matching. That is what keeps `background-color`,
`feat/colorize`, a quoted title and a pasted scan hit out of the rules.
The cost: hyphenated English such as "behavior-driven" and dialogue in
double quotes are masked too. Strict is a gate, so a missed hit is the
cheaper error. Backticks remain the one container the writer controls.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------- extraction

SCRIPT_STYLE = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
TAG = re.compile(r"<[^>]+>")
FENCE = re.compile(r"^\s*(?:`{3,}|~{3,})")
BLOCKQUOTE = re.compile(r"^\s*>")
SCAN_LINE = re.compile(r"^\s*(?:[^\s:]+:)?L\d+ [^:]{1,40}: ")
MARKUP_SUFFIXES = {".html", ".htm", ".xhtml", ".svelte", ".jsx", ".tsx"}


def read_target(target: str) -> tuple[str, str, str]:
	"""Return (display name, raw text, lower-cased suffix); `-` reads stdin."""
	if target == "-":
		return "<stdin>", sys.stdin.read(), ".txt"
	path = Path(target)
	return str(path), path.read_text(encoding="utf-8", errors="replace"), path.suffix.lower()


def extract_lines(raw: str, suffix: str, skip_fences: bool = False, skip_quoted: bool = False) -> list[tuple[int, str]]:
	"""Return [(line_number, visible_text)] with blank lines dropped.

	`skip_fences` drops fenced code blocks; `skip_quoted` drops blockquote
	lines and lines shaped like this scanner's own output. Both are gate-mode
	behaviour; report mode reads everything.
	"""
	if suffix in MARKUP_SUFFIXES:
		# Blank out script/style bodies without losing line count.
		def blank(match: re.Match[str]) -> str:
			return "\n" * match.group(0).count("\n")

		raw = SCRIPT_STYLE.sub(blank, raw)
		lines = [TAG.sub(" ", line) for line in raw.split("\n")]
		lines = [html.unescape(line) for line in lines]
	else:
		lines = raw.split("\n")
	out = []
	fenced = False
	for index, line in enumerate(lines, start=1):
		if skip_fences and FENCE.match(line):
			fenced = not fenced
			continue
		if fenced:
			continue
		if skip_quoted and (BLOCKQUOTE.match(line) or SCAN_LINE.match(line)):
			continue
		text = re.sub(r"\s+", " ", line).strip().replace("’", "'")
		if text:
			out.append((index, text))
	return out


# ------------------------------------------------------------------- masking

CODE_SPAN = re.compile(r"(`+)(.+?)\1")
URL = re.compile(r"\bhttps?://\S+|\S+@\S+\.\w+")
IDENT = re.compile(r"\b\w+(?:[-_./:\\]\w+)+\b")
QUOTED = re.compile(r'"[^"]*"|“[^”]*”')
OPEN_QUOTE = re.compile(r'["“]')


def mask_code(text: str) -> str:
	"""Blank code-ish and quoted spans with same-length spaces so match offsets stay valid.

	Quoted spans are masked last and only within the line; a quote left
	unbalanced masks from itself to the end of the line, never further.
	"""
	for pattern in (CODE_SPAN, URL, IDENT, QUOTED):
		text = pattern.sub(lambda match: " " * len(match.group(0)), text)
	stray = OPEN_QUOTE.search(text)
	if stray:
		text = text[: stray.start()] + " " * (len(text) - stray.start())
	return text


# ------------------------------------------------------------------ patterns

IZE_STOPS = {
	"size", "sizes", "sized", "sizing", "resize", "resized", "resizes",
	"prize", "prizes", "prized", "seize", "seizes", "seized", "seizing",
	"capsize", "capsized", "capsizes", "capsizing", "maize", "downsize",
	"oversize", "midsize", "assize",
}

HOUSE_RULES = [
	("em dash", r"—"),
	("spaced en dash", r"\s–\s"),
	("Oxford comma", r"\b\w+, (?:[^,.;:!?]|\.(?=\S)){1,40}, (?:and|or)\b"),
	("-ize / -ization", r"\b\w*iz(?:e|es|ed|ing|ation|ations)\b"),
	("American -or", r"\b(?:color|behavior|favor|honor|labor|neighbor|humor|flavor|rumor)s?\b"),
	("American -er", r"\b(?:center|centers|meter|meters|liter|liters|theater)\b"),
	("American usage", r"\b(?:toward|gotten|oftentimes|upcoming|deliverable)\b"),
]

# Labels whose matched token adds nothing to a strict-mode line.
PLAIN_LABELS = {"em dash", "spaced en dash", "Oxford comma"}

COUPLETS = [
	("not just / not only", r"\bnot\s+(?:just|only|merely|simply)\b"),
	("rather than", r"\brather than\b"),
	("instead of", r"\binstead of\b"),
	("it's not X, it's Y", r"\b(?:it'?s|this is|that'?s) not\b[^.;!?]{0,90}\b(?:it'?s|that'?s|this is)\b"),
	("isn't X, it's Y", r"\b(?:isn'?t|wasn'?t|aren'?t)\b[^.;!?]{0,90}\b(?:it'?s|but|they'?re)\b"),
	("less about / more about", r"\bless about\b[^.;!?]{0,80}\bmore about\b"),
	("not X but Y", r"\bnot\b[^.,;!?]{0,45},?\s+but\b"),
	("X, not Y", r",\s+not\s+\w+(?:\s+\w+){0,3}[.;]"),
]

FIRST_PERSON = [
	("bare I", r"\bI\b"),
	("I'm / I'll / I've / I'd", r"\bI['’](?:m|ll|ve|d)\b"),
	("my / mine", r"\b(?:my|mine)\b"),
	("we / our", r"\b(?:we|our|ours|we['’](?:re|ve|ll))\b"),
]

HEDGES = [
	("directionally / indicative", r"\b(?:directionally|indicative(?: rather than)?)\b"),
	("something resembling", r"\bsomething (?:resembling|like)\b"),
	("roughly / approximately", r"\b(?:roughly|approximately|around|about)\s+\d"),
	("arguably / broadly", r"\b(?:arguably|broadly speaking|by and large|for the most part)\b"),
	("worth noting", r"\b(?:it'?s|it is) worth (?:noting|saying|checking|flagging)\b"),
	("to be fair", r"\bto be fair\b"),
	("in practice", r"\bin practice\b"),
]

INTENSIFIERS = [
	("precisely / exactly", r"\b(?:precisely|exactly)\b"),
	("simply / actually", r"\b(?:simply|actually)\b"),
	("genuinely / truly", r"\b(?:genuinely|truly|really)\b"),
	("crucially / importantly", r"\b(?:crucially|importantly|notably|critically)\b"),
	("fundamentally / essentially", r"\b(?:fundamentally|essentially|ultimately|inherently)\b"),
]

LLM_LEXICON = [
	("delve / tapestry / realm", r"\b(?:delve[sd]?|tapestry|realm|landscape of|navigate the)\b"),
	("at its core / key insight", r"\b(?:at its core|the key (?:insight|takeaway)|in essence)\b"),
	("important to note", r"\b(?:important to note|it should be noted|that said)\b"),
	("robust / seamless / leverage", r"\b(?:robust|seamless(?:ly)?|leverag(?:e|es|ed|ing))\b"),
	("underscores / testament", r"\b(?:underscore[sd]?|a testament to|speaks volumes)\b"),
	("dive in / unpack", r"\b(?:let'?s (?:dive|unpack)|deep dive into|unpack(?:s|ing)? (?:the|this|why))\b"),
	("game-changer / powerful", r"\b(?:game[- ]chang(?:er|ing)|incredibly powerful|truly transformative)\b"),
]

# Imported from blader/humanizer's pattern list, 2026-09-10: constructions
# that borrow weight the sentence has not earned.
BORROWED_WEIGHT = [
	("participial tail", r",\s+(?:highlighting|emphasi[sz]ing|underscoring|reflecting|showcasing|demonstrating|signal(?:l)?ing|cementing|ensuring)\b"),
	("borrowed authority", r"\b(?:experts|studies|research|analysts|critics|observers|many|some)\s+(?:say|agree|suggest|show|argue|believe|note)\b|\b(?:widely|generally)\s+(?:regarded|considered|seen)\b"),
	("significance inflation", r"\b(?:pivotal|landmark|watershed|cornerstone|turning point|paved the way|far-reaching|profound(?:ly)?)\b"),
	("copula avoidance", r"\b(?:serves as|acts as|functions as|stands as)\b"),
	("chatbot residue", r"\b(?:I hope this helps|let me know if|feel free to|happy to help|great question|certainly!|absolutely!)"),
	("curly quotes", r"[“”‘]"),
]

TRIADS = [
	("literal 'three'", r"\bthree\b"),
	("comma triad", r"\b\w+, \w+(?:\s\w+)? and \w+\b"),
]

GROUPS = [
	("House-rule breaches", HOUSE_RULES),
	("Contrastive couplets and rhetorical defaults", COUPLETS),
	("First person and self-narration", FIRST_PERSON),
	("Hedge boilerplate", HEDGES),
	("Emphasis intensifiers", INTENSIFIERS),
	("LLM lexicon", LLM_LEXICON),
	("Borrowed weight", BORROWED_WEIGHT),
	("Rule of three", TRIADS),
]

NUMBER_WORDS = {
	"one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
	"ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
	"seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty",
	"sixty", "seventy", "eighty", "ninety", "hundred", "thousand",
}

WORD_QUANT = re.compile(
	r"\b(" + "|".join(sorted(NUMBER_WORDS, key=len, reverse=True)) + r")\s+([a-z]{3,})\b",
	re.I,
)
DIGIT_QUANT = re.compile(r"\b(\d[\d,]*)\s+([a-z]{3,})\b", re.I)

STOP_SHINGLE = re.compile(r"[^a-z0-9 ]+")


# ------------------------------------------------------------------- scanning


def scan_group(lines, patterns, top, mask=False):
	"""Match each pattern over the lines; `top=None` keeps every hit.

	With `mask`, matching runs against a code-masked copy of each line while
	excerpts still slice the original, so offsets and context stay honest.
	"""
	results = []
	for label, pattern in patterns:
		regex = re.compile(pattern, re.I if label != "bare I" else 0)
		hits = []
		for number, text in lines:
			haystack = mask_code(text) if mask else text
			for match in regex.finditer(haystack):
				token = match.group(0)
				if label == "-ize / -ization" and token.lower() in IZE_STOPS:
					continue
				start = max(0, match.start() - 42)
				end = min(len(text), match.end() + 42)
				hits.append((number, token, text[start:end].strip()))
		if hits:
			results.append((label, hits[:top], len(hits)))
	return results


def scan_numerals(lines):
	"""Nouns quantified as both a digit and a word: house-style inconsistency."""
	forms = defaultdict(lambda: {"digit": [], "word": []})
	for number, text in lines:
		for match in DIGIT_QUANT.finditer(text):
			noun = match.group(2).lower().rstrip("s")
			forms[noun]["digit"].append((number, match.group(0)))
		for match in WORD_QUANT.finditer(text):
			noun = match.group(2).lower().rstrip("s")
			forms[noun]["word"].append((number, match.group(0)))
	clashes = []
	for noun, seen in sorted(forms.items()):
		if seen["digit"] and seen["word"]:
			clashes.append((noun, seen["digit"][:2], seen["word"][:2]))
	return clashes


def scan_repeats(lines, width, top):
	"""Verbatim n-word shingles appearing more than once: rehash detection."""
	tokens = []
	for number, text in lines:
		for word in STOP_SHINGLE.sub(" ", text.lower()).split():
			tokens.append((number, word))
	counts = Counter()
	places = defaultdict(list)
	for index in range(len(tokens) - width + 1):
		shingle = " ".join(word for _, word in tokens[index : index + width])
		counts[shingle] += 1
		places[shingle].append(tokens[index][0])
	repeats = []
	for shingle, count in counts.most_common():
		if count < 2:
			break
		lines_hit = sorted(set(places[shingle]))
		if len(lines_hit) < 2:
			continue  # same sentence wrapping, not a genuine repeat
		# Drop shingles fully contained in a longer one already reported.
		if any(shingle in kept for kept, _, _ in repeats):
			continue
		repeats.append((shingle, count, lines_hit[:6]))
		if len(repeats) >= top:
			break
	return repeats


# -------------------------------------------------------------------- report


def report(name: str, raw: str, suffix: str, top: int, shingle: int, house_only: bool = False) -> None:
	lines = extract_lines(raw, suffix)
	words = sum(len(text.split()) for _, text in lines)
	print(f"\n{'=' * 72}\n{name}\n{len(lines)} non-blank lines, ~{words} words\n{'=' * 72}")

	for title, patterns in GROUPS[:1] if house_only else GROUPS:
		found = scan_group(lines, patterns, top)
		if not found:
			continue
		total = sum(count for _, _, count in found)
		print(f"\n## {title}  ({total})")
		for label, hits, count in found:
			print(f"  {label}: {count}")
			for number, token, context in hits:
				print(f"    L{number}: …{context}…")
			if count > len(hits):
				print(f"    (+{count - len(hits)} more)")

	if house_only:
		print()
		return

	clashes = scan_numerals(lines)
	if clashes:
		print(f"\n## Numeral style clashes  ({len(clashes)})")
		for noun, digits, words_form in clashes:
			shown_d = ", ".join(f"L{n} '{t}'" for n, t in digits)
			shown_w = ", ".join(f"L{n} '{t}'" for n, t in words_form)
			print(f"  {noun}: {shown_d}  vs  {shown_w}")

	repeats = scan_repeats(lines, shingle, top)
	if repeats:
		print(f"\n## Verbatim repetition ({shingle}-word runs, {len(repeats)} shown)")
		for text, count, where in repeats:
			print(f"  ×{count} L{', L'.join(str(n) for n in where)}: “{text}”")

	print()


def strict(name: str, raw: str, suffix: str, prefix: bool) -> int:
	"""House rules only, code masked, every hit on its own line. 1 if any hit."""
	lines = extract_lines(raw, suffix, skip_fences=True, skip_quoted=True)
	found = scan_group(lines, HOUSE_RULES, None, mask=True)
	hits = sorted(
		(number, label, token, context)
		for label, group_hits, _ in found
		for number, token, context in group_hits
	)
	for number, label, token, context in hits:
		rule = label if label in PLAIN_LABELS else f"{label} '{token}'"
		where = f"{name}:L{number}" if prefix else f"L{number}"
		print(f"{where} {rule}: {context}")
	return 1 if hits else 0


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("targets", nargs="+", help="files to scan, or - for stdin")
	parser.add_argument("--top", type=int, default=6, help="examples per pattern (default 6)")
	parser.add_argument("--shingle", type=int, default=8, help="repetition window in words (default 8)")
	parser.add_argument("--house-only", action="store_true", help="report the house-rule group only; skips the numeral and repetition passes")
	parser.add_argument(
		"--strict",
		action="store_true",
		help="gate mode: house rules only, code masked, one hit per line, exit 1 on any hit",
	)
	args = parser.parse_args()

	missing = [target for target in args.targets if target != "-" and not Path(target).is_file()]
	if missing:
		print("not a file: " + ", ".join(missing), file=sys.stderr)
		return 1

	status = 0
	for target in args.targets:
		name, raw, suffix = read_target(target)
		if args.strict:
			status |= strict(name, raw, suffix, prefix=len(args.targets) > 1)
		else:
			report(name, raw, suffix, args.top, args.shingle, args.house_only)
	return status


if __name__ == "__main__":
	raise SystemExit(main())
