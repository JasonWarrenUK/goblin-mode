# Runtime Detection, Browser DevTools, Node Debugging, Svelte Debugging, Logging

Detail for `Debugging`.

## Runtime Detection Pattern

Projects use different runtimes (npm, bun, deno). Always detect before running commands:

```bash
if [ -f "bun.lockb" ]; then
  # bun project
elif [ -f "deno.json" ] || [ -f "deno.lock" ]; then
  # deno project
else
  # npm/pnpm/yarn project
fi
```

### Runtime-Specific Debug Commands

**Deno**:
```bash
deno test --watch path/to/test.ts
deno run --inspect-brk script.ts  # Debug with Chrome DevTools
```

**Bun**:
```bash
bun test --watch path/to/test.ts
bun --inspect script.ts  # Debug
bun --hot script.ts      # Hot reload
```

**npm**:
```bash
npm test -- --watch path/to/test.ts
node --inspect-brk script.js  # Debug
```

## Browser DevTools

### Console

**Strategic logging**:
```typescript
// ✗ Bad: Non-informative
console.log(data);

// ✓ Good: Labelled and contextual
console.log('API Response:', data);
console.log('User state before update:', user);

// ✓ Better: Grouped related logs
console.group('Data Processing');
console.log('Input:', rawData);
console.log('Processed:', processedData);
console.log('Output:', finalResult);
console.groupEnd();

// ✓ Advanced: Conditional logging
const DEBUG = true;
DEBUG && console.log('Debug info:', state);

// ✓ Tables for arrays of objects
console.table(users);
```

**Console methods**:
```typescript
console.log('Normal message');
console.info('Informational');
console.warn('Warning - check this');
console.error('Error occurred');
console.debug('Debug details');

// Timing
console.time('operation');
// ... code to measure
console.timeEnd('operation'); // operation: 45.2ms

// Assertions
console.assert(value > 0, 'Value must be positive:', value);

// Count occurrences
console.count('API call'); // API call: 1
console.count('API call'); // API call: 2
```

### Network Tab

**Inspect API requests**:
- Check request URL and method
- Verify headers (Authorization, Content-Type)
- Inspect request payload
- Check response status and body
- Look for failed requests (red)
- Check timing (slow responses)

**Common issues**:
```text
404 Not Found → Check URL spelling, route exists
401 Unauthorized → Check auth token present and valid
500 Server Error → Check server logs, API issue
CORS Error → Check server allows origin
Timeout → API too slow or not responding
```

### Elements Tab

**Inspect DOM**:
- Check element exists
- Verify classes applied
- Check computed styles
- Inspect event listeners
- Modify styles live

**Common CSS issues**:
```css
/* Check computed styles for: */
- Display: none (hidden element)
- Z-index conflicts
- Overflow: hidden (content clipped)
- Position issues
- Flexbox/Grid properties
```

### Sources Tab (Debugger)

**Breakpoints**:
```typescript
function processData(data) {
  // Set breakpoint on this line
  const result = transform(data);

  // Execution pauses, inspect:
  // - data value
  // - Scope variables
  // - Call stack

  return result;
}
```

**Breakpoint types**:
- **Line breakpoints** - Pause at specific line
- **Conditional breakpoints** - Pause only when condition true
- **Logpoints** - Log without stopping execution
- **Exception breakpoints** - Pause on errors

**Debugger controls**:
- **Continue** (F8) - Resume execution
- **Step over** (F10) - Execute current line, don't go into functions
- **Step into** (F11) - Go into function calls
- **Step out** (Shift+F11) - Exit current function

### Application Tab

**Inspect storage**:
- **Local Storage** - Persistent key-value storage
- **Session Storage** - Session-only storage
- **Cookies** - Check authentication cookies
- **IndexedDB** - Client-side database
- **Cache Storage** - Service worker cache

**Common storage issues**:
```typescript
// Check if data stored correctly
localStorage.getItem('user'); // "undefined" as string? null?

// Check cookie domain/path
// Check expiration
// Check HttpOnly/Secure flags
```

### Performance Tab

**Profile performance**:
1. Click record
2. Perform slow action
3. Stop recording
4. Analyse flame chart

