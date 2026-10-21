# Claude Code Customisation Guide

A practical reference for developers who know how to code but are new to customising Claude Code. Features are ordered by dependency — each section builds on the last.

---

## 1. Configuration Scopes

Every customisation lives at one of four levels. The more specific level wins when two conflict.

| Scope | File location | Shared? | Use for |
|---|---|---|---|
| **Managed** | System-level (IT-deployed) | All users on machine | Organisation policies |
| **User** | `~/.claude/settings.json` | No — just you | Personal preferences across all projects |
| **Project** | `.claude/settings.json` | Yes — committed to git | Team-wide settings |
| **Local** | `.claude/settings.local.json` | No — gitignored | Your personal overrides for this project |

**Precedence:** Managed > Local > Project > User.

The same structure applies to most other features (CLAUDE.md files, subagents, skills): a `~/.claude/` version is personal, a `.claude/` version is shared with the team.

> **Docs:** https://code.claude.com/docs/en/settings

---

## 2. CLAUDE.md Files

A `CLAUDE.md` file is a plain markdown file Claude reads at the start of every session. Use it to give Claude persistent context: coding standards, architecture notes, build commands, naming conventions.

Claude treats CLAUDE.md as instructions, not enforced rules. Specific, concrete instructions work better than vague ones.

**Where to put it:**

| Location | Loaded when |
|---|---|
| `~/.claude/CLAUDE.md` | Every project |
| `CLAUDE.md` or `.claude/CLAUDE.md` | This project only |
| Subdirectory `CLAUDE.md` | When Claude reads files in that directory |

**Tip:** Run `/init` inside Claude Code and it will generate a starter CLAUDE.md by analysing your codebase.

### Effective example

```markdown
# Project: payments-api

## Build & test
- Run tests: `npm test`
- Lint: `npm run lint`

## Conventions
- Use 2-space indentation
- All API handlers live in `src/handlers/`
- Validate all inputs with Zod at the boundary
- Return errors as `{ error: string, code: string }`
```

**Why it works:** Commands are exact and runnable. Rules are verifiable. Claude can check "did I follow this?" for each line.

### Ineffective example

```markdown
# Project notes

Make sure the code is well organised and follows best practices.
Tests are important. Keep things clean and consistent.
```

**Why it's weak:** None of these instructions are testable. "Well organised" means different things to different people. Claude cannot reliably follow vague guidance — it will make its own interpretation every time.

> **Docs:** https://code.claude.com/docs/en/memory

---

## 3. Rules

Rules are an extension of CLAUDE.md for larger projects. Place markdown files in `.claude/rules/` — each file covers one topic. Rules without path scoping load at session start just like CLAUDE.md. Rules *with* path scoping only load when Claude is working with matching files, saving context.

**Directory structure:**

```
.claude/
├── CLAUDE.md
└── rules/
    ├── testing.md          # loads every session
    ├── api-design.md       # loads every session
    └── frontend.md         # can be path-scoped
```

**Path-scoped rule** — only loads when Claude touches matching files:

### Effective example

```markdown
---
paths:
  - "src/api/**/*.ts"
---

# API Rules

- All endpoints must validate inputs with Zod
- Return `{ data, error }` shape consistently
- Include JSDoc on exported handler functions
```

**Why it works:** The path scope means these rules only appear in context when relevant — they don't clutter sessions working on unrelated files.

### Ineffective example

```markdown
---
paths:
  - "src/api/**/*.ts"
---

When writing API code, try to follow good API design principles
and make sure things work correctly.
```

**Why it's weak:** The `paths` scope is correct — but the content is useless. "Good API design principles" is not actionable. The path scope does not compensate for vague instructions.

> **Docs:** https://code.claude.com/docs/en/memory#organize-rules-with-clauderules

---

## 4. Skills

A skill is a reusable instruction set Claude can invoke. Create a directory with a `SKILL.md` file inside it. The directory name becomes the `/slash-command`. Claude can also trigger skills automatically if the description matches what you're asking.

**Where to store:**

