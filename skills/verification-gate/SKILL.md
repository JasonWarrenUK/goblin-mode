---
name: verification-gate
description: This skill should be used when the agent is about to claim something is "done", "fixed", "working", "complete", "implemented", "resolved", "ready", or any variant thereof. Also triggers on phrases like "should work now", "I'm confident", "that should do it", "I believe this fixes", or when the conversation reaches a natural completion point for a task. Enforces evidence-based completion claims.
version: 1.0.0
---

# Verification Gate

Hard gate on completion claims. You do not get to say something works until you've proved it works. "I'm confident this fixes it" is not evidence. Running the code and showing the output is evidence.

This skill operationalises the CLAUDE.md rule: **"Never commit code that hasn't been verified."**

---

## When This Skill Applies

This skill fires **every time** the agent is about to:
- Claim a task is complete
- Say a bug is fixed
- Declare a feature is working
- Mark a todo item as done
- Suggest the user review or merge something
- Use any language implying "finished"

**No exceptions.** Not for small changes. Not for "obvious" fixes. Not for typos. The gate is the gate.

---

## The Verification Gate

Before ANY completion claim, pass all 5 steps. No skipping.

### Step 1: State What Was Changed

List every file modified, created, or deleted. Not "updated the component" — the actual file paths and what changed in each.

### Step 2: State the Expected Behaviour

What should happen now that didn't happen before? Or what should stop happening? Be specific. "It works" is not a behaviour description.

### Step 3: Produce Fresh Evidence

**Run something.** The evidence must be:
- **Fresh** — generated after the change, not before
- **Observable** — output the agent can show, not just assert
- **Relevant** — directly demonstrates the expected behaviour

Valid evidence:
- Test output (ran the tests, they pass)
- Build output (compiled without errors)
- Command output (ran the thing, got the right result)
- Type-check output (tsc reports no errors)
- Manual verification steps with observed results

Invalid evidence:
- "The code looks correct"
- "Based on my understanding..."
- "This should resolve..."
- "I'm confident that..."
- Referencing tests that weren't actually run

### Step 4: Check for Regressions

Did the fix break anything else? Evidence required here too:
- Run the full test suite, not just the changed test
- Check that related functionality still works
- If no test suite exists, state that explicitly and describe what was manually verified

### Step 5: State Completion with Evidence Reference

Only now may you claim completion. The claim must reference the evidence:

```
✓ Fixed: [description]
  Evidence: [test output / build output / manual verification]
  Regressions: [test suite passed / manually verified X, Y, Z]
```

---

## Anti-Rationalisation Table

The agent will generate excuses to skip verification. Here are the pre-written rebuttals.

| Excuse | Rebuttal |
|--------|----------|
| "It's a trivial change" | Trivial changes cause production outages. Verify it. |
| "I just changed a string/comment" | Then verification takes 5 seconds. Do it. |
| "The type system guarantees correctness" | The type system guarantees type correctness. Run the code. |
| "I can see from the code that it works" | You can see from the code that it *should* work. That's not the same thing. |
| "There are no tests to run" | Then describe what you manually verified. Or write a test. |
| "Running tests would take too long" | Skipping tests takes longer when the bug ships. Run them. |
| "The change is identical to a pattern used elsewhere" | Identical patterns in different contexts produce different bugs. Verify. |
| "I already verified a similar change earlier" | Earlier evidence is stale. This is a different change. Fresh evidence required. |
| "The user asked me to move fast" | Moving fast without verification is moving fast toward a rollback. |

---

## Banned Completion Phrases

These phrases are **never acceptable** as standalone completion claims:

- "Should work now"
- "I'm confident this fixes..."
- "That should do it"
- "I believe this resolves..."
- "This looks correct"
- "The issue should be resolved"
- "I've made the necessary changes"
- "Everything should be in order"

Each of these is a **claim without evidence**. Replace with evidence, then state the conclusion the evidence supports.

---

## Integration Points

### With testing-obsessive
Testing-obsessive tells you *how* to test. Verification gate tells you *that you must* test. Testing-obsessive provides methodology; this skill provides discipline.

### With systematic-debugger
The debugger's Step 4 (Verify) aligns with this gate. When debugging, the verification gate ensures you don't skip the debugger's final step.

### With git-manager
No commit should pass without the verification gate clearing first. The git workflow should include verification evidence in commit context.

### With scope-coach
Scope coach may reduce what you build. Verification gate ensures that whatever you *did* build actually works. Smaller scope doesn't mean lower verification standards.

---

## Success Criteria

The verification gate is working when:
- Every completion claim includes observable evidence
- "Should work" never appears without evidence following it
- Tests are run, not just written
- Regressions are checked, not assumed absent
- The agent's completion claims are trustworthy because they're backed by proof
