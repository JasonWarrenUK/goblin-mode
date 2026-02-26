# Git Configuration Documentation

> **Created**: 2026-01-06  
> **Purpose**: Document and maintain Jason's git configuration

---

## `.gitconfig` Overview

**Location**: `~/.gitconfig`

### Current Configuration

```ini
[filter "lfs"]
    clean = git-lfs clean -- %f
    smudge = git-lfs smudge -- %f
    process = git-lfs filter-process
    required = true

[user]
    name = Jason Warren
    email = jason@foundersandcoders.com

[core]
    excludesfile = /Users/jasonwarren/.gitignore_global
    editor = code --wait

[pull]
    rebase = false
```

### Configuration Breakdown

#### Git LFS (Large File Storage)
```ini
[filter "lfs"]
    required = true
```
- **Purpose**: Track large files (binaries, media, datasets) efficiently
- **Usage**: Files tracked in `.gitattributes` (e.g., `*.png filter=lfs`)
- **Required**: Must have `git-lfs` installed for repos using LFS

#### User Identity
```ini
[user]
    name = Jason Warren
    email = jason@foundersandcoders.com
```
- **Used for**: All commits made on this machine
- **Scope**: Global (all repositories)
- **Override**: Can be overridden per-repository with `git config user.email <other-email>`

#### Core Settings
```ini
[core]
    excludesfile = /Users/jasonwarren/.gitignore_global
    editor = code --wait
```
- **excludesfile**: Global gitignore (see next section)
- **editor**: 
  - Currently: `code --wait` (VS Code)
  - **Note**: Jason uses LazyGit for all git operations, so editor config is rarely invoked
  - Kept for fallback scenarios (e.g., interactive rebase, git revert)

#### Pull Strategy
```ini
[pull]
    rebase = false
```
- **Behaviour**: Use merge strategy when pulling (creates merge commits)
- **Alternative**: `rebase = true` would replay local commits on top of remote
- **Why merge**: 
  - Simpler mental model
  - Preserves exact history of how work was integrated
  - Aligns with feature branch workflow

---

## Global Gitignore

**Location**: `~/.gitignore_global`

### Purpose
Ignore files across ALL repositories on this machine. Used for:
- OS-generated files (macOS `.DS_Store`)
- Editor configurations (personal Zed settings)
- Environment variables (`.env` files)
- Build artifacts and dependencies

### Categories

#### macOS System Files
```
.DS_Store               # Finder metadata
.AppleDouble            # Resource forks
.LSOverride             # Icon customizations
._*                     # AppleDouble files
```

**Why global**: These appear in every directory, never want to commit them

#### Editor Configurations
```
.config/zed/settings.json    # Personal Zed config (NOT project-level)
.vscode/                     # VS Code workspace (if collaborators use it)
.idea/                       # JetBrains IDEs
*.swp, *.swo, *~             # Vim swap files
```

**Why global**: Editor preferences are personal, not project-specific

**Important**: Project-level configs (`.vscode/extensions.json`, workspace settings) should NOT be globally ignored - those are intentionally shared with team

#### Environment & Secrets
```
.env
.env.*
!.env.example            # Exception: template files are tracked
!.env.template
```

**Why global**: Prevent accidental exposure of API keys, credentials, database URLs

#### Dependencies & Build Artifacts
```
node_modules/           # NPM packages
dist/                   # Build output
build/
.next/                  # Next.js build
.cache/                 # Various caches
coverage/               # Test coverage reports
```

**Why global**: Generated files, always reconstructable from source

#### Logs & Temp Files
```
*.log
logs/
tmp/
*.tmp
*.bak
```

**Why global**: Runtime artifacts, never want in version control

### Management

**Adding new patterns**:
```bash
echo "new-pattern/" >> ~/.gitignore_global
```

**Checking if file is ignored**:
```bash
git check-ignore -v path/to/file
```

**Why a file isn't being ignored**:
- Global ignore only applies to UNTRACKED files
- If file was previously committed, it remains tracked
- Solution: `git rm --cached <file>` to untrack

---

## Workflow Integration

### LazyGit
- **Primary interface**: All git operations done through LazyGit TUI
- **Config location**: `~/.config/lazygit/config.yml` (not yet documented)
- **Benefits**: 
  - Visual branch/commit graph
  - Interactive staging/unstaging
  - Simplified rebase/cherry-pick
  - Integrated diff viewer

### Shell Aliases (from `dev-aliases.zsh`)
- `gs` - Git status (short format)
- `gl` - Last 10 commits
- `gd` - Diff unstaged changes
- `gDC` - Diff staged changes
- `gb` - List all branches
- `gCM` - Quick commit with message

**Note**: These complement LazyGit for quick CLI checks, not as replacement

---

## Removed Configurations

### Sourcetree Integration (2026-01-06)
```ini
# REMOVED - no longer using Sourcetree
[difftool "sourcetree"]
[mergetool "sourcetree"]
```
**Reason**: Migrated to LazyGit for all git workflows

### Commit Template (2026-01-06)
```ini
# REMOVED
[commit]
    template = /Users/jasonwarren/.stCommitMsg
```
**Reason**: LazyGit handles commit messages, template was Sourcetree-specific

---

## Future Considerations

### Potential Additions

**Auto-correct typos**:
```ini
[help]
    autocorrect = 10   # Auto-run closest match after 1 second
```

**Better diff algorithm**:
```ini
[diff]
    algorithm = histogram   # More readable diffs
```

**Default branch name**:
```ini
[init]
    defaultBranch = main
```

**Credential caching** (if using HTTPS):
```ini
[credential]
    helper = osxkeychain   # macOS keychain integration
```

**Push behaviour**:
```ini
[push]
    default = current      # Push current branch to same name on remote
    autoSetupRemote = true # Auto-create remote branch on first push
```

### Not Adding (Intentionally)

**Git aliases in `.gitconfig`**:
- **Reason**: Jason uses shell aliases + LazyGit
- Git aliases (e.g., `git co` for `checkout`) less discoverable than shell aliases
- Shell aliases show up in command history, easier to remember

**Complex merge/rebase settings**:
- **Reason**: Will be covered in RS-02 (Git merge vs rebase understanding)
- Premature to configure before understanding tradeoffs

---

## Maintenance

### Regular Reviews
- **Quarterly**: Check if global gitignore needs updates (new tools, frameworks)
- **Per-project**: If committing unwanted files, add pattern to global ignore
- **After LazyGit updates**: Review if config needs adjustments

### Backup
```bash
# Backup current config
cp ~/.gitconfig ~/Dropbox/backups/gitconfig-$(date +%Y%m%d)
cp ~/.gitignore_global ~/Dropbox/backups/gitignore_global-$(date +%Y%m%d)
```

### Version Control
Consider tracking dotfiles in a repository:
```bash
# Example structure
~/dotfiles/
├── .gitconfig
├── .gitignore_global
├── .zshrc
└── install.sh   # Symlink script
```

---

## References
- [Git Configuration Docs](https://git-scm.com/docs/git-config)
- [Global Gitignore Best Practices](https://gist.github.com/octocat/9257657)
- [LazyGit](https://github.com/jesseduffield/lazygit)
