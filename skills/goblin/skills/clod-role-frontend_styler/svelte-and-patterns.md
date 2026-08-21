# Svelte Specifics and CSS Patterns

## Contents
- Svelte-specific guidelines (scoped styles, :global, custom properties, reactive classes)
- Common patterns (flexbox, grid, component structure)
- Anti-patterns to avoid
- External references

## Svelte-Specific Guidelines

### Component-Scoped Styles
Svelte's `<style>` blocks are scoped by default - leverage this:

```svelte
<style>
  /* Scoped automatically - no class name collisions */
  .button {
    padding: 0.5rem 1rem;
    border-radius: 0.25rem;
  }

  .button--primary {
    background: var(--color-primary);
  }
</style>
```

### Global Styles
Use `:global()` sparingly and intentionally:

```svelte
<style>
  /* Only when deliberately styling external elements */
  :global(.markdown-content h1) {
    margin-top: 2rem;
  }
</style>
```

### CSS Custom Properties
Prefer CSS variables for theming and consistency:

```svelte
<style>
  .card {
    background: var(--card-bg, #fff);
    border: 1px solid var(--card-border, #e5e7eb);
    border-radius: var(--radius-md, 0.5rem);
  }
</style>
```

### Reactive Classes
Use Svelte's class directive for dynamic styling:

```svelte
<button
  class="btn"
  class:btn--active={isActive}
  class:btn--disabled={disabled}
>
  Click me
</button>
```

## Common Patterns

### Flexbox Layouts
```css
/* Center content */
.container {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Responsive row to column */
.flex-container {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}
```

### Grid Layouts
```css
/* Responsive grid */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}
```

### Component Structure
```svelte
<script>
  // Logic
</script>

<div class="component">
  <!-- Template -->
</div>

<style>
  .component {
    /* Styles scoped to component */
  }
</style>
```

## Anti-Patterns to Avoid

### Don't: Mix Styling Approaches
```svelte
<!-- ✗ Bad: Mixing inline styles with classes -->
<div class="card" style="margin: 10px;">
```

### Don't: Over-Nest Selectors
```css
/* ✗ Bad: Deep nesting */
.container .wrapper .card .header .title {
  font-size: 1.5rem;
}

/* ✓ Good: Flat structure */
.card-title {
  font-size: 1.5rem;
}
```

### Don't: Use `!important` Without Cause
```css
/* ✗ Bad: Using important as a crutch */
.button {
  color: red !important;
}

/* ✓ Good: Increase specificity properly */
.card .button {
  color: red;
}
```

### Don't: Hard-Code Values Repeatedly
```css
/* ✗ Bad: Repeated magic numbers */
.card { padding: 16px; }
.modal { padding: 16px; }
.panel { padding: 16px; }

/* ✓ Good: Use variables */
:root {
  --spacing-md: 1rem;
}
.card, .modal, .panel {
  padding: var(--spacing-md);
}
```

## References

For deeper dives into specific topics:
- [Svelte Style Docs](https://svelte.dev/docs/svelte-components#style)
- [CSS Tricks Flexbox Guide](https://css-tricks.com/snippets/css/a-guide-to-flexbox/)
- [CSS Tricks Grid Guide](https://css-tricks.com/snippets/css/complete-guide-grid/)
- [BEM Naming Convention](http://getbem.com/naming/)
