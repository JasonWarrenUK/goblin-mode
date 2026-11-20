<script lang="ts">
	import { onMount } from 'svelte';
	import CopyCommand from '#lib/components/CopyCommand.svelte';
	import HowTo from '#lib/components/mod/HowTo.svelte';
	import Roster from '#lib/components/mod/Roster.svelte';
	import SituationSlip from '#lib/components/mod/Situation.svelte';
	import { fill as fillWith } from '#lib/content/fill.ts';
	import { MOD_FILES } from '#lib/content/mod-files.ts';
	import { modSummary } from '#lib/content/mods.ts';
	import { facts, MOD_ORDER } from '#lib/facts.ts';
	import { home, modPage } from '#lib/paths.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const mod = $derived(modSummary(facts, data.key));
	const file = $derived(MOD_FILES[data.key]);
	const modFacts = $derived(facts.mods[data.key]);
	const fill = (text: string): string => fillWith(text, facts);

	const lastNumeral = modSummary(facts, MOD_ORDER[MOD_ORDER.length - 1]!).numeral;
	const position = $derived(MOD_ORDER.indexOf(data.key));
	const previous = $derived(position > 0 ? modSummary(facts, MOD_ORDER[position - 1]!) : null);
	const next = $derived(position < MOD_ORDER.length - 1 ? modSummary(facts, MOD_ORDER[position + 1]!) : null);

	// A link to a situation (a tab, a roster row, #iii-2 from another page) opens it.
	const openTarget = (): void => {
		const target = location.hash ? document.getElementById(decodeURIComponent(location.hash.slice(1))) : null;
		if (target instanceof HTMLDetailsElement) {
			target.open = true;
			target.scrollIntoView({ block: 'start' });
		}
	};
	onMount(openTarget);
</script>

<svelte:window onhashchange={openTarget} />

<svelte:head>
	<title>{mod.name} · Goblin Mode</title>
	<meta name="description" content={mod.tagline} />
</svelte:head>

<main class="desk">
	<nav class="crumbs" aria-label="Site">
		<a href={home()}>Back to the desk</a>
		<span>{mod.numeral} of {lastNumeral}</span>
	</nav>

	<header class="sheet head">
		<div>
			<span class="num">{mod.numeral}</span>
			<h1>{mod.name}</h1>
			<p class="tag">{mod.tagline}</p>
			<p class="facts">
				{#if modFacts.version}<span>v{modFacts.version}</span>{/if}
				{#if modFacts.skills > 0}<span>{modFacts.skills} skills</span>{/if}
				{#if modFacts.typescriptLines > 0}<span>{modFacts.typescriptLines.toLocaleString('en-GB')} lines of TypeScript</span>{/if}
				{#if mod.shipped}<span class="stamp shipped">Goblin Approve</span>{:else}<span class="stamp proposed">Soon. Very Soon.</span>{/if}
			</p>
		</div>
		{#if mod.installCommand}
			<div class="slip install">
				<p class="install-label">Install</p>
				<CopyCommand command={mod.installCommand} label={`install ${mod.name}`} />
			</div>
		{/if}
	</header>

	<nav aria-label="Situations">
		<ul class="tabs">
			{#each file.situations as situation (situation.id)}
				<li><a href={`#${situation.id}`}>{situation.num}</a></li>
			{/each}
			{#if file.howTo}<li><a class="how" href="#how-to">How to Use It</a></li>{/if}
		</ul>
	</nav>

	<div class="file">
		<div class="situations">
			{#each file.situations as situation (situation.id)}
				<SituationSlip {situation} {fill} planned={file.plannedCommands} />
			{/each}
		</div>
		<Roster name={mod.name} rows={file.roster} situations={file.situations} {fill} />
	</div>

	{#if file.howTo}
		<HowTo name={mod.name} howTo={file.howTo} mod={modFacts} addCommand={facts.marketplace.addCommand} {fill} />
	{/if}

	<nav class="pager" aria-label="Mods">
		{#if previous}<a class="previous" href={modPage(previous.slug)}>← {previous.numeral} {previous.name}</a>{:else}<span></span>{/if}
		<a href={home()}>The desk</a>
		{#if next}<a class="next" href={modPage(next.slug)}>{next.numeral} {next.name} →</a>{:else}<span></span>{/if}
	</nav>
</main>

<style>
	.crumbs { display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap; font-family: var(--font-print); font-size: 0.9rem; }
	.head {
		padding: 1.75rem clamp(1.25rem, 3vw, 2.5rem) 1.5rem;
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 22rem);
		gap: 1rem 2.5rem;
		align-items: end;
	}
	.num { font-family: var(--font-marker); font-size: 1.6rem; color: var(--accent); }
	h1 { font-size: clamp(2.4rem, 6vw, 4.4rem); margin: 0.2rem 0 0.6rem; overflow-wrap: anywhere; }
	.tag { margin: 0; font-size: 1.1rem; max-width: 40rem; }
	.facts {
		margin: 0.9rem 0 0;
		font-family: var(--font-mono);
		font-size: 0.8rem;
		color: var(--ink-muted);
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.25rem 1.25rem;
		font-variant-numeric: tabular-nums;
	}
	.install { padding: 1rem; display: grid; gap: 0.4rem; }
	.install-label { margin: 0; font-size: 0.85rem; font-weight: 600; }
	.tabs { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0; padding: 0; list-style: none; }
	.tabs a {
		display: inline-block;
		text-decoration: none;
		background: var(--card);
		color: var(--card-ink);
		font-family: var(--font-marker);
		padding: 0.35rem 0.8rem 0.25rem;
		border-radius: var(--radius-md) var(--radius-md) 0 0;
		box-shadow: var(--shadow);
	}
	.tabs a.how { background: var(--slip); color: var(--slip-ink); font-family: var(--font-print); font-weight: 600; font-size: 0.85rem; }
	.file { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 20rem); gap: 2rem; align-items: start; }
	.situations { display: grid; gap: 1rem; }
	.pager {
		display: grid;
		grid-template-columns: 1fr auto 1fr;
		gap: 1rem;
		align-items: center;
		font-family: var(--font-display);
		font-size: 1.25rem;
	}
	.pager .next { text-align: right; }
	@media (max-width: 760px) {
		.head, .file { grid-template-columns: minmax(0, 1fr); }
		.pager { grid-template-columns: 1fr; text-align: center; }
		.pager .next { text-align: center; }
	}
</style>
