# Pre-PR checks for the site

Run after the one rebase onto main, once goblin-jester, goblin-seneschal, goblin-scout and goblin-warband have all merged (the site merges last). Each line is checked against the merged plugin, not against the rename brief.

## Automatic

- `bun run test` under `BASE_PATH=/goblin-mode`: the test "names only commands and skills the plugin registers" skips until a mod's rename is on main, then fails on any command or skill the copy names that the plugin does not register. Confirm it ran (not skipped) for all four shipped mods.
- `python3 -I site/scripts/names-scan.py` prints nothing but its summary.

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
| goblin-archivist | every skill and pane name follows decision 19; unbuilt, so check against its spec, not code | V.1 to V.5 |

## Also

- Fixed-behaviour numbers kept by Jason's ruling (2026-11-19): "three to five bullets", "one a minute", "Three are shown", "five minutes", "four hours", "six months", "a minute". Confirm each still matches its skill or code.
- List all seven workflow trigger paths in the PR description, and say that the interview chose SvelteKit 2 and Jason moved to 3.3.1 after a side agent flagged it.
