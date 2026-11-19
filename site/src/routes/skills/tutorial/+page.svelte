<script lang="ts">
	import { TUTORIAL } from '#lib/content/tutorial.ts';
	import { skillsIndex, tutorialLevel } from '#lib/paths.ts';
	import '#lib/styles/tutorial.css';
</script>

<svelte:head>
	<title>Some Assembly Required · Goblin Mode</title>
</svelte:head>

<main class="desk tutorial">
	<p class="back"><a href={skillsIndex()}>Back to Build Your Own</a></p>
	<header class="sheet lvl-head">
		<p class="kicker">Build Your Own</p>
		<h1>Some Assembly Required</h1>
		<p class="lede">One skill, built up over five levels. Each level adds to the files the last one left.</p>
	</header>
	<ol class="levels">
		{#each TUTORIAL as level, index (level.n)}
			<li class={['sheet', 'level', index % 2 === 1 && 'alt']}>
				<p class="kicker">Level {level.n} of {TUTORIAL.length}</p>
				<h2><a href={tutorialLevel(level.n)}>{level.title}</a></h2>
				<p>{@html level.intro}</p>
			</li>
		{/each}
	</ol>
</main>

<style>
	.back { margin: 0; font-family: var(--font-print); }
	.levels { list-style: none; margin: 0; padding: 0; display: grid; gap: 1.25rem; }
	.level { padding: 1.25rem clamp(1rem, 3vw, 2rem); display: grid; gap: 0.5rem; }
	.level.alt { border-radius: var(--wonk-2); }
	h2 { font-size: clamp(1.5rem, 3vw, 2rem); }
	h2 a { color: inherit; text-decoration-thickness: 2px; }
	.level :global(code) { font-family: var(--font-mono); font-size: 0.86em; background: var(--surface-raised); padding: 0 0.25em; border-radius: var(--radius-sm); }
	.level :global(mark) { background: none; color: inherit; }
</style>
