<script lang="ts">
	import ThemeToggle from './ThemeToggle.svelte';
	import { countWord, type Facts } from '#lib/facts.ts';

	interface Props {
		facts: Facts;
	}

	let { facts }: Props = $props();
</script>

<section class="sheet notice" aria-labelledby="notice-title">
	<span class="tape" aria-hidden="true"></span>
	<span class="tape right" aria-hidden="true"></span>
	<div class="eyebrow">
		<span>goblin-mode · a marketplace for Claude Code</span>
		<ThemeToggle />
	</div>
	<h1 id="notice-title"><span>Every</span> <span>Human</span> <span>Need</span> <span>Goblin</span> <span>Mode</span></h1>
	<p class="lede">
		Claude Code is built for professional developers, and this needs to be rectified immediately. Here are {countWord(
			facts.counts.modsTotal,
		)} mods that can make your config more arcane, opaque and finicky.
	</p>
	<p class="meta">
		<span>{facts.counts.modsTotal} mods</span>
		<span>{facts.counts.modsShipped} goblin-approved</span>
		<span>{facts.counts.modsProposed} soon</span>
		{#if facts.build.rootVersion}<span>goblin-mode {facts.build.rootVersion}</span>{/if}
		<span>built from {facts.build.commit} on {facts.build.date}</span>
	</p>
</section>

<style>
	.notice { padding: 2rem clamp(1.25rem, 3vw, 2.5rem) 1.75rem; transform: rotate(-0.5deg); }
	.eyebrow {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 1rem;
		flex-wrap: wrap;
		font-family: var(--font-marker);
		color: var(--accent);
		font-size: 0.95rem;
		letter-spacing: 0.04em;
	}
	h1 { font-size: clamp(2.6rem, 7vw, 5.2rem); margin-top: 0.6rem; letter-spacing: 0.01em; }
	h1 span { display: inline-block; }
	h1 span:nth-child(2) { transform: rotate(-2deg); }
	h1 span:nth-child(4) { transform: rotate(1.5deg); }
	.lede { max-width: 44rem; font-size: 1.12rem; margin: 1rem 0 0; }
	.meta {
		margin: 1.1rem 0 0;
		padding-top: 0.7rem;
		border-top: 2px dashed var(--line);
		font-family: var(--font-mono);
		font-size: 0.8rem;
		color: var(--ink-muted);
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 1.25rem;
		font-variant-numeric: tabular-nums;
	}
	/* a compact notice at 390 so the install slip reaches the first screen; last, so it wins */
	@media (max-width: 760px) {
		.notice { padding: 1.25rem 1rem 1rem; }
		.notice :global(.tape) { display: none; }
		h1 { font-size: 2.3rem; }
		.lede { font-size: 1rem; margin-top: 0.6rem; }
		.meta { display: none; }
	}
</style>
