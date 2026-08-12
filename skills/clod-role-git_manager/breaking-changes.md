# Breaking Change Detection

Detail for `git-manager` — the full lookup tables backing CLAUDE.md §8.5's breaking-change flagging rule.

**Proactively flag breaking changes** whenever reviewing code, discussing commits, or observing changes — even when the user is handling commits themselves.

## What Constitutes a Breaking Change

### API & Exports (High Priority)
| Change | Example | Breaking? |
|--------|---------|-----------|
| Removed export | `export function foo()` deleted | YES |
| Renamed export | `foo()` → `bar()` | YES |
| Changed parameters | `foo(a, b)` → `foo(a, b, c)` (required) | YES |
| Changed parameters | `foo(a, b)` → `foo(a, b, c?)` (optional) | NO |
| Reordered parameters | `foo(a, b)` → `foo(b, a)` | YES |
| Changed return type | `returns string` → `returns number` | YES |
| Narrowed return type | `returns string \| null` → `returns string` | NO |
| Widened return type | `returns string` → `returns string \| null` | YES |

### TypeScript Types & Interfaces
| Change | Breaking? |
|--------|-----------|
| Removed property from exported interface | YES |
| Added required property to exported interface | YES |
| Added optional property to exported interface | NO |
| Renamed exported type/interface | YES |
| Changed property type | YES |
| Made optional property required | YES |
| Made required property optional | NO |

### Database & Schema
| Change | Breaking? |
|--------|-----------|
| Removed column | YES |
| Renamed column | YES |
| Changed column type | YES |
| Added NOT NULL column without default | YES |
| Added nullable column | NO |
| Removed table | YES |
| Changed foreign key constraints | YES |
| Modified RLS policies (restrictive) | YES |

### HTTP API Endpoints
| Change | Breaking? |
|--------|-----------|
| Removed endpoint | YES |
| Changed route path | YES |
| Changed HTTP method | YES |
| Removed request field | YES (if was required) |
| Added required request field | YES |
| Removed response field | YES |
| Changed response field type | YES |
| Changed authentication requirements | YES |
| Changed error response format | YES |

### Configuration & Environment
| Change | Breaking? |
|--------|-----------|
| New required env variable | YES |
| Removed env variable | YES |
| Changed env variable name | YES |
| Changed config file format | YES |
| Changed default values | MAYBE (assess impact) |

### Component Props (Svelte/React)
| Change | Breaking? |
|--------|-----------|
| Removed prop | YES |
| Renamed prop | YES |
| Changed prop type | YES |
| Added required prop | YES |
| Added optional prop | NO |
| Changed event signature | YES |

## Detection Patterns

When reviewing code, watch for these patterns:

```typescript
// BREAKING: Removed export
- export function calculateTotal(items: Item[]): number { ... }

// BREAKING: Renamed export
- export const UserContext = createContext(...)
+ export const AuthContext = createContext(...)

// BREAKING: Added required parameter
- export function fetchUser(id: string): Promise<User>
+ export function fetchUser(id: string, options: FetchOptions): Promise<User>

// BREAKING: Changed return type
- export function getConfig(): Config
+ export function getConfig(): Config | null

// BREAKING: Removed interface property
  export interface User {
    id: string;
    name: string;
-   email: string;
  }

// BREAKING: Added required property
  export interface CreateUserRequest {
    name: string;
+   email: string;  // required, no ?
  }
```

## How to Flag

When you detect a potential breaking change, flag it clearly:

```
⚠️ **Breaking Change Detected**

This change removes the `email` property from the exported `User` interface.
Any code depending on `User.email` will break.

Consider:
- Adding `BREAKING CHANGE: removed email from User interface` to commit footer
- Or using `feat!:` or `refactor!:` prefix
- Branch naming: `feat/breaking-remove-user-email`
```

## Non-Breaking Alternatives

When flagging, suggest non-breaking alternatives where possible:

| Breaking Change | Non-Breaking Alternative |
|-----------------|-------------------------|
| Remove function | Deprecate first, remove in next major |
| Rename export | Export both names, deprecate old |
| Add required param | Make param optional with default |
| Remove field | Mark as deprecated, return null |
| Change type | Use union type for transition period |

## Commit Message Format

For breaking changes, use one of:

```bash
# Option 1: Footer
feat(api): redesign user authentication

BREAKING CHANGE: removed password field from login endpoint,
now uses OAuth tokens exclusively

# Option 2: ! indicator
feat!: redesign user authentication

# Option 3: Both (for emphasis)
feat(api)!: redesign user authentication

BREAKING CHANGE: removed password field from login endpoint
```
