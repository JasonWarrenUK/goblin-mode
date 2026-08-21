# Diff Review Template

Use this template when the playground is about reviewing code diffs: git commits, pull requests, code changes with interactive line-by-line commenting for feedback.

## Layout

```
+-------------------+----------------------------------+
|                   |                                  |
|  Commit Header:   |  Diff Content                    |
|  • Hash           |  (files with hunks)              |
|  • Message        |  with line numbers               |
|  • Author/Date    |  and +/- indicators              |
|                   |                                  |
+-------------------+----------------------------------+
|  Prompt Output Panel (fixed bottom-right)            |
|  [ Copy All ]                                        |
|  Shows all comments formatted for prompt             |
+------------------------------------------------------+
```

Diff review playgrounds display git diffs with syntax highlighting. Users click lines to add comments, which become part of the generated prompt for code review feedback.

## Control types for diff review

| Feature | Control | Behavior |
|---|---|---|
| Line commenting | Click any diff line | Opens textarea below the line |
| Comment indicator | Badge on commented lines | Shows which lines have feedback |
| Save/Cancel | Buttons in comment box | Persist or discard comment |
| Copy prompt | Button in prompt panel | Copies all comments to clipboard |

## Diff rendering

Parse diff data into structured format for rendering:

```javascript
const diffData = [
  {
    file: "path/to/file.py",
    hunks: [
      {
        header: "@@ -41,13 +41,13 @@ function context",
        lines: [
          { type: "context", oldNum: 41, newNum: 41, content: "unchanged line" },
          { type: "deletion", oldNum: 42, newNum: null, content: "removed line" },
          { type: "addition", oldNum: null, newNum: 42, content: "added line" },
        ]
      }
    ]
  }
];
```

## Line type styling

| Type | Background | Text Color | Prefix |
|---|---|---|---|
| `context` | transparent | default | ` ` (space) |
| `addition` | green-tinted, from the palette's semantic tokens | green, from the palette's semantic tokens | `+` |
| `deletion` | red-tinted, from the palette's semantic tokens | red, from the palette's semantic tokens | `-` |
| `hunk-header` | blue-tinted, from the palette's semantic tokens | blue, from the palette's semantic tokens | `@@` |

Colour roles only, not literal values: source the actual hex/RC values from `~/.claude/library/references/artefact-conventions.md`'s palette rules, per the Theme support section below.

## Comment system

Each diff line gets a unique identifier for comment tracking:

```javascript
const comments = {}; // { lineId: commentText }

function selectLine(lineId, lineEl) {
  // Deselect previous
  document.querySelectorAll('.diff-line.selected').forEach(el =>
    el.classList.remove('selected'));
  document.querySelectorAll('.comment-box.active').forEach(el =>
    el.classList.remove('active'));

  // Select new
  lineEl.classList.add('selected');
  document.getElementById(`comment-box-${lineId}`).classList.add('active');
}

function saveComment(lineId) {
  const textarea = document.getElementById(`textarea-${lineId}`);
  const comment = textarea.value.trim();

  if (comment) {
    comments[lineId] = comment;
  } else {
    delete comments[lineId];
  }

  renderDiff(); // Re-render to show comment indicator
  updatePromptOutput();
}
```

## Prompt output format

Generate a structured code review format:

```javascript
function updatePromptOutput() {
  const commentKeys = Object.keys(comments);

  if (commentKeys.length === 0) {
    promptContent.innerHTML = '<span class="no-comments">Click on any line to add a comment...</span>';
    return;
  }

  let output = 'Code Review Comments:\n\n';

  commentKeys.forEach(lineId => {
    const lineEl = document.querySelector(`[data-line-id="${lineId}"]`);
    const file = lineEl.dataset.file;
    const lineNum = lineEl.dataset.lineNum;
    const content = lineEl.dataset.content;

    output += `📍 ${file}:${lineNum}\n`;
    output += `   Code: ${content.trim()}\n`;
    output += `   Comment: ${comments[lineId]}\n\n`;
  });

  promptContent.textContent = output;
}
```

## Data attributes for line elements

Store metadata on each line element for prompt generation:

```html
<div class="diff-line addition"
     data-line-id="0-1-5"
     data-file="src/utils/handler.py"
     data-line-num="45"
     data-content="subagent_id = tracker.register()">
```

## Pre-populating with real data

To create a diff viewer for a specific commit:

1. Run `git show <commit> --format="%H%n%s%n%an%n%ad" -p`
2. Parse the output into the `diffData` structure
3. Include commit metadata in the header section

## Theme support

Follow the three-state contract from `~/.claude/library/references/artefact-conventions.md`, not a flat light/dark split. Define semantic tokens on bare `:root` (the light palette), redefine them under `@media (prefers-color-scheme: dark)` guarded as `:root:not([data-theme="light"])`, and redefine them again under `:root[data-theme="dark"]` so an explicit toggle wins in both directions. Every element below (`body`, `.file-card`, `.diff-line.addition`, `.diff-line.deletion`, `.diff-line.hunk-header`) takes its colour from a token, never a literal hex value:

```css
:root {
  --diff-ground: /* RC-sourced, light */;
  --diff-surface: /* RC-sourced, light */;
  --diff-ink: /* RC-sourced, light */;
  --diff-add-bg: /* RC-sourced green tint, light */;
  --diff-del-bg: /* RC-sourced red tint, light */;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --diff-ground: /* RC-sourced, dark */;
    /* ...and so on for every token above */
  }
}

:root[data-theme="dark"] {
  --diff-ground: /* same dark values, wins over an explicit light choice too */;
  /* ...and so on */
}

body { background: var(--diff-ground); color: var(--diff-ink); }
.file-card { background: var(--diff-surface); }
.diff-line.addition { background: var(--diff-add-bg); }
.diff-line.deletion { background: var(--diff-del-bg); }
```

## Interactive features

- **Hover hint:** Show "Click to comment" tooltip on line hover
- **Comment indicator:** Badge (💬) on lines with saved comments
- **Toast notification:** "Copied to clipboard!" feedback on copy
- **Edit existing:** Allow editing previously saved comments

## Example topics

- Git commit review (single commit diff with line comments)
- Pull request review (multiple commits, file-level and line-level comments)
- Code diff comparison (before/after refactoring)
- Merge conflict resolution (showing both versions with annotations)
- Code audit (security review with findings per line)
