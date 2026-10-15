# Web design principles

Agreed by Jason on 15 October 2026, distilled from the 2RT.25 review of the CHIRPdb review tool (PR #178). Read by `web-check` and by the `web-principles` agent.

**Amending this file.** The agent may propose an amendment or an addition after a check, with the observation that prompted it. Nothing is written here without Jason's approval in the conversation. An approved change is added below with its date and the task it came from; a principle is never deleted, only marked `Retired` with the reason.

## Before drawing

1. **Inventory first.** List every region's content before any layout: what it holds, how many, which actions. The layout falls out of the inventory.
2. **Lay out by what each region holds, never by a template.** Short field lists pair up side by side, long homogeneous lists become rows, dense sets become a grid of cards and one long column is the fallback only when nothing else fits.

## On the page

3. **State in form, never in prose.** A stripe on the edge, a chip, a tinted band. The one state nobody may miss gets a full-width band in its own colour.
4. **One fixed toolbar per repeating item.** Every repeating item gets one toolbar, in the same place on every item, holding the same controls in the same order. Opening anything from that toolbar (a note field, an editor, a confirmation) adds a new row beneath the item; it never grows the toolbar's own cell, so the buttons stay where the hand last found them. Test: open the optional field on one item and watch the buttons; if they moved, the toolbar is not fixed.
5. **One element per question.** When two elements would answer related questions ("where is X" and "how far along is X"), merge them into one that answers both, rather than adding a second element that repeats what the first already lists. The section map that carries each section's count and state bar is one instance; a breadcrumb that shows the step's status, or a tab strip with per-tab counts, are others.

## Process

6. **Draw the proposal in the product's own tokens** with numbered callouts mapped back to the observations they answer, so approval of the picture is the build spec.
7. **Observations live in a shared store** with a status and a resolution line; every pass closes the loop by writing back, and the next pass starts from what is still open.
8. **Find out which devices and viewports the product is meant for before verifying anything**: the scope document, the client's brief, analytics where they exist or a direct question. Then verify every page on each of them, including every open state (forms, disclosures, drawers).
9. **Watch for class-name collisions with the UI library in use**; a stray dot or blank column is the symptom.

## Copy and first screens

10. **Copy is briefed before it is written.** Before any user-facing wording, establish with Jason who it addresses, what register and mood it carries and what it may state outright and what it must leave unsaid (some products state their purpose baldly; in others that would wreck the mood). Every page's copy is then checked against that brief, read once as each audience it names. No assumption about purpose, audience or tone is made where the brief is silent: ask.
11. **The first screen is the map, when the trigger holds.** Trigger: the page's content runs past one screen on the intended device, and the reader arrives to choose where to work rather than to read in order (a review queue, a record with many sections, a dashboard). Then long lists start folded, counts and state summaries stay visible and the reader chooses what to open. Not triggered: a page with one job (a sign-in, a form, a settings screen), a narrative meant to be read top to bottom, or a list that already fits the screen; folding those adds a click for nothing.

## How each principle is checked

| Principle | Mechanical (script) | Judgement (agent) |
|---|---|---|
| 1, 2 | | Inventory present in the scope or artefact index; each region's layout justified by its row |
| 3 | | No state carried only by a sentence |
| 4 | Toolbar control positions measured before and after opening each optional field | Same controls, same order, on every item |
| 5 | | No two elements answering the same question |
| 6 | Wireframe `:root` matches the product's; every callout number has a target | Callouts answer the observations they cite |
| 7 | Export present and no older than the last pass; every non-open entry has a resolution | |
| 8 | Device list declared; every route captured on every device | Open states covered, not only closed ones |
| 9 | Product class names intersected with the UI library's | |
| 10 | Copy brief present when user-facing copy was written | Each page read once as each audience |
| 11 | | Trigger judged per page; folding present or absent accordingly |

## Amendments

| Date | Task | Change |
|---|---|---|
| 2026-10-15 | CHIRPdb 2RT.25 | Initial eleven, all agreed |
