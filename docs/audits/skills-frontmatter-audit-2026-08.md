# Skills Frontmatter Audit — August 2026

| Prop | Value |
|------|-------|
| Started | 2026-08-13 |
| Status | Phase 9 COMPLETE (2026-08-14): all 56 original skills dialogued, 9 ditched, 1 merged, 14 gap-fixes applied — Phase 10 (artefact + steering interview) remains |
| Skills | 47 (was 56: nine ditched, one merged) |

Record of decisions for every skill across every audit step. Each cell starts as `TBD`; a completed step fills in the decision and (where non-obvious) the reasoning. Steps are completed for ALL skills before moving to the next step.

## Cross-cutting findings

- `Skill(version)` allow rule in `settings.json:19` references a skill that does not exist (closest: `project-tag_version`). Flag for Phase on permissions/visibility.
- Prefix → directory namespace (Non-Property Audit 1): docs do NOT support nested namespace directories under `~/.claude/skills/`. Directory-qualified names (`apps/web:deploy`) come only from nested `.claude/skills/` dirs under the *working directory* (monorepo pattern), and only surface on name clashes. Decision needed from Jason.

## Rulings from Jason (2026-08-13)

- Research-prop categories approved as proposed (context/agent/background conditional; paths conditional; shell skipped globally; hooks optional-default-no; metadata optional).
- Model-tag glyphs move from `description` to `metadata`; new glyph set to be chosen (incl. fable). Old tags were Greek letters, not runes.
- Namespace conversion: accepted as not possible for personal skills — keep flat prefixes.
- Stale `Skill(version)` permission: removal is in scope (Phase 5).
- `when_to_use` must work hard on dual-invocable skills: agent discoverability there, `description` kept concise for humans.
- Interim note: skills whose model changes in Phase 2 will briefly disagree with the old Greek tag still in their description; the tag sweep happens in the metadata phase.

## Phase 2 sign-off outcomes (2026-08-13)

- roadmap-update-tasks → sonnet confirmed: the semantic wiring is proposal-quality output that Step 7's approval gate and roadmap.py validate both check before anything is written.
- roadmap-maintain → sonnet confirmed, but effort raised medium→high specifically because the reconcile path infers completion from codebase evidence; the confirmation gate remains the backstop. Recorded in frontmatter comment.
- Knowledge-skill exceptions double-checked: none survive. The tempting ones (domain_modeller/data_ontologist `effort: high`, debug_dervish) fail because the override is absolute, not a floor — a session at xhigh/max triggering the skill would be *downgraded* to high. All 16 inherit.
- next-task-ship → fable approved with safeguard: new hard rule 4 caps the gate loop at 6 fix-and-rerun rounds (implement gate and post-review fix gate), converging on BLOCKED.md instead of unbounded overnight burn. Also load-bearing: pr-create's approval gate stops the loop before PR creation, so one invocation cannot chain into a second task.
- Glyphs agreed: ᚺ haiku, ᛊ sowilo/sonnet, ᛟ othala/opus, ᚠ fehu/fable — single glyph in `metadata`, swept in Phase 4.4.
- Metadata keys agreed: `glyph`, `family`, `bundle` (roadmap-system membership for export-roadmap_zip discovery).

## Phase 3 findings (2026-08-13)

- **Orchestration-blocking defect found and fixed**: next-task-ship invokes next-task-suggest, pr-create and pr-review via the Skill tool, and branch-qa_review offers pr-create — all were `disable-model-invocation: true`, which mechanically blocks a model-side Skill call regardless of context. All three flipped to dmi:false with rationale comments; pr-create relies on its internal approval gate, pr-review on a when_to_use guardrail pending a Phase 5 permission ask rule.
- Three roadmap interview skills were implicitly dual (no dmi field); made explicit with rationale comments per the convention.
- when_to_use on user-only (dmi:true) skills is invisible to the model AND costs zero context; retained everywhere as maintainer documentation (one blanket decision).
- Named `arguments` added to 9 skills with single clean slots; skips recorded for free-form, variadic, polymorphic and intent-parsed argument shapes.

## Interim amendments (2026-08-13, post-Phase 3)

