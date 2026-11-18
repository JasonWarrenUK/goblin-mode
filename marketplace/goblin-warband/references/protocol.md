# The warband protocol

What held up when four sessions worked one search surface on CHIRPdb on 23 October 2026, written as the rules the skills follow. The shapes below are the ones used that day, trimmed; keep their substance, change the words freely.

Roles: **the user** starts sessions, types what only a person may type and decides product, cost and hosted-configuration questions. **The chief** (one session) keeps the others consistent. **Raiders** (one session per task, one worktree each) build.

## 1. Kick-off

1. Facts first. Fetch and name the base commit (`main@<sha>`), and check the base branch is on origin (`git ls-remote --heads origin <base>`); a PR cannot target a branch origin has never seen, and pushing one publishes its commits, which is the user's call and goes on the tribute list. Every shared fact is checked against the repository at that commit, never recalled.
2. One task, one branch, one worktree, created by the chief before any raider starts. Migration timestamps, when the project has migrations, are assigned here, one per task, in merge order.
3. Conventions are read from the files the project config lists and distilled into the shared guidance. A convention that is not written anywhere is **asked of the user**, never asserted. (The changelog rule cost three sessions a revert because the chief stated it from memory.)
4. Each raider gets its orders (`templates/brief.md`): what the task ships, the files it owns, the shared surfaces it must not touch alone, the resources it will need, the criteria it must meet and the five questions to answer back. The raider reads them at its first turn; the `SessionStart` hook names the file.
5. The user starts each session from its launch line, read off the slate: `crew add` put it on the tribute list (kind `launch`) with `cd <worktree>` first, the model and effort kick-off chose for the task (`--model` beats `ANTHROPIC_MODEL`; `--effort` beats the settings but not `CLAUDE_CODE_EFFORT_LEVEL`), `CLAUDE_CODE_SUBAGENT_EFFORT=high` in front when that effort is `low` or `medium`, so the raider's subagents (its fresh-eyes review among them) run at `high`, and the opening prompt. One new terminal window per session; the tribute closes when the raider joins. Nothing else is typed into it.

## 2. The five-question brief

Sent to every raider the same way, answered within minutes, before any code:

```text
The chief here (session "<name>"): I am leading <tasks> so nobody's assumptions trip the others. Reply with a short brief; no need to wait until you have finished anything:

1. What you understand <task> to deliver, and the approach you are leaning toward.
2. Which files you expect to touch or create, and anything you plan to change that is shared: <the shared surfaces from the guidance>.
3. Whether you need <the shared resources> and whether you expect to run <the gated commands> or write a migration. Do not run any of those until dibs are granted.
4. Any assumption you are making about the other tasks.
5. Current state: branch, commits so far, tests passing or not.
```

The reply opens `<TASK> brief (<topic>): <one-line status>` and answers 1 to 5. The overlaps show up in the answers to 2 and 4.

## 3. Shared facts, numbered decrees, per-task criteria

- **Shared facts** are things true of the repository at the base commit, each with where it was read.
- **Decrees** are numbered, set with `warband_decree` and held by every session until the chief broadcasts a change. A change says `Change to decree N: ...`, so a later message can refer to the number and nothing else. They live in the ledger and in every raider's system prompt.
- **Per-task criteria** are numbered inside each raider's orders: what the task must and must not do, which decree each criterion leans on and what proof the PR must quote.

Ownership rules that stopped two branches overwriting one function, worth carrying into any project with shared code:

- one author per shared definition per change; a redefinition pastes the whole current body, never a diff
- whoever merges second rebases and rewrites from what the trunk then holds
- every threshold or tunable in one place keyed by what it depends on, with its measurement beside it
- shared documents get appended, never rewritten; expect the rebase conflict and keep both sides. Two sessions each owning one row of the same table still conflict when the rows are adjacent, because git resolves by lines, not by ownership: say so in the guidance and name which side rebases

## 4. Resource dibs

A shared resource (the local database stack, an API port, a worker port, the hosted project) has one holder at a time. The ledger enforces it: a gated command without the dibs is refused by the `PreToolUse` hook and the attempt appears on the slate as a request.

