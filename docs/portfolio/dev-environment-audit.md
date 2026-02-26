# Dev Environment Audit
> **Purpose**: Systematic review of Jason's developer environment and Claude Code workflow, with focus on optimising for upcoming projects (especially Iris, the ILR File Creator replacement).
>
> **Context**: Created 2026-01-06 while waiting for AM1 Proposal confirmation. Cannot start new projects until confirmation received, so using downtime productively.

---

## Jason's Profile
### Overview
- Jason Warren, completing Level 4 Software Developer apprenticeship at Founders and Coders
- Neurodivergent - prefers direct, structured communication
- Primary interface: Claude Code CLI (rarely web/chat)
- Hardware: MacBook Air M2 (2022)
- IDE: Zed

### Naming Convention
Projects use evocative single words paired with functional descriptors (Rhea, Theia, Iris, etc.)

---

## Active Projects
### Level 4 Software Developer Apprenticeship End-Point Assessment
- **AM1 Project**: Proposal submitted, awaiting confirmation
	- **Iris**: Planned replacement for ILR File Creator
- **AM2 Portfolio**: Submitted
	- evidence catalogue approach
	- ~80% evidence / 20% context

### Rhea
- Svelte/LangChain curriculum generator

---

## Environment Baseline
### Claude Code Configuration
- **Location**: `~/.claude/`
- **Global CLAUDE.txt**: Empty (identified as gap)
- **Commands directory**: `~/.claude/commands/` with nested structure
- **Agents**: `~/.claude/agents/implementation-planner.md`
- **Output styles**: `~/.claude/output-styles/quality-dev-mentor.md`

### Existing Slash Commands
| Path                         | Purpose                                  | Notes                          |
| ---------------------------- | ---------------------------------------- | ------------------------------ |
| `analyse/codebase.md`        | High-level codebase overview             |                                |
| `analyse/critique.md`        | Code critique                            |                                |
| `analyse/roadmap.md`         | Compare roadmaps to codebase state       |                                |
| `git/commit.md`              | Conventional commits with pig notes      | Custom commit style            |
| `git/pull-request.md`        | PR creation                              |                                |
| `plan/create.md`             | Implementation planning                  |                                |
| `style/layout/fix.md`        | Layout fixes                             |                                |
| `style/style/unify.md`       | Style unification                        |                                |
| `task/execute/minima.md`     | Minimalist task execution                |                                |
| `task/suggest/general.md`    | Suggest next task from codebase analysis |                                |
| `task/suggest/targeted.md`   | Suggest next task with focus area        |                                |
| `update/docs/recent-work.md` | Update docs based on recent commits      |                                |
| `update/roadmaps/all.md`     | Update roadmaps                          | **Rhea-specific, not generic** |

### Zed Configuration
- **Theme**: Catppuccin (Latte light / Macchiato dark)
- **Font**: Fira Code 16px
- **Default AI model**: claude-sonnet-4-5-thinking-latest
- **Formatter**: Prettier (external) for JS/TS
- **MCP servers configured**:
  - context7 (library docs)
  - GitHub (full suite of tools)
  - sequential-thinking

### Project-Level Config Example (ILR File Creator)
- Location: `~/Code/ilr-file-creator/.claude/settings.local.json`
- Permissions: Read `~/`, limited bash (cat, git, head, npm view), WebFetch (npm, github)
- Output style: quality-dev-mentor

---

## Status Key
- 🔴 Identified (not started)
- 🟡 In Progress
- 🟢 Addressed
- ⚪ Deferred (with reason)

---

## Findings
### `CC`: 🟡 Claude Code Config
| ID    | Status | Finding                                                         | Notes |
| ----- |:------:| --------------------------------------------------------------- | ----- |
| CC-01 |   🟢   | Global CLAUDE.txt empty                                         | Should contain: skill level, communication preferences (direct, neurodivergent-friendly), code style preferences, British English |
| CC-02 |   🔴   | No project onboarding/scaffolding workflow                      | Critical for Iris. Need command to structure new project setup. **Includes:** roadmap config (`.claude/roadmaps.json`), MCP config (`.mcp.json`), project-level CLAUDE.md, directory structure. Addresses overall project init strategy. Incorporates learnings from SH-01, GC-01. |
| CC-03 |   🟢   | Roadmap command is Rhea-specific                                | Hardcodes paths like `docs/dev/roadmap/Rhea-MVP.md`. Needs genericising or project-specific override pattern |
| CC-04 |   🔴   | No testing workflow commands                                    | No `/test/...` structure despite Vitest/Jest experience. `.claude/skills/testing-foundations/SKILL.md` now exists but consider creating slash commands if they add value |
| CC-05 |   🟢   | No hooks configured                                             | Three hooks implemented: (1) post-commit-evidence - AI-powered KSB evidence extraction for AM1 portfolio, (2) post-commit-docs - documentation sync reminders, (3) pre-push-tests - test automation checks. All working and tested. |
| CC-06 |   🟢   | MCP servers not configured for CLI                              | Zed has context7, GitHub, sequential-thinking; Claude Code CLI doesn't mirror this |
| CC-07 |   🟢   | Current slash commands need audit                               | Assess each command: keep/modify/delete based on actual usage and modern best practices |
| CC-08 |   🟢   | CLAUDE.txt should be CLAUDE.md                                  | Documentation emphasises .md format. Current global config uses .txt extension |
| CC-09 |   🟢   | Skills (SKILL.md) system unexplored                             | Auto-invoked knowledge bases in `.claude/skills/<name>/SKILL.md`. Different from manual slash commands. **Decision:** Will use skills for project styling conventions (replace existing style commands) |
| CC-10 |   🔴   | .mcp.json project-level config not used                         | Can check in MCP config to projects for team-wide access. Currently only user-level MCP |
| CC-11 |   🟢   | Complete audit of `~/.claude/` directory structure and contents | |

