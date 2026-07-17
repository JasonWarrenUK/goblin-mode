← [Wiki home](../README.md)

# Agents

Agents (`agents/*.md`) are autonomous multi-step workflows Claude delegates to. Each runs in its own context window with its own model, spawned when Claude recognises a matching situation from the agent's `description` — not invoked with a slash command the way [command skills](skills.md#command-skills) are.

See [Skills vs Agents](skills.md#skills-vs-agents) for how the two systems divide responsibility.

## The ten agents

| Agent | Model | Purpose | Invoke with |
|---|---|---|---|
| `session-orchestrator` | Sonnet | Builds a ranked work plan at session start from project context, task-tracker state, open branches, and roadmap priorities. Primes the session on selection (sets task-tracker status, checks out the branch). | "What should I work on?" or `SessionStart` |
| `project-context-loader` | Sonnet | Rebuilds mental context when switching projects — git history, architectural decisions, current work state. | "What's the state of this project?" / "Catch me up on X" |
| `implementation-planner` | Opus | Breaks a vague development request into a detailed, actionable implementation plan. | A feature request that needs structuring |
| `design-reviewer` | Opus | Reviews a proposed feature against design values: sophistication, empowerment, robustness, ethics, explainability. | "Review this design" / "Does this approach hold up?" |
| `scope-guard` | Sonnet | Proactively monitors scope during planning and implementation — plan step count, branch diff vs. stated task, drift. | "Is this getting too big?" / "Check scope" |
| `test-gap-scanner` | Sonnet | Identifies undertested code via risk-based prioritisation (impact × complexity × change frequency) against the branch diff. | "What should I test?" or as a subagent of `ship-checker` |
| `ship-checker` | Opus | Multi-dimensional pre-ship check: branch readiness, test gaps, doc staleness, breaking changes, task-tracker state, into one ready/not-ready verdict. | "Am I ready to ship?" / "check this branch" |
| `task-sync` | Sonnet | Keeps the task tracker (see [Task Trackers](task-trackers/README.md) for supported sources) consistent with git/branch state. | "sync tasks" or as a subagent |
| `roadmap-maintainer` | Opus | Keeps documentation and roadmaps aligned with actual code changes. | After significant progress, or a roadmap/doc request |
| `session-closer` | Haiku | End-of-session wrap-up: summarises accomplishments, notes uncommitted work, updates task status, writes a handoff note. | "I'm done for today" / "wrap up" or `SessionEnd` |

## The two loops

These agents were designed as a pair of loops (see [design history](../design-history/agent-workflow-design.md) for the original proposal — all six new agents it specified have since shipped).

**The session loop:**

```
session-orchestrator ──→ (pick a task) ──→ implementation
        │                                       │
        │                                scope-guard monitors
        │                                       │
        │                                 ship-checker
        │                                       │
        │                                session-closer
        │                                       │
        └───────────── next session ←───────────┘
```

**The shipping loop:**

```
"Am I ready?" ──→ ship-checker
                      │
             ┌────────┼─────────┐
             ▼        ▼         ▼
      test-gap-scanner  task-sync  doc staleness check
             │        │         │
             └────────┼─────────┘
                       ▼
               verdict + action items
```

## Subagent relationships

```
session-orchestrator
├── project-context-loader
└── task-sync

ship-checker
├── test-gap-scanner
└── task-sync

session-closer
└── task-sync
```

`scope-guard` and `task-sync` also run standalone, event-driven rather than only as subagents.

## When to create a new agent

Agents solve *process* problems, not *knowledge* problems (that's what [role skills](skills.md#role-skills) are for). If a workflow requires autonomous investigation across multiple steps — not just following a fixed template — and you keep doing it inconsistently or skipping it, that's an agent candidate.

---
← [Wiki home](../README.md) · [Skills](skills.md) · [Hooks](hooks.md) · [Architecture](../architecture.md)
