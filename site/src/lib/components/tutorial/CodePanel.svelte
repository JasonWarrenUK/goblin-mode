<script lang="ts">
	// One file on an exhibit panel: a block per line so wrapped lines hang under the
	// gutter, folds as one "..." line and, in the live stage, removed lines struck through.
	import { shownLines, type Tone } from '#lib/content/tutorial-view.ts';
	import type { FileView } from '#lib/content/tutorial.types.ts';

	interface Props {
		file: FileView;
		/** The tone of each line, by the step that added it. */
		tones?: (Tone | null)[];
		/** The live stage: removed lines show and new lines fade in. */
		live?: boolean;
		/** Marks this step's added lines as new. */
		markAdded?: boolean;
		/** Line number to the label of the callout pointing at it, and whether that callout is an earlier step's. */
		labels?: Map<number, { label: string; past: boolean; tone: Tone | null }>;
	}

	let { file, tones, live = false, markAdded = true, labels }: Props = $props();

	const lines = $derived(shownLines(file, tones, live));
</script>

<pre class="code"><code
	>{#each lines as line, index (index)}{#if line.kind === 'line'}{@const pin = labels?.get(line.n)}<span
				class={['ln', line.tone, markAdded && line.added && 'cur new', live && markAdded && line.added && 'fresh', pin?.past && 'pastpin', pin && !line.tone && pin.tone]}
				data-n={line.n}
				data-label={pin?.label}>{line.text}</span
			>{:else if line.kind === 'fold'}<span class="ln fold" data-fold="{line.from}-{line.to}"
				>...<span class="visually-hidden"> lines {line.from} to {line.to} left out</span></span
			>{:else}<span class="ln del"><span class="visually-hidden">Removed: </span>{line.text}</span>{/if}{/each}</code
></pre>
