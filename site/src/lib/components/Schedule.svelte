<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { modPage } from '#lib/paths.ts';
	import type { ModSummary } from '#lib/content/mods.ts';
	import type { ModKey } from '#lib/facts.ts';

	interface Props {
		id: string;
		title: string;
		blurb: string;
		mods: readonly ModSummary[];
		/** The open folder across every schedule on the page; one at a time. */
		open: ModKey | null;
		ontoggle: (key: ModKey) => void;
	}

	let { id, title, blurb, mods, open, ontoggle }: Props = $props();

	// Without JavaScript each folder is a plain link to its mod's page; once the
	// page hydrates it becomes a button that opens the folder's drawer.
	let enhanced = $state(false);
	onMount(() => (enhanced = true));

	const folders: Partial<Record<ModKey, HTMLElement>> = {};
	const drawers: Partial<Record<ModKey, HTMLElement>> = {};

	const placeNotch = (key: ModKey): void => {
		const folder = folders[key];
		const drawer = drawers[key];
		if (!folder || !drawer) return;
		const f = folder.getBoundingClientRect();
		const d = drawer.getBoundingClientRect();
		drawer.style.setProperty('--notch-x', `${Math.round(f.left + f.width / 2 - d.left)}px`);
	};

	// Opening one folder closes the drawer above it; scroll by however far that
	// moved the pressed folder, so it stays under the pointer.
	const press = async (key: ModKey): Promise<void> => {
		const folder = folders[key];
		const before = folder?.getBoundingClientRect().top ?? 0;
		ontoggle(key);
		await tick();
		if (folder) window.scrollBy(0, folder.getBoundingClientRect().top - before);
		placeNotch(key);
	};

	const href = (mod: ModSummary): string => modPage(mod.slug);
</script>

<svelte:window onresize={() => open && placeNotch(open)} />

