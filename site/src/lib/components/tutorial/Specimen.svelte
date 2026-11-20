<script lang="ts">
	// The specimen: a state's files, one tab each when there are several, with the
	// callouts that belong to the file on show. In the margins they are placed beside
	// their lines; otherwise they are listed under the file.
	import { tick } from 'svelte';
	import CodePanel from './CodePanel.svelte';
	import { clearCallouts, placeCallouts } from './place.ts';
	import { tabLabels, toneMarks, type ShownCallout, type Tone } from '#lib/content/tutorial-view.ts';
	import type { FileView, StagePage } from '#lib/content/tutorial.types.ts';

	interface Props {
		level: StagePage;
		files: FileView[];
		tones?: Map<string, (Tone | null)[]>;
		callouts: ShownCallout[];
		/** margins: callouts beside their lines (fixed height when `fixed`); list: under the file. */
		layout: 'margins' | 'list';
		/** The pinned stage: the specimen fills a fixed height and never grows. */
		fixed?: boolean;
		/** The live stage: removed lines show, new lines fade in, earlier callouts stay dimmed. */
		live?: boolean;
		/** Changes when the stage moves to another state, so new lines fade in again. */
		stateKey?: string | number;
		/** Which file is on show. */
		tab?: number;
	}

	let { level, files, tones, callouts, layout, fixed = false, live = false, stateKey = 0, tab = $bindable(0) }: Props = $props();

	const active = $derived(files[Math.min(tab, files.length - 1)]!);
	// earlier steps' callouts stay, dimmed, only beside the file in the live margins
	const shown = $derived(callouts.filter((callout) => callout.file === active.path && (!callout.past || (live && layout === 'margins'))));
	const elsewhere = (path: string): ShownCallout[] => callouts.filter((callout) => callout.file === path && !callout.past);
	// a line pointed at twice shows this step's label over an earlier one
	const labels = $derived(new Map([...shown].reverse().map((callout) => [callout.line, { label: callout.label, past: callout.past, tone: callout.tone }])));
	const sideOf = (label: string): 'left' | 'right' => {
		const letter = label.charCodeAt(label.length - 1) - 97;
		const step = Number(label.split('.')[1]?.[0] ?? 0);
		return (letter + step) % 2 === 0 ? 'right' : 'left';
	};
	const names = $derived(tabLabels(files.map((file) => file.path)));
	const activeIndex = $derived(Math.min(tab, files.length - 1));

	let stage = $state<HTMLElement>();

	// After every render that can move a line, measure and place the callouts again.
	const place = async (): Promise<void> => {
		await tick();
		if (!stage) return;
		if (layout === 'margins') placeCallouts(stage, fixed);
		else clearCallouts(stage);
	};
	$effect(() => {
		void [active, shown, layout, fixed, stateKey];
		void place();
	});
	$effect(() => {
		if (!stage || typeof ResizeObserver === 'undefined') return;
		const observer = new ResizeObserver(() => void place());
		observer.observe(stage.querySelector('.code') ?? stage);
		const fonts = document.fonts;
		void fonts?.ready.then(() => void place());
		return () => observer.disconnect();
	});
</script>

{#if files.length > 1}
	<div class={['tabs', layout === 'margins' && 'over-panel']} role="group" aria-label="Files">
		{#each files as file, index (file.path)}
			{@const marks = elsewhere(file.path)}
			<button type="button" class="tab" aria-pressed={index === tab} title={file.path} onclick={() => (tab = index)}>
				<span>{names[index]}</span>
				{#if index !== tab}{#each marks as callout (callout.label)}<span class="marker {callout.tone}">{callout.label}</span>{/each}{/if}
			</button>
		{/each}
	</div>
{:else}
	<p class={['fname', layout === 'margins' && 'over-panel']}>{active.path}</p>
{/if}
<div class={['stage', layout === 'margins' && 'marginal']} bind:this={stage}>
	{#key stateKey}
		<CodePanel file={active} tones={tones?.get(active.path)} {live} {labels} />
	{/key}
	{#if shown.length}
		<ol class="callouts" aria-label="Notes on {names[activeIndex]}">
			{#each shown as callout (callout.label)}
				<li
					class={['co', callout.tone, callout.past && 'past', live && !callout.past && 'fresh']}
					data-label={callout.label}
					data-line={callout.line}
					data-to={callout.to ?? callout.line}
					data-side={sideOf(callout.label)}
				>
					<p><span class="lab">{callout.label}</span> <span class="co-text">{@html toneMarks(callout.html, level)}</span></p>
				</li>
			{/each}
		</ol>
	{/if}
	<svg class="leaders" aria-hidden="true" focusable="false"></svg>
</div>
