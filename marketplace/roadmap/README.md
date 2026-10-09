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

### 2d. One-Off Utilities

| Situation                               | Skill |
|-----------------------------------------|-------|
| No roadmap yet                          | `/roadmap:create` |
| Half-formed ideas to explore into tasks | `/roadmap:create-interview` |
| Old single-file format detected         | `/roadmap:migrate` |

### 2e. `/ready`: The Ready Set as a Pane

Opens a pane with the ready set in leverage order, the claims in play and each milestone's progress by release tier, read from the `.claude/roadmaps.json` above the session's working directory. Running `/ready` again closes it. It runs inside Claude Code with no turn, so it works while Claude is busy.

| Key | Does |
|---|---|
| `1` to `9` | Picks a ready row. |
| `q w e t y u i o p` | Picks a claim in play, in the order listed. |
| `c` | Claims the picked ready task: asks who is doing it (a name is never inferred or pre-filled), then runs `claim <id> --assignee=<name> --reassign`, so a name typed here replaces any assignee the task already had. The change is in `roadmaps.json`; commit it when you are ready. |
| `a` | Assigns the picked task without starting it, ready or in play: asks who will do it, then runs `assign <id> --assignee=<name>`. Submitting a blank name clears the assignee (`assign <id> --unassign`). |
| `r` | Refreshes from the CLI. |
| Esc, or `/ready` | Closes the pane. |

The pane refreshes itself every two minutes while open and whenever a tool call touches `roadmaps.json` or runs the CLI. It is a tab beside any other pane, `/diff` included: Ctrl+X Tab moves the keyboard between panes, and only one shows at a time. In a fullscreen terminal of 110 columns or more it docks beside the transcript; narrower, it sits above the prompt. Without a roadmap it says so and names `/roadmap:create`.

---

## 3. Concepts

### 3a. Claims

A claim says someone has started a task. The task gains a `started` date, and views show it as in progress while it is todo or blocked (a paused, deferred or finished status wins); its status stays computed, so a claim never changes one.

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