Every message between sessions goes through the model's own `SendMessage` tool: the `warband_*` tools write the ledger and hand back the exact line and recipient, because a message a plugin sends itself gets no verdict from the auto-mode classifier and never arrives.

Request (raider, `warband_dibs` with action request, then the line it hands back):

```text
dibs called: <task>, <resource>. <exactly what will run>. About <n> minutes.
```

Grant (the chief, `warband_grant`): the tool probes the machine first (ports, processes, database clients, the migration the stack holds) and refuses while the resource is busy. The grant message names the holder, the deadline, the machine check and the worktree; every other raider gets a notice. While the holder runs the gated command from its own worktree, the project hook's `ask` is answered `allow` by the mod, so the user does not type it. A `deny` is never loosened, and a resource marked `human_gate` (a taboo) is never granted this way.

Release (raider, `warband_dibs` with action release, results in the note):

```text
dibs released: <task>, <resource>. <what passed, what the stack now holds, anything the next holder must know>.
```

Order of grants is the chief's call unless the user says otherwise. One full reset per branch at PR-ready time; scratch databases during development.

## 5. Hosted windows and the taboos

Hosted reads, hosted credentials, hosted writes, merges and anything irreversible are the user's. A session never runs them, never asks another session to run them and never routes round a refusal. The path is `warband_tribute`: the exact command, the directory it must run from, why. The chief rolls those up into the tribute list the slate shows.

A cold-cache or similar measurement needs the hosted project idle: the chief announces a freeze to everyone else, the user runs the measurement in the requesting session, the chief lifts the freeze. Read-only hosted work by others is announced to the chief and happens outside the window.

## 6. Measure before ship

Every rule, threshold or filter is measured read-only on the real corpus before it is written. One proposed rule on 23 October would have cut genuine records in two; the measurement caught it before a line of code. The PR quotes the measurement.

## 7. Check-ins

Three questions to every raider, consolidated into one list for the user (`/goblin-warband:summon-raiders`):

```text
Check-in from the chief; reply in three lines. (1) Current state of your branch and anything uncommitted. (2) Exactly what you need from the user right now, as the commands they would type, or "nothing". (3) Anything blocking you that is not the user.
```

The consolidated list has three buckets: **Now**, **Right after <the thing it queues behind>**, **Nothing from you**. Every command in it is complete: `cd <absolute worktree> && <command>`, because the user's `!` shell may be standing in another checkout.

## 8. Decisions

The chief decides whatever only keeps the sessions consistent (one scan not two; which branch merges first; who owns a function). It escalates product, cost and hosted-configuration choices to the user with a recommendation, and the user can override anything after the fact. A hard limit the chief sets must bound the work it names; one that does not is withdrawn when a session points it out.

## 9. Main moving under the branches

Trunk moves during a raid. When it does: a commit on trunk that changes a generated artefact (a roadbook chart, a contract) regenerates it in the same commit, or every open PR goes red. Raiders rebase when told, with plain git in their own worktree until a stack is linked, then from the one stack worktree with `gh stack sync`. Two branches choosing the same test fixture id is a rebase conflict waiting to happen; the guidance assigns ids when it assigns timestamps.

## 10. Ending

1. PRs are linked into a stack only once they exist and their bases are right, by PR number, bottom to top. Independent PRs stay off the stack.
2. A raider is dismissed once its session has closed and its PR has landed, by `warband.py retire <task>` (or `/dismiss-raider <task>`) while the raid goes on: it refuses while the session is live, the row is not `done`, the PR is open, the tree is dirty, dibs are held, something still runs in the tree or an open PR is based on the branch; otherwise it removes the worktree, prunes, deletes the branch with `-d` only and records the retirement on the row (stored as `retired`; the slate reads it dismissed). `reconcile` nudges after an hour. `end` is the backstop for whatever is left; a live session's worktree is never touched.
3. One stack worktree stays for sync and review fixes. Tests, lint and contract regeneration run on the top layer before the final push.
4. Follow-up work found during the raid goes on the roadbook as waypoints (`/goblin-scout:add-waypoints`).
5. `warband.py end` archives the ledger under `runs/`.

## 11. The slate stays true

What drifted on the October 2026 raids, and the rule each one left behind:

