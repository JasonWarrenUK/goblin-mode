# Hand-off: originality gate improvements (applicability + surface-type scoping)

Written 2026-09-22 during the `explain` CLI build in `apps/explainers`, when `explaintui` warned at distance 0.053 against `tumulus` and the "keep it anyway" justification exposed two gaps in `checkOriginality` (`~/.claude/library/scripts/theme/validate.ts:280`). Not built there: both are changes to shared global tooling, out of scope for a single project's task. Two separable pieces of work.

## Piece 1: applicability — can the two themes ever occur in the same project?

**Problem.** `seen.json` signatures carry no notion of which project registered them (`Signature` interface at `validate.ts:63` is `{ family, source, swatches }`, nothing else). A theme from an unrelated project's `.claude/themes/` gets compared against every new theme everywhere, even though the two can never be open side by side. Only genuinely global things — the `~/.claude/library/themes/` fallback family and any project the user works in concurrently — are real collision risk.

**Why it's a schema change, not a tweak.** Fixing this means `--register` (`validate.ts:365`) writes a project field (repo path, or "global" for the `~/.claude/library/themes/` family) alongside each signature. Every existing entry in `seen.json` is then missing that field. Three registered entries (`brass`, `tuff`, `tumulus` — confirmed via `find` across the filesystem during this session, no backing `.json` files exist anywhere) can't even be back-filled with a real project path, since their source files are gone. Needs a decision: treat fieldless legacy entries as "always applicable" (safe, conservative, keeps today's behaviour for them) or drop them from the comparison set entirely (loses whatever signal they still carry).

**Suggested shape.** Add `project: string | null` to `Signature`. `theme-factory` passes the current working directory (or a `--project` flag) through to `--register`. `checkOriginality` only compares against signatures where `project === null` (global fallback, always applicable) or `project` matches a list of "concurrently open" projects — which doesn't exist as a concept anywhere yet, so the honest v1 is probably: global signatures always apply, project-scoped signatures only apply to re-runs within the same project. That alone would have kept `explaintui` from ever seeing `tumulus` if `tumulus` turns out to be a different project's theme (unconfirmed — its source file is gone, so this can't be verified from here).

## Piece 2: surface-type scoping — do the two themes target the same kind of interface?

**Problem.** `checkOriginality` compares core-to-core (`palette` signatures via `signatureOf`, `validate.ts:73`), never looking at which target files (`html`, `vhs`, `tui`, etc.) either family has actually been extended to. A `tui`-only theme and an `html`-only theme with similar core swatches trip the warning even though they're never rendered next to each other or even in the same medium.

**Why it's not a clean glob.** The obvious fix — glob sibling `<family>-*.json` files next to each core to see its targets — breaks immediately for exactly the entries that most need it: `brass`, `tuff` and `tumulus` are registered in `seen.json` with no backing core file on disk at all, so there's nothing to glob. Any fix has to work when the signature comes only from `seen.json`, not from a live file.

**Suggested shape.** Two options, in order of how much they cost:
1. **Cheapest, partial:** when validating a target file (not just a core), only compare against `seen.json` entries that also record having a same-target file, which means `--register` needs a `targets: string[]` field too, populated the same way as the project field, best-effort for legacy entries.
2. **More complete:** `checkOriginality` takes the target being validated as a parameter (currently it's core-only, called once at `validate.ts:343`, before any target-specific work). When a `tui` target is what's actually being checked, the comparison set should probably be "other tui targets across the same-or-related projects", not "every core signature regardless of medium". This changes the gate from running once per core to running per target extension too, which is a bigger structural change to when/how `checkOriginality` fires.

## What's cheap to do now if you want a quick win before the full redesign

Neither of the above needs to land before this: **filter the comparison set by whether the candidate is a `tui` target at all.** Since `SIGNATURE_KEYS = ['surface', 'surface-raised', 'ink', 'accent', 'accent-2']` already comes from the *core*, not the target, this doesn't get you surface-type scoping properly, but a one-line addition — skip any `seen.json` entry whose `source` filename doesn't correspond to a family known to have a `tui` (or the target currently being validated) — is a partial, honest step that doesn't require a schema migration, at the cost of being wrong for any family missing its source file (same three orphans again).

## Recommendation for whoever picks this up

Start with piece 1 (project field), since it's the simpler schema addition and immediately de-risks the common case (unrelated small projects tripping each other's originality gate). Piece 2 needs the harder decision about *when* `checkOriginality` runs (core-time vs target-time) and should probably wait until there are enough `tui`/`vhs`/etc. targets in the wild to know whether cross-medium collisions are a real problem worth the added complexity, or a hypothetical one.

Either piece should start by deciding what to do about the three orphan `seen.json` entries (`brass`, `tuff`, `tumulus`): back-fill with best-guess metadata, mark them legacy/unscoped, or drop them and accept a slightly weaker originality history.