| Location | Scope |
|---|---|
| `~/.claude/skills/<name>/SKILL.md` | All your projects |
| `.claude/skills/<name>/SKILL.md` | This project only |

**Frontmatter fields** (all optional except `description` is strongly recommended):

| Field | Purpose |
|---|---|
| `name` | Slash command name. Defaults to directory name |
| `description` | When Claude should load this skill. Front-load the key use case |
| `disable-model-invocation` | Set `true` to prevent Claude invoking it automatically — you must type `/name` |
| `user-invocable` | Set `false` to hide from the `/` menu; Claude-only background knowledge |
| `allowed-tools` | Restrict which tools Claude can use while this skill is active |
| `model` | Which model to use when this skill runs |
| `argument-hint` | Autocomplete hint, e.g. `[issue-number]` |
| `context` | Set `fork` to run in an isolated subagent |

**Two types of skill:**

- **Command skill** (`disable-model-invocation: true`) — you trigger it manually with `/name`. Good for actions with side effects like `/deploy` or `/commit`.
- **Knowledge skill** (`user-invocable: false`) — Claude loads it automatically when relevant. Good for reference material or guidelines Claude should apply in context.

### Effective example — command skill

```markdown
---
name: create-component
description: Scaffold a new React component with tests
disable-model-invocation: true
argument-hint: <ComponentName>
allowed-tools: Write, Read
---

Create a new React component named $ARGUMENTS.

1. Create `src/components/$ARGUMENTS/$ARGUMENTS.tsx`
2. Create `src/components/$ARGUMENTS/$ARGUMENTS.test.tsx` with basic render test
3. Export the component from `src/components/index.ts`

Follow the existing component patterns in `src/components/`.
```

**Why it works:** `disable-model-invocation: true` means Claude won't randomly scaffold components mid-conversation. `$ARGUMENTS` is used correctly. The steps are specific and the instruction to follow existing patterns is verifiable.

### Ineffective example — command skill

```markdown
---
name: create-component
description: Makes components
---

Create a component for the user. Make it look nice and work properly.
```

**Why it's weak:** The description is too vague — Claude might trigger this for any UI question. Without `disable-model-invocation: true`, Claude could scaffold a component when you only asked a question. The body gives no actionable steps.

> **Docs:** https://code.claude.com/docs/en/skills

---

## 5. Subagents

Subagents are specialised AI assistants that run in their own context window. Claude delegates tasks to them automatically based on their description. Each subagent has its own system prompt, tool access, and optionally its own model.

Built-in subagents include `Explore` (read-only, fast, for codebase search), `Plan` (used during plan mode), and `general-purpose`.

**Where to store:**

| Location | Scope |
|---|---|
| `~/.claude/agents/<name>.md` | All your projects |
| `.claude/agents/<name>.md` | This project only |

**Key frontmatter fields:**

| Field | Purpose |
|---|---|
| `name` | Identifier (lowercase, hyphens) |
| `description` | When Claude should delegate to this agent |
| `tools` | Allowlist of tools this agent can use |
| `disallowedTools` | Denylist (applied before `tools`) |
| `model` | `sonnet`, `opus`, `haiku`, or `inherit` |
| `maxTurns` | Maximum agentic turns before it stops |

The markdown body is the agent's system prompt. It receives only that — not the full Claude Code system prompt.

### Effective example

```markdown
---
name: security-reviewer
description: Reviews code changes for security vulnerabilities. Use when reviewing authentication, authorization, input handling, database queries, or any code that handles user data.
tools: Read, Grep, Glob
model: sonnet
---

You are a security code reviewer. When invoked:

1. Read the changed files
2. Check for: SQL injection, XSS, insecure direct object references, missing auth checks, secrets in code
3. Report each issue with: file, line number, severity (high/medium/low), and a concrete fix

Do not suggest refactors unrelated to security. Stay focused.
```

**Why it works:** The description is specific enough that Claude will delegate security questions here without triggering on unrelated work. Tool access is read-only — it cannot accidentally modify files. The system prompt has a clear, bounded task.

