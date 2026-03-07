# Agent & Workflow Design Analysis

Analysis of the workflows this repo encodes, and proposals for agents and subagents that would benefit a developer using this setup.

---

## Workflows Identified

### 1. Task Selection → Implementation → Shipping

The most common loop. Currently handled by a loose chain:

```
/suggest:task → (manual decision) → /linear:tackle → implementation-planner agent
→ coding → /git:commit → /git:assess-branch → /git:pr → /linear:hoover
```

**Gap:** No orchestration between these steps. The developer is the glue. Each transition requires a conscious decision, which is exactly the kind of executive function tax this setup was built to reduce.

### 2. Context Switching Between Projects

Currently: `project-context-loader` agent rebuilds mental context.

**Gap:** The context loader produces a briefing but doesn't prime the session. After reading the briefing, the developer still has to manually decide what to work on, check Linear, review open branches — all things that could cascade from the context load.

### 3. Documentation Maintenance

Currently: `post-commit-docs` hook detects staleness, `roadmap-maintainer` agent handles doc updates, various `/doc:*` commands create docs.

**Gap:** Documentation is reactive (triggered by commits) rather than integrated into the dev loop. The `roadmap-maintainer` agent and the doc commands operate independently — no workflow connects "I finished a feature" to "update the roadmap, write the work record, check if the README is stale."

### 4. Quality Gates Before Shipping

Currently: `pre-push-tests` hook catches untested code, `/git:assess-branch` checks PR readiness, `design-reviewer` agent evaluates designs.

**Gap:** These are isolated checkpoints. A developer can (and will, with ADHD) skip the design review, go straight to implementation, and only hit quality gates at push time — when the cost of rework is highest.

### 5. Linear ↔ Codebase Synchronisation

Currently: `/linear:tackle` fetches a task, `/linear:hoover` scans for addressed issues, `/linear:crit-path-to` decomposes projects.

**Gap:** Linear status updates are manual. The `CLAUDE.md` says to set status to "In Progress" when starting and "In Review" when a PR is created, but nothing enforces this beyond the developer remembering.

### 6. Scope Discipline

Currently: `scope-coach` skill fires on keywords, `implementation-planner` includes a scope check.

**Gap:** Scope coaching is reactive — it fires when you say "overwhelmed" but not when your plan quietly grows to 15 steps. There's no proactive check that compares plan complexity against the original ask.

---

## Proposed Agents

### Agent 1: `session-orchestrator`

**Model:** Sonnet
**Purpose:** Runs at session start (or on demand) and builds a work plan for the session.

**What it does:**
1. Spawns `project-context-loader` as subagent to get project state
2. Queries Linear for assigned/in-progress tasks
3. Checks for open branches with uncommitted work
4. Cross-references roadmap priorities against Linear backlog
5. Presents a ranked list of 2-3 things to work on, with time estimates
6. On selection, primes the session — sets Linear status, checks out the right branch, loads relevant context

**Subagents:**
- `project-context-loader` (existing) — project state
- `task-sync` (new, see below) — task state from whatever tracker the project uses

**Why:** Eliminates the "staring at the screen wondering what to do" problem. Collapses 4-5 manual steps (check Linear, check branches, check roadmap, decide, context-switch) into one invocation. Directly addresses task initiation difficulty.

**Trigger:** `SessionStart` hook or explicit invocation ("what should I work on?").

---

### Agent 2: `task-sync`

**Model:** Sonnet
**Purpose:** Keeps task tracker state consistent with git/codebase state. Adapts to the project's task source — Linear, GitHub Issues, or git-native (branch conventions + local state).

**What it does:**
- Detects task source: checks project config, then probes for Linear CLI, GitHub remote, or falls back to git-native
- On branch checkout → sets matching task to "In Progress"
- On PR creation → sets matching tasks to "In Review"
- On merge to main → sets tasks to "Done" (with confirmation)
- Detects orphaned "In Progress" tasks with no matching branch
- Detects branches with no matching task (suggests creating one)

**Task sources:**
- **Linear**: Full status management via Linear API/CLI
- **GitHub Issues**: Labels and PR linking via `gh` CLI
- **Git-native**: Branch state + `.claude/session-state.json` as the sole source of truth

**Subagents:** None — lightweight, event-driven.

