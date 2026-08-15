---
name: "Artefact: Design Conventions"
description: "Jason's structural and epistemic-honesty conventions for every artefact Claude creates"
when_to_use: "Before writing any artefact — a claude.ai/Cowork Artifact, a Claude Code project artefact, or the styling pass inside import-scaffold_artefact — alongside whatever medium-specific requirements already apply (e.g. the Artifact tool's own artifact-design skill)."
disable-model-invocation: false # the trigger moment (about to write an artefact) is one Claude recognises before the user does; the per-project interview (Step 2b) is its own approval gate before anything gets written
metadata:
  family: artefact
allowed-tools: ["Read", "Glob", "Grep", "Write", "AskUserQuestion"]
---

# Artefact design conventions

Every artefact Claude writes for Jason — a claude.ai/Cowork Artifact, a
Claude Code project artefact, a ported real app's styling pass — follows the
same location rule and the same values, expressed in a bespoke way each
time. The full ruleset lives in
`~/.claude/library/references/artefact-conventions.md`; this skill is the
procedure that gets it applied.

**Announce at start** (briefly, not a whole paragraph): which artefact
you're about to write and where.

## Step 1: Location, always

Every artefact — named-skill output or something created ad hoc
mid-conversation — writes to `<project-root>/docs/artefacts/{slug}.html`.
No other location. If there's no obvious project root (a bare claude.ai
conversation with no repo), this step doesn't apply — that's the `Artifact`
tool's territory, not a repo file.

- [ ] Target path resolved to `<project-root>/docs/artefacts/{slug}.html`

## Step 2: Check what's already there

```bash
ls <project-root>/docs/artefacts/*.html 2>/dev/null
```

**Existing artefacts found** → read one (or a couple, if they look
stylistically inconsistent with each other). Extract the established
palette/hue-mapping (read the CSS `:root` block and its mapping-notes
comments if present), font pairing, and tone. State it back in one line —
*"this project already has an artefact aesthetic: {short description};
reusing it"* — and carry it into the new artefact. **No interview.**
Consistency with the project's own prior artefacts wins over inventing
something new.

**This is the project's first artefact** → go to Step 2b.

- [ ] Directory checked before writing anything
- [ ] Existing aesthetic (if any) read and stated back in one line

## Step 2b: First artefact for this project — brief interview

Run a short, round-based interview — same discipline as
`import-scaffold_artefact` Step 3 and `roadmap-create-interview`: **2-4
questions per round**, never a long list at once, and end each round with
*"Anything else, or shall I go ahead?"*. Skip any question the content
itself already answers (a pipeline-metrics doc doesn't need to ask if this
is a data-heavy artefact).

Cover:
- **Palette mood** — what hue(s) should this artefact's semantic aliases map
  to, and why (the reference doc's RC-mapping rule expects a stated reason,
  not just a colour pick).
- **Font pairing** — display/body voice + monospace workhorse; free choice,
  but ask rather than default silently.
- **Tone** — reference/data page, narrative piece, or something between; this
  determines whether Step 3's honesty rule expresses as status chips or a
  footnote (see the reference doc).

Once agreed, **write the outcome into the CSS as explicit mapping-notes
comments**, the way `those-who-came-before/site/assets/site.css` does —
document *why* each alias maps to which RC hue. This first artefact becomes
the self-documenting spec Step 2 reads back on every artefact after it in
this project; nobody should have to re-ask these questions for the second
artefact.

- [ ] Interview run in 2-4-question rounds, none dumped at once
- [ ] Outcome written as mapping-notes comments in the artefact's own CSS

## Step 3: Apply the shared rules

Read `~/.claude/library/references/artefact-conventions.md` in full and
apply: masthead structure, RC-sourced semantic palette (this project's own
mapping from Step 2/2b), the three-state theming contract, typography
pairing, the collapsibility threshold, the epistemic-honesty rule (structural
marking, never hedging prose), and the technical-hygiene list
(self-contained, `overflow-x` scrollers, `tabular-nums`, British spelling).

For a claude.ai/Cowork `Artifact` publish specifically: this skill's rules
are additive to Anthropic's built-in `artifact-design` /
`artifact-diagramming` / `artifact-capabilities` skills, not a replacement —
favicon, CSP self-containment, and runtime capabilities stay owned by those.
Load both.

- [ ] Masthead present (or deliberately compressed for a short narrative piece)
- [ ] Palette routes through RC tokens via semantic aliases only
- [ ] Three-state theming contract present, or single-look justified explicitly
- [ ] Collapsibility applied if past the threshold
- [ ] Honesty rule expressed structurally, not as hedging prose
- [ ] Self-contained; `overflow-x` scrollers on wide content; British spelling

## Step 4: Write

Show the draft (or its key structural decisions, for a long artefact) before
writing, following the same approval convention `artefact-audit` and
`artefact-roadmap` already use. Write to the Step 1 path. Report the file
path, the aesthetic decision (reused or newly interviewed), and anything
notable in how the honesty rule was expressed.
