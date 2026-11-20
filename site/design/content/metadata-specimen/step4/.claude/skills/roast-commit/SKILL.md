---
name: roast-commit
description: Roast the last commit message.
model: sonnet
effort: low
allowed-tools: Bash(git log *)
disallowed-tools: [Agent, Bash, Edit, Write, NotebookEdit]
metadata:
  family: roast
  heat: mild
  hands-off: true
---

The last commit, fetched before you read this:

!`git log -1 --format='%h %s%n%n%b'`

Roast the message in two sentences: one on what it says, one
on what it leaves out. Be rude about the message, never the
person who wrote it.
