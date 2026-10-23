# {{ run name }}: shared guidance

Coordinator: session "{{ coordinator name }}". Base: `{{ base branch }}@{{ base commit }}`. Written {{ date }}.

## Crew

| Task | Branch | Worktree | Migration |
|---|---|---|---|
| {{ id }} {{ title }} | `{{ branch }}` | `{{ worktree }}` | {{ timestamp or none }} |

## Shared facts (checked against `{{ base branch }}@{{ base commit }}`)

- {{ One fact per line, each with where it was read: a file and line, a command's output. Nothing from memory. }}

## Shared assumptions (held until the coordinator broadcasts a change)

{{ Set each with mc_assume so the ledger and every crew prompt carry them; paste the numbered list here too. }}

1. {{ ... }}

## Shared resources

| Resource | Rule |
|---|---|
| {{ name }} | {{ the config's notes, plus anything the kick-off learned: what the stack holds now, which worktree's migrations it carries }} |

## Human gates

{{ The config's human_gates list, one per line. The path for each is mc_need with the exact command and directory. }}

## Conventions

{{ One line per convention file the config lists, with the one or two rules from it that this run leans on. Then every entry from the config's facts list. A convention not found written down was asked of the user and is recorded here with "(from the user, {{ date }})". }}

## Message the coordinator when

- you want to touch a file outside your brief, or any shared surface above
- you need a slot (`mc_slot`), or a hosted window
- the user makes a decision that changes a shared assumption (the coordinator broadcasts it)
- you open a PR (`mc_report` with the number, plus one line) and when it merges
