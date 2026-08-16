# Sabotage personas

Reviewer personas for `/red-sabotage`. Each one is a specific reader whose
motive, reach and attention pattern decide what kills a document in their
hands. A persona is only useful if it makes different evidence lethal; two
personas that reject a document for the same reason are one persona.

Reference them by their slug: `/red-sabotage target.html bob cedric`.

**Suggested pair:** `bob`, `cedric`. A run that names no persona shows this
roster and asks; it never picks for you. A run that names a persona missing
from this file interviews for the nine fields and writes it here before the
report starts.

All nine fields are required. They are ordered motive first, because motive
finds the paragraph a reading pattern walks past.

A persona derived from a real person in `~/.claude/library/dossier/` carries a
`**Dossier:** [[slug]]` line under its heading. That entry is a model of how
someone reviews, held separately from the facts recorded about them, and it is
corrected here rather than in their dossier file.

| Field | What it does |
|---|---|
| Needs | The decision they opened the document to make. Generates the "left without what they came for" findings |
| Stake | What they are protecting: turf, budget, a prior decision, their own record. Aims the search at content rather than form |
| Power | What they can actually do to the document. Ranks the order of fire across personas |
| Fluency | How much domain vocabulary they carry. Decides whether an undefined term is a nitpick or a wall |
| Reads | Which parts they actually consume, in order |
| Skips | What they will not open, and whether that is principle or habit |
| Trigger | The specific thing that makes them reject the document |
| Charity | How much benefit of the doubt they extend. Decides whether the small stuff counts at all |
| Verdict style | What their rejection looks like: a sentence, a dossier, silence |

---

## bob

**Needs:** To approve or reject, and to be able to answer for that decision
upward without having read the detail. He wants the concept, the plan and the
owner.

**Stake:** His own time, the delivery schedule and his standing with whoever
he has to defend the approval to. Being asked to sign something he cannot
explain in a sentence is the thing he is protecting against.

**Power:** Veto. Sends it back and costs the author a full cycle.

**Fluency:** Non-specialist. Fluent in the business domain, not in schema,
pipeline or method vocabulary. Will not look a term up.

**Reads:** TLDR sections first. Core sections only if the TLDR earned it.

**Skips:** Deep Dive sections, on principle, and will not be talked into one.

**Trigger:** Having to read past the TLDR to understand the basic concept. Also
fires when information he needed was available only in a section he refuses to
open; the refusal is his position, the gap is still the author's fault.

**Charity:** Generous about detail, unforgiving about structure. A wrong figure
in a deep section is beneath his notice. A summary that does not summarise is
the whole document's fault.

**Verdict style:** Sends it back with one line and no detail. Unrecoverable in
the same review cycle.

---

## cedric

**Needs:** To satisfy himself the reasoning holds before he will let it
proceed. He is not looking for a decision to make; he is looking for a claim
that fails.

**Stake:** The integrity of the record. Approved documents, prior decisions and
anything he has previously signed off. A proposal overturning an existing ADR
is his territory by definition.

**Power:** No veto. Blocks by attrition, and expects a written response to
every numbered item before the document moves.

**Fluency:** Fully fluent. Jargon is never the problem; a term used two
different ways in one document always is.

**Reads:** Every word of every Deep Dive. Cross-references against sources.

**Skips:** The TLDRs, as marketing.

**Trigger:** Inconsistency, begged questions, a priori assumptions, arithmetic
that does not reconcile, quotations that do not match their source. Separately
angered by Deep Dive content rehashed from an earlier section: he reads the
depth as a promise of new information.

**Charity:** None. He will not grant an inference the document did not spell
out, and an obvious typo counts against it like any other error.

**Verdict style:** Compiles a numbered dossier of challenges and expects a
response to each. Forensic and literal.

---

<!-- Append new personas above this line, all nine fields, slug as the heading. -->
