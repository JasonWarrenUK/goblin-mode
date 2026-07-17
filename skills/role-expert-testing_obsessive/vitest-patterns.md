# Vitest Setup and Test Patterns

Detail for `testing-obsessive` — mechanical how-to once risk assessment (see SKILL.md) has decided what to test.

## Vitest Setup

### Installation
```bash
npm install -D vitest @vitest/ui
npm install -D @testing-library/svelte @testing-library/jest-dom
```

### Configuration (`vitest.config.ts`)
```typescript
import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte({ hot: !process.env.VITEST })],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['**/*.test.ts', '**/*.spec.ts', '**/types.ts']
    }
  }
});
```

### Setup File (`src/test/setup.ts`)
```typescript
import '@testing-library/jest-dom';
import { expect, afterEach } from 'vitest';
import { cleanup } from '@testing-library/svelte';

// Cleanup after each test
afterEach(() => {
  cleanup();
});
```

## Basic Test Structure

### Unit Test Pattern
```typescript
import { describe, it, expect, beforeEach, afterEach } from 'vitest';

describe('calculateTotal', () => {
  it('should sum array of numbers', () => {
    const result = calculateTotal([1, 2, 3]);
    expect(result).toBe(6);
  });

  it('should return 0 for empty array', () => {
    const result = calculateTotal([]);
    expect(result).toBe(0);
  });

  it('should handle negative numbers', () => {
    const result = calculateTotal([-1, -2, 3]);
    expect(result).toBe(0);
  });
});
```

### AAA Pattern (Arrange-Act-Assert)
```typescript
it('should update user profile', () => {
  // Arrange - Set up test data
  const user = { id: '1', name: 'Alice' };
  const updates = { name: 'Alicia' };
  
  // Act - Execute the code under test
  const result = updateProfile(user, updates);
  
  // Assert - Verify the outcome
  expect(result.name).toBe('Alicia');
  expect(result.id).toBe('1');
});
```

## Svelte Component Testing

### Basic Component Test
```typescript
import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, it, expect } from 'vitest';
import Counter from './Counter.svelte';

describe('Counter', () => {
  it('should render initial count', () => {
    render(Counter, { props: { initialCount: 0 } });
    
    expect(screen.getByText('Count: 0')).toBeInTheDocument();
  });

  it('should increment count on button click', async () => {
    render(Counter, { props: { initialCount: 0 } });
    
    const button = screen.getByRole('button', { name: /increment/i });
    await fireEvent.click(button);
    
    expect(screen.getByText('Count: 1')).toBeInTheDocument();
  });
});
```

### Testing Component Props
```typescript
it('should accept and display custom label', () => {
  render(Button, { 
    props: { 
      label: 'Click Me',
      variant: 'primary' 
    } 
  });
  
  const button = screen.getByRole('button');
  expect(button).toHaveTextContent('Click Me');
  expect(button).toHaveClass('btn--primary');
});
```

### Testing Events
```typescript
it('should emit custom event on click', async () => {
  const { component } = render(Button);
  
  const handleClick = vi.fn();
  component.$on('click', handleClick);
  
  const button = screen.getByRole('button');
  await fireEvent.click(button);
  
  expect(handleClick).toHaveBeenCalledTimes(1);
});
```

### Testing Reactive Statements
```typescript
import { tick } from 'svelte';

it('should update derived value when input changes', async () => {
  const { component } = render(Calculator);
  
  const input = screen.getByLabelText('Number');
  await fireEvent.input(input, { target: { value: '5' } });
  await tick(); // Wait for reactive statements to run
  
  expect(screen.getByText('Doubled: 10')).toBeInTheDocument();
});
```

## Mocking Strategies

### Mocking Functions
```typescript
import { vi } from 'vitest';

it('should call API with correct parameters', async () => {
  const mockFetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ id: '1', name: 'Test' })
  });
  
  global.fetch = mockFetch;
  
  await fetchUser('1');
  
  expect(mockFetch).toHaveBeenCalledWith('/api/users/1');
});
```

### Mocking Modules
```typescript
import { vi } from 'vitest';

// Mock entire module
vi.mock('$lib/api', () => ({
  fetchUsers: vi.fn().mockResolvedValue([
    { id: '1', name: 'Alice' }
  ])
}));

// Or mock specific exports
vi.mock('$lib/utils', async () => {
  const actual = await vi.importActual('$lib/utils');
  return {
    ...actual,
    generateId: vi.fn(() => 'test-id')
  };
});
```

### Mocking Supabase
```typescript
import { vi } from 'vitest';

const mockSupabase = {
  from: vi.fn().mockReturnValue({
    select: vi.fn().mockReturnValue({
      eq: vi.fn().mockResolvedValue({
        data: [{ id: '1', email: 'test@example.com' }],
        error: null
      })
    }),
    insert: vi.fn().mockResolvedValue({
      data: { id: '1' },
      error: null
    })
  })
};

vi.mock('$lib/supabaseClient', () => ({
  supabase: mockSupabase
}));
```