<section class="schedule" aria-labelledby={`${id}-title`}>
	<header>
		<h2 id={`${id}-title`}>{title}</h2>
		<p>{blurb}</p>
	</header>
	<div class="folders" style:--columns={mods.length}>
		{#each mods as mod (mod.key)}
			{#if enhanced}
				<button
					type="button"
					class="folder"
					bind:this={folders[mod.key]}
					aria-expanded={open === mod.key}
					aria-controls={`drawer-${mod.key}`}
					onclick={() => press(mod.key)}
				>
					{@render face(mod)}
				</button>
			{:else}
				<a class="folder" href={href(mod)}>{@render face(mod)}</a>
			{/if}
			<section
				class="sheet drawer"
				id={`drawer-${mod.key}`}
				bind:this={drawers[mod.key]}
				aria-labelledby={`drawer-${mod.key}-title`}
				hidden={open !== mod.key}
			>
				<h3 class="drawer-title" id={`drawer-${mod.key}-title`}>{mod.name}</h3>
				<div class="drawer-grid">
					<div>
						<h4>Present Deficiency</h4>
						<p>{mod.deficiency}</p>
					</div>
					<div>
						<h4>Remedy</h4>
						<p>{mod.remedy}</p>
					</div>
					<p class="goblin">{mod.goblin}</p>
					<div class="drawer-foot">
						{#if !mod.shipped}<span class="stamp proposed">Not yet installable</span>{/if}
						<a class="open-file" href={href(mod)}>Open the file on {mod.name}</a>
					</div>
				</div>
			</section>
		{/each}
	</div>
</section>

{#snippet face(mod: ModSummary)}
	<span class="num">{mod.numeral}</span>
	<h3>{mod.name}</h3>
	<span class="tag">{mod.tagline}</span>
	{#if mod.shipped}
		<span class="stamp shipped">Goblin Approve</span>
	{:else}
		<span class="stamp proposed">Soon. Very Soon.</span>
	{/if}
{/snippet}

<style>
	.schedule { display: grid; gap: 1rem; }
	header { display: flex; align-items: baseline; gap: 1.25rem; flex-wrap: wrap; }
	h2 {
		font-size: clamp(1.9rem, 4vw, 2.6rem);
		background: var(--slime);
		color: var(--on-slime);
		padding: 0 0.4rem;
		transform: rotate(-1deg);
	}
	header p { margin: 0; max-width: 42rem; }
	.folders {
		display: grid;
		grid-template-columns: repeat(var(--columns), minmax(0, 1fr));
		gap: 1.25rem 1.5rem;
		align-items: start;
	}
	.folder {
		all: unset;
		box-sizing: border-box;
		cursor: pointer;
		position: relative;
		display: grid;
		gap: 0.35rem;
		align-content: start;
		background: var(--card);
		color: var(--card-ink);
		padding: 1.6rem 1.25rem 1.1rem;
		border-radius: 0 var(--radius-lg) var(--radius-md) var(--radius-md);
		box-shadow: var(--shadow);
		order: 1;
		margin-top: 1.1rem;
		min-height: 9.5rem;
		transition: transform 120ms ease;
	}
	.folder::before {
		content: '';
		position: absolute;
		top: -1.1rem;
		left: 0;
		width: 42%;
		height: 1.2rem;
		background: inherit;
		border-radius: var(--radius-md) var(--radius-md) 0 0;
	}
	.folder:hover { transform: translateY(-2px); }
	.folder:focus-visible { outline: 3px solid var(--accent); outline-offset: 4px; }
	.folder[aria-expanded='true'] { box-shadow: 0 0 0 3px var(--ink), var(--shadow); }
	.num { font-family: var(--font-marker); font-size: 1.4rem; line-height: 1; }
	h3 { font-size: 1.6rem; overflow-wrap: anywhere; }
	.tag { font-size: 0.95rem; }
	.folder .stamp { margin-top: 0.25rem; }
	.drawer {
		order: 2;
		grid-column: 1 / -1;
		margin-top: 0.9rem;
		border-radius: var(--wonk-2);
		padding: 1.5rem clamp(1rem, 3vw, 2rem);
	}
	/* the notch points up at the open folder; --notch-x is set from the folder's centre */
	.drawer::before,
	.drawer::after {
		content: '';
		position: absolute;
		border-style: solid;
		border-color: transparent;
		border-top-width: 0;
	}
	.drawer::before {
		top: -0.95rem;
		left: calc(var(--notch-x, 3rem) - 0.9rem);
		border-width: 0 0.9rem 0.95rem;
		border-bottom-color: var(--ink);
	}
	.drawer::after {
		top: -0.7rem;
		left: calc(var(--notch-x, 3rem) - 0.7rem);
		border-width: 0 0.7rem 0.75rem;
		border-bottom-color: var(--surface);
	}
	.drawer-title { font-size: 1.5rem; margin-bottom: 1rem; }
	.drawer-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 1.25rem 2rem; }
	h4 {
		font-family: var(--font-print);
		font-weight: 600;
		font-size: 0.75rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		margin: 0 0 0.3rem;
		color: var(--ink-muted);
	}
	.drawer p { margin: 0; }
	.goblin {
		grid-column: 1 / -1;
		font-family: var(--font-marker);
		font-size: 1.05rem;
		line-height: 1.5;
		color: var(--accent-2);
		max-width: 62rem;
	}
	.drawer-foot {
		grid-column: 1 / -1;
		display: flex;
		flex-wrap: wrap;
		gap: 1rem 2rem;
		align-items: center;
		justify-content: flex-end;
		border-top: 2px dashed var(--line);
		padding-top: 1rem;
	}
	.drawer-foot .stamp { margin-right: auto; }
	.open-file { font-family: var(--font-display); font-size: 1.35rem; text-decoration-thickness: 2px; }
	@media (max-width: 760px) {
		.folders { grid-template-columns: minmax(0, 1fr); gap: 0.9rem; }
		/* folders become banded rows: numeral, name and stamp on one line, description beneath */
		.folder {
			order: 0;
			min-height: 0;
			margin-top: 0.9rem;
			padding: 0.85rem 1rem 0.8rem;
			grid-template-columns: auto minmax(0, 1fr) auto;
			column-gap: 0.6rem;
			align-items: baseline;
		}
		.folder::before { top: -0.8rem; height: 0.85rem; width: 30%; }
		h3 { font-size: 1.3rem; }
		.folder .tag { grid-column: 1 / -1; font-size: 0.88rem; }
		.folder .stamp { grid-column: 3; grid-row: 1; margin-top: 0; font-size: 0.6rem; }
		.drawer { order: 0; margin-top: 0.4rem; }
		.drawer-grid { grid-template-columns: minmax(0, 1fr); }
	}
	@media (prefers-reduced-motion: reduce) {
		.folder:hover { transform: none; }
	}
</style>
