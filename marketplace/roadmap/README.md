# Roadmap Plugin

## 1. Install

```sh
claude plugin marketplace add JasonWarrenUK/goblin-mode
claude plugin install roadmap@goblin-mode
```

Requires `python3` (3.8+, stdlib only) on `PATH`. The `/ready` pane needs Claude Code 2.1.287 or later and draws in the terminal; the skills work on any version.

---

## 2. Skills

### 2a. Working from the Roadmap

| Situation                       | Skill |
|---------------------------------|-------|
| Choose the next task (one pick) | `/roadmap:next-suggest` |
| See the whole ready-set         | `/roadmap:next-group` |

### 2b. Updating the Roadmap

| Situation                                             | Skill |
|-------------------------------------------------------|-------|
| Add a task, a chain of tasks or a milestone           | `/roadmap:update-tasks` |
| Tasks need owners, or a dev's load needs handing over | `/roadmap:update-devs` |
| You are starting a task, or dropping one | `/roadmap:claim [<task id>] [<assignee>\|release]` |

### 2c. Maintaining the Roadmap

| Situation                                                              | Skill |
|------------------------------------------------------------------------|-------|
| Work landed / statuses drifted (add `reconcile` to check against code) | `/roadmap:maintain` |
| Priorities, freshness or dependency-graph review                       | `/roadmap:review` |
| Render the HTML dashboard                                              | `/roadmap:dashboard` |
| Write the dashboard somewhere other than the default path              | `/roadmap:configure artefact <path> [phase]` |

### 2d. One-Off Utilities

| Situation                               | Skill |
|-----------------------------------------|-------|
| No roadmap yet                          | `/roadmap:create` |
| Half-formed ideas to explore into tasks | `/roadmap:create-interview` |
| Old single-file format detected         | `/roadmap:migrate` |

### 2e. `/ready`: The Ready Set as a Pane

Opens a pane with the whole ready set, the claims in play and each milestone's progress by release tier, read from the `.claude/roadmaps.json` above the session's working directory. Running `/ready` again closes it. It runs inside Claude Code with no turn, so it works while Claude is busy.

The ready set is split into subgroups, by dev unless you change it, each subgroup in leverage order. Every ready task draws; when the list outgrows the pane the body scrolls (the arrow keys while the pane has the keyboard, or the wheel). The digits follow the drawn order, so the subgroups you put first take `1` upwards.

| Key | Does |
|---|---|
| `1` to `9` | Picks one of the first nine ready rows. Rows past the ninth have no digit; Tab reaches them. |
| `q w e t y u i o p` | Picks a claim in play, in the order listed. |
| `c` | Claims the picked ready task: asks who is doing it (a name is never inferred or pre-filled), then runs `claim <id> --assignee=<name> --reassign`, so a name typed here replaces any assignee the task already had. The change is in `roadmaps.json`; commit it when you are ready. |
| `a` | Assigns the picked task without starting it, ready or in play: asks who will do it, then runs `assign <id> --assignee=<name>`. Submitting a blank name clears the assignee (`assign <id> --unassign`). |
| `g` | Cycles what the ready set is grouped by: dev, milestone, tier, nothing. |
| `s` | Asks which subgroups lead, as a comma-separated list of names or ids (`Jason, unassigned`; `M8`; `secondary`), matched without regard to case. The rest follow in natural order: devs alphabetically with the unassigned last, milestones by number, tiers lowest first. A blank answer restores the natural order. |
| `r` | Refreshes from the CLI. |
| Esc, or `/ready` | Closes the pane. |

The grouping and the order are kept in the plugin's own store on your machine, never in the roadmap, so each dev's pane remembers their own: Jaz's can lead with Jaz while Jason's leads with Jason, from the same `roadmaps.json`.

The pane refreshes itself every two minutes while open and whenever a tool call touches `roadmaps.json` or runs the CLI. It is a tab beside any other pane, `/diff` included: Ctrl+X Tab moves the keyboard between panes, and only one shows at a time. In a fullscreen terminal of 110 columns or more it docks beside the transcript; narrower, it sits above the prompt. Without a roadmap it says so and names `/roadmap:create`.

### 2f. The workflow, start to finish