**Why:** The existing `/linear:hoover` command does retrospective matching, but status management is entirely manual. This agent makes whatever task tracker is in use a reliable source of truth instead of a stale backlog. Projects without Linear still get task awareness through GitHub Issues or git conventions.

**Trigger:** `PostToolUse` hook on git commands (branch, commit, push), or as a subagent of `session-orchestrator`.

---

### Agent 3: `ship-checker`

**Model:** Opus
**Purpose:** Runs a multi-dimensional quality check before shipping, combining checks that are currently separate.

**What it does:**
1. Runs `/git:assess-branch` logic (commit quality, branch naming, diff size)
2. Checks for untested code paths (overlaps with `pre-push-tests`, but earlier in the loop)
3. Scans for documentation staleness (same logic as `post-commit-docs`, but proactive)
4. Checks for breaking changes and flags them with the `BREAKING CHANGE:` format
5. Validates tasks/issues are linked and status is correct (via task-sync)
6. Produces a single "ready/not ready" verdict with prioritised action items

**Subagents:**
- `test-gap-scanner` (new, see below) — identifies untested code
- `task-sync` — validates task/issue state

**Why:** Currently the developer has to remember to run `/git:assess-branch`, and separately rely on hooks to catch test gaps and doc staleness. This collapses the entire "am I ready to ship?" question into one agent that front-loads the checks. Finding problems before `git push` instead of during it.

**Trigger:** Explicit invocation ("am I ready to ship?", "check this branch"), or automatically when conversation suggests shipping intent (keywords: "PR", "merge", "push", "ship").

---

### Agent 4: `test-gap-scanner`

**Model:** Sonnet
**Purpose:** Identifies code that should have tests but doesn't, using the risk-based framework from the `testing-obsessive` skill.

**What it does:**
1. Reads the diff (branch vs main) to identify changed/new code
2. Applies the risk matrix from `testing-obsessive`: impact × complexity × change frequency
3. Cross-references against existing test files
4. Produces a prioritised list: "must test", "should test", "can skip"
5. For "must test" items, generates test file stubs with describe blocks and test names

**Subagents:** None.

**Why:** The `pre-push-tests` hook detects untested files, but it fires at push time and only checks for file existence. This agent applies the actual testing philosophy encoded in the skill — risk-based prioritisation, not "does a .test.ts file exist?" It turns a binary check into a nuanced recommendation that matches how you want to think about testing.

**Trigger:** As a subagent of `ship-checker`, or explicit invocation ("what should I test?").

---

### Agent 5: `scope-guard`

**Model:** Sonnet
**Purpose:** Proactive scope monitoring that fires during planning and implementation, not just when the developer says "overwhelmed."

**What it does:**
1. Monitors implementation plans for step count (>7 steps = warning)
2. Compares current branch diff against the original Linear issue scope
3. Detects "scope drift" — when the branch touches files unrelated to the stated task
4. Applies the scope-coach patterns: "What's the smallest version that delivers value?"
5. Suggests splitting into multiple PRs when scope has grown

**Subagents:** None — lightweight analysis.

**Why:** The `scope-coach` skill is reactive (keyword-triggered). This agent is proactive — it watches what's happening and intervenes before scope creep becomes entrenched. The difference between "I feel overwhelmed" (late) and "this plan has 12 steps, which 4 deliver the core?" (early).

**Trigger:** `PostToolUse` hook on Edit/Write operations (monitors implementation growth), or as a check within `implementation-planner`.

---

### Agent 6: `session-closer`

**Model:** Haiku
**Purpose:** End-of-session wrap-up that captures state for next time.

**What it does:**
1. Summarises what was accomplished (from git log since session start)
2. Notes any uncommitted work or half-finished branches
3. Updates task status if work is paused mid-task (via task-sync)
4. Generates a work record entry (reuses `/doc:create:work-record` logic)
5. Flags any documentation reminders that were deferred
6. Writes a brief "next session" note to the project context

**Subagents:**
- `task-sync` — ensure task tracker state is current

**Why:** Session endings are where context gets lost. The developer closes the terminal, and tomorrow everything starts from scratch. This agent creates a handoff note — whether to your future self or to the `session-orchestrator` agent that will run at the start of the next session. Directly addresses the "20 minutes reading git logs before writing a line of code" problem described in the README.

