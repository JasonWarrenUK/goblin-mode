---
name: "Docs: Changelog"
description: "{{ ƔƔƔ }} Build or update the changelog from conventional commits and project it to every surface the project uses"
when_to_use: "After a release tag lands (pr-land names this moment), or when the user asks for a changelog, release notes, a what's-new page, or to bring an existing CHANGELOG.md up to date."
model: sonnet
disable-model-invocation: false # programmatic (built from commits), and its trigger moment follows pr-land; approval gates the write
allowed-tools: ["Read", "Glob", "Grep", "Write", "Edit", "Bash(git:*)", "Bash(gh:*)", "Bash(svu:*)"]
arguments: ["targets"]
argument-hint: "[md|release|app|docs|all] (default: md + whatever already exists)"
---

# Distro: Changelog

One source of truth, projected outward — the same shape as the roadmap system. `CHANGELOG.md` at the repo root is canonical; GitHub Releases, an in-app what's-new surface and a docs-site page are projections built from it, never written independently. A projection that drifts from the file is a bug.

## Targets

| Token | Surface | Applies when |
|---|---|---|
| `md` | `CHANGELOG.md`, Keep a Changelog layout | always — this is the source |
| `release` | GitHub Release notes per tag (`gh release`) | repo has tags on GitHub |
| `app` | structured data for an in-app what's-new surface | the app has (or wants) one |
| `docs` | changelog page in the docs site | a docs site exists |
| `all` | every surface that applies to this project | |

No arguments: build `md`, then refresh any projection that already exists in the repo (an existing release for the previous tag, an existing changelog data file or docs page). Never scaffold `app` or `docs` surfaces unasked — offer when the project looks like it wants one.

## Step 1 — Establish the range

`git tag --sort=-v:refname` for existing tags; `svu current` for the latest version. The unit of work is tag-to-tag: each version section covers `previousTag..tag`, and `[Unreleased]` covers `latestTag..HEAD`. If `CHANGELOG.md` exists, its most recent version heading shows where it stopped — only generate forward from there; never rewrite sections already published.

## Step 2 — Build the canonical entries

For each version in range, read `git log previousTag..tag --format='%h %s%n%b'` and map conventional-commit types to Keep a Changelog sections:

| Commit type | Section |
|---|---|
| `feat` | Added |
| `fix` | Fixed |
| `enhance`, `refactor`, `perf` | Changed |
| `BREAKING CHANGE` footer or `!` | its own **Breaking** entry, listed first |
| `docs`, `test`, `chore`, `ci`, `deps` | omitted unless user-visible |

Entries describe the change from the user's side ("Exports now include timestamps"), not the commit's ("add timestamp to export serialiser"). Collapse commit-level noise: one entry per coherent change, not per commit. British spelling; no em-dashes.

## Step 3 — Write `CHANGELOG.md`

Keep a Changelog structure: `# Changelog` intro, `## [Unreleased]`, then `## [x.y.z] — YYYY-MM-DD` sections newest first, comparison links at the bottom when the repo is on GitHub. Show the draft (or the diff, when updating) and **await approval** before writing.

**npm packages** (a `package.json` with no `"private": true`): check `CHANGELOG.md` ships or is reachable — either listed in `files` or linked from the README, since the npm page shows only the README. Flag whichever is missing; registry users otherwise never see release history.

## Step 4 — Project

Only after `md` is approved and written:

- **`release`** — for each new tag: `gh release create {tag} --title {tag} --notes-file -` fed with that version's section verbatim (`gh release edit` when the release exists). The Release body is the section, not a rewrite.
- **`app`** — emit the structured form the app consumes. If none exists yet and the user asked for `app`, propose the simplest fit for the stack (for SvelteKit: a `changelog.json` importable by a route) and build it from the same entries.
- **`docs`** — update the docs-site changelog page from the same sections, matching that site's existing format.

## Step 5 — Report

Versions covered, surfaces written, surfaces skipped and why, plus any npm visibility flag from Step 3.

## Red flags

**Never:** write a projection that disagrees with `CHANGELOG.md`; rewrite already-published version sections (corrections get an explicit edit, called out to the user); invent user-facing descriptions for changes you don't understand — quote the commit and ask.

<raw-arguments value="$ARGUMENTS" />
