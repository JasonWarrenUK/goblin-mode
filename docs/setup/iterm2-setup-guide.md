# iTerm2 Configuration Guide

> **Created**: 2026-01-06  
> **Purpose**: Optimize iTerm2 for efficient development workflow

---

## Overview

This guide covers setting up iTerm2 profiles, keyboard shortcuts, and tab management for Jason's workflow. All settings are accessed via **iTerm2 → Settings** (⌘,).

---

## Profile Configuration

### Creating a Development Profile

**Location**: Settings → Profiles → Click "+" to create new profile

#### Basic Settings

**General Tab**:
- **Name**: "Development" (or "Dev")
- **Badge**: Optional - can show username, hostname, or custom text in terminal corner
- **Working Directory**: "Reuse previous session's directory"

**Colors Tab**:
- **Preset**: Choose one (recommendations below)
  - **Catppuccin Latte** (light mode) - matches Zed theme
  - **Catppuccin Macchiato** (dark mode) - matches Zed theme
  - **Dracula** (popular, high contrast)
  - **Nord** (muted, easy on eyes)
- **Minimum contrast**: Adjust if text is hard to read (range: 0-1)

**Text Tab**:
- **Font**: Fira Code (matches Zed)
  - **Size**: 14-16pt (16pt matches Zed)
  - **Use ligatures**: ✓ Enabled (shows `=>` as single character, etc.)
  - **Vertical spacing**: 100-110% (adjust for comfort)
  - **Horizontal spacing**: 100%
- **Anti-aliased**: ✓ Enabled

**Window Tab**:
- **Transparency**: 0-5% (subtle - too much is distracting)
- **Blur**: 0-10 (only if using transparency)
- **Columns**: 120-140 (wide enough for code + git status side-by-side)
- **Rows**: 30-40 (enough for command output without excessive scrolling)
- **Style**: Native (or Minimal for cleaner look)

**Terminal Tab**:
- **Scrollback lines**: Unlimited (or 10,000+)
- **Character encoding**: UTF-8
- **Report terminal type**: xterm-256color

**Session Tab**:
- **Status bar enabled**: ✓ (optional but useful)
  - If enabled, configure components: CPU, Memory, Clock, Current Directory

**Keys Tab**:
- **Load Preset**: "Natural Text Editing"
  - Allows Option+Arrow to jump words
  - Command+Arrow to jump to line start/end
  - Enables standard macOS text editing shortcuts

---

## Keyboard Shortcuts

### Tab Management

**Access**: Settings → Keys → Key Bindings

Recommended shortcuts (may already be set):