### `DA`: 🔴 Documents & Artefacts Required
| ID    | Status | Finding                             | Notes                                                                                 |
| ----- |:------:| ----------------------------------- | ------------------------------------------------------------------------------------- |
| DA-01 |   🟢   | Structured overview of audit outcome is needed after Phase 1 & 2 | This needs to be comprehensive but scannable by Jason's manager |
| DA-02 |   🔴   | Update of audit overview is needed after Phase 3 |  |
| DA-03 |   🔴   | OrbStack installation & configuration | Fast, native macOS Docker runtime. Solves "I don't understand Docker" problem. Enables database containers for projects (PostgreSQL, Redis, Neo4j) |
| DA-04 |   🔴   | Mani installation & multi-repo configuration | Cross-project overview and batch operations tool. Requires fzf (already installed). Enables portfolio metrics, bulk git operations |


### `GC`: 🟢 Git Config
| ID    | Status | Finding                        | Notes                                                                                                                                                      |
| ----- |:------:| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GC-01 |   🟢   | Git configuration optimization | Part A: Review and document current `.gitconfig`. Part C: Establish branch naming conventions. Part D: Configure useful git aliases. Part B moved to RS-02 |

### `RS`: 🟡 Research
| ID    | Status | Finding                             | Notes |
| ----- |:------:| ----------------------------------- | ----- |
| RS-01 |   🟢   | Claude Code capabilities unexplored | Research official documentation for features/patterns not currently leveraged. Create tasks based on findings |
| RS-02 |   🔴   | Git merge vs rebase understanding   | Educational: Understand merge vs rebase with practical examples. Important for workflow, but lower urgency than immediate git config optimization |
| RS-03 |   🔴   | CLI tools discovery                 | Research and identify 3-5 CLI tools that would significantly improve workflow efficiency. Will be tackled after establishing baseline workflows (CC-12, CC-13) |
| RS-04 |   🔴   | User interested in state machine functionality | Help user decide whether this would be beneficial, then research & identify 2-3 libaries work with their stack |

### `SH`: 🟢 Shell/Terminal Config
| ID    | Status | Finding                        | Notes                                                                                                                                                                            |
| ----- |:------:| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SH-01 |   🟢   | Terminal workflow optimization | Part A: Document current setup (zsh, Oh My Zsh, zoxide, iTerm2). Part B: Create high-impact aliases. Part C: Configure iTerm2 profiles and tab management. Part D moved to RS-03 |

### `WF`: 🔴 Workflow Gaps
| ID    | Status | Finding                             | Notes                                                                                 |
| ----- |:------:| ----------------------------------- | ------------------------------------------------------------------------------------- |
| WF-02 |   🔴   | Command usage patterns unknown      | No data on which commands are actually used vs theoretical                            |
| WF-03 |   🔴   | Headless mode (-p flag) unexplored  | `claude -p "prompt"` for programmatic/CI usage. Fan-out patterns for bulk operations  |
| WF-04 |   🔴   | Git worktrees workflow not explored | Multiple parallel agents on different branches. Useful for complex multi-feature work |

### `WP`: 🔴 Workflow Patterns
| ID    | Status | Finding                                   | Notes                                                                                                                                                        |
| ----- |:------:| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| WP-01 |   🟢   | Documentation workflow strategy           | Created comprehensive strategy with templates, slash commands, and hook integration. Templates in `~/.claude/doc-templates/`, commands in `~/.claude/commands/doc/` |
| WP-02 |   🟢   | Debugging workflow patterns               | Created five-step universal framework, debugging skill, and runtime-aware patterns. Strategy in `~/.claude/debugging-workflow-patterns.md`, skill in `~/.claude/skills/debugging/` |
| WP-03 |   🔴   | Apprenticeship evidence tracking workflow | Generic framework for tracking development work for portfolio evidence. Maps work to KSBs/assessment criteria. Reusable and shareable with other apprentices |
| WP-04 |   🔴   | Degit template creation workflow | Create reusable project templates (Svelte+TS+Supabase, etc) for rapid experiment bootstrapping. Ensures consistent structure across projects |

