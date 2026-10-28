← [Wiki home](../README.md)

# Library

`library/` is the shared-code layer for skills: reference material, fill-in templates, executable scripts and example configs. If a skill needs the same fragment twice, it lives here once. See the [deterministic-half pattern](../architecture.md#the-deterministic-half-pattern) for why so much of it is executable rather than prose.

## `references/`: agent-loaded background reading

Skills point here instead of restating shared rules, so lineages of related skills (stud-\*, asset-\*) can't drift against each other.

| File | Used by |
|---|---|
| `theme-conventions.md` | `theme-factory`, `theme-target`, every `asset-*` skill and any styling work: theme file format, resolution order, core→target mapping, quality gates (see [CLAUDE.md §7.5](../../CLAUDE.md)) |
| `asset-tools.md` | The `asset-*` family: verified flags and config shapes for shot-scraper, VHS, freeze, pdftoppm, Playwright and the toolkit scripts |
| `reasonable-colors-reference.md` | `theme-factory`: one optional seed palette for a new theme (24 hues × 6 shades with a known contrast table); no longer enforced anywhere |
| `react-to-svelte5.md` | `import-scaffold_artefact`: mapping React/JSX patterns to Svelte 5 idioms |
| `stud/conventions.md` | `do-stud`, `clod-approach-stud`: the mechanical *how* of scaffold banners (`&` new, `!` edited), shared so the two stud lineages can't drift |
| `stud/worked-example.md` | A complete worked stud scaffold, for the same pair of skills |
| `review-reaction-signals.md` | `pr-handle_review`: the GitHub reaction vocabulary Jason uses to signal verdicts on review threads, and how it interacts with the skill's independent-verification promise |

## `templates/`: fill-in-the-blanks documents

Blank skeletons a doc-creating skill fills in. Human-readable, not executed.

| Template | Filled in by |
|---|---|
| `ADR.md` | `doc-adr` |
| `api-reference.md`, `technical-overview.md`, `feature-spec.md` | `doc-readme` / `doc-update_misc`, ad hoc |
| `readme-root.md`, `readme-sub.md` | `doc-readme`: root vs. directory-level READMEs get different section sets |
| `work-record.md` | Session/agent work-record entries (e.g. `session-closer`) |
| `pr-description.md` | `pr-create` and `pr-update` share this template so the two can't drift on PR body structure |
| `web-scope.md` | `web-design`: the scope document its interview writes and its scope mode reads (audience, devices, copy brief, inventory, layout decisions, numbered requirements, assumptions) |

## `configs/examples/`: canonical shape references

| File | Purpose |
|---|---|
| `skill-frontmatter.yaml` | The canonical frontmatter shape for a new skill: `name`, `description`, `when_to_use` (flagged with a `CLOD TRIGGER` comment), invocability flags, `model`, `effort`, `allowed-tools`/`disallowed-tools`. This sweep brought every existing skill up to what this template already prescribed. |

## `scripts/`: the deterministic halves

Each script is the fact-gathering half of a skill: it does the part that has one correct answer (parsing git output, reading a lockfile, validating a schema) so the model's job is judgement on structured data, not orchestrating shell calls itself.

| Script | Feeds | Does |
|---|---|---|
| `branch-facts.sh` | `branch-qa_review`, `branch-rename` | Emits branch-readiness facts as JSON (commit quality, diff size, naming) so the model judges from exact numbers |
| `deps-dump.sh` | `project-investigate-deps` | Detects the package manager from lockfiles, dumps declared vs. installed vs. latest versions plus audit output in one pass |
| `git-doc-history.sh` | `doc-update_misc`, `doc-readme` | "What changed since this doc was last touched": one structured dump instead of several exploratory git calls |
| `git-integrate.sh` | `git-integrate` | Mechanical merge/rebase/squash execution; the model only steps in on exit code 3 (conflicts) or to write the squash message |
| `pr-facts.sh` | `pr-update` | PR metadata, current body, watermark and every commit since it in one dump |
| `pr-wall.sh` | `hud-pr_wall` | Buckets open PRs by relationship to the user (GraphQL search) and cross-references local clones |
| `safe-version-next.sh` | `project-tag_version`, `pr-land` | `svu next` with a programmatic guard: never crosses 0.x → 1.x automatically |
| `config_permit.py` | `config-permit` | Deterministic half of permission-granting: the skill's `allowed-tools` is scoped to only this one script |
| `validate_audit_findings.py` | `artefact-audit` | Schema gate for findings data: fails fast on a malformed finding instead of rendering it wrong |
| `slop-scan.py` | `red-doc` (report mode); `hooks/commit-msg`, `pr-create`, `pr-update`, `doc-readme`, `doc-changelog` (`--strict`) | Mechanical prose scan: house-rule breaches plus rhetorical-tell candidates; `--strict` is the gate mode (house rules only, code masked, exit 1 on a hit) |
| `skill-lint.py` | `clod-config-skill_conventions` (run by hand after editing a skill's `model` or `metadata.glyph`) | Checks every skill's glyph against its model; reports a mismatch, a glyph without a model and a model without a glyph; exit 1 on any finding |
| `md-lint.py` | `pr-create`, `pr-update`; `hooks/pr-body-lint.sh` (`--hook`) | Markdown typography gate for GitHub-rendered bodies: setext headings from a stray `---`, text swallowed by an HTML block, backticks in `<summary>`, doubled rules; exit 1 on a hit, or 2 in hook mode to block the `gh pr` call |
| `gh-guard.py` | `hooks/gh-body-guard.sh` (`--hook`); `--command TEXT` by hand | Guard for what `gh` posts: blocks an inline comment, review or reply body (use `-F body=@<file>`, `--body-file <file>` or a heredoc on `-`) and a `gh release create` with no notes source, inline `--notes` or an empty notes file; exit 2 with the reason on stderr, fail-open on anything unparseable |
| `test_gh_guard.py` | none | Tests for `gh-guard.py`: inline and file bodies for `gh api`, `gh pr comment`, `gh pr review` and `gh issue comment`, heredocs, a `gh` call quoted inside a heredoc, every release-notes shape and hook mode |
| `prose-metrics.py` | `hud-prose_health` | House-rule breaches per day in Claude's own terminal output, from the session transcripts; `--record` keeps the trend in `state/prose-metrics.json` |
| `prose-health.py` | `hud-prose_health` | PASS/WARN/FAIL per layer of the prose-gating suite (settings, style, hook, skills, frontmatter, tree scan, tests, index, output trend) |
| `test_slop_scan.py`, `test_prose_metrics.py`, `test_commit_msg_hook.py` | none | Tests for the two scanners above and for `hooks/commit-msg`; `prose-health.py` runs all three |
| `test_skill_lint.py` | none | Tests for `skill-lint.py`: a glyph that mirrors its model, drifts, is missing or has no model, and the quoting and comment forms of both fields |
| `test_md_lint.py` | none | Tests for `md-lint.py`: every rule, the clean PR template and hook-mode body extraction |
| `web/observations.py` | `web-review`, `web-check`, `web-walkthrough`; `hooks/web-signoff-guard.sh` (`guard`) | The observation store's repo side: `export` assembles the ArtifactData documents into `docs/artefacts/<task>/observations.json` and validates the store contract; `status` says what blocks sign-off; `add` appends findings where no live store exists; `guard` reads the PreToolUse payload and exits 2 on an open export, blocking `gh pr create` |
| `web/check.py` | `web-check`, `web-walkthrough` | The mechanical half of the principles check, one subcommand per principle: export hygiene (7), capture coverage under the naming rule (8), class-name collisions with the UI library (9), wireframe tokens and callout pairing (6), the copy brief (10); `--json` prints findings as store entries |
| `web/walkthrough-plan.py` | `web-walkthrough` | Routes × devices × open states into `docs/assets/walkthrough.yml` under the capture naming rule; discovered states the inventory did not name are kept and marked unplanned |
| `web/open-states.ts` | `web-walkthrough` | Playwright (Node) discovery of every openable state per route and device (`details`, `aria-expanded`, `aria-haspopup`, hidden `aria-controls` targets) with the JS that reopens each under shot-scraper, and whether the toolbar the trigger sits in moved when it opened: principle 4's test. Own `package.json`, Playwright pinned to the asset toolkit's version |
| `web/test_observations.py`, `web/test_check.py`, `web/test_walkthrough_plan.py` | none | Tests for the three Python scripts above; `fixtures/toolbar.html` is the page `open-states.ts` is run against by hand |

`gen-skills-index.py` also lives here (see [Skills](skills.md#regenerating-the-index)).

---
← [Wiki home](../README.md) · [Skills](skills.md) · [Configuration](configuration.md)
