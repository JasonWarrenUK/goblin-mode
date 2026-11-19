# Some Assembly Required

A five-level tutorial that builds one Claude Code skill, `tidy-imports`, from a single file to a plugin. Each level changes the same files; every step shows them whole as they stand after it.

Draft status: copy only. Every behavioural claim is listed in **Sources** at the end; anything the docs did not settle is in **Open questions**.

---

## Level 1: One File, One Job

`tidy-imports` does not exist yet. This level makes it: one folder, one `SKILL.md`, one argument and a first run on a real file.

### 1.1 A Folder and a SKILL.md

A skill is a folder holding a file called `SKILL.md`. Put it in the project at `.claude/skills/tidy-imports/` so everyone who clones the repository gets it. The file has two parts: YAML frontmatter between `---` lines, then the instructions Claude follows when the skill runs.

```bash
mkdir -p .claude/skills/tidy-imports
```

`.claude/skills/tidy-imports/SKILL.md` after step 1.1:

```markdown
---
name: tidy-imports
description: Sort the import statements at the top of a file
---

Sort the import statements at the top of the file
alphabetically, one per line. Leave everything below
the imports exactly as it was.
```

New in 1.1: every line.

- **1.1a** `name: tidy-imports` sets the command you type (`/tidy-imports`) and matches the folder name, which invokes the skill as well.
- **1.1b** `description:` is the line Claude reads to decide whether this skill fits what you asked for, so it says what the skill does in plain words.
- **1.1c** The three lines under the frontmatter are the whole job, written as instructions to Claude.

### 1.2 An Argument

The skill needs to know which file to tidy. `arguments: [path]` names the first word after the command `path`, and `$path` in the body is replaced with that word before Claude reads it. `argument-hint` shows what to type while you are typing the command.

`.claude/skills/tidy-imports/SKILL.md` after step 1.2:

```markdown
---
name: tidy-imports
description: Sort the import statements at the top of a file
arguments: [path]
argument-hint: "[file]"
---

Tidy the imports in $path.

Sort the import statements at the top of the file
alphabetically, one per line. Leave everything below
the imports exactly as it was.
```

New in 1.2: `arguments: [path]`, `argument-hint: "[file]"` and `Tidy the imports in $path.`

- **1.2a** `arguments: [path]` maps names to positions in order, so `path` is the first argument and a second name would be the second.
- **1.2b** `argument-hint: "[file]"` appears beside the command in autocomplete and changes nothing about how the skill runs.
- **1.2c** `$path` in `Tidy the imports in $path.` is swapped for the file you typed, and becomes an empty string when you type none.

### 1.3 Run It

Start Claude Code in the project and type the command with a file. If `.claude/skills/` did not exist when the session started, run `/reload-skills` first; Claude Code only watches skill folders it knew about at startup. Claude can also load the skill without the slash command when you ask it to sort a file's imports, because its description is in Claude's context.

```text
/tidy-imports src/app.ts
```

`src/app.ts` before the run:

```ts
import { serve } from './server';
import { readFileSync } from 'node:fs';
import express from 'express';

const app = express();
```

`src/app.ts` after the run:

```ts
import express from 'express';
import { readFileSync } from 'node:fs';
import { serve } from './server';

const app = express();
```

`.claude/skills/tidy-imports/SKILL.md` after step 1.3: unchanged from 1.2.

- **1.3a** `/tidy-imports src/app.ts` puts `src/app.ts` in place of `$path`, so the body's first line reaches Claude as `Tidy the imports in src/app.ts.`
- **1.3b** `const app = express();` is untouched, which is the line `Leave everything below the imports exactly as it was` exists to protect.

### Try it: handle a missing file

Run `/tidy-imports` with no file. `$path` becomes empty and Claude reads `Tidy the imports in .` Add one line to the body so Claude asks for a file instead of guessing.

**Answer.** Under `Tidy the imports in $path.`, add:

```markdown
If no path follows "in" above, ask which file to tidy and stop.
```

A named argument with nothing typed for it expands to an empty string, so the instruction has to cover that case in words.

---

## Level 2: Give It a Script and a Ledger

At level 1, `tidy-imports` was one file that asked Claude to sort a file's imports by hand. This level gives the sorting to a script, lets that one script run without a prompt and keeps a ledger of every file it touches.

### Where Level 1 Left It

This is `SKILL.md` as level 1 left it: four frontmatter fields and a body that asks Claude to do the sorting itself, in prose. The three sorting lines at the bottom are the ones step 2.1 replaces with a script.

```markdown
---
name: tidy-imports
description: Sort the import statements at the top of a file
arguments: [path]
argument-hint: "[file]"
---

Tidy the imports in $path.

Sort the import statements at the top of the file
alphabetically, one per line. Leave everything below
the imports exactly as it was.
```

### 2.1 Give It a Script

At level 1, Claude sorted the imports itself. A model asked to reorder lines will now and then reflow one it was told to leave alone. A script does the same thing every time, and Claude no longer rewrites the file line by line to get there. The sorting moves into `scripts/sort-imports.sh` in the skill's folder. Make it executable once with `chmod +x`.

`.claude/skills/tidy-imports/scripts/sort-imports.sh` after step 2.1:

```bash
#!/usr/bin/env bash
# Sort the import lines at the top of a file, in place.
set -euo pipefail
export LC_ALL=C # byte order, so every machine sorts the same way

file="$1"

# How many lines from the top start with "import "?
count=$(awk '/^import /{n++; next} {exit} END{print n+0}' "$file")
if [ "$count" -eq 0 ]; then
	echo "no imports at the top of $file"
	exit 0
fi

{ head -n "$count" "$file" | sort; tail -n +"$((count + 1))" "$file"; } > "$file.tmp"
mv "$file.tmp" "$file"
echo "sorted $count imports in $file"
```

New in 2.1: every line.

`.claude/skills/tidy-imports/SKILL.md` after step 2.1:

````markdown
---
name: tidy-imports
description: Sort the import statements at the top of a file
arguments: [path]
argument-hint: "[file]"
---

Tidy the imports in $path.

Run the script on the file, by exactly this path:

```bash
.claude/skills/tidy-imports/scripts/sort-imports.sh "$path"
```

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.
````

