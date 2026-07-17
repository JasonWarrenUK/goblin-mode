---
name: "Config: Grant Permission"
description: "{{ 𝚫𝚫𝚫 }} Grant a permission rule globally or for the current project"
when_to_use: "When the user says things like 'allow X', 'add permission for Y', 'stop asking me about Z', or wants a Bash/tool rule added to settings without hand-editing JSON."
model: haiku
effort: low
disable-model-invocation: true
# Deliberately scoped to the one script — a permission-granting skill gets no
# broader shell access than the command it exists to run.
allowed-tools: ["Bash(python3 ~/.claude/library/scripts/config_permit.py:*)", "Read"]
arguments: ["scope", "rule"]
argument-hint: "[global|project] [permission rule, e.g. Bash(svu:*)]"
---

Add the permission rule to `permissions.allow` at the requested scope. Replaces the former config-permit-global / config-permit-project pair; the JSON handling lives in a script so the array append, dedupe and sync are one deterministic command — do not hand-edit the settings files as a fallback.

## Steps

1. Both arguments are required. If `$scope` is not `global` or `project`, or `$rule` is empty, ask rather than guessing — a permission grant is not a place for inference.
2. Run:

   ```bash
   python3 ~/.claude/library/scripts/config_permit.py $scope "$rule"
   ```

   - **global** edits `~/.claude/settings.local.jsonc` (comments preserved) and runs the settings-sync hook automatically.
   - **project** edits `.claude/settings.local.json` in the current project, creating it if absent.
3. Report the script's output verbatim: added, already present, or the error. On exit 2, surface the message and stop — if the script could not find the `allow` array, tell the user the file needs a look rather than editing it yourself.
