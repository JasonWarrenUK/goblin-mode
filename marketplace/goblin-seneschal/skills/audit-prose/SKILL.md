---
name: "Audit Prose"
description: "Check every layer of the prose-gating suite is still wired and report how Claude's own output is trending against the house rules"
when_to_use: "When the user asks whether the writing-style setup is working, whether em dashes are creeping back, how often the commit-msg hook fires or after editing settings, hooks, the output style or the commit and prose skills; also as a periodic check."
model: sonnet
effort: low
metadata:
  glyph: ᛊ
  family: hud
  goblin-spinner: checking the gates|grading prose|counting hits
disable-model-invocation: true
allowed-tools: ["Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/prose-health.py *)", "Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/prose-metrics.py *)", "Read"]
arguments: ["scope"]
argument-hint: "[metrics] (no args = full check; metrics = the output trend only)"
---

# Audit Prose

The prose-gating suite has five layers: the output style and CLAUDE.md in the system prompt, the `commit-msg` git hook, the strict scan the prose skills run before their approval gates, the rejection contract in the commit skills and the scanner that backs all of it. Any one of them can silently come unwired (a settings file rewritten, a hook losing its executable bit, a skill edited without its gate text). This skill runs the deterministic check and turns the result into a fix list.

The suite is the user's own: the plugin ships the two audit scripts, never the scanner, the hook or the style they audit. Where each lives comes from the plugin's options, every one defaulting to goblin-mode's layout under `~/.claude`.

## Step 1: Run the check

Full check (default):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/prose-health.py --scripts-dir "${user_config.prose_scripts_dir}" --hook "${user_config.commit_msg_hook}" --hook-log "${user_config.commit_msg_log}" --style "${user_config.output_style}" --metrics-store "${user_config.prose_metrics_store}"
```

`metrics` only:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/prose-metrics.py --days 28 --scan "${user_config.prose_scripts_dir}/slop-scan.py" --state "${user_config.prose_metrics_store}"
```

The paths are quoted so one with a space stays whole; the scripts expand a leading `~/` themselves. The full check records today's output metrics into the metrics store as a side effect, so the trend survives transcript pruning.

**Exit 2 means the suite is not there.** Either script prints one `missing:` line naming the path and the option that set it (most often `slop-scan.py` under `prose_scripts_dir`). A missing PyYAML is not an exit: the full check reports `frontmatter` as a WARN and carries on. Relay that line, say which option in `/config` points elsewhere, and stop: there is nothing to audit.

## Step 2: Relay the report verbatim

Print the script's output as it came: the status lines, any `tree hits` list and the metrics table. Do not summarise the numbers away; the table is the point.

## Step 3: Turn every WARN and FAIL into a next action

One line per check that is neither PASS nor SKIP, naming the file to open or the command to run. `skills` reads SKIP only when none of the named prose and commit skills is installed on this machine; when some are and some are not, it reads WARN and names the absent ones, since a renamed or deleted skill looks the same as one never installed. A missing skill is never a FAIL.

| Check         | Fix |
|---------------|-----|
| `settings`    | Edit `~/.claude/settings.json`: `outputStyle` names the configured style file, and the `attribution` block is cleared |
| `style`       | Edit the output style file's frontmatter (`output_style` option), or run the strict scan on it and fix the hits |
| `hook`        | `git config --global core.hooksPath <the hook's folder>`, `chmod +x <the commit_msg_hook option>`, or reinstall python3 |
| `hook-log`    | Informational; a rejection rate above about 20% over a week means the commit skills are not pre-checking their messages |
| `skills`      | FAIL: open the named skill; the gate text or the `allowed-tools` entry was removed. Restore it from git history. WARN: for each absent skill, say whether it was renamed, deleted or never installed here (`git log --diff-filter=D --name-only -- skills/` in `~/.claude` shows a deletion); a rename means `SKILL_WIRING` in the plugin's `prose-health.py` wants the new name, which is a change to the plugin |
| `frontmatter` | Open the named file; usually an unquoted colon in a `description:` value |
| `tree`        | Run `slop-scan.py --strict` from the `prose_scripts_dir` option on the listed files and fix them. If the new hits are clause-joining commas, say so: the tolerance is `RESIDUAL_TOLERANCE` in the plugin's own `prose-health.py`, which an update replaces, so raising it is a change to the plugin, never an edit in the cache (the tolerance carries headroom above the audited count, so tripping it means several have accumulated) |
| `tests`       | Run `python3 -m pytest test_slop_scan.py test_prose_metrics.py test_commit_msg_hook.py` in the `prose_scripts_dir` folder and read the failure |
| `index`       | `python3 gen-skills-index.py` in the `prose_scripts_dir` folder |
| `output`      | The system-prompt layer is not holding. Check `settings` and `style` first; if both pass and the rate stays above 3 per 1k words for a week, the next structural step is a `MessageDisplay` hook, which nothing here builds |

Never apply a fix in this skill; it reports. Offer the fix and stop.

## Red flags

**Never:** edit `RESIDUAL_TOLERANCE` to make `tree` pass without reading the hits; suppress a FAIL by editing the check; read the metrics as a verdict on one session (the window is seven days for a reason); audit a different suite than the options name.

<raw-arguments value="$ARGUMENTS" />