New in 2.1: from `Run the script on the file` to `report its message and stop.` Removed in 2.1: the three sorting lines.

- **2.1a** The script call takes the place of the three lines that told Claude how to sort.
- **2.1b** `Do not reorder any lines yourself` keeps Claude's hands off the sorting: it leaves the file alone after the script runs, and a non-zero exit ends the run with the script's message.

### 2.2 Scope the Tool

Running a script is a Bash call, and Claude Code asks before each one unless something approves it. `allowed-tools` approves the calls it names for the rest of the turn that started the skill. Naming the script's exact path, with `:*` for whatever arguments follow, approves that one script and no other command. It only adds approval: every other tool stays available under your usual permission settings.

The rule matches the start of the command, so the script call from 2.1a uses exactly that path, with no `bash` or `./` in front.

`.claude/skills/tidy-imports/SKILL.md` after step 2.2:

````markdown
---
name: tidy-imports
description: Sort the import statements at the top of a file
arguments: [path]
argument-hint: "[file]"
allowed-tools: Bash(.claude/skills/tidy-imports/scripts/sort-imports.sh:*)
---

Tidy the imports in $path.

Run the script on the file, by exactly this path:

```bash
.claude/skills/tidy-imports/scripts/sort-imports.sh "$path"
```

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.
````

New in 2.2: the `allowed-tools:` line.

- **2.2a** `allowed-tools` approves Bash calls that start with this path until you send your next message, and the `:*` covers whatever arguments follow.

### 2.3 Keep a Ledger

A ledger lets a later run say what an earlier one touched. The script appends one line per file to `.claude/tidy-imports.log`: the path and how many imports it sorted. Because the script writes it, keeping the ledger needs no extra permission.

The script's two new lines, in context:

```bash
...
file="$1"
ledger=".claude/tidy-imports.log"
...
mv "$file.tmp" "$file"
printf '%s\t%s\n' "$file" "$count" >> "$ledger"
echo "sorted $count imports in $file"
```

New in 2.3: the `ledger=` line and the `printf` line.

`.claude/tidy-imports.log` after two runs:

```text
src/app.ts	3
src/routes/home.ts	2
```

`.claude/skills/tidy-imports/SKILL.md` after step 2.3:

````markdown
---
name: tidy-imports
description: Sort the import statements at the top of a file
arguments: [path]
argument-hint: "[file]"
allowed-tools: Bash(.claude/skills/tidy-imports/scripts/sort-imports.sh:*)
---

Tidy the imports in $path.

Read .claude/tidy-imports.log if it exists. If $path is
already listed there, say so before going on.

Run the script on the file, by exactly this path:

```bash
.claude/skills/tidy-imports/scripts/sort-imports.sh "$path"
```

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.

The script also writes the ledger line. Never write to
.claude/tidy-imports.log yourself.
````

New in 2.3: the two lines from `Read .claude/tidy-imports.log` and the two lines from `The script also writes the ledger line`.

- **2.3a** `Read .claude/tidy-imports.log if it exists` makes a second run on the same file say so before it starts.
- **2.3b** `The script also writes the ledger line` keeps the ledger's format the same on every run and needs no permission beyond 2.2a.

### The Real Thing: `skills/project-tag_version/SKILL.md`

`project-tag_version` lives in this repository and tags a release after a merge to main. Its first marked line is a move `tidy-imports` does not have yet. The other two are this level's moves.

````markdown
---
name: "Project: Tag Version"
description: "Tag the release after a merge to main, computing the next semver tag with svu"
...
disable-model-invocation: true
allowed-tools: ["Bash(svu:*)", "Bash(git:*)", "Bash(~/.claude/library/scripts/safe-version-next.sh:*)"]
...
---

# Tag the release with `svu`

...

```bash
TAG="$("$HOME"/.claude/library/scripts/safe-version-next.sh)" && git tag "$TAG" && git push origin "$TAG"
```
...
````

- **R.a** `disable-model-invocation: true` stops Claude starting the skill on its own, so it runs only when a person asks for it by name after a merge has landed, which suits a step that pushes a tag.
- **R.b** `allowed-tools` names `safe-version-next.sh` by its full path, the move from 2.2a, beside `svu` and `git` for reading history and pushing one tag.
- **R.c** The `TAG=` line runs the script and tags whatever it prints, so Claude never works out the next version itself, the move from 2.1.

### Try it: put the date in the ledger

Change the script so each ledger line starts with the day it was written. Then change the ledger paragraph in `SKILL.md` so Claude says when a file was last tidied.

**Answer.** In `sort-imports.sh`, put the date in front of the path:

```bash
printf '%s\t%s\t%s\n' "$(date +%F)" "$file" "$count" >> "$ledger"
```

`date +%F` prints the date as `2026-11-19`, which sorts in date order as plain text. In `SKILL.md`, the second ledger line becomes: `already listed there, say on which date it was last tidied.`

---

## Level 3: Say Who Runs It, and How

`tidy-imports` now runs a script, approves only that script and keeps a ledger. This level writes down who may start it, which model and effort it runs on and which tools it must never touch, all in the frontmatter.

### 3.1 Who May Start It

By default both you and Claude can start a skill. `disable-model-invocation: true` would make it yours alone, and `user-invocable: false` would make it Claude's alone. `tidy-imports` stays open to both, so the line is written out with a comment that says why, and `when_to_use` tells Claude the moment to reach for it.

`.claude/skills/tidy-imports/SKILL.md` after step 3.1:

````markdown
---
name: tidy-imports
description: Sort the import statements at the top of a file
when_to_use: "After you add or remove imports in a file, or when the user asks to sort or tidy a file's imports."
arguments: [path]
argument-hint: "[file]"
disable-model-invocation: false # Claude may start it after changing a file's imports; the script only reorders import lines
allowed-tools: Bash(.claude/skills/tidy-imports/scripts/sort-imports.sh:*)
---

Tidy the imports in $path.

Read .claude/tidy-imports.log if it exists. If $path is
already listed there, say so before going on.

Run the script on the file, by exactly this path:

```bash
.claude/skills/tidy-imports/scripts/sort-imports.sh "$path"
```

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.

The script also writes the ledger line. Never write to
.claude/tidy-imports.log yourself.
````

