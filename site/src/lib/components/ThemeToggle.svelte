<script lang="ts">
	import { onMount } from 'svelte';

	type Choice = 'light' | 'system' | 'dark';
	const CHOICES: readonly Choice[] = ['light', 'system', 'dark'];
	const KEY = 'goblin-theme';

	let choice = $state<Choice>('system');

	onMount(() => {
		const current = document.documentElement.dataset.theme;
		choice = current === 'light' || current === 'dark' ? current : 'system';
	});

	const choose = (next: Choice): void => {
		choice = next;
		const root = document.documentElement;
		if (next === 'system') delete root.dataset.theme;
		else root.dataset.theme = next;
		try {
			if (next === 'system') localStorage.removeItem(KEY);
			else localStorage.setItem(KEY, next);
		} catch {
			// Storage refused (private window, blocked site data): the choice holds for this page only.
		}
	};
</script>

<span class="toggle" role="group" aria-label="Colour theme">
	{#each CHOICES as option (option)}
		<button type="button" aria-pressed={choice === option} onclick={() => choose(option)}>{option}</button>
	{/each}
</span>

<style>
	.toggle {
		display: inline-flex;
		border: 2px solid var(--ink);
		border-radius: var(--radius-md);
		overflow: hidden;
		font-family: var(--font-print);
	}
	button {
		all: unset;
		cursor: pointer;
		padding: 0.15rem 0.55rem;
		font-size: 0.8rem;
		color: var(--ink);
	}
	button[aria-pressed='true'] { background: var(--ink); color: var(--surface); }
	button:focus-visible { outline: 3px solid var(--accent); outline-offset: -3px; }
</style>
