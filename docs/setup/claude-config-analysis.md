# Claude Code Configuration Analysis
> **Created**: 2026-01-06  
> **Purpose**: Complete audit of `~/.claude/` directory structure and contents 
> **Context**: CC-11 task - Foundation for Phase 2 configuration work

---

## Overview
**Location**: `/Users/jasonwarren/.claude/`

This directory contains all user-level Claude Code configuration, including slash commands, agents, output styles, plugins, and project-specific settings.

---

## Directory Structure Summary
```
~/.claude/
├── CLAUDE.md                          # Global configuration (recently updated)
├── settings.json                      # User settings
├── history.jsonl                      # Command history
├── stats-cache.json                   # Usage statistics
├── commands/                          # Slash commands (13 files)
├── agents/                            # Custom agents (1 file)
├── output-styles/                     # Output formatting (1 file)
├── plugins/                           # Plugin marketplace & configs
├── projects/                          # Project-specific configs (5 projects)
├── plans/                             # Saved plan mode files (2 files)
├── debug/                             # Debug information
├── downloads/                         # Downloaded files
├── file-history/                      # File version history
├── ide/                               # IDE integration
├── scratch/                           # Temporary workspace
├── session-env/                       # Session environment variables
├── shell-snapshots/                   # Shell state captures
├── statsig/                           # Analytics/telemetry
├── telemetry/                         # Usage telemetry
├── todos/                             # Task tracking
└── [documentation files]              # User-created docs (audit, git, terminal, etc.)
```

---

## Slash Commands
**Location**: `~/.claude/commands/`

### Active Commands (13 total)
#### Analyse Category (3)
| Command | Path | Purpose |
|---------|------|---------|
| `/analyse/codebase` | `analyse/codebase.md` | High-level codebase overview |
| `/analyse/critique` | `analyse/critique.md` | Code critique and review |
| `/analyse/roadmap`  | `analyse/roadmap.md`  | Compare roadmaps to codebase state |

#### Git Category (2)
| Command | Path | Purpose |
|---------|------|---------|
| `/git/commit`       | `git/commit.md`       | Conventional commits (cleaned, no pig notes) |
| `/git/pull-request` | `git/pull-request.md` | PR creation (cleaned, no pig notes) |

#### Style Category (2)
| Command | Path | Purpose |
|---------|------|---------|
| `/style/layout/fix`  | `style/layout/fix.md`  | Layout fixes |
| `/style/style/unify` | `style/style/unify.md` | Style unification |

**Note**: Style commands earmarked for replacement with Skills system (CC-09)

#### Task Category (3)
| Command | Path | Purpose |
|---------|------|---------|
| `/task/execute/minima`   | `task/execute/minima.md`   | Minimalist task execution |
| `/task/suggest/general`  | `task/suggest/general.md`  | Suggest next task from codebase |
| `/task/suggest/targeted` | `task/suggest/targeted.md` | Suggest task with focus area |

#### Update Category (3)
| Command | Path | Purpose |
|---------|------|---------|
| `/update/docs/recent-work` | `update/docs/recent-work.md` | Update docs from recent commits |
| `/update/roadmaps/all`     | `update/roadmaps/all.md`     | Update all active roadmaps (generic) |
| `/update/roadmaps/single`  | `update/roadmaps/single.md`  | Update specific roadmap by ID |

#### Empty Categories
- **Plan** (`plan/`) - Empty directory (plan mode now native)

### Command Organization

Commands follow hierarchical structure:
```
<category>/<subcategory?>/<action>.md
```

Examples:
- Simple: `git/commit.md`
- Nested: `task/execute/minima.md`
- Deep: `style/layout/fix.md`

---

## Agents

**Location**: `~/.claude/agents/`

### Active Agents (1 total)
| Agent | File | Purpose |
|-------|------|---------|
| Implementation Planner | `implementation-planner.md` | Strategic implementation planning |

**Gaps**:
- No testing-focused agent
- No debugging agent
- No documentation agent
- No code review agent (available in plugins but not installed)

---

## Output Styles

**Location**: `~/.claude/output-styles/`

### Active Styles (1 total)
| Style | File | Purpose |
|-------|------|---------|
| Quality Dev Mentor | `quality-dev-mentor.md` | Mentor-style explanatory output |

**Characteristics**:
- Technical precision with personality
- Avoids corporate handbook tone
- Direct and neurodivergent-friendly
- British English

---

## Plugins System
**Location**: `~/.claude/plugins/`

### Installation Status
**Currently Installed**: **NONE** (0 plugins)

From `installed_plugins.json`:
```json
{
  "version": 2,
  "plugins": {}
}
```

### Available Plugins
#### External MCP Servers (13 available)
Located in: `marketplaces/claude-plugins-official/external_plugins/`