- **Roadmap collapsibles**: default-open logic removed from `library/templates/roadmap-artefact.html` (line 331: first/ready milestones auto-opened). All roadmap HTML flows through `roadmap.py render` + this template, so the fix covers artefact-roadmap, roadmap-maintain, roadmap-update-tasks and pr-land in one place. Guard lines added to artefact-roadmap (Notes) and roadmap-maintain (Step 3): never re-add `open` attributes. artefact-audit's separate audit artefact also uses collapsibles but is not roadmap output; unchanged, flagged as available.
- **argument-hint normalisation**: all hints normalised to quoted YAML strings in "[...]" style (previously a mix of flow-sequences, bare brackets and one "<pr-number>"); weak wordings clarified (pr-update, pr-handle_review, pr-land, project-audit_deps, pr-review's "[#|URL]").
- **New arguments added** (upgrading two Phase 3 skips): branch-qa_review gains ["base"] wired through branch-facts.sh and the review diff; hud-whats_new gains ["since"] with a Scope section defining the measurement window. project-tag_version considered again and skipped: tag-vs-report mode is auto-detected from the branch, which beats an argument.

## Full argument re-sweep (2026-08-13, at Jason's challenge)

Every one of the 56 skills re-examined for candidate NEW arguments under the clarified policy. Added (with body wiring): commit-batch ["hints"] (grouping intent feeds the split plan), commit-one ["hint"] (type/scope/emphasis nudge for the message), roadmap-create-interview ["focus"] (seeds Step 2's scope questions, skipping to the interview proper). Deliberate skips, each recorded in its row: pr-create base branch (the whole PR workflow targets main by design), next-task-group assignee filter (the panorama view is the point; per-dev picks belong to next-task-suggest), doc-changelog range (derived from tags automatically), export-roadmap_zip (deterministic script, nothing to parameterise), analyse-*/artefact-* output paths (the free-form brief already carries them). All other skills either have their arguments already or take none for structural reasons recorded in Phase 3.

## Phase 4 findings (2026-08-13)

Note: the per-skill rows numbered 5.1–5.5 hold Phase 4's execution-context decisions (the scaffold numbered steps before the plan reordered phases); rows 4.1–4.2 hold Phase 5's tools decisions.

- **build-roadmap-zip.sh was already broken**: its hardcoded list referenced `skills/task-suggest/` and `skills/roadmap-build-zip/`, both stale pre-rename paths — the exact rot `bundle:` metadata prevents. The script now discovers members by grepping frontmatter for `bundle: roadmap-system` (11 members; rebuilt zip verified).
- Forks: project-audit_deps gains fork+Explore; analyse-concept pins background:false; analyse-critique confirmed. Everything else records why not (approval gates/interviews a subagent cannot conduct, cross-skill loads, or work too small to fork).
- Paths: 4 of 6 users removed — each glob suppressed the skill's primary conversational trigger, contradicting its own when_to_use. Kept on frontend_styler and svelte where file identity is genuinely the dominant trigger (their when_to_use conversation clauses queue for a Phase 8 trim).
- Hooks: none anywhere. The tempting candidate (validate roadmaps.json after each Edit) fails because the maintain/update workflows pass through a deliberately inconsistent intermediate state before the recompute; a hook would abort the designed flow.
- Metadata: glyph (ᚺᛊᛟᚠ mirroring model), family, and bundle applied to all 56; Greek tags stripped from every description; clod-config-skill_conventions' body rewritten to teach the metadata convention and mark both old tag forms as recognise-and-migrate.
- Shell: omitted everywhere (macOS, bash default).

## Phase 5 findings (2026-08-13)

- allowed-tools now present on all 56 (was 52): writing_style, debug_dervish, opentui gained read grants; do-minima gained reads-only with the unbounded-domain justification as a comment.
- Two unscoped `Bash` grants tightened: git_manager to Bash(git:*), testing_obsessive to the test runners. An unscoped Bash in allowed-tools pre-approves the entire shell for the invoking turn.
- disallowed-tools added to six skills whose bodies promise read-only or no-fix behaviour (pr-review, branch-qa_review, the three roadmap interviews, project-tag_version's --tags ban). The promise is now mechanical, not prose.
- settings.json: stale `Skill(version)` allow rule removed; `Skill(pr-review)`/`Skill(pr-review *)` ask rules added — the mechanical gate Phase 3 deferred. Ask rules bind the Skill *tool*, so Claude-initiated posting prompts while typed /pr-review does not.
- No other settings-level permissions needed: every remaining control was expressible in frontmatter (audit item 8's "if and only if" satisfied).

## Phase 6 findings (2026-08-13)

- Namespaces: recorded per skill as not-possible (personal-skill commands come from the flat directory name); the family axis lives in metadata instead.
- Substitutions: the collection already uses the right forms — ${CLAUDE_SKILL_DIR} for bundled scripts (stud twins, pr-review), absolute ~/.claude/library paths for the shared layer, argument placeholders from Phase 3. SESSION_ID and EFFORT have no current use case anywhere.
- Supporting files: one structural change — clod-role-frontend_styler split (458 → 183 lines) into workflows-and-checklists.md and svelte-and-patterns.md, matching its siblings. The roadmap family's "shared namespace-level files" already exist as library/ (scripts, conventions reference, template); recorded as the deliberate architecture.
- Dynamic context: the commit twins' ```! blocks are the reference pattern, and its preconditions turn out to be strict — the command must not depend on arguments, must not legitimately fail (a non-zero exit aborts the whole invocation), and its output must be consumable as a one-shot snapshot. Every other candidate fails at least one precondition; each records which.

## Phase 9 (added 2026-08-13 at Jason's direction): intent-gap dialogue

After Phase 8, a conversational pass through every skill, family by family, inferring gaps between what Jason *wants* each skill to do and what it *actually* does. Method: for each skill, state its observable behaviour in one or two sentences, Jason confirms or corrects, divergences become fixes. First documented specimen (found before the pass began): pr-update appended an updates block despite Step 3 instructing integration — fixed by naming the failure mode explicitly and giving provenance its own collapsible trail so "append a block" stops doubling as the provenance strategy.

## Phase 7 findings (2026-08-13)

- Visibility: verified clean across settings.json, settings.local.json and ~/.claude.json — no skillOverrides, no disableBundledSkills, no disableSkillShellExecution. Every visibility decision lives in the skills themselves.
- Evals: six candidates recorded (pr-review-dry_run the strongest — checkable taxonomy and verdict rules; plus commit-batch, branch-rename, roadmap-update-tasks, hud-whats_new, doc-changelog's haiku benchmark). Execution deliberately queued until after Phase 8, because description rewrites change trigger behaviour and skill-creator's description-tuning mode should grade the final text. Everything else records its disqualifier: script-owned behaviour, ungradable knowledge content, or interview flows a harness cannot conduct.
- Visual output (amended after Jason's challenge — four amendments total): the cut runs on four disqualifiers (ephemeral output, canonical dashboard already exists, output is already the artefact, interactive flow). Applying them consistently added project-audit_deps, roadmap-review and analyse-critique alongside the original — roadmap-audit-deps now offers to render substantial findings through artefact-audit's render-only mode (the schemas align). The artefact-* family is visual by design; review flows keep the terminal/GitHub as their surface; analyse-critique flagged for the Phase 9 dialogue.

## Phase 10 (added 2026-08-13, always last — position N+1 even if more phases are added)

Create an HTML artefact documenting the skills setup. Jason will be interviewed at that point for specific steering (audience, scope, depth, aesthetic). Not started until every other phase, including any added later, is complete.

## Phase 8 findings (2026-08-14)

- 27 display names aligned to the Family: Action convention, families matching metadata.family; the knowledge skills' four naming styles (kebab, Title Case, bare words, parenthetical) collapse into Lens/Role/Stack/Approach prefixes. Personality names (svelte-ninja, Cypher Linguist) retired with Jason's sign-off.
- All ten approved description/when_to_use rewrites applied, plus casualties found during the sweep: git_manager's when_to_use referenced non-existent "git-*" command skills (now branch-*/commit-*), analyse-critique carried a contrastive couplet, do-minima was first-person.
- Em-dash ruling: purge ruthlessly, everywhere, per the writing-style skill. Frontmatter of all 56 now clean (five stragglers included two added by this very audit). Body purge (~580 instances) and supporting files (~38) delegated to five parallel agents with the replacement palette, the mention-vs-punctuation exception and a per-file verification requirement; clod-approach-writing_style excluded as the document that defines the ban.
- Oxford commas swept from frontmatter alongside the dashes.
- **Body purge verified complete**: 617 instances replaced by five parallel agents plus 24 in the conventions reference and the generator, independently re-verified. Justified survivors only: partition-findings.mjs's dash ban-list regex (the validator needs the characters it bans), four "no default" table placeholders in opentui reference tables, two backticked legacy-format literals roadmap-migrate must parse, the legacy-format example in library/templates/roadmap.md, code comments in the two find-scaffold.sh scripts, and clod-approach-writing_style (defines the ban; already contained none in its body).
- **Generated-format ripple handled**: the PHASE task-line and annotation formats the roadmap skills specify changed to colon forms, consistently across roadmap-create/maintain/update-tasks AND library/references/roadmap-conventions.md. roadmap.py is unaffected (its old-format detection keys on `graph TD` plus the legacy `**depends on` literal, both untouched); test_roadmap.py exits 0. Zip rebuilt with the updated conventions.
- **skills/README.md regenerated**: gen-skills-index.py was still keying on the retired Greek tags and emitting dashes of its own; it now reads metadata.glyph, carries the ᚺ/ᛊ/ᛟ/ᚠ legend (fable added) and prints dash-free. --check confirms idempotence.

## Per-skill record

### analyse-concept

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | forked deep investigation; judgement is the product |
| 2.2 effort | high (add) | standalone forked workload |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | single free-form text blob; positional naming would fight shell quoting |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | fork confirmed; background:false ADDED | backgrounded forks run a narrower tool set (this needs Write) and the doc should land in-turn |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛟ, family: analyse | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | argument placeholders wired in Phase 3; SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, none useful |  |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | the written doc is the artefact |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Analyse: Investigate Target" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: DITCHED, no longer used (its @-directory footgun dies with it) |  |

### analyse-critique

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | adversarial architectural read needs top-tier judgement |
| 2.2 effort | high (add) | standalone forked workload |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | single free-form text blob; positional naming would fight shell quoting |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | not needed | Explore agent carries no Edit/Write tools at all |
| 5.1 context / agent / background | fork + agent:Explore confirmed; stays backgrounded | read-only fits the background tool set; result returns on completion |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛟ, family: analyse | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | argument placeholders wired in Phase 3; SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, none useful |  |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | AMENDED: closes with an artefact-audit render pointer when worth sharing | decided now rather than punted to Phase 9; read-only fork, so pointer-form |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Analyse: Critique" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | contrastive couplet and Oxford comma removed alongside the dash purge | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: DITCHED, no longer used |  |

### artefact-audit

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | verification-gated findings + verdicts; quality is the product |
| 2.2 effort | high (add) | multi-step audit with adversarial verify |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | polymorphic arg (topic or JSON path); a single name would mislead |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛟ, family: artefact | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | considered split, skipped | under the 500-line cap and a single linear flow; indirection would cost more than it saves |
| 6.4 dynamic context | considered, none useful |  |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | already visual by design |  |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: TRIMMED to renderer-plus-schema per option (a) — standalone topic-investigation machinery cut, feeders named as the findings source, collapsibles now closed by default, model downshifted opus→sonnet with the investigation half gone, display name and description reframed as Render |  |

### artefact-intro

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (down from opus) | comprehension + presentation, no verdicts; Sonnet 5 sufficient |
| 2.2 effort | high (add) | unfamiliar-codebase comprehension still deserves depth |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | single free-form text blob; positional naming would fight shell quoting |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | cross-skill dependency: loads the visual-explainer plugin skill |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛊ, family: artefact | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | argument placeholders wired in Phase 3; SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, none useful |  |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | already visual by design |  |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: GAP FIXED, output moves from the global ~/.agent/diagrams dump to the project's docs/artefacts/ home |  |

### artefact-roadmap

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (keep) | deterministic script render |
| 2.2 effort | low (add) | no judgement in the loop |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["phase"] | single clean slot |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | instant script/summary; fork overhead exceeds the work |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᚺ, family: artefact, bundle: roadmap-system | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none in-skill — by design | library/ (roadmap.py, conventions reference, HTML template) is the shared namespace-level layer the audit brief asked about |
| 6.4 dynamic context | considered, rejected | a failed injected command aborts the whole invocation; the body's exit-code protocol handles failure gracefully |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | already visual by design |  |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed as-is |  |

### branch-integrate

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (UP from haiku) | conflict resolution is judgement; haiku under-powered for merge semantics |
| 2.2 effort | medium (add) | conflicts are consequential but scoped |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["strategy","target"]), confirmed |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛊ, family: branch | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, rejected | the candidate command exits non-zero in legitimate situations (unfetched origin, no tags, outside a repo) and would abort the invocation; and for worktrees the state must be re-read after each mutation anyway |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Branch: Integrate" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: GAP FIXED, conflict resolution now weighs both sides (our intent wins for this branch's subject; the incoming side wins elsewhere) |  |

### branch-qa_review

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | full pr-review methodology plus gate interpretation |
| 2.2 effort | high (add) | review quality is the product |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | AMENDED: added "[base branch (default main)]" | [base] arg implemented at Jason's direction |
| 3.3 arguments (named) | AMENDED: added ["base"], wired through branch-facts.sh and the review diff | |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | ADDED Edit/Write/NotebookEdit | assesses readiness, never fixes |
| 5.1 context / agent / background | no fork | cross-skill dependency: loads pr-review-dry_run and offers pr-create |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛟ, family: branch | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, rejected | the candidate command exits non-zero in legitimate situations (unfetched origin, no tags, outside a repo) and would abort the invocation; and for worktrees the state must be re-read after each mutation anyway |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | verdict + findings belong in the terminal; GitHub is the visual surface once the PR exists |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: GAP FIXED, >500-line split flag removed from mechanics and verdict — small branches are a start-of-branch aspiration, never a PR-ready blocker |  |

### branch-rename

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (down from sonnet) | name derivation is summarisation + convention matching |
| 2.2 effort | low (add) | small, reversible, approval-gated |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual (dmi:false + gate comment) confirmed; when_to_use strong | recognise-before-user moment; rename awaits approval |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["desired-name"]), confirmed |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᚺ, family: branch | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, none useful |  |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | CANDIDATE — queued post-Phase 8 | name-suggestion quality and trigger accuracy both checkable |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | description trimmed of the example duplicating when_to_use | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: GAP FIXED, pushed-branch rename now checks gh pr list --head first and refuses when an open PR would be closed by the head-branch delete |  |

### clod-approach-stud

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove override) | same inline hazard: effort override displaces the session effort chosen by the user for the very task that triggered the skill |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | present, confirmed (git/gh banned) | skeleton stage must not commit |
| 5.1 context / agent / background | never fork | docs warn: guideline-only content forked into a subagent has no actionable task |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | no paths (correct as-is) | conversation-triggered knowledge; no reliable file proxy |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | family: clod-approach (no glyph — no model pin) | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ${CLAUDE_SKILL_DIR} already used for bundled scripts — the canonical pattern |
| 6.3 supporting files | present, confirmed | find-scaffold.sh (+ handoff template on do-stud) |
| 6.4 dynamic context | considered, none useful |  |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | knowledge content; no mechanically gradable output, and trigger tuning is covered by the dual-invocable set |
| 7.3 visual output | no | output is conversational or a file; a visual layer adds nothing |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Approach: Stud" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | description restructured: leads with what it does, triggers stay in when_to_use | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: RESTRUCTURED — same extraction; this file keeps the announce, checkpoint and its unique mistakes |  |

### clod-approach-writing_style

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (none set) — confirmed | knowledge skill; correct as-is |
| 2.2 effort | inherit (none set) — confirmed | knowledge skill; correct as-is |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | ADDED ["Read"] | was the only skill with no allowed-tools; pure guidance needs only reads |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | never fork | docs warn: guideline-only content forked into a subagent has no actionable task |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | no paths (correct as-is) | conversation-triggered knowledge; no reliable file proxy |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | family: clod-approach (no glyph — no model pin) | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | nothing applicable | no commands, no arguments, no bundled files |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | n/a | knowledge content; no invocation-time commands to inject |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | knowledge content; no mechanically gradable output, and trigger tuning is covered by the dual-invocable set |
| 7.3 visual output | no | output is conversational or a file; a visual layer adds nothing |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Approach: Writing Style" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed; the audit's own governing text |  |

### clod-config-skill_conventions

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove haiku) | dual-invocable reference content; model:haiku live-downgrades the skill-editing session that loads it |
| 2.2 effort | inherit (remove low) | same hazard, currently a live bug |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + comment); loads at skill-editing moments | read-only guidance needs no gate |
| 3.2 argument-hint | n/a — takes no arguments |  |
| 3.3 arguments (named) | n/a — takes no arguments |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | never fork | docs warn: guideline-only content forked into a subagent has no actionable task |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | no paths (correct as-is) | conversation-triggered knowledge; no reliable file proxy |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | family: clod-config (no glyph — no model pin) | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | nothing applicable | no commands, no arguments, no bundled files |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | n/a | knowledge content; no invocation-time commands to inject |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | knowledge content; no mechanically gradable output, and trigger tuning is covered by the dual-invocable set |
| 7.3 visual output | no | output is conversational or a file; a visual layer adds nothing |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Config: Skill Conventions" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | description and when_to_use rewritten for the metadata convention | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed |  |

### clod-lens-empathy

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove low) | effort:low would sandbag the design turn that triggers the lens |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | never fork | docs warn: guideline-only content forked into a subagent has no actionable task |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | no paths (correct as-is) | conversation-triggered knowledge; no reliable file proxy |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | family: clod-lens (no glyph — no model pin) | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | nothing applicable | no commands, no arguments, no bundled files |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | n/a | knowledge content; no invocation-time commands to inject |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | knowledge content; no mechanically gradable output, and trigger tuning is covered by the dual-invocable set |
| 7.3 visual output | no | output is conversational or a file; a visual layer adds nothing |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Lens: Empathy" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: kept for now (trio retained on Jason's call) |  |