New in 3.1: the `when_to_use:` line and the `disable-model-invocation:` line.

- **3.1a** `when_to_use` is added to the description in the list Claude reads, so it names the moment: just after Claude has changed a file's imports.
- **3.1b** `disable-model-invocation: false` is already the default, and writing it out gives the comment a place to record why Claude may start this skill unasked.
- **3.1c** The comment names the only safeguard so far, a script that touches nothing but import lines; git holds no copy of a file's uncommitted state, and step 4.3 adds a gate for that case.
- **3.1d** Had this line been `true`, the skill's description and `when_to_use` would leave Claude's context altogether, so `when_to_use` only does any work on a skill Claude may start.

### 3.2 Pin the Model and Effort

The skill reads a ledger and runs one script, so a mid-sized model at low effort is enough. `model` and `effort` in the frontmatter override the session for the rest of the turn the skill runs in. When you send your next message, the session's own model and effort come back.

`.claude/skills/tidy-imports/SKILL.md` after step 3.2:

````markdown
---
name: tidy-imports
description: Sort the import statements at the top of a file
when_to_use: "After you add or remove imports in a file, or when the user asks to sort or tidy a file's imports."
arguments: [path]
argument-hint: "[file]"
model: sonnet
effort: low
disable-model-invocation: false # Claude may start it after changing a file's imports; the script only reorders import lines
allowed-tools: Bash(.claude/skills/tidy-imports/scripts/sort-imports.sh:*)
---

Tidy the imports in $path.

Read .claude/tidy-imports.log if it exists. If $path is
already listed there, say so before going on.

Run the script on the file, by exactly this path:

```bash
.claude/skills/tidy-imports/scripts/sort-imports.sh "$path"
```

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.

The script also writes the ledger line. Never write to
.claude/tidy-imports.log yourself.
````

New in 3.2: `model: sonnet` and `effort: low`.

- **3.2a** `model: sonnet` takes the same aliases as `/model` and is skipped when your organisation's allowed list or auto mode rules it out, in which case the session model carries on.
- **3.2b** `effort: low` accepts `low`, `medium`, `high`, `xhigh` or `max`, though which of those a model offers depends on the model.
- **3.2c** Per the docs, both pins hold until your next message, so when Claude starts the skill partway through other work, whatever it does after the tidy in that turn also runs on `sonnet` at low effort.

### 3.3 Promises the Frontmatter Enforces

Since 2.1 the body has told Claude never to edit the file itself. `disallowed-tools` turns that sentence into a rule: the tools it lists are taken out of Claude's reach while the skill is active. `allowed-tools` adds approval; `disallowed-tools` removes tools. The removal lasts until your next message, so the sentence in the body stays.

`.claude/skills/tidy-imports/SKILL.md` after step 3.3:

````markdown
---
name: tidy-imports
description: Sort the import statements at the top of a file
when_to_use: "After you add or remove imports in a file, or when the user asks to sort or tidy a file's imports."
arguments: [path]
argument-hint: "[file]"
model: sonnet
effort: low
disable-model-invocation: false # Claude may start it after changing a file's imports; the script only reorders import lines
allowed-tools: Bash(.claude/skills/tidy-imports/scripts/sort-imports.sh:*)
disallowed-tools: [Edit, Write, NotebookEdit] # the script changes the file; Claude never does
---

Tidy the imports in $path.

Read .claude/tidy-imports.log if it exists. If $path is
already listed there, say so before going on.

Run the script on the file, by exactly this path:

```bash
.claude/skills/tidy-imports/scripts/sort-imports.sh "$path"
```

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.

The script also writes the ledger line. Never write to
.claude/tidy-imports.log yourself.
````

New in 3.3: the `disallowed-tools:` line.

- **3.3a** `disallowed-tools: [Edit, Write, NotebookEdit]` removes the three file-writing tools, so Claude cannot fix up the file after the script runs even if it decides to.
- **3.3b** The comment `the script changes the file; Claude never does` restates the promise from 2.1b, so a reader of the frontmatter alone sees why the list exists.
- **3.3c** `Do not reorder any lines yourself` stays in the body, because the tool removal clears at your next message and the instruction does not.
- **3.3d** The removal also lasts for the rest of the turn the skill started in, so if Claude runs the tidy partway through a task, it cannot edit any file again until you send your next message.

### The Real Thing: `skills/pr-update/SKILL.md`

`pr-update` rewrites a pull request's description after new commits land. It is open to Claude, pins its model and names its gate in a comment.

```markdown
---
name: "PR: Update"
description: "Update a PR description to account for commits made since it was last written"
when_to_use: "When commits have been pushed to a branch after its PR was opened or last described; offer it whenever new work lands on a branch with an open PR rather than leaving the description stale."
model: sonnet
effort: medium
...
disable-model-invocation: false # invocable by Claude so it can offer a refresh when new commits leave the description stale; its approval step still gates the write
...
---
...
### 5. Show me the diff

Display the updated body in full and a brief summary of what changed vs the previous description. **Wait for my approval.**
...
```

- **R.a** `when_to_use` names a moment Claude sees first, new commits on a branch whose description has gone stale, the move from 3.1a.
- **R.b** `model: sonnet` and `effort: medium` pin the run the same way 3.2 does, one notch higher on effort.
- **R.c** The comment on `disable-model-invocation: false` names the gate that makes it safe to leave open, the move from 3.1b.
- **R.d** `**Wait for my approval.**` is that gate, and step 4.3 gives `tidy-imports` one of its own.

`pr-update` has no `disallowed-tools` line. For that move, see line 13 of `skills/project-tag_version/SKILL.md`, which removes `git push --tags` because it would publish every stray local tag.

### Try it: make it yours alone

tam wants `tidy-imports` to run only when someone types it. Change the frontmatter.

**Answer.** Set the line to `disable-model-invocation: true` with a new comment, and delete `when_to_use`:

```yaml
disable-model-invocation: true # runs only when typed
```

A skill with `disable-model-invocation: true` has its description taken out of Claude's context, so `when_to_use` would never be read. Typing `/tidy-imports src/app.ts` still works.

---

## Level 4: Skills That Call Skills

`tidy-imports` now says who may start it, what it runs on and what it may never touch. This level splits a read-only check into a skill of its own, calls it from `tidy-imports` and adds a gate before the one change git cannot undo.