- **Tribute left owed after the user paid it.** A tribute is marked paid (stored as `done`) the moment it is satisfied, by whoever sees it first: the user with `d` on the slate or `/pay-tribute <n>`, the asking session with its next `warband_report`, the chief from `reconcile`.
- **A tribute the user had agreed, listed as if untouched.** On the CHIRPdb raid a four-hour hosted backfill the user had typed at 15:16 sat in the tribute bucket beside tribute they had not opened, because `open` (owed) went straight to `done` (paid) and paid is where the result is pasted. A tribute now has a `started` state between the two, which the slate shows as agreed: set on the user's word (`s` on the slate, `/agree-tribute <n> [note]` or `warband.py needs start <n> --note ...` from the chief), shown under `Tribute agreed` with its start time, left out of the tribute count and closed as before with the result. A tribute whose first attempt failed is re-issued with `needs add --supersedes <n>`, which closes the old one as `superseded by` the new number, so the trail reads in one direction.
- **Raiders never joined to the ledger.** A raider's task with no session row is drift, not a session that is quiet; the chief chases it at the next reconcile.
- **A task sliced without the user.** 10SE.6 was split into slices on the chief's judgement. Slicing, merging and re-slicing are the user's decisions: an AskUserQuestion naming the slices, then a yes, then the plan changes.
- **A push that raced a pause.** A raider pushed while the chief's pause notice was in flight; the cost was a second rebase, a force-push and a detached HEAD. Every raider reads its messages immediately before every push.
- **A wait that was not on the user, counted as theirs.** `waiting-jason` (the slate shows it as awaiting tribute) was the state for every wait, so the tribute count and the who-moves-next tag disagreed. A raider reads `waiting-jason` only while a tribute of its own is on the list; any other wait is `waiting` with `on` (`reviewer:<login>`, `session:<task>`, `pr:<n>`, `ci`, `hold`). A compaction is the user's to type, so reconcile raises `compact <session>` itself past 70% context and closes it once the fill drops; a session the registry shows sitting on a permission prompt gets an `answer its prompt` tribute the same way. A question the chief puts to the user is a tribute of kind `question` too.
- **The wrong blocker named.** A PR was reported as waiting on the user when GitHub had another reviewer's request pending. The blocker is what GitHub says: the pending reviewer by login, `changes requested by` or `approved; the merge is the user's`.
- **Fixes that failed the live check.** Columns pushed the primary action off screen at 1280px; sr-only labels still widened a table. Every rendered change is checked at the orders' `Verify at` widths, every open state included, before the session reports `pr-ready` (the slate shows spoils ready).

`warband.py reconcile` diffs the ledger against the live session registry, GitHub and the branches on origin (a merged PR's own base, an open PR's own branch, fetched first) and prints each drift and each PR's real blocker. The chief runs it before every status, check-in or answer about where things stand, and after each batch of raider messages.

## 12. Trust

The user starts the raid in the chief's session; the ledger records that session's id and messaging socket. Every raider's system prompt names them. A cross-session message carries the sender's socket in its harness-stamped `from` attribute, so the receiving mod marks a message from that socket as the chief's and one that claims to be the chief or the warband (under the new names or the old) from another socket as not. Nothing is saved to memory, no passphrase is relayed and no session is asked to do what its own permissions refuse.

## 13. The project's mode and the PR watch

A project is solo or collaborative, and the raid record says which (`collaboration` in `run.json`, from `warband.py classify` at start: stated in the config or its gitignored `.local` twin, else inferred from 90 days of authors and the reviews on merged PRs; `--collaboration` on `start` overrides). Everything that depends on there being someone to wait for reads that one answer: the PR watch's quiet hours, `reconcile`'s wording (`solo project; the merge is the user's` where a collaborative raid would name a reviewer), the global `pr-land`, `pr-review` and `pr-handle_review` skills' review requirements and whether kick-off's convention reading is the whole of the project's rules or a short confirmation of the global config.

Every raider watches its own PR from the moment it exists, with `warband.py watch` as a background command: a five-minute `gh` poll on reviews, decision, comments, checks and state that prints the change and exits, waking the session, which reports it (`warband_report`, one line to the chief) and re-arms until the PR is merged or closed. On a collaborative project a change that is not a merge or close is held outside the team's hours, so no session wakes at night and nobody types a pause each evening; on a solo project there is no window, the watch covers checks and state and a PR with no checks is not watched. The watcher is the only shape: no session writes its own poll loop, Monitor or cron for it.