### clod-lens-ethics

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove low) | effort:low would sandbag the review turn that triggers the lens |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | never fork | docs warn: guideline-only content forked into a subagent has no actionable task |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | no paths (correct as-is) | conversation-triggered knowledge; no reliable file proxy |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | family: clod-lens (no glyph — no model pin) | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | nothing applicable | no commands, no arguments, no bundled files |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | n/a | knowledge content; no invocation-time commands to inject |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | knowledge content; no mechanically gradable output, and trigger tuning is covered by the dual-invocable set |
| 7.3 visual output | no | output is conversational or a file; a visual layer adds nothing |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Lens: Ethics" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: kept for now |  |

### clod-lens-scope

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove low) | effort:low would sandbag the planning turn that triggers the lens |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | never fork | docs warn: guideline-only content forked into a subagent has no actionable task |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | no paths (correct as-is) | conversation-triggered knowledge; no reliable file proxy |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | family: clod-lens (no glyph — no model pin) | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | nothing applicable | no commands, no arguments, no bundled files |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | n/a | knowledge content; no invocation-time commands to inject |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | knowledge content; no mechanically gradable output, and trigger tuning is covered by the dual-invocable set |
| 7.3 visual output | no | output is conversational or a file; a visual layer adds nothing |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Lens: Scope" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: kept for now |  |

