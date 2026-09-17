# Review Reaction Signals

Shared reference for `pr-handle_review`, which is the only skill that reads
this vocabulary. It exists here rather than inline so the mapping can be
printed on request (`pr-handle_review legend`) without loading the whole
skill, and so a second skill can point here later without restating it.

GitHub's reaction pills are read as a one-click signalling channel on PR
review threads: a fast path alongside a written reply, not a replacement for
one. Only Jason's own reactions carry signal. Anyone else's are ignored, and
`pr-handle_review` reports the ignored count in one line rather than silently
dropping it.

## The mapping

| Emoji | Name | Verdict | What the skill does |
|---|---|---|---|
| 👍 | Accept | Valid | Endorsement, overridable by evidence. Verify anyway. |
| ❤️ | Pattern | Valid | As 👍, plus: an excellent fix Jason hadn't considered. Sweep forward for other sites where the same **solution** would apply. |
| 👎 | Reject | Invalid | Draft pushback with `file:line` counter-evidence. |
| 🚀 | Defer | Valid, out of scope | Right place, later. Track it; offer a roadmap entry if one exists. |
| 🎉 | Done | No action | Already handled and satisfying. Acknowledge, change nothing, still reply. |
| 👀 | Scrutinise | No prior | Verify hard. Never shortcut, never cluster into a shared subagent. |
| 😄 | Missed it | Valid, elevated | "I can't believe I missed this." Sweep backward for other sites carrying the same **defect**. |
| 😕 | Unclear | No prior | Don't guess. Surface at Gate 1 as a question for Jason. |

Unlisted or absent reaction means no signal, never inferred.

## Why ❤️ and 😄 aren't the same signal

Both start from "this fix is right", so the difference has to live in what
each one searches for afterwards. ❤️ generalises the *solution*: it looks for
sites that are currently fine but would benefit from the same fix. 😄
generalises the *bug*: it looks for sites that are currently broken by the
same defect. The reply differs accordingly: a ❤️ reply lists candidate sites
for the pattern; a 😄 reply lists confirmed instances of the defect and says
why the class was missed the first time. If a sweep under either signal turns
up nothing, say so rather than omitting the section.

## Whose reaction counts

Only reactions whose reactor login matches the authenticated login from
`gh api user --jq .login`. Use login comparison, not GraphQL's
`viewerHasReacted`: the two give the same answer when the skill runs as
Jason, but login comparison stays explicit about whose signal was read and
lets the skill name what it ignored.

`Reactor` is a GraphQL union over `User`, `Bot`, `Organization` and
`Mannequin`. Only `User` carries a `login`; any other type parses as "not
Jason" rather than being treated as an error.

## Conflicting and layered signals

Two or more of Jason's reactions on the same comment collapses to 😕 Unclear:
surface both at Gate 1, never pick one.

A text reply is more specific than a reaction, so text wins when both sit on
the same thread. The one exception: if the reaction is on a comment that
comes *after* Jason's last reply, the reaction is the fresher signal and the
thread becomes a live disagreement carried to Gate 1 rather than resolved
either way. This is derived from comment position, not from reaction
timestamps: see the hard caveat below.

Review bodies (`gh pr view --json reviews`) carry no reaction signal. One
review body can produce several extracted asks, and a single body-level
reaction can't say which ask it targets. Where precision matters, react on
the thread comment instead.

## Hard caveats

Verified against the live GitHub GraphQL API, 2026-09-17, against
`JasonWarrenUK/goblin-mode` PR 18. Re-verify if `reactionGroups` behaviour
changes.

- **`reactionGroups` always returns all 8 groups**, one per `ReactionContent`
  enum value, whether or not anyone has used them. An unused group has an
  empty `reactors` list. Never treat group presence as a signal; test
  `reactors.totalCount > 0`.
- `ReactionContent` has exactly 8 values: `THUMBS_UP` `THUMBS_DOWN` `LAUGH`
  `HOORAY` `CONFUSED` `HEART` `ROCKET` `EYES`.
- `ReactionGroup.createdAt` is the group's first reaction time, not a
  per-reactor timestamp. It cannot be used to order a reaction against a
  reply with any reliability. Precedence rules here are static (text beats
  reaction, with the one comment-position exception above), never
  timestamp-derived.
- Page `reactors` generously (50 is enough for a single-maintainer repo) and
  read `totalCount`, so a reaction can't silently fall off the end of a page.
- This vocabulary is disjoint from the `pr-review` family's severity taxonomy
  (🔴🟠🟡🟣) and delta vocabulary (⚪⚫🟢), and from its banned set
  (🆕✅⚠️, `partition-findings.mjs`). No collision, no shared meaning.
