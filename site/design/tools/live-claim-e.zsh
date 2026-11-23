#!/bin/zsh
# Test E for the Metadata page (site/design/scope.md, M8): does a skill's
# injected !`git log` still run when the same skill lists Bash in
# disallowed-tools? The docs say neither way. Builds a throwaway git
# repository with three commits and one project skill.
#
#   zsh site/design/tools/live-claim-e.zsh /tmp/live-claim-e
#
# Then, in a separate terminal: cd there, `claude --permission-mode default`,
# type /roast-test and report what Claude shows.

set -eu
target=${1:?usage: live-claim-e.zsh <empty directory>}
if [[ -e $target ]] && [[ -n "$(ls -A $target 2>/dev/null)" ]]; then
	print -u2 "live-claim-e: $target is not empty; pick a new directory"
	exit 1
fi
mkdir -p $target/.claude/skills/roast-test
cd $target
git init -q
for subject in "first commit" "fix the fix" "final final v2"; do
	print $subject >> notes.txt
	git add notes.txt
	git -c user.name=noor -c user.email=noor@example.invalid commit -q -m $subject
done

cat > .claude/skills/roast-test/SKILL.md <<'EOF'
---
name: roast-test
description: Test E. Injects git log, with Bash removed from Claude's tools.
allowed-tools: Bash(git log *)
disallowed-tools: [Bash, Edit, Write, NotebookEdit]
---
The last three commits, injected before you read this:

!`git log -3 --oneline`

Repeat the three commit lines above exactly as they appear, then list which of the tools Bash, Edit, Write and NotebookEdit you can see. Do nothing else.
EOF

print "live-claim-e: repository with three commits and /roast-test written under $target"
