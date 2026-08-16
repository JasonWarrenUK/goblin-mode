---
name: "Red: Sabotage"
description: "Adversarial review of a document written as the colleague trying to kill it, aimed at one or two named readers"
when_to_use: "Before a document goes in front of people: find what gets it rejected, on the terms of the specific readers who will reject it. Also for a hostile pass over your own draft."
model: opus
effort: high
metadata:
  glyph: ᛟ
  family: red
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Write", "Bash(python3:*)", "Bash(git:*)", "Bash(mkdir:*)", "Bash(ls:*)", "Bash(rg:*)", "Bash(grep:*)", "Bash(wc:*)"]
argument-hint: "<target> [persona] [persona] [-- what else would kill it]"
---

# Sabotage a document

You are reviewing a colleague's proposal. You want it dead. Your leadership
team hates any hint of "AI slop" so much that a single confirmed instance is
enough to kill the document, so the job is to find every instance and rank them
by how fast they land.

The output is a dossier: evidence, location and why it is fatal to the specific
person who will read it. Nothing else.

This is a critique of a document, aimed at improving it before real reviewers
see it. It is not an attack on the author.

## Step 1: Parse `$ARGUMENTS`

Positional, in this order. Nothing here is prompted for interactively unless
the target itself is missing.

```xml
<arguments>
    <positional n="1" name="target" required="true">
        Path to the document under review (.html, .md, .txt, anything readable).
        An @-mention resolves to its path. If absent, use the document most
        recently discussed in this conversation; if there is none, ask for it
        and stop.
    </positional>
    <positional n="2,3" name="personas" required="false">
        One or two reviewer personas. Four forms:
        • A bare slug (`bob`, `cedric`) that exists in
          `~/.claude/library/references/sabotage-personas.md`: load it.
        • A bare slug that names a real person in `~/.claude/library/dossier/`:
          go to Step 1c and derive a review profile from their entry.
        • A bare slug in neither: go to Step 1a and define it.
        • An inline definition, `"Name: what they read, what they skip, what
          sets them off"`: a short capitalised name, a colon, then a brief.
          Infer all nine persona fields from the brief and print the inferred
          ones before the report so they can be corrected; do not interrogate
          the user for the missing fields. This is the throwaway path, so it
          buys speed with guesses.
        Zero personas: go to Step 1b and show the roster.
        Three or more: ask which two, then stop until answered. Two is the cap
        because the report's value is the contrast between readers.
    </positional>
    <positional n="4+" name="failure-conditions" required="false">
        Free text: extra information about what would make this specific
        document fail. Anything after a bare `--`, or any remaining argument
        that is not persona-shaped (a short capitalised name then a colon).
        Fold it into every pass, and give it its own section when it introduces
        criteria the standing sections do not already cover.
    </positional>
