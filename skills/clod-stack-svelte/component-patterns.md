# Component Patterns

Detail for `clod-stack-svelte`: slots and composition.

## Snippet Patterns

Svelte 5 replaces slots with snippets: `{@render children()}` on the creation side, `{#snippet name()}...{/snippet}` on the usage side.

**Basic content**:
```svelte
<!-- Card.svelte -->
<script>
	let { children } = $props();
</script>

<div class="card">
	{@render children()}
</div>
```

**Named snippets**:
```svelte
<!-- Modal.svelte -->
<script>
	let { header, children, footer } = $props();
</script>

<div class="modal">
	<header>
		{@render header?.()}
	</header>
	<main>
		{@render children()}
	</main>
	<footer>
		{@render footer?.()}
	</footer>
</div>
```

**Usage**:
```svelte
<Modal>
	{#snippet header()}
		<h2>Title</h2>
	{/snippet}

	<p>Content here</p>

	{#snippet footer()}
		<button>Close</button>
	{/snippet}
</Modal>
```

**Snippet parameters** (replaces slot props):
```svelte
<!-- List.svelte -->
<script>
	let { items, children } = $props();
</script>

<ul>
	{#each items as item}
		<li>
			{@render children(item)}
		</li>
	{/each}
</ul>
```

**Usage**:
```svelte
<List items={users}>
	{#snippet children({ item })}
		<strong>{item.name}</strong>
	{/snippet}
</List>
```

## Composition Patterns

**Compound components**:
```svelte
<!-- Tabs.svelte -->
<script>
	let { children } = $props();
	let activeTab = $state(0);
	
	export function setActive(index) {
		activeTab = index;
	}
</script>

<div class="tabs">
	{@render children({ activeTab, setActive })}
</div>
```

**Higher-order components**:
```javascript
// withAuth.js
export function withAuth(Component) {
	return (props) => {
		const { user } = useAuth();
		if (!user) return 'Please log in';
		return new Component({ ...props, user });
	};
}
```