### 4.1 Split Out a Read-Only Check

Telling whether a file's imports are already sorted is useful on its own: before a commit, or to decide whether a tidy is needed at all. It also never writes, so it can be shared freely. It becomes `tidy-imports-check`, with its own script that reports and changes nothing.

`.claude/skills/tidy-imports-check/scripts/check-imports.sh` after step 4.1:

```bash
#!/usr/bin/env bash
# Report whether the import lines at the top of a file are sorted. Never writes.
set -euo pipefail
export LC_ALL=C # the same order sort-imports.sh uses

file="$1"

count=$(awk '/^import /{n++; next} {exit} END{print n+0}' "$file")
if [ "$count" -eq 0 ]; then
	echo "no imports at the top of $file"
	exit 0
fi

if head -n "$count" "$file" | sort -c 2>/dev/null; then
	echo "sorted: $count imports in $file"
else
	echo "unsorted: $count imports in $file; sorted, they would read:"
	head -n "$count" "$file" | sort
fi
```

New in 4.1: every line.

`.claude/skills/tidy-imports-check/SKILL.md` after step 4.1:

````markdown
---
name: tidy-imports-check
description: Report whether the import statements at the top of a file are sorted, without changing the file
when_to_use: "Before tidy-imports rewrites a file, or when the user asks whether a file's imports are in order."
arguments: [path]
argument-hint: "[file]"
model: sonnet
effort: low
disable-model-invocation: false # tidy-imports calls this skill, so Claude must be able to invoke it
allowed-tools: Bash(.claude/skills/tidy-imports-check/scripts/check-imports.sh:*)
disallowed-tools: [Edit, Write, NotebookEdit] # reads, never writes
---

Check the imports in $path.

Run the script on the file, by exactly this path:

```bash
.claude/skills/tidy-imports-check/scripts/check-imports.sh "$path"
```

Report its output as it stands. Do not sort, fix or change
anything, even when the imports are out of order.
````

New in 4.1: every line.

On `src/app.ts` from 1.3, before tidying, the script prints:

```text
unsorted: 3 imports in src/app.ts; sorted, they would read:
import express from 'express';
import { readFileSync } from 'node:fs';
import { serve } from './server';
```

- **4.1a** `sort -c` only checks the order and exits non-zero on the first line out of place, so the script never opens the file for writing.
- **4.1b** `export LC_ALL=C` matches the line in `sort-imports.sh`, so the check and the tidy agree on what sorted means.
- **4.1c** `disable-model-invocation: false` is already the default, and its comment records that another skill calls this one, so nobody flips it to `true` without seeing what 4.2 depends on.
- **4.1d** `disallowed-tools` lists only the file-writing tools and leaves Bash alone, because the check runs its own script.

### 4.2 Call It From tidy-imports

`tidy-imports` now runs the check first and stops when there is nothing to do. The body says to load the skill by name, and Claude does that through its Skill tool, the same way it loads any skill. That tool refuses a skill marked `disable-model-invocation: true` unless your own message names that skill's command, so a skill another skill calls must stay open to Claude.

`.claude/skills/tidy-imports/SKILL.md` after step 4.2:

````markdown
---
name: tidy-imports
description: Sort the import statements at the top of a file
when_to_use: "After you add or remove imports in a file, or when the user asks to sort or tidy a file's imports."
arguments: [path]
argument-hint: "[file]"
model: sonnet
effort: low
disable-model-invocation: false # Claude may start it after changing a file's imports; the script only reorders import lines
allowed-tools: Bash(.claude/skills/tidy-imports/scripts/sort-imports.sh:*)
disallowed-tools: [Edit, Write, NotebookEdit] # the script changes the file; Claude never does
---

Tidy the imports in $path.

Read .claude/tidy-imports.log if it exists. If $path is
already listed there, say so before going on.

Load the tidy-imports-check skill on $path. If it reports
the imports already sorted, say so and stop. If the check
cannot run, say why and stop.

Run the script on the file, by exactly this path:

```bash
.claude/skills/tidy-imports/scripts/sort-imports.sh "$path"
```

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.

The script also writes the ledger line. Never write to
.claude/tidy-imports.log yourself.
````

New in 4.2: the three lines from `Load the tidy-imports-check skill`.

- **4.2a** `Load the tidy-imports-check skill on $path` names the skill and its argument, which is all one skill needs to call another.
- **4.2b** `If the check cannot run, say why and stop` covers the day someone marks the check `disable-model-invocation: true` and the call is refused.
- **4.2c** Both files pin `model: sonnet` and `effort: low`: the docs say a skill's `model` and `effort` hold for the rest of the turn, so a different pin in the check would carry into the rest of the tidy.

### 4.3 A Gate Before Anything Irreversible

The script rewrites the file in place and keeps no copy. For a committed file, git holds the old order. For a file with uncommitted changes, or one git has never seen, nothing does. `tidy-imports` checks for that case and waits for a yes before the script runs.

`.claude/skills/tidy-imports/SKILL.md` after step 4.3:

````markdown
---
name: tidy-imports
description: Sort the import statements at the top of a file
when_to_use: "After you add or remove imports in a file, or when the user asks to sort or tidy a file's imports."
arguments: [path]
argument-hint: "[file]"
model: sonnet
effort: low
disable-model-invocation: false # Claude may start it after changing a file's imports; it stops for a yes before rewriting a file git has no copy of
allowed-tools: ["Bash(.claude/skills/tidy-imports/scripts/sort-imports.sh:*)", "Bash(git status:*)"]
disallowed-tools: [Edit, Write, NotebookEdit] # the script changes the file; Claude never does
---

Tidy the imports in $path.

Read .claude/tidy-imports.log if it exists. If $path is
already listed there, say so before going on.

Load the tidy-imports-check skill on $path. If it reports
the imports already sorted, say so and stop. If the check
cannot run, say why and stop.

Run `git status --porcelain -- "$path"`. If it prints
anything, the file has changes git holds no copy of, and
the rewrite cannot be undone from git. Show the check's
report, say this and stop. Run the script only after the
user replies yes.

Run the script on the file, by exactly this path:

```bash
.claude/skills/tidy-imports/scripts/sort-imports.sh "$path"
```

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.

