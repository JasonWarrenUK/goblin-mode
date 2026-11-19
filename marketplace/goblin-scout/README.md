# goblin-scout

*Scouted it, wrote it in the roadbook, lost the pencil. It keeps your plan as a map of what waits on what.*

goblin-scout keeps a **roadbook**: a project's plan as a dependency graph in `.claude/roadbook.json`. Its words, used everywhere you read them:

| Word | Means |
|---|---|
| waypoint | a task (`tasks` in the JSON) |
| scout | the person doing a waypoint (`assignee`) |
| trail | a waypoint someone has started (`started` set) |
| expedition | a planned batch of new waypoints |
| the chart | the rendered HTML page of a phase |

Phases and milestones keep their names. The JSON field names are unchanged, so a collaborator reading the file sees `tasks` and `assignee`.

## 1. Install

```sh
claude plugin marketplace add JasonWarrenUK/goblin-mode
claude plugin install goblin-scout@goblin-mode
```

Requires `python3` (3.8+, stdlib only) on `PATH`. The `/scout-waypoints` pane needs Claude Code 2.1.287 or later and draws in the terminal; the skills work on any version.

### 1a. Coming from the roadmap plugin (2.x)

goblin-scout 3.0.0 is the roadmap plugin renamed. The marketplace's `renames` map moves your `enabledPlugins` entry across. A project's `.claude/roadmaps.json` keeps working: goblin-scout reads it where it is, and its first write moves it to `.claude/roadbook.json` (and a `roadmaps.local.json` beside it to `.claude/roadbook.local.json`) with a line of notice. No value in the file is rewritten; the live phase is stamped so a 2.x plugin refuses the moved file, and the chart, projections and overview stay at their old paths. The one exception is a phase in the local file with no chart path of its own: its chart renders to the new default name from then on, the notice names each such phase and `rebind --outputs` moves its old chart across. `/goblin-scout:rebind-roadbook` does the move on request, and with `outputs` moves those three to the roadbook's names in one commit.

| Was | Is |
|---|---|
| `/ready` | `/scout-waypoints` |
| `roadmap:create`, `create-interview`, `update-tasks`, `update-devs`, `claim` | `goblin-scout:start-roadbook`, `plan-expedition`, `add-waypoints`, `assign-scouts`, `start-trail` |
| `roadmap:next-suggest`, `next-group`, `maintain`, `review` | `goblin-scout:suggest-waypoint`, `survey-waypoints`, `tend-roadbook`, `review-roadbook` |
| `roadmap:dashboard`, `configure`, `migrate` | `goblin-scout:unroll-chart`, `configure-roadbook`, `rebind-roadbook` |
| `scripts/roadmap.py` | `scripts/roadbook.py`, every subcommand and flag unchanged |
| `branch.<name>.roadmapClaim` | `branch.<name>.roadbookClaim`; the old key is still honoured |

---

## 2. Skills

### 2a. Working from the Roadbook

| Situation                           | Skill |
|-------------------------------------|-------|
| Choose the next waypoint (one pick) | `/goblin-scout:suggest-waypoint` |
| See every ready waypoint            | `/goblin-scout:survey-waypoints` |

### 2b. Updating the Roadbook

| Situation                                                    | Skill |
|--------------------------------------------------------------|-------|
| Add a waypoint, a chain of them or a milestone               | `/goblin-scout:add-waypoints` |
| Waypoints need scouts, or a scout's load needs handing over  | `/goblin-scout:assign-scouts` |
| You are starting a waypoint, or dropping one                 | `/goblin-scout:start-trail [<waypoint id>] [<scout>\|release]` |

### 2c. Tending the Roadbook

| Situation                                                              | Skill |
|------------------------------------------------------------------------|-------|
| Work landed / statuses drifted (add `reconcile` to check against code) | `/goblin-scout:tend-roadbook` |
| Priorities, freshness or dependency-graph review                       | `/goblin-scout:review-roadbook` |
| Render the chart                                                       | `/goblin-scout:unroll-chart` |
| Write the chart somewhere other than the default path                  | `/goblin-scout:configure-roadbook artefact <path> [phase]` |

### 2d. One-Off Utilities

| Situation                                                  | Skill |
|------------------------------------------------------------|-------|
| No roadbook yet                                            | `/goblin-scout:start-roadbook` |
| Half-formed ideas to explore into an expedition            | `/goblin-scout:plan-expedition` |
| Old single-file roadmap, or a 2.x `roadmaps.json` to move  | `/goblin-scout:rebind-roadbook` |

### 2e. `/scout-waypoints`: The Ready Waypoints as a Pane

Opens a pane with every ready waypoint, the trails in play and each milestone's progress by release tier, read from the `.claude/roadbook.json` above the session's working directory. Running `/scout-waypoints` again closes it. It runs inside Claude Code with no turn, so it works while Claude is busy. The header card carries the phase's facts on its left and the mod's wordmark, `S C O U T` between two rules, on its right; below 24 cells of room for the facts the wordmark steps aside.