### clod-role-api_designer

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove medium) | same inline hazard: effort override displaces the session effort chosen by the user for the very task that triggered the skill |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | never fork | docs warn: guideline-only content forked into a subagent has no actionable task |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | REMOVED paths | API design conversations start before route files exist; the glob suppressed the skill's core trigger |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | family: clod-role (no glyph — no model pin) | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | nothing applicable | no commands, no arguments, no bundled files |
| 6.3 supporting files | present, confirmed | reference files linked one level deep from SKILL.md |
| 6.4 dynamic context | n/a | knowledge content; no invocation-time commands to inject |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | knowledge content; no mechanically gradable output, and trigger tuning is covered by the dual-invocable set |
| 7.3 visual output | no | output is conversational or a file; a visual layer adds nothing |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Role: API Designer" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | when_to_use rewritten: stale auto-load mechanism claim dropped | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed |  |

### clod-role-data_ontologist

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove high) | even an upward override second-guesses the user's session dial; consistency wins |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | never fork | docs warn: guideline-only content forked into a subagent has no actionable task |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | REMOVED paths | 'which database?' happens before schema files exist |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | family: clod-role (no glyph — no model pin) | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | nothing applicable | no commands, no arguments, no bundled files |
| 6.3 supporting files | present, confirmed | reference files linked one level deep from SKILL.md |
| 6.4 dynamic context | n/a | knowledge content; no invocation-time commands to inject |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | knowledge content; no mechanically gradable output, and trigger tuning is covered by the dual-invocable set |
| 7.3 visual output | no | output is conversational or a file; a visual layer adds nothing |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Role: Data Ontologist" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | when_to_use rewritten: stale auto-load mechanism claim dropped | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed |  |

### clod-role-debug_dervish

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (none set) — confirmed | knowledge skill; correct as-is |
| 2.2 effort | inherit (none set) — confirmed | knowledge skill; correct as-is |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | ADDED ["Read","Glob","Grep"] | was missing; lets it read its own reference files unprompted |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | never fork | docs warn: guideline-only content forked into a subagent has no actionable task |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | no paths (correct as-is) | conversation-triggered knowledge; no reliable file proxy |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | family: clod-role (no glyph — no model pin) | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | nothing applicable | no commands, no arguments, no bundled files |
| 6.3 supporting files | present, confirmed | reference files linked one level deep from SKILL.md |
| 6.4 dynamic context | n/a | knowledge content; no invocation-time commands to inject |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | knowledge content; no mechanically gradable output, and trigger tuning is covered by the dual-invocable set |
| 7.3 visual output | no | output is conversational or a file; a visual layer adds nothing |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Role: Debug Dervish" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: DITCHED (superseded by the bundled /debug era) |  |

### clod-role-domain_modeller

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove high) | as data_ontologist |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | never fork | docs warn: guideline-only content forked into a subagent has no actionable task |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | no paths (correct as-is) | conversation-triggered knowledge; no reliable file proxy |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | family: clod-role (no glyph — no model pin) | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | nothing applicable | no commands, no arguments, no bundled files |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | n/a | knowledge content; no invocation-time commands to inject |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | knowledge content; no mechanically gradable output, and trigger tuning is covered by the dual-invocable set |
| 7.3 visual output | no | output is conversational or a file; a visual layer adds nothing |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Role: Domain Modeller" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed |  |

### clod-role-frontend_styler

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove medium) | same inline hazard: effort override displaces the session effort chosen by the user for the very task that triggered the skill |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | never fork | docs warn: guideline-only content forked into a subagent has no actionable task |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | paths KEPT (*.svelte, *.css) | file identity is a reliable proxy; conversation-only styling questions are marginal |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | family: clod-role (no glyph — no model pin) | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | argument placeholders wired in Phase 3; SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | SPLIT APPLIED: 458 → 183 lines | workflows-and-checklists.md + svelte-and-patterns.md extracted, matching the sibling pattern; both carry tables of contents |
| 6.4 dynamic context | considered, none useful |  |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | knowledge content; no mechanically gradable output, and trigger tuning is covered by the dual-invocable set |
| 7.3 visual output | no | output is conversational or a file; a visual layer adds nothing |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Role: Frontend Styler" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | when_to_use rewritten: paths gate stated honestly | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed |  |

