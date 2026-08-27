# Research artefact formats

Section schemas for `artefact-research`. Sections are in page order. A field marked **req** is present on every item; the page shows `unverified` where it could not be filled.

## `assess`

One subject. Strands are numbered (I, II, III) and each takes one hue, the way the reference artefact does.

1. **Verdict box**: adopt / spike / skip, one paragraph of reason, then a numbered plan (first action, time estimate, abandon condition).
2. **Strand I · The thing**: what it is in its own terms; integration surface as a table (surface / status / detail, status ∈ verified · none · unverified); constraints (licence, platform, scheduling, rate limits, maturity signals such as release cadence).
3. **Strand II · The terms**: what the relevant tier or licence actually grants, quoted; the gate (who or what is counted); the clocks (trials, expiry, caps); open readings of the terms marked `unverified`.
4. **Strand III · Fit**: one collapsed section per candidate project or group, each headed with a chip (`fits` / `stretch` / `no fit`) and a gloss; body gives the reason, what would make it fail, and a spike plan for every `fits`.
5. Footer ledger.

Chips: `fits` (green), `stretch` (amber), `no fit` (grey), `unverified` (dashed), `verified` (strand hue).

## `compare`

Two to six candidates on criteria stated before any candidate is scored.

1. **Verdict box**: the recommendation, the runner-up and the one condition that would flip them.
2. **Criteria**: a short table of what is being judged and why each criterion matters *to this user*; criteria that came from the user's own constraints are marked as such.
3. **Matrix**: candidates × criteria in a `.scroller` table; each cell a chip (`strong` / `adequate` / `weak` / `unverified`) with a one-clause note. Ties are allowed; forced ranking is not.
4. **Per candidate**: one collapsed section each; what it is, where it wins, where it loses, quoted evidence for the load-bearing cells.
5. **Fit**: as `assess` Strand III, when a project context exists.
6. Footer ledger.

Chips: `strong` (green), `adequate` (amber), `weak` (grey), `unverified` (dashed), `recommended` (accent).

## `list`

A catalogue. Every entry has the same fields; the page is a filterable table plus expandable rows, never a wall of prose cards.

**Fields per entry**: name **req**, one-line what-it-is **req**, source link **req**, maintainer or origin, licence, last activity date, maturity (`active` / `quiet` / `dormant` / `unverified`), tags (2 to 4), a one-sentence note on when you would reach for it.

1. **Shortlist box**: the three to five entries worth opening first, with one clause each. No overall winner.
2. **Filter bar**: by tag and by maturity, plain JS, no library.
3. **Table**: `.scroller`, `tabular-nums`, one row per entry, expandable to show the note and evidence.
4. **Left out**: entries considered and dropped, with the reason (a closed `<details>`). This is what makes the catalogue falsifiable.
5. Footer ledger.

Chips: maturity set above, plus `unverified`.

## `primer`

Teaching, not deciding. Written to the "Explaining Complex Ideas" rules: prerequisites first, one anchor, deltas from it, real trade-offs argued both ways.

1. **Anchor**: the one thing the reader already understands that the subject is a delta from; stated in a box where the verdict would be.
2. **Prerequisites**: what has to be true in the reader's head before section 3 lands; each one a collapsed section, skip-able.
3. **The idea**: built as deltas from the anchor, in order of dependency, no forward references.
4. **Advocate / critic**: two columns (stack on narrow widths); the strongest case for and the strongest case against, each with a quoted source.
5. **Where it breaks**: the analogy's limits and the subject's; marked plainly.
6. **Go further**: three to five sources, each with why it is next.
7. Footer ledger.

Chips: `core` / `optional` on prerequisite sections; `unverified` where a claim rests on one source.

## `brief`

State of a subject at a date. Short: the page should read in five minutes.

1. **Verdict box**: what changed since the last brief (or since the user last looked), in three bullets at most.
2. **Stable**: what has not moved and can be relied on.
3. **Moving**: what is changing, with release or announcement links and dates.
4. **Watch**: two to four things with a date or condition attached ("if X ships before Y").
5. **Ledger** footer, with the brief's own date in the kicker so the next one can diff against it.

Chips: `new` (accent), `changed` (amber), `deprecated` (grey), `unverified`.
