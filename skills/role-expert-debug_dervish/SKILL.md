---
name: Debugging
description: Systematic debugging methodology — runtime errors, test failures, logic bugs, performance issues, production incidents. Five-step framework, root-cause analysis, browser/Node/Svelte tooling, and common bug patterns.
when_to_use: "When something is broken and the cause isn't obvious yet — an error, a failing test, unexpected behaviour, or a performance regression that needs systematic root-causing rather than guessing."
user-invocable: false
---

# Systematic Debugging

Methodical approach to identifying and fixing software issues. Emphasises reproducibility, isolation, and verification over trial-and-error debugging. Covers browser DevTools, Node debugging, logging strategies, and Svelte-specific debugging techniques.

## When This Skill Applies

Use this skill when:

- User reports something "not working"
- Investigating errors or unexpected behaviour
- Performance issues need diagnosis
- Setting up debugging infrastructure
- Explaining debugging approaches
- Teaching debugging techniques
- Questions about DevTools or debugging tools

## The Debugging Methodology

**Five-step process**: Reproduce → Isolate → Diagnose → Fix → Verify

This applies to every debugging scenario without exception.

### 1. Reproduce

**Make the bug happen reliably**

Can't fix what you can't reproduce. First priority is finding reliable steps to trigger the issue.

**Questions to ask**:
- What exact steps produce the error?
- Does it happen every time or intermittently?
- What's the expected vs actual behaviour?
- What's the minimal reproduction case?

**Document reproduction steps**:

````markdown
## To Reproduce

1. Navigate to `/dashboard`
2. Click "Load More" button
3. Scroll to bottom of page
4. Click "Load More" again

**Expected**: More items load
**Actual**: Page freezes, console shows error
**Frequency**: Happens every time on 2nd click
````

**If intermittent**:
- Look for race conditions
- Check network timing issues
- Consider state-dependent bugs
- Try multiple environments

### 2. Isolate (Root-Cause Depth)

**Narrow down the cause — then go deeper.**

Once reproducible, determine exactly where the problem originates. But don't stop at the first explanation. The first "cause" is often a symptom. Ask **why** repeatedly until you reach the structural root.

**The Five Whys**:

```text
Bug: Users see stale data after updating their profile.

Why? → The cache isn't invalidated after the update.
Why? → The update function doesn't call cache.invalidate().
Why? → The caching layer was added after the update function was written.
Why? → There's no pattern ensuring new writes invalidate related caches.
Root: Missing cache invalidation convention. Fix the convention, not just this instance.
```

**Depth vs speed**: Not every bug warrants five whys. Use your judgement:
- **Shallow fix appropriate**: Typo, wrong variable name, missing null check
- **Deep investigation warranted**: Bug that could recur, affects multiple users, or reveals a pattern gap

**Isolation techniques**:

**Binary search approach**:
````typescript
// Working at line 50?
console.log('Check 1:', data); // ✓ Data good here

// Working at line 75?
console.log('Check 2:', result); // ✗ Result undefined here

// Problem is between lines 50-75
````

**Comment out code**:
````typescript
// Does removing this fix it?
// await someAsyncFunction();

// If yes, problem is in someAsyncFunction
````

**Minimal reproduction**:
````typescript
// Strip away everything non-essential
// Original: 300 lines, complex state, multiple API calls
// Minimal: 20 lines that show the exact issue

async function minimalRepro() {
  const data = await fetch('/api/items');
  console.log(data); // undefined when expected array
}
````

**Check assumptions**:
````typescript
// Assumption: API returns array
console.log(typeof data); // "object" - it's null!

// Assumption: User is logged in
console.log(user); // undefined - not logged in!
````

### 3. Diagnose

**Understand why it's happening**

- Runtime error: Type error, logic error, or environment issue?
- Test failure: Async issues, mock problems, environment differences, shared state?
- Logic bug: Off-by-one, wrong condition, state mutation, edge case?
- Performance: N+1 queries, large data, sync ops, memory leaks, inefficient algorithms?
- Production: Differences between local and production? Check logs, monitoring, external services.

### 4. Fix

**Implement targeted solution**

Now that you know the cause, fix it specifically.

**Fix patterns**:

**Null/undefined checks**:
````typescript
// Before (crashes)
const count = items.length;

// After
const count = items?.length ?? 0;
````

**Async timing**:
````typescript
// Before (race condition)
fetch('/api/data');
renderUI(); // Renders before data arrives

// After
const data = await fetch('/api/data');
renderUI(data);
````

**State initialisation**:
````typescript
// Before (undefined on first render)
let items;

// After
let items = [];
````

**Error boundaries**:
````typescript
// Before (crashes entire app)
const result = riskyOperation();

// After
try {
  const result = riskyOperation();
} catch (error) {
  console.error('Operation failed:', error);
  showErrorToUser('Something went wrong');
}
````

### 5. Verify

**Confirm the fix works**

Don't assume it's fixed. Test thoroughly.

**Verification checklist**:
- ✓ Original reproduction steps no longer produce error
- ✓ Expected behaviour now occurs
- ✓ No new errors introduced
- ✓ Edge cases still work
- ✓ Performance not degraded

**Test edge cases**:
````typescript
// Fixed for normal case, but what about:
- Empty array
- Null values
- Very large datasets
- Network failures
- Simultaneous requests
````

**Write regression test** (see `testing-obsessive` skill):
````typescript
it('should handle second "Load More" click', async () => {
  render(ItemList);

  await clickLoadMore();
  await clickLoadMore(); // This used to crash

  expect(screen.getAllByRole('listitem').length).toBeGreaterThan(10);
});
````

## Additional resources

Tool-specific reference and worked bug patterns, loaded only when needed:

- [tooling.md](tooling.md) — runtime detection, Browser DevTools (Console/Network/Elements/Sources/Application/Performance tabs), Node.js debugging, Svelte-specific debugging (reactive statements, lifecycle, store debugging), logging strategies
- [bug-patterns-and-performance.md](bug-patterns-and-performance.md) — race conditions, stale closures, undefined reference errors, memory leaks, performance profiling, TypeScript debugging

## Root-Cause vs Symptom Fixes

**Symptom fix**: Fixes the immediate problem but doesn't prevent recurrence.
**Root-cause fix**: Addresses the structural issue that allowed the bug to exist.

```typescript
// Symptom fix: Add null check where the crash happens
const name = user?.profile?.name ?? 'Unknown';

// Root-cause fix: Ensure profile is always populated at creation
async function createUser(data: CreateUserRequest): Promise<User> {
	return await db.users.create({
		...data,
		profile: { name: data.name } // Profile guaranteed at creation
	});
}
```

**When to ship a symptom fix**: When the root cause is expensive to fix and the symptom fix is safe. But always log the root cause as a follow-up task.

**When to insist on root-cause fix**: When the bug pattern could recur in other places, when data integrity is at risk, or when the symptom fix introduces its own complexity.

## Debugging Checklist

**Before:**
- [ ] Can you reproduce it?
- [ ] Captured error/stack trace?
- [ ] Know when it started?

**During:**
- [ ] Isolated problem area?
- [ ] Checked assumptions?
- [ ] Reviewed recent changes?
- [ ] Documenting attempts?

**After:**
- [ ] Root cause fixed?
- [ ] Test added?
- [ ] Nothing else broken?
- [ ] Solution documented?
