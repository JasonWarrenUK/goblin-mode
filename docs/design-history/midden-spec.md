← [Wiki home](../README.md)

# Midden: build spec

| Prop | Value |
|---|---|
| Drafted | 2026-11-14, in a cloud session with no access to the vault |
| Status | Design agreed with Jason; nothing built |
| Reader | A Claude Code session on Jason's Mac, which can see the vault |
| Home | `marketplace/midden/`, the fifth plugin in this repo's marketplace |

Midden connects every Claude Code session on the Mac to one local Obsidian vault, whatever directory the session runs in. A midden is the heap archaeologists dig through to learn how people lived; the name is a fair description of the vault today.

## 0. How to use this document

Precedence when sources disagree:

| Question | Winner |
|---|---|
| What midden does and when | §4, the roster. An action not listed there does not happen |
| Note shape, properties and tags | The owner named in §2, once §8 step 1 has produced it |
| How a mod is laid out, validated and tested | `docs/reference/mods.md` and Anthropic's mods docs |
| Anything about the vault's real contents | The vault. This spec was written blind and guesses nothing about it |

Three line kinds appear below. **Decided** lines are settled with Jason and are not reopened without him. **Assumed** lines are my call, flagged for him to overrule. **Verify** lines are facts the Mac session must check before relying on them.

## 1. Decisions from the interview

| Topic | Decision |
|---|---|
| Vault location | Local to one Mac, no sync. Cloud sessions and other machines never reach it |
| Current structure | Daily notes, project notes, frontmatter and tags, all in inconsistent use |
| Plugins in use | Templater or Templates; Tasks, with a heavily customised schema; Dataview and Bases inconsistently |
| Existing Dataview and Bases fields | Free to break. The schema is designed fresh and old fields are migrated or dropped |
| Write trust | Full edit |
| Undo | Local git repository inside the vault, no remote |
| Obsidian app | Open sometimes. Hybrid access: plain files by default, the CLI where only the app can do the job |
| Repo to project note | A `repo` frontmatter property on the project note |
| Session logging | SessionEnd queues; a digest runs automatically at the next session start |
| Surfaces | Slash commands, a pane, a band hint, an HTML audit report |

## 2. Ownership

One owner per fact. Everything else points at the owner.

| Fact | Owner |
|---|---|
| What Claude learned about a repo | Native auto memory, in its default location. Midden never writes there and never copies from it |
| What Jason wrote: specs, decisions, research | Vault notes |
| What happened in a session | The daily note for that day |
| A project's session history | Nobody stores it. It is the project note's backlinks (§5.2) |
| What a well-formed note looks like | `schema.json` in the vault |
| Where the vault is | The plugin's `userConfig` |
| Project work as a dependency graph | The roadmap plugin. Midden links to roadmap IDs and never copies tasks out of it |
| The assumption graph | The assumption notes and their links. The canvas (§5.7) is a projection, regenerated and never edited by hand |
| The snag index (§5.4) | Derived data outside the vault, rebuildable from snag notes at any time |

`autoMemoryDirectory` stays unset: pointing it at the vault would put Claude's scratch notes in the graph and in search.

## 3. Architecture

### 3.1. Access layer

TypeScript on Bun, one module that every hook, skill and script goes through. Two backends:

| Operation | Backend | When the app is closed |
|---|---|---|
| Search, read, append, create | Plain files | Works |
| Frontmatter read and write | Plain files | Works |
| Wikilink parse, unresolved-link scan | Plain files | Works |
| Rename, move | Obsidian CLI (`rename`, `move`) | The CLI's first command launches the app; slower, still works |
| Backlinks | CLI when the app is open, file scan otherwise | Works |
| Bases queries | CLI (`base:query`) | Launches the app |

Renames and moves never happen on plain files. Obsidian's link updating is an app feature, and the docs do not say it applies to renames made outside the app.

### 3.2. Reach

Setup adds the vault path to `permissions.additionalDirectories` in user settings. That grants file access from every session on the machine. It does not load skills or `CLAUDE.md` from the vault, which is why midden ships its skills in the plugin.

### 3.3. Git net