**Look for**:
- Long tasks (>50ms)
- Excessive re-renders
- Slow API calls
- Memory leaks (increasing usage)

## Node.js Debugging

### Built-in Debugger

**Start with inspect**:
```bash
node --inspect server.js
# or
node --inspect-brk server.js  # Break on first line
```

**Chrome DevTools**:
1. Open chrome://inspect
2. Click "Open dedicated DevTools for Node"
3. Same interface as browser debugging

### Console Debugging

```typescript
// Strategic placement
async function fetchUserData(userId) {
  console.log('Fetching user:', userId);

  const user = await db.query('SELECT * FROM users WHERE id = ?', [userId]);
  console.log('Query result:', user);

  if (!user) {
    console.log('User not found');
    return null;
  }

  console.log('Returning user:', user);
  return user;
}
```

### Debug Module

```typescript
import debug from 'debug';

const log = debug('app:users');

log('Fetching user %s', userId); // Only shows if DEBUG=app:* enabled

// Enable specific namespaces
// DEBUG=app:users node server.js
// DEBUG=app:* node server.js
// DEBUG=* node server.js
```

## Svelte-Specific Debugging

### Reactive Statements

**Log reactive changes**:
```svelte
<script>
  let count = 0;

  // Debug reactive statement
  $: console.log('Count changed:', count);

  // Debug derived value
  $: doubled = count * 2;
  $: console.log('Doubled:', doubled);

  // Debug with condition
  $: if (count > 10) {
    console.log('Count exceeded threshold');
  }
</script>
```

### Component Lifecycle

```svelte
<script>
  import { onMount, onDestroy, beforeUpdate, afterUpdate } from 'svelte';

  onMount(() => {
    console.log('Component mounted');
    return () => console.log('Component cleanup');
  });

  onDestroy(() => {
    console.log('Component destroyed');
  });

  beforeUpdate(() => {
    console.log('Before DOM update');
  });

  afterUpdate(() => {
    console.log('After DOM update');
  });
</script>
```

### Store Debugging

```typescript
import { writable } from 'svelte/store';

function createDebugStore(name, initial) {
  const store = writable(initial);

  const { subscribe, set, update } = store;

  return {
    subscribe,
    set: (value) => {
      console.log(`${name} set to:`, value);
      set(value);
    },
    update: (fn) => {
      console.log(`${name} updated`);
      update((val) => {
        const newVal = fn(val);
        console.log(`  Old:`, val, `New:`, newVal);
        return newVal;
      });
    }
  };
}

export const userStore = createDebugStore('user', null);
```

### Svelte DevTools

**Browser extension** - Install Svelte DevTools

Features:
- Component tree inspection
- Props and state values
- Store contents
- Event listeners
- Performance profiling

## Logging Strategies

### Log Levels

```typescript
const LOG_LEVELS = {
  ERROR: 0,
  WARN: 1,
  INFO: 2,
  DEBUG: 3
};

const currentLevel = LOG_LEVELS.INFO;

function log(level, message, ...args) {
  if (level <= currentLevel) {
    const prefix = ['ERROR', 'WARN', 'INFO', 'DEBUG'][level];
    console.log(`[${prefix}]`, message, ...args);
  }
}

// Usage
log(LOG_LEVELS.ERROR, 'Failed to load user');
log(LOG_LEVELS.DEBUG, 'Cache hit for key:', key); // Only shows if DEBUG level
```

### Contextual Logging

```typescript
function createLogger(context) {
  return {
    info: (msg, ...args) => console.log(`[${context}]`, msg, ...args),
    error: (msg, ...args) => console.error(`[${context}]`, msg, ...args),
    debug: (msg, ...args) => console.debug(`[${context}]`, msg, ...args)
  };
}

const log = createLogger('UserService');
log.info('Fetching user', userId);
log.error('Failed to fetch', error);
```

### Production Logging

**Don't ship debug logs**:
```typescript
// ✗ Bad: Logs in production
console.log('User clicked button');

// ✓ Good: Conditional logging
if (import.meta.env.DEV) {
  console.log('User clicked button');
}

// ✓ Better: Logging service
logger.info('User action', { action: 'button_click', userId });
```
