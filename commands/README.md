# Commands

Slash commands for Claude Code. Organised by domain, with model tier encoded in the filename:

| Suffix | Model | Use when |
|--------|-------|----------|
| `delta` | Haiku | Fast, straightforward tasks |
| `gamma` | Sonnet | Balanced reasoning |
| `omega` | Opus | Complex analysis or thorough work |

---

## Codebase (`codebase/`)

| Command | Description |
|---------|-------------|
| `/codebase:introduce:omega` | High-level overview for a new developer |
| `/codebase:analyse:investigate:omega` | Deep-dive into structure and relationships |
| `/codebase:analyse:critique:omega` | Identify weaknesses and implementation issues |
| `/codebase:check:dependencies:omega` | Audit packages — deprecations, updates, risks |

---

## Documentation (`doc/`)

| Command | Description |
|---------|-------------|
| `/doc:create:readme:omega` | Generate a comprehensive README |
| `/doc:create:roadmap:omega` | Create a structured milestone roadmap |
| `/doc:create:adr:gamma` | Guide through an Architecture Decision Record |
| `/doc:create:work-record:delta` | Summarise today's development session |
| `/doc:create:status-report:delta` | Generate a status report |
| `/doc:update:roadmap:omega` | Reorganise roadmap tasks and update diagrams |
| `/doc:update:target:gamma` | Update docs to reflect recent code changes |

---

## Git (`git/`)

| Command | Description |
|---------|-------------|
| `/git:commit:one:delta` | Stage all and generate a conventional commit |
| `/git:commit:batch:delta` | Split changes into granular logical commits |
| `/git:assess-branch:omega` | Check branch readiness for PR |
| `/git:merge-from-main:omega` | Merge main into current branch |
| `/git:pr:draft:main:gamma` | Create a draft PR to main |
| `/git:pr:full:main:gamma` | Create a final PR to main |
| `/git:pr:full:staging:gamma` | Create a PR to staging |

---

## Linear (`linear/`)

| Command | Description |
|---------|-------------|
| `/linear:create:issue:gamma` | Create an issue with optional relations |
| `/linear:crit-path-to:project:omega` | Decompose a project into dependency-ordered issues |
| `/linear:crit-path-to:task:omega` | Decompose an issue into sub-issues |
| `/linear:tackle:delta` | Fetch and begin a Linear task |
| `/linear:tackle:gamma` | Fetch and begin — fix adjacent issues |
| `/linear:tackle:omega` | Fetch and begin — thorough, fix wider issues |

---

## Suggest (`suggest/task/`)

Analyse the codebase and suggest the next logical task. Breaks anything >45 min into subtasks.

| Command | Description |
|---------|-------------|
| `/suggest:task:delta` | Quick suggestion |
| `/suggest:task:gamma` | Balanced suggestion |
| `/suggest:task:omega` | Thorough suggestion with full context |

---

## Do (`do/minima/`)

Accomplish an arbitrary task with a minimalist approach. Pass the task inline.

| Command | Description |
|---------|-------------|
| `/do:minima:delta` | Haiku — fast |
| `/do:minima:gamma` | Sonnet — balanced |
| `/do:minima:omega` | Opus — thorough |

---

## WIP (`wip/`)

| Command | Description |
|---------|-------------|
| `/wip:roadmap` | Compare roadmaps to current codebase state |
| `/wip:version` | Check and update version numbers across files |
