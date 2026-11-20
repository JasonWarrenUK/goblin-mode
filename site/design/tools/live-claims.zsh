#!/bin/zsh
# Builds a throwaway project for the four tutorial claims the docs leave open
# (site/design/pre-pr-checks.md, "Tutorial claims to prove on a live install").
# Nothing here is a plugin and nothing loads from this repository: the skills
# are project skills in the target directory, so a normal install runs them.
#
#   zsh site/design/tools/live-claims.zsh /tmp/live-claims
#
# Then, from that directory, start Claude Code in default permission mode
# (`claude --permission-mode default`) and run the four tests the need lists.

set -eu
target=${1:?usage: live-claims.zsh <empty directory>}
if [[ -e $target ]] && [[ -n "$(ls -A $target 2>/dev/null)" ]]; then
	print -u2 "live-claims: $target is not empty; pick a new directory"
	exit 1
fi
skills=$target/.claude/skills
mkdir -p $skills/{caller-a,callee-a,caller-b,callee-b,gate-c,folder-d}

# A: a skill marked disable-model-invocation: true, loaded by another skill
cat > $skills/caller-a/SKILL.md <<'EOF'
---
name: caller-a
description: Test A caller. Loads callee-a and reports what happened.
---
Load the callee-a skill with the Skill tool. Then report exactly what happened, quoting any error text word for word. Do nothing else.
EOF
cat > $skills/callee-a/SKILL.md <<'EOF'
---
name: callee-a
description: Test A callee, closed to Claude.
disable-model-invocation: true
---
Reply with the single line CALLEE-A RAN and stop.
EOF

# B: a called skill's model, effort and disallowed-tools, after the call returns
cat > $skills/caller-b/SKILL.md <<'EOF'
---
name: caller-b
description: Test B caller. Loads callee-b, then tries to write a file.
---
1. Load the callee-b skill with the Skill tool and follow it.
2. After it finishes, use the Write tool to create after-callee.txt containing the word hello.
3. Report whether the Write tool was available and whether the file was written, quoting any error text word for word.
EOF
cat > $skills/callee-b/SKILL.md <<'EOF'
---
name: callee-b
description: Test B callee. Pins haiku at low effort and removes Write and Edit.
model: haiku
effort: low
disallowed-tools: Write, Edit
---
Reply with the single line CALLEE-B RAN and stop.
EOF

# C: an allowed-tools grant on either side of an AskUserQuestion answer
cat > $skills/gate-c/SKILL.md <<'EOF'
---
name: gate-c
description: Test C. Runs an approved script, asks a question, runs it again.
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/hello.sh)
---
1. Run ${CLAUDE_SKILL_DIR}/hello.sh.
2. Ask me with the AskUserQuestion tool: "Run it again?" with the options Yes and No.
3. If I answer Yes, run ${CLAUDE_SKILL_DIR}/hello.sh again.
EOF
cat > $skills/gate-c/hello.sh <<'EOF'
#!/bin/sh
echo "hello from gate-c at $(date +%H:%M:%S)"
EOF
chmod +x $skills/gate-c/hello.sh

# D: a folder name and a name field that differ
cat > $skills/folder-d/SKILL.md <<'EOF'
---
name: Display D
description: Test D. Its folder is folder-d and its name field is Display D.
---
Reply with the single line FOLDER-D RAN and stop.
EOF

print "live-claims: six skills written under $skills"
