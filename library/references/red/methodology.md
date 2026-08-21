# Red Methodology

The shared core both red skills execute: `red-doc` (adversarial review of a document, aimed at one or two named readers) and `red-branch` (adversarial review of a branch diff, same reader-first structure aimed at code). Each skill's own file carries only what differs; everything below applies to both. Personas live one-per-file in [../../profiles/personas/](../../profiles/personas/), read and filtered via `library/scripts/red-personas.py`; the file contract, field-purpose table and document/branch compatibility note live in [../../profiles/personas/README.md](../../profiles/personas/README.md).

## Contents

- The stance
- Persona resolution (Step 1 and its sub-steps)
- The nine-field schema
- The persona-pass field ordering
- The report skeleton
- Discipline rules
- Refine, then save

## The stance

You are reviewing a colleague's work. You want it dead. The output is a
dossier: evidence, location and why it is fatal to the specific person who
will see it. Nothing else.

This is a critique aimed at improving the target before real reviewers see it.
It is not an attack on the author.

## Persona resolution

### Step 1: Parse `$ARGUMENTS`

Positional. Nothing here is prompted for interactively unless the target
itself is missing (target parsing is each skill's own job; this step covers
the persona positionals that follow it).

```xml
<arguments>
    <positional name="personas" required="false">
        One or two reviewer personas. A bare slug is resolved in this order:

        1. **An invented persona's own name** (`bob`, `cedric`): found by
           `red-personas.py get {slug}` directly. If found but out of scope
           (its `scope` list doesn't include this skill's tag), say so — a
           doc-only persona named in a branch run is a real situation to
           surface, not silently substitute.
        2. **A real person's name**, checked against
           `~/.claude/library/profiles/dossier/{name}.md`. If that file exists
           and its `linkedProfileIds` names a persona,
           `red-personas.py get {invented name}` loads the derived persona
           directly (an invented name, per the privacy convention in
           [../../profiles/personas/README.md](../../profiles/personas/README.md);
           the real name is never a filename or slug in this tracked
           directory). Before using it, compare the dossier's live `updated`
           against the timestamp recorded in that `linkedProfileIds` entry: if
           the dossier is newer, the derivation is stale — offer a refresh
           (re-run Step 1c against the current entry, overwriting the existing
           file) rather than silently reviewing on an out-of-date model. A
           "no" keeps the existing persona for this run.
        3. **A real person's name, no persona linked yet**: go to Step 1c
           and derive a review profile from their entry for the first time.
        4. **A bare slug matching neither** an existing persona nor a dossier
           file: go to Step 1a and define it.

        A fifth form, independent of the above: an inline definition, `"Name:
        what they read, what they skip, what sets them off"` — a short
        capitalised name, a colon, then a brief. Infer all nine persona
        fields from the brief and print the inferred ones before the report
        so they can be corrected; do not interrogate the user for the missing
        fields. This is the throwaway path, so it buys speed with guesses.

        Zero personas: go to Step 1b and show the roster.
        Three or more: ask which two, then stop until answered. Two is the cap
        because the report's value is the contrast between readers.
    </positional>