### `ZD`: 🟢 Zed Config
| ID    | Status | Finding                          | Notes                                                                                     |
| ----- |:------:| -------------------------------- | ----------------------------------------------------------------------------------------- |
| ZD-01 |   🟢   | API key exposed in settings.json | context7 and GitHub PAT in plaintext. Security concern if dotfiles are version controlled |

---

## Decisions Made
| Date       | Decision                                            | Rationale                                                |
| ---------- | --------------------------------------------------- | -------------------------------------------------------- |
| 2026-01-06 | Track audit in `~/.claude/dev-environment-audit.md` | Keep with Claude Code config; serves as handoff document |

---

## Proposed Task Order
### Phase 1: 🟢 Foundation & Quick Wins
**Goal**: Fix security, establish efficient baseline

1. 🟢 **ZD-01** - Secure API keys
2. 🟢 **SH-01** - Terminal workflow optimization
	- 🟢 **SH-01A** - Document current setup (zsh, Oh My Zsh, zoxide, iTerm2)
	- 🟢 **SH-01B** - Create high-impact aliases for frequent operations
	- 🟢 **SH-01C** - Configure iTerm2 profiles and tab management
3. 🟢 **GC-01** - Git configuration optimization
	- 🟢 **GC-01A** - Review and document current `.gitconfig`
	- 🟢 **GC-01C** - Establish branch naming conventions (document why, not just what)
	- 🟢 **GC-01D** - Configure useful git aliases

### Phase 2: 🟢 Infrastructure & Learning
4. 🟢 **CC-11** - Complete `~/.claude/`audit
5. 🟢 **CC-06** - MCP servers for CLI
6. 🟢 **CC-09** - Skills system + create styling skill (~30-45 min)
7. 🟢 **CC-05** - Hooks exploration + configure automation (~30 min)
8. 🟢 **WP-01** - Documentation workflow strategy (~30-45 min)
9. 🟢 **WP-02** - Debugging workflow patterns (~30-45 min)
10. 🟢 **RS-03** - CLI tools discovery (end of Phase 2, after baseline workflows)
11. 🟢 **DA-01** - Structured overview of Audit Outcome (~30 min)

**Phase 2 Status**: 100% complete (8 of 8 tasks done)

### Phase 3: 🟡 Iris Preparation (4-6 hours)
12. 🟢 **WP-03** - Generic apprenticeship evidence tracking (~1-2 hours)
    - **Already complete from CC-05:** post-commit-evidence hook provides this functionality
    - Reusable for future apprenticeships, shareable with Jaz
13. 🔴 **CC-02** - Project onboarding workflow (~2-3 hours)
    - Incorporates learnings from SH-01, GC-01
    - Includes: roadmap config, MCP config, project CLAUDE.md, directory structure
14. 🔴 **PI-01** - Project integration checklist (~30-45 min)
    - Per-project setup guide ensuring consistent workflow across portfolio projects
    - Checklist for conventional commits, svu tagging, accessibility audits, stats generation
    - **Depends on:** CC-02 (project onboarding workflow)
15. 🔴 **CC-04** - Testing workflow patterns (~1-2 hours)
16. 🔴 **DA-02** - Update of structured audit outcome overview (~30 min)

### Phase 4: 🔴 Optional/Deferred Infrastructure
17. 🔴 **DA-03** - OrbStack installation & configuration (~30 min)
    - Docker Desktop replacement, solves "I don't understand Docker" problem
    - Set up PostgreSQL, Redis, Neo4j containers
    - **Not blocking Iris:** Can develop without local database containers
18. 🔴 **DA-04** - Mani installation & multi-repo configuration (~45 min)
    - Cross-project overview and batch operations
    - Create config for all apprenticeship projects
    - **Not blocking Iris:** Nice-to-have for portfolio management
19. 🔴 **WP-04** - Degit template creation (~1 hour)
    - Create reusable Svelte+TS+Supabase template
    - Document template usage and customization
20. 🔴 **RS-02** - Git merge vs rebase understanding
21. 🔴 **WF-02** - Command usage patterns analysis
22. 🔴 **WF-03** - Headless mode exploration
23. 🔴 **WF-04** - Git worktrees workflow
24. 🔴 **RS-04** - State machine investigation

### Phase 5: 🔴 **Iris** Development
See `docs/iris-development-tracker.md` - begins after AM1 confirmation + environment optimization complete

---

## Session Log
### 2026-01-06 - Initial Audit
- Established hardware/IDE baseline
- Mapped full slash command structure
- Reviewed Zed settings including MCP servers
- Reviewed output style (quality-dev-mentor) and agent (implementation-planner)
- Identified 6 Claude Code gaps, 1 Zed issue, 3 Iris setup items, 2 workflow gaps
- Created this tracking document

