<script lang="ts">
	import type { Situation } from '#lib/content/mod-files.types.ts';

	interface Props {
		situation: Situation;
		/** Fills the count placeholders in the copy. */
		fill: (text: string) => string;
	}

	let { situation, fill }: Props = $props();
</script>

<details class="sheet situation" id={situation.id}>
	<summary>
		<span class="cnum">{situation.num}</span>
		<h2>{situation.title}</h2>
		<p class="hint">{@html fill(situation.hint)}</p>
	</summary>
	<p class="slip scene">{@html fill(situation.scene)}</p>
	<div class="versus">
		<div class="side before">
			<h3>How Human Suffer Before</h3>
			<ol>
				{#each situation.before as line, index (index)}<li>{@html fill(line)}</li>{/each}
			</ol>
		</div>
		<div class="side slip with">
			<h3>{situation.withHeading}</h3>
			<ol>
				{#each situation.with as line, index (index)}<li>{@html fill(line)}</li>{/each}
			</ol>
		</div>
	</div>
	<div class="ruling">
		<span class="label">Goblin Ruling (Is Final)</span>
		<p>{@html fill(situation.ruling)}</p>
	</div>
</details>

<style>
	.situation { padding: 0 clamp(1rem, 3vw, 2rem); scroll-margin-top: 1rem; }
	.situation[open] { padding-bottom: 1.5rem; }
	.situation[open] > :not(summary) { margin-top: 1rem; }
	summary {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto;
		column-gap: 0.75rem;
		align-items: baseline;
		cursor: pointer;
		padding: 1rem 0;
		list-style: none;
	}
	summary::-webkit-details-marker { display: none; }
	summary::after {
		content: '\25B8';
		grid-column: 3;
		grid-row: 1;
		font-size: 1.2rem;
		color: var(--accent);
		transition: transform 120ms ease;
	}
	.situation[open] summary::after { transform: rotate(90deg); }
	.cnum { grid-row: 1 / span 2; font-family: var(--font-marker); color: var(--accent); font-size: 1.15rem; }
	h2 { grid-column: 2; font-size: clamp(1.5rem, 3vw, 2rem); }
	.hint { grid-column: 2; margin: 0; color: var(--ink-muted); font-size: 0.95rem; }
	.scene { margin: 0; padding: 0.8rem 1rem; transform: rotate(-0.4deg); }
	.versus { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 1rem 1.25rem; align-items: start; }
	h3 {
		font-family: var(--font-print);
		font-weight: 600;
		font-size: 0.75rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		margin: 0 0 0.5rem;
	}
	ol { margin: 0; padding-left: 1.2rem; display: grid; gap: 0.45rem; }
	.before {
		background: var(--surface-raised);
		padding: 1rem;
		border-radius: var(--radius-md);
		font-family: var(--font-marker);
		line-height: 1.45;
		color: var(--ink);
	}
	.before h3 { color: var(--ink-muted); }
	.with { padding: 1rem; font-size: 0.95rem; }
	.with h3 { color: var(--slip-accent-2); }
	.with :global(code) { color: var(--slip-accent); font-size: 0.88em; }
	.ruling { display: grid; gap: 0.25rem; border-top: 2px dashed var(--line); padding-top: 0.9rem; }
	.label {
		justify-self: start;
		background: var(--slime);
		color: var(--on-slime);
		font-family: var(--font-print);
		font-weight: 600;
		font-size: 0.72rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		padding: 0.05rem 0.4rem;
	}
	.ruling p { margin: 0; font-family: var(--font-marker); color: var(--accent-2); font-size: 1.08rem; }
	@media (max-width: 760px) {
		.versus { grid-template-columns: minmax(0, 1fr); }
	}
	@media (prefers-reduced-motion: reduce) {
		summary::after { transition: none; }
	}
</style>
