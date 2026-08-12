# Component Patterns

Detail for `svelte-ninja` — slots and composition.

## Slot Patterns

**Basic slot**:
```svelte
<!-- Card.svelte -->
<div class="card">
	<slot />
</div>
```

**Named slots**:
```svelte
<!-- Modal.svelte -->
<div class="modal">
	<header>
		<slot name="header" />
	</header>
	<main>
		<slot />
	</main>
	<footer>
		<slot name="footer" />
	</footer>
</div>
```

**Usage**:
```svelte
<Modal>
	<svelte:fragment slot="header">
		<h2>Title</h2>
	</svelte:fragment>
	
	<p>Content here</p>
	
	<svelte:fragment slot="footer">
		<button>Close</button>
	</svelte:fragment>
</Modal>
```

**Slot props**:
```svelte
<!-- List.svelte -->
<script>
	let { items } = $props();
</script>

<ul>
	{#each items as item}
		<li>
			<slot {item} />
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
