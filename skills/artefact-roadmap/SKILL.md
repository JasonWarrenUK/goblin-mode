---
name: "Artefacts: Create Roadmap"
description: "{{ 𝚫𝚫𝚫 }} Generate the HTML roadmap dashboard deterministically via roadmap.py render."
when_to_use: "When you want to view or share the current roadmap as an interactive dashboard rather than reading roadmaps.json directly."
model: haiku
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Bash(python3:*)", "Bash(open:*)"]
argument-hint: [phase name (optional, when several are active)]
---

Render the interactive roadmap dashboard. The HTML is generated deterministically by `roadmap.py render` from the template at `~/.claude/library/templates/roadmap-artefact.html` — this skill runs the command and opens the result; it writes no HTML itself. Same data in, same file out, so regenerated artefacts diff cleanly and can never drift from `roadmaps.json`.

Shared conventions (statuses, colour table): `~/.claude/library/references/roadmap-conventions.md`.

## Steps

1. **Check the format.** Run `python3 "$HOME"/.claude/library/scripts/roadmap.py detect`. Exit **3** = old simple format — stop and tell the user to run `roadmap-migrate` first. Exit **2** = could not locate/parse — ask for the path. Proceed on exit 0.
2. **Render.** Run `python3 "$HOME"/.claude/library/scripts/roadmap.py render`, adding `--phase "$ARGUMENTS"` when the user named a phase (required if several are active). Default output: `{project_root}/docs/artefacts/roadmap-{slug}.html`. On a validation-discrepancy note in the output, still render (the page shows a discrepancy banner) but include the discrepancies in your report.
3. **Open and report.** `open` the written file. Report: the file path; milestone and task counts plus done percentage (`roadmap.py stats`); the unblocked `todo` tasks (`roadmap.py ready` — surfaced directly, no need to open the file); any validation discrepancies.

## Notes

- The dashboard refreshes automatically when `roadmap-maintain` runs (`recompute --render`); invoke this skill for the first render or an on-demand refresh.
- Sections, palette and behaviour live in the template. To change the dashboard's look, edit `library/templates/roadmap-artefact.html`; to change status colours, change the canonical table (`STATUS_STYLE` in `roadmap.py` + the conventions reference) — never patch a generated file.
