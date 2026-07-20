---
name: "Roadmap: Build Zip"
description: "{{ 𝚫𝚫𝚫 }} Rebuild roadmap-system.zip, the distributable snapshot of the roadmap tooling (scripts, HTML template, conventions reference, and every roadmap-touching skill, including this one)."
when_to_use: "When the roadmap scripts, conventions reference, or any roadmap-* skill have changed and the distributable zip needs refreshing before sharing it outside this repo."
model: haiku
disable-model-invocation: true
allowed-tools: ["Bash(zsh:*)"]
---

Run the build script and report its output:

```bash
zsh "$HOME/.claude/library/scripts/build-roadmap-zip.sh"
```

It rewrites `roadmap-system.zip` at the repo root from the manifest in `build-roadmap-zip.sh`'s `files` array, then lists the archive contents to confirm. If it exits non-zero (a manifest entry went missing), report the missing path — the fix is to update the `files` array in `build-roadmap-zip.sh`, not to work around it here.
