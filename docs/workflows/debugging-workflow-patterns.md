# Debugging Workflow Patterns

> **Purpose**: Establish systematic approaches to debugging code, tests, performance, and production issues
>
> **Context**: Effective debugging requires structured methodology, not random trial-and-error. This document defines repeatable patterns for different debugging scenarios.

---

## Current State

### Debugging Approaches You Likely Use
Based on common developer patterns:
- Console.log debugging (quick but messy)
- Browser DevTools (for frontend issues)
- Git bisect (for finding when bugs were introduced)
- Stack trace analysis (for errors)
- Test failures (when tests exist)

### Common Pain Points
1. **Random debugging** - No systematic approach, leads to wasted time
2. **Lost context** - Forget what you've tried when debugging drags on
3. **Insufficient data** - Not capturing enough information upfront
4. **Repeat issues** - Same bugs resurface because root cause wasn't addressed
5. **No documentation** - Solutions aren't recorded for future reference

---

## Debugging Methodology: The Five-Step Pattern

### Universal Debugging Framework

```
1. REPRODUCE → Make the bug happen reliably
2. ISOLATE   → Narrow down where the problem is
3. DIAGNOSE  → Understand why it's happening
4. FIX       → Implement the solution
5. VERIFY    → Confirm the fix works and doesn't break anything
```

This pattern applies to **every** debugging scenario.

---

## Project Type Detection

Your projects use different runtimes (npm, bun, deno). Use this pattern to detect which one:

```bash
# Detect project type by checking for lockfiles/config
detect_runtime() {
  if [ -f "bun.lockb" ]; then
    echo "bun"
  elif [ -f "deno.json" ] || [ -f "deno.lock" ]; then
    echo "deno"
  elif [ -f "package-lock.json" ]; then
    echo "npm"
  elif [ -f "pnpm-lock.yaml" ]; then
    echo "pnpm"
  elif [ -f "yarn.lock" ]; then
    echo "yarn"
  else
    echo "npm"  # default
  fi
}

RUNTIME=$(detect_runtime)
```

Use this pattern throughout debugging workflows to run the correct commands.

---

## Scenario 1: Runtime Errors

### When: Application crashes, throws exceptions, errors in logs

**Reproduce**:
```typescript
// Capture the exact error
try {
  problematicCode();
} catch (error) {
  console.error('Full error:', error);
  console.error('Stack trace:', error.stack);
  console.error('Context:', { relevantVariables });
}
```

**Isolate**:
1. Identify the exact line from stack trace
2. Check what values led to the error
3. Verify inputs and state at failure point

**Diagnose**:
- Is it a type error? (accessing undefined, wrong type)
- Is it a logic error? (wrong condition, off-by-one)
- Is it an environment issue? (missing config, wrong permissions)

**Fix**:
- Add validation before the error point
- Handle the error case explicitly
- Fix the root cause (not just the symptom)

**Verify**:
```typescript
// Add test case for the error scenario
it('should handle [error case]', () => {
  expect(() => problematicCode(badInput)).toThrow('Expected error');
});
```

---

## Scenario 2: Test Failures

### When: Unit tests, integration tests, or E2E tests fail

**Reproduce**:
```bash
# Detect runtime and run failing test in isolation
if [ -f "bun.lockb" ]; then
  bun test path/to/failing.test.ts
elif [ -f "deno.json" ] || [ -f "deno.lock" ]; then
  deno test path/to/failing.test.ts
else
  npm test path/to/failing.test.ts
fi

# Run with verbose output
if [ -f "bun.lockb" ]; then
  bun test path/to/failing.test.ts --verbose
elif [ -f "deno.json" ] || [ -f "deno.lock" ]; then
  deno test path/to/failing.test.ts --allow-all
else
  npm test -- --verbose path/to/failing.test.ts
fi

# Run in watch mode for rapid iteration
if [ -f "bun.lockb" ]; then
  bun test --watch path/to/failing.test.ts
elif [ -f "deno.json" ] || [ -f "deno.lock" ]; then
  deno test --watch path/to/failing.test.ts
else
  npm test -- --watch path/to/failing.test.ts
fi
```

Or use your shell aliases:
```bash
nT path/to/failing.test.ts   # npm test
bT path/to/failing.test.ts   # bun test
dTest path/to/failing.test.ts # deno test
```

**Isolate**:
1. Read the test failure message carefully
2. Identify what the test expected vs what it got
3. Check if test is correct or implementation is wrong

**Diagnose**:
```typescript
// Add debug output in the test
it('should do something', () => {
  const result = functionUnderTest(input);
  console.log('Input:', input);
  console.log('Result:', result);
  console.log('Expected:', expectedOutput);
  expect(result).toEqual(expectedOutput);
});
```

**Common test failure causes**:
- Async timing issues (missing `await`)
- Mock not configured correctly
- Test environment differs from production
- Shared state between tests
- Flaky test (passes sometimes, fails others)

**Fix**:
- Fix the implementation if test is correct
- Fix the test if implementation is correct
- Add better assertions for clarity
- Isolate test setup/teardown

