<script lang="ts">
	// "Metadata Is Whatever I Say It Is" (scope M6 to M12): the tutorial's pinned stage on one
	// page, with The Real Thing and the exercise after it. Counts in the copy come from the build.
	import Exercise from '#lib/components/tutorial/Exercise.svelte';
	import RealThing from '#lib/components/tutorial/RealThing.svelte';
	import TutorialStage from '#lib/components/tutorial/TutorialStage.svelte';
	import { stepTone, toneMarks } from '#lib/content/tutorial-view.ts';
	import { fill } from '#lib/content/fill.ts';
	import { METADATA } from '#lib/content/metadata.ts';
	import { facts } from '#lib/facts.ts';
	import { home, skillsIndex } from '#lib/paths.ts';
	import '#lib/styles/tutorial.css';

	const page = METADATA;
	const real = page.realThing ? { ...page.realThing, intro: fill(page.realThing.intro, facts) } : null;
</script>

<svelte:head>
	<title>{page.title} · Goblin Mode</title>
</svelte:head>

<main id="main" class="desk tutorial">
	<nav class="level-nav" aria-label="Build Your Own">
		<p><a href={skillsIndex()}>Build Your Own</a></p>
	</nav>

	<header class="sheet lvl-head">
		<p class="kicker">Build Your Own</p>
		<h1>{page.title}</h1>
		<p class="lede">{@html toneMarks(page.intro, page)}</p>
		<p class="key">
			Colour key:
			{#each page.steps as step, index (step.id)}
				<mark class={stepTone(index)}>{step.id} {step.title}</mark>{' '}
			{/each}
		</p>
		<p class="how">Scroll and the sheet below builds the files one step at a time, pinning each step's notes. One scroll moves one step; the step buttons, the arrow keys or j and k do the same.</p>
	</header>

	<TutorialStage level={page} name="Metadata" />

	{#if real}
		<RealThing level={page} {real} />
	{/if}

	<Exercise level={page} />

	<nav class="pager" aria-label="Build Your Own">
		<a class="previous" href={skillsIndex()}>← Build Your Own</a>
		<a href={home()}>Back to the desk</a>
		<span></span>
	</nav>
</main>
