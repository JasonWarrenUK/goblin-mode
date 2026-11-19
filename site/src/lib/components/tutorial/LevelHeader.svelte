<script lang="ts">
	// The level's header: its place among the five, its title and its intro. A key to the
	// step colours follows. It scrolls away above the stage.
	import { stepTone, toneMarks } from '#lib/content/tutorial-view.ts';
	import type { Level } from '#lib/content/tutorial.types.ts';
	import { tutorialIndex, tutorialLevel } from '#lib/paths.ts';

	interface Props {
		level: Level;
		levels: readonly Pick<Level, 'n' | 'title'>[];
	}

	let { level, levels }: Props = $props();
</script>

<nav class="level-nav" aria-label="Levels">
	<p><a href={tutorialIndex()}>Some Assembly Required</a> · Level {level.n} of {levels.length}</p>
	<ol class="level-tabs">
		{#each levels as other (other.n)}
			<li><a href={tutorialLevel(other.n)} title={`Level ${other.n}: ${other.title}`} aria-current={other.n === level.n ? 'page' : undefined}>{other.n}</a></li>
		{/each}
	</ol>
</nav>

<header class="sheet lvl-head">
	<p class="kicker">Some Assembly Required · Level {level.n} of {levels.length}</p>
	<h1>{level.title}</h1>
	<p class="lede">{@html toneMarks(level.intro, level)}</p>
	<p class="key">
		Colour key:
		{#each level.steps as step, index (step.id)}
			<mark class={stepTone(index)}>{step.id} {step.title}</mark>{' '}
		{/each}
	</p>
	<p class="how">Scroll and the sheet below builds the files one step at a time, pinning each step's notes. One scroll moves one step; the step buttons, the arrow keys or j and k do the same.</p>
</header>
