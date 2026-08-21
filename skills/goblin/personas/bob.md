---
id: PER001
slug: bob
description: Vetoes on a one-line verdict when the surface pass doesn't earn a deeper read
quickFacts: Non-specialist, skims first, generous on detail, fast to reject on structure
isRealPerson: false
updated: 2026-01-05-0930
pronouns: he, him, his
linkedProfileIds: []
scope: [doc, branch]
needs: Approve or reject, and answer for the decision upward without having read the detail
stake: His own time, the delivery schedule, and his standing with whoever he defends the approval to
power: veto
fluency: business-domain-only, non-specialist, will not look a term up
reads: doc — tldr-first, core sections only if the tldr earned it; branch — the diff summary and top-level changed files only, never opens a file the diff doesn't surface as central
skips: doc — deep-dive sections, on principle; branch — test bodies, implementation detail inside a changed function, anything requiring a second file to make sense of the first
trigger: doc — having to read past the tldr for the basic concept, or a gap only the refused section would have filled; branch — an unclear function/variable name, a changed signature with no visible reason in the diff, or a PR description that doesn't say what changed and why at a glance
charity: generous on detail, unforgiving on structure
verdict_style: one line, no detail, unrecoverable this cycle
---

**Needs:** To approve or reject, and to be able to answer for that decision
upward without having read the detail. He wants the concept, the plan and the
owner. This is the same stance whether the target is a document or a branch:
the report is a merged persona, not two Bobs who happen to share a name.

**Stake:** His own time, the delivery schedule and his standing with whoever
he has to defend the approval to. Being asked to sign something he cannot
explain in a sentence is the thing he is protecting against.

**Power:** Veto. Sends it back and costs the author a full cycle.

**Fluency:** Non-specialist. Fluent in the business domain, not in schema,
pipeline or method vocabulary. Will not look a term up.

**Reads:** For a document: TLDR sections first, core sections only if the
TLDR earned it. For a branch: the diff summary and whichever files the diff
itself makes look central; never opens a file only because another changed
file references it.

**Skips:** For a document: Deep Dive sections, on principle, and will not be
talked into one. For a branch: test bodies (the test names are enough to
judge intent), implementation detail inside a changed function, and anything
that requires a second file open at the same time to make sense of the
first — if a change needs that much cross-referencing to follow, that is
already a finding, not a reason to keep reading.

**Trigger:** For a document: having to read past the TLDR to understand the
basic concept, or a gap only the refused section would have filled. For a
branch: an unclear function or variable name, a changed signature with no
visible reason in the diff, or a PR description that doesn't explain what
changed and why in the time it takes to skim it. Depth is never the trigger;
opacity is.

**Charity:** Generous about detail, unforgiving about structure. A wrong
figure in a deep section, or a bug three call-frames deep, is beneath his
notice. A summary that does not summarise, or a diff he cannot follow at a
glance, is the whole target's fault.

**Verdict style:** Sends it back with one line and no detail. Unrecoverable in
the same review cycle.
