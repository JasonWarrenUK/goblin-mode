---
name: "Version: Tag"
description: "{{ 𝚫𝚫𝚫 }} Compute the next semver tag with svu and push it"
when_to_use: "At PR creation, or on merge to main or staging — svu doesn't commit, push, or merge, so pair it with git tag whenever a versioning moment is reached."
model: haiku
effort: low
disable-model-invocation: true
allowed-tools: ["Bash(svu:*)", "Bash(git tag:*)", "Bash(git push:*)", "Bash(~/.claude/library/scripts/safe-version-next.sh:*)"]
---

# Tag the next version with `svu`

[`svu`](https://github.com/caarlos0/svu) derives the next semver tag from conventional-commit history. It only computes the version; it never commits, pushes, or merges.

**Hard rule:** the tag always comes from `safe-version-next.sh`, never bare `svu next`. The script is identical to `svu next` except it refuses to cross 0.x → 1.x automatically — declaring the API stable is a human decision, so it emits a 0.x minor bump instead (and says so on stderr). Later major bumps pass through. If the guard fires, relay its note.

## Always tag at these moments

Run the script, then tag and push:

| Moment | Command sequence |
|---|---|
| PR creation | `git tag "$("$HOME"/.claude/library/scripts/safe-version-next.sh)" && git push --tags` |
| Merge to `main` | `git tag "$("$HOME"/.claude/library/scripts/safe-version-next.sh)" && git push --tags` |
| Merge to `staging` | `git tag "$("$HOME"/.claude/library/scripts/safe-version-next.sh)" && git push --tags` |

## Mid-branch commits: offer, don't tag silently

Proactively offer a tag **only** when the pending bump is major or minor. Stay silent on patch bumps.

Detect the bump level by comparing `svu current` with `svu next`:

- Different major segment → major; offer a tag.
- Same major, different minor → minor; offer a tag.
- Only the patch segment changed → patch; do not offer.

Surface the proposed version rather than tagging silently, e.g.:

```text
⬆️ minor bump available — tag v1.3.0?
```