**Conversation ended**: Ready to resume in new instance. Start by reviewing this document and asking which finding to tackle first.

---

### 2026-01-06 - Continuation: RS-01 Research & Priority Tasks
- ✅ **RS-01 Complete**: Researched Claude Code capabilities from Anthropic docs and community resources
	- Added 4 new CC findings: CLAUDE.md format (CC-08), Skills system (CC-09), .mcp.json (CC-10), slash command audit (CC-07)
	- Added 2 new WF findings: Headless mode (WF-03), Git worktrees (WF-04)
	- Key discoveries: Skills vs Commands distinction, Hooks lifecycle events, hierarchical settings, subagent patterns
- ✅ **Task Categorization Complete**: Analyzed all tasks and reassigned to appropriate categories
	- **Consolidated tasks**: Merged WF-01 (project init strategy) and former CC-11 (roadmap config) into CC-02 (project onboarding workflow)
	- **Separated Iris development**: Moved IR-* tasks to `iris-development-tracker.md` - this audit focuses on preparatory tooling and environment optimization only
	- Created new categories: SH (Shell/Terminal), GC (Git), WP (Workflow Patterns)
	- Reassigned: CC-15→SH-01, CC-16→GC-01, CC-12→WP-01, CC-13→WP-02, CC-14→WP-03
	- Split educational tasks: CC-15D→RS-03, CC-16B→RS-02
	- Final structure: 18 tasks across 7 categories for clearer organization
- ✅ **CC-01 & CC-08 Complete**: Created global CLAUDE.md (not .txt) with comprehensive config
	- Developer profile (corrected: Python minimal, Rust removed, Svelte preferred, testing as weakness)
	- Communication preferences (direct, British, neurodivergent-friendly)
	- Code style (paradigm-neutral, honest about testing gaps)
	- Documentation/security standards
	- Tone: Technical precision with personality, not corporate handbook
- ✅ **CC-03 Complete**: Genericised roadmap command with config-driven approach
	- Moved Rhea-specific version to project-level (`rhea/.claude/commands/update/roadmaps/all.md`)
	- Created generic `all.md` (process all active roadmaps from config)
	- Created generic `single.md` (process specific roadmap by ID)
	- Identified need for `.claude/roadmaps.json` config (incorporated into CC-02)
- ✅ **CC-07 Complete**: Audited all slash commands (15 total)
	- **Deleted (2)**: `plan/create.md` (superseded by native plan mode), `update/roadmaps/chain.md` (superseded by config-driven approach)
	- **Modified (4)**: `analyse/codebase.md` & `analyse/critique.md` (removed outdated skill guidance), `git/commit.md` & `git/pull-request.md` (removed pig notes)
	- **Kept (9)**: All other commands remain valuable for their specific workflows
	- **Decision**: Use Skills system for styling conventions (replaces style commands - tracked in CC-09)
- **Next**: Begin Phase 1 execution (ZD-01, SH-01, GC-01)

---

### 2026-01-06 - Phase 1 Execution: Security & Terminal Optimization
- ✅ **ZD-01 Complete**: Secured API keys (~15 min)
	- Moved Context7 API key and GitHub PAT from Zed settings.json to environment variables
	- Added keys to ~/.zshrc: CONTEXT7_API_KEY and GITHUB_PAT
	- Updated Zed settings to reference $CONTEXT7_API_KEY and $GITHUB_PAT
	- **Incident**: Accidentally overwrote entire ~/.zshrc during initial implementation
	- **Recovery**: Reconstructed from captured tail (30 lines), Oh My Zsh template, and pre-oh-my-zsh backup
	- Result: API keys now stored securely in shell environment, not version controlled
- ✅ **SH-01 Complete**: Terminal workflow optimization (~1.5 hours)
	- **Part A**: Documented current setup in `~/.claude/terminal-setup-documentation.md`
	    - Shell: zsh with Oh My Zsh (robbyrussell theme, git plugin)
	    - Navigation: zoxide with custom alias (cd → z), broot
	    - Runtime managers: NVM, Deno, bun
	    - Language paths: Python 3.9, .NET
	    - Inactive plugins identified: zsh-autosuggestions (installed but not enabled)
	- **Part B**: Created high-impact aliases in `~/.oh-my-zsh/custom/dev-aliases.zsh`
	    - Git: 12 aliases (gs, gl, gd, gDC, gb, gBD, gCM, gClean, gPristine)
	    - npm: 7 aliases (nI, nID, nRD, nRB, nRT, nRS, nukeN)
	    - bun: 6 aliases (bI, bID, bD, bB, bT, nukeB)
	    - deno: 5 aliases (dR, dT, dTest, dFmt, dLint)
	    - Workflow: 6 aliases (z., cc, ll, .., ..., tree, reload)
	    - System: 3 aliases (dUs, myIP, psGrep)
	    - All use camelCase for multi-char shortcuts for memorability
	- **Part C**: Created iTerm2 configuration guide in `~/.claude/iterm2-setup-guide.md`
	    - Profile setup (colors matching Zed: Catppuccin, font: Fira Code 16pt)
	    - Keyboard shortcuts for tab/pane management
	    - Shell integration instructions
	    - Status bar configuration
	    - Window arrangements for project workflows
	    - Export/backup process
	    - 10-15 min quick start checklist