| Plugin            | Type | Auth Required | Use Case              |
| ----------------- | ---- | ------------- | --------------------- |
| **asana**         | SSE  | None          | Project management    |
| **context7**      | npx  | API key       | Library documentation |
| **firebase**      | ?    | Yes           | Firebase integration  |
| **github**        | HTTP | PAT           | GitHub operations     |
| **gitlab**        | ?    | Yes           | GitLab operations     |
| **greptile**      | ?    | API key       | Code search           |
| **laravel-boost** | ?    | ?             | Laravel development   |
| **linear**        | ?    | API key       | Issue tracking        |
| **playwright**    | ?    | None          | Browser automation    |
| **serena**        | ?    | ?             | Unknown               |
| **slack**         | ?    | Token         | Slack integration     |
| **stripe**        | ?    | API key       | Payment integration   |
| **supabase**      | ?    | Key/URL       | Backend as service    |

**Note**: Each has `.mcp.json` config file defining connection method

#### Official Plugins (24 available)
Located in: `marketplaces/claude-plugins-official/plugins/`

**Development Tools**:
- `agent-sdk-dev` - Agent SDK development
- `code-review` - Code review workflows
- `commit-commands` - Git commit helpers
- `feature-dev` - Feature development workflows
- `frontend-design` - Frontend design system
- `plugin-dev` - Plugin development tools
- `pr-review-toolkit` - PR review tools

**Language Support (LSP)**:
- `clangd-lsp` - C/C++
- `csharp-lsp` - C#
- `gopls-lsp` - Go
- `jdtls-lsp` - Java
- `lua-lsp` - Lua
- `php-lsp` - PHP
- `pyright-lsp` - Python
- `rust-analyzer-lsp` - Rust
- `swift-lsp` - Swift
- `typescript-lsp` - TypeScript

**Utilities**:
- `explanatory-output-style` - Output style plugin
- `hookify` - Hook management system
- `learning-output-style` - Learning-focused output
- `ralph-wiggum` - Unknown (needs investigation)
- `security-guidance` - Security best practices

### Plugin Structure
Each plugin contains:
```
plugin-name/
├── .claude-plugin/
│   └── plugin.json        # Plugin metadata
├── .mcp.json             # MCP server config (if applicable)
├── README.md
├── commands/             # Slash commands (optional)
├── agents/               # Custom agents (optional)
├── skills/               # Skills (optional)
└── hooks/                # Lifecycle hooks (optional)
```

Example: **stripe** plugin has:
- `.mcp.json` - MCP server connection
- `commands/` - explain-error.md, test-cards.md
- `skills/stripe-best-practices/` - Stripe-specific guidance

---

## Project-Specific Configurations
**Location**: `~/.claude/projects/`

### Tracked Projects (5)
Projects identified by normalized path:

| Project          | Normalized Path                            | Status |
| ---------------- | ------------------------------------------ | ------ |
| ILR File Creator | `-Users-jasonwarren-Code-ilr-file-creator` | Active |
| LLM Council      | `-Users-jasonwarren-Code-llm-council`      | Active |
| Nottingmas       | `-Users-jasonwarren-Code-nottingmas`       | Active |
| Psyche           | `-Users-jasonwarren-Code-psyche`           | Active |
| Rhea             | `-Users-jasonwarren-code-rhea`             | Active |

### Project Contents
Each project directory contains:
- **Session histories** (`.jsonl` files) - Conversation logs per session
- **Agent histories** (`agent-*.jsonl`) - Agent-specific conversations

Example from `rhea`:
```
-Users-jasonwarren-code-rhea/
├── 08462c35-b9c2-469a-86a9-24baae269f01.jsonl
├── 51e09854-8ee2-4792-9d95-232367c74888.jsonl
├── 7ee7fbf8-da77-478b-8cce-7f9de131aa50.jsonl
├── a0aecf46-a6b9-4762-99fd-c56b9e0f0f87.jsonl
├── a7c4745e-e240-4fdf-ae40-f32ca7f4a3e1.jsonl
├── agent-a0fea63.jsonl
├── agent-a62aad6.jsonl
├── agent-a6742fb.jsonl
└── agent-af9ab8f.jsonl
```

**Note**: No project-level CLAUDE.md or .mcp.json files exist yet (tracked in CC-02)

---

## Plan Mode
**Location**: `~/.claude/plans/`

### Saved Plans (2)
| Plan | File | Status |
|------|------|--------|
| Unknown 1 | `imperative-gliding-hare.md` | Saved |
| Unknown 2 | `zazzy-plotting-seahorse.md` | Saved |

**Note**: Plan filenames are randomly generated (adjective-verb-animal pattern)

---

## Configuration Files
### Global Config
**File**: `~/.claude/CLAUDE.md`

**Contents** (recently updated):
- Developer profile (skills, preferences, weaknesses)
- Communication preferences (direct, British, neurodivergent-friendly)
- Code style guidelines
- Documentation standards
- Security guidelines

**Tone**: Technical precision with personality, not corporate

### Settings
**File**: `~/.claude/settings.json`

