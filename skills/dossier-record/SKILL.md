---
name: "Dossier: Record"
description: "Record a durable fact about a person Jason works with, in their own dossier file"
when_to_use: "Whenever Jason says something durable about a named person he works with: their role, expertise, preferences, what they care about, how they review or respond, how to work with them. Also when he introduces someone new, or asks for something about a person to be noted."
metadata:
  family: dossier
# No model or effort on purpose. This skill fires inline, mid-turn, inside
# whatever the session was already doing; both fields override the session
# absolutely while a skill is active, so setting either would downgrade the
# turn that triggered it.
disable-model-invocation: false # the trigger is a fact landing in conversation, which Claude sees before Jason thinks to record it; step 4 is the gate
user-invocable: true
allowed-tools: ["Read", "Glob", "Grep", "Write", "Edit"]
argument-hint: "[name] [what to record]"
---

# Record a person fact

Files live in `~/.claude/library/dossier/{slug}.md`, one per person, gitignored.
`library/dossier/README.md` holds the schema and is the authority on file shape.

This skill fires in the middle of other work. It must be quiet: one line of
output, no summary, no restating what Jason just said back to him.

## Step 1: Should this fire at all

Fires on a **durable attribute** of a named person Jason works with:

- Role, seniority, ownership: "Izaak leads fac-cra"
- Expertise and its limits: "Jaz is light on YAML but picks things up fast"
- Preferences and standards: "Dan wants PRs smaller"
- What they care about, what they reject, how they review
- How to work with them: pitch, handover, register, what to leave out
- Relationships: "Jaz, Max and I work together"
- Pronouns, when stated

Stays silent on:

- Routing and tasking: "send it to Dan", "ask Jess for the spreadsheet"
- One-off state: "Dan's on leave next week", "Jaz is reviewing it today"
- Passing mentions with no claim attached
- Anything about a person Jason does not work with, unless he asks for it
- Third-party gossip. A claim about someone's character, relayed from someone
  else, is not a working fact.

When it does not fire, do nothing and say nothing. A skill that announces its
own restraint is worse than one that never ran.

## Step 2: Resolve the person

```bash
ls ~/.claude/library/dossier/
```

- **Exact slug match**: open that file.
- **Near miss** (`izak` against `izaak`, a nickname, a surname): ask which
  person is meant before writing. Two files for one person is the failure mode
  that makes the whole directory untrustworthy.
- **No match**: new person, so create the file from the README's schema with
  what is known and an `## Open questions` section listing what is not. A file
  with one fact and three open questions is doing its job; it gives the next
  fact somewhere to land.

## Step 3: Write the fact

Append one bullet to `## Facts`, in Jason's words where he gave them, with
today's date in backticks at the end of the line.

- **Mark inference.** A fact Jason stated stands bare. Anything worked out from
  context takes `*(inferred)*`. This matters most when the file is later used
  to predict how someone behaves.
- **One fact per bullet.** A sentence carrying three claims becomes three
  bullets, each separately correctable.
- **Absolute dates.** "Last week" becomes the date.
- **Pronouns are only ever recorded when stated.** `unstated` stays in the
  frontmatter until Jason says otherwise, and everything written about that
  person uses they/them in the meantime.
- Update `metadata.updated`.

Facts about how to work with someone go under `## Working with them` instead.
An answered open question is deleted from `## Open questions` when its answer
is added to `## Facts`.

## Step 4: The contradiction gate

If the new fact contradicts a line already in the file, **write neither**.
Raise it in one line, quote both versions, ask which holds. The correction is
usually the more interesting fact, and silently overwriting loses the fact that
something changed.

Additive facts need no permission. This gate exists for conflicts alone.

## Step 5: Index it

A new person gets a one-line pointer in the People section of
`~/.claude/projects/-Users-jasonwarren--claude/memory/MEMORY.md`:

```markdown
- **Name**: one-line hook, [dossier](../../../../library/dossier/{slug}.md)
```

Existing people need no index change unless the one-line hook is now wrong.

## Step 6: Report

One line. `Recorded: Jaz is light on advanced skill builds → library/dossier/jaz.md`.
Then carry on with whatever the turn was actually about.

## Rules

- **Local only.** These files are gitignored on purpose. Never copy dossier
  content into a tracked file, a commit message, a PR description, an artefact
  or anything published. A guide written for a person is calibrated against
  their file; it never names them or quotes it.
- **Working notes.** Record what changes how work gets done. Personal detail
  Jason volunteers in passing stays out of the file.
- **Jason can always see it.** Anything in these files should be something he
  would be comfortable reading aloud to the person it describes.