- **Key learnings**:
	- Always check file size/structure before overwriting (use append for shell configs)
	- Keep backups of critical config files (`.zshrc`, `.gitconfig`)
	- zoxide fuzzy matching explained: frecency-based directory jumping
	- User prefers camelCase aliases (nID not nid) and consistent naming (nukeN/nukeB)
	- `lsd` already installed (modern ls replacement)
	- Claude Code currently invoked as `claude`, aliased to `cc` for efficiency
- **Next**: GC-01 (Git configuration optimization - Parts A, C, D)

---

### 2026-01-06 - Phase 1 Execution: Git Configuration
- ✅ **GC-01 Complete**: Git configuration optimization (~1 hour)
	- **Part A**: Reviewed and documented git setup in `~/.claude/git-configuration-documentation.md`
		- Cleaned `.gitconfig`: Removed Sourcetree integration and commit template
		- Current config: LFS, user identity, pull strategy (merge, not rebase)
		- Editor kept as `code --wait` (fallback, LazyGit is primary interface)
	- **Part A (continued)**: Updated `.gitignore_global`
		- Removed duplicate `.DS_Store`
		- Changed broad `settings.json` to `.config/zed/settings.json` (Zed-specific)
		- Added comprehensive ignores: macOS system files, editor configs, env files, dependencies, build artifacts, logs
		- Organized into 6 categories for maintainability
	- **Part C**: Created branch naming conventions in `~/.claude/git-branch-naming-conventions.md`
		- 21 branch prefixes across 7 categories (Core Development, Code Quality, Docs/Content, Styling/UI, Dependencies/Config, CI/CD, Experimental)
		- Structure: `<prefix>/<short-description>` (lowercase, hyphens, imperative mood)
		- Breaking changes: Prefix description with `breaking-` (e.g., `feat/breaking-api-redesign`)
		- Distinction: `styles/` for visual styling vs `layout/` for structural positioning
		- Decision tree for choosing correct prefix
		- Quick reference card for common lookups
	- **Part D**: Added 8 git aliases to `.gitconfig`
		- Semantic operations: `unstage`, `undo`, `amend`
		- Information: `last`, `branches`
		- Workflow: `sync`, `save`
		- Cleanup: `delete-merged`
		- Complement (not replace) shell aliases - used for semantic clarity when not in LazyGit
- **Key learnings**:
	- LazyGit is primary interface - git aliases useful for semantic operations and CLI fallbacks
	- Global gitignore needs specificity (`.config/zed/settings.json` not broad `settings.json`)
	- Branch naming benefits from granularity: 21 prefixes better than generic `feature/`
	- Breaking changes work better as prefix (`feat/breaking-`) than suffix for scannable branch lists
	- Git aliases vs shell aliases: Different invocations (`git unstage` vs `gs`), different use cases
- **Next**: Phase 2 starts with CC-06 (MCP servers for CLI)

### 2026-01-07 - Phase 2 Execution: Configuration Analysis & MCP Setup
- ✅ **CC-11 Complete**: Analyse `.claude` folder contents (~30 min)
	- Created comprehensive analysis in `~/.claude/claude-config-analysis.md`
	- **Findings**:
		- 13 slash commands across 6 categories (analyse, git, style, task, update)
		- 1 agent (implementation-planner), 1 output style (quality-dev-mentor)
		- 0 plugins installed (clean slate for Phase 2)
		- 13 MCP servers available in marketplace (context7, GitHub, asana, slack, stripe, etc.)
		- 24 official plugins available (LSPs, development tools, utilities)
		- 5 tracked projects with session histories
	- **Critical gaps identified**:
		- No MCP servers active in CLI (despite available integrations)
		- No project-level CLAUDE.md or .mcp.json files
		- Style commands should migrate to skills system
		- No hooks configured for automation
	- **Strategic opportunities**:
		- Enable context7 and GitHub MCP for CLI workflows
		- Create styling skill to replace style commands
		- Configure hooks for common workflows
		- Install useful official plugins
