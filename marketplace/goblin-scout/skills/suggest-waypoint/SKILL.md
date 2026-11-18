---
name: "Suggest Waypoint"
description: "Suggest the next logical waypoint (task) from the roadbook's pre-vetted ready-set, driven by its leverage signals"
when_to_use: "When you don't know what to work on next and want a grounded recommendation rather than picking arbitrarily."
model: sonnet
effort: low
metadata:
  glyph: ᛊ
  family: next-task
disable-model-invocation: false # read-only suggestion; invocable so "what should I work on?" loads it
allowed-tools: ["Read", "Glob", "Grep", "Bash(python3:*)", "Bash(npm:*)", "Bash(bun:*)", "Bash(pnpm:*)", "Bash(deno:*)"]
argument-hint: "[named scout (default none)] [topic focus (optional)]"
---

Suggest the next logical waypoint I can complete. Selection is grounded in deterministic data wherever possible; you choose between pre-vetted options rather than deriving them.

## Step 0: Parse arguments

`$ARGUMENTS` may carry a scout (an assignee), a focus area, both or neither; positionally, scout first. Parse by intent; blind position-splitting misreads them:

- No arguments → no scout, no focus.
- One token/phrase that plainly reads as a person's name → treat as **scout** only.
- One token/phrase that plainly reads as a topic/area (e.g. "auth", "the export flow") → treat as **focus** only, even though it's in the first position. Don't force a topic into the scout slot.
- Two tokens/phrases where the first is a name and the rest is a topic → first is **scout**, remainder is **focus**.
- If genuinely ambiguous which is which, ask rather than guess.

## Step 1: The roadbook

Run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py detect`.

**Exit 0 (rich roadbook):** run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py ready --json` and `... stats`. The `candidates` array is the complete set of actionable waypoints: every one is unblocked by definition. Each candidate carries an `assignee` field (empty string when unassigned; never assume unassigned means "anyone" without saying so). Pick using the supplied signals, in this order of pull:

1. **Scout**, when given: filter to candidates whose `assignee` matches. If none match, say so explicitly (`"No ready waypoint assigned to {name}."`), then fall back to the highest-leverage pick from the full candidate set below; never stay silent and never invent a match.
2. Focus area, when given: filter to candidates matching it
3. `transitiveUnblocks`: prefer the waypoint that unblocks the most downstream work
4. `isMilestoneSink` on a milestone with high `milestoneDonePct`: closing out a nearly-done milestone beats starting a new front

Waypoints on a trail (the `claimed` list: a scout has started them) are never candidates; if the user asks about one, say whose trail it is and since when.

Name the chosen waypoint by its roadbook ID and say which signals drove the choice. Close with how it starts: where the goblin-scout hooks are installed, creating its branch prompts the trail; otherwise `goblin-scout:start-trail <ID>` records it. If `candidates` is empty, say so and name the cheapest unblock instead (which blocker or gate, if cleared, frees the most waypoints; read the `stats` breakdown).

**Exit 3:** tell the user to run `goblin-scout:rebind-roadbook` and stop. **Exit 2:** no roadbook; point at `goblin-scout:start-roadbook` (or ask for the path if one exists somewhere unusual) and stop. This skill suggests from roadbook data only; it never derives waypoints from the codebase.

## Always

- If the waypoint will take longer than 45 minutes, subdivide it and suggest the first piece.
- After suggesting the waypoint, add a **"When complete, you'll be able to:"** section. Describe concretely and specifically what the user will see on screen or be able to do in the app that they cannot do right now. Focus on observable behaviour and leave implementation detail out.

<raw-arguments value="$ARGUMENTS" />