**Trigger:** `SessionEnd` hook, or explicit ("I'm done for today", "wrap up").

---

## Orchestration Model

These agents form two loops:

### The Session Loop

```
session-orchestrator ──→ (dev selects task) ──→ implementation
        │                                           │
        │                                    scope-guard monitors
        │                                           │
        │                                     ship-checker
        │                                           │
        │                                    session-closer
        │                                           │
        └───────────── next session ←───────────────┘
```

### The Shipping Loop

```
"Am I ready?" ──→ ship-checker
                      │
                ┌─────┼──────────┐
                ▼     ▼          ▼
          test-gap  task-sync    doc staleness
          scanner   validation   check
                │     │          │
                └─────┼──────────┘
                      ▼
              verdict + action items
                      │
               ┌──────┴──────┐
               ▼              ▼
            "Ready"      "Needs work"
               │              │
          /git:pr        fix + re-check
```

### Subagent Relationships

```
session-orchestrator
├── project-context-loader (existing)
└── task-sync

ship-checker
├── test-gap-scanner
└── task-sync

session-closer
└── task-sync

scope-guard (standalone, event-driven)
task-sync (standalone, event-driven, also used as subagent — adapts to Linear/GitHub Issues/git-native)
test-gap-scanner (standalone, also used as subagent)
```

---

## Implementation Priority

Ordered by impact ÷ effort, accounting for the specific friction points this setup was built around:

| Priority | Agent | Rationale |
|----------|-------|-----------|
| 1 | `task-sync` | Highest reuse (3 agents depend on it), solves a daily friction point, low complexity, works across all projects regardless of tracker |
| 2 | `session-orchestrator` | Directly addresses task initiation and context-switching — the two costliest ADHD tax points |
| 3 | `session-closer` | Completes the session loop; cheap to build (Haiku, mostly summarisation) |
| 4 | `ship-checker` | Consolidates existing scattered checks; moderate complexity |
| 5 | `test-gap-scanner` | Valuable but narrow scope; can exist as a standalone command first |
| 6 | `scope-guard` | Most architecturally complex (requires PostToolUse monitoring); high value but defer until the event-driven pattern is proven with `task-sync` |

---

## Model Tier Assignments

| Agent | Model | Justification |
|-------|-------|---------------|
| `session-orchestrator` | Sonnet | Coordination, not deep analysis |
| `task-sync` | Sonnet | API calls and pattern matching; task source detection adds minimal overhead |
| `ship-checker` | Opus | Needs to reason about code quality, breaking changes, and architectural concerns |
| `test-gap-scanner` | Sonnet | Risk assessment against a defined matrix — structured, not creative |
| `scope-guard` | Sonnet | Pattern matching against known signals |
| `session-closer` | Haiku | Summarisation from git log — mechanical, not analytical |

---

## Design Principles Applied

These proposals follow the repo's own stated principles:

- **Friction-driven:** Each agent traces to a specific gap identified in the existing workflow, not speculative design
- **Context window discipline:** Agents run as subprocesses. Only descriptions load into the main session
- **Model tier thinking:** Each agent uses the cheapest model that can do the job
- **Weakness-aware:** `test-gap-scanner` and `scope-guard` exist because testing and scope discipline are self-identified weaknesses
- **Organic growth:** The priority order allows building one at a time, starting with the highest-leverage, lowest-risk addition (`task-sync`)

---

## Open Questions

1. **`PostToolUse` monitoring cost:** `scope-guard` running on every Edit/Write could be noisy. Should it batch analysis (every N edits) or run on explicit checkpoints?
2. **`task-sync` automation level:** Should status changes be automatic or confirmed? Automatic reduces friction but risks wrong matches. A hybrid (auto for obvious matches, confirm for fuzzy ones) might be the pragmatic middle.
3. **`session-orchestrator` vs. enhanced `SessionStart` hook:** Could the session orchestrator be a hook rather than an agent? Hooks are lighter but less capable. An agent can investigate; a hook follows a script.
4. **Agent memory:** `session-closer` and `session-orchestrator` form a pair — one writes state, the other reads it. Should they share a memory directory, or should state transfer happen through a file convention (e.g., `.claude/session-state.json`)?
