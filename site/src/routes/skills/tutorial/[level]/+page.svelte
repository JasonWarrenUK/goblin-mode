<script lang="ts">
	import Exercise from '#lib/components/tutorial/Exercise.svelte';
	import LevelHeader from '#lib/components/tutorial/LevelHeader.svelte';
	import RealThing from '#lib/components/tutorial/RealThing.svelte';
	import TutorialStage from '#lib/components/tutorial/TutorialStage.svelte';
	import { tutorialIndex, tutorialLevel } from '#lib/paths.ts';
	import '#lib/styles/tutorial.css';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const level = $derived(data.level);
	const previous = $derived(data.levels.find((other) => other.n === level.n - 1));
	const next = $derived(data.levels.find((other) => other.n === level.n + 1));
</script>

<svelte:head>
	<title>Level {level.n}: {level.title} · Goblin Mode</title>
</svelte:head>

<main id="main" class="desk tutorial">
	<LevelHeader {level} levels={data.levels} />

	{#key level.n}
		<TutorialStage {level} name={`Level ${level.n}`} />
	{/key}

	{#if level.realThing}
		<RealThing {level} real={level.realThing} />
	{/if}

	<Exercise {level} />

	<nav class="pager" aria-label="Levels">
		{#if previous}<a class="previous" href={tutorialLevel(previous.n)}>← Level {previous.n}: {previous.title}</a>{:else}<span></span>{/if}
		<a href={tutorialIndex()}>All levels</a>
		{#if next}<a class="next" href={tutorialLevel(next.n)}>Level {next.n}: {next.title} →</a>{:else}<span></span>{/if}
	</nav>
</main>
