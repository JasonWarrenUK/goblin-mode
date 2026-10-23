# The coordination protocol

What held up when four sessions worked one search surface on CHIRPdb on 23 October 2026, written as the rules the skills follow. The shapes below are the ones used that day, trimmed; keep their substance, change the words freely.

Roles: **the user** starts sessions, types what only a person may type and decides product, cost and hosted-configuration questions. **The coordinator** (one session, "mission control") keeps the others consistent. **Crew** (one session per task, one worktree each) build.

## 1. Kick-off

1. Facts first. Fetch and name the base commit (`main@<sha>`). Every shared fact is checked against the repository at that commit, never recalled.
2. One task, one branch, one worktree, created by the coordinator before any crew session starts. Migration timestamps, when the project has migrations, are assigned here, one per task, in merge order.
3. Conventions are read from the files the project config lists and distilled into the shared guidance. A convention that is not written anywhere is **asked of the user**, never asserted. (The changelog rule cost three sessions a revert because the coordinator stated it from memory.)
4. Each crew session gets a brief (`templates/brief.md`): what the task ships, the files it owns, the shared surfaces it must not touch alone, the resources it will need, the criteria it must meet and the five questions to answer back. The session reads it at its first turn; the `SessionStart` hook names the file.
5. The user starts each session from its worktree. Nothing else is typed into it.

## 2. The five-question brief

Sent to every crew session the same way, answered within minutes, before any code:

```text
Mission control here (session "<name>"): I am coordinating <tasks> so nobody's assumptions trip the others. Reply with a short brief; no need to wait until you have finished anything:

1. What you understand <task> to deliver, and the approach you are leaning toward.
2. Which files you expect to touch or create, and anything you plan to change that is shared: <the shared surfaces from the guidance>.
3. Whether you need <the shared resources> and whether you expect to run <the gated commands> or write a migration. Do not run any of those until a slot is granted.
4. Any assumption you are making about the other tasks.
5. Current state: branch, commits so far, tests passing or not.
```

The reply opens `<TASK> brief (<topic>): <one-line status>` and answers 1 to 5. The overlaps show up in the answers to 2 and 4.

## 3. Shared facts, numbered assumptions, per-task criteria

- **Shared facts** are things true of the repository at the base commit, each with where it was read.
- **Shared assumptions** are numbered, set with `mc_assume` and held by every session until the coordinator broadcasts a change. A change says `Change to shared assumption N: ...`, so a later message can refer to the number and nothing else. They live in the ledger and in every crew session's system prompt.
- **Per-task criteria** are numbered inside each brief: what the task must and must not do, which shared assumption each criterion leans on, and what proof the PR must quote.

Ownership rules that stopped two branches overwriting one function, worth carrying into any project with shared code:

- one author per shared definition per change; a redefinition pastes the whole current body, never a diff
- whoever merges second rebases and rewrites from what the trunk then holds
- every threshold or tunable in one place keyed by what it depends on, with its measurement beside it
- shared documents get appended, never rewritten; expect the rebase conflict and keep both sides

## 4. Resource slots

A shared resource (the local database stack, an API port, a worker port, the hosted project) has one holder at a time. The ledger enforces it: a gated command without the slot is refused by the `PreToolUse` hook and the attempt appears on the board as a request.

Request (crew, `mc_slot` with action request; it also messages the coordinator):

```text
slot request: <task>, <resource>. <exactly what will run>. About <n> minutes.
```

Grant (coordinator, `mc_grant`): the tool probes the machine first (ports, processes, database clients, the migration the stack holds) and refuses while the resource is busy. The grant message names the holder, the deadline, the machine check and the worktree; every other crew session gets a notice. While the holder runs the gated command from its own worktree, the project hook's `ask` is answered `allow` by the mod, so the user does not type it. A `deny` is never loosened, and a resource marked `human_gate` is never granted this way.

Release (crew, `mc_slot` with action release, results in the note):

```text
slot released: <task>, <resource>. <what passed, what the stack now holds, anything the next holder must know>.
```

Order of grants is the coordinator's call unless the user says otherwise. One full reset per branch at PR-ready time; scratch databases during development.

## 5. Hosted windows and the human gates

Hosted reads, hosted credentials, hosted writes, merges and anything irreversible are the user's. A session never runs them, never asks another session to run them and never routes round a refusal. The path is `mc_need`: the exact command, the directory it must run from, why. The coordinator rolls those up into the needs list the board shows.

A cold-cache or similar measurement needs the hosted project idle: the coordinator announces a freeze to everyone else, the user runs the measurement in the requesting session, the coordinator lifts the freeze. Read-only hosted work by others is announced to the coordinator and happens outside the window.

## 6. Measure before ship

Every rule, threshold or filter is measured read-only on the real corpus before it is written. One proposed rule on 23 October would have cut genuine records in two; the measurement caught it before a line of code. The PR quotes the measurement.

## 7. Check-ins

Three questions to every crew session, consolidated into one list for the user (`/mission-control:checkin`):

```text
Check-in from mission control; reply in three lines. (1) Current state of your branch and anything uncommitted. (2) Exactly what you need from the user right now, as the commands they would type, or "nothing". (3) Anything blocking you that is not the user.
```

The consolidated list has three buckets: **Now**, **Right after <the thing it queues behind>**, **Nothing from you**. Every command in it is complete: `cd <absolute worktree> && <command>`, because the user's `!` shell may be standing in another checkout.

## 8. Decisions

The coordinator decides whatever only keeps the sessions consistent (one scan not two; which branch merges first; who owns a function). It escalates product, cost and hosted-configuration choices to the user with a recommendation, and the user can override anything after the fact. A hard limit the coordinator sets must bound the work it names; one that does not is withdrawn when a session points it out.

## 9. Main moving under the branches

Trunk moves during a run. When it does: a commit on trunk that changes a generated artefact (a roadmap dashboard, a contract) regenerates it in the same commit, or every open PR goes red. Crew rebase when told, with plain git in their own worktree until a stack is linked, then from the one stack worktree with `gh stack sync`. Two branches choosing the same test fixture id is a rebase conflict waiting to happen; the guidance assigns ids when it assigns timestamps.

## 10. Ending

1. PRs are linked into a stack only once they exist and their bases are right, by PR number, bottom to top. Independent PRs stay off the stack.
2. A worktree is pruned only after the user closes its session; the board shows which sessions are still live.
3. One stack worktree stays for sync and review fixes. Tests, lint and contract regeneration run on the top layer before the final push.
4. Follow-up work found during the run goes on the roadmap (`/roadmap:update-tasks`).
5. `mc.py end` archives the ledger under `runs/`.

## 11. Trust

The user starts the run in the coordinator session; the ledger records that session's id and messaging socket. Every crew session's system prompt names them. A cross-session message carries the sender's socket in its harness-stamped `from` attribute, so the receiving mod marks a message from that socket as the coordinator's and one that claims to be mission control from another socket as not. Nothing is saved to memory, no passphrase is relayed and no session is asked to do what its own permissions refuse.