The ready set is split into subgroups, by scout unless you change it, each subgroup in leverage order. Every ready waypoint draws; when the list outgrows the pane the body scrolls (the arrow keys while the pane has the keyboard, or the wheel). The digits follow the drawn order, so the subgroups you put first take `1` upwards.

| Key | Does |
|---|---|
| `1` to `9` | Picks one of the first nine ready rows. Rows past the ninth have no digit; Tab reaches them. |
| `q w e t y u i o p` | Picks a trail in play, in the order listed. |
| `c` | Starts a trail on the picked ready waypoint: asks which scout (a name is never inferred or pre-filled), then runs `claim <id> --assignee=<name> --reassign`, so a name typed here replaces any assignee the waypoint already had. The change is in `roadbook.json`; commit it when you are ready. |
| `a` | Assigns the picked waypoint without starting it, ready or on a trail: asks which scout will take it, then runs `assign <id> --assignee=<name>`. Submitting a blank name clears the assignee (`assign <id> --unassign`). |
| `g` | Cycles what the ready set is grouped by: scout, milestone, tier, nothing. |
| `s` | Asks which subgroups lead, as a comma-separated list of names or ids (`Jason, unassigned`; `M8`; `secondary`), matched without regard to case. The rest follow in natural order: scouts alphabetically with the unassigned last, milestones by number, tiers lowest first. A blank answer restores the natural order. |
| `r` | Refreshes from the CLI. |
| Esc, or `/scout-waypoints` | Closes the pane. |

The grouping and the order are kept in the plugin's own store on your machine, never in the roadbook, so each scout's pane remembers their own: noor's can lead with noor while Jason's leads with Jason, from the same `roadbook.json`. The store is the plugin's, so a grouping kept under the 2.x roadmap plugin starts afresh.

The pane refreshes itself every two minutes while open and whenever a tool call touches `roadbook.json` (or a not-yet-moved `roadmaps.json`) or runs the CLI. It is a tab beside any other pane, `/diff` included: Ctrl+X Tab moves the keyboard between panes, and only one shows at a time. In a fullscreen terminal of 110 columns or more it docks beside the transcript; narrower, it sits above the prompt. Without a roadbook it says so and names `/goblin-scout:start-roadbook`.

### 2f. The workflow, start to finish

| Moment | What you run | What it writes |
|---|---|---|
| A project with no roadbook | `/goblin-scout:start-roadbook`, or `/goblin-scout:rebind-roadbook` for an old single-file roadmap | `.claude/roadbook.json`, the phase's waypoint list and the overview |
| Ideas to turn into waypoints | `/goblin-scout:plan-expedition`, then its approved batch through `/goblin-scout:add-waypoints` | waypoints with ids, dependencies wired both ways |
| One waypoint you can already state | `/goblin-scout:add-waypoints` | the waypoint, asking its scout as it goes |
| Scouts | `/goblin-scout:assign-scouts` | `assignee` on each waypoint; no `started` |
| Picking what to do | `/scout-waypoints` (the pane), `/goblin-scout:suggest-waypoint` or `/goblin-scout:survey-waypoints` | nothing |
| Starting a waypoint | the branch hook's question, `c` on `/scout-waypoints` or `/goblin-scout:start-trail <id>` | `started` and `assignee` on the waypoint, committed |
| Dropping a trail | `/goblin-scout:start-trail <id> release` | `started` removed |
| Work lands | `pr-land` stamps `ended` on what the PR finished (`stamp-ended`); then `/goblin-scout:tend-roadbook` | statuses recomputed, every projection and the chart refreshed |
| Statuses look wrong against the code | `/goblin-scout:tend-roadbook reconcile` | the same, after reading the codebase |
| Now and then | `/goblin-scout:review-roadbook` | nothing until you approve its edits |
| The chart elsewhere | `/goblin-scout:configure-roadbook artefact <path>`, then `/goblin-scout:unroll-chart` | the phase's `artefact` option and the HTML file |

**The CLI by hand.** `python3 <plugin-root>/scripts/roadbook.py <subcommand>` from anywhere under the project. The ones you will type yourself: `ready`, `open`, `stats`, `validate`, `claim <id> --assignee <name>`, `assign <id> (--assignee <name> | --unassign)`, `release <id>`, `end <id>`, `recompute [--check] [--render]`, `render`, `graph --mermaid`, `config artefact <path>`, `backfill-ended --dry-run`, `rebind [--outputs] [--dry-run]`. `--help` lists the rest. With several active phases every subcommand needs `--phase <name>`; it never guesses.

### 2g. Do not

