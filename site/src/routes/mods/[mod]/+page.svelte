<script lang="ts">
	// Placeholder until the mod page is wireframed and approved (scope M1 to M3).
	import { home } from '$lib/paths';
	import { modSummary } from '$lib/content/mods';
	import { facts } from '$lib/facts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const mod = $derived(modSummary(facts, data.key));
</script>

<svelte:head>
	<title>{mod.name} · Goblin Mode</title>
</svelte:head>

<main class="desk">
	<section class="sheet placeholder" aria-labelledby="mod-title">
		<p class="back"><a href={home()}>Back to the desk</a></p>
		<h1 id="mod-title">{mod.name}</h1>
		<p>{mod.tagline}</p>
	</section>
</main>

<style>
	.placeholder { padding: 2rem clamp(1.25rem, 3vw, 2.5rem); }
	h1 { font-size: clamp(2.2rem, 5vw, 3.6rem); margin: 0.5rem 0 1rem; }
	.back { margin: 0; font-family: var(--font-print); }
</style>
