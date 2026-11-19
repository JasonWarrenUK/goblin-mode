<script lang="ts">
	// Placeholder until the skills wing is designed with Jason (scope S1 to S4).
	import { home, skillHref } from '#lib/paths.ts';
	import { SKILL_PAGES } from '#lib/content/skills.ts';
</script>

<svelte:head>
	<title>Build Your Own · Goblin Mode</title>
</svelte:head>

<main class="desk">
	<section class="sheet placeholder" aria-labelledby="skills-title">
		<p class="back"><a href={home()}>Back to the desk</a></p>
		<h1 id="skills-title">Build Your Own</h1>
		<ul>
			{#each SKILL_PAGES as page (page.slug)}
				<li><a href={skillHref(page)}>{page.title}</a></li>
			{/each}
		</ul>
	</section>
</main>

<style>
	.placeholder { padding: 2rem clamp(1.25rem, 3vw, 2.5rem); }
	h1 { font-size: clamp(2.2rem, 5vw, 3.6rem); margin: 0.5rem 0 1rem; }
	.back { margin: 0; font-family: var(--font-print); }
</style>
