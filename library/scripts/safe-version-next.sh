#!/bin/zsh
# safe-version-next.sh: `svu next` with a hard guard on the 0.x -> 1.x boundary.
#
# Prints the tag to create. Identical to `svu next` except when the current
# version is 0.x and svu proposes 1.0.0: crossing into 1.x is a human decision
# (it declares the public API stable), so the script emits a minor bump within
# 0.x instead: semver's own convention for breaking changes pre-1.0. Later
# major bumps (1 -> 2, 2 -> 3, ...) pass through untouched. One exception: a
# renamed plugin whose plugin.json declares 1.0.0 out of a 0.x series has
# made that decision in its rename, and gets 1.0.0 (see --plugin below).
#
# usage: safe-version-next.sh [--plugin NAME --dir PATH]
#   no flags        root repo: tag prefix "v", history from the whole repo
#   --plugin --dir  scope to one plugin subtree: tag prefix "NAME-v",
#                    history and svu's commit scan both limited to PATH, so a
#                    plugin only bumps on commits that actually touched it;
#                    a plugin with no tags under NAME-v that the
#                    marketplace's renames map gives an earlier name
#                    continues that name's series, and declaring 1.0.0 in
#                    its plugin.json takes it across the 0.x guard
# exit codes: 0 ok (tag on stdout; guard note on stderr when it fired),
#             2 environment error; also a matching tag that is not a version
#               (another plugin's, or one svu cannot read), a plugin.json
#               version of digits and dots that is not major.minor.patch, and
#               tagged earlier names on separate paths of the renames map (a
#               person picks),
#             3 nothing to release (no version-bumping commits since the
#               current tag: creating a tag would fail on a duplicate),
#             4 omitted by policy (the target is in omit-gh-tag in the
#               repository's .claude/versioning.json; see versioning-policy.py)
set -u

