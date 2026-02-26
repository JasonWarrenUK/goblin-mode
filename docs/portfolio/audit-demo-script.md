# Development Environment Demo Script

**Duration:** 15 minutes  
**Audience:** Fellow apprentice developers  
**Focus:** Implementation details and decision-making process  
**Format:** Live screen cast demonstration

---

## Setup Before Demo (Do This First)

```bash
# Have these windows ready:
# 1. iTerm2 with zsh
# 2. Zed editor
# 3. LazyGit (in separate terminal)
# 4. Browser with ~/.claude/ directory open

# Navigate to Rhea for demos
cd ~/Code/rhea

# Source shell functions if needed
source ~/.zshrc
```

---

## Demo Flow (15 minutes)

### Part 1: The Problem (1 min)

**Script:**
"Right, so while waiting for AM1 confirmation, I spent about 12 hours systematically auditing my dev environment. Not just installing random tools - actually figuring out what workflow gaps I had and how to solve them properly."

**Show:** The audit document structure
```bash
# Show the tracking document
bat ~/.claude/dev-environment-audit.md | head -50
```

**Key point:** "This is the tracking doc. Everything we did is documented with reasoning, not just 'installed X because someone on Twitter said so'."

---

### Part 2: Claude Code Features (5 min)

**2.1: Skills vs Commands (2 min)**

**Script:**
"First discovery: Claude Code has this 'skills' system that nobody talks about. It's like slash commands but automatic. Watch this."

**Demo:**
1. Show the debugging skill:
```bash
bat ~/.claude/skills/debugging/SKILL.md | head -30
```

2. Trigger it naturally in Zed:
```
# In Zed, type:
"I've got a failing test in course-generator.test.ts - help me debug it"

# Claude auto-invokes the debugging skill
# Show the five-step framework appearing
```

**Key point:** "See that? I didn't type `/debug` or anything. Keywords like 'failing' or 'bug' auto-invoke this. The skill has a five-step framework: Reproduce → Isolate → Diagnose → Fix → Verify. Works for every bug type."

**Show the trigger pattern:**
```yaml
# From debugging/SKILL.md
activate_on:
  - "bug"
  - "error"
  - "failing"
  - "broken"
  - "doesn't work"
```

**Decision process:**
"Why skills instead of commands? Commands you have to remember to type. Skills activate when you need them. Created two: debugging (just showed) and styling. Styling triggers on 'layout', 'design', 'css' - gives me project-specific Tailwind conventions automatically."

---

**2.2: Git Hooks (1.5 min)**

**Script:**
"Second discovery: git hooks. These run automatically after commits. I made three."

**Demo:**
```bash
# Show the hooks
ls -la ~/Code/rhea/.git/hooks/
bat ~/Code/rhea/.git/hooks/post-commit-evidence
```

**Key point:** "This one extracts portfolio evidence from commit messages automatically. Every commit with 'feat:' or 'fix:' gets analyzed for KSB mapping."

**Show it working:**
```bash
# Make a dummy commit
echo "# test" >> README.md
git add README.md
git commit -m "feat: add automated evidence extraction

Implements S4 (build/deploy) by creating git hooks for CI/CD workflow.
Uses conventional commits for semantic versioning."

# Show the output - hook runs automatically
# Evidence gets saved to ~/portfolio-evidence/
```

**Decision process:**
"Why hooks? Because I kept forgetting to document evidence. Now it's automatic. Other hooks: one reminds me when docs need updating, one checks tests ran before pushing."

---

**2.3: MCP Servers (1.5 min)**

**Script:**
"Third thing: MCP servers extend Claude. I added four to the CLI."

**Demo:**
```bash
# Show the config
bat ~/.config/mcp/config.json | jq '.mcpServers | keys'

# Show context7 in action (if time)
# In Zed:
"Show me the latest SvelteKit documentation for form actions"
# Claude uses context7 MCP to fetch live docs
```