| Moment | What you run | What it writes |
|---|---|---|
| A project with no roadmap | `/roadmap:create`, or `/roadmap:migrate` for an old single-file one | `.claude/roadmaps.json`, the PHASE task list and the overview |
| Ideas to turn into tasks | `/roadmap:create-interview`, then its approved batch through `/roadmap:update-tasks` | tasks with ids, dependencies wired both ways |
| One task you can already state | `/roadmap:update-tasks` | the task, asking its assignee as it goes |
| Owners | `/roadmap:update-devs` | `assignee` on each task; no `started` |
| Picking what to do | `/ready` (the pane), `/roadmap:next-suggest` or `/roadmap:next-group` | nothing |
| Starting a task | the branch hook's question, `c` on `/ready` or `/roadmap:claim <id>` | `started` and `assignee` on the task, committed |
| Dropping a task | `/roadmap:claim <id> release` | `started` removed |
| Work lands | `pr-land` stamps `ended` on what the PR finished (`stamp-ended`); then `/roadmap:maintain` | statuses recomputed, every projection and the dashboard refreshed |
| Statuses look wrong against the code | `/roadmap:maintain reconcile` | the same, after reading the codebase |
| Now and then | `/roadmap:review` | nothing until you approve its edits |
| The dashboard elsewhere | `/roadmap:configure artefact <path>`, then `/roadmap:dashboard` | the phase's `artefact` option and the HTML file |

**The CLI by hand.** `python3 <plugin-root>/scripts/roadmap.py <subcommand>` from anywhere under the project. The ones you will type yourself: `ready`, `open`, `stats`, `validate`, `claim <id> --assignee <name>`, `assign <id> (--assignee <name> | --unassign)`, `release <id>`, `end <id>`, `recompute [--check] [--render]`, `render`, `graph --mermaid`, `config artefact <path>`, `backfill-ended --dry-run`. `--help` lists the rest. With several active phases every subcommand needs `--phase <name>`; it never guesses.

### 2g. Do not

- **Do not edit a task's `status` by hand.** Status is computed from the graph and `recompute` (which `maintain` runs) writes it back; a hand-set status is overwritten, and a held one (`paused`, `deferred`, `out_of_scope`) is the only kind that sticks.
- **Do not mark work done by editing the file.** `/roadmap:maintain` after the merge; `pr-land` stamps the `ended` dates.
- **Do not add a task or a dependency by editing the JSON.** `/roadmap:update-tasks` assigns the id and wires the edge in both directions; a one-sided edge fails `validate`.
- **Do not use `assign` to mean start.** `assign` sets an owner; `claim` records a start. The pane's `a` and `c` keep them apart for the same reason.
- **Do not infer or pre-fill who is doing a task.** Every claim path asks; a name never comes from the branch, the git author or the last claim.
- **Do not silence the branch question by ignoring it.** `git config branch.<name>.roadmapClaim none` is the switch for a branch that is not roadmap work.
- **Do not commit a `recompute` that changes the dashboard without the re-rendered dashboard in the same commit** where the project checks it in; `recompute --render` does both.
- **Do not run with two active phases and no `--phase`.** The CLI stops rather than guess.
- **Do not keep the pane's grouping in the roadmap.** It lives in the plugin's store per machine, which is why two devs can order the same file differently.

---

## 3. Concepts

### 3a. Claims

A claim says someone has started a task. The task gains a `started` date, and views show it as in progress while it is todo or blocked (a paused, deferred or finished status wins); its status stays computed, so a claim never changes one. A blocked task can be claimed when every task or milestone member blocking it is already claimed in the same file (work stacked on the work that unblocks it); a gate always refuses.

You rarely claim by hand. When a branch appears (from a git command or a worktree, or one you made just before) or a session starts on a branch that claims nothing, the plugin has Claude ask one question: which ready task this is, who is doing it and whether to push the branch so the team sees the claim. Nothing is written until you answer. To claim or drop a task yourself, run `/roadmap:claim`: it lists the ready tasks when you give no ID, asks who is doing it and commits the change.

| To                              | Run |
|---------------------------------|-----|
| Claim by hand (no skill)        | `python3 <plugin-root>/scripts/roadmap.py claim <ID> [--assignee NAME]` |
| Assign without claiming         | `python3 <plugin-root>/scripts/roadmap.py assign <ID> (--assignee NAME \| --unassign)` |
| Drop a claim (no skill)         | `python3 <plugin-root>/scripts/roadmap.py release <ID> [--unassign]` |
| Stop the question on one branch | `git config branch.<name>.roadmapClaim none` |

The hooks need `python3` too; without it they stay silent.

---

## 4. Where Do I Find...?

### 4a. Within a Roadmap Project

| File                    | Path                              | Notes |
|-------------------------|-----------------------------------|-------|
| Roadmap Source of Truth | `<project>/.claude/roadmaps.json` | every skill finds it by walking up from the working directory |

### 4b. Within the Plugin

| File                | Path |
|---------------------|------|
| Roadmap Conventions | `references/roadmap-conventions.md` |
| The CLI every skill and the pane run | `scripts/roadmap.py`; `python3 -m unittest test_roadmap` in that directory runs its tests |
| The pane's code | `hooks/register.tsx`; `claude plugin test <plugin-root>` runs its tests |
