# Performance Optimization and Common Patterns

Detail for `svelte-ninja`.

## Performance Optimization

### Lazy Loading Components
```svelte
<script>
	import { onMount } from 'svelte';
	
	let HeavyComponent;
	
	onMount(async () => {
		const module = await import('./HeavyComponent.svelte');
		HeavyComponent = module.default;
	});
</script>

{#if HeavyComponent}
	<svelte:component this={HeavyComponent} />
{/if}
```

### Virtualizing Long Lists
```svelte
<script>
	let items = $state(Array.from({ length: 10000 }, (_, i) => i));
	let scrollTop = $state(0);
	
	const itemHeight = 50;
	const visibleCount = 20;
	
	let visibleItems = $derived(() => {
		const start = Math.floor(scrollTop / itemHeight);
		return items.slice(start, start + visibleCount);
	});
</script>

<div class="viewport" bind:scrollTop>
	<div style="height: {items.length * itemHeight}px">
		<div style="transform: translateY({Math.floor(scrollTop / itemHeight) * itemHeight}px)">
			{#each visibleItems as item}
				<div class="item">{item}</div>
			{/each}
		</div>
	</div>
</div>
```

### Memoizing Expensive Calculations
```svelte
<script>
	let data = $state([/* large dataset */]);
	
	// Automatically memoized
	let processed = $derived.by(() => {
		return data
			.filter(/* expensive filter */)
			.map(/* expensive transform */)
			.sort(/* expensive sort */);
	});
</script>
```

### Avoiding Unnecessary Re-renders
```svelte
<script>
	let todos = $state([
		{ id: 1, text: 'Task 1', done: false }
	]);
	
	// Each todo is keyed, only changed todos re-render
</script>

{#each todos as todo (todo.id)}
	<TodoItem {todo} />
{/each}
```

## Common Patterns

### Form Validation
```svelte
<script>
	let email = $state('');
	let password = $state('');
	
	let errors = $derived.by(() => {
		const errs = {};
		if (!email.includes('@')) errs.email = 'Invalid email';
		if (password.length < 8) errs.password = 'Too short';
		return errs;
	});
	
	let isValid = $derived(Object.keys(errors).length === 0);
</script>

<form>
	<input bind:value={email} />
	{#if errors.email}<span class="error">{errors.email}</span>{/if}
	
	<input type="password" bind:value={password} />
	{#if errors.password}<span class="error">{errors.password}</span>{/if}
	
	<button disabled={!isValid}>Submit</button>
</form>
```

### Modal Management
```svelte
<script>
	let isOpen = $state(false);
	
	$effect(() => {
		if (isOpen) {
			document.body.style.overflow = 'hidden';
		}
		
		return () => {
			document.body.style.overflow = '';
		};
	});
</script>

<button onclick={() => isOpen = true}>Open Modal</button>

{#if isOpen}
	<div class="modal-backdrop" onclick={() => isOpen = false}>
		<div class="modal" onclick={(e) => e.stopPropagation()}>
			<slot />
			<button onclick={() => isOpen = false}>Close</button>
		</div>
	</div>
{/if}
```

### Debounced Input
```svelte
<script>
	let searchQuery = $state('');
	let debouncedQuery = $state('');
	
	$effect(() => {
		const timeout = setTimeout(() => {
			debouncedQuery = searchQuery;
		}, 300);
		
		return () => clearTimeout(timeout);
	});
	
	// Use debouncedQuery for API calls
	$effect(() => {
		if (debouncedQuery) {
			fetch(`/api/search?q=${debouncedQuery}`);
		}
	});
</script>

<input bind:value={searchQuery} placeholder="Search..." />
```
