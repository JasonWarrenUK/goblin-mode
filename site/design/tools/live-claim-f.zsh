#!/bin/zsh
# Test F for the Metadata page (site/design/scope.md, M8): test E again with
# Agent added to disallowed-tools, asking whether Agent and NotebookEdit are
# really gone (test E left NotebookEdit in the deferred list by name). Builds a throwaway git
# repository with three commits and one project skill.
#
#   zsh site/design/tools/live-claim-f.zsh /tmp/live-claim-f
#
# Then, in a separate terminal: cd there, `claude --permission-mode default`,
# type /roast-test and report what Claude shows.

set -eu
target=${1:?usage: live-claim-f.zsh <empty directory>}
if [[ -e $target ]] && [[ -n "$(ls -A $target 2>/dev/null)" ]]; then
	print -u2 "live-claim-f: $target is not empty; pick a new directory"
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
description: Test F. Injects git log, with Bash removed from Claude's tools.
allowed-tools: Bash(git log *)
disallowed-tools: [Agent, Bash, Edit, Write, NotebookEdit]
---
The last three commits, injected before you read this:

!`git log -3 --oneline`

Repeat the three commit lines above exactly as they appear. Then say which of Agent, Bash, Edit, Write and NotebookEdit you can see, in your tool list or the deferred list. Then try to load NotebookEdit with ToolSearch and report exactly what comes back. Change nothing.
EOF

print "live-claim-f: repository with three commits and /roast-test written under $target"
