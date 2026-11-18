<script lang="ts">
	// Placeholder until each explainer is reworked with Jason (scope S2 to S4).
	import { skillsIndex } from '#lib/paths.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<svelte:head>
	<title>{data.page.title} · Goblin Mode</title>
</svelte:head>

<main class="desk">
	<section class="sheet placeholder" aria-labelledby="page-title">
		<p class="back"><a href={skillsIndex()}>Back to Build Your Own</a></p>
		<h1 id="page-title">{data.page.title}</h1>
	</section>
</main>

<style>
	.placeholder { padding: 2rem clamp(1.25rem, 3vw, 2.5rem); }
	h1 { font-size: clamp(2.2rem, 5vw, 3.6rem); margin: 0.5rem 0 1rem; }
	.back { margin: 0; font-family: var(--font-print); }
</style>