- `git init` in the vault, no remote. Ignore `.obsidian/workspace*.json` and any cache files the survey finds.
- Every write batch makes two commits. First a snapshot of whatever is uncommitted, so Jason's own edits are never mixed into Claude's diff. Then Claude's change, with the session ID in the commit body.
- Automatic writes (the digest) only append. Rewrites happen only from an approved audit fix or an explicit command.

### 3.4. Schema

`schema.json` lives in the vault under a dot-folder (**Verify**: that Obsidian leaves dot-folders out of its index). It defines:

- Note types: `daily`, `project`, `assumption`, `ponder`, `premortem`, `snag`, plus whatever the survey finds in real use.
- Required and optional properties per type, with Obsidian property types. A property name has one type across the whole vault; Obsidian enforces that.
- The tag taxonomy.
- The Tasks line format Jason uses, captured from the vault and reproduced exactly.
- Where each type lives and which template creates it.

Templates are audited against the schema like any other file, so a template cannot become a second owner of note shape.

### 3.5. Mod

Laid out per `docs/reference/mods.md`: `hooks/hooks.json`, `hooks/register.tsx`, `types/index.d.ts`, one `userConfig` switch that turns all of it off, colours from the project theme. Vault data reaches the pane the way roadmap's ready set reaches `/ready`: `marketplace/roadmap/hooks/register.tsx` runs the plugin's CLI through `$.process.run` and draws the JSON it returns. Midden does the same with its own CLI. **Verify** that `$.session.send` can address the current session, which R17 and the Wanted view rely on.

## 4. Roster

Every action midden takes. An action not in this table does not happen.

| # | Trigger | Action | Vault writes |
|---|---|---|---|
| R1 | SessionStart | Resolve the cwd's git remote to a project note by `repo`; inject a capped digest of the note and its path | None |
| R2 | SessionStart | If the queue is non-empty, start the digest (R4) in the background | Via R4 |
| R3 | SessionEnd | Append transcript path, cwd, repo, branch and time to the queue. Must finish inside the 1.5 second budget, so no summarising here | None; the queue is outside the vault |
| R4 | R2, or `/midden digest` | Claim queued sessions under a lock, summarise each into its day's daily note with a link to the project note, write snag notes (§5.4), rebuild the snag index | Append; create snag notes |
| R5 | `/midden search`, or Claude answering a recall question | The librarian subagent searches the vault and returns conclusions with links, keeping file contents out of the main context | None |
| R6 | `/midden link` | Bind the current repo to a project note by setting `repo`, or create the note from its template | Edit or create |
| R7 | `/midden survey` | Read the vault, report what is there, propose `schema.json` | Schema only, after approval |
| R8 | `/midden audit` | Deterministic script lists schema violations; render the HTML report; apply approved fix classes, one commit per class | Full edit, approved classes only |
| R9 | `/midden ponder` | Run a thought experiment as an interview; write the ponder note and its assumption notes (§5.5) | Create |
| R10 | `/midden premortem` | Run a pre-mortem on the current project (§5.6) | Create; add tasks |
| R11 | `/midden fell <assumption>` | Mark an assumption fallen; walk its backlinks; report and flag every dependent (§5.1) | Edit; add tasks |
| R12 | `/midden wanted` | Rank unresolved wikilinks by inbound count (§5.3) | None |
| R13 | `/midden canvas` | Regenerate the assumption graph as a `.canvas` file (§5.7) | Overwrite one generated file |
| R14 | PostToolUseFailure | Look the failure up in the snag index; on a hit, inject one line (§5.4) | None |
| R15 | `/midden seen <text>` | The same lookup as R14, on demand | None |
| R16 | Pane and band redraw | Draw the views and band segment of §5.8 from one snapshot | None |
| R17 | Pane `/` | Search the vault by file search; open a hit in Obsidian or hand its path to Claude. No model turn | None |
| R18 | Pane `c` | Append one typed line to today's daily note with a link to the project. No model turn | Append |
| R19 | Pane `u` | Revert the selected digest's commit | Git revert |
| R20 | Pane `o` | Open the selected note in Obsidian by URI | None |

Pane keys `l`, `d` and `f` run R6, R4 and R11; they are the same actions, reached from the pane.

Deliberately absent: a search on every prompt, any write to auto memory, any copy of roadmap tasks, any automatic creation of project notes.

## 5. Features

### 5.1. Assumptions as notes