### Ineffective example

```markdown
---
name: helper
description: Helps with coding tasks
tools: Read, Write, Bash, Edit, Grep, Glob
model: opus
---

You are a helpful coding assistant. Help the user with whatever they need.
```

**Why it's weak:** The description matches everything — Claude will delegate almost any task here. Opus is expensive; using it for generic help wastes money. Giving all tools including Write and Bash to a vaguely-scoped agent is a security risk. The system prompt adds no specialised value.

> **Docs:** https://code.claude.com/docs/en/sub-agents

---

## 6. Hooks

Hooks are shell commands that run automatically at lifecycle events. Configure them in `settings.json` under the `hooks` key. They let you enforce rules, auto-format files, log activity, or block unsafe operations.

**Hook events (most common):**

| Event | When |
|---|---|
| `SessionStart` | Session begins |
| `PreToolUse` | Before Claude uses a tool — can block it |
| `PostToolUse` | After a tool runs |
| `Stop` | When Claude finishes responding |
| `UserPromptSubmit` | When you submit a message — can block it |

**Hook configuration shape:**

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "ToolNameRegex",
        "hooks": [
          {
            "type": "command",
            "command": "path/to/script.sh"
          }
        ]
      }
    ]
  }
}
```

The hook script receives JSON on stdin describing what Claude is about to do. To block an action, exit with code `2` and print a reason to stderr.

### Effective example — auto-lint after edits

In `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/lint.sh"
          }
        ]
      }
    ]
  }
}
```

`.claude/hooks/lint.sh`:

```bash
#!/bin/bash
FILE=$(cat | jq -r '.tool_input.file_path')

if [[ "$FILE" == *.js || "$FILE" == *.ts ]]; then
  npx eslint --fix "$FILE" 2>/dev/null
fi

exit 0
```

**Why it works:** Matcher is specific (`Write|Edit` only). The script parses stdin for the file path instead of guessing. It only acts on JS/TS files. Exit 0 means non-blocking — a lint error won't stop Claude.

### Ineffective example

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Claude is doing something' >> /tmp/log.txt"
          }
        ]
      }
    ]
  }
}
```

**Why it's weak:** Empty matcher fires on *every* tool call including Read, Grep, and Glob — thousands of times per session. Writing to `/tmp/log.txt` with no timestamp or context produces useless logs. This will slow every Claude action down by the time it takes to spawn a shell.

> **Docs:** https://code.claude.com/docs/en/hooks

---

## 7. MCP Servers

MCP (Model Context Protocol) servers give Claude access to external tools: databases, APIs, issue trackers, browsers. You don't need to understand the protocol to use them — just add a server with the CLI.

**Three transport types:**

```bash
# Remote HTTP (recommended for cloud services)
claude mcp add --transport http <name> <url>

# Local stdio (runs as a process on your machine)
claude mcp add --transport stdio <name> -- <command> [args...]

# Remote SSE (deprecated — prefer HTTP)
claude mcp add --transport sse <name> <url>
```

**Scope flags:**

| Flag | Where stored | Shared? |
|---|---|---|
| `--scope local` (default) | `~/.claude.json`, per-project | No |
| `--scope project` | `.mcp.json` in project root | Yes — commit to git |
| `--scope user` | `~/.claude.json` | No — all your projects |

**Useful management commands:**

```bash
claude mcp list          # see all configured servers
claude mcp get <name>    # details for one server
claude mcp remove <name> # remove a server
```

Inside Claude Code, run `/mcp` to see server status and authenticate with OAuth.

### Effective example — adding GitHub

```bash
# Add once — stored in your user scope
claude mcp add --transport http github --scope user https://api.githubcopilot.com/mcp/
```

Then inside Claude Code:

```
/mcp
```

Select GitHub and authenticate. Then ask:

```
Review open PRs and summarise what's waiting for my review
```

**Why it works:** User scope means it's available in all projects without reconfiguring. HTTP transport is the right choice for a cloud service.

### Ineffective example

