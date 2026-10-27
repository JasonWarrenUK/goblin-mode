---
name: "PR: Land"
description: "Land an approved PR: merge to main, delete the branch, tag the version, sync the roadmap, clean up"
when_to_use: "When a PR is approved with checks green and the user wants it merged and the aftermath handled."
model: opus
effort: medium
metadata:
  glyph: ᛟ
  family: pr
  goblin-spinner: merging|deleting evidence|tagging|cleaning up
disable-model-invocation: true
allowed-tools: ["Read", "Edit", "Bash(git:*)", "Bash(gh:*)", "Bash(cd:*)", "Bash(grep:*)", "Bash(~/.claude/library/scripts/safe-version-next.sh:*)", "Bash(~/.claude/library/scripts/checkout-occupied.sh:*)", "Bash(~/.claude/library/scripts/stack-status.py:*)", "Bash(python3:*)"]
arguments: ["pr"]
argument-hint: "[PR number | URL]"
---

# PR: Land

The post-approval sequence as one skill: verify the PR is genuinely ready, merge with a merge commit (granular commits are documentation; they belong on main), then handle everything a merge leaves behind: branch, worktree, version tag, roadmap.

## Hard rule: the version guard

**The 0.x → 1.x boundary is never crossed by this skill, under any circumstances.** Tagging v1.0.0 (or `{plugin}-v1.0.0`) declares that surface's API stable and only a human does that. The guard is programmatic: every tag this skill creates, root or plugin, always comes from `safe-version-next.sh` (bare for root, `--plugin {name} --dir {source}` for a plugin), which emits a 0.x minor bump when svu proposes 1.0.0 and passes every other bump through (2.x, 3.x major bumps are fine). Never call `svu next` directly here, and never hand-compute a tag or a `plugin.json` version.

The same line holds where CI does the tagging. A repo with `.github/release-packages.json` runs several tag series at once (one per `packages[]` entry, each with its own `prefix` such as `api/v`), and its CI tags each of them on push to main. **Nobody creates or suggests a 1.x tag in a manifest series by hand.** Only the repo's Declare Stable workflow, a manual dispatch by a signer listed in the manifest's `signers[]`, moves a package to 1.0.0; this skill neither runs that workflow nor recommends it.

## Step 1: Verify readiness

Resolve the PR from `$ARGUMENTS`, then `gh pr view --json state,reviewDecision,mergeable,mergeStateStatus,statusCheckRollup,headRefName,baseRefName,title`.

Proceed only when: state `OPEN`, every entry in `statusCheckRollup` has finished and passed, and `mergeable` isn't `CONFLICTING`. Both halves of the rollup are default-deny, so an enum value this text doesn't name still blocks. A check run whose `status` isn't `COMPLETED` (`QUEUED`, `IN_PROGRESS`, `PENDING`, `WAITING`, `REQUESTED`) counts as not passed, as does a status context whose `state` isn't `SUCCESS` (`PENDING` and `EXPECTED` are the non-terminal ones); a `conclusion` or `state` of `FAILURE`, `ERROR`, `CANCELLED`, `TIMED_OUT` or `ACTION_REQUIRED` fails outright. A completed check run passes on a `conclusion` of `SUCCESS`, `NEUTRAL` or `SKIPPED`; a status context passes only on `state` `SUCCESS`. `reviewDecision` must additionally be `APPROVED` unless the repo lives under `github.com/jasonwarrenuk/` (personal repos have no reviewer, so that value never appears; check the resolved owner, not the local remote string). Anything short of that: report exactly what's unmet and stop, with one exception. A failure that comes only from the roadmap's rendered dashboards goes through Step 1.1 first, because a rebase onto main usually clears it without anyone reading a log. This skill lands ready PRs; it doesn't chase approvals (`pr-handle_review`) or fix branches.