### clod-role-git_manager

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove low) | effort:low on conflict-resolution guidance is actively harmful |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | TIGHTENED Bash → Bash(git:*) | unscoped Bash pre-approved the entire shell whenever the skill fired |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | never fork | docs warn: guideline-only content forked into a subagent has no actionable task |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | no paths (correct as-is) | conversation-triggered knowledge; no reliable file proxy |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | family: clod-role (no glyph — no model pin) | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | nothing applicable | no commands, no arguments, no bundled files |
| 6.3 supporting files | present, confirmed | reference files linked one level deep from SKILL.md |
| 6.4 dynamic context | n/a | knowledge content; no invocation-time commands to inject |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | knowledge content; no mechanically gradable output, and trigger tuning is covered by the dual-invocable set |
| 7.3 visual output | no | output is conversational or a file; a visual layer adds nothing |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Role: Git Manager" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | when_to_use fixed: stale git-* skill reference now names branch-*/commit-* | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed |  |

### clod-role-testing_obsessive

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove medium) | same inline hazard: effort override displaces the session effort chosen by the user for the very task that triggered the skill |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | TIGHTENED Bash → npm/bun/pnpm/deno/vitest | same unscoped-Bash hole, scoped to test runners |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | never fork | docs warn: guideline-only content forked into a subagent has no actionable task |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | REMOVED paths | 'should I test this?' happens while writing source, with no test file to match |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | family: clod-role (no glyph — no model pin) | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | nothing applicable | no commands, no arguments, no bundled files |
| 6.3 supporting files | present, confirmed | reference files linked one level deep from SKILL.md |
| 6.4 dynamic context | n/a | knowledge content; no invocation-time commands to inject |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | knowledge content; no mechanically gradable output, and trigger tuning is covered by the dual-invocable set |
| 7.3 visual output | no | output is conversational or a file; a visual layer adds nothing |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Role: Testing Obsessive" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | when_to_use rewritten: stale auto-load mechanism claim dropped | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed |  |

### clod-stack-cypher

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove medium) | same inline hazard: effort override displaces the session effort chosen by the user for the very task that triggered the skill |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | never fork | docs warn: guideline-only content forked into a subagent has no actionable task |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | REMOVED paths | Cypher lives inside .ts strings; file identity is an unreliable proxy |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | family: clod-stack (no glyph — no model pin) | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | nothing applicable | no commands, no arguments, no bundled files |
| 6.3 supporting files | present, confirmed | reference files linked one level deep from SKILL.md |
| 6.4 dynamic context | n/a | knowledge content; no invocation-time commands to inject |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | knowledge content; no mechanically gradable output, and trigger tuning is covered by the dual-invocable set |
| 7.3 visual output | no | output is conversational or a file; a visual layer adds nothing |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Stack: Cypher" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | when_to_use rewritten: stale auto-load mechanism claim dropped; embedded-strings reality named | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed |  |

### clod-stack-opentui

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (none set) — confirmed | knowledge skill; correct as-is |
| 2.2 effort | inherit (none set) — confirmed | knowledge skill; correct as-is |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | ADDED ["Read","Glob","Grep"] | was missing; matches sibling stack skills |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | never fork | docs warn: guideline-only content forked into a subagent has no actionable task |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | considered, not added | no reliable glob — OpenTUI code is plain .ts |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | family: clod-stack (no glyph — no model pin) | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | nothing applicable | no commands, no arguments, no bundled files |
| 6.3 supporting files | present, confirmed | reference files linked one level deep from SKILL.md |
| 6.4 dynamic context | n/a | knowledge content; no invocation-time commands to inject |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | knowledge content; no mechanically gradable output, and trigger tuning is covered by the dual-invocable set |
| 7.3 visual output | no | output is conversational or a file; a visual layer adds nothing |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Stack: OpenTUI" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed |  |

### clod-stack-svelte

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove medium) | same inline hazard: effort override displaces the session effort chosen by the user for the very task that triggered the skill |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | never fork | docs warn: guideline-only content forked into a subagent has no actionable task |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | paths KEPT (*.svelte, +page.*, +layout.*) | dominant trigger is file work; keeps a 421-line skill from loading on passing mentions |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | family: clod-stack (no glyph — no model pin) | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | nothing applicable | no commands, no arguments, no bundled files |
| 6.3 supporting files | present, confirmed | reference files linked one level deep from SKILL.md |
| 6.4 dynamic context | n/a | knowledge content; no invocation-time commands to inject |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | knowledge content; no mechanically gradable output, and trigger tuning is covered by the dual-invocable set |
| 7.3 visual output | no | output is conversational or a file; a visual layer adds nothing |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Stack: Svelte" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | when_to_use rewritten: paths gate stated honestly | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed |  |

### commit-batch

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (keep) | mechanical splitting; grouping confirmed with user anyway |
| 2.2 effort | low (keep) | confirmed |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | n/a — takes no arguments |  |
| 3.3 arguments (named) | AMENDED: added ["hints"] + Step 2 wiring | grouping intent is exactly what the user knows and the diff doesn't show |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᚺ, family: commit | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | argument placeholders wired in Phase 3; SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | confirmed — reference pattern | ```! blocks capture git status/diff at invocation; command cannot legitimately fail, takes no arguments, state consumed once |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | CANDIDATE — queued post-Phase 8 | grouping quality is assertable against fixture diffs |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed incl. bundled auto-push |  |