Manually editing `~/.claude.json` to add:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["/Users/yourname/projects/server.js"]
    }
  }
}
```

**Why it's weak:** `~/.claude.json` is managed by Claude Code and may be overwritten. The path is absolute and machine-specific — won't work on another machine or in CI. Use `claude mcp add` instead; it handles the correct file format and location.

> **Docs:** https://code.claude.com/docs/en/mcp

---

## 8. Plugins

A plugin packages skills, subagents, hooks, and MCP servers together so they can be shared, versioned, and installed across projects. The key difference from standalone configuration: plugin skills are namespaced (e.g. `/my-plugin:deploy` instead of `/deploy`) to prevent conflicts.

**Plugin structure:**

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json       ← manifest (only file in .claude-plugin/)
├── skills/
│   └── deploy/
│       └── SKILL.md
├── agents/
│   └── reviewer.md
└── hooks/
    └── hooks.json
```

**Minimal `plugin.json`:**

```json
{
  "name": "my-plugin",
  "description": "What this plugin does",
  "version": "1.0.0",
  "author": { "name": "Your Name" }
}
```

**Test locally:**

```bash
claude --plugin-dir ./my-plugin
```

**Reload without restarting:**

```
/reload-plugins
```

When ready to share: push to a GitHub repository and distribute the URL. Teams install via `/plugin install`.

### Effective example — plugin.json

```json
{
  "name": "acme-standards",
  "description": "Acme Corp coding standards — linting hooks, review agents, commit conventions",
  "version": "1.2.0",
  "author": {
    "name": "Acme Platform Team"
  },
  "homepage": "https://github.com/acme/claude-standards"
}
```

**Why it works:** The description makes the plugin's purpose clear. Version is semver. Homepage allows teammates to find the source.

### Ineffective example — plugin.json

```json
{
  "name": "MyPlugin",
  "description": "my plugin",
  "version": "1"
}
```

**Why it's weak:** `name` uses PascalCase — plugin names must be lowercase with hyphens; this will cause skill namespacing issues. Version `"1"` is not semver. The description is useless for anyone deciding whether to install it. These are technically valid JSON but will cause behavioural problems.

> **Docs:** https://code.claude.com/docs/en/plugins

---

## 9. Worktrees (brief)

Git worktrees let you run multiple Claude sessions simultaneously, each in its own isolated copy of the repository, on separate branches, without interference.

```bash
# Start Claude in an isolated worktree
claude --worktree feature-name
```

This creates `.claude/worktrees/feature-name/` on a new branch called `worktree-feature-name`. When you exit, Claude cleans up automatically if no changes were made.

You can have Claude use worktrees for subagents too — add `isolation: worktree` to an agent's frontmatter.

This is a more advanced topic. Come back to it once you're comfortable with skills and subagents.

> **Docs:** https://code.claude.com/docs/en/common-workflows#run-parallel-claude-code-sessions-with-git-worktrees

---

## Putting It Together

A typical progression:

1. Start with `CLAUDE.md` — get Claude to understand your project
2. Add `.claude/rules/` as your instructions grow
3. Create skills for repetitive tasks you invoke manually
4. Add knowledge skills for domain context Claude should apply automatically
5. Create subagents for specialised reviewers or researchers
6. Wire hooks to enforce standards (linting, commit format)
7. Add MCP servers for your tools (GitHub, Jira, databases)
8. Package everything into a plugin when you want to share with your team

---

## Reference Links

| Feature | Official docs |
|---|---|
| Settings & scopes | https://code.claude.com/docs/en/settings |
| CLAUDE.md & rules | https://code.claude.com/docs/en/memory |
| Skills | https://code.claude.com/docs/en/skills |
| Subagents | https://code.claude.com/docs/en/sub-agents |
| Hooks | https://code.claude.com/docs/en/hooks |
| MCP servers | https://code.claude.com/docs/en/mcp |
| Plugins | https://code.claude.com/docs/en/plugins |
| Worktrees | https://code.claude.com/docs/en/common-workflows |