- ✅ **CC-06 Complete**: MCP servers for CLI (~10 min)
	- User manually configured context7 and GitHub MCP servers using official documentation
	- **Commands used**:
		- `claude mcp add --transport stdio context7 -- npx -y @upstash/context7-mcp`
		- `claude mcp add --transport http github https://api.githubcopilot.com/mcp/ --header "Authorization: Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}"`
	- **Environment setup**:
		- Added `export GITHUB_PERSONAL_ACCESS_TOKEN="$GITHUB_PAT"` to `.zshrc`
		- Sourced `.zshrc` to reload environment
	- **Result**: Claude Code CLI now has library documentation (context7) and GitHub integration available
- **Key learnings**:
	- Always check official Anthropic documentation first for accurate configuration methods
	- MCP servers use `claude mcp add` command with transport types (stdio, http, sse)
	- Environment variable aliases needed when MCP expects different var names
	- User prefers self-service after guidance rather than automated execution

### 2026-01-08 - Phase 2 Execution: Skills System & Hooks Configuration
- ✅ **CC-09 Complete**: Skills system exploration + 8 skills created (~2 hours)
	- Created 8 skills in `~/.claude/skills/` using SKILL.md format
	- **Skills created**:
		1. frontend-styling (public) - Design patterns for web UI
		2. testing-foundations (public) - Vitest testing patterns
		3. data-ontology (user) - Graph/relational DB design
		4. systematic-debugging (user) - Structured problem-solving
		5. cypher-linguist (user) - Neo4j query patterns
		6. git-manager (public) - Git workflow patterns
		7. svelte-ninja (user) - Svelte 5 + SvelteKit patterns
		8. api-designer (user) - TypeScript API design patterns
	- **Key decisions**:
		- Zod for validation (TypeScript-first, type inference)
		- No universal ORM (polyglot persistence with typed wrappers)
		- Result types for expected failures, Error classes for exceptions
		- URL-based API versioning (`/api/v1/`)
		- Svelte 5 runes ($state, $derived, $effect)
	- **Skills system advantages**:
		- Auto-invoked by Claude (no manual slash commands)
		- Persistent knowledge across sessions
		- Can be public (shared) or user-specific
- ✅ **CC-05 Complete**: Hooks configuration (~3 hours)
	- Created 3 hooks in `~/.claude/hooks/`
	- **Hook 1 - post-commit-evidence**: AI-powered KSB evidence extraction
		- Hybrid approach: keyword triggers → Claude AI analysis
		- Comprehensive AM1-only KSB detection (K2, K6, K9, K11, S1, S4, S6, S7, S10, S11, S12, S16, B2, B3)
		- Outputs to `~/.claude/docs/evidence-tracker.md`
		- Evidence format: KSB Index (with links) + Evidence Journal (chronological)
		- Extracts detailed technical evidence with line numbers, algorithms, patterns
		- Includes methodology notes and next steps
		- Handles multiline commits, strips markdown from Claude responses
	- **Hook 2 - post-commit-docs**: Documentation sync reminders
		- Maps changed files to relevant docs (api.md, components.md, database.md, etc.)
		- Prompts to update docs or saves to `~/.claude/doc-reminders.txt`
		- CLI helper: `claude-docs` to show/clear reminders
	- **Hook 3 - pre-push-tests**: Test automation checks
		- Detects new code without tests (functions, classes, components)
		- Identifies test runner (npm/bun/deno/pnpm/yarn)
		- Runs existing tests before push
		- Prompts to add tests or push anyway if tests fail
		- Ignores config/doc/style files
	- **Per-project activation**:
		- `.git/hooks/post-commit` calls both evidence and docs hooks
		- `.git/hooks/pre-push` symlinks to pre-push-tests
	- **Testing**: All hooks tested and working in ilr-file-creator project
- **Key learnings**:
	- Skills auto-invoke (superior to manual commands for persistent knowledge)
	- Hooks enable automated workflows without manual intervention
	- AI-powered evidence extraction provides detailed, technical KSB documentation
	- Bash on macOS requires careful handling of multiline strings and process forking
	- Claude CLI `--print` mode required for parsing JSON responses
	- Markdown code fences must be stripped from Claude responses for JSON parsing
- ✅ **WP-01 Complete**: Documentation workflow strategy (~1.5 hours)
	- Created comprehensive documentation workflow strategy in `~/.claude/documentation-workflow-strategy.md`
	- **Templates created** (6 templates in `~/.claude/doc-templates/`):
		1. ADR.md - Architecture Decision Records with structured decision capture
		2. technical-overview.md - Component/system documentation with API details
		3. feature-spec.md - Feature specifications with user stories and acceptance criteria
		4. api-reference.md - Comprehensive API endpoint documentation
		5. work-record.md - Development session summaries for portfolio evidence
		6. roadmap.md - MVP/feature tracking with milestones and KPIs
	- **Slash commands created** (4 commands in `~/.claude/commands/doc/`):
		1. `/doc/adr` - Interactive ADR generation from template
		2. `/doc/sync` - Update docs based on code changes
		3. `/doc/generate-readme` - Auto-generate README from project analysis
		4. `/doc/work-record` - Generate session summary from git commits
	- **Integration points**:
		- Commands use templates for consistent structure
		- Integrates with post-commit-docs hook for reminders
		- Work records provide AM2 portfolio evidence
		- Follows existing Rhea documentation patterns
	- **Quick reference**: Created `~/.claude/doc-commands-reference.md` with examples and tips