plugin=""
dir=""
while (( $# > 0 )); do
	case "$1" in
	--plugin) [[ $# -ge 2 ]] || { print -u2 -- "--plugin needs a value"; exit 2 }
		plugin="$2"; shift 2 ;;
	--dir) [[ $# -ge 2 ]] || { print -u2 -- "--dir needs a value"; exit 2 }
		dir="$2"; shift 2 ;;
	*) print -u2 -- "unknown argument: $1"; exit 2 ;;
	esac
done
if [[ -n "$plugin" && -z "$dir" ]] || [[ -z "$plugin" && -n "$dir" ]]; then
	print -u2 -- "--plugin and --dir must be given together"
	exit 2
fi

command -v svu >/dev/null 2>&1 || { print -u2 -- "svu not installed"; exit 2 }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { print -u2 -- "not inside a git repository"; exit 2 }

# The repository's policy can take a target out of tagging altogether (a root
# with no installable thing attached, say). The check runs before svu so an
# omitted target never has a version computed for it; check exits 0 when the
# target is omitted, 1 when it is not and 2 on an error, which reads as not
# omitted so a broken policy file never silently stops a release; the reader's
# own line on stderr says why, so the fail-open is never an unreported one.
target="${plugin:-root}"
policy="${0:A:h}/versioning-policy.py"
if [[ -f "$policy" ]] && python3 "$policy" check tag "$target" >/dev/null; then
	print -u2 -- "omitted by policy: $target is in omit-gh-tag (.claude/versioning.json), so no tag is computed for it"
	exit 4
fi

# The current tag under one prefix (svu's own arguments follow it), or
# <prefix>0.0.0 when no tag matches. Any other svu failure (a tag it cannot
# read as a version, say) is named on stderr and returns 1, so the caller exits
# 2 instead of reading a broken series as an untagged one. A glob cannot tell
# a version from another plugin's tag (api-v[0-9]* matches api-v2-v0.1.0,
# which svu reads as 2.0.0), so every tag the pattern matches must read as
# <prefix><major>.<minor>.<patch>, with only a pre-release or build after it.
series_current() {
	local tag_prefix="$1" err_file out code err pattern tag
	local -a bad
	shift
	local -a given=("$@")
	pattern="${given[${given[(i)--tag.pattern]}+1]:-}"
	if [[ -n "$pattern" ]]; then
		for tag in ${(f)"$(git tag -l "$pattern")"}; do
			[[ "${tag#$tag_prefix}" =~ '^[0-9]+\.[0-9]+\.[0-9]+([-+].*)?$' ]] || bad+=("$tag")
		done
		if (( ${#bad} )); then
			print -u2 -- "tags matching ${pattern} that do not read as ${tag_prefix} versions (another plugin's, or a malformed one of its own): ${(j:, :)bad}; rename a plugin whose name has a digit after the -v, or retag a malformed one, then run this again"
			return 1
		fi
	fi
	err_file=$(mktemp) || return 1
	out=$(svu current "$@" 2>"$err_file")
	code=$?
	err=$(tr -s '[:space:]' ' ' <"$err_file")
	rm -f "$err_file"
	if (( code == 0 )); then
		print -r -- "$out"
		return 0
	fi
	if [[ "$err" == *"no tags match"* ]]; then
		print -r -- "${tag_prefix}0.0.0"
		return 0
	fi
	print -u2 -- "svu current failed for ${tag_prefix}:${err}"
	return 1
}

# svu current has no --log.directory (it only needs the latest matching tag,
# not a commit scan); svu next needs it to limit which commits count towards
# a bump. Passing --log.directory to `current` fails with "Unknown flag" and
# would otherwise read as an untagged series below, so the two commands get
# their own argument lists rather than one shared array. Each pattern ends in
# a digit after the "-v", so a plugin named "<name>-v<letters>" (roadmap and
# roadmap-viewer) never lands in another's series.
current_args=()
next_args=()
prefix="v"
if [[ -n "$plugin" ]]; then
	[[ -d "$dir" ]] || { print -u2 -- "$dir: not a directory"; exit 2 }
	prefix="${plugin}-v"
	current_args=(--tag.prefix "$prefix" --tag.pattern "${prefix}[0-9]*")
	next_args=("${current_args[@]}" --log.directory "$dir")
fi

current=$(series_current "$prefix" "${current_args[@]}") || exit 2

# What the plugin's built plugin.json declares at its top level, if anything:
# the start of a fresh series, and for a renamed plugin the human's word on
# crossing to 1.x. A nested "version" (a dependency's, say) never counts. Only
# major.minor.patch counts as declared: a run of digits and dots of another
# shape (0.3, 1.0, 0.3.0.) exits 2 naming it, since printed as a tag it is
# one the tag-shape check refuses at the next release. Anything else (none, a
# pre-release) reads as nothing declared.
declared=""
if [[ -n "$plugin" && -f "$dir/.claude-plugin/plugin.json" ]]; then
	declared=$(python3 -I -c '
import json, re, sys
version = json.load(open(sys.argv[1])).get("version")
if isinstance(version, str) and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
	print(version)
elif isinstance(version, str) and re.fullmatch(r"[0-9.]+", version):
	print("malformed:" + version)
' "$dir/.claude-plugin/plugin.json" 2>/dev/null)
	if [[ "$declared" == malformed:* ]]; then
		print -u2 -- "$dir/.claude-plugin/plugin.json declares version \"${declared#malformed:}\", which is not major.minor.patch; set it to three numbers and run this again"
		exit 2
	fi
fi

# A renamed plugin continues its old series. When nothing is tagged under the
# new prefix, the marketplace's renames map is walked back from this name,
# nearest earlier names first (several at once where names folded into one,
# which is reported). Every path back through the map is followed to its own
# nearest tagged name, and a name behind a tagged one is not walked; the
# version is then computed under that prefix and printed under the new one.
# More than one tagged name on separate paths exits 2 naming them all: which
# series goes on is a person's call, never the map's order or how far back a
# name sits. The commit scan
# covers the new directory and every walked-back name's directory, so a
# change made before the move still counts: each directory is that name's
# source in the marketplace as tagged, else a sibling of the new directory.
# A map that cannot be read says why on stderr, as the policy reader does, so
# falling back to a fresh series is never a silent one.
renamed_from=""
walked=()
if [[ -n "$plugin" && "$current" == "${prefix}0.0.0" ]]; then
	marketplace="$(git rev-parse --show-toplevel)/.claude-plugin/marketplace.json"
	if [[ -f "$marketplace" ]]; then
		earlier=("${(@f)$(python3 -I -c '
import json, sys
try:
	manifest = json.load(open(sys.argv[1]))
except (OSError, ValueError) as error:
	sys.exit(f"renames: cannot read {sys.argv[1]} ({error}); treating {sys.argv[2]} as unrenamed")
renames = manifest.get("renames") if isinstance(manifest, dict) else None
if renames is None:
	sys.exit(0)
if not isinstance(renames, dict):
	sys.exit(f"renames: the map in {sys.argv[1]} is not an object; treating {sys.argv[2]} as unrenamed")
queue, seen = [sys.argv[2]], {sys.argv[2]}
while queue:
	name = queue.pop(0)
	before = [old for old, new in renames.items() if new == name and old not in seen]
	if len(before) > 1:
		names = ", ".join(before)
		print(f"renames: {name} has several earlier names ({names}); trying each", file=sys.stderr)
	for old in before:
		seen.add(old)
		queue.append(old)
		print(f"{name}\t{old}")
' "$marketplace" "$plugin")}")
		typeset -A behind
		tagged=()
		for line in "${earlier[@]}"; do
			[[ -n "$line" ]] || continue
			parent="${line%%$'\t'*}"
			old="${line#*$'\t'}"
			# a name behind a tagged one is not walked: that path already has its nearest tag
			if [[ -n "${behind[$parent]:-}" ]]; then
				behind[$old]=1
				continue
			fi
			walked+=("$old")
			found=$(series_current "${old}-v" --tag.prefix "${old}-v" --tag.pattern "${old}-v[0-9]*") || exit 2
			[[ "$found" == "${old}-v0.0.0" ]] && continue
			behind[$old]=1
			tagged+=("$found")
			renamed_from="$old"
			old_current="$found"
		done
		if (( ${#tagged} > 1 )); then
			print -u2 -- "renames: $plugin has several tagged earlier names (${(j:, :)tagged}); a person picks which series goes on: tag ${prefix}<version> by hand from the one chosen, or drop the other from the renames map"
			exit 2
		fi
	fi
fi

if [[ -n "$renamed_from" ]]; then
	old_prefix="${renamed_from}-v"
	tagged_marketplace=$(git show "${old_current}:.claude-plugin/marketplace.json" 2>/dev/null)
	log_dirs=(--log.directory "$dir")
	for old in "${walked[@]}"; do
		source=$(print -r -- "$tagged_marketplace" | python3 -I -c '
import json, sys
try:
	for entry in json.load(sys.stdin).get("plugins") or []:
		if entry.get("name") == sys.argv[1] and isinstance(entry.get("source"), str):
			print(entry["source"].removeprefix("./"))
			break
except (ValueError, AttributeError):
	pass
' "$old" 2>/dev/null)
		# a tagged source is relative to the repository's top level, wherever this runs from;
		# the sibling guess is beside --dir, resolved first so that --dir . from inside the plugin works
		log_dirs+=(--log.directory "${source:+$(git rev-parse --show-toplevel)/}${source:-${dir:A:h}/$old}")
	done
	old_next=$(svu next --tag.prefix "$old_prefix" --tag.pattern "${old_prefix}[0-9]*" "${log_dirs[@]}") || { print -u2 -- "svu next failed"; exit 2 }
	current="${prefix}${old_current#$old_prefix}"
	next="${prefix}${old_next#$old_prefix}"
	print -u2 -- "renamed: continuing ${renamed_from}'s series from ${old_current}"
elif [[ -n "$plugin" && "$current" == "${prefix}0.0.0" ]]; then
	# Plugin-only: svu current tolerates zero matching tags (falls back
	# above); svu next does not, it hard-errors "no tags match" instead of
	# treating an empty series as a first release. A fresh series starts at
	# whatever the plugin's already-built plugin.json declares (so a plugin
	# authored at 0.3.0 before its first tag doesn't get written back down
	# to 0.1.0), or 0.1.0 when no built plugin.json exists yet either.
	# Root mode never hits this: an untagged repo's bare "v" pattern still
	# matches everything, so svu next works unaided and a docs-only history
	# correctly falls through to the "nothing to release" exit below.
	next="${prefix}${declared:-0.1.0}"
else
	next=$(svu next "${next_args[@]}") || { print -u2 -- "svu next failed"; exit 2 }
fi

# Print the tag. A renamed plugin whose plugin.json declares neither the
# current version nor the one printed has a hand-set number the commits did
# not earn (a 3.0.0 with no breaking commit, say): said on stderr, before
# pr-land writes the printed version over it.
emit() {
	local version="${1#$prefix}"
	if [[ -n "$renamed_from" && -n "$declared" && "$declared" != "$version" && "$declared" != "${current#$prefix}" ]]; then
		print -u2 -- "renamed: plugin.json declares $declared, but the series gives $version; settle which is right before the manifest is rewritten"
	fi
	print -r -- "$1"
}

cur_major=${${current#$prefix}%%.*}
next_major=${${next#$prefix}%%.*}

# A rename that declares 1.0.0 out of a 0.x series is the human decision the
# guard waits for, and the rename alone is the release, whatever its commit
# type: so it is answered before the nothing-to-release exit.
if [[ -n "$renamed_from" && "$cur_major" == "0" && "$declared" == "1.0.0" ]]; then
	print -r -- "${prefix}1.0.0"
	exit 0
fi

if [[ "$next" == "$current" ]]; then
	since="$current"
	[[ -n "$renamed_from" ]] && since="$old_current"
	print -u2 -- "nothing to release: no version-bumping commits since $since"
	exit 3
fi

if [[ "$cur_major" == "0" && "$next_major" != "0" ]]; then
	minor=${${${current#$prefix}#*.}%%.*}
	print -u2 -- "guard: svu proposed $next, but the first 1.x tag is a human decision: emitting a 0.x minor bump instead. Tag ${prefix}1.0.0 manually when the API is ready to be called stable."
	emit "${prefix}0.$((minor + 1)).0"
else
	emit "$next"
fi
