<script lang="ts">
	// The level's exercise on a torn slip, its answer folded away.
	import CodePanel from './CodePanel.svelte';
	import { toneMarks } from '#lib/content/tutorial-view.ts';
	import type { StagePage } from '#lib/content/tutorial.types.ts';

	interface Props {
		level: StagePage;
	}

	let { level }: Props = $props();
	const exercise = $derived(level.exercise);
</script>

<aside class="slip torn exercise" aria-labelledby="exercise-h">
	<h2 id="exercise-h">{exercise.title}</h2>
	{#each exercise.prompt as paragraph, index (index)}
		<p>{@html toneMarks(paragraph, level)}</p>
	{/each}
	<details>
		<summary>Show the answer</summary>
		{#each exercise.answer as part, index (index)}
			{#if 'prose' in part}
				<p>{@html toneMarks(part.prose, level)}</p>
			{:else if 'table' in part}
				<div class="answer-table">
					<table>
						<thead><tr>{#each part.table.head as cell, c (c)}<th scope="col">{@html toneMarks(cell, level)}</th>{/each}</tr></thead>
						<tbody>
							{#each part.table.rows as row, r (r)}
								<tr>{#each row as cell, c (c)}{#if c === 0}<th scope="row">{@html toneMarks(cell, level)}</th>{:else}<td>{@html toneMarks(cell, level)}</td>{/if}{/each}</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<div class="file">
					<CodePanel file={{ path: 'answer', lang: part.lang, text: part.code }} markAdded={false} />
				</div>
			{/if}
		{/each}
	</details>
</aside>
