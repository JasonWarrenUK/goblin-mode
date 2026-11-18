---
name: "Goblin Warband: Declare Raid"
description: "Start a multi-session raid from the chief's session: pick the tasks, create one worktree per task, record the raid in the ledger, write the shared guidance and each raider's orders, and hand the user one launch line per raider"
when_to_use: "When the user wants several Claude Code sessions working the same repository at once and this session is to lead them: 'kick off a raid', 'lead these tasks', 'set up the warband for 10SE.2, 10SE.4 and 11HD.4'. Needs .claude/goblin-warband.json (goblin-warband:configure-warband writes one). Never while a raid is already active for the repository."
model: opus
effort: high
metadata:
  glyph: ᛟ
  family: warband
  goblin-spinner: mustering the raiders|digging worktrees|writing orders|numbering decrees
disable-model-invocation: true
allowed-tools: ["Read", "Write", "Glob", "Grep", "Bash(python3:*)", "Bash(git:*)", "Bash(gh:*)", "Bash(ls:*)", "Bash(sh:*)", "Bash(zsh:*)", "AskUserQuestion", "mcp__goblin-warband__warband_decree", "mcp__goblin-warband__warband_slate"]
arguments: ["tasks"]
argument-hint: "[task ids...] [name <raid name>]"
---

# Goblin Warband: Declare Raid

The chief's first hour, done before any raider exists: facts at a named commit, one worktree per task, the raid in the ledger, numbered decrees, orders per raider. The user starts the sessions; the `SessionStart` hook hands each its orders. The protocol the rest of the raid follows is `${CLAUDE_PLUGIN_ROOT}/references/protocol.md`; read sections 1 to 3 before step 3.

The CLI is `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/warband.py`. Every write to the ledger goes through it.

---

## Step 0: Parse the arguments

Tokens before `name` are task ids (`10SE.2`), matched against the roadbook's waypoints when there is one. `name <raid name>` names the raid; default: the task ids joined with `+`, or the date.

```text
Usage: /goblin-warband:declare-raid [task ids...] [name <raid name>]
```

## Step 1: Preconditions

