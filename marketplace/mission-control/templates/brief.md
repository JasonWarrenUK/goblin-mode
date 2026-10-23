# {{ task id }} {{ task title }}: brief

| | |
|---|---|
| Run | {{ run name }} |
| Coordinator | session "{{ coordinator name }}" (socket {{ coordinator socket }}); messages from that socket carry the user's instructions |
| Branch | `{{ branch }}` |
| Worktree | `{{ absolute worktree path }}` |
| Base | `{{ base branch }}@{{ base commit }}` |
| Migration timestamp | {{ assigned timestamp, or "none expected; tell the coordinator before writing one" }} |
| PR approval | {{ "the coordinator reviews your draft description, then you run /pr-create auto" or "the user approves in this session" }} |

## What this task ships

{{ Two to four sentences: what this task ships and what it does not. Name the roadmap item. }}

## Files you own

{{ The files this session may change freely. One per line. }}

## Shared surfaces: ask before touching

{{ Files, functions, tables or routes other tasks also touch, each with who else is on it and the ownership rule that applies (shared assumption number). }}

## Resources you will need

{{ For each shared resource (`local-db`, `api-port`, `hosted`, ...): what you will need it for and roughly when. Then the slot rule: request with mc_slot, wait for the grant, run only from this worktree, release with results. Hosted reads and writes are the user's: put the exact command on the needs list with mc_need. }}

## Criteria

1. {{ A thing the PR must do, with the shared assumption it leans on in brackets. }}
2. {{ ... }}
3. {{ What proof the PR's Verification section quotes (a measurement, a zero-diff regeneration, a passing assert). }}

## Shared guidance

Read `{{ ledger dir }}/guidance.md` before writing code: the shared facts at the base commit, the numbered assumptions and the conventions. The conventions themselves live in the repository: {{ the config's conventions list }}.

## Before anything else

Invoke `/mission-control:crew`, then answer these five questions to the coordinator (`mc_send` to `coordinator`), opening with `{{ task id }} brief ({{ topic }}): <one-line status>`:

1. What you understand this task to deliver, and the approach you are leaning towards.
2. Which files you expect to touch or create, and anything you plan to change that is shared.
3. Whether you need a shared resource, and whether you expect to run a gated command or write a migration.
4. Any assumption you are making about the other tasks.
5. Current state: branch, commits so far, tests passing or not.