The script also writes the ledger line. Never write to
.claude/tidy-imports.log yourself.
````

New in 4.3: the five lines from `Run` to `user replies yes.`, the `Bash(git status:*)` entry in `allowed-tools` and the new comment on `disable-model-invocation`.

- **4.3a** `git status --porcelain -- "$path"` prints nothing for a file git already holds as it is, so a clean file goes straight to the script with no question asked.
- **4.3b** `Show the check's report, say this and stop` puts the planned order in front of the person before they answer, so the yes is an informed one.
- **4.3c** The yes arrives as a new message, which clears both the `allowed-tools` grant and the `disallowed-tools` removal, so Claude Code asks before the script runs unless your permission settings already allow it.
- **4.3d** The comment on `disable-model-invocation` now names the gate, which is what makes it reasonable to leave a file-rewriting skill open to Claude.

### The Real Thing: `pr-review-dry_run`, `pr-review` and `branch-qa_review`

Three skills in this repository share one review method. `pr-review-dry_run` holds it and prints findings; `pr-review` and `branch-qa_review` both call it.

`skills/pr-review-dry_run/SKILL.md`:

```markdown
---
name: "PR: Review (Dry Run)"
...
model: opus
effort: high
...
disable-model-invocation: false # required so pr-review can call it
...
disallowed-tools: ["Edit", "Write", "NotebookEdit"] # reviews, never fixes
...
---
...
Canonical review methodology. Produces structured findings only; **never posts to GitHub**. `pr-review` loads this skill and handles posting; keep all methodology here to avoid divergence.
...
```

`skills/pr-review/SKILL.md`:

```markdown
...
model: opus
effort: high
...
disable-model-invocation: false # invocable so next-task-ship's Step 7 self-review can call it; it posts to GitHub, so never invoke without an explicit ask or that orchestration
...
    <step num="3">Load the pr-review-dry_run skill and run it against the resolved PR identifier, ...
...
```

`skills/branch-qa_review/SKILL.md`:

```markdown
...
disable-model-invocation: true
...
Load the `pr-review-dry_run` skill and run its full methodology against this branch: ...
...
If the verdict is **Ready**, offer to run the `pr-create` skill immediately, ...
```

- **R.a** `disable-model-invocation: false # required so pr-review can call it` is the move from 4.1c, with the reason written beside it.
- **R.b** `pr-review` posts to GitHub with no approval step, so its gate lives in the comment on its `disable-model-invocation` line, which limits when Claude may start it.
- **R.c** `Load the pr-review-dry_run skill` appears in both callers, the same plain instruction as 4.2a.
- **R.d** `branch-qa_review` is itself `disable-model-invocation: true`, which shows the rule runs one way: the caller may be yours alone, and the skill it calls may not; it also ends by offering `pr-create` and leaves the yes to you.

Caller and callee pin the same `model: opus` and `effort: high`, the pairing from 4.2c.

### Try it: predict the refusal

ravi sets `tidy-imports-check` to `disable-model-invocation: true`, then types `/tidy-imports src/app.ts`. What happens?

**Answer.** `tidy-imports` starts, because ravi typed its command. When it tries to load `tidy-imports-check`, Claude Code refuses, because ravi's message named only `/tidy-imports`. The line from 4.2b applies, so Claude says the check could not run and stops before the script.
---

## Level 5: Pack It as a Plugin

`tidy-imports` and `tidy-imports-check` live in one project's `.claude/skills/`. This level moves them into a plugin so any project can install them with one command.

### 5.1 A Plugin Folder and plugin.json

A plugin is a folder with a manifest at `.claude-plugin/plugin.json` and its components beside it. Skills go in `skills/`, one folder each, exactly as they sat in `.claude/skills/`. Call the plugin `tidy`. Its two skills become `/tidy:tidy-imports` and `/tidy:tidy-imports-check`.

The plugin folder after step 5.1:

```text
tidy/
	.claude-plugin/
		plugin.json
	skills/
		tidy-imports/
			SKILL.md
			scripts/sort-imports.sh
		tidy-imports-check/
			SKILL.md
			scripts/check-imports.sh
```

`tidy/.claude-plugin/plugin.json` after step 5.1:

```json
{
	"name": "tidy",
	"version": "0.1.0",
	"description": "Sort the import statements at the top of a file, with a read-only check first",
	"author": {
		"name": "noor"
	},
	"license": "MIT"
}
```

New in 5.1: every line, and the folder itself.

- **5.1a** `"name": "tidy"` is the only required field; written in kebab-case, it becomes the prefix on every skill the plugin holds.
- **5.1b** `"version": "0.1.0"` keeps people who install the plugin from a hosted marketplace on this version until you change the number.
- **5.1c** `.claude-plugin/` holds the manifest and nothing else, while `skills/` sits at the plugin root beside it.

Test it before anything else with `claude --plugin-dir ./tidy`, which loads the plugin for that one session without installing it.

### 5.2 ${CLAUDE_PLUGIN_ROOT} Replaces .claude Paths

Every path that pointed into `.claude/skills/` (or into `~/.claude/` for a personal skill) now points at a folder that is not there on someone else's machine. A plugin installed from a hosted marketplace is copied into Claude Code's plugin cache, a new folder for each version; one from a marketplace on your own disk loads from where it sits. `${CLAUDE_PLUGIN_ROOT}` is replaced with that folder's path in both the body and `allowed-tools`, so the rule still matches the command Claude runs. The call to the check uses its plugin name too.

`tidy/skills/tidy-imports/SKILL.md` after step 5.2:

````markdown
---
name: tidy-imports
description: Sort the import statements at the top of a file
when_to_use: "After you add or remove imports in a file, or when the user asks to sort or tidy a file's imports."
arguments: [path]
argument-hint: "[file]"
model: sonnet
effort: low
disable-model-invocation: false # Claude may start it after changing a file's imports; it stops for a yes before rewriting a file git has no copy of
allowed-tools: ["Bash(${CLAUDE_PLUGIN_ROOT}/skills/tidy-imports/scripts/sort-imports.sh:*)", "Bash(git status:*)"]
disallowed-tools: [Edit, Write, NotebookEdit] # the script changes the file; Claude never does
---

Tidy the imports in $path.

