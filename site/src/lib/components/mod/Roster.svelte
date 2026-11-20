<script lang="ts">
	import type { RosterRow, Situation } from '#lib/content/mod-files.types.ts';

	interface Props {
		name: string;
		rows: readonly RosterRow[];
		situations: readonly Situation[];
		fill: (text: string) => string;
	}

	let { name, rows, situations, fill }: Props = $props();
	const idOf = (num: string): string | undefined => situations.find((situation) => situation.num === num)?.id;
</script>

<aside class="slip torn roster" aria-labelledby="roster-title">
	<h2 id="roster-title">Everything {name} Does</h2>
	<table>
		<tbody>
			{#each rows as row, index (index)}
				{@const id = row.where ? idOf(row.where) : undefined}
				<tr class:missing={!row.shown}>
					<td class="box" aria-label={row.shown ? 'shown' : 'not shown'}>{row.shown ? '☑' : '☐'}</td>
					<td>{@html fill(row.text)}{#if row.planned} <span class="stamp proposed inline">Not built yet</span>{/if}</td>
					<td class="where">{#if id}<a href={`#${id}`}>{row.where}</a>{:else}no scene{/if}</td>
				</tr>
			{/each}
		</tbody>
	</table>
</aside>

<style>
	.roster { position: sticky; top: 1rem; padding: 1.4rem 1.1rem 1.1rem; transform: rotate(0.6deg); --rag: var(--rag-b); }
	h2 {
		font-family: var(--font-print);
		font-weight: 600;
		font-size: 0.8rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--slip-accent);
		margin-bottom: 0.6rem;
	}
	table { border-collapse: collapse; width: 100%; font-size: 0.82rem; }
	td { padding: 0.3rem 0.25rem; border-bottom: 1px solid var(--slip-line); vertical-align: top; }
	.box { width: 1.1rem; font-family: var(--font-mono); }
	.where { white-space: nowrap; text-align: right; font-family: var(--font-mono); }
	.missing { color: var(--ink-muted); }
	td :global(code) { color: var(--slip-accent); font-size: 0.9em; }
	@media (max-width: 760px) {
		.roster { position: static; transform: none; }
	}
</style>
