# Skills Frontmatter Audit — August 2026

| Prop | Value |
|------|-------|
| Started | 2026-08-13 |
| Status | Phase 3 complete (applied 2026-08-13) — Phase 4 next |
| Skills | 56 |

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

## Per-skill record

### analyse-concept

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | forked deep investigation; judgement is the product |
| 2.2 effort | high (add) | standalone forked workload |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | single free-form text blob; positional naming would fight shell quoting |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### analyse-critique

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | adversarial architectural read needs top-tier judgement |
| 2.2 effort | high (add) | standalone forked workload |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | single free-form text blob; positional naming would fight shell quoting |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### artefact-audit

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | verification-gated findings + verdicts; quality is the product |
| 2.2 effort | high (add) | multi-step audit with adversarial verify |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | polymorphic arg (topic or JSON path); a single name would mislead |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### artefact-intro

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (down from opus) | comprehension + presentation, no verdicts; Sonnet 5 sufficient |
| 2.2 effort | high (add) | unfamiliar-codebase comprehension still deserves depth |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | single free-form text blob; positional naming would fight shell quoting |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### artefact-roadmap

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (keep) | deterministic script render |
| 2.2 effort | low (add) | no judgement in the loop |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["phase"] | single clean slot |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### branch-integrate

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (UP from haiku) | conflict resolution is judgement; haiku under-powered for merge semantics |
| 2.2 effort | medium (add) | conflicts are consequential but scoped |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["strategy","target"]), confirmed |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### branch-qa_review

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | full pr-review methodology plus gate interpretation |
| 2.2 effort | high (add) | review quality is the product |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | AMENDED: added "[base branch (default main)]" | [base] arg implemented at Jason's direction |
| 3.3 arguments (named) | AMENDED: added ["base"], wired through branch-facts.sh and the review diff | |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### branch-rename

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (down from sonnet) | name derivation is summarisation + convention matching |
| 2.2 effort | low (add) | small, reversible, approval-gated |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual (dmi:false + gate comment) confirmed; when_to_use strong | recognise-before-user moment; rename awaits approval |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["desired-name"]), confirmed |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### clod-approach-stud

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove override) | same inline hazard: effort override displaces the session effort chosen by the user for the very task that triggered the skill |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### clod-approach-writing_style

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (none set) — confirmed | knowledge skill; correct as-is |
| 2.2 effort | inherit (none set) — confirmed | knowledge skill; correct as-is |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### clod-config-skill_conventions

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove haiku) | dual-invocable reference content; model:haiku live-downgrades the skill-editing session that loads it |
| 2.2 effort | inherit (remove low) | same hazard, currently a live bug |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + comment); loads at skill-editing moments | read-only guidance needs no gate |
| 3.2 argument-hint | n/a — takes no arguments |  |
| 3.3 arguments (named) | n/a — takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### clod-lens-empathy

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove low) | effort:low would sandbag the design turn that triggers the lens |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### clod-lens-ethics

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove low) | effort:low would sandbag the review turn that triggers the lens |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### clod-lens-scope

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove low) | effort:low would sandbag the planning turn that triggers the lens |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### clod-role-api_designer

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove medium) | same inline hazard: effort override displaces the session effort chosen by the user for the very task that triggered the skill |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### clod-role-data_ontologist

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove high) | even an upward override second-guesses the user's session dial; consistency wins |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### clod-role-debug_dervish

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (none set) — confirmed | knowledge skill; correct as-is |
| 2.2 effort | inherit (none set) — confirmed | knowledge skill; correct as-is |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### clod-role-domain_modeller

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove high) | as data_ontologist |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### clod-role-frontend_styler

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove medium) | same inline hazard: effort override displaces the session effort chosen by the user for the very task that triggered the skill |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### clod-role-git_manager

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove low) | effort:low on conflict-resolution guidance is actively harmful |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### clod-role-testing_obsessive

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove medium) | same inline hazard: effort override displaces the session effort chosen by the user for the very task that triggered the skill |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### clod-stack-cypher

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove medium) | same inline hazard: effort override displaces the session effort chosen by the user for the very task that triggered the skill |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### clod-stack-opentui

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (none set) — confirmed | knowledge skill; correct as-is |
| 2.2 effort | inherit (none set) — confirmed | knowledge skill; correct as-is |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### clod-stack-svelte

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove override) | knowledge skill loads inline mid-task; a model override would switch the session model for the rest of the turn it fires in |
| 2.2 effort | inherit (remove medium) | same inline hazard: effort override displaces the session effort chosen by the user for the very task that triggered the skill |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | user-invocable:false confirmed; when_to_use present and trigger-rich | agent-only knowledge; correct per convention |
| 3.2 argument-hint | n/a — not user-invoked, takes no arguments |  |
| 3.3 arguments (named) | n/a — not user-invoked, takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### commit-batch

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (keep) | mechanical splitting; grouping confirmed with user anyway |
| 2.2 effort | low (keep) | confirmed |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | n/a — takes no arguments |  |
| 3.3 arguments (named) | n/a — takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### commit-one

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (keep) | message generation from one diff |
| 2.2 effort | low (keep) | confirmed |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | n/a — takes no arguments |  |
| 3.3 arguments (named) | n/a — takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### config-clod_permits

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (keep) | single scripted operation |
| 2.2 effort | low (keep) | confirmed |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["scope","rule"]), confirmed |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### do-minima

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | inherit (remove haiku) | task domain is unbounded — forcing haiku on arbitrary asks is a trap; minimalism is an instruction, not a capability ceiling |
| 2.2 effort | medium (add) | minimal changes still need correct ones |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | single free-form text blob; positional naming would fight shell quoting |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### do-stud

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (keep) | structural skeleton work; deliberately cheap before expensive fill |
| 2.2 effort | medium (keep) | confirmed |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["outcome","questions"]), confirmed |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### doc-adr

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (keep) | decision-rationale prose |
| 2.2 effort | medium (add) | one document, real judgement |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["title"]), confirmed |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### doc-changelog

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (down from sonnet) | projection from conventional commits is mechanical |
| 2.2 effort | medium (add) | curation across surfaces needs some care |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + gate comment); when_to_use names its trigger moment (pr-land) |  |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["targets"]), confirmed |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### doc-readme

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (keep) | user-facing structure + prose |
| 2.2 effort | medium (add) | standard doc work |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + gate comment) |  |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["mode","target"]), confirmed |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### doc-update_misc

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (keep) | reconciling doc against shipped code |
| 2.2 effort | medium (add) | standard doc work |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + gate comment) |  |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["doc"] | single clean slot |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### export-roadmap_zip

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (keep) | runs one zsh script |
| 2.2 effort | low (add) | deterministic |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | n/a — takes no arguments |  |
| 3.3 arguments (named) | n/a — takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### hud-pr_wall

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (keep) | script output + bucketing |
| 2.2 effort | low (keep) | confirmed |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + comment); read-only |  |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["scope","root"]), confirmed |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### hud-whats_new

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (keep) | user-facing synthesis of diffs |
| 2.2 effort | low (add) | quick memo, not analysis |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + comment); read-only wrap-up |  |
| 3.2 argument-hint | AMENDED: added "[since ref (optional)]" | |
| 3.3 arguments (named) | AMENDED: added ["since"] + Scope section pinning the measurement window | |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### hud-worktrees

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (keep) | shepherds destructive ops; safety judgement |
| 2.2 effort | medium (add) | mutations are approval-gated but consequential |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + comment); mutations approval-gated |  |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["action","branch"]), confirmed |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### import-scaffold_artefact

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (down from opus) | code conversion/porting; Sonnet 5 strong at mechanical translation |
| 2.2 effort | high (add) | large multi-file transform |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | path plus optional 'react' flag; variadic-ish |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### next-task-group

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (keep) | script + grouping |
| 2.2 effort | low (keep) | confirmed |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["pivot"] | single clean slot |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### next-task-ship

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | fable (UP from opus) | unattended long-horizon delivery loop (implement, test, PR, self-review) — the one workload where Mythos-class autonomy pays |
| 2.2 effort | high (add) | unattended = no human catches mid-loop drift |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | forwards $ARGUMENTS verbatim to next-task-suggest |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### next-task-suggest

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (keep) | grounded pick from pre-vetted ready-set |
| 2.2 effort | low (keep) | confirmed |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | CHANGED dmi true→false + comment: next-task-ship Step 1 invokes it via the Skill tool, which dmi:true mechanically blocks; also a natural 'what should I work on?' trigger. Read-only, no gate needed | orchestrator dependency |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | body parses by intent, not position; named args would misrepresent the contract |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### pr-create

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (keep) | description prose from commits |
| 2.2 effort | medium (add) | outward-facing but bounded |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | CHANGED dmi true→false + comment: invoked by next-task-ship Step 6 and branch-qa_review's Ready offer — both were mechanically blocked. Internal approval step is the gate; when_to_use rewritten with explicit never-invoke-speculatively guardrail | orchestrator dependency + existing gate |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | variadic: mode flags plus screenshot files/issue numbers |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### pr-handle_review

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | independent verification of review feedback before acting |
| 2.2 effort | high (add) | wrong triage ships wrong fixes |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["pr"] | single clean slot |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### pr-land

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (keep) | procedural but irreversible (merge, tag, delete) |
| 2.2 effort | medium (add) | irreversibility deserves attention, scripts do the maths |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["pr"] | single clean slot |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### pr-review-dry_run

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep; follows pr-review) | canonical methodology both entry points share |
| 2.2 effort | high (add) | as pr-review |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false, required by pr-review + branch-qa_review); read-only via disallowed-tools |  |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["mode","pr"]), confirmed |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### pr-review

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep; fable considered — flagged for user) | posted, outward-facing review; opus 5 strong, fable would boost at cost |
| 2.2 effort | high (add) | review quality is the product |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | CHANGED dmi true→false + comment: next-task-ship Step 7 invokes it. No internal gate before posting, so when_to_use carries a hard guardrail and Phase 5 will consider a Skill(pr-review) ask rule as the mechanical gate | orchestrator dependency; gate deferred to permissions |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | present (["mode","pr"]), confirmed |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### pr-update

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (keep) | description refresh from new commits |
| 2.2 effort | medium (add) | outward-facing prose |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + gate comment) |  |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["pr"] | single clean slot |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### project-audit_deps

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (down from opus) | script dump + web-research aggregation; advisory interpretation within Sonnet 5's reach |
| 2.2 effort | high (add) | security-adjacent conclusions need care |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["dep"] | single clean slot |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### project-tag_version

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | haiku (keep) | script-guarded svu tagging |
| 2.2 effort | low (keep) | confirmed |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | n/a — no arguments (body has no $ARGUMENTS) |  |
| 3.3 arguments (named) | n/a — takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### roadmap-audit-deps

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | graph-rationality interview; systemic judgement |
| 2.2 effort | high (add) | wrong edges poison the whole plan |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | was implicitly dual (no dmi field) — made EXPLICIT dmi:false + rationale comment | read-only interview; convention wants the exception annotated |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["milestone"] | single clean slot |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### roadmap-create-interview

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | interview synthesis into a coherent proposal |
| 2.2 effort | high (add) | quality of questions drives quality of plan |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | was implicitly dual — made EXPLICIT dmi:false + rationale comment | read-only interview |
| 3.2 argument-hint | n/a — no arguments (scope emerges in the interview) |  |
| 3.3 arguments (named) | n/a — takes no arguments |  |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### roadmap-create

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | greenfield decomposition of a project |
| 2.2 effort | high (add) | foundational output |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["phase"] | single clean slot |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### roadmap-maintain

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (down from opus) | roadmap.py does the graph maths; skill orchestrates and narrates |
| 2.2 effort | high (add) | raised from proposed medium: reconcile path infers from codebase evidence |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + gate comment) |  |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | arg is milestone-id-or-'reconcile'; dual semantics resist a single name |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### roadmap-migrate

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (down from opus) | validator-gated procedural conversion |
| 2.2 effort | high (add) | one-way transform; git checkpoint advised by the skill itself |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dmi:true confirmed; when_to_use retained as maintainer documentation | user-only, so description/when_to_use never reach the model; when_to_use costs zero context and documents intent |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["roadmap"] | single clean slot |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### roadmap-review

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | strategic health judgement, not mechanics |
| 2.2 effort | high (add) | the strategic complement; depth is the point |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | was implicitly dual — made EXPLICIT dmi:false + rationale comment | read-only interview, writes nothing |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | added ["milestone"] | single clean slot |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

### roadmap-update-tasks

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | sonnet (down from opus) | mechanical ID/edge wiring, approval-gated, roadmap.py validates |
| 2.2 effort | medium (add) | graph edits checked by validator |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | dual confirmed (dmi:false + gate comment); when_to_use already phrase-rich |  |
| 3.2 argument-hint | present, confirmed |  |
| 3.3 arguments (named) | skip — recorded | single free-form text blob; positional naming would fight shell quoting |
| 4.1 allowed-tools | TBD | |
| 4.2 disallowed-tools | TBD | |
| 5.1 context / agent / background | TBD | |
| 5.2 hooks | TBD | |
| 5.3 paths | TBD | |
| 5.4 shell | TBD | |
| 5.5 metadata | TBD | |
| 6.1 namespace conversion | TBD | |
| 6.2 string substitutions | TBD | |
| 6.3 supporting files | TBD | |
| 6.4 dynamic context | TBD | |
| 7.1 visibility lives in skill | TBD | |
| 7.2 evals | TBD | |
| 7.3 visual output | TBD | |
| 7.4 permissions | TBD | |
| 8.1 name | TBD | |
| 8.2 description | TBD | |