Read .claude/tidy-imports.log if it exists. If $path is
already listed there, say so before going on.

Load the tidy:tidy-imports-check skill on $path. If it
reports the imports already sorted, say so and stop. If the
check cannot run, say why and stop.

Run `git status --porcelain -- "$path"`. If it prints
anything, the file has changes git holds no copy of, and
the rewrite cannot be undone from git. Show the check's
report, say this and stop. Run the script only after the
user replies yes.

Run the script on the file, by exactly this path:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/tidy-imports/scripts/sort-imports.sh "$path"
```

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.

The script also writes the ledger line. Never write to
.claude/tidy-imports.log yourself.
````

Changed in 5.2: the script path in `allowed-tools`, the script path in the `bash` block and `tidy:tidy-imports-check` in the call.

`tidy/skills/tidy-imports-check/SKILL.md` after step 5.2:

````markdown
---
name: tidy-imports-check
description: Report whether the import statements at the top of a file are sorted, without changing the file
when_to_use: "Before tidy:tidy-imports rewrites a file, or when the user asks whether a file's imports are in order."
arguments: [path]
argument-hint: "[file]"
model: sonnet
effort: low
disable-model-invocation: false # tidy:tidy-imports calls this skill, so Claude must be able to invoke it
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/skills/tidy-imports-check/scripts/check-imports.sh:*)
disallowed-tools: [Edit, Write, NotebookEdit] # reads, never writes
---

Check the imports in $path.

Run the script on the file, by exactly this path:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/tidy-imports-check/scripts/check-imports.sh "$path"
```

Report its output as it stands. Do not sort, fix or change
anything, even when the imports are out of order.
````

Changed in 5.2: the script path in `allowed-tools`, the script path in the `bash` block and `tidy:tidy-imports` in `when_to_use` and the comment. Both scripts are unchanged from 4.1 and 2.3.

- **5.2a** `${CLAUDE_PLUGIN_ROOT}` appears in `allowed-tools` and in the `bash` block alike, so after substitution the rule and the command carry the same absolute path.
- **5.2b** `Load the tidy:tidy-imports-check skill` uses the full plugin name, the form every plugin skill carries.
- **5.2c** `.claude/tidy-imports.log` stays a project path, because the plugin's own folder changes with every version and is no place to keep state.

### 5.3 Install From a Marketplace

A marketplace is a folder or repository with `.claude-plugin/marketplace.json` listing plugins and where each one lives. noor keeps one called `noor-tools` with `tidy` under `plugins/`. Anyone can then add the marketplace once and install from it.

`noor-tools/.claude-plugin/marketplace.json`:

```json
{
	"name": "noor-tools",
	"owner": {
		"name": "noor"
	},
	"plugins": [
		{
			"name": "tidy",
			"source": "./plugins/tidy",
			"description": "Sort the import statements at the top of a file, with a read-only check first"
		}
	]
}
```

New in 5.3: every line.

Install it in a session:

```text
/plugin marketplace add ./noor-tools
/plugin install tidy@noor-tools
```

Or from your shell:

```bash
claude plugin marketplace add ./noor-tools
claude plugin install tidy@noor-tools
```

Then, in any project:

```text
/tidy:tidy-imports src/app.ts
```

- **5.3a** The entry `"name": "tidy"` matches the plugin's own `name`, because installs use the entry name and skill prefixes use the manifest name, and a mismatch breaks the install.
- **5.3b** `"source": "./plugins/tidy"` is written from the marketplace root, the folder that holds `.claude-plugin/`.
- **5.3c** `tidy@noor-tools` is the plugin's entry name, an `@` and the marketplace name.
- **5.3d** `/plugin marketplace add` also takes a GitHub `owner/repo`, so once `noor-tools` is pushed, `/plugin marketplace add noor/noor-tools` adds it on any machine.

Delete the old `.claude/skills/tidy-imports/` and `.claude/skills/tidy-imports-check/` folders from the project once the plugin works. While they stay, `/tidy-imports` still runs the project copy.

### The Real Thing: `marketplace/goblin-scout/`

`goblin-scout` is a plugin in this repository that keeps a project plan, the roadbook, as a graph of what waits on what. Its skills run as `/goblin-scout:<skill>`. The excerpts come from the `feat/goblin-scout-rename` branch at commit `82719bd`, which renames the plugin from `roadmap`.

`marketplace/goblin-scout/.claude-plugin/plugin.json`:

```json
{
    "name": "goblin-scout",
    "version": "3.0.0",
    ...
    "license": "Zlib",
    ...
    "types": "./types/index.d.ts"
}
```

`marketplace/goblin-scout/skills/start-roadbook/SKILL.md`:

```markdown
---
...
when_to_use: "When a project has no roadbook yet, or an existing simple-style one needs superseding with a new phase built from scratch (for converting an old single-file roadmap, use goblin-scout:rebind-roadbook instead)."
model: fable
effort: high
...
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Write", "Bash(python3:*)"]
arguments: ["phase"]
argument-hint: "[phase name (optional, e.g. PHASE_1)]"
---
...
Shared conventions (status vocabulary, colour table, graph rules, formatting) live in `${CLAUDE_PLUGIN_ROOT}/references/roadbook-conventions.md`; read it before writing anything. The CLI is `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py`.
```

`.claude-plugin/marketplace.json` at the repository root:

```json
{
	"name": "goblin-mode",
	...
	"plugins": [
		{
			"name": "goblin-scout",
			"source": "./marketplace/goblin-scout",
			...
```

- **R.a** `"name": "goblin-scout"` is the prefix every skill in the plugin carries, so `start-roadbook` runs as `/goblin-scout:start-roadbook`, the move from 5.1a.
- **R.b** `use goblin-scout:rebind-roadbook instead` names a sibling skill by its full plugin name, the move from 5.2b.
- **R.c** `${CLAUDE_PLUGIN_ROOT}/references/` and `${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py` reach files the plugin ships, wherever it was installed, the move from 5.2a.
- **R.d** The marketplace entry's `"name": "goblin-scout"` matches the manifest's, so it installs as `goblin-scout@goblin-mode` after `/plugin marketplace add <owner>/goblin-mode`, where `<owner>` stands for the GitHub account that hosts the repository.