**Stack detection** (see `~/.claude/library/references/stacked-prs.md`): run `~/.claude/library/scripts/stack-status.py {number}` and read its verdict, never the base branch alone. `linked`: the PR is a layer of a GitHub stack and Step 2 uses `gh stack merge`. `chained-unlinked`: the bases form a chain GitHub does not know; stop and offer `/branch-stack link <bottom> ... <top>` first, because `gh stack merge` cannot land an unlinked chain and `gh pr merge` would land the layer without retargeting its children. `independent`: an ordinary merge. A stacked merge is bottom-up and contiguous: merging this PR also merges **every unmerged PR below it** (the row's `chain` field lists them), so extend the readiness check to each of those layers too, and note any open children above (they survive the merge and retarget automatically). A layer whose `statusCheckRollup` is empty has had no CI and does not pass: a workflow that only runs on pull requests into `main` never reaches the upper layers.

## Step 1.1: Roadmap-only failures

Only when Step 1 blocked and the repo has a rich roadmap (`python3 "$HOME"/.claude/marketplace/roadmap/scripts/roadmap.py detect` exits 0); any other block stops in Step 1 as written. CI tests the merge of the branch with main as main stood when the run started, so a roadmap check that fails on a branch touching no roadmap file is normally main's stale dashboard, fixed on main minutes later. A rebase onto the current main and a fresh run is all such a PR needs. This step does exactly that, once, and hands anything else back to Step 1's report.

**The roadmap files.** Read them from `.claude/roadmaps.json` rather than guessing paths: the JSON itself, every phase's `path` (its PHASE file), every phase's `artefact` (its rendered dashboard; `docs/artefacts/roadmap-{slug}.html` when the key is absent) and `docs/reports/ROADMAP_OVERVIEW.md`. Only the dashboard is a pure render (`roadmap.py render --phase {name}` reproduces it byte for byte); the JSON is the source of truth and the PHASE file and overview are hand-synced by `roadmap:maintain`. A conflict in a dashboard resolves by re-rendering. A conflict in any of the other three needs judgement and is not this step's business.

**One shape qualifies, nothing else does:** a stale dashboard check. `mergeable` isn't `CONFLICTING` (a conflicted PR changed whatever it conflicts on, dashboards included, so it stops in Step 1 and `/branch-integrate rebase main` is the route), and the failed rollup entries are all the repo's roadmap-artefact check (CHIRPdb's is the `Roadmap dashboards` job running `.github/scripts/check-roadmap-artefacts.py`; go by the log, never the name, since another repo names its check differently). Each failed entry's `detailsUrl` ends `/actions/runs/{runId}/job/{jobId}`; read `gh run view {runId} --job {jobId} --log-failed` and confirm every `error:` line names one of the roadmap files above and nothing else. Entries still running are tolerated, since the push below restarts them anyway. Any other entry that finished without passing: stop in Step 1.

**Then confirm the rebase can only help.** All three must hold:

- The branch is behind main: `git fetch origin main {head}`, then `git rev-list --count origin/{head}..origin/main` is above zero. Zero means the branch already holds main's tip, the rebase would change nothing and the failure is the branch's own: stop and report it as Step 1 would.
- Main's own tip passes the check that failed. CI tested the branch merged into main as main stood when the run's merge ref was made (the job's checkout log names it: `Merge {head} into {base}`), so being behind main alone shows nothing: if main has not fixed its dashboard since, a rebase reproduces the failure and spends the push for a diagnosis available without one. Name the failed run's workflow (`gh run view {runId} --json workflowName --jq .workflowName`), then find main's run for its current tip (`gh run list --branch main --commit "$(git rev-parse origin/main)" --workflow "{workflowName}" --limit 1 --json databaseId,status,conclusion`) and read the same-named job from `gh api repos/{owner}/{repo}/actions/runs/{databaseId}/jobs --jq '.jobs[] | [.name, .status, .conclusion] | @tsv'`. The job's conclusion is the signal, never the run's: a main run can fail elsewhere while this job passes. `success` means the rebase can only help. Anything else (failed, still running, no run for that tip) means main itself is stale or unproven: stop, say so and point at `roadmap:maintain` on main, with nothing rebased or pushed. A workflow that triggers only on `pull_request` never runs on main, so an empty lookup there says nothing about main's health: report it as unprovable rather than stale, and have `roadmap:maintain` check main's dashboards directly. (`git log --since` on main's dashboards is not a substitute: a fix committed days earlier and merged later carries the older committer date, and path-limited history skips the merge that brought it in.)
- The PR's own diff leaves the roadmap files alone: `gh pr diff {number} --name-only` matches none of them. The one allowed match is `.claude/roadmaps.json` when every commit touching it is this skill's own Step 1.6 commit: `git log --no-merges --format=%s origin/main..origin/{head} -- .claude/roadmaps.json` prints only subjects starting `chore(roadmap): end ` (those commits set `ended` dates the dashboard never renders; `--no-merges` keeps a merge of main into the branch out of the list). Any other subject there, or any other roadmap file in the diff, is roadmap work the PR carries, so the failure is its own: stop.

**Where to rebase.** `git worktree list --porcelain` says whether a worktree already holds `{head}`:

- It does: run `~/.claude/library/scripts/checkout-occupied.sh {path}`. Exit 1 means another live session is working there and a rebase under it would collide with its next commit; stop and name the session, so the user can run `/branch-integrate rebase main` from inside it. Exit 0 with `dirty_files` above 0 stops too (uncommitted work would block the rebase and is not yours to stash). Exit 0 and clean: rebase in that worktree.
- Nothing holds it: `git worktree add "${TMPDIR:-/tmp}/pr-land-{repo}-{number}-rebase" {head}` and rebase there. A local `{head}` that already exists is checked out as it stands, however far behind the remote it sits, which is why the rebase below starts with a fast-forward. Leave the worktree in place afterwards: Steps 1.5 and 1.6 need a checkout of the head branch and Step 4 removes it with the rest.

The main checkout is never switched for this, as Step 3 says.

**Ask before pushing when an approval is at stake.** A force-push can dismiss an existing approval on a repo that requires reviews, which costs a reviewer another pass. On a repo where `reviewDecision` applies, show the plan (head, how far behind, the failing check, the worktree) and **await approval** before rebasing. On a personal repo (`github.com/jasonwarrenuk/`) proceed, and record the pre-rebase SHA (`git rev-parse origin/{head}`) in the report so the old history is one `git reset` away. This rebase is the second exemption to `pr-handle_review`'s rule against rewriting reviewed commits (the stack cascade is the first): it re-parents the PR's own commits onto main without rewording, squashing or dropping any, so reviewed content survives apart from dashboard hunks replaced by main's copy below.

**Rebase.** For an `independent` PR, from the chosen checkout:

```bash
git merge --ff-only origin/{head} &&
test "$(git rev-list --count origin/{head}..HEAD)" -eq 0 &&
git rebase origin/main
```

The fast-forward comes first because the fetch refreshed `origin/{head}` without moving the local branch, and a local branch behind the remote (a review suggestion committed in the GitHub UI exists only there) would otherwise rebase without that commit and then push over it: `--force-with-lease` compares against the refreshed remote, so the lease passes and the commit is gone. `--ff-only` refusing means local and remote have diverged: stop and report it as Step 1 would, without guessing which side wins. The count guards the other direction. A local branch ahead of the remote (a committed but unpushed WIP commit, which `checkout-occupied.sh` cannot see because it counts uncommitted files only) fast-forwards with `Already up to date.`, and the rebase then carries that commit onto the PR, where `--force-if-includes` lets it through because the remote tip is in local history. Steps 1.5 and 1.6 push every commit they make, so a non-zero count never comes from this skill: stop as Step 1 would and name the commits (`git log --oneline origin/{head}..HEAD`). The three lines are chained with `&&` so the call stops, with a non-zero exit, at the first one that fails; run as separate statements, a refused fast-forward or a non-zero count prints its message and the rebase runs anyway, reporting exit 0. Read the exit before going on.

A conflict in a dashboard can still appear mid-rebase when an intermediate commit edited it and a later one reverted it (the PR's net diff is clean, so the gate above let it through). Resolve by taking main's copy (`git checkout --ours -- {path}`, where `--ours` is main during a rebase), `git add` and `git rebase --continue`, once per commit that conflicts. A conflict anywhere else: `git rebase --abort` and stop as Step 1 would, naming the paths. Once the rebase completes, re-render each phase whose dashboard conflicted (`roadmap.py render --phase {name}`) and, if `git status --short` shows a change, commit it as `chore(roadmap): re-render dashboard after rebase`; a render that changes nothing confirms main's copy was already current. Then `git push --force-with-lease --force-if-includes`: the second flag refuses the push unless the remote tip is in the local branch's history, which is the backstop should the fast-forward above ever be skipped. For a `linked` stack layer the rebase is `gh stack sync` from the stack's checkout instead (the worktree rules above apply to that checkout). Sync pushes every active layer of the stack, above this PR as well as below, so the count guard runs per layer first: `git fetch origin`, then for each branch in `gh stack view --json | jq -r '.branches[] | select((.isMerged or .isQueued) | not) | .name'` check `git rev-list --count origin/{layer}..{layer}` and stop on any non-zero, naming the layer and its commits. A layer with commits on both sides is unsafe too: sync skips its fast-forward silently, and the rebase that follows pushes over the remote-only commit. Sync's output must be read: it prints `Sync aborted` and still exits 0 when the local and remote *stacks* have diverged (membership or order), which says nothing about a single layer's commits.

**Wait, then re-check.** Straight after the push the rollup is empty while Actions registers the new commit's suites, and `gh pr checks --watch` exits at once with `no checks reported` rather than waiting (gh 2.94.0 returns that error before its watch loop starts); an empty rollup is never a pass. Nor is a non-empty one enough: the watch ends when every check it can see has finished, so a quick workflow that registers and completes before the roadmap one is listed would end it with the one check this step exists to re-run still absent. Poll `gh pr view {number} --json statusCheckRollup` until the rollup lists the roadmap check that failed, by the name read in the qualification above, for at most five minutes; if it never appears, stop and report it as Step 1 would. Then `gh pr checks {number} --watch` until every check finishes, then re-run Step 1's readiness check against the pushed commit. A roadmap failure that survives the rebase means main's own run was wrong about its tip or main moved again underneath: stop, say so and point at `roadmap:maintain` on main; this step runs once per landing, never in a loop. Any other failure after the rebase is reported as Step 1 reports it.

## Step 1.5: Bump any touched plugin

Only when `.claude-plugin/marketplace.json` exists (most repos don't ship plugins; skip this step entirely when it's absent). For each plugin entry (`name`, `source`), check whether this PR's diff touches that subtree: `gh pr diff {number} --name-only | grep -q "^${source#./}/"`. A stacked merge checks every layer's diff, not just this PR's own.

**Run every command in this step from a checkout of the PR's own head branch**, not main: `safe-version-next.sh --dir` (svu's `--log.directory` underneath) scans commits from `HEAD`, so running it from main (the common case, since Step 1 doesn't require checking the branch out) scans the wrong history and either misses the bump or, once a plugin tag exists, silently scans zero relevant commits. `gh pr checkout {number}` first (or `cd` into the worktree that already holds it, which after Step 1.1 is the rebase worktree), exactly as Step 4's cleanup later expects a checkout to exist.

For each touched plugin, run `~/.claude/library/scripts/safe-version-next.sh --plugin {name} --dir {source}`:

- **Exit 0** (a real bump): note the tag it printed (`{name}-v{X.Y.Z}`, not created yet, just computed) and the bare version (`{X.Y.Z}`) for the manifest. A hand-maintained plugin (every plugin in this repo) keeps its version in `{source}/.claude-plugin/plugin.json`'s `version` field. A plugin generated by a build script keeps it in that script's version source instead, found by reading the plugin's own docs rather than assumed. Read the current value first: if it already equals `{X.Y.Z}` (someone bumped it by hand, or this step already ran once on this branch), skip the commit rather than trying to commit a no-op. Otherwise write the bare version there (and rerun the build script, for a generated plugin), then commit onto the PR branch: `git commit -m "chore({name}): bump plugin version to {X.Y.Z}"` and push. This becomes part of what gets merged; it is no exception to the "never amend or rebase reviewed commits" rule (whose only exemptions are the stack cascade and Step 1.1's rebase), because it is a brand new commit, not a rewrite of one the reviewer already saw. For a generated plugin, `git status --short` its output directory after the build and commit any diff, since the version alone changing isn't the only reason the build could differ.
- **Exit 3** (nothing to release): the touching commits were all `docs`/`chore`/`refactor`-type, nothing version-worthy. Leave the plugin's version untouched; note this in the Step 2 summary so it's not mistaken for an oversight.
- **Exit 2** (environment error): stop and report; don't guess a version by hand.

A plugin's own bump commit is scoped to that plugin's subtree only (the version bump, plus the rebuild output for a generated plugin); never bundle unrelated changes into it. Multiple touched plugins in one PR each get their own bump commit, pushed in the same batch before Step 2's confirmation.

**Pushing restarts checks.** A push here can dismiss an existing approval or re-queue CI on a repo that has either; re-run Step 1's readiness check against the pushed commit before proceeding to Step 2, rather than trusting the state Step 1 read before this step existed.

## Step 1.6: Stamp end dates

Only when the repo has a rich roadmap (`python3 "$HOME"/.claude/marketplace/roadmap/scripts/roadmap.py detect` exits 0); otherwise skip silently. It runs on the PR's head branch, in the same checkout as Step 1.5, because the roadmap it edits is the branch's own and the date has to merge with the work. Never commit it to main afterwards: Step 3's rule stands.

1. Preview: `python3 "$HOME"/.claude/marketplace/roadmap/scripts/roadmap.py stamp-ended --base origin/{default branch} --pr {number} --dry-run --json`. The set is every done task that was not done at the branch's merge-base with the default branch, plus any done task whose `pr` is this PR's number, minus tasks that already have `ended`. Using the default branch as the base, even for a stacked PR, makes the set span every layer this merge lands.
2. Non-zero exit: the CLI prints a plain `✗` line, not JSON; relay it word for word. If it says `roadmaps.json` is not in canonical form, say that a write would reformat the whole file and rerun the preview with `--reformat` solely when the user agrees, keeping the flag on the write. On a refusal or any other failure (no merge-base with `origin/{default branch}`, a phase the merge-base cannot read, a bad `--date`, an unreadable roadmap on exit 2), skip this step, say in the Step 2 summary that no end dates were stamped and carry on; `roadmap:maintain` in Step 4 backfills them.
3. Empty `tasks`: nothing to do, move on. Otherwise rerun without `--dry-run`, then `git commit -m "chore(roadmap): end {IDs}"` (the roadmap file only) and push.
4. The date is today, which is the landing day. If the PR sits waiting past midnight, pass `--date` with the day the approval to merge is given.

A task the PR finished but that is not marked `done` on the branch is not stamped; say so in the Step 2 summary so it is not mistaken for an oversight (`roadmap:maintain` fixes the status and backfills the date later). Like Step 1.5, this push restarts checks: re-run Step 1's readiness check against the pushed commit before Step 2.

## Step 2: Confirm and merge

Show a one-line summary (title, head → base, review state, checks) and **await approval**; merging is irreversible in practice. For a stacked PR the summary must list every layer the merge will land (this PR plus all unmerged PRs below it): the approval covers the lot. If Step 1.5 bumped any plugin, list each one's new version and the commit that carries it, so the approval covers that too. If Step 1.6 stamped end dates, list the task IDs and the date. Then, for an ordinary PR:

```bash
gh pr merge {number} --merge --delete-branch
```

For a stacked PR:

```bash
gh stack merge {number} --merge
```

Do not run plain `gh pr merge` on a stack (the docs say the legacy merge endpoint can't merge stacks). **Always name the PR: `gh stack merge {number} --merge`, never a bare `gh stack merge`, a stack number or `--yes` alone.** In Claude's shell, which has no terminal, `gh stack merge` merges everything it names without prompting, so a bare invocation lands every layer including those above the PR just approved. Stack numbers and PR numbers never overlap (`gh stack link --help`), so there is no collision to work around; before running, confirm the layers `gh stack merge {number}` would land match the approved summary. It lands that PR and every unmerged layer below it, all or nothing, bottom-up (whether each layer gets its own merge commit is unverified: check `git log --first-parent` after the first real stacked landing); open PRs above retarget `main` via GitHub's server-side rebase, which produces unsigned commits. `gh stack merge` has no `--delete-branch`, so afterwards delete each merged layer's remote branch (`git push origin --delete {branch}`), but **only after confirming no open PR still targets it** (`gh pr list --base {branch}`; retargeting is normally immediate).

Merge commit, never squash or rebase: the branch's atomic commits are the history. `--delete-branch` removes the remote branch and, where the local branch isn't checked out elsewhere, the local one too.

If child PRs remain open above the merge point, run `gh stack sync --prune` from a checkout of the stack so the surviving local branches rebase onto the new `main` and stale refs go; `/branch-stack sync` is that command with its checks. Once every layer has landed, the stack's entry in local tracking is stale: `/branch-stack tidy`.

## Step 3: Tag the version

**The main checkout is never switched, pulled or committed to here.** Another session may be working in it, and a branch change under that session sends its next commits to the wrong branch. Everything after the merge runs in a detached landing worktree on `origin/main`, created from wherever the shell is:

```bash
git fetch origin main --tags \
  && git worktree add --detach "${TMPDIR:-/tmp}/pr-land-{repo}-{number}" origin/main \
  && cd "${TMPDIR:-/tmp}/pr-land-{repo}-{number}"
```

The path is built from the repo name and PR number because shell variables don't survive between commands; later steps rebuild the same string.

**Then find out whether CI tags this repo.** Look on the default branch for a workflow that creates tags on push:

```bash
git grep -lE 'git tag|svu|semantic-release|release-please|tag-action' origin/main -- .github/workflows
```

Read each hit (`git show origin/main:{path}`) to confirm it runs on a push to the default branch and pushes a tag for this series. A repo with `.github/release-packages.json` on the default branch tags one series per `packages[]` entry, so one landing may produce several tags; read the manifest (`git show origin/main:.github/release-packages.json`) so the prefixes are known before the run finishes.

**A tagging workflow exists: defer to it and create no tag.** Find its run for the merge commit and wait for it:

```bash
gh run list --workflow {file} --commit {mergeSha} --json databaseId,status,conclusion
gh run watch {databaseId} --exit-status
git fetch origin --tags && git tag --points-at {mergeSha}
```

Report **every** tag that `git tag --points-at {mergeSha}` returns, one line each, not just the first: a manifest repo tags each touched package separately (`api/v0.2.0` and `db/v0.1.1` from one merge, say). An empty list means CI found nothing to release; say so. A failed or missing run gets reported as it stands and tagging stops there: a hand-made tag on a repo whose CI tags is how tag and changelog drift apart. If any CI tag crossed 0.x → 1.x, say so plainly in the report; in a manifest series that can only have come from the Declare Stable workflow, never from this landing, so an unexpected 1.0.0 is worth a sentence to the user.

**No tagging workflow: tag from the landing worktree.**

```bash
TAG="$("$HOME"/.claude/library/scripts/safe-version-next.sh)" \
  && { git ls-remote --exit-code --tags origin "refs/tags/$TAG" >/dev/null 2>&1 \
       && echo "$TAG already on origin, leaving it alone." \
       || { git tag "$TAG" && git push origin "$TAG"; }; }
```

The `ls-remote` check is a backstop for a tag source the grep missed; it costs one no-op round-trip everywhere else. A multi-layer stack merge is one landing event: tag once for the lot, never once per layer. Push the single tag, never `git push --tags` (that publishes every local tag, strays included). Script exit **3** means nothing to release: no version-bumping commits since the current tag (a docs-only or chore-only PR); say so and skip to Step 4. If the script printed its 0.x guard note to stderr, relay it: the user should know a major bump was requested and deliberately held at 0.x.

**Any plugin Step 1.5 bumped gets tagged here too** (unless the CI workflow covers that plugin's tag series as well), same landing event, same `ls-remote`-before-push pattern, with `--plugin {name} --dir {source}` on `safe-version-next.sh` and `{name}-v{X.Y.Z}` as the tag. Since the version was already computed and committed pre-merge, this recomputes the same value from the now-merged commit (the tag anchors to the merge commit, not the pre-merge bump commit) rather than reusing the Step 1.5 string outright: if something else landed on main between Step 1.5 and the merge, this is the check that catches drift. A mismatch here (the script proposes something other than what Step 1.5 bumped to) means main moved under you; stop and report rather than tagging something that no longer matches `plugin.json`.

## Step 4: Clean up the checkout

Steps 1 and 2 run from the landing worktree: it sits outside the branch's own worktree, and its `HEAD` holds the merge, which is what `git branch -d` checks against.

1. If a worktree held this branch (`git worktree list`), remove it, from **outside** it, never while the shell is inside. A stack merge may have landed several branches; clean up each merged layer's worktree, but leave the worktrees of still-open child PRs alone (post-sync they're live work, not leftovers).
2. If the local branch survived (it was checked out somewhere), `git branch -d {branch}`: only `-d`; a refusal means unmerged commits and stops the line, not `-D`.
3. Remove the landing worktree last, standing in the main checkout without touching its branch: `cd "$(git rev-parse --path-format=absolute --git-common-dir)/.." && git worktree remove "${TMPDIR:-/tmp}/pr-land-{repo}-{number}" && git worktree prune`.
4. Bring the main checkout up to date only when that is safe. Run `~/.claude/library/scripts/checkout-occupied.sh` there: fast-forward with `git pull --ff-only` when it exits 0 **and** its JSON shows `branch` as `main` and `dirty_files` as 0. Anything else (another live session, a different branch, uncommitted files), leave the checkout exactly as it is and name the reason in the Step 6 report.

## Step 5: Roadmap sync

If the repo has a rich roadmap (`python3 "$HOME"/.claude/marketplace/roadmap/scripts/roadmap.py detect` exits 0), offer to run the `roadmap:maintain` skill so the merged work's task lands as `done` and the projections refresh; it also backfills any done task whose `ended` Step 1.6 missed. Offer, don't assume; the PR may not map to a roadmap task.

## Step 6: Report

PR merged (URL), every tag created (root, any bumped plugin and each tag CI returned in Step 3), branch/worktree state after cleanup, roadmap synced or skipped, and the task IDs given an end date by Step 1.6. If the changelog matters for this project, offer `/doc-changelog root md {tag}` for the root tag and, for each bumped plugin, `/doc-changelog plugin:{name} md {name}-v{X.Y.Z}`. On a manifest repo, offer `/doc-changelog pkg:{name} md {tag}` for each Step 3 tag whose prefix matches a `packages[]` entry's `prefix` (`api/v0.2.0` pairs with the entry whose prefix is `api/v`, so `pkg:api`); a tag matching no entry is reported but gets no offer. `doc-changelog`'s scope and version arguments together scope each run to exactly one release. Also offer `/hud-whats_new {previousTag}` so the user sees what they can now do that they couldn't before this landing.

## Red flags

**Never:** cross 0.x → 1.x on any tag series, root or plugin (the guard script is the only tag source); create or suggest a 1.x tag in a `release-packages.json` series (only the Declare Stable workflow, dispatched by a listed signer, does that); squash or rebase-merge; merge with failing or pending checks "because they'll pass"; rebase a branch for any failure other than the roadmap dashboard check, rebase it twice in one landing, or rebase it in a worktree another session holds; hand-merge a conflicted dashboard instead of re-rendering it; run `git checkout`, `git switch` or a bare `git pull` in the main checkout; create a tag on a repo whose CI tags; remove a worktree from inside it; use `git branch -D`; tag before the merge has actually landed on main; run plain `gh pr merge` on a stacked PR, or run `gh stack merge` with no PR number, with a stack number, or with `--yes` alone (use `gh stack merge {number} --merge`); delete a branch that is still the base of an open PR; hand-edit a plugin's `version` field or its build output instead of running `safe-version-next.sh` and the plugin's own build script.

<raw-arguments value="$ARGUMENTS" />
