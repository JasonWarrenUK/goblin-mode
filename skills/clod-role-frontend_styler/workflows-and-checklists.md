# Workflows and Checklists

## Contents
- Layout debugging workflow (root cause → fix location → systematic application)
- Style consistency workflow (analyse → identify → propose → execute)
- Accessibility checklist
- Debugging checklist

## Layout Debugging Workflow

### Step 1: Identify Root Cause
Common layout issues and their causes:

**Alignment Problems:**
- Check parent container's `display` property (flex/grid/block)
- Verify `align-items`, `justify-content`, `align-self`
- Check for unexpected margins/padding
- Look for `position: absolute` breaking flow

**Spacing Issues:**
- Examine margin collapse behaviour
- Check for inconsistent spacing units
- Look for `box-sizing` mismatches
- Verify padding vs margin usage

**Responsive Breakage:**
- Check media query breakpoints
- Verify `min-width` vs `max-width` logic
- Look for fixed widths instead of flexible units
- Check for overflow issues

**Z-Index Conflicts:**
- Verify stacking context creation
- Check `position` property (relative/absolute/fixed)
- Look for competing `z-index` values
- Examine parent-child z-index relationships

### Step 2: Determine Fix Location
Ask: "Should this be fixed in the component or its parent?"

**Fix in Component When:**
- Issue is internal to component layout
- Component violates its own design contract
- Changes won't affect siblings or parent

**Fix in Parent When:**
- Issue involves multiple children
- Problem is container-level (flexbox/grid)
- Fix benefits component reusability

### Step 3: Apply Fixes Systematically
1. Start with structural changes (display, position, layout)
2. Then spacing (margin, padding, gap)
3. Then sizing (width, height, flex-grow/shrink)
4. Finally visual polish (borders, shadows, etc.)

## Style Consistency Workflow

### Step 1: Analyse Current Implementation
Check for:
- **Naming conventions** - BEM, utility classes, or other patterns
- **Styling location** - Component `<style>` vs external CSS
- **Value patterns** - Hard-coded vs CSS variables
- **Units** - rem, px, em usage patterns
- **Responsiveness** - Media query patterns

### Step 2: Identify Inconsistencies
Compare component styling against project patterns:

```
✗ Inconsistent: <div class="cardContainer">
✓ Consistent:   <div class="card-container">

✗ Inconsistent: padding: 8px;
✓ Consistent:   padding: 0.5rem;

✗ Inconsistent: background: #3B82F6;
✓ Consistent:   background: var(--color-primary); /* → --color-azure-3 */
```

### Step 3: Propose Changes
List specific changes needed to match project patterns:
- "Replace hard-coded colors with CSS variables"
- "Convert class names from camelCase to kebab-case"
- "Move inline styles to component `<style>` block"
- "Use rem units instead of px for spacing"

### Step 4: Execute After Approval
Apply changes in logical order:
1. CSS files first (if applicable)
2. Child components
3. Parent component last

## Accessibility Checklist

When building or reviewing UI components:

- [ ] Does every interactive element have a visible focus indicator?
- [ ] Does the colour contrast pass WCAG 2.1 AA? (Use browser DevTools audit — or use Reasonable Colors where shade diff ≥ 3 guarantees AA body text)
- [ ] Is information conveyed by more than just colour?
- [ ] Are all images/icons either decorative (`aria-hidden`) or labelled (`alt`/`aria-label`)?
- [ ] Do form inputs have associated `<label>` elements?
- [ ] Are error messages linked to inputs via `aria-describedby`?
- [ ] Does the component work with keyboard only (Tab, Enter, Escape)?
- [ ] Does `prefers-reduced-motion` disable animations?
- [ ] Are touch targets at least 44×44px?
- [ ] Is text readable at 200% zoom without horizontal scrolling?

## Debugging Checklist

When encountering styling issues, verify:

- [ ] Is `box-sizing: border-box` set globally?
- [ ] Are there competing CSS specificity issues?
- [ ] Is the element in the correct stacking context?
- [ ] Are flexbox/grid properties on the correct element (parent vs child)?
- [ ] Are units consistent (rem vs px vs em)?
- [ ] Does the issue exist at all breakpoints?
- [ ] Are CSS variables defined and accessible?
- [ ] Is the component's `<style>` block scoped correctly?
- [ ] Are there any typos in class names or property names?
- [ ] Is the browser's developer tools showing overridden styles?