</arguments>
```

`personas` (as the whole invocation, no other arguments) prints the roster
from the personas file and stops.

### Step 1a: A named persona that does not exist yet

Fires when a bare slug matches no existing persona and no dossier file, per
Step 1's resolution order (form 4). By this point the dossier has already
been ruled out, so this step never re-checks it. Do not guess the persona, do
not substitute a default, do not start the report.

1. **Check for a typo first.** Run `red-personas.py find-typo {slug} --scope
   {this skill's scope}`; if it surfaces a near miss, ask which was meant. Only
   go on once the user confirms this reader is genuinely new.
2. **Interview.** Nine fields, all required, in three `AskUserQuestion` rounds
   of three. Motive first, because motive decides what the later answers are
   worth.

   **Round 1, motive and reach:**

   | Field | The question | Options to offer |
   |---|---|---|
   | Needs | What decision did they open this to make? | Approve or reject it; check the reasoning holds; find out what it means for their own work; nothing, they were sent it |
   | Stake | What are they protecting? | A prior decision of theirs; their team's scope or budget; the schedule; their own time; the integrity of the record |
   | Power | What can they actually do to it? | Veto it outright; block by attrition until answered; delay it a cycle; complain, and be overruled |

   **Round 2, how they read:**

   | Field | The question | Options to offer |
   |---|---|---|
   | Fluency | How much of the domain vocabulary do they carry? | Fully fluent; fluent in the business domain only; lay reader; fluent but will not look anything up |
   | Reads | What do they actually read, and in what order? | Summaries first; the detail sections; front to back; whatever a search turns up |
   | Skips | What will they not open, and is that principle or habit? | Long-form detail on principle; summaries as marketing; appendices and tables; nothing, they read it all |

   **Round 3, how they judge:**

   | Field | The question | Options to offer |
   |---|---|---|
   | Trigger | What makes them reject a target outright? | Cost or effort not stated; unverified claims; repetition and padding; anything touching their own area |
   | Charity | How much benefit of the doubt do they extend? | None, a typo counts; generous on detail, unforgiving on structure; the reverse; charitable until the second error |
   | Verdict style | What does their rejection look like? | One line, no detail; a numbered dossier; silence and no reply; a meeting nobody wanted |

   Every option list ends where the user's own answer takes over, so keep them
   as prompts rather than a menu to be picked from. A persona is worth nothing
   if it makes the same evidence lethal as the other one, so if the answers
   land close to an existing persona, say so and ask what separates them; the
   most useful pairs disagree on Power, Charity or Fluency, beyond disagreeing
   on Reads.
3. **Show the drafted persona back**, both levels: the full nine-field prose
   (as always) and, once that's confirmed, a one-line summary per field for
   frontmatter — write both from the same draft, since the prose has to exist
   before it can be compressed. Get a yes on the whole thing, prose and
   summaries together.
4. **Write it** to `~/.claude/library/profiles/personas/{slug}.md`
   (an invented persona's `slug` is its name, same as `bob`/`cedric` — Step 1c's
   personas derived from a real dossier entry also get an invented name, never
   the person's own): a `---`-delimited frontmatter block (`slug`, `description`,
   `quickFacts`, `isRealPerson: false`, `updated`, `pronouns`,
   `linkedProfileIds: []`, `scope` — default to the calling skill's own scope
   tag unless the drafted fields read as scope-agnostic, then the nine summary
   fields) followed by the full prose body, per the contract in
   [../../profiles/personas/README.md](../../profiles/personas/README.md). This
   happens before the report starts, so the persona exists in the store even if
   the run is abandoned halfway.

Then continue with the new persona alongside any others named.

### Step 1b: No persona named

Do not fall back to the suggested pair silently. Run `red-personas.py roster
--scope {this skill's scope}` and print its output: each slug with its Needs,
Power and Trigger summaries, with the suggested pair marked. Anyone in
`~/.claude/library/profiles/dossier/` who has no persona yet is listed after them,
under "real people", since rehearsing against an actual reviewer beats
rehearsing against a stand-in — the script only knows about persona files, so
this part stays your own read of the dossier directory. Then ask which one or
two to use, offering those entries plus "define a new one", which routes to
Step 1a. Multi-select, capped at two. Stop until answered.

### Step 1c: A real person from the dossier

Fires per Step 1's resolution order (form 3): the slug names a file in
`~/.claude/library/profiles/dossier/` whose `linkedProfileIds` names no
persona yet — a first derivation — or Step 1's staleness check offered a
refresh and the user took it. This is the case the personas system exists
for: rehearsing a target against the people who will actually see it, with
Bob and Cedric as the stand-ins they always were.

**The privacy boundary this step must not cross.** `library/profiles/dossier/`
is gitignored on purpose, and `dossier-record`'s own rule is explicit: dossier
content never enters a tracked file, and a person named there is never named
in anything published. The persona store (`library/profiles/personas/`)
is **tracked**, and Step 5's refine-then-save writes reports out of it that
can end up read by other people. A persona derived from a real dossier entry
must therefore carry an **invented name**, never the real one — the
substitution is the anonymisation — and its fields must be a
**generalisation**, not a paraphrase: strip the specific facts (a repo path, a
named project, a direct quote of what someone said they reject) down to the
*behavioural pattern* those facts imply, the same distance a
scope-generalised field already keeps (compare how `cedric`'s `stake` field
names "the codebase's own claims about itself" rather than `fac-cra` by
name). If a field can't be generalised without losing everything that made it
worth deriving, leave it for the interview instead of writing the specific
version.

Read the person's file, then split the nine fields by what it can honestly
support.

| Usually derivable | Rarely in a dossier |
|---|---|
| **Fluency**, from recorded expertise and its limits | **Power**, unless the file records what they can block |
| **Stake**, from role, ownership and what they are responsible for | **Reads** and **Skips**, which are reading habits nobody writes down |
| **Needs**, from their relationship to this kind of work | **Charity** and **Verdict style**, which only show up under pressure |
| **Trigger**, when the file records what they reject or insist on | |

Then:

1. **Print what was derived**, field by field, each marked with the dossier line
   it came from, so the user can correct a bad generalisation in one word. The
   print can be as specific as the dossier line itself: this is a conversation,
   not a write. The generalisation happens at step 4, before anything is saved.
2. **Interview the gaps only**, in a single `AskUserQuestion` round of up to
   four. Nine questions for someone the config already knows is an insult to
   the dossier.
3. **Invent a name**, or reuse the existing one on a refresh (check the
   dossier entry's `linkedProfileIds` for an existing link to this slug — see
   Step 1's staleness check). A short capitalised name, obviously fictional,
   distinct from any existing persona or dossier slug.
4. **Write the review profile** to `personas/{invented-name}.md` — the
   invented name, never the person's own, as both filename and `slug` — with
   both levels (frontmatter summaries and full prose), generalised per the
   privacy boundary above: never the dossier's own wording verbatim, never a
   project name, a file path, or a quote attributable to one person.
   Frontmatter's `linkedProfileIds` carries
   `["{dossier slug}", false, "{dossier entry's current updated}",
   "{generalised linkDescription}"]` — `isSource: false` because the dossier
   entry is the origin — so a later dossier edit is detectable as drift next
   time this slug resolves. On a refresh, this overwrites the existing file at
   the same invented name; the name never changes.
5. **Write the same link back on the dossier side**, in that entry's
   `linkedProfileIds`, with `isSource: true` and a `linkDescription` that can
   be as specific as the dossier itself already is — that file never leaves
   the machine. This is the one write this step makes into the person's own
   file: the link exists, but no field of the persona (`needs`, `stake`, and
   so on) is ever copied there. How someone reviews a target is inference
   about them; their dossier holds facts they said or that Jason stated. The
   review profile is labelled as a model, lives in the persona store, and
   stays correctable there.

Say once, in the report's provenance line, that this persona was derived from
a real person's dossier entry. A report that reads as a prediction about a
colleague should announce itself as one — but the announcement names the
persona, never the person, in anything the report itself might reach. The
provenance line never prints the dossier slug next to the persona's invented
name in the same breath; the whole point of the invented name is that the two
never sit together outside the gitignored dossier file.

## The nine-field schema

Needs, Stake, Power, Fluency, Reads, Skips, Trigger, Charity, Verdict style.
Full definitions and the table form live in [../../profiles/personas/README.md](../../profiles/personas/README.md).

## The persona-pass field ordering

Work the fields in this order, because each one narrows what the next is
looking for:

- **Needs** first, before any reading pattern is considered. Whatever they
  opened the target to decide, find the point at which they cannot decide it.
  A reader who came to approve a plan is killed by a target with no owner and
  no dates; the same absence is invisible to a reader who came to check the
  reasoning.
- **Stake** aims the search at content. Read the target for the passage that
  touches what they are protecting: the decision of theirs it overturns, the
  scope it annexes, the schedule it lengthens. That passage gets read hostilely
  no matter how the rest is skimmed, so it is worth finding even when the
  target buries it.
- **Fluency** decides whether undefined terms are findings. A lay reader is
  stopped by the first unglossed term in a section they must understand. For a
  fluent reader, drop the whole vocabulary line of attack and look instead for
  one term used two different ways.
- **Charity** sets the floor. Where charity is high, a typo or a stray figure
  is not worth a numbered item and including it weakens the section. Where
  charity is none, misquotation and arithmetic slips are lethal on their own.
- A persona defined by what they **skip** dies on content they need living
  where they will not go, and on any TLDR that contradicts its own section.
  Ask of every core claim: can this reader act on it without opening the part
  they refuse to open?
- A persona defined by **forensics** dies on arithmetic that does not
  reconcile, quotations that do not match their source, sample sizes that go
  unreconciled, numbering with a gap in it, tables contradicting the sentence
  that introduces them, and constraints that do not do what their caption says.
  Then the begged questions: what the target assumes rather than establishes.
  Then rehash, if that is a stated trigger: sections that restate earlier ones,
  quoted against each other.

Where a persona has sub-triggers worth separating, group the section
(load-bearing failure, then internal contradiction, then unexamined
assumptions, then rehash).

## The report skeleton

Print in full, in this order:

1. **Title**: `{calling skill's dossier title}: {target identifier}`.
2. **Provenance line**: which sources were read, and the note that ✅ marks
   confirmed items.
3. **Kill shot**: the single item to fire first, in two or three sentences,
   with why one instance of it is enough.
4. **Evidence sections** specific to the calling skill (document: AI slop,
   self-indulgence; branch: correctness, security, convention violations,
   reinforcement), each item numbered within its section with a
   section-initial prefix.
5. **A section per persona**: opened by one line naming what that reader came
   for, what they can do about it and what they will not forgive, so the items
   below can be read against the lens that produced them. Then the items,
   prefixed with the persona's initial (`B1`, `C1` …), one line each where one
   line does it.
6. **Named failure conditions**, if the calling skill's argument grammar
   supports them and any were supplied.
7. **Recommended order of fire**: three items, each attacking a different axis,
   with one clause on what each proves. Then the count of what is left in the
   dossier. Rank by **Power**, not by how good the finding is: the item that
   lands with the reader who can veto goes first, even when a sharper item
   exists against the reader who can only block by attrition. Say which reader
   each shot is for.
8. **Real defects**: a short closing note separating the items that are genuine
   bugs from the items that are debating points. The author needs to know which
   is which, and an honest dossier is more useful than a uniformly hostile one.

## Discipline rules

Hold throughout, regardless of target type:

- **Information content only.** Layout, typography and visual design (for
  documents) or formatting/style nits already covered by a linter (for
  branches) are invalid targets, unless the calling skill's failure-conditions
  argument makes them fair game.
- **Quote verbatim, locate precisely.** Section name or heading; line numbers
  where the target is code or Markdown.
- **✅ means you read the source.** Never on an inference.
- **No invention.** If a pass yields little, report little and say the target
  is clean on that axis.
- **The report obeys the house rules it is enforcing.** No em dashes, no
  contrastive couplets, no Oxford commas, British spelling. A slop dossier
  written in slop, or a code-quality dossier with sloppy prose, is a joke at
  its own expense.

## Refine, then save

Print the report and stop. Expect the user to push back, add a persona, demand
a different emphasis or ask for a section reworked; iterate in the conversation.

Save only when the user approves the final version:

```bash
mkdir -p {project_root}/docs/reports/adversarial
```

Write to `{project_root}/docs/reports/adversarial/{target-slug}-red-team.md`,
keeping the printed structure, with a header table naming the target, the
sources, the personas used and the date. Report the path.

If an inline persona was defined this run and it is worth keeping, offer to
write it as a new `~/.claude/library/profiles/personas/{slug}.md`, both
frontmatter summaries and full prose per the contract in
[../../profiles/personas/README.md](../../profiles/personas/README.md), scoped to the calling skill. Only on
a yes.
