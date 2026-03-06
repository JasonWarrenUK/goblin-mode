---
name: subagent-executor
description: This skill should be used when the agent is about to execute a multi-step implementation plan, build a large feature, work through a task list with more than 3 steps, or when the user says "build this", "implement the plan", "execute", "work through these tasks", "start building". Also applies when the agent has just finished planning (via implementation-planner or manually) and is transitioning to execution. Enforces disciplined execution with review gates.
version: 1.0.0
---

# Subagent Executor

Disciplined execution of multi-step plans. Takes the output of planning (from implementation-planner agent, brainstorming-gate, or manual planning) and executes it with review checkpoints, not as one uninterrupted stream of code.

The problem this solves: agents plan well but execute badly. They start strong, drift from the spec by step 4, and by step 7 they're solving a different problem. This skill forces checkpoint discipline.

---

## When This Skill Applies

Use this skill when:
- Executing a plan with 4+ steps
- Building a feature that touches 3+ files
- Working through a task list or implementation sequence
- Transitioning from planning to building
- The implementation-planner agent has produced a plan
- A brainstorming-gate session has concluded with an approved design

**Does NOT apply to:**
- Single-file changes
- Bug fixes (use systematic-debugger instead)
- Quick refactors under 3 steps
- Documentation-only changes

---

## Execution Model

### Batch Execution

Group plan steps into **batches of 2-3 related tasks**. Never execute the entire plan as one continuous stream.

```
Plan: 8 steps total

Batch 1: Steps 1-2 (data model + migration)
  → Review Gate
Batch 2: Steps 3-4 (API endpoints)
  → Review Gate
Batch 3: Steps 5-6 (UI components)
  → Review Gate
Batch 4: Steps 7-8 (integration + tests)
  → Review Gate + Final Review
```

### Why Batches?

- **Drift detection**: Catch spec divergence early, not after 8 steps
- **Course correction**: User can redirect before wasted work compounds
- **Context preservation**: Each batch starts with clear intent
- **Evidence accumulation**: Verification gate applies per batch, not just at the end

---

## Review Gates

After each batch, pause and run this checklist. Do not proceed until it clears.

### Gate 1: Spec Compliance Review

Compare what was built against what was planned:

```
Batch N Complete — Spec Compliance:
  Planned: [what the plan said to do]
  Built: [what was actually built]
  Drift: [any differences — even minor ones]
  Decision: [proceed / adjust / revert]
```

**If drift detected:**
- Minor drift (naming differences, slightly different approach): flag it, proceed if equivalent
- Moderate drift (extra features added, scope expanded): stop, consult user
- Major drift (solving a different problem): revert batch, re-read the plan

### Gate 2: Code Quality Review

Quick quality check — not a full code review, but enough to catch rot early:

- [ ] Changes follow existing project patterns?
- [ ] No `any` types introduced?
- [ ] No hardcoded values that should be configurable?
- [ ] Error handling present at boundaries?
- [ ] No TODO comments left without corresponding tasks?

### Gate 3: Verification (delegates to verification-gate skill)

Run the verification gate for the batch. Evidence required before proceeding.

---

## Blocker Protocol

When something doesn't work as expected during execution:

### Hard Rule: Stop Immediately

Do **not**:
- Guess at a fix and continue
- Work around the blocker with a hack
- Skip the blocked step and come back to it
- Assume the blocker will resolve itself

**Do**:
1. State what's blocked and why
2. Show the error or unexpected behaviour
3. Propose 1-2 approaches to unblock
4. Wait for direction (or apply systematic-debugger if it's a bug)

### Anti-Rationalisation Table

| Excuse | Rebuttal |
|--------|----------|
| "I'll come back to this later" | Later never comes. The hack you write now becomes permanent. Stop and fix. |
| "It's probably fine, let me continue" | "Probably fine" is how tech debt is born. Verify or stop. |
| "I can work around this" | Workarounds compound. One workaround creates two more. Address the root cause. |
| "This is a minor issue" | Minor issues in step 3 become major issues by step 7. Fix it now. |
| "The user probably wants me to keep going" | The user wants working software, not fast-but-broken software. Pause. |
| "I'll just add a TODO" | TODOs are where good intentions go to die. Fix it or flag it as a blocker. |

---

## Fresh Context Per Batch

Each batch should begin with a brief re-orientation:

```
--- Batch N: [description] ---
Plan context: [what the overall plan is achieving]
Previous batches: [what's been built so far]
This batch: [specific steps being executed]
Dependencies: [what this batch relies on from previous batches]
```

This prevents the drift that happens when execution continues on autopilot without reconnecting to the plan.

---

## Subagent Delegation

For complex batches, delegate to a subagent (via the Agent tool):

**When to delegate:**
- Batch involves deep research (exploring unfamiliar APIs, reading docs)
- Batch is self-contained and doesn't need main conversation context
- Parallel execution possible (two independent batches)

**When NOT to delegate:**
- Batch requires user decisions
- Batch depends on conversation context not captured in the plan
- The task is simple enough that delegation overhead exceeds the work

**Delegation format:**
```
Delegating Batch N to subagent:
  Task: [precise description]
  Inputs: [files, context, constraints]
  Expected output: [what the subagent should produce]
  Review: [will review output before integrating]
```

Always review subagent output before integrating. Subagents don't have full conversation context — they may solve the wrong problem.

---

## Final Review

After all batches complete, run a final review that covers the entire implementation:

1. **Plan vs Reality**: Walk through the original plan. Was everything built? What changed and why?
2. **Integration Check**: Do all the pieces work together, not just individually?
3. **Full Verification Gate**: Run the complete test suite, not just per-batch tests
4. **Regression Sweep**: Check that pre-existing functionality still works
5. **Summary**: Concise list of what was built, what was deferred, what needs follow-up

---

## Integration Points

### With implementation-planner agent
The planner produces the plan; this skill executes it. The handoff should be explicit: "Plan complete. Switching to execution mode."

### With verification-gate
The verification gate fires at every review gate checkpoint, not just at final completion. Each batch must clear verification before the next begins.

### With brainstorming-gate
If brainstorming produced an approved design, the executor takes that design as its spec. Spec compliance reviews compare against the brainstorming output.

### With scope-coach
If execution reveals unexpected complexity, scope coach may fire to suggest cutting scope. The executor should respect scope reductions — update the remaining batches accordingly.

---

## Success Criteria

The subagent executor is working when:
- Multi-step implementations don't drift from their plan
- Blockers are caught and addressed at batch boundaries, not at the end
- Each batch has its own verification evidence
- The user has visibility into progress at natural checkpoints
- Subagent delegation is used strategically, not reflexively
- Final output matches the plan (or divergences are documented and justified)