An assumption is an atomic note of type `assumption` with a `status` of `holds`, `doubted` or `fallen`. Ponder notes, pre-mortems and decision notes link to the assumptions they stand on. A conclusion can itself be an assumption for something else.

R11 is the payoff. When an assumption falls, its backlinks are the list of conclusions now in doubt. The command sets the status, walks backlinks transitively to a fixed depth, reports the affected notes and adds a revisit task to each in Jason's Tasks format. It reports and flags; it does not rewrite any conclusion.

**Verify**: whether a wikilink inside a list property counts as a link for backlinks. If it does, use an `assumes` property, which Bases can query. If it does not, use a `## Stands on` section in the body.

### 5.2. Backlinks as the session index

Each digest entry in a daily note links to its project note. The project note's backlinks are therefore its session history, with nothing stored twice and nothing to keep in step. The entry format waits for the survey, since it has to sit inside whatever the daily notes already look like.

### 5.3. Most-wanted notes

The digest and `/midden ponder` may link to a note that does not exist when a concept keeps coming up without a home. R12 parses every wikilink, subtracts existing note names and aliases, and ranks what remains by inbound count.

The audit must never report an unresolved link as a violation. Unresolved links are how this feature stores its data.

### 5.4. Déjà vu

The first version searched the whole vault whenever a session hit trouble, which would fire constantly and match badly. This version narrows both ends, and Jason has confirmed it.

- **Corpus:** snag notes only. When the digest sees a failure followed by a fix in a transcript, it writes a note of type `snag`: the error text verbatim, the cause, the fix, the repo and a link to the session's daily note.
- **Signature:** the error text normalised by stripping paths, numbers, hashes and quoted values, then lowercased. Matching is lexical: equal signatures, or token overlap above a threshold tuned on real snags. No embeddings, no model call.
- **Trigger:** R14 computes the signature of a failed tool call and looks it up in the index, a JSON file outside the vault. A hit injects one line holding the snag's link, where and when it happened and the fix in a sentence. Each signature fires at most once per session. Claude decides whether to read the note.
- **Budget:** the hook does one file read and a hash lookup. If it cannot answer in about 100 ms it exits silently.
- **Off switch:** its own `userConfig` flag, separate from the master switch, because this is the feature most likely to annoy.

It cannot see a problem that never produces a tool failure (a design going wrong slowly, say); R15 covers that by hand. It also misses an error whose wording changed between versions of a tool.

Cost: snag notes accumulate, and their quality depends entirely on the digest spotting a failure and its fix. Review the first twenty snags against their transcripts before trusting the hook.

### 5.5. Ponder

A note type with: the premise; linked assumptions (§5.1); the strongest case for each side; what would change Jason's mind; a revisit date as a task in his Tasks format. The skill runs as an interview, then argues the side he did not take, then writes the note. Existing assumption notes are reused by search before any new one is created, since shared assumptions are what make §5.1 worth having.

### 5.6. Pre-mortem

"It is six months on and this project is dead: why?" The skill seeds itself from the project note and the session history in its backlinks, then proposes causes for Jason to rank. Each accepted cause becomes a task, and each names the assumption that would have had to be false, linked or created as an assumption note. A pre-mortem therefore feeds the same graph as a ponder.

### 5.7. Canvas

R13 writes one `.canvas` file showing assumptions, the notes standing on them and status by colour. It is a projection: regenerated from the notes each time, so hand-arranged layout is lost on the next run. **Verify** the JSON Canvas format against Obsidian's published `obsidian-skills` repository, which has a `json-canvas` skill.

### 5.8. Pane, band and toasts

Obsidian is the better note reader, so the pane is not one. It sits beside a session and shows two flows: what from the vault bears on this session, and what from this session is heading into the vault. `/midden` opens and closes it. It never opens itself; the band carries ambient state.

Data comes from one CLI call that returns a JSON snapshot, run through `$.process.run` as roadmap's pane does. The pane refreshes on open, on `r` and after a digest.

**Views** (**Assumed**: Jason approved the layout and cut none of them). A key switches view; the header strip shows each view's count.

| View | Shows | Keys |
|---|---|---|
| Here (default) | Binding, how much Claude was injected with, the project's assumptions by status, recent sessions from backlinks, déjà vu hits this session | `l` link when unbound |
| Buried | Sessions queued for digest with their age, recent digests, audit count | `d` digest now, `u` revert the selected digest's commit |
| Stands on | The assumption graph as a tree, fallen first with their dependents | `f` fell the selected assumption |
| Wanted | Unresolved links ranked by inbound count | A digit asks Claude to draft that note |