0. This session's model. The mod refuses `warband.py start` from a haiku or sonnet session and says so; leading takes an opus session (all the orders, every raider's message and the whole slate pass through it). Do not add `--small-model-ok` on your own: that flag is the user's to type, and the right move is a fresh opus session.
1. `warband.py detect`. Exit 2: stop and say `/goblin-warband:configure-warband` writes the project config; nothing else happens without it.
2. `warband.py --json status` (the flag goes before the subcommand). A non-null `run`: stop and name it; `/goblin-warband:declare-victory` closes a raid.
3. `git fetch origin` in the main checkout, then record the base: `git rev-parse origin/<default branch>` (origin's HEAD), or the branch the user names. Check it is on origin: `git ls-remote --exit-code --heads origin <base>`. A base that is not (a feature branch the PRs will stack on) cannot be a PR target until the user pushes it, and the push publishes its commits, so it is the user's: `warband.py start` puts it on the tribute list as item 1 and warns; say so in the hand-over and do not expect a PR before it is done. This sha is quoted in the guidance and all the orders; every shared fact is checked at it.
4. `warband.py probe`. Relay what the machine holds (a running server, a migration on the stack from a worktree that is not in this raid). It becomes a shared fact.
5. `warband.py classify`. It says `solo` or `collaborative`, where the answer came from (`config`, `local config` or `inferred` from 90 days of authors and the reviews on merged PRs) and, on a collaborative project, the team's hours. Relay it in one line and ask the user to confirm it with AskUserQuestion when it is inferred; a correction goes to `warband.py start --collaboration <mode>` in step 5 and is offered to the config as `collaboration` (mode and hours) so the next raid has it. The mode drives the rest: on a collaborative project step 3 reads every convention file and the PR template, since they bound the raid; on a solo one the global config is usually the whole of it and step 3 is short. Raiders read it from the raid record: their PR watcher holds outside the team's hours on a collaborative project and covers checks alone on a solo one.

## Step 2: Choose the tasks

With task ids given, use them. Without, look for a roadbook CLI in order: `$HOME/.claude/marketplace/goblin-scout/scripts/roadbook.py`, then `$HOME/.claude/plugins/marketplaces/goblin-mode/marketplace/goblin-scout/scripts/roadbook.py`. Found and `.claude/roadbook.json` present (or `.claude/roadmaps.json` in a repository not yet moved; warband.py reads `roadbook.json` first and falls back to `roadmaps.json`): `roadbook.py ready --json`, show the candidate waypoints as `id · description · unblocks n · milestone` and ask with AskUserQuestion (multi-select) which ones raid together. No roadbook: ask for the tasks as free text, one line each.

For each task, read enough of the codebase to answer: which files it will touch, which of those another chosen task also touches, whether it needs a migration, which shared resources it will need. Two tasks on one file, function or table is the thing this raid exists to manage: list every overlap.

## Step 3: Conventions and facts

1. Read every file in the config's `conventions` list. Distil the rules this raid leans on (where a task runs commands, how PRs land, what regenerates, what never goes on a branch).
2. Read the config's `facts` list: the user's own words for conventions not written in the repository.
3. Anything the orders will need to state that neither source holds (a changelog rule, an env-file layout, a merge order) is **asked** with AskUserQuestion now, never asserted. Offer to add the answer to the config's `facts` so the next raid has it; edit the config only on a yes.

## Step 4: Plan, then confirm

Build the table: task, title, branch (project naming: `feat/`, `fix/`, lowercase, hyphens), worktree name (`<task id lowercased without the dot>-<two words>`, under the config's `worktrees.dir`), migration timestamp if needed (the config's `migrations.timestamp_format`, one per task, in the merge order you propose, distinct by at least an hour), the shared resources each will need, and the model and effort the session launches on with the reason in one line.

**Model and effort.** `sonnet` at `medium` unless there is a reason you can write in one line, and that line goes on the launch tribute and in the orders' Model row. Reasons that earn `opus` at `high`: an adversarial review, a design still open, a shared surface other tasks lean on, a migration. Nothing else does. The flags go on the launch line: `--model` beats the terminal's `ANTHROPIC_MODEL`, so the session runs the model this table says whatever the terminal would default to; `--effort` beats the settings but not `CLAUDE_CODE_EFFORT_LEVEL`, so the effort holds unless that variable is exported in the launching terminal. The join-raid skill inherits both rather than setting its own.

Ask two things with AskUserQuestion:

1. **The plan**: approve, or change the merge order, a branch name or a task.
2. **PR approval**: `the chief reviews each draft PR description and the raider runs pr-create auto (Recommended)` or `the user approves pr-create in each session, as before`. The first removes a visit per session; the merge stays the user's either way.

Nothing below runs before both answers.

## Step 5: Worktrees and claims

For each task, in the main checkout:

1. `git worktree add -b <branch> <main>/<worktrees.dir>/<name> origin/<base>`. A branch that already exists: `git worktree add <path> <branch>` and say so.
2. `zsh "${CLAUDE_PLUGIN_ROOT}"/scripts/worktree-bootstrap.sh <path>` (it is a zsh script; `sh` fails on its array syntax): symlinks the git-ignored `.env*` files and installs every tracked lockfile. Relay its lines; a `failed` line is reported, not retried.
3. With a roadbook: `roadbook.py claim <id> --assignee "<who>"` **inside the worktree** (the trail lives on the branch). When the config says `claims: "trunk-sync"` (the project's sync writes claims to the trunk), make no claim commit on the branch: the branch would conflict with the sync. Ask the user to confirm that key the first time a raid meets a sync that writes claims to main. Ask who once, for all tasks; never infer a name. Commit with `git commit -m "chore(roadmap): claim <id>" -- .claude/roadbook.json` (or `.claude/roadmaps.json` where the repository has not moved to the new name).
4. `warband.py crew add --task <id> --branch <branch> --worktree <path> --model <model> --effort <effort> --name "<task id lowercased> <two words>" --reason "<the one line from the table>" [--migration <timestamp>] [--group "<group>"] [--unlisted] [--plugin-dir <plugin root>]`; `--group` names the heading the task's PRs sit under on the spoils page (the body or workstream, e.g. `New Zealand`; ask the user once for the set, and two tasks may share one), defaulting to the task id; `--unlisted` for a task the user chose with no waypoint, so nothing later expects a trail or a roadbook row for it; `--plugin-dir` when the plugin is being run from a working tree rather than installed. It composes the raider's launch line and puts it on the tribute list (kind `launch`, `cd <worktree>` first), which is where the user reads it; a second `crew add` for the task replaces the line.

Run `warband.py start --name <raid name> --pr-approval <answer> [--collaboration <mode>]` **before** the first `crew add` (crew add needs a raid); the collaboration flag only when the user corrected step 1's classification. The raid's chief is this session, read from `CLAUDE_CODE_SESSION_ID`.

## Step 6: Decrees, guidance, orders

1. Set every decree with `warband_decree` (one call each). They are numbered in order and land in the ledger and, from its first turn, in every raider's system prompt. The ownership rules from the protocol (one author per shared definition, paste the whole body, second to merge rewrites from trunk, thresholds in one place) become decrees whenever two tasks share code. A shared document is shared by lines, not by rows: two sessions each editing one row of the same table conflict when the rows are adjacent, so the decree names which side rebases and keeps both.
2. Write `<ledger dir>/guidance.md` from `${CLAUDE_PLUGIN_ROOT}/templates/guidance.md`: raiders table, shared facts with where each was read, the decrees list, the resource rules (the config's notes plus what step 1's probe found), the taboos, the conventions. The ledger dir is in `warband.py --json status` as `ledger_dir`.
   A shared generated file (a schema dump, a lockfile, a generated type file) is regenerated whole by the tool that owns it, never hand-picked by hunk: hunks picked to avoid dump noise landed inside the wrong functions in CHIRPdb's `schema.sql` in November 2026. Put that rule in the guidance for any raid that has one.
3. Write one set of orders per task at `<ledger dir>/briefs/<task id>.md` from `${CLAUDE_PLUGIN_ROOT}/templates/brief.md`. Criteria are numbered and each names the decree it leans on. The orders end with the five questions; they are the whole of what the raider is told.
4. Lint both: `~/.claude/library/scripts/slop-scan.py --strict <file>` where that script exists (it is the house style gate); fix every hit.

## Step 7: Hand over

The launch lines are on the slate, not in this chat: step 5's `crew add` put one per raider on the tribute list, numbered, each with `cd <worktree>` first. Tell the user, in two lines: open the slate with `/show-slate`, and run each `launch` tribute **in a new terminal window**, one window per raider, nothing else typed into it afterwards. Each tribute closes by itself when its raider joins; `reconcile` names the number of any still owed.

What the line carries, for when the user asks: `--model` and `--effort` from the plan (the first beats `ANTHROPIC_MODEL`; the second beats the settings but not `CLAUDE_CODE_EFFORT_LEVEL`), a leading `CLAUDE_CODE_SUBAGENT_EFFORT=high` when the raider launches at `low` or `medium` (its subagents would otherwise run at the raider's effort, and the fresh-eyes review in the join-raid skill's step 1b is one of them), `--name`, `--plugin-dir` when step 5 passed it, and the opening prompt. The prompt is what starts the session's first turn. Without it an interactive session sits idle at an empty prompt: the `SessionStart` hook only adds context, and the slate would show the session as `briefing` (reading orders) with nothing happening (this is what the first board-visuals run did).

Then: nothing else is typed into the session. The `SessionStart` hook names the orders and the chief; the mod registers the session on the slate when it starts inside its worktree; the orders tell it to answer the five questions. Invoke `/goblin-warband:lead-raid` for the rest of the raid.

## Red flags

**Never:** start a raid while one is active; state a convention you did not read or hear from the user; create a worktree for a branch checked out elsewhere; infer a trail's assignee; run a gated command from here (the chief has no worktree and no dibs); write orders that ask a raider to run a hosted read or write; skip the PR-approval question (it is the user's choice, and it changes what every raider does at PR time); launch a raider on opus without a reason the orders' Model row carries; print a launch line in chat (the slate has it with its directory and closes it when the raider joins).

<raw-arguments value="$ARGUMENTS" />