**Verify**:
```bash
# Run the test multiple times to ensure stability
for i in {1..10}; do
  if [ -f "bun.lockb" ]; then
    bun test path/to/test.ts || break
  elif [ -f "deno.json" ]; then
    deno test path/to/test.ts || break
  else
    npm test path/to/test.ts || break
  fi
done
```

---

## Scenario 3: Logic Bugs (Wrong Behavior)

### When: Code runs but produces wrong results

**Reproduce**:
```typescript
// Create minimal reproduction
function reproduce() {
  const input = getMinimalFailingInput();
  const actual = buggyFunction(input);
  const expected = correctOutput;
  
  console.log('Input:', input);
  console.log('Actual:', actual);
  console.log('Expected:', expected);
  console.log('Match:', actual === expected);
}
```

**Isolate**:
- Add breakpoints or console.logs at each step
- Check intermediate values
- Verify assumptions about data flow

**Diagnose using scientific method**:
```typescript
// Hypothesis: The bug is in the calculation step
function debugCalculation(data) {
  console.log('Before calculation:', data);
  const result = calculate(data);
  console.log('After calculation:', result);
  console.log('Expected:', expectedResult);
  return result;
}
```

**Fix patterns**:
- Off-by-one: Check loop bounds and array indices
- Wrong condition: Verify boolean logic (`&&` vs `||`, `!==` vs `===`)
- State mutation: Check for unintended side effects
- Edge cases: Test boundaries (empty, null, max values)

**Verify**:
```typescript
// Add test for the specific bug
it('should handle [specific case that was broken]', () => {
  const input = reproduceBugInput;
  expect(buggyFunction(input)).toEqual(correctOutput);
});
```

---

## Scenario 4: Performance Issues

### When: Code is slow, freezes, or times out

**Reproduce**:
```typescript
// Measure performance
console.time('operation');
slowFunction();
console.timeEnd('operation');

// Measure with more detail
const start = performance.now();
slowFunction();
const end = performance.now();
console.log(`Took ${end - start}ms`);
```

**Isolate**:
```typescript
// Use browser profiler or runtime profiler
// In browser: Performance tab in DevTools
// In Node/Bun: node --prof / bun --inspect
// In Deno: deno run --inspect

// Binary search: Comment out halves of code to find slow section
```

**Diagnose**:
Common performance killers:
- **N+1 queries**: Database query in a loop
- **Large data processing**: Processing arrays/objects without pagination
- **Synchronous operations**: Blocking the main thread
- **Memory leaks**: Not cleaning up listeners/timers
- **Inefficient algorithms**: O(n²) where O(n) possible

**Fix patterns**:
```typescript
// Before: O(n²) - nested loops
for (const item of list1) {
  for (const match of list2) {
    if (item.id === match.id) { /* ... */ }
  }
}

// After: O(n) - hash map lookup
const map = new Map(list2.map(item => [item.id, item]));
for (const item of list1) {
  const match = map.get(item.id);
  if (match) { /* ... */ }
}
```

**Verify**:
```typescript
// Benchmark before and after
console.time('before');
slowFunction();
console.timeEnd('before');

console.time('after');
fastFunction();
console.timeEnd('after');
```

---

## Scenario 5: Production Issues

### When: Bug only happens in production, not locally

**Reproduce**:
```bash
# Check production logs
# Look for error patterns
# Identify affected users/requests

# Try to reproduce locally with production-like conditions:
# - Same runtime version
# - Same environment variables
# - Same data volume
# - Same external service states
```

**Isolate**:
1. Check what's different between local and production
   - Environment variables
   - Data volume/characteristics
   - External service availability
   - Timing/race conditions
   - Browser/client differences

2. Add detailed logging (temporarily)
```typescript
// Add structured logging for diagnosis
logger.info('Processing request', {
  userId,
  requestId,
  timestamp: Date.now(),
  context: relevantData
});
```

**Diagnose**:
- Review production logs around error time
- Check monitoring dashboards (if available)
- Verify database state
- Check external service status
- Look for resource exhaustion (memory, CPU, connections)

**Fix**:
```typescript
// Add defensive code for production edge cases
try {
  await externalService.call();
} catch (error) {
  logger.error('External service failed', { error, context });
  // Graceful degradation or retry logic
  return fallbackBehavior();
}
```

**Verify**:
```typescript
// Deploy to staging first
// Test with production-like data
// Monitor closely after production deploy
// Add alerting for recurrence
```

---

## Debugging Tools & Techniques

### Browser DevTools (Frontend)
```javascript
// Breakpoints
debugger; // Stops execution here

// Conditional breakpoints
// Right-click in Sources tab → Add conditional breakpoint
// Condition: userId === '123'

// Console methods
console.log('Basic output');
console.table(arrayOfObjects); // Formatted table
console.trace(); // Show call stack
console.time('label'); console.timeEnd('label'); // Timing

// Network tab
// Check request/response payloads
// Look for failed requests
// Verify headers and status codes
```