| Action | Shortcut | Notes |
|--------|----------|-------|
| New Tab | ⌘T | Standard |
| Close Tab | ⌘W | Standard |
| Next Tab | ⌘⇧] or ⌃Tab | Navigate right |
| Previous Tab | ⌘⇧[ or ⌃⇧Tab | Navigate left |
| Go to Tab 1-9 | ⌘1 through ⌘9 | Quick tab switching |
| Move Tab Left | ⌘⌥← | Reorder tabs |
| Move Tab Right | ⌘⌥→ | Reorder tabs |

### Pane Management (Split Windows)

| Action | Shortcut | Notes |
|--------|----------|-------|
| Split Vertically | ⌘D | Side-by-side panes |
| Split Horizontally | ⌘⇧D | Top-bottom panes |
| Next Pane | ⌘] | Cycle through panes |
| Previous Pane | ⌘[ | Cycle backwards |
| Close Pane | ⌘W | Same as close tab |

### Navigation & Search

| Action | Shortcut | Notes |
|--------|----------|-------|
| Find | ⌘F | Search output |
| Clear Buffer | ⌘K | Clean terminal |
| Clear Scrollback | ⌘⌥K | Nuclear option |

### Custom Shortcuts to Add

**Option 1: Clear and List** (common workflow)
1. Settings → Keys → Key Bindings → "+"
2. Keyboard Shortcut: ⌘⌥L
3. Action: "Send Text"
4. Text: `clear\nll\n` (clear, then list with lsd)

**Option 2: Git Status** (quick repo check)
1. Keyboard Shortcut: ⌘⌥G
2. Action: "Send Text"
3. Text: `gs\n` (your git status alias)

---

## Profile Management

### Setting Default Profile

1. Settings → Profiles
2. Select your "Development" profile
3. Click "Other Actions..." (bottom left)
4. Choose "Set as Default"

Now all new windows/tabs use this profile.

### Profile Shortcuts

Assign hotkeys to quickly open specific profiles:

1. Settings → Keys → Hotkey
2. Check "Create a Dedicated Hotkey Window..."
3. Set hotkey (e.g., ⌥Space for Visor-style dropdown terminal)

---

## Window Arrangements

### Saving Window Layout

For projects requiring multiple tabs/panes:

1. Set up your ideal layout (e.g., 3 tabs: code, server, logs)
2. Window → Save Window Arrangement → Give it a name
3. Later: Window → Restore Window Arrangement → Select saved layout

**Use Case**: "Rhea Development" arrangement could have:
- Tab 1: Main terminal (for git, npm commands)
- Tab 2: Dev server (`nRD`)
- Tab 3: Separate terminal for testing/debugging

---

## Advanced Settings

### Shell Integration

**Strongly Recommended** - Adds powerful features:

1. Settings → Profiles → [Your Profile] → General → Command
2. Check "Login shell" (should already be set)
3. Install shell integration:
   ```bash
   curl -L https://iterm2.com/shell_integration/install_shell_integration_and_utilities.sh | bash
   ```

**Features Gained**:
- Command history timestamps
- Right-click to "Copy Last Command Output"
- Semantic history (⌘-click filenames to open)
- Command marking (jump between commands with ⇧⌘↑/↓)

### tmux Integration (Optional)

If using tmux for session management:
- Settings → General → tmux
- Check "Use tmux integration"
- Turns tmux panes into native iTerm2 tabs

*Note: Not required for most workflows*

---

## Status Bar Configuration

### Enabling Status Bar

Settings → Profiles → [Your Profile] → Session → Status bar enabled ✓

### Recommended Components

Drag these to the status bar (Settings → Profiles → Session → Configure Status Bar):

| Component | Value | Position |
|-----------|-------|----------|
| Current Directory | Last 2 components | Left |
| git branch | Auto | Left-Middle |
| CPU Utilization | Auto | Right-Middle |
| Memory Utilization | Auto | Right-Middle |
| Clock | Time (24h) | Right |

**Styling**:
- Background color: Slightly darker than terminal background
- Font: Match terminal font, 1-2pt smaller

---

## Performance Optimization

### If iTerm2 Feels Slow

Settings → General → Performance:
- ✓ Enable GPU rendering
- ✓ Prefer integrated GPU

Settings → Profiles → [Your Profile] → Terminal:
- Disable unnecessary features if slow:
  - Unchecked: "Enable mouse reporting"
  - Unchecked: "Report focus" (if not needed)

---

## Exporting Configuration

### Once You're Happy With Setup

**Export Preferences**:
1. Settings → General → Preferences
2. Check "Load preferences from a custom folder or URL"
3. Choose location: `~/Dropbox/iTerm2/` or `~/Documents/iTerm2/`
4. Check "Save changes to folder when iTerm2 quits"

**Benefits**:
- Sync across machines (if using Dropbox/iCloud)
- Version control preferences (if using Git directory)
- Easy disaster recovery

### Backup Current Config

```bash
# One-time backup of current config
mkdir -p ~/Documents/iTerm2-backups
cp ~/Library/Preferences/com.googlecode.iterm2.plist ~/Documents/iTerm2-backups/iterm2-backup-$(date +%Y%m%d).plist
```

---

## Quick Start Checklist

For immediate productivity gains, prioritize these:

- [ ] Create "Development" profile
- [ ] Set Fira Code 16pt font
- [ ] Choose color scheme (Catppuccin to match Zed)
- [ ] Enable "Natural Text Editing" key preset
- [ ] Set terminal size to 120-140 columns
- [ ] Install shell integration
- [ ] Set as default profile
- [ ] Test keyboard shortcuts (⌘T, ⌘D, ⌘W)

**Time estimate**: 10-15 minutes

---

## Troubleshooting

### Fonts Not Loading
- Ensure Fira Code is installed system-wide
- Try: `brew install font-fira-code`
- Restart iTerm2 after installing fonts

### Aliases Not Working
- Shell integration might override PATH
- Check: `echo $PATH` in iTerm2 vs other terminals
- Ensure `.zshrc` is being loaded: Add `echo "zshrc loaded"` temporarily

### Colors Look Wrong
- Check terminal type: `echo $TERM` should show `xterm-256color`
- Profile → Terminal → Report terminal type

---

## Next Steps

After configuring iTerm2, consider:
1. Creating saved window arrangements for common projects
2. Exploring Marks & Annotations feature for long-running outputs
3. Setting up automatic profile switching (based on directory)

---

## References
- [iTerm2 Documentation](https://iterm2.com/documentation.html)
- [Shell Integration](https://iterm2.com/documentation-shell-integration.html)
- [Catppuccin for iTerm2](https://github.com/catppuccin/iterm2)
