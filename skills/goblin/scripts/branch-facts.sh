#!/bin/zsh
# branch-facts.sh — deterministic fact-gathering for the git-branch-review
# skill. Emits JSON so the reviewing model judges readiness from exact
# numbers instead of deriving them across half a dozen git calls.
#
# usage: branch-facts.sh [base-branch]   (default main)
# exit codes: 0 ok, 2 repository/usage error
set -u

base=${1:-main}
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { print -u2 "not inside a git repository"; exit 2 }
branch=$(git symbolic-ref --short -q HEAD) || { print -u2 "detached HEAD"; exit 2 }
git rev-parse --verify -q "origin/$base" >/dev/null || { print -u2 "origin/$base not found — fetch first"; exit 2 }

merge_base=$(git merge-base HEAD "origin/$base")
ahead=$(git rev-list --count "origin/$base..HEAD")
behind=$(git rev-list --count "HEAD..origin/$base")

# Conventional-commit compliance over the branch's own commits
subjects=$(git log --format=%s "origin/$base..HEAD")
total_commits=0 compliant=0 wip=0
while IFS= read -r s; do
	[[ -z "$s" ]] && continue
	(( total_commits++ ))
	[[ "$s" =~ '^(feat|fix|docs|refactor|test|chore|enhance|types|perf|styles|layout|deps|config|build|agents|ci|deploy|spike|experiment|hotfix)(\([^)]*\))?!?: ' ]] && (( compliant++ ))
	[[ "${s:l}" == (wip*|fixup!*|squash!*) ]] && (( wip++ ))
done <<< "$subjects"

# Diff shape
diff_stat=$(git diff --shortstat "$merge_base..HEAD")
files_changed=$(git diff --name-only "$merge_base..HEAD" | wc -l | tr -d ' ')
insertions=$(print "$diff_stat" | grep -oE '[0-9]+ insertion' | grep -oE '[0-9]+' || print 0)
deletions=$(print "$diff_stat" | grep -oE '[0-9]+ deletion' | grep -oE '[0-9]+' || print 0)

# Anti-patterns introduced by this branch (added lines only)
added=$(git diff "$merge_base..HEAD" | grep '^+' | grep -v '^+++')
conflict_markers=$(print "$added" | grep -cE '^\+(<{7}|={7}|>{7})' || true)
todos=$(print "$added" | grep -cE 'TODO|FIXME' || true)
console_logs=$(print "$added" | grep -cE 'console\.(log|debug)' || true)

# Test-file presence in the diff
test_files=$(git diff --name-only "$merge_base..HEAD" | grep -cE '\.(test|spec)\.[jt]sx?$|_test\.(go|py)$|test_.*\.py$' || true)

# svu bump level, when svu is installed
if command -v svu >/dev/null 2>&1; then
	current=$(svu current 2>/dev/null || print "")
	next=$(svu next 2>/dev/null || print "")
else
	current="" next=""
fi

# Branch-name convention: <prefix>/<short-description>, lowercase + hyphens
name_ok=false
[[ "$branch" =~ '^(feat|fix|enhance|refactor|types|perf|styles|layout|docs|test|deps|config|build|agents|chore|ci|deploy|spike|experiment|wip|hotfix)/[a-z0-9][a-z0-9-]*$' ]] && name_ok=true

jq -n \
	--arg branch "$branch" --arg base "$base" \
	--argjson ahead "$ahead" --argjson behind "$behind" \
	--argjson totalCommits "$total_commits" --argjson conventionalCommits "$compliant" \
	--argjson wipCommits "$wip" \
	--argjson filesChanged "$files_changed" --argjson insertions "${insertions:-0}" \
	--argjson deletions "${deletions:-0}" \
	--argjson conflictMarkersAdded "${conflict_markers:-0}" \
	--argjson todosAdded "${todos:-0}" --argjson consoleLogsAdded "${console_logs:-0}" \
	--argjson testFilesTouched "${test_files:-0}" \
	--arg svuCurrent "$current" --arg svuNext "$next" \
	--argjson branchNameCompliant "$name_ok" \
	'{branch: $branch, base: $base, ahead: $ahead, behind: $behind,
	  commits: {total: $totalCommits, conventional: $conventionalCommits, wip: $wipCommits},
	  diff: {filesChanged: $filesChanged, insertions: $insertions, deletions: $deletions},
	  antiPatterns: {conflictMarkersAdded: $conflictMarkersAdded, todosAdded: $todosAdded, consoleLogsAdded: $consoleLogsAdded},
	  testFilesTouched: $testFilesTouched,
	  svu: {current: $svuCurrent, next: $svuNext},
	  branchNameCompliant: $branchNameCompliant}'
