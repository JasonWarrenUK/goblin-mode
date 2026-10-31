---
name: "Approach: Types"
description: "Data models carry domain intent in their types: branded identifiers, closed state sets and declared shapes, in TypeScript, Python and Go. Backed by the type-guard hooks, which re-inject the rule after compaction and lint each file written."
when_to_use: "Writing or changing an interface, type alias, class, dataclass, pydantic model, struct or enum; reviewing a model for primitive obsession; deciding how to represent an identifier or a lifecycle."
user-invocable: false
metadata:
  family: clod-approach
  goblin-spinner: branding ids|closing the state set|naming the shape
# No model/effort override: fires inside an ongoing build, so it inherits the
# session the user chose for that work
allowed-tools: ["Read"]
---

# Types as domain models

A type checker only proves that a `string` went where a `string` was expected. It cannot see that the string was a customer id handed to a function wanting an order id, or that `status: string` admits every typo ever written. The gap is not a type-checking problem, it is a modelling one: the types never said what the values mean. This skill closes it.

The rule itself lives in [`reminder.md`](reminder.md), the single owner of the wording. The hooks print that file verbatim; this document carries the reasoning, the per-language shape and the machinery.

## Why a preference was not enough

Stated once in `CLAUDE.md`, the preference held for the first hour of a session and vanished at the first compaction. Reviewing for it afterwards found the same three drifts every time: `id: string`, `status: string` and a struct full of `isX` booleans. So the rule has three layers, each covering a failure of the one before:

| Layer | Where | Covers |
|---|---|---|
| Statement | `reminder.md`, this skill | The rule exists and has a reason |
| Re-injection | `hooks/type-guard.sh remind` and `compact` | The rule is in context at the moment a type is written, and again after every compaction |
| Enforcement | `hooks/type-guard.sh scan` | The two cases a structural match can decide: a bare-string identifier field, a bare-string status field |

Enforcement is deliberately narrow. A lint can say a field named `orderId` is typed `string`; it cannot say whether `Enrolment` should have been an entity rather than a boolean on `User`. That judgement belongs to `clod-role-domain_modeller` at design time, and to the reminder at write time.

## The shape per language

**TypeScript.** Brand the identifier, close the state set, declare the shape:

```typescript
export type Brand<T, B extends string> = T & { readonly __brand: B };
export type CustomerId = Brand<string, 'CustomerId'>;

export type AccountStatus = 'active' | 'suspended' | 'archived';

export interface Account {
	id: CustomerId;
	status: AccountStatus;
}
```

When each state carries its own data, a discriminated union on a `kind` field replaces the string-literal union. Parse once at the boundary (`z.string().brand<'CustomerId'>()`), never cast in the middle.

**Python.** `NewType` for identifiers, `Enum` or `Literal` for state, `@dataclass` or pydantic `BaseModel` for the shape:

```python
from dataclasses import dataclass
from enum import Enum
from typing import NewType

CustomerId = NewType("CustomerId", str)

class AccountStatus(Enum):
	ACTIVE = "active"
	SUSPENDED = "suspended"
	ARCHIVED = "archived"

@dataclass(frozen=True)
class Account:
	id: CustomerId
	status: AccountStatus
```

`NewType` is enforced by mypy or pyright and is an identity function at runtime, so the boundary still needs a validator (pydantic, or a constructor) to produce one.

**Go.** A defined type, never an alias. `type CustomerID string` is a distinct type the compiler keeps apart from `string`; `type CustomerID = string` is the same type under another name and buys nothing.

```go
type CustomerID string

type AccountStatus int

const (
	StatusActive AccountStatus = iota
	StatusSuspended
	StatusArchived
)

type Account struct {
	ID     CustomerID
	Status AccountStatus
}
```

## Where it does not apply

- UI component props. `isOpen`, `isLoading`, `disabled` on a Svelte or React component describe the widget, not a domain lifecycle. The scan never reads `.svelte` files, and the reminder says so.
- Wire formats. A JSON payload as it arrives is bare by nature. The rule is that it gets parsed into the branded or narrowed type once at the edge, and nothing past the edge sees the bare version.
- Test files and declaration bundles. The scan skips `*.test.ts`, `*.spec.ts`, `test_*.py`, `*_test.py`, `conftest.py`, `*.d.ts` and anything under `node_modules`, `dist`, `build`, `.svelte-kit` or a virtualenv.

## The hooks

All three run `hooks/type-guard.sh <mode>`, which pipes the payload to `library/scripts/type-guard.py`. Wiring, in `settings.json` (not in git; see `docs/reference/hooks.md`):

```json
"PreToolUse": [
	{ "matcher": "Edit|Write", "hooks": [{ "type": "command", "command": "~/.claude/hooks/type-guard.sh remind", "timeout": 10 }] }
],
"PostToolUse": [
	{ "matcher": "Edit|Write", "hooks": [{ "type": "command", "command": "~/.claude/hooks/type-guard.sh scan", "timeout": 30 }] }
],
"SessionStart": [
	{ "matcher": "compact", "hooks": [{ "type": "command", "command": "~/.claude/hooks/type-guard.sh compact", "timeout": 10 }] }
]
```

| Mode | Fires | Does |
|---|---|---|
| `remind` | Before an `Edit` or `Write` whose new text declares a type in a `.ts`, `.py` or `.go` file | Adds `reminder.md` as context, at most once per session every 30 minutes |
| `scan` | After an `Edit` or `Write` to a `.ts` or `.py` file | Runs the rules in `library/ast-grep/rules/` over the file; a finding exits 2 with `L<n> <rule> (<text>): <fix>` lines on stderr |
| `compact` | After any compaction | Adds `reminder.md` as context, since compaction is where the rule used to vanish |

Opt a repo out with `git config typeGuard.enforce false` (scan) or `git config typeGuard.remind false` (remind and compact); `TYPE_GUARD_OFF=1` silences everything for one shell. Every mode fails open: no ast-grep, no python3 or an unparseable payload means silence, never a blocked edit.

Scan a file by hand: `python3 ~/.claude/library/scripts/type-guard.py --file src/account.ts`, or run ast-grep directly with `ast-grep scan -c ~/.claude/library/ast-grep/sgconfig.yml src/`.

## Install

The scan needs [ast-grep](https://ast-grep.github.io) on the machine: `brew install ast-grep` or `bun add -g @ast-grep/cli`. The script looks on `PATH`, then in the bun, Homebrew, cargo and `~/.local/bin` install directories; `TYPE_GUARD_AST_GREP=/path/to/ast-grep` overrides. Without it the reminder layers still run and the scan stays silent.

## Not yet

Go rules. Go is listed as learning in the technical profile, and `type UserID string` is already the reminder's example, so the scan currently covers TypeScript and Python only. Build the Go rules when a Go project shows the reminder alone was not holding: the shapes to match are a struct field named `ID` or `*ID` typed `string`, and a `Status` or `State` field typed `string`.
