# goblin-archivist: living spec

| Prop | Value |
|---|---|
| Started | 2026-11-18, from the Midden build spec |
| Status | Step 1 (the survey) built; steps 2 to 9 wait for the survey to be read and for a slicing Jason approves |
| History | [`docs/design-history/midden-spec.md`](../../docs/design-history/midden-spec.md) is the design as agreed on 2026-11-14 under the name Midden. It stays as written. This file holds every decision made since and wins wherever the two disagree |

The archivist connects every Claude Code session on one Mac to one local Obsidian vault, whatever directory the session runs in. Everything in the Midden spec still holds unless a section below changes it; read that spec's sections 2 to 7 for ownership, architecture, the roster, features, states and the facts checked on 2026-11-14, translating its words through section 1.

## 1. Name and vocabulary

Midden became goblin-ragpicker and then goblin-archivist, Jason's ruling on 2026-11-18. The archivist is a goblin, so the words are an archivist's with goblin in them. Approved word by word (raid ruling #19):

| Midden spec | Archivist |
|---|---|
| vault | vault (Obsidian's word, and it sounds suitably underground) |
| note | note (Obsidian's word) |
| schema | schema |
| canvas | canvas |
| survey (R7) | sniff |
| audit (R8) | nitpick |
| what a session leaves for the digest (transcript path, cwd, repo, branch, time) | leavings. A session makes leavings; it is not itself what gets stored |
| digest (R4) | gnaw |
| the queue; the Buried view | the pile |
| snag note | grudge. Sits beside goblin-seneschal's "grievance" (friction with Claude Code itself); Jason chose it knowing |
| déjà vu (R14, R15) | whiff |
| assumption | hunch |
| holds / doubted / fallen | holds / wobbles / toppled (glyphs `●` `◐` `○` kept) |
| fell (R11) | topple |
| wanted (R12) | holes |
| ponder (R9) | brood |
| pre-mortem (R10) | read the bones |
| capture (R18) | scribble |
| search, the librarian (R5, R17) | rummage |
| link a repo (R6) | bind. Sits beside goblin-scout's `rebind-roadbook`, which converts an old roadmap file |
| revert a digest (R19) | spit out |
| the project digest injected at session start (R1) | whisper ("whispered 38 lines") |

## 2. Surfaces

Approved by Jason on 2026-11-18. Skills run as `/goblin-archivist:<name>`; each skill's description opens with one plain line saying what it does, since several names are deliberately odd.

| Kind | Name | Roster | Does |
|---|---|---|---|
| Skill | `sniff-vault` | R7 | Survey and draft schema. **Built in step 1** |
| Skill | `nitpick-vault` | R8 | Audit against the schema; apply approved fix classes |
| Skill | `gnaw-leavings` | R4 | Gnaw the pile now |
| Skill | `rummage-vault` | R5 | The librarian: search, return conclusions with links |
| Skill | `bind-repo` | R6 | Bind this repo to its project note, or create the note |
| Skill | `brood-quandary` | R9 | Brood: the thought-experiment interview |
| Skill | `read-bones` | R10 | The pre-mortem |
| Skill | `topple-hunch` | R11 | Topple a hunch and walk its backlinks |
| Skill | `daub-canvas` | R13 | Regenerate the canvas |
| Skill | `count-holes` | R12 | Rank unresolved links |
| Skill | `whiff-grudge` | R15 | Whiff by hand |
| Bare command | `/peek-vault` | R16 | Open or close the pane |
| Hook | SessionStart | R1, R2 | Whisper; gnaw the pile in the background |
| Hook | SessionEnd | R3 | Put this session's leavings on the pile |
| Hook | PostToolUseFailure | R14 | Whiff |
| Pane key | `/` | R17 | Rummage files without a turn |
| Pane key | `c` | R18 | Scribble a line into today's daily note |
| Pane key | `o` | R20 | Open the selected note in Obsidian |
| Pane key | `u` | R19 | Spit out the selected gnawing |
| Pane key | `l`, `g`, `t`, `r` | R6, R4, R11 | Bind, gnaw now, topple, refresh |

Pane views: **here**, **pile**, **hunches**, **holes** (the Midden spec's Here, Buried, Stands on and Wanted). Header strip: `▌HERE▐   pile 3   hunches 7   holes 12`.

## 3. Decisions, 2026-11-18

| Topic | Decision |
|---|---|
| Reading the vault | Every note may be read, archived folders included |
| Reading cheaply later | Once the frontmatter is organised, read frontmatter first and bodies on demand, the way skills load their descriptions before their bodies. Input for the schema (a summary-like property) and for rummage |
| What reports may quote | Anything, since reports never enter a repository |
| Language | Python, standard library only, like goblin-scout and goblin-warband |
| YAML | A hand-written parser for the subset Obsidian properties use. Anything valid but outside it (nested maps, lists of maps, anchors) is reported verbatim as unparsed, never guessed. Anything invalid marks the block invalid, as Obsidian shows no properties for it |
| Where the vault is | The `vault` option (a directory), no default, so no vault name sits in this public repository. Empty, `sniff-vault` lists Obsidian's known vaults from its `obsidian.json` and asks |
| Where the archivist writes | The `base_folder` option, set once per machine, outside the vault: one subfolder per project named after the repository, and `vault/` for vault-wide output. Unset, every skill refuses and asks for it. Jason's is `~/.claude/docs/personal/archivist`, which the repository's `.gitignore` already covers (`docs/personal/`) |
| Survey output | `<base>/vault/sniff/`: `survey.json`, `report.md` and `schema.draft.json` from the script; `schema.notes.md` from Claude, which the script never touches |
| Draft schema | The script drafts it by fixed thresholds (required at 90% of a type's notes, optional from 10%); Claude annotates beside it; Jason rules |
| The off switch | `enabled` stops the mod registering anything and stops every skill at its first step, since skills do not pass through the mod |
| This repository | Commits the plugin, its tests and an invented fixture vault. Nothing read from the real vault is ever committed |
| Archivist properties | Every property the archivist writes carries the prefix `gob-arc-` (`gob-arc-repo`, `gob-arc-revisit`), so it is plain which mod wrote it. The Midden spec's `repo` property on a project note becomes `gob-arc-repo` |
| What the schema covers | The `gob-arc-` properties and the notes the archivist creates. Jason's own properties and `type` values stay untouched. Separately, `nitpick-vault` offers opt-in fix classes for Jason's own notes (journal migration, properties whose names differ only in case, empty duplicates), each approved as a class |
| Daily notes | The archivist follows Periodic Notes' daily folder and format, and ignores the core Daily Notes setting |
| Older journals | Migrated: daily notes named in earlier formats become the current Periodic Notes format and folders, as an opt-in `nitpick-vault` fix class, renamed through Obsidian so links survive |
| Tasks | The archivist writes no task lines, in any note. A revisit date is a `gob-arc-revisit` property on the archivist's own note (hunch, brood, bones), and the pane and the whisper surface what is due. This replaces the Midden spec's revisit tasks in §5.1, §5.5, §5.6 and R10, R11 |

## 4. Step 1: what ships

- `.claude-plugin/plugin.json`: three options, `enabled`, `vault`, `base_folder`.
- `hooks/register.tsx`: registers nothing yet; returns at once when switched off.
- `skills/sniff-vault/SKILL.md`: runs the survey, annotates the draft, walks Jason through it.
- `scripts/archivist.py`: the command line (`vaults`, `sniff`). `scripts/_frontmatter.py`: the YAML subset. `scripts/_sniff.py`: the survey, the draft and the report.
- `scripts/fixtures/vault/`: an invented vault (made-up notes, invented people only) covering broken frontmatter, nested maps, lists of maps, inline and nested tags, tags in code and URLs, custom Tasks statuses, Dataview inline fields, a canvas, a base, excluded folders, `.trash`, and Digital Garden, Share Note and Linter settings with fake secrets the survey must never print.

What the survey reports, per Midden spec step 1 and the raid brief: folder layout; note counts by apparent type and the rule that typed them; every property with its value shapes, frequency, top values, declared Obsidian type and case variants; every tag with where it was found; the templates and which templating they use; daily and periodic note settings; the Tasks plugin's statuses and every task line format in use; installed and enabled plugins; every note Digital Garden or Share Note publishes; Linter's switches and the rules that rewrite notes; and every note whose frontmatter will not parse.

**Publishing is per note.** The brief asked which folders are published. Both plugins publish note by note: Digital Garden by a `dg-publish` checkbox (`dg-home` marks the home note; docs.forestry.md, getting started, read 2026-11-18), Share Note by writing `<prefix>_link` and `<prefix>_updated`, prefix `share` unless its `yamlField` setting says otherwise (alangrainger/share-note, `src/settings.ts`, read 2026-11-18). The survey lists flagged notes grouped by folder.

## 5. Open

Each item has an answer from Jason or waits here. **After the survey** means it is settled with the report open beside the vault; **at slicing** means it is raised when steps 2 to 9 are sliced.

| # | Item | Source | State |
|---|---|---|---|
| O1 | How later writes treat published notes and Linter | Brief item 7 | Answered: guard only while a publishing plugin is enabled. With Digital Garden or Share Note switched on, the archivist never writes to a note carrying `dg-publish: true` or `<prefix>_link`; switched off, flagged notes are ordinary notes. Linter is treated the same way: while it is on, a write the archivist makes may be rewritten on save |
| O2 | Where `schema.json` lives in the vault | Brief item 8, spec §3.4 Verify | Answered: `<config folder>/archivist/schema.json`, beside the templates and visible in Obsidian, so Jason can read and edit it there. The audit skips that folder. Which config folder is a setting, never a name in this repository |
| O3 | `$.session.send` is documented for another session or an agent, never the current one; `$.prompt.submit({ text })` starts a turn in the current session (code.claude.com/docs/en/plugins/mods/api.md, read 2026-11-18). R17's hand-off and the holes view's "draft that note" change to `$.prompt.submit` | Brief item 9, spec §3.5 Verify | At slicing: tell Jason the design changes |
| O4 | How gnawing runs, on which model and at what cost. `claude -p` loads hooks and plugins unless `--bare` is passed, and `--bare` cannot use a subscription login, so a gnaw started that way fires the archivist's own SessionStart and SessionEnd and queues itself | Brief item 10 | At slicing |
| O5 | The spec's Obsidian checks (backlinks from list properties §5.1; the canvas format §5.7; cell widths in Jason's font §5.8) need the app. Running the Obsidian binary launches the app and does not return; ask Jason before anything that starts it | Brief item 11 | At slicing |
| O6 | Mismatches between the three sources, listed in section 6 | Brief item 12 | After the survey |
| O7 | Tasks features that come from what his customised format encodes; a high bar, every earlier idea was turned down | Spec §9.1 | After the survey (section 7 of the report) |
| O8 | How many lines the whisper may inject | Spec §9.2 | After the survey, from real project notes |
| O9 | Whether all four pane views stay. Jason named all four and cut none; holes goes first if the pane feels crowded | Spec §9.3, §5.8 Assumed | Answered for now |
| O10 | Whether Obsidian leaves dot-folders out of its index | Spec §3.4 Verify | Moot: the schema lives in a visible folder (O2) |
| O11 | Whether a second mod can draw in the band | Spec §5.8 Verify | Answered: since Claude Code 2.1.323 each mod that draws in the band gets its own row (code.claude.com/docs/en/plugins/mods/interface.md, read 2026-11-18) |
| O12 | Heavy rule and half-block characters at the round border's cell width in Jason's font | Spec §5.8 Verify | Pane slice; check with `ghostty +show-face --string=` |
| O13 | Whether `session_id`, `transcript_path`, `cwd` and `hook_event_name` reach every hook event | Spec §7 | Hooks slice |
| O14 | What `${user_config.enabled}` and an unset `directory` option substitute to in skill content. `sniff-vault` treats empty and the literal `${user_config...}` as unset; the boolean's text is unchecked | New | First live run of the skill |

## 6. Mismatches between the sources (O6)

| Claim | Midden spec | Design page | Goblin Mode Notice |
|---|---|---|---|
| How whiff matches | Normalised signature, equal or token overlap above a tuned threshold (§5.4) | "compared word for word" | Not said |
| The band | Verify whether a second mod can draw in it (§5.8) | Marked open | Described as working: "the band says so" when a repo has no note |
| States around a session | Seven situations (§6) | Four | Not said |
| Pane views | Four, assumed (§5.8) | Four, assumed | The roster leaves "the pane's four views" unticked, with no scene |
| Counts | 20 actions (R1 to R20), 6 note types, 9 build steps | Statline: 20 actions, 6 note types, 4 pane views, 9 build steps | "Twenty action planned. Six kind of note" |

The counts agree. The band is now settled by O11, so the Notice's line becomes true once the band slice ships.

## 7. For the pane slice

The pane takes the wordmark every goblin-mode pane carries in the right of its header card (raid decree 7, ruling #11): the body lives in goblin-warband's `hooks/register.tsx` (`WORDMARK_WORD`, `WORDMARK_GAP`, `WORDMARK_MIN_FACTS`, `wordmark`, `cells`, `fit`, `packFacts`, `headerLayout` and the drawing block; introduced in commit `33f7ee8`, lines 828 to about 905). Paste it whole and change only `WORDMARK_WORD` to `ARCHIVIST` (17 cells); copy the three tests beside it in `hooks/warband.test.tsx` (lines 171, 178 and 191 in that commit). Read the file on main if the hash has gone.

## 8. Checks

| Check | Command, from the repository root |
|---|---|
| Survey and parser tests | `cd marketplace/goblin-archivist/scripts && python3 -m unittest discover -p 'test_*.py'` |
| Manifest and module | `claude plugin validate marketplace/goblin-archivist --strict` |
| Mod tests | `claude plugin test marketplace/goblin-archivist` |
| Types | `tsc -p marketplace/goblin-archivist`, once the engine's declarations sit in `.claude-plugin/types/` |
