---
name: "Do: Minima"
description: "Achieve the stated outcome with the smallest change that satisfies it"
when_to_use: "When the ask is small and well-understood and you want the smallest change that satisfies it, without the interview/scaffold ceremony of do-stud."
# No model override: the task domain is unbounded, so inherit the session model
effort: medium
metadata:
  family: do
disable-model-invocation: true
argument-hint: "[desired outcome]"
# Reads pre-approved only: the task domain is unbounded, so any broader grant
# would blanket-approve arbitrary work
allowed-tools: ["Read", "Glob", "Grep"]
---

Using the most minimal approach possible, achieve this: $ARGUMENTS