**Key settings**:
```json
{
  "permissions": {
    "allow": [
      "WebSearch",
      "Bash(npm search:*)",
      "Bash(uv run:*)",
      "Bash(uv add:*)",
      "Bash(cat:*)"
    ],
    "defaultMode": "default"
  },
  "statusLine": {
    "type": "command",
    "command": "[complex git-aware zsh prompt]"
  },
  "alwaysThinkingEnabled": true
}
```

**Notable**:
- Web search enabled
- Selective bash permissions (npm, uv, cat)
- Custom status line with git integration
- Extended thinking always enabled

---

## Supporting Directories
### Debug
**Location**: `~/.claude/debug/`
**Purpose**: Debug logs and diagnostics

### Downloads
**Location**: `~/.claude/downloads/`
**Purpose**: Files downloaded during sessions

### File History
**Location**: `~/.claude/file-history/`
**Purpose**: Version control for edited files

### Scratch
**Location**: `~/.claude/scratch/`
**Purpose**: Temporary workspace for intermediate files

### Session Environment
**Location**: `~/.claude/session-env/`
**Purpose**: Environment variables per session

### Shell Snapshots
**Location**: `~/.claude/shell-snapshots/`
**Purpose**: Shell state captures for restore

### Telemetry
**Location**: `~/.claude/statsig/`, `~/.claude/telemetry/`
**Purpose**: Usage analytics and telemetry data

### Todos
**Location**: `~/.claude/todos/`
**Purpose**: Task tracking and reminders

---

## User Documentation
**Custom documentation files** (created during this audit):

| File                                 | Purpose                      |
| ------------------------------------ | ---------------------------- |
| `dev-environment-audit.md`           | This audit tracking document |
| `git-branch-naming-conventions.md`   | Branch naming standards      |
| `git-configuration-documentation.md` | Git setup documentation      |
| `terminal-setup-documentation.md`    | Terminal/shell configuration |
| `iterm2-setup-guide.md`              | iTerm2 configuration guide   |
| `iris-development-tracker.md`        | Iris project tracking        |
| `command-guide.md`                   | Command usage guide          |
| `command-template.md`                | Template for new commands    |

---

## Key Findings
### Strengths
1. **Organized command structure** - Clear hierarchical organization
2. **Clean slate for plugins** - No conflicting installed plugins
3. **Project tracking** - Automatic session history per project
4. **Comprehensive global config** - CLAUDE.md well-defined
5. **Custom documentation** - Building knowledge base

### Gaps
1. **No MCP servers active** - Despite available integrations (context7, GitHub)
2. **No plugins installed** - Not leveraging official plugins
3. **Limited agents** - Only 1 agent (implementation-planner)
4. **No hooks configured** - Missing automation opportunities
5. **No skills** - Skills system unexplored
6. **No project-level configs** - Missing per-project CLAUDE.md and .mcp.json
7. **Style commands outdated** - Should migrate to skills

### High-Impact Opportunities
**Immediate** (Phase 2):
1. Enable context7 and GitHub MCP servers (CC-06)
2. Create styling skill to replace style commands (CC-09)
3. Configure hooks for common workflows (CC-05)
4. Install useful official plugins (feature-dev, pr-review-toolkit)

**Strategic** (Phase 3):
1. Project onboarding workflow with per-project configs (CC-02)
2. Testing workflow commands and agents (CC-04)
3. Documentation workflow strategy (WP-01)
4. Debugging workflow patterns (WP-02)

---

## Comparison with Zed
### Zed Has (Claude Code Doesn't)
- Active MCP servers: context7, GitHub, sequential-thinking
- Configured in Zed settings.json

### Claude Code Has (Zed Doesn't)
- Slash commands (13 custom workflows)
- Custom agents (implementation-planner)
- Custom output styles (quality-dev-mentor)
- Project-specific session histories
- Plan mode with saved plans

### Recommendation
**Don't mirror Zed** - They serve different purposes:
- **Zed**: IDE integration, LSP, real-time assistance
- **Claude Code**: CLI workflows, automation, project management

Focus Claude Code on CLI-specific needs (MCP for CLI workflows, not IDE features)

---

## Next Steps
Based on this analysis, Phase 2 priorities are clear:

1. **CC-06**: Enable MCP servers for CLI (context7, GitHub)
2. **CC-09**: Create skills (starting with styling skill)
3. **CC-05**: Configure hooks for automation
4. **Plugin evaluation**: Assess which official plugins would be useful

This analysis informs all subsequent configuration work.

---

## Maintenance Notes
### Regular Review
- **Monthly**: Check for new available plugins
- **Per project**: Consider project-specific configs
- **After major updates**: Re-audit plugin marketplace

### Cleanup
- **Session histories**: Old project sessions can be archived
- **Plans**: Review and delete obsolete plans
- **Debug logs**: Periodic cleanup

### Documentation
- Keep user docs in `~/.claude/` for easy reference
- Version control recommended for critical configs
- Consider backing up to Dropbox/Git
