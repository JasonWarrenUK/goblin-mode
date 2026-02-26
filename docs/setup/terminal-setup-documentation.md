# Terminal Setup Documentation

> **Created**: 2026-01-06  
> **Purpose**: Complete documentation of Jason's terminal configuration for reference and disaster recovery

---

## Shell Configuration

### Base Shell
- **Shell**: zsh (macOS default)
- **Framework**: Oh My Zsh
- **Installation path**: `~/.oh-my-zsh`
- **Config file**: `~/.zshrc`

### Oh My Zsh Configuration
- **Theme**: `robbyrussell` (default)
- **Active plugins**: 
  - `git` (commit shortcuts, branch info, etc.)
- **Custom directory**: `~/.oh-my-zsh/custom/`

### Installed but Inactive Plugins
- **zsh-autosuggestions**: Installed at `~/.oh-my-zsh/custom/plugins/zsh-autosuggestions` but not enabled in plugins array
  - To enable: Add `zsh-autosuggestions` to the `plugins=()` array in `.zshrc`

---

## Navigation & Directory Management

### zoxide
- **Purpose**: Smarter `cd` with frecency-based directory jumping
- **Initialization**: `eval "$(zoxide init zsh)"`
- **Custom alias**: `alias cd="z"` (defined in `~/.oh-my-zsh/custom/shortcuts.zsh`)
- **Usage**:
  - `z <partial-name>` jumps to most frequent/recent match
  - `zi <partial-name>` interactive selection
  - Standard `cd` now uses zoxide under the hood

### broot
- **Purpose**: Terminal file navigation and preview
- **Config**: Sourced from `/Users/jasonwarren/.config/broot/launcher/bash/br`
- **Usage**: `br` command for interactive file browsing

---

## Language Runtime Managers

### Node Version Manager (NVM)
- **Location**: `~/.nvm`
- **Purpose**: Manage multiple Node.js versions
- **Initialization**: Loaded in `.zshrc` with bash completion
- **Common commands**:
  - `nvm install <version>` - Install Node version
  - `nvm use <version>` - Switch to version
  - `nvm current` - Show active version

### Deno
- **Environment file**: `/Users/jasonwarren/.deno/env`
- **Purpose**: TypeScript/JavaScript runtime
- **Loaded conditionally**: Only if env file exists

### bun
- **Installation**: `~/.bun`
- **Purpose**: Fast JavaScript runtime and package manager
- **Completions**: Loaded from `~/.bun/_bun`
- **Added to PATH**: `$BUN_INSTALL/bin`

---

## Language-Specific Paths

### Python 3.9
- **Xcode Python**: `/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/bin`
- **User Python**: `~/Library/Python/3.9/bin`
- Both added to PATH

### .NET
- **DOTNET_ROOT**: `/usr/local/share/dotnet/x64`
- Required for .NET CLI and development

---

## Additional PATH Entries

- `~/.local/bin` - User-local binaries (common convention)
- `$BUN_INSTALL/bin` - bun executables

---

## API Keys & Secrets

Stored as environment variables in `.zshrc`:
- `CONTEXT7_API_KEY` - Context7 MCP server
- `GITHUB_PAT` - GitHub Personal Access Token

**Security note**: These are loaded into the environment but not exposed in version control (assuming `.zshrc` is not tracked or uses .gitignore)

---

## iTerm2 Configuration

### Profiles
> **TODO**: Document iTerm2 profiles once configured
> - Default profile settings
> - Color schemes
> - Font configuration
> - Split pane preferences
> - Tab management

### Preferences Location
- macOS: `~/Library/Preferences/com.googlecode.iterm2.plist` (binary plist)
- Can be exported to JSON/XML via iTerm2 Preferences → General → Preferences → "Load preferences from a custom folder"

---

## Customization Files

### Oh My Zsh Custom
- **Location**: `~/.oh-my-zsh/custom/`
- **shortcuts.zsh**: Custom aliases (currently just `cd` → `z`)
- **Example template**: `example.zsh` (reference for creating new custom files)

### Adding New Aliases
1. Create file in `~/.oh-my-zsh/custom/` with `.zsh` extension
2. Add aliases/functions
3. Restart shell or run `source ~/.zshrc`

### Adding New Plugins
1. Install plugin to `~/.oh-my-zsh/custom/plugins/<plugin-name>/`
2. Add plugin name to `plugins=()` array in `.zshrc`
3. Restart shell

---

## Disaster Recovery

### Backup Files Present
- `.zshrc.pre-oh-my-zsh` - Pre-Oh-My-Zsh configuration
- Contains legacy PATH exports and early NVM setup

### Critical Files to Backup
- `~/.zshrc` - Main shell config
- `~/.oh-my-zsh/custom/*.zsh` - Custom aliases and functions
- `~/.gitconfig` - Git configuration (tracked separately)
- iTerm2 preferences (if configured)

### Restore Process
1. Install Oh My Zsh: `sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"`
2. Restore `.zshrc` from backup
3. Install custom plugins:
   - zsh-autosuggestions: `git clone https://github.com/zsh-users/zsh-autosuggestions ~/.oh-my-zsh/custom/plugins/zsh-autosuggestions`
4. Install tools:
   - zoxide: `brew install zoxide` (or `cargo install zoxide`)
   - broot: `brew install broot`
   - NVM: Follow https://github.com/nvm-sh/nvm#installing-and-updating
5. Restart shell

---

## Performance Considerations

### Startup Time
Current configuration should be relatively fast:
- Single Oh My Zsh plugin (git)
- Lazy-loaded tools (NVM, Deno, bun)
- No heavy prompt themes

### Potential Optimizations
- Enable `zsh-autosuggestions` if useful (minimal overhead)
- Consider `zsh-syntax-highlighting` for better command feedback
- Profile startup time with: `time zsh -i -c exit`

---

## Next Steps (SH-01 Parts B & C)

### Part B: High-Impact Aliases
> To be created based on usage patterns

### Part C: iTerm2 Configuration
> To be documented once profiles are established

---

## References
- [Oh My Zsh](https://ohmyz.sh/)
- [zoxide](https://github.com/ajeetdsouza/zoxide)
- [broot](https://dystroy.org/broot/)
- [NVM](https://github.com/nvm-sh/nvm)