The manifest's `"types"` line declares the state of the plugin's mod, the hooks module that ships beside its skills: code that runs inside Claude Code and can draw panes. Plugins and mods get a fuller article of their own later.

### Try it: which one runs?

tam installs `tidy@noor-tools` in a project that still has `.claude/skills/tidy-imports/`, then types `/tidy-imports src/app.ts`. Which skill runs, and what should tam type to be sure of the plugin's?

**Answer.** The project copy runs. Both skills load because the plugin's is namespaced. A plugin skill answers to its bare name only when no other command already uses that name. `/tidy:tidy-imports src/app.ts` always reaches the plugin's skill; deleting the project folder makes the bare name reach it too.

---

## Open Questions

1. **The `name` field in this repository's skills.** The docs say a skill's frontmatter `name` sets the command name, and in a plugin skill it sets the last segment. This repository writes display titles there: `name: "Project: Tag Version"`, `name: "Start Roadbook"`. This session lists plugin skills as `roadmap:claim (roadmap:Claim)`, which suggests the folder name is the command and `name` is shown beside it. The draft writes `/goblin-scout:start-roadbook` as the outline asks, but the docs as written would predict a command built from `Start Roadbook`. Needs a test on a live install.
2. **Whether R.b at level 2 runs without a prompt.** `project-tag_version` approves `Bash(~/.claude/library/scripts/safe-version-next.sh:*)`, but its body runs `TAG="$("$HOME"/.claude/...)" && git tag ...`. The permissions page says an allow rule does not match past an assignment of a variable outside a known-safe list, and the command uses `$HOME` where the rule writes `~`. The draft claims only what the frontmatter says and makes no claim about whether the command prompts.
3. **Calling one skill from another.** The docs do not describe skill-to-skill calls as a feature. They say Claude invokes skills through the Skill tool and that `disable-model-invocation: true` stops Claude invoking a skill unless the person's message names it. The draft infers from these that a call made partway through another skill is refused in the same way. The docs do not name that case directly.
4. **What a called skill's settings do to its caller.** The docs say `model` and `effort` hold for the rest of the turn and `disallowed-tools` until the next message. The draft infers that a called skill's pins and removals carry into the rest of the calling skill's turn (4.2c). The docs do not describe a nested case, so this is a reading of the wording.
5. **Gates that wait for a reply.** The docs say an `allowed-tools` grant clears at the next message. Any skill whose gate waits for the person's yes (`pr-update` step 5, `tidy-imports` 4.3) runs its post-gate command without the skill's grant. Whether answering an `AskUserQuestion` prompt counts as a new message was not checked.
6. **goblin-scout is unmerged.** The level 5 excerpts come from `origin/feat/goblin-scout-rename` at `82719bd`. Line numbers and wording may change before it merges. The outline's word list (roadbook, `start-roadbook`, `tend-roadbook`, `unroll-chart`, `.claude/roadbook.json`) matches that branch.
7. **Relative script paths.** Levels 2 to 4 call `.claude/skills/tidy-imports/scripts/sort-imports.sh`, a path relative to the project root, and the `allowed-tools` rule matches that exact text. A session started in a subdirectory, or a Claude that has run `cd`, would miss the file. The docs offer `${CLAUDE_SKILL_DIR}` in both the body and `allowed-tools` for exactly this; the draft keeps the relative path so that 5.2's change has something to replace. Worth deciding whether 2.1 should teach `${CLAUDE_SKILL_DIR}` instead.
8. **3.1 leaves `tidy-imports` open to Claude with no gate until 4.3.** This repository's convention (`skills/clod-config-skill_conventions/SKILL.md:17`) keeps a command skill `disable-model-invocation: true` until it has its own approval gate. The draft names the gap in 3.1c and closes it in 4.3, because `when_to_use` only reaches Claude on a skill Claude may start, so a user-only 3.1 would teach a field that does nothing.
9. **The `renames` key.** The branch's `marketplace.json` carries `"renames": {"roadmap": "goblin-scout", ...}`. The manifest and marketplace pages read for this draft do not document it, so the draft does not mention it.
10. **Changes made to the lifted level 2 copy.** `argument-hint` added to every level 2 snapshot so it carries forward from 1.2; "for as long as the skill runs" rewritten to the turn-scoped grant the docs describe; "costs no tokens" removed; `export LC_ALL=C` added to the script, because the default `sort` on macOS with `en_GB.UTF-8` puts `import {` lines before `import express` and C order puts them after; the ledger sample's counts changed from 6 and 3 to 3 and 2, the first to match the 1.3 file; the Real Thing callout R.a now says "which suits a step that pushes a tag" in place of a reason the source file does not give. Each needs a matching edit in `gen-hybrid.ts` if the mockup is kept.

---

## Sources