**Key point:** "context7 gives live library docs. GitHub MCP lets me search issues, create PRs. Filesystem MCP lets Claude read my actual codebase structure. These were in Zed but not CLI - now they're in both."

---

### Part 3: CLI Tool Combinations (4 min)

**Script:**
"Right, the shell tools. Installed 13, but the power is in combinations."

**3.1: Interactive Search (1.5 min)**

**Demo:**
```bash
# Show the workflow
rgi "useState"

# This runs:
# 1. ripgrep searches for pattern
# 2. fzf makes it interactive
# 3. bat previews the file with syntax highlighting
# As you arrow through results, preview updates live

# Press Enter to select, shows the file
```

**Key point:** "Three tools working together. ripgrep is grep but 10x faster. fzf makes anything interactive. bat is cat with syntax highlighting. Separately they're fine. Together they're incredible."

**Show the alias:**
```bash
# Show what rgi actually does
type rgi

# Output shows:
rgi() {
  rg "$1" --line-number --no-heading --color=always | \
    fzf --ansi --delimiter=: \
      --preview 'bat --color=always {1} --highlight-line {2}'
}
```

---

**3.2: TODO Tracking (1 min)**

**Demo:**
```bash
# Show TODOs interactively
todosi

# This searches all TODOs/FIXMEs
# Shows them in fzf with context
# Preview shows surrounding code
```

**Decision process:**
"Initially researched 'tickgit' for TODO tracking. Installation failed. Realized ripgrep can do the same thing better. Just created aliases instead of installing another tool. That's the pattern - research thoroughly, then choose simplest solution."

---

**3.3: Semantic Versioning (1.5 min)**

**Script:**
"Best tool: svu. Semantic versioning from git commits."

**Demo:**
```bash
# Show current version
vcurrent
# Output: v0.2.3

# Show next version (analyzes commits)
vnext
# Output: v0.3.0 (because last commit was feat:)

# Show the automation
gtag
# Creates v0.3.0 tag and pushes it
```

**Show LazyGit integration:**
```bash
# Open LazyGit
lazygit

# Show custom commands in config
# Press V - shows next version
# Press T - creates and pushes tag
# Shift+V - shows current version
```

**Key point:** "Conventional commits drive versioning automatically. 'fix:' = patch bump. 'feat:' = minor bump. 'feat!:' = major bump. No more manually deciding version numbers."

---

### Part 4: Daily Workflow (2 min)

**Script:**
"Here's what my actual daily workflow looks like now."

**4.1: Morning Standup (45 sec)**

**Demo:**
```bash
standup

# Output shows:
# - Current branch per project
# - Uncommitted changes count
# - Last commit time and message
# - TODO count
# All in one command
```

**Key point:** "Before: manually checking 4 projects, took 15 minutes. Now: one command, 30 seconds."

---

**4.2: Development Flow (45 sec)**

**Demo sequence:**
```bash
# Find files
preview

# Search code
rgi "CourseGenerator"

# Check TODOs
todos

# Quick edit
fe  # Opens fzf, select file, opens in Zed
```

**Key point:** "Everything's interactive now. No more cd-ing around, grepping, forgetting file paths."

---

**4.3: End of Day (30 sec)**

**Demo:**
```bash
eod

# Shows any:
# - Uncommitted changes
# - Unpushed commits
# - Projects needing attention
```

**Key point:** "Before logging off, one command tells me if I've forgotten anything."

---

### Part 5: Portfolio Evidence (1.5 min)

**Script:**
"This all feeds into apprenticeship portfolio."

**Demo:**
```bash
# Weekly portfolio generation
portfolioWeekly

# Creates markdown report with:
# - Code stats per project
# - Git activity last 7 days
# - TODO counts
# - Saved to ~/portfolio-evidence/weekly/
```

**Show the template:**
```bash
bat ~/.claude/docs/weekly-portfolio-review-template.md | head -50
```

