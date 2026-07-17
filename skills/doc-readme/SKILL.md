---
name: "Docs: Readme"
description: "{{ ƔƔƔ }} Create or update a README — project root or any directory"
when_to_use: "When a project or directory has no README, or its existing one no longer matches the current structure or setup steps."
model: sonnet
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Write", "Edit", "Bash(git:*)", "Bash(~/.claude/library/scripts/git-doc-history.sh:*)"]
arguments: ["mode", "target"]
argument-hint: "[create|update] [directory, default ./]"
---

# README create/update

Replaces the former doc-readme-create / doc-readme-create-sub / doc-readme-update trio: `$mode` picks the verb, `$target` picks the directory (project root when empty). If `$mode` is empty, infer it: README exists at the target → `update`; absent → `create`. Say which you inferred.

## Mode: create

1. Confirm the target directory exists; stop and report if not.
2. Analyse it: purpose, contents, structure, key modules, build system, existing docs. For a sub-directory, read the surrounding context too (parent README, siblings, project docs) to place it in the codebase.
3. Fill the matching skeleton — `~/.claude/library/templates/readme-root.md` for the project root, `readme-sub.md` for a sub-directory. Each {{ slot }} describes its content; drop sections that do not apply, never invent content to fill one.
4. Include actual paths and commands, not placeholders. Match the style of existing project READMEs. Keep it proportional: a README is an overview, not full docs.
5. Show the draft and **stop for approval** before writing. Back up an existing README first if one is present.

## Mode: update

1. Resolve the README (`$target/README.md`, default `./README.md`). If it does not exist, say so and offer create mode instead.
2. Read it for structure and style, then gather what changed in one command:

   ```bash
   "$HOME"/.claude/library/scripts/git-doc-history.sh $target/README.md $target
   ```

   It prints the commits, file changes and diff stat since the README was last touched — analyse that dump rather than running exploratory git calls.
3. Identify what needs updating: outdated descriptions, undocumented additions, removed content to clean up, structural changes.
4. Generate targeted updates preserving the existing structure and style; show a diff; apply on approval.
5. If the changes are minor, say so — don't invent updates for the sake of it. Prefer surgical edits over rewrites; don't remove content unless genuinely obsolete.
