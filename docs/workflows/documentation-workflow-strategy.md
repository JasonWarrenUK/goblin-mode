# Documentation Workflow Strategy

> **Purpose**: Define systematic approach to creating, maintaining, and syncing documentation across projects
>
> **Context**: Jason maintains comprehensive docs (Rhea example: technical overviews, ADRs, roadmaps, work records) but faces common pain points: docs getting out of sync, uncertainty about what to document, and time constraints.

---

## Current State Analysis

### Documentation Types You Use
Based on Rhea structure:

1. **User-facing**
   - About/Executive Summary
   - Getting Started guides
   - Quick reference guides

2. **Developer-focused**
   - Technical Overview (architecture, structure, components)
   - Architecture Decision Records (ADRs)
   - Reference docs (features, naming conventions)

3. **Project management**
   - Roadmaps (MVP tracking with status)
   - Work records (development sessions, refactoring progress)
   - Status reports (snapshots)

4. **Archives**
   - Old analyses, outputs, status reports
   - Preserves history without cluttering active docs

### Current Strengths
- ✅ Well-organized hierarchy (dev/, archives/, wip/)
- ✅ Comprehensive coverage across doc types
- ✅ Living documents (roadmaps track real-time status)
- ✅ Markdown with callouts/collapsibles
- ✅ Project-specific naming (Greek mythology theme)

### Identified Pain Points
1. **Docs get out of sync** - Code changes, docs lag behind
2. **Uncertainty about what to document** - What's worth the effort?
3. **Time constraints** - Documentation competes with development
4. **Discoverability** - Finding relevant docs as project grows

---

## Proposed Documentation Workflow

### Phase 1: Document Generation Triggers

**Automated prompts via hooks** (already configured):
- ✅ `post-commit-docs` hook detects when docs need updates
- Maps changed files to relevant documentation
- Saves reminders to `~/.claude/doc-reminders.txt`
- CLI helper: `claude-docs` to show/clear reminders

**Manual triggers** (for planning/design docs):
- Before starting new feature: Write design doc
- After architectural decision: Create ADR
- When API changes: Update API reference
- End of development session: Update work record

### Phase 2: Documentation Templates

Create reusable templates in `~/.claude/doc-templates/`:

```
~/.claude/doc-templates/
├── ADR.md                    # Architecture Decision Record
├── technical-overview.md     # Component/system overview
├── feature-spec.md           # Feature specification
├── api-reference.md          # API endpoint documentation
├── work-record.md            # Development session notes
├── roadmap.md                # MVP/feature roadmap
└── troubleshooting.md        # Common issues and solutions
```

**Usage**: Slash command or skill to scaffold from template

### Phase 3: AI-Assisted Documentation

**Leverage Claude Code for doc generation**:

1. **Automatic README generation**
   ```bash
   /doc/generate-readme
   ```
   - Analyzes project structure
   - Extracts key info from code
   - Generates comprehensive README

2. **API documentation from code**
   ```bash
   /doc/api-from-code
   ```
   - Scans route files
   - Extracts endpoint signatures
   - Documents parameters, responses

3. **Update existing docs**
   ```bash
   /doc/sync <doc-name>
   ```
   - Compares doc to current code
   - Suggests specific updates
   - Shows what's out of date

4. **ADR generation**
   ```bash
   /doc/adr <decision-title>
   ```
   - Interactive prompts for context, decision, alternatives
   - Generates formatted ADR
   - Places in appropriate directory

### Phase 4: Documentation Structure Convention

**Standardize across all projects**:

```
<project>/
├── docs/
│   ├── README.md              # Project overview (auto-generated)
│   ├── Getting-Started.md     # Setup instructions
│   ├── dev/
│   │   ├── Technical-Overview.md
│   │   ├── Architecture-Decisions.md
│   │   ├── architecture/      # Individual ADRs
│   │   ├── reference/         # API docs, guides
│   │   ├── roadmap/           # MVP tracking
│   │   └── troubleshooting.md
│   ├── wip/                   # Work in progress docs
│   └── archives/              # Historical docs
│       ├── analyses/
│       ├── status-reports/
│       └── work-records/
├── .claude/
│   └── CLAUDE.md              # Project context for AI
└── README.md                  # Root README (links to docs/)
```

### Phase 5: Documentation Maintenance Strategy

**What to document WHEN**:

| When | Document Type | Trigger |
|------|---------------|---------|
| **Before coding** | Design doc, Feature spec | Starting new feature |
| **During coding** | Inline comments, Code docs | Complex logic, public APIs |
| **After coding** | Work record, Update README | End of session, feature complete |
| **On architecture change** | ADR | Major design decision |
| **On API change** | API reference | Route added/modified |
| **Weekly** | Roadmap update | Sprint planning/review |
| **Monthly** | Status report, Archive old docs | End of milestone |

**Prioritization framework** (when time is limited):

1. **Critical** (always document)
   - Public APIs
   - Architecture decisions
   - Setup/installation steps
   - Breaking changes

2. **Important** (document if time allows)
   - Component overviews
   - Feature specifications
   - Troubleshooting guides
   - Work records

3. **Nice-to-have** (defer if pressed)
   - Detailed inline comments
   - Historical status reports
   - Design alternatives not chosen

---

## Implementation Plan

### Immediate Actions (Today)

1. ✅ Post-commit-docs hook already configured
2. Create doc templates directory
3. Test `claude-docs` CLI helper

### Short-term (This Week)

4. Create slash commands for doc generation:
   - `/doc/generate-readme`
   - `/doc/api-from-code`
   - `/doc/adr <title>`
   - `/doc/sync <doc-name>`

5. Apply standard structure to new Iris project

### Medium-term (Next 2 Weeks)

6. Migrate existing projects to standard structure
7. Create documentation skill in `~/.claude/skills/documentation/`
8. Set up weekly roadmap review reminder

---

## Documentation Skill Definition

Create `/Users/jasonwarren/.claude/skills/documentation/SKILL.md`:

**Purpose**: Guide consistent, efficient documentation across all projects

**Key patterns**:
- Doc structure conventions
- Template usage
- Auto-generation strategies
- Prioritization framework
- Sync workflow (code → docs)

**Auto-invoked when**:
- Creating new project
- Adding API endpoints
- Making architecture decisions
- Updating existing docs

---

## Success Metrics

**Documentation is working when**:

1. ✅ Docs stay in sync with code (hook prompts catch changes)
2. ✅ New features have docs before/during development
3. ✅ Architecture decisions are recorded as ADRs
4. ✅ Team members (future you, collaborators) can onboard from docs alone
5. ✅ Documentation takes <20% of development time

**Red flags** (doc debt accumulating):

- ⚠️ Multiple reminder entries in `doc-reminders.txt` ignored
- ⚠️ Code comments say "TODO: document this"
- ⚠️ Questions about "how does X work" that docs should answer
- ⚠️ Breaking changes without updated docs

---

## Next Steps

1. Create doc templates directory and templates
2. Build `/doc/...` slash commands
3. Create documentation skill
4. Apply to Iris project when it starts

---

## Related Files

- Post-commit-docs hook: `~/.claude/hooks/post-commit-docs`
- Doc reminders: `~/.claude/doc-reminders.txt`
- CLI helper: `~/bin/claude-docs`
- Example structure: `/Users/jasonwarren/Code/rhea/docs/`
