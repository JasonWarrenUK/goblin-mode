---
name: "Docs: Update Target"
description: "{{ ƔƔƔ }} Update an existing documentation file to reflect recent code changes"
model: sonnet
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Edit", "Bash(git:*)", "Bash(~/.claude/library/scripts/git-doc-history.sh:*)"]
argument-hint: [doc path or name, e.g. Technical-Overview]
---

Analyse recent code changes and update the specified documentation file. (For READMEs specifically, use `doc-readme` — this skill covers everything else: technical overviews, ADRs, guides.)

## Steps

1. Resolve the doc from `$ARGUMENTS` (a path, or a name to Glob for under `docs/`). If nothing was given or nothing matches, ask — do not guess which doc was meant.
2. Read the doc to understand its structure and style, then gather what changed in one command:

   ```bash
   "$HOME"/.claude/library/scripts/git-doc-history.sh {doc-path} {scope-dir}
   ```

   Pass the code directory the doc describes as the scope (default: the doc's own directory, which is rarely right for docs living under `docs/` — pick the source dir it documents).
3. Identify specific updates needed: outdated sections, missing coverage of new behaviour, stale examples.
4. Generate updates preserving the existing structure; show a diff; apply on approval.
5. Update any timestamp in the doc's frontmatter.

## Notes

- Match the existing documentation style; British spelling.
- Don't remove content unless it is genuinely obsolete.
- If nothing needs updating, say so plainly.
