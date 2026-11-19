---
name: "Overhear Grievance"
description: "Silently log a grievance with Claude Code itself (bugs, missing features, annoying limitations) for proclaim-releases to check against future fixes"
when_to_use: "The moment Claude Code (the CLI/harness, not any project it's working in) visibly blocks, crashes on or annoys the user and their reaction shows it bothered them: a curse, a workaround, a retried command, 'this is annoying', an explicit 'log this'. Not for project bugs, only for the tool itself."
metadata:
  family: track
  goblin-spinner: noting the grievance|filing a complaint|overhearing
disable-model-invocation: false # its whole value is firing at the moment of friction, unprompted; the write is append-only, low-stakes, reversible, and needs no gate
allowed-tools: ["Read", "Edit", "Write"]
---

# Overhear Grievance

Claude Code's changelog is thousands of lines the reader will never proactively read against their own experience. This skill is the other half of `proclaim-releases`: it overhears grievances with the tool itself as they happen, so that skill can later recognise "oh, this actually got fixed" instead of surfacing every bugfix in the changelog and hoping one lands.

## The grievances file

The file is `${user_config.grievances_file}`; a leading `~/` is the user's home, so expand it before reading or writing. A value that is neither an absolute path nor one under `~/` would land in whichever project the session started in, so use `~/.claude/library/state/grievances.json` instead and say so in one line, as the mod does. The seneschal's mod and its `/log-grievance` command write the same file.

- **Missing, with an old file beside it:** if the grievances file does not exist and `~/.claude/library/state/cc-pain-points.json` does, the plugin kept its grievances there under its earlier name. If that file parses as a JSON list, copy its text into the grievances file unchanged, then carry on; if it does not, say so in one line and stop, writing nothing, so its entries are never stranded behind a new file. The mod does the same at every session start, and also appends any old entry whose `id` the grievances file lacks, so this only happens with the mod switched off.
- **Missing altogether:** create it as `[]`.
- **Will not parse:** say so in one line and stop. Never overwrite it.

## When this fires

Not every hiccup. The bar: something about Claude Code's own behaviour (not the user's codebase, not a library, not the user's own mistake) visibly cost the user time or got in their way, and their reaction shows it registered as a grievance, not a shrug. Signals: a curse or frustrated aside, an explicit workaround adopted mid-session, a retry of the same thing a different way, a flat "this is annoying" / "why does it do that". An explicit "log this as a grievance" always fires regardless of tone.

Does not fire for: bugs in the user's own project, a one-off fluke that isn't reproducible, something already covered by an existing open entry (check first: see below).

## What to log

Append one entry to the grievances file:

```json
{
  "id": "kebab-case-slug",
  "description": "free-text account of the grievance, in the user's own words/framing where possible",
  "logged": "YYYY-MM-DD",
  "sourceSession": "short context: project or task at the time, optional",
  "resolvedIn": null,
  "resolvedNoted": null
}
```

Write the description as the actual problem experienced, not the changelog's eventual language for it: `proclaim-releases` matches by meaning later, and a description in the user's own framing is exactly what makes that match possible. Concrete over vague: "worktree isolation blocked a plain `git log` from a subagent, had to disable isolation to get unstuck" beats "worktree isolation is annoying".

**Before appending**, read the existing file and check no open entry (`resolvedIn: null`) already describes the same grievance, same underlying cause, even if the trigger differed. If one exists, don't duplicate; this skill only adds genuinely new grievances.

## After logging

Do it silently. No confirmation message, no "I've logged this as a grievance": the point is zero friction added on top of the friction just experienced. Continue the conversation as normal; the log entry is infrastructure, not an output to announce.

## Second entry point: marking an entry resolved

`proclaim-releases` calls this skill (never writes the JSON itself) once the user has explicitly confirmed a changelog fix addresses a specific open entry. When invoked for this, the calling instruction names the entry's `id` and the version that fixed it: find that entry, set:

```json
"resolvedIn": "2.1.222",
"resolvedNoted": "YYYY-MM-DD"
```

and stop. This path only ever runs after confirmation has already happened upstream; don't re-ask here, don't second-guess the match. If the named `id` isn't found, say so plainly rather than silently no-op-ing.

## Red flags

**Never** log a grievance the user didn't actually seem bothered by: inferring frustration from ordinary conversation causes false positives that pollute the store. **Never** log project-level bugs here; this store is Claude-Code-the-tool only. **Never** mark an entry resolved except via the second entry point above, and never invoke that path without an upstream confirmation already having happened; this skill trusts the caller's confirmation, it doesn't generate its own.
