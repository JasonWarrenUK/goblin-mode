<script lang="ts">
	// The Real Thing: a skill from this repository that makes the level's moves, on the
	// same grid as the stage above it, with its callouts in the margins when there is room.
	import { onMount } from 'svelte';
	import Specimen from './Specimen.svelte';
	import { toneMarks, type ShownCallout } from '#lib/content/tutorial-view.ts';
	import type { Level } from '#lib/content/tutorial.types.ts';

	interface Props {
		level: Level;
		real: NonNullable<Level['realThing']>;
	}

	let { level, real }: Props = $props();

	const labels = $derived(real.callouts.map((callout) => callout.label));
	const callouts = $derived<ShownCallout[]>(real.callouts.map((callout) => ({ ...callout, past: false, tone: 'tr' })));
	let margins = $state(false);
	let tab = $state(0);

	onMount(() => {
		const wide = matchMedia('(min-width: 1100px)');
		const update = (): void => {
			margins = wide.matches;
		};
		update();
		wide.addEventListener('change', update);
		return () => wide.removeEventListener('change', update);
	});
</script>

<article class="sheet alt real" aria-labelledby="real-h">
	<div class="real-text">
		<h2 id="real-h">The Real Thing</h2>
		<p>{@html toneMarks(real.intro, level, labels)}</p>
		{#each real.after ?? [] as paragraph, index (index)}
			<p>{@html toneMarks(paragraph, level)}</p>
		{/each}
	</div>
	<div class="real-specimen">
		<Specimen {level} files={real.files} {callouts} layout={margins ? 'margins' : 'list'} bind:tab />
	</div>
</article>