- **Key learnings**:
	- Templates reduce cognitive load (no blank page problem)
	- Hooks + templates + AI = automated documentation workflow
	- Interactive commands gather context that git can't capture
	- Work records double as both development history and portfolio evidence
	- Documentation is most effective when integrated into development flow, not as afterthought
- ✅ **WP-02 Complete**: Debugging workflow patterns (~45 min)
	- Created comprehensive debugging workflow strategy in `~/.claude/debugging-workflow-patterns.md`
	- **Five-step universal framework**: Reproduce → Isolate → Diagnose → Fix → Verify
	- **Debugging scenarios covered**:
		1. Runtime errors (crashes, exceptions)
		2. Test failures (unit, integration, E2E)
		3. Logic bugs (wrong behavior)
		4. Performance issues (slow, timeout)
		5. Production issues (only in prod)
	- **Runtime detection pattern**: Automatically detect npm/bun/deno for correct commands
	- **Debugging skill created** in `~/.claude/skills/debugging/SKILL.md`:
		- Auto-invokes on bug/error/failing keywords
		- Five-step methodology for all scenarios
		- Runtime-aware command examples
		- Integration with work records, tests, and ADRs
	- **Tools & techniques documented**:
		- Browser DevTools patterns
		- Git bisect for finding when bugs introduced
		- TypeScript type debugging
		- Binary search debugging
		- Runtime-specific debugging (deno/bun/npm)
	- **Debugging checklist**: Before/during/after steps
	- **Common anti-patterns**: Random changes, no reproduction, masking errors, no documentation
- **Key learnings**:
	- Systematic debugging (five steps) prevents random trial-and-error
	- Runtime detection crucial for polyglot projects
	- Every fixed bug should get a test
	- Debugging sessions are valuable portfolio evidence (S7, B2, K9)
	- Reproducible bugs are half-solved
- ✅ **RS-03 Complete**: CLI tools discovery (~90 min)
	- Researched 14 homebrew formulae and 1 cask
	- **Recommended for installation** (3 tools):
		1. svu - Semantic version utility (automatic git tag versioning from conventional commits)
		2. vacuum - OpenAPI linter (conditional - if user builds REST APIs)
		3. pake - Webpage → desktop app (for Tauri/Iris learning and prototyping)
	- **Tools rejected** (8): beads, maigret, neo4j-mcp, xmlmind-editor, headson, mq, rad, witr
	- **Confirmed Phase 2 installations** (14 tools total):
		- Foundation: fzf, ripgrep, bat, jq, fd
		- Analysis: tokei, tickgit (via Go), axe-cli
		- Specialized: svu, vacuum, pake, degit
		- Infrastructure: orbstack (deferred to DA-03), mani (deferred to DA-04)
	- **Installation corrections identified**:
		- tickgit: Not in homebrew, requires Go installation
		- pake: Syntax requires `--name` flag
		- degit: LocalStorage warning is harmless
		- LazyGit: Remove invalid `--reuse-window` flag
	- **New audit tasks created**:
		- DA-03: OrbStack installation (Docker replacement)
		- DA-04: Mani installation (multi-repo management)
		- WP-04: Degit template creation workflow
	- **Key findings**:
		- svu perfect fit for git-based workflow with conventional commits
		- OrbStack solves stated "I don't understand Docker" problem
		- Tool research should consider stack fit, not just features
- **Key learnings**:
	- Not all useful tools are in homebrew (Go ecosystem important)
	- OSINT/specialized tools rarely relevant to software development
	- Installation instructions need verification against actual behavior
	- Deferred tasks better added to audit than rushed
