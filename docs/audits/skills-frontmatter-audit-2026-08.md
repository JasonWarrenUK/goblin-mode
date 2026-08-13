# Skills Frontmatter Audit — August 2026

| Prop | Value |
|------|-------|
| Started | 2026-08-13 |
| Status | Phase 2 — decisions recorded, edits pending sign-off on two policies |
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

## Per-skill record

### analyse-concept

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | opus (keep) | forked deep investigation; judgement is the product |
| 2.2 effort | high (add) | standalone forked workload |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 2.2 effort | medium (add) | validator-gated |
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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
| 3.1 invocation (disable-model-invocation / user-invocable / when_to_use) | TBD | |
| 3.2 argument-hint | TBD | |
| 3.3 arguments (named) | TBD | |
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