### commit-one

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (keep) | message generation from one diff |
| 2.2 effort | low (keep) | confirmed |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | n/a — takes no arguments |  |
| 3.3 arguments (named) | AMENDED: added ["hint"] + Step 2 wiring | a type/scope/why nudge beats regenerating the message |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᚺ, family: commit | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | argument placeholders wired in Phase 3; SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | confirmed — reference pattern | ```! blocks capture git status/diff at invocation; command cannot legitimately fail, takes no arguments, state consumed once |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed incl. bundled auto-push |  |

### config-clod_permits

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (keep) | single scripted operation |
| 2.2 effort | low (keep) | confirmed |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["scope","rule"]), confirmed |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᚺ, family: config | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, none useful |  |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: DITCHED (never used) along with config_permit.py |  |

### do-minima

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove haiku) | task domain is unbounded — forcing haiku on arbitrary asks is a trap; minimalism is an instruction, not a capability ceiling |
| 2.2 effort | medium (add) | minimal changes still need correct ones |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | single free-form text blob; positional naming would fight shell quoting |
| 4.1 allowed-tools | ADDED ["Read","Glob","Grep"] + comment | reads only — unbounded task domain makes any broader grant a blanket approval |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | one-liner that deliberately inherits the session's full context |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | family: do (no glyph — no model pin) | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | argument placeholders wired in Phase 3; SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, none useful |  |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | description rewritten out of first person | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed, the purest skill in the set |  |

### do-stud

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (keep) | structural skeleton work; deliberately cheap before expensive fill |
| 2.2 effort | medium (keep) | confirmed |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["outcome","questions"]), confirmed |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | present, confirmed (git/gh banned) | same |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛊ, family: do | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ${CLAUDE_SKILL_DIR} already used for bundled scripts — the canonical pattern |
| 6.3 supporting files | present, confirmed | find-scaffold.sh (+ handoff template on do-stud) |
| 6.4 dynamic context | considered, none useful |  |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | approval-gated/interview flow; an eval harness cannot conduct the conversation |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Do: Stud" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: RESTRUCTURED — shared methodology extracted to library/references/stud/methodology.md (161→~60 lines); this file keeps the interview, handoff and its unique mistakes. Duplicate find-scaffold.sh consolidated to library/scripts/ |  |

### doc-adr

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (keep) | decision-rationale prose |
| 2.2 effort | medium (add) | one document, real judgement |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["title"]), confirmed |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛊ, family: doc | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none in-skill — by design | fills templates from library/templates/ |
| 6.4 dynamic context | considered, none useful |  |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: DITCHED, never used |  |

### doc-changelog

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (down from sonnet) | projection from conventional commits is mechanical |
| 2.2 effort | medium (add) | curation across surfaces needs some care |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + gate comment); when_to_use names its trigger moment (pr-land) |  |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | re-checked: no range arg | range derives from tags/commits automatically |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᚺ, family: doc | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, none useful |  |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | CANDIDATE — queued post-Phase 8 | haiku downshift deserves a with/without benchmark on fixture history |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: all four improvements APPLIED — first-parent PR-level entries, refactor moved to omit-unless-user-visible, version argument wired into pr-land's hand-off, Unreleased promotion over regeneration |  |

### doc-readme

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (keep) | user-facing structure + prose |
| 2.2 effort | medium (add) | standard doc work |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + gate comment) |  |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["mode","target"]), confirmed |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛊ, family: doc | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none in-skill — by design | fills templates from library/templates/ |
| 6.4 dynamic context | considered, none useful |  |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: GAP FIXED, vestigial backup step replaced with 'git is the backup' |  |

### doc-update_misc

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (keep) | reconciling doc against shipped code |
| 2.2 effort | medium (add) | standard doc work |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + gate comment) |  |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["doc"] | single clean slot |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛊ, family: doc | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, none useful |  |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: DITCHED, never used |  |

### export-roadmap_zip

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (keep) | runs one zsh script |
| 2.2 effort | low (add) | deterministic |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | n/a — takes no arguments |  |
| 3.3 arguments (named) | re-checked: no args | deterministic script, nothing to parameterise |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | instant script/summary; fork overhead exceeds the work |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᚺ, family: roadmap, bundle: roadmap-system | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none in-skill — by design | library/ (roadmap.py, conventions reference, HTML template) is the shared namespace-level layer the audit brief asked about |
| 6.4 dynamic context | considered, rejected | a failed injected command aborts the whole invocation; the body's exit-code protocol handles failure gracefully |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | description and when_to_use updated for bundle-tag discovery | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: DITCHED at Jason's direction; skill, build script, zip artefact and all bundle: metadata removed |  |

### hud-pr_wall

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (keep) | script output + bucketing |
| 2.2 effort | low (keep) | confirmed |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + comment); read-only |  |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["scope","root"]), confirmed |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | instant script/summary; fork overhead exceeds the work |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᚺ, family: hud | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, rejected | the natural command depends on arguments/PR resolution not available at render time |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: DITCHED (skill + pr-wall.sh); pr-land's reference cleaned up |  |

### hud-whats_new

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (keep) | user-facing synthesis of diffs |
| 2.2 effort | low (add) | quick memo, not analysis |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + comment); read-only wrap-up |  |
| 3.2 argument-hint | AMENDED: added "[since ref (optional)]" | |
| 3.3 arguments (named) | AMENDED: added ["since"] + Scope section pinning the measurement window | |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | instant script/summary; fork overhead exceeds the work |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛊ, family: hud | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | argument placeholders wired in Phase 3; SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, rejected | the natural command depends on arguments/PR resolution not available at render time |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | CANDIDATE — queued post-Phase 8 | observable-behaviour-only rule is easy to violate and easy to grade |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "HUD: What's New" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: GAP FIXED, wired into pr-land's report step as an offered wrap-up |  |

### hud-worktrees

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (keep) | shepherds destructive ops; safety judgement |
| 2.2 effort | medium (add) | mutations are approval-gated but consequential |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + comment); mutations approval-gated |  |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["action","branch"]), confirmed |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛊ, family: hud | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | argument placeholders wired in Phase 3; SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, rejected | the candidate command exits non-zero in legitimate situations (unfetched origin, no tags, outside a repo) and would abort the invocation; and for worktrees the state must be re-read after each mutation anyway |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | approval-gated/interview flow; an eval harness cannot conduct the conversation |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: GAP FIXED, map now groups deliberate vs machine-made worktrees (both always shown, unclear provenance defaults to deliberate) and abandoned machine-made trees become first-class cleanup candidates |  |

### import-scaffold_artefact

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (down from opus) | code conversion/porting; Sonnet 5 strong at mechanical translation |
| 2.2 effort | high (add) | large multi-file transform |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | path plus optional 'react' flag; variadic-ish |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛊ, family: import | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | argument placeholders wired in Phase 3; SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | considered split, skipped | under the 500-line cap and a single linear flow; indirection would cost more than it saves |
| 6.4 dynamic context | considered, none useful |  |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Import: Scaffold from Artefact" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed, the collection's most thorough body |  |

### next-task-group

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (keep) | script + grouping |
| 2.2 effort | low (keep) | confirmed |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | re-checked: no assignee filter | panorama view by design; per-dev picks are next-task-suggest's job |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | instant script/summary; fork overhead exceeds the work |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᚺ, family: next-task, bundle: roadmap-system | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none in-skill — by design | library/ (roadmap.py, conventions reference, HTML template) is the shared namespace-level layer the audit brief asked about |
| 6.4 dynamic context | considered, rejected | a failed injected command aborts the whole invocation; the body's exit-code protocol handles failure gracefully |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Next Task: Group" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed, topic pivot actively used |  |

### next-task-ship

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | fable (UP from opus) | unattended long-horizon delivery loop (implement, test, PR, self-review) — the one workload where Mythos-class autonomy pays |
| 2.2 effort | high (add) | unattended = no human catches mid-loop drift |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | forwards $ARGUMENTS verbatim to next-task-suggest |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | orchestrator: needs the Skill tool and stops at user gates a subagent cannot present |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᚠ, family: next-task | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | argument placeholders wired in Phase 3; SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | considered extracting BLOCKED.md template, skipped | small and load-bearing inline |
| 6.4 dynamic context | considered, none useful |  |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Next Task: Ship" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: GAP FIXED, now fully autonomous end-to-end with the task-pick veto as the run's ONLY gate. pr-create invoked with new auto token (no second pause); dirty-tree check writes BLOCKED.md instead of asking; after the fix cycle it re-reviews once so the verdict reflects the fixed state. PENDING: Skill(pr-review) ask-rule removal blocked by permission classifier; without it the unattended run stalls at a prompt when Step 7 posts |  |

### next-task-suggest

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (keep) | grounded pick from pre-vetted ready-set |
| 2.2 effort | low (keep) | confirmed |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | CHANGED dmi true→false + comment: next-task-ship Step 1 invokes it via the Skill tool, which dmi:true mechanically blocks; also a natural 'what should I work on?' trigger. Read-only, no gate needed | orchestrator dependency |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | body parses by intent, not position; named args would misrepresent the contract |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | instant script/summary; fork overhead exceeds the work |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᚺ, family: next-task, bundle: roadmap-system | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none in-skill — by design | library/ (roadmap.py, conventions reference, HTML template) is the shared namespace-level layer the audit brief asked about |
| 6.4 dynamic context | considered, rejected | a failed injected command aborts the whole invocation; the body's exit-code protocol handles failure gracefully |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Next Task: Suggest" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: GAP FIXED, codebase-analysis fallback removed entirely (Jason only uses roadmap structures); no-roadmap now routes to roadmap-create/migrate and stops. Haiku concern dissolves with it; 45-min threshold confirmed by silence |  |

### pr-create

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (keep) | description prose from commits |
| 2.2 effort | medium (add) | outward-facing but bounded |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | CHANGED dmi true→false + comment: invoked by next-task-ship Step 6 and branch-qa_review's Ready offer — both were mechanically blocked. Internal approval step is the gate; when_to_use rewritten with explicit never-invoke-speculatively guardrail | orchestrator dependency + existing gate |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | re-checked: no base-branch arg | PR workflow targets main by design (pr-land assumes it too) |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛊ, family: pr | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none in-skill — by design | fills templates from library/templates/ |
| 6.4 dynamic context | considered, rejected | the natural command depends on arguments/PR resolution not available at render time |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: behaviour confirmed, absurd-metaphor summary confirmed intentional everywhere |  |

### pr-handle_review

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | independent verification of review feedback before acting |
| 2.2 effort | high (add) | wrong triage ships wrong fixes |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["pr"] | single clean slot |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛟ, family: pr | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | argument placeholders wired in Phase 3; SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, rejected | the natural command depends on arguments/PR resolution not available at render time |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: GAP FIXED, stock pushback closer removed | door stays open in Claude's own words, matched to thread tone |

### pr-land

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (keep) | procedural but irreversible (merge, tag, delete) |
| 2.2 effort | medium (add) | irreversibility deserves attention, scripts do the maths |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["pr"] | single clean slot |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛊ, family: pr | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, rejected | the natural command depends on arguments/PR resolution not available at render time |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: GAP FIXED, APPROVED requirement now waived for github.com/jasonwarrenuk/* repos | personal repos have no reviewer; the value can never appear |

### pr-review-dry_run

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep; follows pr-review) | canonical methodology both entry points share |
| 2.2 effort | high (add) | as pr-review |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false, required by pr-review + branch-qa_review); read-only via disallowed-tools |  |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["mode","pr"]), confirmed |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | present, confirmed (Edit/Write/NotebookEdit) | reviews, never fixes |
| 5.1 context / agent / background | no fork | cross-skill dependency: called BY pr-review and branch-qa_review — findings must land in the caller's context |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛟ, family: pr | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | argument placeholders wired in Phase 3; SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, rejected | the natural command depends on arguments/PR resolution not available at render time |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | CANDIDATE — queued post-Phase 8 | structured findings with a checkable taxonomy and verdict rules — the strongest eval target in the collection |
| 7.3 visual output | no | deliberately terminal-only by contract |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | description rewritten (was three words; now names the terminal output and its role as the shared methodology) | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: behaviour confirmed |  |

### pr-review

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep; fable considered — flagged for user) | posted, outward-facing review; opus 5 strong, fable would boost at cost |
| 2.2 effort | high (add) | review quality is the product |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | CHANGED dmi true→false + comment: next-task-ship Step 7 invokes it. No internal gate before posting, so when_to_use carries a hard guardrail and Phase 5 will consider a Skill(pr-review) ask rule as the mechanical gate | orchestrator dependency; gate deferred to permissions |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["mode","pr"]), confirmed |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | ADDED Edit/Write/NotebookEdit | mirrors dry_run: posts a review, never touches the tree |
| 5.1 context / agent / background | no fork | cross-skill dependency: loads pr-review-dry_run; posts from main context |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛟ, family: pr | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ${CLAUDE_SKILL_DIR} already used for bundled scripts — the canonical pattern |
| 6.3 supporting files | present, confirmed | partition-findings.mjs; pr-review-dry_run serves as the shared methodology 'file' for this skill and branch-qa_review |
| 6.4 dynamic context | considered, rejected | the natural command depends on arguments/PR resolution not available at render time |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | GitHub review IS the visual output |
| 7.4 permissions | Skill(pr-review) + Skill(pr-review *) ask rules added to settings.json | mechanical gate on model-invoked posting (the Phase 3 deferral); user slash invocation is not a Skill tool call, so /pr-review stays frictionless |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: auto-submit without a preview gate probed and confirmed intentional | speed over ceremony; ask-rule gates model invocation |

### pr-update

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (keep) | description refresh from new commits |
| 2.2 effort | medium (add) | outward-facing prose |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + gate comment) |  |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["pr"] | single clean slot |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛊ, family: pr | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, rejected | the natural command depends on arguments/PR resolution not available at render time |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: behaviour confirmed incl. watermark convention (gap already fixed pre-pass) |  |

### project-audit_deps

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (down from opus) | script dump + web-research aggregation; advisory interpretation within Sonnet 5's reach |
| 2.2 effort | high (add) | security-adjacent conclusions need care |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["dep"] | single clean slot |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | ADDED context:fork + agent:Explore | self-contained read-only investigation; large read/web footprint stays out of the main context |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛊ, family: project | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, none useful |  |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | AMENDED: closes its report with an artefact-audit render pointer | consistency fix after Jason's challenge — severity-ranked findings revisited over days; runs in a read-only fork so the pointer is textual and rendering happens in the main conversation |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Project: Audit Dependencies" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed |  |

### project-tag_version

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (keep) | script-guarded svu tagging |
| 2.2 effort | low (keep) | confirmed |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | n/a — no arguments (body has no $ARGUMENTS) |  |
| 3.3 arguments (named) | n/a — takes no arguments |  |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | ADDED Bash(git push --tags:*) | the body's hard warning made mechanical |
| 5.1 context / agent / background | no fork | instant script/summary; fork overhead exceeds the work |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᚺ, family: project | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none needed | body well under the 500-line budget; single flow |
| 6.4 dynamic context | considered, rejected | the candidate command exits non-zero in legitimate situations (unfetched origin, no tags, outside a repo) and would abort the invocation; and for worktrees the state must be re-read after each mutation anyway |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | CHANGED → "Project: Tag Version" | display name aligned to the Family: Action convention and metadata.family |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed |  |

### roadmap-audit-deps

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | graph-rationality interview; systemic judgement |
| 2.2 effort | high (add) | wrong edges poison the whole plan |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | was implicitly dual (no dmi field) — made EXPLICIT dmi:false + rationale comment | read-only interview; convention wants the exception annotated |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["milestone"] | single clean slot |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | ADDED Edit/Write/NotebookEdit | interview only; edits belong to the writer skills |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛟ, family: roadmap, bundle: roadmap-system | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none in-skill — by design | library/ (roadmap.py, conventions reference, HTML template) is the shared namespace-level layer the audit brief asked about |
| 6.4 dynamic context | considered, rejected | a failed injected command aborts the whole invocation; the body's exit-code protocol handles failure gracefully |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | approval-gated/interview flow; an eval harness cannot conduct the conversation |
| 7.3 visual output | ADDED: offers artefact-audit render-only mode for substantial findings lists | the findings shape maps onto artefact-audit's JSON schema |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: MERGED into roadmap-review as its 'deps' lens; directory deleted |  |

### roadmap-create-interview

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | interview synthesis into a coherent proposal |
| 2.2 effort | high (add) | quality of questions drives quality of plan |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | was implicitly dual — made EXPLICIT dmi:false + rationale comment | read-only interview |
| 3.2 argument-hint | n/a — no arguments (scope emerges in the interview) |  |
| 3.3 arguments (named) | AMENDED: added ["focus"] + Step 2 wiring | seeds the interview scope, skipping the warm-up questions |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | ADDED Edit/Write/NotebookEdit | read-only by contract |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛟ, family: roadmap, bundle: roadmap-system | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none in-skill — by design | library/ (roadmap.py, conventions reference, HTML template) is the shared namespace-level layer the audit brief asked about |
| 6.4 dynamic context | considered, rejected | a failed injected command aborts the whole invocation; the body's exit-code protocol handles failure gracefully |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | approval-gated/interview flow; an eval harness cannot conduct the conversation |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: batch hand-off adopted; proposal now feeds roadmap-update-tasks' new batch mode |  |

### roadmap-create

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | greenfield decomposition of a project |
| 2.2 effort | high (add) | foundational output |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["phase"] | single clean slot |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛟ, family: roadmap, bundle: roadmap-system | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none in-skill — by design | library/ (roadmap.py, conventions reference, HTML template) is the shared namespace-level layer the audit brief asked about |
| 6.4 dynamic context | considered, rejected | a failed injected command aborts the whole invocation; the body's exit-code protocol handles failure gracefully |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: GAPS FIXED — interview restructured feature-first (milestones proposed from the grouping, never demanded cold) and the PHASE_1 default replaced with a proposed, confirmed phase name |  |

### roadmap-maintain

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (down from opus) | roadmap.py does the graph maths; skill orchestrates and narrates |
| 2.2 effort | high (add) | raised from proposed medium: reconcile path infers from codebase evidence |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + gate comment) |  |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | arg is milestone-id-or-'reconcile'; dual semantics resist a single name |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no | a validate-after-edit hook would fire on the deliberately inconsistent intermediate state (statuses edited before recompute); end-of-flow validation is already mandated |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛊ, family: roadmap, bundle: roadmap-system | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none in-skill — by design | library/ (roadmap.py, conventions reference, HTML template) is the shared namespace-level layer the audit brief asked about |
| 6.4 dynamic context | considered, rejected | a failed injected command aborts the whole invocation; the body's exit-code protocol handles failure gracefully |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: behaviour confirmed; automatic trigger wish met with a SessionStart drift hook (roadmap-drift-check.sh) that nudges when validate reports discrepancies | trigger condition: detect==rich AND validate!=clean, silent everywhere else |

### roadmap-migrate

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (down from opus) | validator-gated procedural conversion |
| 2.2 effort | high (add) | one-way transform; git checkpoint advised by the skill itself |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["roadmap"] | single clean slot |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛊ, family: roadmap, bundle: roadmap-system | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none in-skill — by design | library/ (roadmap.py, conventions reference, HTML template) is the shared namespace-level layer the audit brief asked about |
| 6.4 dynamic context | considered, rejected | a failed injected command aborts the whole invocation; the body's exit-code protocol handles failure gracefully |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | behaviour is the script's, not the skill's — the test suite/validator is the eval harness |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed as-is |  |

### roadmap-review

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | strategic health judgement, not mechanics |
| 2.2 effort | high (add) | the strategic complement; depth is the point |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | was implicitly dual — made EXPLICIT dmi:false + rationale comment | read-only interview, writes nothing |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["milestone"] | single clean slot |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | ADDED Edit/Write/NotebookEdit | writes nothing itself |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no — nothing to enforce beyond allowed/disallowed-tools and in-body validators |  |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛟ, family: roadmap, bundle: roadmap-system | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none in-skill — by design | library/ (roadmap.py, conventions reference, HTML template) is the shared namespace-level layer the audit brief asked about |
| 6.4 dynamic context | considered, rejected | a failed injected command aborts the whole invocation; the body's exit-code protocol handles failure gracefully |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | not warranted | approval-gated/interview flow; an eval harness cannot conduct the conversation |
| 7.3 visual output | AMENDED: offers artefact-audit render-only mode like roadmap-audit-deps | the 'value is the conversation' distinction applied equally to audit-deps; inconsistency resolved |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: absorbed roadmap-audit-deps; now lens-driven ([health|deps|full], default full) with the suspect-list machinery as axis 5 |  |

### roadmap-update-tasks

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (down from opus) | mechanical ID/edge wiring, approval-gated, roadmap.py validates |
| 2.2 effort | medium (add) | graph edits checked by validator |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + gate comment); when_to_use already phrase-rich |  |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | single free-form text blob; positional naming would fight shell quoting |
| 4.1 allowed-tools | present, confirmed — scoped to the skill's commands |  |
| 4.2 disallowed-tools | none — considered | nothing destructive to ban; unlisted tools still prompt under normal permissions |
| 5.1 context / agent / background | no fork | mid-flow user interaction (approval gate or interview) that a forked subagent cannot conduct |
| 5.2 hooks | no | same intermediate-state problem; roadmap.py validate runs as the final step by design |
| 5.3 paths | n/a — auto-load relevance is conversational or the skill is user-only |  |
| 5.4 shell | omit (blanket: macOS, bash is the default; powershell N/A) | |
| 5.5 metadata | glyph: ᛊ, family: roadmap, bundle: roadmap-system | Greek tag stripped from description where present |
| 6.1 namespace conversion | not possible for personal skills — flat prefix stays; family axis captured in metadata instead | |
| 6.2 string substitutions | confirmed | ~/.claude/library paths are deliberately absolute (shared layer, not skill-local); SESSION_ID/EFFORT considered, no use case |
| 6.3 supporting files | none in-skill — by design | library/ (roadmap.py, conventions reference, HTML template) is the shared namespace-level layer the audit brief asked about |
| 6.4 dynamic context | considered, rejected | a failed injected command aborts the whole invocation; the body's exit-code protocol handles failure gracefully |
| 7.1 visibility lives in skill | clean | no skillOverrides/disableBundledSkills/shell-execution overrides anywhere; the only external control is the deliberate Skill(pr-review) ask pair, which gates invocation, not listing |
| 7.2 evals | CANDIDATE — queued post-Phase 8 | graph-integrity assertions on fixture roadmaps; roadmap.py validate doubles as the grader |
| 7.3 visual output | no | terminal output is the right surface |
| 7.4 permissions | none needed | frontmatter expresses every control this skill wants |
| 8.1 name | confirmed | already on convention |
| 8.2 description | confirmed, dash/Oxford purge applied where needed | writing-style gate run on every edited string |
| 9.1 intent-gap dialogue | dialogue done: confirmed good, incl. placeholder children; gained batch mode (one consolidated proposal/approval/write for multi-task proposals) |  |

