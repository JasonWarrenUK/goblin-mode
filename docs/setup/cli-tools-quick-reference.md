# CLI Tools - Quick Reference Card
> **Single-page cheat sheet for daily workflows**  
> **Print or keep on second monitor while habits form**

---

## Daily Workflow

```bash
# Morning
standup                    # Check all projects status

# Development
preview                    # Find files interactively
rgi "pattern"              # Search code with preview
fe                         # Find and edit quickly
todos                      # Check TODOs

# Committing
git add .
git commit -m "feat: ..."
vnext                      # Check next version
gtag                       # Tag and push

# Evening
eod                        # Check uncommitted work
```

---

## Find Anything

| What                | Command               | Notes                    |
|---------------------|-----------------------|--------------------------|
| Any file            | `preview`             | Interactive with preview |
| TypeScript/Svelte   | `fts`                 | Filtered file types      |
| In specific dir     | `fdir src/`           | Limit scope              |
| By content          | `rgi "pattern"`       | Search and preview       |
| Find and edit       | `fe` or `rge "x"`     | Jump straight to editor  |
| Ultimate search     | `ultimate "x"`        | Filename OR content      |

---

## Search Code

| What                | Command               | Notes                    |
|---------------------|-----------------------|--------------------------|
| Interactive search  | `rgi "pattern"`       | Live preview             |
| TypeScript only     | `rgts "pattern"`      | Filtered by extension    |
| Search and edit     | `rge "pattern"`       | Opens in editor          |
| All projects        | `searchAll "pattern"` | Cross-project search     |

---

## Track TODOs

| What                | Command               | Notes                    |
|---------------------|-----------------------|--------------------------|
| List all            | `todos`               | With context             |
| Count               | `todosCount`          | Number only              |
| Interactive         | `todosi`              | Browse with preview      |
| In specific files   | `todosIn src/lib/`    | Filtered by path         |
| Export for tracking | `todos > file.txt`    | Save snapshot            |

---

## Git & Versioning

| What                | Command               | Notes                    |
|---------------------|-----------------------|--------------------------|
| Current version     | `vcurrent`            | Shows git tag            |
| Next version        | `vnext`               | Based on commits         |
| Create & push tag   | `gtag`                | Automatic versioning     |
| Version history     | `vhistory`            | Last 20 tags             |
| Browse commits      | `gitLog`              | Interactive with preview |
| Find line change    | `gitBlame file.ts`    | Interactive blame        |

**Conventional Commits:**
- `fix: ...` → patch (0.1.0 → 0.1.1)
- `feat: ...` → minor (0.1.0 → 0.2.0)
- `feat!: ...` → major (0.1.0 → 1.0.0)

---

## Project Stats

| What                | Command               | Notes                    |
|---------------------|-----------------------|--------------------------|
| Current project     | `stats`               | tokei output             |
| All projects        | `statsAll`            | Compare sizes            |
| JSON output         | `statsJson`           | Pipe to jq               |
| Portfolio evidence  | `statsPortfolio`      | Saves to ~/portfolio-evidence |

---

## Dependencies

| What                | Command               | Notes                    |
|---------------------|-----------------------|--------------------------|
| List all            | `deps`                | From package.json        |
| Dev dependencies    | `devdeps`             | Dev only                 |
| Specific version    | `depVersion "pkg"`    | Check version            |
| Compare projects    | `depsCompare ~/Code/rhea ~/Code/iris` | Diff |
| Find usage          | `findPackageUsage "supabase"` | Which projects use it |

---

## Testing

| What                | Command               | Notes                    |
|---------------------|-----------------------|--------------------------|
| Local dev           | `axeLocal`            | Port 5173 default        |
| Specific route      | `axeRoute 5173 /about`| Test single route        |
| All routes          | `axeRoutes 5173`      | Test multiple            |

---

## Scaffolding

| What                | Command               | Notes                    |
|---------------------|-----------------------|--------------------------|
| Svelte starter      | `svelteStart name`    | Quick experiment         |
| SvelteKit starter   | `svelteKitStart name` | Full framework           |
| Clone template      | `degit user/repo dir` | No git history           |
| Web → desktop       | `desktop url Name`    | Tauri wrapper            |

---

## Weekly Routine

```bash
portfolioWeekly           # Generate evidence report
statsAll                  # Compare project sizes
searchAll "TODO"          # Technical debt review
```

---

## LazyGit Integration

Press these keys in LazyGit:
- `V` - Show next version
- `T` - Create and push tag
- `Shift+V` - Show current version

---

## Common Patterns

### Portfolio Evidence Generation
```bash
cd ~/Code/rhea
statsPortfolio              # Code metrics
axeLocal                    # Accessibility
todos > ~/portfolio-evidence/rhea-todos-$(date +%Y-%m-%d).txt
```

### Project Status Check
```bash
standup                     # Morning overview
cd ~/Code/rhea
vcurrent                    # Current version
todos                       # Check TODOs
git status                  # Git status
```

### Quick Debugging
```bash
rgi "error"                 # Find error handling
rgi "console.log"           # Find debug statements
todosi                      # Check TODOs interactively
```

### Cross-Project Analysis
```bash
searchAll "useState"        # Find pattern everywhere
depsCompare ~/Code/rhea ~/Code/iris  # Compare stacks
findPackageUsage "supabase" # Which projects use it
```

---

## Keyboard Shortcuts

### fzf (in interactive mode)
- `Ctrl-/` - Toggle preview
- `↑↓` - Navigate results
- `Enter` - Select
- `Esc` - Cancel

### bat
- `q` - Quit
- `Space` - Page down
- `b` - Page up

---

## Troubleshooting Quick Fixes

| Problem             | Solution              |
|---------------------|-----------------------|
| fzf preview blank   | Check `$FZF_DEFAULT_OPTS` in .zshrc |
| svu "no tags"       | Initialize: `git tag v0.0.0` |
| todos returns nothing | No TODOs in code (good!) |
| stats shows 0       | Run from project root |

---

**Full documentation:** `~/.claude/docs/cli-tools-usage-guide.md`  
**Last updated:** 2026-01-08