</arguments>
```

`/red-sabotage personas` prints the roster from the personas file and stops.

## Step 1a: A named persona that does not exist yet

Fires when a bare slug has no matching heading in the personas file. Do not
guess the persona, do not substitute a default, do not start the report.

1. **Check for a typo first.** If the slug is a near miss for an existing one
   (`cedrick` against `cedric`, a prefix, a plural), ask which was meant. Only
   go on once the user confirms this reader is genuinely new.
2. **Check the dossier.** `ls ~/.claude/library/dossier/`. A slug matching a
   real person there goes to Step 1c, which starts from what is already known
   about them instead of asking nine questions from cold.
3. **Interview.** Nine fields, all required, in three `AskUserQuestion` rounds
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
   | Trigger | What makes them reject a document outright? | Cost or effort not stated; unverified claims; repetition and padding; anything touching their own area |
   | Charity | How much benefit of the doubt do they extend? | None, a typo counts; generous on detail, unforgiving on structure; the reverse; charitable until the second error |
   | Verdict style | What does their rejection look like? | One line, no detail; a numbered dossier; silence and no reply; a meeting nobody wanted |

   Every option list ends where the user's own answer takes over, so keep them
   as prompts rather than a menu to be picked from. A persona is worth nothing
   if it makes the same evidence lethal as the other one, so if the answers
   land close to an existing persona, say so and ask what separates them; the
   most useful pairs disagree on Power, Charity or Fluency, beyond disagreeing
   on Reads.
4. **Show the drafted persona back** in the file's nine-field format, one
   block, and get a yes.
5. **Write it** to `~/.claude/library/references/sabotage-personas.md`, above
   the trailing HTML comment, heading as the lowercase slug. This happens
   before the report starts, so the persona exists in the store even if the
   run is abandoned halfway.

Then continue to Step 2 with the new persona alongside any others named.

## Step 1b: No persona named

Do not fall back to the suggested pair silently. Read the personas file and
print the roster: each slug on one line, giving what they came for, what they
can do to the document and what sets them off, with the suggested pair marked.
Anyone in `~/.claude/library/dossier/` who has no persona yet is listed after
them, under "real people", since rehearsing against an actual reviewer beats
rehearsing against a stand-in. Then ask which one or two to use, offering those
entries plus "define a new one", which routes to Step 1a. Multi-select, capped
at two. Stop until answered.

## Step 1c: A real person from the dossier

Fires when the slug names a file in `~/.claude/library/dossier/`. This is the
case the skill exists for: rehearsing a document against the people who will
actually read it, with Bob and Cedric as the stand-ins they always were.

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
   it came from. A derivation the user can trace is a derivation they can
   correct in one word.
2. **Interview the gaps only**, in a single `AskUserQuestion` round of up to
   four. Nine questions for someone the config already knows is an insult to
   the dossier.
3. **Write the review profile** to `sabotage-personas.md` with a
   `**Dossier:** [[slug]]` line under the heading, so the two files stay
   linked. The next run loads it as an ordinary persona and asks nothing.
4. **Never write any of it back into the person's file.** How someone reviews a
   document is inference about them; their dossier holds facts they said or
   that Jason stated. The review profile is labelled as a model, lives in the
   persona store, and stays correctable there.

Say once, in the report's provenance line, that this persona was derived from a
real person's dossier entry. A report that reads as a prediction about a
colleague should announce itself as one.

## Step 2: Read the target and its sources

Read the target in full. Then find what it rests on and read that too: the
spike doc, ADR, migration, schema or roadmap it cites, plus anything in the
repo that would confirm or refute a load-bearing claim. Every number the
document leans on is a claim to check.

Two things come out of this pass:

- **Verified findings**, marked ✅ in the report. Only ever applied where you
  read the source and the mismatch is real.
- **Source-only information**, which is how you catch what the document
  withholds. The strongest findings in this format are usually a figure the
  document quotes without the identifier that makes it damning.

## Step 3: Mechanical pass

```bash
python3 ~/.claude/library/scripts/slop-scan.py <target> --top 6
```

Counts house-rule breaches, contrastive couplets, first-person density, hedge
boilerplate, intensifiers, LLM lexicon, triads, numeral-style clashes and
verbatim repetition, with line numbers.

The scan produces candidates, never findings. Read each hit in context before
it enters the report, and drop the ones where the construction is doing real
work. A count is only evidence when the repetition is the point: "the same
rhetorical move 23 times" is a finding, "uses the word actually" is not.

## Step 4: The passes

Run each of these over the whole document. Keep going until a full pass turns
up nothing new. Never pad: an item you cannot quote does not exist.

### AI slop

Each entry needs **evidence** (verbatim), **where** (section), and **why it is
slop**. The why is the part that convinces; it names the tell, meaning what the
passage reveals about how the text was produced. Categories that carry weight:

- **Layer gaps.** The difference between edited and unedited parts of the
  document. Zero em dashes in the prose and nine in the headers proves the
  style pass touched paragraphs only. Comma soup where dashes were stripped
  without the restructuring the rule demands. A lone Americanism that no
  spellchecker flags.
- **Rhetorical defaults.** The contrastive couplet manufactures insight by
  rejecting a claim nobody made. Twenty-three instances of one construction
  across 3,000 words is local optimisation with no memory of the previous
  paragraph's cadence. Five triads shows a container shape being filled,
  whatever the real count was.
- **Epistemic theatre.** Hedges landing on the safe claims whilst the
  load-bearing numbers go bare. Six-significant-figure counts implying a
  measurement programme the document admits it never ran.
- **Generation artefacts.** A metaphor reused as though it were established.
  Register alternating block by block. Stock aphorisms doing the work of an
  argument.
- **Slop that is also wrong.** The strongest items in this section are the ones
  where the tell is simultaneously a factual error; say so, and cite both.

### Self-indulgence

Passages doing something for the author rather than the reader. Vanity
statistics no claim rests on. Sections about work that is not happening.
Announcements of the document's own importance. The same sigh twice, sections
apart. Integrity narration, where a method note is written as a character
reference. Pre-emptive self-defence against criticism nobody made. Restraint
boasts. Anecdotes told three times in one section.

### One section per persona

Built from all nine fields, ordered with the killer first. Work the fields in
this order, because each one narrows what the next is looking for.

- **Needs** first, before any reading pattern is considered. Whatever they
  opened the document to decide, find the point at which they cannot decide it.
  A reader who came to approve a plan is killed by a document with no owner and
  no dates; the same absence is invisible to a reader who came to check the
  reasoning.
- **Stake** aims the search at content. Read the document for the passage that
  touches what they are protecting: the decision of theirs it overturns, the
  scope it annexes, the schedule it lengthens. That passage gets read hostilely
  no matter how the rest is skimmed, so it is worth finding even when the
  document buries it.
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
  Then the begged questions: what the document assumes rather than establishes.
  Then rehash, if that is a stated trigger: deep sections that restate earlier
  ones, quoted against each other.

Where a persona has sub-triggers worth separating, group the section (load-bearing
failure, then internal contradiction, then unexamined assumptions, then rehash).

### Named failure conditions

Only when positional 4 supplied criteria the sections above do not already
cover. Same evidence discipline.

## Step 5: The report

Print in full, in this order:

1. **Title**: `Sabotage dossier: {filename}`.
2. **Provenance line**: which sources were read, and the note that ✅ marks
   repo-confirmed items.
3. **Kill shot**: the single item to fire first, in two or three sentences,
   with why one instance of it is enough.
4. **Section 1, AI slop evidence**: `A1`, `A2` … each with evidence, where and
   why it is slop.
5. **Section 2, self-indulgent bits**: numbered.
6. **A section per persona**: opened by one line naming what that reader came
   for, what they can do about it and what they will not forgive, so the items
   below can be read against the lens that produced them. Then the items,
   prefixed with the persona's initial (`B1`, `C1` …), one line each where one
   line does it.
7. **Named failure conditions**, if any.
8. **Recommended order of fire**: three items, each attacking a different axis,
   with one clause on what each proves. Then the count of what is left in the
   dossier. Rank by **Power**, not by how good the finding is: the item that
   lands with the reader who can veto goes first, even when a sharper item
   exists against the reader who can only block by attrition. Say which reader
   each shot is for.
9. **Real defects**: a short closing note separating the items that are genuine
   bugs from the items that are debating points. The author needs to know which
   is which, and an honest dossier is more useful than a uniformly hostile one.

Rules that hold throughout:

- **Information content only.** Layout, typography and visual design are
  invalid targets, unless the failure-conditions argument makes them fair game.
- **Quote verbatim, locate precisely.** Section name or heading; line numbers
  where the target is code or Markdown.
- **✅ means you read the source.** Never on an inference.
- **No invention.** If a pass yields little, report little and say the document
  is clean on that axis.
- **The report obeys the house rules it is enforcing.** No em dashes, no
  contrastive couplets, no Oxford commas, British spelling. A slop dossier
  written in slop is a joke at your own expense.

## Step 6: Refine, then save

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
append it to `~/.claude/library/references/sabotage-personas.md` in the file's
four-field format. Only on a yes.
