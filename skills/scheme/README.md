# scheme

Roadmaps as a dependency graph. `.claude/roadmaps.json` in your project is the source of truth; everything else (the PHASE task list, the Mermaid diagram, the prose overview, the HTML dashboard) is a projection regenerated from it by a single Python CLI. Statuses are computed from dependencies, never judged by hand.

## Install

```bash
claude plugin marketplace add JasonWarrenUK/goblin-mode
claude plugin install scheme@goblin-mode
```

Requires Python 3.8+ (stdlib only). No version is pinned: the plugin tracks the marketplace's commit, so `/plugin marketplace update` picks up the latest.

## Skills

| Skill | Does |
|---|---|
| `/scheme:create` | Build a new roadmap (or phase) from a short interview |
| `/scheme:create-interview` | Turn half-formed ideas into a reviewed batch of tasks (read-only) |
| `/scheme:update-tasks` | Add a task, or an approved batch, with dependency wiring in both directions |
| `/scheme:maintain` | Recompute statuses and refresh every projection; `reconcile` checks against the code |
| `/scheme:review` | Interview-led health and dependency-graph review |
| `/scheme:migrate` | Upgrade an old single-file roadmap to the rich format |
| `/scheme:artefact` | Render the HTML dashboard |
| `/scheme:suggest` | Pick the next task from the ready-set by leverage |
| `/scheme:group` | Show the whole ready-set, grouped by milestone or topic |

## Layout

```text
scheme/
  .claude-plugin/plugin.json
  skills/<name>/SKILL.md          one folder per skill above
  scripts/roadmap.py              the CLI: detect, validate, recompute, stats, graph, ready, render
  scripts/_roadmap_core.py        graph logic shared by the CLI
  scripts/test_roadmap.py         fixture tests (python3 scripts/test_roadmap.py)
  scripts/roadmap-drift-check.sh  optional SessionStart nudge when validate reports drift
  references/roadmap-conventions.md  status vocabulary, graph rules, colour table, file formats
  templates/roadmap-artefact.html  dashboard shell used by `roadmap.py render`
  templates/roadmap.md             prose skeleton for a new PHASE file
```

Skills reach their own files through `${CLAUDE_PLUGIN_ROOT}`, so the plugin works identically installed from the marketplace or loaded in place from `~/.claude/skills/scheme/`.
