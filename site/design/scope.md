# Goblin Mode site: scope

| Prop | Value |
|---|---|
| Updated | 2026-11-18 |
| Task | SITE, run "Goblin Mode Enhancements" |
| Branch | `feat/goblin-mode-pages-site` |
| Status | Front page in design; nothing built |

Every line below is a decision Jason made in the SITE interview on 2026-11-18, unless it is marked **assumed**.

## Site

| Id | Requirement |
|---|---|
| R1 | SvelteKit 2, Svelte 5, `adapter-static`, Bun, TypeScript strict. One build command. |
| R2 | Served from GitHub Pages at `jasonwarrenuk.github.io/goblin-mode/`; base path `/goblin-mode`, no custom domain. |
| R3 | The site takes over `site/`: it carries the Goblin Mode Notice and the skill explainers. The Vercel project `skill-explainers` is retired afterwards as Jason's step. |
| R4 | Routes: `/` (front page), `/mods/<mod>/` (one page per mod), `/skills/` and `/skills/<page>/` (the explainers wing). |
| R5 | One theme, `goblin` (`.claude/themes/goblin.json`, `goblin-html.json`). Colour, type and shape come from its tokens; no inline hex in components. Fonts self-hosted. |
| R6 | One goblin writes the whole site: the notice's goblin, in the notice's three registers (pedant on typewriter, goblin in marker, plain instruction on printed slips). No per-mod persona voice. |
| R7 | Counts and facts (lines of code, skill counts, versions) are generated at build from the repository, never hand-written. |
| R8 | Mod names, commands and skills follow the rename table: goblin-seneschal, goblin-jester, goblin-scout, goblin-warband, goblin-archivist. |
| R9 | No published page names a real person other than Jason; invented people only (`ravi`, `noor`, `tam`). |
| R10 | Works at 1280 and 390 wide, light and dark, with reduced motion respected and every interactive element reachable by keyboard. No horizontal page scroll. |

## Audience

| Id | Requirement |
|---|---|
| A1 | Curious developers who might install a mod, or who want to learn how to build their own. |
| A2 | Primary action on the front page: install a mod. Secondary: read a mod's page; learn to build in the skills wing. |

## Front page

| Id | Requirement |
|---|---|
| F1 | Keeps the title notice ("Every Human Need Goblin Mode") and its why. |
| F2 | Keeps the two schedules, Snacks (goblin-seneschal, goblin-jester) and Feasts (goblin-scout, goblin-warband, goblin-archivist). |
| F3 | Gains an install slip: the marketplace add command and an install command. It is the only place that answers how to install; opening a folder switches its picker to that mod. |
| F4 | Layout is a desk of papers, replacing the artifact's single vertical scroll: the notice pinned, the five mods as cardboard folders laid out by schedule, the install slip taped beside the notice. Folders run as banded rows at 390. |
| F5 | Clicking a folder opens a drawer notched under it, holding the mod's name, Deficiency and Remedy, the goblin's paragraph and a link to its page. One drawer at a time; the page scrolls so the pressed folder stays still. The page loads with every folder shut. |
| F6 | The ledger table and the sources slip leave the front page. The lede carries the why; each folder carries its own Deficiency and Remedy. |
| F8 | Each open drawer quotes the mod's persona line (its README opener) under its name, in the printed face, set apart from the goblin. A mod without a settled line shows none. |
| F7 | Closed folders name what the mod does in plain words; the joke lives in the drawer. Status uses one vocabulary: stamps "Goblin Approve" and "Soon. Very Soon.", meta line "goblin-approved" and "soon". |

### Front page regions

| Region | Holds | Actions |
|---|---|---|
| Notice | eyebrow, theme toggle, title, lede (one generated count), meta line (5 generated facts; hidden at 390) | 3 theme buttons |
| Install slip | 2 commands, the longest 57 characters of monospace; a picker of the installable mods (4 today) | 2 copy buttons, 1 picker |
| Schedule header (x2) | title, one sentence with 1 or 2 generated counts | none |
| Folder, closed (x5) | numeral, name, one-line plain description, status stamp | the folder itself (open or close) |
| Drawer, open (one at a time) | mod name, 2 labelled fields, 1 goblin paragraph, 1 link; archivist adds a stamp | 1 link |
| Box file | label, one sentence, 5 links | 5 links |

## Mod pages

| Id | Requirement |
|---|---|
| M1 | One page per mod carrying the detail: a header with its install line, numbered tabs, every situation in order and folded to its number, title and when-it-applies line (a tab or roster link opens the one it names), its roster pinned beside them (at the end at 390) and previous/next links. No sources slip on mod pages (Jason, 2026-11-18). |
| M4 | After the situations, "How to Use It" as collapsed slips: install and first run, configure it (the plugin's options, generated from `plugin.json`), commands and skills (generated from each skill's file), turn it off or remove it. |
| M5 | Copy rule (proposed in the mod-page wireframe): scenes and "Before" keep everyday words; "With" and the Ruling use each mod's own vocabulary (decisions 7, 10, 19). |
| M2 | goblin-seneschal keeps clauses I.5 and I.7: `audit-prose` and `consult-dossiers` move into the plugin (decision 14). |
| M3 | goblin-archivist is shown as proposed, under its new name, with its five clauses; updated by hand when it ships. Nothing read from the vault. |

## Skills wing

| Id | Requirement |
|---|---|
| S1 | Explainers re-dressed in the goblin theme; their family hue survives only as an accent. |
| S2 | "A Skill Is One Goblin", "Metadata Is Whatever I Say It Is" and "Everyone Gets a File": reworked section by section with Jason. |
| S3 | "Some Assembly Required": kept in spirit; its baseline assumptions rethought (for instance, loose skills against a plugin). |
| S4 | "Bob Will Not Open the Deep Dive": reworked as one red family page (`red-doc` and `red-branch` on the shared methodology), keeping the premise, the kill shot and Bob, with goblin flavour. |

## Delivery

| Id | Requirement |
|---|---|
| D1 | One PR for everything. |
| D2 | Deployed by a committed workflow under `.github/workflows/`, on any push to main touching what the generator reads: `marketplace/**`, `.claude-plugin/**`, `skills/**`, `site/**` or the workflow file (decision 18). |
| D4 | Mod names and install commands are read from `.claude-plugin/marketplace.json` at build. The site merges last, after every rename PR (decision 18). |
| D3 | Tests: a build check and a check that every in-page link resolves. |

## Skills wing: the tutorial

| Id | Requirement |
|---|---|
| T1 | "Some Assembly Required" is five levels, one page each (`/skills/tutorial/1/` to `/5/`), one invented skill (`tidy-imports`) growing through them, a real repository skill as The Real Thing from level 2. Plain voice throughout; full desk look. |
| T2 | Each level is the approved hybrid (mockup v3): a pinned specimen sheet holding the step's write-up and the file, built up in lockstep; one gesture per step, snapped, scoped to the stage; the release costs one step; The Real Thing rises after; Steps/File toggle at phone width; static fallback under reduced motion or no JS. Callouts numbered by step. |
| T3 | Every step is written to fit a 760px-tall window: a long step is split in two, and a long file shows its changed region with the rest folded as `...`. Below a minimum height the page uses the scrolling Steps/File layout. Nothing scrolls inside the sheet. |
| T4 | A step that touches more than one file shows them as folder tabs across the specimen, opening on the file the step changes; callouts belong to the visible file. |
| T5 | Every step's write-up stays in the accessibility tree; screen readers take priority over find-in-page. |