### Git Bisect (Find When Bug Was Introduced)
```bash
# Start bisect session
git bisect start
git bisect bad                    # Current commit is bad
git bisect good <commit>          # Known good commit

# Git will checkout commits to test
# For each commit, detect runtime and test:
if [ -f "bun.lockb" ]; then
  bun test && git bisect good || git bisect bad
elif [ -f "deno.json" ]; then
  deno test && git bisect good || git bisect bad
else
  npm test && git bisect good || git bisect bad
fi

# Git will narrow down to the problematic commit
git bisect reset                  # Exit bisect mode
```

### TypeScript Type Debugging
```typescript
// Reveal the actual type
type Debug<T> = T extends infer U ? U : never;
type Revealed = Debug<ComplexType>; // Hover to see actual type

// Force type errors to see what TypeScript infers
const test: never = someValue; // Error shows actual type
```

### Binary Search Debugging
```typescript
// Comment out half the code
// Does bug still happen?
// - Yes: Bug is in uncommented half
// - No: Bug is in commented half
// Repeat until you find the exact line
```

### Runtime-Specific Debugging

**Deno**:
```bash
# Debug with Chrome DevTools
deno run --inspect-brk your-script.ts

# Then open chrome://inspect in Chrome
```

**Bun**:
```bash
# Debug with built-in debugger
bun --inspect your-script.ts

# Hot reload during debugging
bun --hot your-script.ts
```

**Node/npm**:
```bash
# Debug with Chrome DevTools
node --inspect-brk your-script.js

# Debug with VS Code/Zed built-in debugger
```

---

## Creating a Debugging Skill

### Skill Definition

Create `/Users/jasonwarren/.claude/skills/debugging/SKILL.md`:

**Purpose**: Provide systematic debugging methodology and common patterns

**Key patterns**:
- Five-step universal framework (Reproduce → Isolate → Diagnose → Fix → Verify)
- Scenario-specific strategies
- Runtime detection for polyglot projects
- Tool recommendations
- Common pitfalls and solutions

**Auto-invoked when**:
- User mentions "bug", "error", "broken", "failing"
- Test failures discussed
- Performance issues mentioned
- Production issues reported

**Integration with workflow**:
- Work records should document debugging sessions
- ADRs should capture decisions made during debugging
- Tests should be added for fixed bugs

---

## Debugging Checklist

When you encounter a bug, use this checklist:

### Before You Start
- [ ] Can you reproduce it reliably?
- [ ] Have you captured the error message/stack trace?
- [ ] Do you know when it started happening?
- [ ] Is it affecting other users/systems?

### During Debugging
- [ ] Have you isolated the problem area?
- [ ] Have you checked your assumptions?
- [ ] Have you reviewed recent changes (git log)?
- [ ] Have you tried the simplest fix first?
- [ ] Are you documenting what you've tried?

### After Fixing
- [ ] Does the fix address the root cause?
- [ ] Have you added a test to prevent regression?
- [ ] Have you verified it doesn't break anything else?
- [ ] Have you documented the solution?
- [ ] Should this be shared with the team?

---

## Common Anti-Patterns to Avoid

### ❌ Random Changes
**Bad**: "Let me try changing this and see if it works"  
**Good**: "Based on the error, I hypothesize X is the cause. Let me test that."

### ❌ No Reproduction
**Bad**: "It happened once, let me try to fix it"  
**Good**: "Let me create a minimal test case that reproduces the issue"

### ❌ Masking Errors
**Bad**: `try { risky(); } catch { /* ignore */ }`  
**Good**: `try { risky(); } catch (error) { log(error); handleGracefully(); }`

### ❌ No Documentation
**Bad**: Fix the bug and move on  
**Good**: Add test, update docs, record decision if significant

### ❌ Runtime Assumptions
**Bad**: `npm test` (assumes npm)  
**Good**: Detect runtime first, then use appropriate command

---

## Debugging Script Helper

Create a reusable debugging helper:

```bash
# ~/bin/debug-test
#!/bin/bash

# Detect runtime and run tests with useful debugging flags
detect_and_test() {
  local test_path="$1"
  
  if [ -f "bun.lockb" ]; then
    echo "🔍 Running bun tests..."
    bun test --watch "$test_path"
  elif [ -f "deno.json" ] || [ -f "deno.lock" ]; then
    echo "🔍 Running deno tests..."
    deno test --watch --allow-all "$test_path"
  else
    echo "🔍 Running npm tests..."
    npm test -- --watch "$test_path"
  fi
}

detect_and_test "$@"
```

Usage:
```bash
chmod +x ~/bin/debug-test
debug-test path/to/failing.test.ts
```

---

## Next Steps

1. Create debugging skill in `~/.claude/skills/debugging/SKILL.md`
2. Add debugging patterns to work record template
3. Practice five-step method on next bug
4. Create `debug-test` helper script
5. Consider creating slash command for debugging assistance

---

## Related Files

- Evidence tracking: `~/.claude/docs/evidence-tracker.md`
- Work records: `~/.claude/doc-templates/work-record.md`
- Testing skill: `~/.claude/skills/testing-foundations/SKILL.md`
- Pre-push hook: `~/.claude/hooks/pre-push-tests` (uses same runtime detection)