**Key point:** "Every Friday, run that command. Gets all metrics automatically. Template has all KSBs pre-populated. Just fill in evidence. Before: 2+ hours manual gathering. Now: 30 minutes."

---

### Part 6: Decision Process (1 min)

**Script:**
"The methodology matters. Not just 'install all the things'."

**Show the research doc:**
```bash
bat /mnt/user-data/outputs/homebrew-formulae-research.md | head -30
```

**Key point:** "Researched 14 tools. Installed 3. The rest? Either:
1. Rejected - didn't fit my stack
2. Deferred - good idea but not needed yet
3. Found better alternative

Example: tickgit for TODOs. Installation failed. Used ripgrep instead. Simpler, more reliable."

**Show the filter process:**
```markdown
# From DA-01 task
- Accept (created immediately): Quick reference, weekly template
- Sanity check (scheduled properly): Project integration checklist - depends on onboarding workflow first
- Defer (implement when needed): Automation scripts, troubleshooting guides
- Reject (won't create): Decision trees, migration guides - over-engineered
```

---

### Closing (30 sec)

**Script:**
"Three main takeaways:

1. **Systematic beats ad-hoc** - Audit framework found gaps I didn't know existed
2. **Combinations > individual tools** - fzf+fd+ripgrep+bat example
3. **Filter ruthlessly** - Research 14, install 3, reject the rest

All documented in `~/.claude/dev-environment-audit.md` if you want details. Questions?"

---

## Backup Demos (If Time Remains)

### Accessibility Testing
```bash
cd ~/Code/rhea
npm run dev &
sleep 3
axeLocal
kill %1
```

### Code Stats
```bash
stats  # Show tokei output
statsAll  # Compare all projects
```

### Dependency Analysis
```bash
deps  # Show all dependencies
depVersion "@sveltejs/kit"  # Check specific version
findPackageUsage "supabase"  # Which projects use it
```

---

## Common Questions to Anticipate

**Q: "How long did this take?"**  
A: "12 hours across two phases. Phase 1 (foundation) was 3 hours. Phase 2 (tools) was 8-9 hours. Broke even after ~3 weeks of development."

**Q: "Which tool should I install first?"**  
A: "fzf. It makes everything else interactive. Then ripgrep for search. Then bat for syntax highlighting. Those three first."

**Q: "How did you know about skills/hooks?"**  
A: "Didn't. Found them during systematic audit of official Claude Code docs. Nobody talks about them but they're incredibly powerful."

**Q: "Can I copy your config?"**  
A: "Yes. Everything's in `~/.claude/`. The shell functions are in `~/.claude/docs/cli-tools-zshrc-additions.sh`. Just append to your `.zshrc`."

**Q: "Is this overkill?"**  
A: "Maybe for a week-long project. For apprenticeship spanning months with portfolio requirements? Absolutely not. Time investment pays back quickly."

**Q: "What about Windows/Linux?"**  
A: "Most tools are cross-platform (fzf, ripgrep, bat, fd). Shell aliases need adapting for PowerShell/bash. Core concepts (skills, hooks, MCP) identical."

---

## Technical Notes

**Screen cast recording:**
- Record terminal at 16-20pt font (visibility)
- Slow down typing (easier to follow)
- Use `bat` with `--paging=never` to avoid interactive pager
- Keep Zed at 100% zoom minimum

**Timing:**
- Part 1: 1 min (problem)
- Part 2: 5 min (Claude tooling - MAIN FOCUS)
- Part 3: 4 min (CLI combinations)
- Part 4: 2 min (daily workflow)
- Part 5: 1.5 min (portfolio)
- Part 6: 1 min (decision process)
- Closing: 30 sec
- **Total: 15 min**

**Emphasis distribution:**
- 33% Claude Code features (skills, hooks, MCP)
- 27% CLI tool combinations
- 20% Implementation decisions and process
- 13% Daily workflow demo
- 7% Portfolio impact

**Fallback if over time:**
Skip backup demos and Part 6 (decision process). Covers everything in 13.5 minutes.