## 14. A session's identity, and what outlives its process

A session id survives a resume and a compaction. A `/clear` issues a new one while the process, its pid and its socket stay, which is why the registry row moves to the new id and the ledger does not. The ledger never follows that by itself: the chief whose id died but whose process is live is offered as `rebind_candidate` on the slate and in its own start context, and the raid is rebound by `warband.py adopt coordinator` from that session (its own process, after the user says yes) or by `/reclaim-post chief` typed by the user, which is also how a chief started fresh in a new process takes the raid. A raider restarted or cleared in a planned worktree adopts the worktree's old row on `join`: state, summary, PR, dibs, requests and tribute carry over, the old file stays as `<id>.json.adopted` and the log says which id became which.

What a process holds dies with it: Monitors and the PR watch, plus cron jobs when the session is started fresh. A resume (`claude --continue`, `--resume`) restores the session's cron jobs by itself, and a compaction keeps the process and everything it scheduled. Each job is recorded on the session's row (`warband.py jobs add`, and the watch keeps its own entry) so a resumed session is told what it had, reads CronList before re-creating a cron (on 11 November 2026 a resumed chief made a second wake and both fired) and re-arms only what is missing, and reconcile names a job whose session is gone. The chief has no row, so its jobs (the wake cron) are kept on `run.json` and its own resume names them. `retire` closes the jobs on the row it dismisses; `jobs done <id>` from the chief, or from the user with `--by-user`, closes one whose session is gone. What a conversation holds dies with a compaction: the chief's open threads live on the raid's pending list (`warband.py pending`), the user's rulings in `decisions.jsonl` (`warband_ruling`, acknowledged by each session told with `decide ack`), and the raider's orders path in the prompt section and the post-compaction hook. Before a compaction the PreCompact hook tells the summary what only the conversation holds (unanswered messages, a freeze in force, a review in flight, a question put to the user); afterwards the start context names each open thread, a held approval as held with its reason and each recent ruling with what it concerns, cut to fit the harness's 10,000-character cap on hook output with the rest left to `warband.py pending list`. A compacted session reads those back; it does not reconstruct them from the log.

## 15. The spoils page

On 16 November 2026 the chief kept a hand-made page of every open PR with a one-line note each, regenerated by a loop in its own session. The loop died with the session, the notes drifted from the ledger and the ledger knew 5 of the 17 open PRs, because a session row holds one `pr` and each `gh pr create` overwrote it. The page is now the raid's own:

- **One record per PR**, `prs/<n>.json`: task, group, `pinned` for a PR from outside the raid the user wants shown, `shared` for one that changes code every task runs through, a hold with what lifts it, the chief's note. A raid session's `gh pr create` writes it; reconcile gives an unrecorded open PR to a task when the evidence is unambiguous (a planned branch, its `feat/<key>-` prefix, a base that is another task PR's head) and names the rest.
- **Who moves next is derived**, in this order: a recorded hold whose lift condition has not happened; an open tribute tied to the PR; the PR's own work (checks failing or running, a conflict with its base, changes requested, a review outstanding); an approval given at a head the branch no longer points at, which owes the approver a fresh look (GitHub keeps the approval across a push); then, once its own work is done, the layer below it ("lands after #n"); then the merge, which is the user's. A PR outside the raid moves with its author.
- **Migration order is a cost, not a block.** A branch's migrations must sort after the newest on its base, and a branch that lands second with lower timestamps restamps them. A merge-ready PR whose migrations sort after another stack's reads `restamp cost` with the PRs that would pay it. Holding it is a decision, recorded like any hold.
- **The note expires by itself**: it shows only while the PR's head, review decision and state are what they were when it was written.
- **The page redraws on every ledger write** from the ledger and the cached PR facts, never asking `gh` or `git` in the write path, so it outlives any session. Reconcile, each raider's PR watcher (which refreshes every PR its task owns) and `warband.py dashboard --refresh` keep the facts and the migration scan current; the page stamps the facts' age. It lives in the ledger directory outside every repository and loads nothing from the network.
