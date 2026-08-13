# Skills Frontmatter Audit — August 2026

| Prop | Value |
|------|-------|
| Started | 2026-08-13 |
| Status | Phase 1 — awaiting plan approval |
| Skills | 57 |

Record of decisions for every skill across every audit step. Each cell starts as `TBD`; a completed step fills in the decision and (where non-obvious) the reasoning. Steps are completed for ALL skills before moving to the next step.

## Cross-cutting findings

- `Skill(version)` allow rule in `settings.json:19` references a skill that does not exist (closest: `project-tag_version`). Flag for Phase on permissions/visibility.
- Prefix → directory namespace (Non-Property Audit 1): docs do NOT support nested namespace directories under `~/.claude/skills/`. Directory-qualified names (`apps/web:deploy`) come only from nested `.claude/skills/` dirs under the *working directory* (monorepo pattern), and only surface on name clashes. Decision needed from Jason.

## Per-skill record

### analyse-concept

| Step | Decision | Reasoning |
|------|----------|-----------|
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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
| 2.1 model | TBD | |
| 2.2 effort | TBD | |
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