Every view takes `/` (search), `c` (capture), `o` (open the selected note in Obsidian through the `obsidian://open` URI) and `r`.

**Turn-free actions.** `/` takes a query, runs the file search and lists hits; a digit opens the hit in Obsidian or hands its path to Claude. `c` takes one line and appends it to today's daily note with a link to the project. Neither spends a model turn, and capture never reaches Claude's context. This is the pattern goblin-util's `/pain` already uses.

**Chrome.** Jason asked for more of it than the first sketch had. The Here view:

```text
╭─ midden ───────────────────────────── goblin-mode ─╮
│ ▌HERE▐   buried 3   stands on 7   wanted 12        │
╰────────────────────────────────────────────────────╯
╭─ PROJECT ──────────────────────────────── ● bound ─╮
│ [[Goblin Mode]]                                    │
│ Claude was told 38 lines at session start          │
╰────────────────────────────────────────────────────╯

━━ STANDS ON ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2 ━
 ●  Mods stay terminal-only
 ◐  One marketplace is enough                  doubted

━━ RECENT SESSIONS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2 ━
 1  12 Nov  crew context fill surfaced
 2  09 Nov  mission-control 0.12 changelog

━━ SEEN BEFORE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 0 ━
 ╌  nothing yet this session

╭────────────────────────────────────────────────────╮
│ / search   c capture   o obsidian   l link   r     │
╰────────────────────────────────────────────────────╯
```

The type scale, using only what the existing panes already draw (`bold`, `dimColor`, theme colour keys, round borders):

| Level | Treatment |
|---|---|
| Pane header | Round frame; plugin name in the top border at the left, repo at the right; active view in capitals, bold, between half-blocks; other views dim with their counts |
| Card | Round frame with a capitals label in the border and a status at the right. Used only for things that do not scroll |
| Section heading | Heavy rule, capitals bold label, dim rule, count at the right |
| Subgroup (Stands on tree) | Light dashed rule, lowercase dim label |
| Row | Two-column glyph or digit gutter, text at normal weight, metadata dim and right-aligned |
| Key legend | Round frame pinned at the bottom; keys bold, labels dim |

Frames cost two rows and four columns each, so only the three fixed regions get one. Scrolling sections get rules, which cost one row and no columns.

Colour is theme keys only, per CLAUDE.md §7.5: frames `subtle`, active view `claude`, holds `success`, doubted `warning`, fallen `error`, déjà vu `suggestion`. Status always has a glyph too (`●` holds, `◐` doubted, `○` fallen), so colour is never the only signal.

**Verify**: that the engine draws the heavy rule and half-block characters at the same cell width as the round border in Jason's terminal font; if not, fall back to roadmap's light rule with a bold label.

**Band.** One segment showing the most urgent state, in this order: unreachable, a queued session nearing transcript deletion, a fallen assumption under this project, unbound, bound. **Verify** whether a second mod can draw in the band or whether goblin-chrome owns it; if it owns it, midden publishes its state in its contract and goblin-chrome reads it.

**Toasts.** Digest finished, a déjà vu hit, an assumption falling under the current project.

## 6. States

| Situation | SessionStart | Logging | Commands |
|---|---|---|---|
| Vault path unset or unreachable | Exit quietly; band says unreachable | Queue still fills, so nothing is lost once the vault returns (30-day limit, §7) | Each explains the vault is unreachable and stops |
| Cwd is not a git repository | No injection | Digest writes to the daily note with the directory name and no project link | All work except `link` and `premortem` |
| Repository with no bound note | No injection; band says unbound | Daily note entry names the repo as plain text. No project note is created | `link` offers to bind or create |
| Repository bound | Inject the digest | Full | All |
| Two sessions start together | Both run R2 | The lock in R4 lets one digest and the other skip | Unaffected |
| App closed | Unaffected | Unaffected | Rename, move and Bases queries launch the app |
| Master switch off | Nothing runs | Nothing queues | Commands say midden is off |

## 7. Facts checked on 2026-11-14

Checked against the docs by subagents in the drafting session. Re-check anything load-bearing; these surfaces move.

