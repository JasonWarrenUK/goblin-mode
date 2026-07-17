← [Wiki home](../README.md)

# Library

`library/` is the shared-code layer for skills: reference material, fill-in templates, executable scripts, and example configs. If a skill needs the same fragment twice, it lives here once. See the [deterministic-half pattern](../architecture.md#the-deterministic-half-pattern) for why so much of it is executable rather than prose.

## `references/` — agent-loaded background reading

Skills point here instead of restating shared rules, so lineages of related skills (roadmap-\*, stud-\*) can't drift against each other.

| File | Used by |
|---|---|
| `reasonable-colors-reference.md` | Any frontend/styling work — the default colour palette (see [CLAUDE.md §7.5](../../CLAUDE.md)) |
| `react-to-svelte5.md` | `project-scaffold-from_artefact` — mapping React/JSX patterns to Svelte 5 idioms |
| `roadmap-conventions.md` | The roadmap skill family (`roadmap-create`, `-create-interview`, `-maintain`, `-update-tasks`, `-migrate`, `artefact-roadmap`) — shared format rules; the executable half is `scripts/roadmap.py` |
| `stud/conventions.md` | `task-execute-stud`, `role-approach-stud` — the mechanical *how* of scaffold banners (`&` new, `!` edited), shared so the two stud lineages can't drift |
| `stud/worked-example.md` | A complete worked stud scaffold, for the same pair of skills |

## `templates/` — fill-in-the-blanks documents

Blank skeletons a doc-creating skill fills in. Human-readable, not executed.

| Template | Filled in by |
|---|---|
| `ADR.md` | `doc-adr-create` |
| `api-reference.md`, `technical-overview.md`, `feature-spec.md` | `doc-readme` / `doc-misc-update`, ad hoc |
| `readme-root.md`, `readme-sub.md` | `doc-readme` — root vs. directory-level READMEs get different section sets |
| `roadmap.md`, `roadmap-artefact.html` | `roadmap-create` (prose) / `artefact-roadmap` (the HTML dashboard shell, rendered by `roadmap.py render`) |
| `status-report.md` | `doc-status_report-create` |
| `work-record.md` | Session/agent work-record entries (e.g. `session-closer`) |
| `pr-description.md` | `pr-create` and `pr-update` share this template so the two can't drift on PR body structure |

## `configs/examples/` — canonical shape references

| File | Purpose |
|---|---|
| `skill-frontmatter.yaml` | The canonical frontmatter shape for a new skill — `name`, `description`, `when_to_use` (flagged with a `CLOD TRIGGER` comment), invocability flags, `model`, `effort`, `allowed-tools`/`disallowed-tools`. This sweep brought every existing skill up to what this template already prescribed. |
| `roadmaps.jsonc` | Expected shape of a project's `.claude/roadmaps.json` registry |
| `mvp.md` | A complete worked roadmap example, deep into development — the canonical reference for `roadmap-create`'s output |

## `scripts/` — the deterministic halves

Each script is the fact-gathering half of a skill: it does the part that has one correct answer (parsing git output, reading a lockfile, validating a schema) so the model's job is judgement on structured data, not orchestrating shell calls itself.

| Script | Feeds | Does |
|---|---|---|
| `branch-facts.sh` | `git-branch-review` | Emits branch-readiness facts as JSON — commit quality, diff size, naming — so the model judges from exact numbers |
| `deps-dump.sh` | `project-investigate-deps` | Detects the package manager from lockfiles, dumps declared vs. installed vs. latest versions plus audit output in one pass |
| `git-doc-history.sh` | `doc-misc-update`, `doc-readme`, `doc-status_report-create` | "What changed since this doc was last touched" — one structured dump instead of several exploratory git calls |
| `git-integrate.sh` | `git-integrate` | Mechanical merge/rebase/squash execution; the model only steps in on exit code 3 (conflicts) or to write the squash message |
| `roadmap.py` + `_roadmap_core.py` | The whole roadmap-\* family | Single CLI for the rich phase-array roadmap system — ID assignment, status computation, dependency graph integrity, HTML rendering |
| `config_permit.py` | `config-permit` | Deterministic half of permission-granting — the skill's `allowed-tools` is scoped to only this one script |
| `validate_audit_findings.py` | `artefact-audit` | Schema gate for findings data — fails fast on a malformed finding instead of rendering it wrong |
| `test_roadmap.py` | — | Fixture tests for `roadmap.py` + `_roadmap_core.py` |

`gen-skills-index.py` also lives here — see [Skills](skills.md#regenerating-the-index).

---
← [Wiki home](../README.md) · [Skills](skills.md) · [Configuration](configuration.md)