- **Do not edit a waypoint's `status` by hand.** Status is computed from the graph and `recompute` (which `tend-roadbook` runs) writes it back; a hand-set status is overwritten, and a held one (`paused`, `deferred`, `out_of_scope`) is the only kind that sticks.
- **Do not mark work done by editing the file.** `/goblin-scout:tend-roadbook` after the merge; `pr-land` stamps the `ended` dates.
- **Do not add a waypoint or a dependency by editing the JSON.** `/goblin-scout:add-waypoints` assigns the id and wires the edge in both directions; a one-sided edge fails `validate`.
- **Do not use `assign` to mean start.** `assign` names a scout; `claim` starts a trail. The pane's `a` and `c` keep them apart for the same reason.
- **Do not infer or pre-fill which scout is on a waypoint.** Every path that starts a trail asks; a name never comes from the branch, the git author or the last trail.
- **Do not silence the branch question by ignoring it.** `git config branch.<name>.roadbookClaim none` is the switch for a branch that is not roadbook work.
- **Do not commit a `recompute` that changes the chart without the re-rendered chart in the same commit** where the project checks it in; `recompute --render` does both.
- **Do not run with two active phases and no `--phase`.** The CLI stops rather than guess.
- **Do not keep the pane's grouping in the roadbook.** It lives in the plugin's store per machine, which is why two scouts can order the same file differently.

---

## 3. Concepts

### 3a. Trails

A trail says a scout has started a waypoint. The waypoint gains a `started` date, and views show it as in progress while it is todo or blocked (a paused, deferred or finished status wins); its status stays computed, so starting a trail never changes one. A blocked waypoint can take a trail when every waypoint or milestone member blocking it is already on a trail in the same file (work stacked on the work that unblocks it); a gate always refuses.

You rarely start a trail by hand. When a branch appears (from a git command or a worktree, or one you made just before) or a session starts on a branch that claims nothing, the plugin has Claude ask one question: which ready waypoint this is, which scout is on it and whether to push the branch so the team sees the trail. Nothing is written until you answer. To start or drop a trail yourself, run `/goblin-scout:start-trail`: it lists the ready waypoints when you give no ID, asks which scout and commits the change.

| To                              | Run |
|---------------------------------|-----|
| Start a trail by hand (no skill) | `python3 <plugin-root>/scripts/roadbook.py claim <ID> [--assignee NAME]` |
| Assign without starting         | `python3 <plugin-root>/scripts/roadbook.py assign <ID> (--assignee NAME \| --unassign)` |
| Drop a trail (no skill)         | `python3 <plugin-root>/scripts/roadbook.py release <ID> [--unassign]` |
| Stop the question on one branch | `git config branch.<name>.roadbookClaim none` |

The hooks need `python3` too; without it they stay silent.

---

### 3b. Mirrored Phases

When a tracker is the source of truth, a phase can mirror it. `python3 <plugin-root>/scripts/roadbook.py pull --project <JIRA KEY> --name "<phase name>"` reads a Jira project and writes `.claude/roadbook.local.json`, a roadbook file kept out of git that every command and skill then finds first. Plain `pull` refreshes it and never writes to Jira.

Releases (fix versions) become milestones, epics become topics, issues become waypoints under their Jira keys and Blocks links become dependencies, so `ready`, `stats`, the graph and the chart work as they do anywhere. Trails are switched off for mirrored waypoints: status, dates and assignee come from Jira. Your own waypoints go in beside them with `"local": true`; a pull never touches those, nor the `notes` and `pr` you put on a mirrored waypoint. Projects without a local file behave exactly as before. The full rules are under Mirrored phases in `references/roadbook-conventions.md`.

## 4. Where Do I Find...?

### 4a. Within a Roadbook Project

| File                     | Path                              | Notes |
|--------------------------|-----------------------------------|-------|
| Roadbook source of truth | `<project>/.claude/roadbook.json` | every skill finds it by walking up from the working directory; a 2.x `roadmaps.json` is found too until its first write moves it |
| The chart                | `docs/artefacts/chart-<phase>.html` | a phase's `artefact` option overrides it; a project moved from 2.x keeps `roadmap-<phase>.html` |

### 4b. Within the Plugin

| File                | Path |
|---------------------|------|
| Roadbook conventions | `references/roadbook-conventions.md` |
| The CLI every skill and the pane run | `scripts/roadbook.py`; `python3 -m unittest test_roadbook test_roadbook_jira` in that directory runs its tests |
| The pane's code | `hooks/register.tsx`; `claude plugin test <plugin-root>` runs its tests |
| The chart's template and look | `templates/chart.html`, the goblin theme copied as `templates/chart-theme.css` and the embedded faces in `templates/fonts/` |

The plugin is Zlib-licensed. The faces embedded in every chart keep their own licences, each file beside its face in `templates/fonts/`: Cabin Sketch, IBM Plex Mono and IBM Plex Sans are under the SIL Open Font License 1.1; Special Elite and Permanent Marker are under the Apache License 2.0. All five are the latin subsets of the @fontsource 5.3.0 packages.