- ✅ **DA-01 Complete**: Structured audit outcome overview (~30 min)
	- **Collaboration process**: Discussed 8 potential output categories with user, reached consensus on priorities
	- **Decisions made**:
		- ✅ Accept (created): Quick Reference Card (1), Weekly Review Template (5)
		- ⏸️ Sanity check: Project Integration Checklist (3) - deferred to Phase 3 after CC-02
		- 🔄 Defer to Iris tracker: Portfolio evidence automation script (4), Troubleshooting guide (8)
		- ❌ Reject: Workflow Decision Tree (2), Command Comparison Matrix (6), Migration Guide (7)
	- **Outputs created**:
		1. **Quick Reference Card** (`~/.claude/docs/cli-tools-quick-reference.md`):
			- Single-page cheat sheet for daily workflows
			- Tables for all tool categories (find, search, TODO, git, stats, deps, testing, scaffolding)
			- Common patterns and keyboard shortcuts
			- Troubleshooting quick fixes
		2. **Weekly Review Template** (`~/.claude/docs/weekly-portfolio-review-template.md`):
			- Structured template for AM2 portfolio documentation
			- Sections: dev activity, technical metrics, KSB mapping, learnings, evidence generated
			- Pre-populated with all KSBs (K1-K10, S1-S20, B1-B5)
			- Includes command reference for automated data gathering
		3. **Deferred tasks added to Iris tracker** (`~/.claude/docs/iris-development-tracker.md`):
			- DF-01: Portfolio evidence automation script
			- DF-02: Troubleshooting guide (populate as issues arise)
	- **Audit document updates**:
		- Phase 2 status: 100% complete (was 87.5%)
		- Phase 3 updated: Added PI-01 (Project Integration Checklist) task 16
		- Phase 4 task numbers shifted (WP-04 now task 19)
		- Phase 3 time estimate: 6-8 hours (was 5-7)
		- Phase 2 summary added to audit document
		- File locations reference updated with new structure
- **Key learnings**:
	- Collaborative filtering prevents documentation for documentation's sake
	- Quick reference card addresses "while habits form" problem
	- Weekly template structures portfolio narrative building
	- Project integration checklist best done AFTER onboarding workflow (CC-02) exists
	- Deferred automation prevents premature optimization
- **Next**: Phase 3 - Iris Preparation begins

---

## Phase Summaries
### Phase 1 Complete Summary
- **Completed Tasks**: ZD-01, SH-01, GC-01
- **Time**: ~3 hours
- **Outputs**
	- 3 new documentation files (terminal, git config, branch conventions)
	- 1 new guide (iTerm2 setup)
	- 39 shell aliases (git, npm, bun, deno, workflow, system)
	- 8 git aliases (semantic operations, workflow, cleanup)
	- Updated configs: `.zshrc`, `.gitconfig`, `.gitignore_global`, Zed `settings.json`
- **Next**: Phase 2 - Infrastructure & Learning

### Phase 2 Complete Summary
- **Completed Tasks**: CC-11, CC-06, CC-09, CC-05, WP-01, WP-02, RS-03, DA-01
- **Time**: ~8-9 hours
- **Key Outputs**:
	- **Documentation**: 8 new docs (CLI tools guide, quick reference, weekly template, debugging workflow, doc workflow, MCP comparison)
	- **Skills**: 2 new skills (styling, debugging) with auto-invoke patterns
	- **Hooks**: 3 git hooks (post-commit-evidence, post-commit-docs, pre-push-tests)
	- **CLI Tools**: 13 installed (fzf, ripgrep, bat, fd, jq, tokei, axe-cli, svu, vacuum, pake, degit, go)
	- **Shell Functions**: 50+ aliases/functions for daily workflows
	- **MCP Servers**: 4 configured for Claude Code CLI (context7, GitHub, sequential-thinking, filesystem)
- **Major Learnings**:
	- Skills system more powerful than slash commands for conditional invocation
	- Git hooks enable portfolio evidence automation
	- CLI tools work best in combinations (fzf+fd+ripgrep+bat)
	- svu perfect fit for conventional commits workflow
	- Documentation workflow benefits from templates + hooks + slash commands
- **Deferred to Iris tracker**: Portfolio evidence automation script (DF-01), troubleshooting guide (DF-02)
- **New Phase 3 Task**: PI-01 (Project integration checklist) depends on CC-02
- **Next**: Phase 3 - Iris Preparation (6-8 hours)

---

## Reference: Key File Locations
```
~/.claude/
├── CLAUDE.md                  # Global config
├── commands/                  # Slash commands
│   ├── analyse/
│   ├── doc/                   # NEW: Documentation commands
│   ├── git/
│   ├── plan/
│   ├── style/
│   ├── task/
│   └── update/
├── agents/
│   └── implementation-planner.md
├── output-styles/
│   └── quality-dev-mentor.md
├── skills/                    # NEW: Auto-invoke skills
│   ├── styling/
│   └── debugging/
├── doc-templates/             # NEW: Documentation templates
│   ├── adr.md
│   ├── work-record.md
│   └── retrospective.md
├── docs/                      # NEW: Reference documentation
│   ├── cli-tools-usage-guide.md
│   ├── cli-tools-quick-reference.md
│   ├── cli-tools-zshrc-additions.sh
│   └── weekly-portfolio-review-template.md
├── dev-environment-audit.md   # This document
├── iris-development-tracker.md  # Iris-specific development tasks
└── command-template.md        # Template for new commands

~/.config/zed/
├── settings.json              # Main Zed config
├── keymap.json
├── prompts/
├── snippets/
└── themes/

~/Code/
├── ilr-file-creator/          # Current Electron app (to be replaced by Iris)
├── llm-council/               # Python/TS MCP integration
├── rhea/                      # Svelte/LangChain curriculum generator
└── [other projects]
```