### Mocking Stores
```typescript
import { vi } from 'vitest';
import { writable } from 'svelte/store';

// Mock store module
vi.mock('$lib/stores/user', () => ({
  userStore: writable({ id: '1', name: 'Test User' })
}));

// Or spy on store methods
it('should update store on success', async () => {
  const { subscribe, set } = writable(null);
  const setSpy = vi.spyOn({ set }, 'set');
  
  await loadUserData();
  
  expect(setSpy).toHaveBeenCalledWith({ id: '1', name: 'Alice' });
});
```

## Testing Async Code

### Promises
```typescript
it('should fetch user data', async () => {
  const user = await fetchUser('1');
  
  expect(user).toEqual({
    id: '1',
    name: 'Alice'
  });
});
```

### Callbacks
```typescript
it('should call callback with result', (done) => {
  fetchUser('1', (user) => {
    expect(user.name).toBe('Alice');
    done();
  });
});
```

### Waiting for DOM Updates
```typescript
import { waitFor } from '@testing-library/svelte';

it('should show loading then data', async () => {
  render(UserProfile, { props: { userId: '1' } });
  
  expect(screen.getByText('Loading...')).toBeInTheDocument();
  
  await waitFor(() => {
    expect(screen.getByText('Alice')).toBeInTheDocument();
  });
});
```

## Test Organization

### File Structure
```
src/
├── lib/
│   ├── components/
│   │   ├── Button.svelte
│   │   └── Button.test.ts
│   ├── utils/
│   │   ├── date.ts
│   │   └── date.test.ts
│   └── api/
│       ├── users.ts
│       └── users.test.ts
└── test/
    ├── setup.ts
    ├── helpers.ts
    └── mocks/
        ├── supabase.ts
        └── api.ts
```

### Naming Conventions
```
✓ Button.test.ts
✓ Button.spec.ts
✗ test-button.ts
✗ ButtonTests.ts
```

### Test Helpers
```typescript
// test/helpers.ts
export function renderWithProviders(component, props = {}) {
  return render(component, {
    props,
    context: new Map([
      ['supabase', mockSupabase],
      ['user', testUser]
    ])
  });
}

export const testUser = {
  id: 'test-id',
  email: 'test@example.com',
  name: 'Test User'
};
```

## Coverage Goals

### What to Aim For

**Not 100%** - Diminishing returns after ~80%

**Focus coverage on**:
- ✅ Business logic functions
- ✅ Complex algorithms
- ✅ Utilities used across codebase
- ✅ Critical user journeys
- ✅ Bug-prone areas

**Lower priority**:
- ❌ Simple getters/setters
- ❌ Type definitions
- ❌ Configuration files
- ❌ Generated code

### Running Coverage
```bash
# Run tests with coverage
npm run test:coverage

# View HTML report
open coverage/index.html
```

### Coverage Configuration
```typescript
// vitest.config.ts
export default defineConfig({
  test: {
    coverage: {
      statements: 80,
      branches: 75,
      functions: 80,
      lines: 80,
      exclude: [
        '**/*.config.ts',
        '**/*.d.ts',
        '**/types.ts',
        'src/test/**'
      ]
    }
  }
});
```

## Quick Reference

### Common Matchers
```typescript
// Equality
expect(value).toBe(5);              // Strict equality
expect(object).toEqual({ a: 1 });   // Deep equality
expect(array).toContain('item');    // Array contains

// Truthiness
expect(value).toBeTruthy();
expect(value).toBeFalsy();
expect(value).toBeNull();
expect(value).toBeUndefined();
expect(value).toBeDefined();

// Numbers
expect(value).toBeGreaterThan(3);
expect(value).toBeLessThanOrEqual(5);
expect(value).toBeCloseTo(0.3, 2);  // Floating point

// Strings
expect(string).toMatch(/pattern/);
expect(string).toContain('substring');

// Arrays/Objects
expect(array).toHaveLength(3);
expect(object).toHaveProperty('key', 'value');

// Errors
expect(() => fn()).toThrow();
expect(() => fn()).toThrow(Error);
expect(() => fn()).toThrow('message');

// Async
await expect(promise).resolves.toBe('value');
await expect(promise).rejects.toThrow();
```

### Common Testing Library Queries
```typescript
// Preferred (accessible)
screen.getByRole('button', { name: /submit/i });
screen.getByLabelText('Email');
screen.getByPlaceholderText('Enter email');
screen.getByText('Welcome');

// Fallbacks
screen.getByTestId('submit-button');

// Query variants
screen.getBy...    // Throws if not found
screen.queryBy...  // Returns null if not found
screen.findBy...   // Async, waits for element

// Multiple elements
screen.getAllByRole('listitem');
```

### Running Tests
```bash
# Run all tests
npm test

# Watch mode
npm test -- --watch

# Run specific file
npm test Button.test.ts

# Run tests matching pattern
npm test -- --grep "Button"

# Run with coverage
npm test -- --coverage

# UI mode
npm test -- --ui
```
