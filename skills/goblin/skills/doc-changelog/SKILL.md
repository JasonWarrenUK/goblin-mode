---
name: "Docs: Changelog"
description: "Build or update the changelog from conventional commits and project it to every surface the project uses"
when_to_use: "After a release tag lands (pr-land names this moment), or when the user asks for a changelog, release notes, a what's-new page, or to bring an existing CHANGELOG.md up to date."
model: haiku
effort: medium
metadata:
  glyph: ᚺ
  family: doc
disable-model-invocation: false # programmatic (built from commits), and its trigger moment follows pr-land; approval gates the write
allowed-tools: ["Read", "Glob", "Grep", "Write", "Edit", "Bash(git:*)", "Bash(gh:*)", "Bash(svu:*)"]
arguments: ["targets", "version"]
argument-hint: "[md|release|app|docs|all] [tag (optional, scopes to one release)] (default targets: md + whatever already exists)"
---

# Distro: Changelog

One source of truth, projected outward, the same shape as the roadmap system. `CHANGELOG.md` at the repo root is canonical; GitHub Releases, an in-app what's-new surface and a docs-site page are projections built from it, never written independently. A projection that drifts from the file is a bug.

## Targets

| Token | Surface | Applies when |
|---|---|---|
| `md` | `CHANGELOG.md`, Keep a Changelog layout | always; this is the source |
| `release` | GitHub Release notes per tag (`gh release`) | repo has tags on GitHub |
| `app` | structured data for an in-app what's-new surface | the app has (or wants) one |
| `docs` | changelog page in the docs site | a docs site exists |
| `all` | every surface that applies to this project | |

No arguments: build `md`, then refresh any projection that already exists in the repo (an existing release for the previous tag, an existing changelog data file or docs page). Never scaffold `app` or `docs` surfaces unasked; offer when the project looks like it wants one.

## Step 1: Establish the range

First, a **three-way state check** on `CHANGELOG.md`, same idea as `goblin:doc-readme`:

- **(a) No `CHANGELOG.md`** → build fresh from the earliest tag (or full history if untagged).
- **(b) Placeholder, or already Keep a Changelog-shaped** → a `<!-- doc-changelog: generated ... -->` marker (left as the first line by this skill from now on, mirroring `goblin:doc-readme`'s convention) or a file that's already unambiguously in Keep a Changelog structure (a prior unmarked run of this same skill) — proceed with the normal forward-generation logic below.
- **(c) Hand-written `CHANGELOG.md` in some other format/voice** → stop and flag it explicitly before writing anything: offer to convert it to Keep a Changelog format, or to respect the existing format and append new entries in its own voice instead. Don't silently Frankenstein a Keep a Changelog section onto a differently-structured hand-written file.

`git tag --sort=-v:refname` for existing tags; `svu current` for the latest version. The unit of work is tag-to-tag: each version section covers `previousTag..tag`, and `[Unreleased]` covers `latestTag..HEAD`. If `CHANGELOG.md` exists (state b), its most recent version heading shows where it stopped: only generate forward from there; never rewrite sections already published.

`$version` names a tag: scope the run to that single release (`previousTag..$version`), leaving every other section untouched. This is pr-land's hand-off; it can invoke `/doc-changelog md {tag}` right after tagging.

**Promote, don't regenerate:** when a new tag lands and `[Unreleased]` already carries curated entries, promote that content into the new version section, verify nothing in the tag range is missing (add what is), and rebuild `[Unreleased]` from `newTag..HEAD`. Hand-polish survives; only genuinely new material gets derived.

## Step 2: Build the canonical entries

For each version in range, read `git log --first-parent previousTag..tag --format='%h %s%n%b'`: with merge-commit landings this yields one commit per merged PR (plus direct-to-main commits), so each entry derives from a PR-level change rather than branch-internal noise. Stacked-PR landings preserve this: a stack merge lands each layer bottom-up with its own merge commit, so first-parent still gives one entry per PR. Fall back to the full log only when the first-parent output is too thin to describe the release. Map conventional-commit types to Keep a Changelog sections:

| Commit type | Section |
|---|---|
| `feat` | Added |
| `fix` | Fixed |
| `enhance`, `perf` | Changed |
| `BREAKING CHANGE` footer or `!` | its own **Breaking** entry, listed first |
| `refactor`, `docs`, `test`, `chore`, `ci`, `deps` | omitted unless user-visible |

Entries describe the change from the user's side ("Exports now include timestamps"), not the commit's ("add timestamp to export serialiser"). Collapse commit-level noise: one entry per coherent change, not per commit. British spelling; no em-dashes.

## Step 3: Write `CHANGELOG.md`

Keep a Changelog structure: `# Changelog` intro, `## [Unreleased]`, then `## [x.y.z] - YYYY-MM-DD` sections newest first, comparison links at the bottom when the repo is on GitHub. On a fresh build (state a/b from Step 1), the very first line is the marker comment: `<!-- doc-changelog: generated {date}. Delete this line once you hand-edit this file. -->`.

**Collapsibility for older entries.** Once the file holds more than a handful of version sections, wrap everything older than the most recent few in GFM's native `<details><summary>` — `[Unreleased]` and the newest 2-3 versions stay always-visible, older ones collapse behind a one-line summary (`<summary>0.4.0 and earlier</summary>`). No custom chevron needed. Adjusting which sections are wrapped as new versions land is presentational only — it doesn't touch a section's own entries, so it isn't the "rewrite already-published sections" the red flags below warn against.

No badge row and no separate provenance line here — each entry is already dated by construction, which is its own honesty record; a "generated on X" line would just repeat what the file already states more precisely.

Show the draft (or the diff, when updating) and **await approval** before writing.

**npm packages** (a `package.json` with no `"private": true`): check `CHANGELOG.md` ships or is reachable: either listed in `files` or linked from the README, since the npm page shows only the README. Flag whichever is missing; registry users otherwise never see release history.

## Step 4: Project

Only after `md` is approved and written:

- **`release`**: for each new tag, `gh release create {tag} --title {tag} --notes-file -` fed with that version's section verbatim (`gh release edit` when the release exists). The Release body is the section, not a rewrite.
- **`app`**: emit the structured form the app consumes. If none exists yet and the user asked for `app`, propose the simplest fit for the stack (for SvelteKit: a `changelog.json` importable by a route) and build it from the same entries.
- **`docs`**: update the docs-site changelog page from the same sections, matching that site's existing format.

## Step 5: Report

Versions covered, surfaces written, surfaces skipped and why, plus any npm visibility flag from Step 3.

## Red flags

**Never:** write a projection that disagrees with `CHANGELOG.md`; rewrite already-published version sections (corrections get an explicit edit, called out to the user); invent user-facing descriptions for changes you don't understand; quote the commit and ask.

<raw-arguments value="$ARGUMENTS" />