| Claim | Source | Read |
|---|---|---|
| A skill is a folder with `SKILL.md`: frontmatter between `---` lines, then instructions | https://code.claude.com/docs/en/skills#create-your-first-skill | 2026-11-19 |
| Project skills live at `.claude/skills/<name>/SKILL.md`; plugin skills run as `/plugin-name:skill-name` | https://code.claude.com/docs/en/skills#choose-where-skills-load | 2026-11-19 |
| `name` sets the command; the folder name also invokes it; in a plugin, `name` sets the last segment | https://code.claude.com/docs/en/skills#how-a-skill-gets-its-command-name | 2026-11-19 |
| A plugin skill's bare name works only when no other command uses it | https://code.claude.com/docs/en/skills#how-a-skill-gets-its-command-name | 2026-11-19 |
| `description` is what Claude uses to decide when to apply a skill | https://code.claude.com/docs/en/skills#frontmatter-reference | 2026-11-19 |
| `when_to_use` is appended to `description` in the listing | https://code.claude.com/docs/en/skills#frontmatter-reference | 2026-11-19 |
| `arguments` maps names to positions; `$name` expands to that argument; an unfilled named argument becomes an empty string | https://code.claude.com/docs/en/skills#available-string-substitutions | 2026-11-19 |
| `argument-hint` is shown during autocomplete | https://code.claude.com/docs/en/skills#frontmatter-reference | 2026-11-19 |
| Live change detection; `/reload-skills` for a skills folder created after startup | https://code.claude.com/docs/en/skills#edit-a-skill-during-a-session | 2026-11-19 |
| `allowed-tools` approves listed tools for the turn that invokes the skill, clears at the next message and restricts nothing | https://code.claude.com/docs/en/skills#pre-approve-tools-for-a-skill | 2026-11-19 |
| `Bash(x:*)` equals `Bash(x *)`; `:*` is recognised only at the end | https://code.claude.com/docs/en/permissions (Wildcard patterns, around line 189 of the page source) | 2026-11-19 |
| Allow rules do not match past most variable assignments; compound commands need every part allowed | https://code.claude.com/docs/en/permissions#compound-commands and #wrappers | 2026-11-19 |
| `disallowed-tools` removes tools while the skill is active and clears at the next message | https://code.claude.com/docs/en/skills#frontmatter-reference | 2026-11-19 |
| `disable-model-invocation: true`: Claude cannot invoke it on its own; description leaves context; blocked unless the person's message names the command | https://code.claude.com/docs/en/skills#control-who-invokes-a-skill | 2026-11-19 |
| A command name after plain text in a message counts as permission to run it | https://code.claude.com/docs/en/skills#where-you-write-the-skills-name | 2026-11-19 |
| `user-invocable: false` hides the skill from you and leaves it open to Claude | https://code.claude.com/docs/en/skills#control-who-invokes-a-skill | 2026-11-19 |
| Claude invokes skills through the Skill tool; any skill without `disable-model-invocation: true` is open to it | https://code.claude.com/docs/en/skills#restrict-claudes-skill-access | 2026-11-19 |
| `model` holds for the rest of the turn; same values as `/model`; skipped when excluded by the allowed list or auto mode | https://code.claude.com/docs/en/skills#frontmatter-reference | 2026-11-19 |
| `sonnet` is a model alias | https://code.claude.com/docs/en/model-config#model-aliases | 2026-11-19 |
| `effort` levels `low` to `max`; availability depends on the model | https://code.claude.com/docs/en/skills#frontmatter-reference | 2026-11-19 |
| `git` read-only forms run without a prompt (not relied on; 4.3 lists `git status` in `allowed-tools`) | https://code.claude.com/docs/en/permissions#read-only-commands | 2026-11-19 |
| Plugin layout: `.claude-plugin/plugin.json` with components at the plugin root | https://code.claude.com/docs/en/plugins/manifest-reference#manifest-file | 2026-11-19 |
| `name` is the only required manifest field; the docs ask for kebab-case; it namespaces every component | https://code.claude.com/docs/en/plugins/manifest-reference#name | 2026-11-19 |
| `version` pins installers to that version until it changes, except for a plugin loaded in place from a local-path marketplace | https://code.claude.com/docs/en/plugins/manifest-reference#version | 2026-11-19 |
| `types` declares a mod's state | https://code.claude.com/docs/en/plugins/manifest-reference#fields | 2026-11-19 |
| `--plugin-dir` loads a plugin for one session without installing it | https://code.claude.com/docs/en/plugins/create#create-your-first-plugin | 2026-11-19 |
| `${CLAUDE_PLUGIN_ROOT}` is substituted in a plugin skill's body and in `allowed-tools` Bash rules | https://code.claude.com/docs/en/skills#available-string-substitutions | 2026-11-19 |
| Installed plugins are copied to a per-version cache folder; `${CLAUDE_PLUGIN_ROOT}` points there and changes on update, so no state goes there | https://code.claude.com/docs/en/plugins/loading (plugins root table) and https://code.claude.com/docs/en/plugins/manifest-reference#environment-variables | 2026-11-19 |
| Marketplace file, `source` written from the marketplace root, entry name matching the manifest name | https://code.claude.com/docs/en/plugin-marketplaces#rules-for-plugin-entries | 2026-11-19 |
| A plugin skill and a same-named project skill both load; the bare name reaches the plugin's only when no other command uses it | https://code.claude.com/docs/en/skills#resolve-skills-that-share-a-name and #how-a-skill-gets-its-command-name | 2026-11-19 |
| `/plugin marketplace add` sources (local path, `owner/repo`); `/plugin install <plugin>@<marketplace>`; shell equivalents | https://code.claude.com/docs/en/plugins/install#add-a-marketplace and #install-from-your-shell | 2026-11-19 |
| Mods are plugins with a hooks module that can draw panes | https://code.claude.com/docs/en/plugins/overview and `docs/reference/mods.md:5` | 2026-11-19 |
| Repository convention: an open command skill needs its own gate before anything irreversible | `skills/clod-config-skill_conventions/SKILL.md:17` | 2026-11-19 |
| `project-tag_version` excerpt | `skills/project-tag_version/SKILL.md:1-3,11-12,14,16,28-30` | 2026-11-19 |
| `project-tag_version` removes `git push --tags` | `skills/project-tag_version/SKILL.md:13` | 2026-11-19 |
| `pr-update` excerpt | `skills/pr-update/SKILL.md:1-6,11,15,95-97` | 2026-11-19 |
| `pr-review-dry_run` excerpt | `skills/pr-review-dry_run/SKILL.md:1-2,5-6,11,13,16,20` | 2026-11-19 |
| `pr-review` excerpt | `skills/pr-review/SKILL.md:5-6,11,28` | 2026-11-19 |
| `branch-qa_review` excerpt | `skills/branch-qa_review/SKILL.md:11,30,92` | 2026-11-19 |
| goblin-scout manifest excerpt | `marketplace/goblin-scout/.claude-plugin/plugin.json:1-3,9,17-18` at `origin/feat/goblin-scout-rename` `82719bd` | 2026-11-19 |
| `start-roadbook` excerpt | `marketplace/goblin-scout/skills/start-roadbook/SKILL.md:1,4-6,10-14,24` at `82719bd` | 2026-11-19 |
| Marketplace entry excerpt | `.claude-plugin/marketplace.json:1-2,9-12` at `82719bd` | 2026-11-19 |
| Level 2 copy lifted from | `site/design/mockups/src/gen-hybrid.ts:17-264` | 2026-11-19 |
| `sort-imports.sh` and `check-imports.sh` behaviour, including the C-order output shown in 1.3 and 4.1 | Run in a scratch folder on macOS, 2026-11-19 | 2026-11-19 |
