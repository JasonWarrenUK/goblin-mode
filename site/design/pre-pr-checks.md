# Pre-PR checks for the site

Run after the one rebase onto main, once goblin-jester, goblin-seneschal, goblin-scout and goblin-warband have all merged (the site merges last). Each line is checked against the merged plugin, not against the rename brief.

## Automatic

- `bun run test` under `BASE_PATH=/goblin-mode`: the test "names only commands and skills the plugin registers" skips until a mod's rename is on main, then fails on any command or skill the copy names that the plugin does not register. Confirm it ran (not skipped) for all four shipped mods.
- `python3 -I site/scripts/names-scan.py` prints nothing but its summary.
- Old mod names (the coordinator's list, 2026-11-20): `grep -rnE 'goblin-util|goblin-chrome|mission-control|roadmaps\.json|mc\.py|/mc\b|\broadmap:' site/src site/scripts` and read every hit. Anything the site presents as current must use goblin-seneschal, goblin-jester, goblin-scout, goblin-warband or goblin-archivist; only quoted history keeps an old name.

## By hand

Details the ported copy assumed while the renames were still in progress. Check each in the merged plugin's README, `hooks/register.tsx` or skill file, and fix `site/src/lib/content/mod-files.ts` where it differs.

| Mod | Detail assumed | Where it appears |
|---|---|---|
| goblin-warband | `/pay-tribute <n> [@file]` keeps the old `done <n>` argument shape | IV.4 |
| goblin-warband | `/agree-tribute <n>` keeps the old `started <n>` shape | IV.4 |
| goblin-warband | `/reclaim-post` written with no argument (old `adopt coordinator\|crew`) | IV.5 |
| goblin-warband | slate keys `g` (grant) and `x` (release) unchanged | IV.3 |
| goblin-warband | `runs/` archive folder kept under `~/.claude/goblin-warband/` | how-to: remove |
| goblin-scout | pane keys `c`, `a`, `g`, `s` and digits unchanged | III.2 |
| goblin-scout | `/goblin-scout:configure-roadbook artefact <path>` keeps its `artefact` option | III.4, how-to: configure |
| goblin-scout | `branch.<name>.roadbookClaim` (decided; confirm it shipped) | how-to |
| goblin-seneschal | `/log-grievance` reply format (`logged <id>`) unchanged | I.1 |
| goblin-seneschal | state file at `~/.claude/library/state/grievances.json` | how-to |
| goblin-archivist | every skill and pane name follows decision 19; check against the merged plugin (#79) | V.1 to V.5 |

## Also

- Fixed-behaviour numbers kept by Jason's ruling (2026-11-19): "three to five bullets", "one a minute", "Three are shown", "five minutes", "four hours", "six months", "a minute". Confirm each still matches its skill or code.
- List all seven workflow trigger paths in the PR description, and say that the interview chose SvelteKit 2 and Jason moved to 3.3.1 after a side agent flagged it.

## Tutorial claims to prove on a live install

Jason ruled on 2026-11-19 that the tutorial states only what a test shows for the claims the docs leave open. Run each in a throwaway project with `HOME` and `CLAUDE_CONFIG_DIR` pointed at a scratch directory (the run's rule for loading anything unmerged), then match the copy in `site/design/content/tutorial-draft.md` to the result:

| Claim | Where it appears | Test |
|---|---|---|
| A skill marked `disable-model-invocation: true` is refused when another skill tells Claude to load it | 4.2, the 4.2b callout and the level 4 exercise | Two skills, the caller user-invocable and the callee `true`; run the caller and watch the call |
| A called skill's `model`, `effort` and `disallowed-tools` carry into the rest of its caller's turn | 3.2c, 3.3d, 4.2c | The callee pins a different model and removes `Edit`; after the call, ask the caller to edit a file and note the model |
| Answering an `AskUserQuestion` prompt counts as a new message and clears `allowed-tools` | 4.3c | A skill that approves one script, asks a question, then runs the script; note whether Claude Code prompts |
| A command comes from the folder name; `name` is shown beside it | 1.1a | A skill whose folder and `name` differ; type both |