Claude Code ([memory](https://code.claude.com/docs/en/memory.md), [permissions](https://code.claude.com/docs/en/permissions.md), [hooks](https://code.claude.com/docs/en/hooks.md), [sessions](https://code.claude.com/docs/en/sessions.md)):

- Auto memory is stored per git repository under `~/.claude/projects/<project>/memory/`. The first 200 lines or 25KB of `MEMORY.md` load each session.
- `permissions.additionalDirectories` in user settings applies to every session and grants file access only.
- SessionStart, UserPromptSubmit, PreToolUse, PostToolUse and PostToolUseFailure hooks can inject context. Hook input commonly carries `session_id`, `transcript_path`, `cwd` and `hook_event_name`; that all four appear on every event was not confirmed.
- SessionEnd cannot block or inject and has a default budget of 1.5 seconds.
- Transcripts are JSONL at `~/.claude/projects/<project>/<session-id>.jsonl`. The format is internal and may change. They are deleted after 30 days by default (`cleanupPeriodDays`).
- User-scope plugins apply to every project on the machine and do not load in cloud sessions.

Obsidian ([CLI](https://obsidian.md/help/cli), [properties](https://obsidian.md/help/properties), [Bases syntax](https://obsidian.md/help/bases/syntax), [storage](https://obsidian.md/help/Files+and+folders/How+Obsidian+stores+data)):

- The official CLI has been public since 1.12.4 (27 February 2026); the docs ask for installer 1.12.7 or later. It is enabled under Settings, General, "Command line interface". It needs the app running and launches it on the first command.
- CLI commands include `search`, `read`, `create`, `append`, `daily:append`, `properties`, `property:set`, `tags`, `backlinks`, `tasks`, `rename`, `move`, `base:query` and `eval`.
- Obsidian supports external edits and refreshes the vault to pick them up. No official warning about concurrent writes was found.
- The singular properties `tag`, `alias` and `cssclass` were dropped in 1.9; use `tags`, `aliases`, `cssclasses`.

Consequences for the design: the transcript reader is the most fragile part, so isolate it in one module with tests against real transcripts. A queued session older than about 20 days needs a band warning, since at 30 its transcript is gone.

## 8. Build order

Each step ends with a check against the source, made by something other than the code that did the work.

1. **Survey.** Read-only. Report folder layout, note counts by apparent type, every property name with its value shapes and frequency, the tag list, the templates, the Tasks line formats in use and the installed plugins from `.obsidian/`. Propose `schema.json`. *Check:* Jason reads the report beside the vault and corrects it. Nothing is written until he approves the schema.
2. **Access layer and git net.** *Check:* a scripted run that edits, renames and moves notes in a copy of the vault, then a diff of every link before and after.
3. **Link and injection** (R1, R6). *Check:* open sessions in a bound repo, an unbound repo, a non-repo directory and with the vault path broken; confirm each row of §6.
4. **Queue and digest** (R2 to R4, §5.2). *Check:* Jason reads the first ten digest entries against what he remembers of those sessions; a subagent told to find faults compares five entries with their transcripts.
5. **Audit and report** (R8). *Check:* apply each fix class to a copy first; spot-check twenty changed notes rendered in Obsidian beside their originals.
6. **Assumptions, ponder, pre-mortem, fell** (R9 to R11, §5.1, §5.5, §5.6).
7. **Most-wanted and canvas** (R12, R13).
8. **Déjà vu** (R14, R15, §5.4). Last, because it needs a stock of snags from step 4 to tune against.
9. **Pane and band** (R16).

Steps 6 to 9 are independent of each other once step 4 is done.

## 9. Open questions for Jason

1. **Tasks.** Jason wants to exploit his customised Tasks schema and rejected every idea offered so far (loose ends as tasks, due-here injection, a morning block, a weekly pattern note) as not compelling. Tasks appear in this spec only as revisit dates and pre-mortem causes. After the survey has read the schema, propose Tasks features that come from what it encodes, and expect a high bar.
2. **R1 digest size.** "Capped" has no number yet. Choose one after seeing real project notes and confirm it with him.
3. **Pane views.** All four are in by assumption (§5.8). Wanted is the first to cut if the pane feels crowded.

---
← [Wiki home](../README.md) · [Mods](../reference/mods.md)
