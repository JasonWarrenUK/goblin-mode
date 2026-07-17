← [Wiki home](../README.md)

> [!WARNING]
> **Archived — stale as of January 2026.** This tracker hasn't been touched in ~6 months; treat its task statuses as historical, not current. Kept for reference rather than deleted since it documents real decisions made during Iris's early development.

# Iris Development Tracker

> **Purpose**: Track development tasks for Iris, the ILR File Creator replacement
>
> **Context**: Iris replaces the existing Electron-based ILR File Creator with a more efficient Tauri-based application. This document tracks development work only; preparatory tooling and environment optimization remains in the main dev environment audit.

---

## Project Overview

**What**: Tauri-based desktop application for ILR file creation and transformation
**Why**: Replace bloated Electron app (~100MB) with efficient Tauri build (~10MB), better M2 performance
**Distribution**: Internal to employer, CLI-first to avoid MacOS Gatekeeper issues

---

## Status Key

- 🔴 Not Started
- 🟡 In Progress  
- 🟢 Complete
- ⚪ Blocked/Deferred

---

## Development Tasks

### Framework & Architecture

| ID | Task | Status | Notes |
|----|------|--------|-------|
| IR-01 | Desktop framework decision | 🔴 | Tauri vs alternatives. Evaluate Rust backend requirements, bundle size, M2 support, webview approach |
| IR-02 | Project template creation | 🔴 | Use CC-02 onboarding workflow to scaffold Iris. **Depends on:** IR-01, CC-02 |

### Core Development

| ID | Task | Status | Notes |
|----|------|--------|-------|
| IR-03 | Port ILR transformation logic | 🔴 | Audit existing Electron app at `~/Code/ilr-file-creator/`, identify reusable logic, migrate to Tauri. **Depends on:** IR-01, IR-02 |

### Quality & Testing

| ID | Task | Status | Notes |
|----|------|--------|-------|
| IR-06 | Iris testing strategy | 🔴 | Apply CC-04 testing patterns to Iris. Higher priority than general testing due to production replacement stakes. **Depends on:** CC-04 |

### Distribution & Deployment

| ID | Task | Status | Notes |
|----|------|--------|-------|
| IR-04 | Distribution strategy | 🔴 | CLI-first approach, GitHub releases for internal team, installation script, update mechanism (post-MVP) |

### Documentation & Evidence

| ID | Task | Status | Notes |
|----|------|--------|-------|
| IR-05 | Iris-specific evidence tracking | 🔴 | Apply WP-03 framework to Iris development for AM2 portfolio. **Depends on:** WP-03 |

---

## Dependencies

**Blocked until environment prep complete:**
- IR-02 requires CC-02 (project onboarding workflow)
- IR-05 requires WP-03 (generic evidence tracking framework)
- IR-06 requires CC-04 (testing workflow patterns)

**Internal dependencies:**
- IR-02 requires IR-01
- IR-03 requires IR-01, IR-02

---

## Timeline

Development begins once:
1. AM1 Proposal confirmation received
2. Environment optimization complete (dev-environment-audit.md tasks)
3. Framework decision made (IR-01)

---

## Deferred Tasks

### Development Documentation

| ID | Task | Priority | Notes |
|----|------|----------|-------|
| DF-01 | Portfolio evidence automation script | Low | Single command to generate all AM2 evidence (tokei stats, git logs, TODOs, dependencies) for all projects. Shell function that creates dated evidence directory with comprehensive exports. Implementation: Create `~/.claude/scripts/generate-portfolio-evidence.sh` with functions for stats/logs/todos/deps per project. Output to `~/portfolio-evidence/YYYY-MM-DD/`. **Status:** Consider implementing when weekly portfolio generation becomes time-consuming manual work. **Deferred from:** DA-01 development environment audit (2026-01-08) |
| DF-02 | Troubleshooting guide for CLI tools | Low | Document common issues and fixes for CLI tools workflow. Examples: fzf preview issues, svu initialization, todos returning nothing. Self-service debugging reference. Implementation: Create `~/.claude/docs/cli-tools-troubleshooting.md` with problem-solution pairs organized by tool category. Include diagnostic commands and known workarounds. **Status:** Add entries as actual problems arise during usage, not preemptively. **Deferred from:** DA-01 development environment audit (2026-01-08) |

---

## Reference

**Existing codebase:** `~/Code/ilr-file-creator/` (Electron)  
**Test data:** Already available  
**Main tracking doc:** `~/.claude/dev-environment-audit.md`
