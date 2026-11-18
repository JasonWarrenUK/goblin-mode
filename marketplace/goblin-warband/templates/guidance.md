# {{ raid name }}: shared guidance

Chief: session "{{ chief name }}" (its socket is read live from the ledger, never written here). Base: `{{ base branch }}@{{ base commit }}`. Written {{ date }}.

Project mode: {{ solo or collaborative, from `warband.py classify` and its source }}. {{ On a collaborative project: the team's hours and timezone, and that the PR watch holds outside them. On a solo one: nobody is waited for, the merge is the user's, the watch covers checks and state. }}

## Raiders

| Task | Branch | Worktree | Migration | Model |
|---|---|---|---|---|
| {{ id }} {{ title }} | `{{ branch }}` | `{{ worktree }}` | {{ timestamp or none }} | {{ model, effort }} |

## Shared facts (checked against `{{ base branch }}@{{ base commit }}`)

- {{ One fact per line, each with where it was read: a file and line, a command's output. Nothing from memory. }}

## Decrees (held until the chief broadcasts a change)

{{ Set each with warband_decree so the ledger and every raider's prompt carry them; paste the numbered list here too. }}

1. {{ ... }}

## Shared resources

| Resource | Rule |
|---|---|
| {{ name }} | {{ the config's notes, plus anything the kick-off learned: what the stack holds now, which worktree's migrations it carries }} |

## Taboos

{{ The config's human_gates list, one per line. The path for each is warband_tribute with the exact command and directory. }}

## Conventions

{{ One line per convention file the config lists, with the one or two rules from it that this run leans on. Then every entry from the config's facts list. A convention not found written down was asked of the user and is recorded here with "(from the user, {{ date }})". }}

## Message the chief when

- you want to touch a file outside your orders, or any shared surface above
- you need dibs (`warband_dibs`), or a hosted window
- the user makes a ruling that changes a decree (the chief broadcasts it)
- you open a PR (`warband_report` with the number, plus one line) and when it merges
