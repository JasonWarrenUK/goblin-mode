---
name: "Configure Roadbook"
description: "Set or clear a per-phase roadbook option through the CLI, then render the chart (the roadbook's HTML page) once so it exists at the new path. The one option is artefact: where the chart is written, relative to the project root."
when_to_use: "When the user wants the chart written somewhere other than the default docs/artefacts/chart-{slug}.html (a short checked-in filename, a docs site folder) or wants that override removed. Never for changing the chart's look (that is the template) or for a plain render (goblin-scout:unroll-chart)."
model: sonnet
effort: low
metadata:
  glyph: ᛊ
  family: scout
disable-model-invocation: true
allowed-tools: ["Read", "Bash(python3:*)"]
arguments: ["option", "value", "phase"]
argument-hint: "artefact <path>|clear [phase name]"
---

# Roadbook Configure

A phase's `artefact` key in `roadbook.json` says where `render` and `recompute --render` write its chart; without it the slug default applies. This skill is the one way that key changes: the CLI writes it (inserted in field order, nothing else touched), then one render proves the new path. The resolution order and the key's rules are in `${CLAUDE_PLUGIN_ROOT}/references/roadbook-conventions.md` (File formatting). The CLI is `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py`.

## Steps

1. **Read the arguments.** `$ARGUMENTS` is `artefact <path>` or `artefact clear`, optionally followed by a phase name (needed when several phases are active, or to re-home an archived phase's chart). The path is relative to the project root and ends in `.html`, e.g. `docs/artefacts/chart-t1c.html`. Anything missing or any other option name: ask, never guess a path.
2. **Write the key.** Run `roadbook.py config artefact "<path>"` or `roadbook.py config artefact --clear`, adding `--phase "<phase>"` when one was given. Exit codes:
   - **0**: written. Keep the output; it names the new chart path and may add two notes (a chart still at the old path, no chart at the new path yet).
   - **1** with the canonical-form message: `roadbook.json` is not tab-indented. Ask before re-running with `--reformat`, since that rewrites the whole file.
   - **1** with a refusal (absolute path, `..` segment, not `.html`): report the reason and stop.
   - **2**: could not locate, parse or find the phase; report the message and stop.
3. **Render once.** Run `roadbook.py render`, with the same `--phase` when one was given, so the file exists at the new (or restored default) path. Do not open it.
4. **Report.** The new chart path and that `roadbook.json` changed, both ready to commit. If the CLI noted a chart left at the old path, say so: nothing refreshes it any more, so the user deletes it (or `git rm`s it). If the project's `.gitignore` ignores `docs/artefacts/` and the user wants the new file checked in, un-ignoring it is theirs to do; the plugin never edits `.gitignore`.

## Notes

- `recompute --render` (run by `goblin-scout:tend-roadbook`) follows the key from the next run on; no other skill needs telling.
- `render --out PATH` still wins over the key for a one-off render elsewhere.
