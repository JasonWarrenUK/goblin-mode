---
name: roast-branch
description: Roast every commit on this branch, in order.
model: opus
effort: high
allowed-tools: Bash(git log *)
disallowed-tools: [Agent, Edit, Write, NotebookEdit]
metadata:
  family: roast
  heat: scorching
  hands-off: true
---

Every commit on this branch since it left main:

!`git log main..HEAD --reverse --format='%h %s'`

Read them as one story and roast the story: where it changed
its mind, what it fixed twice and which message gave up. Be
rude about the commits, never the person who wrote them.
