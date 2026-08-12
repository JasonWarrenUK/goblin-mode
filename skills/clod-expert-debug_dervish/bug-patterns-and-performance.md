# Common Bug Patterns, Performance Debugging, TypeScript Debugging

Detail for `Debugging`.

## Common Bug Patterns

### Race Conditions

**Problem**:
```typescript
// Race: Which finishes first?
fetchUserData(userId);
fetchUserPosts(userId);
render(); // Might render before data arrives
```

**Solution**:
```typescript
const [userData, userPosts] = await Promise.all([
  fetchUserData(userId),
  fetchUserPosts(userId)
]);
render(userData, userPosts);
```

### Stale Closures

**Problem**:
```svelte
<script>
  let count = 0;

  function startTimer() {
    setInterval(() => {
      console.log(count); // Always logs 0 (stale closure)
      count++;
    }, 1000);
  }
</script>
```

**Solution**:
```svelte
<script>
  let count = 0;

  function startTimer() {
    setInterval(() => {
      count = count + 1; // Access current value via update
    }, 1000);
  }
</script>
```

### Undefined Reference Errors

**Problem**:
```typescript
const name = user.profile.name; // Cannot read property 'name' of undefined
```

**Solution**:
```typescript
// Optional chaining
const name = user?.profile?.name;

// With default
const name = user?.profile?.name ?? 'Unknown';
```

### Memory Leaks

**Problem**:
```svelte
<script>
  import { onMount } from 'svelte';

  onMount(() => {
    const interval = setInterval(() => {
      // Do work
    }, 1000);
    // Never cleaned up! Memory leak
  });
</script>
```

**Solution**:
```svelte
<script>
  import { onMount } from 'svelte';

  onMount(() => {
    const interval = setInterval(() => {
      // Do work
    }, 1000);

    return () => clearInterval(interval); // Cleanup
  });
</script>
```

## Performance Debugging

### Identify Slow Operations

```typescript
function measurePerformance(label, fn) {
  const start = performance.now();
  const result = fn();
  const end = performance.now();
  console.log(`${label}: ${(end - start).toFixed(2)}ms`);
  return result;
}
```

### Find Memory Leaks

**Chrome DevTools Memory Tab**:
1. Take heap snapshot
2. Perform action
3. Take another snapshot
4. Compare snapshots
5. Look for growing objects

## TypeScript Debugging

### Type Errors as Debugging Aid

```typescript
// TypeScript catches bugs at compile time
function getUser(id: string): User {
  return fetchUser(id); // Error: fetchUser expects number
  // Bug found before runtime!
}
```

### Type Narrowing

```typescript
function processValue(value: string | number) {
  if (typeof value === 'string') {
    console.log(value.toUpperCase());
  } else {
    console.log(value.toFixed(2));
  }
}
```
