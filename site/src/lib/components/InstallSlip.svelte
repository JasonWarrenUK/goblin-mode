<script lang="ts">
	import CopyCommand from './CopyCommand.svelte';
	import type { ModSummary } from '#lib/content/mods.ts';

	interface Props {
		addCommand: string;
		mods: readonly ModSummary[];
		/** The mod the picker shows; opening a folder on the page sets it. */
		picked?: string;
	}

	let { addCommand, mods, picked = $bindable() }: Props = $props();
	const installable = $derived(mods.filter((mod) => mod.installCommand !== null));
	const chosen = $derived(installable.find((mod) => mod.key === picked) ?? installable[0]);
</script>

<section class="slip install" aria-labelledby="install-title">
	<h2 id="install-title">Install</h2>
	<ol>
		<li>
			<p>Add the marketplace, once.</p>
			<CopyCommand command={addCommand} label="add the marketplace" />
		</li>
		{#if chosen?.installCommand}
			<li>
				<label for="mod-pick">Install a mod.</label>
				<select id="mod-pick" bind:value={picked}>
					{#each installable as mod (mod.key)}
						<option value={mod.key}>{mod.name}</option>
					{/each}
				</select>
				<CopyCommand command={chosen.installCommand} label={`install ${chosen.name}`} />
			</li>
		{/if}
	</ol>
</section>

<style>
	.install {
		padding: 1.25rem 1.25rem 1rem;
		transform: rotate(1.2deg);
		margin-top: 1.5rem;
		background-image: repeating-linear-gradient(
			to bottom,
			transparent 0 1.6rem,
			var(--slip-line) 1.6rem calc(1.6rem + 1px)
		);
	}
	h2 {
		font-family: var(--font-print);
		font-weight: 600;
		font-size: 0.8rem;
		text-transform: uppercase;
		letter-spacing: 0.14em;
		color: var(--slip-accent);
	}
	ol { margin: 0.75rem 0 0; padding-left: 1.2rem; display: grid; gap: 0.9rem; }
	li { min-width: 0; }
	p, label { margin: 0 0 0.35rem; font-size: 0.92rem; display: block; }
	select { font: inherit; font-size: 0.85rem; margin-bottom: 0.35rem; max-width: 100%; }
	@media (max-width: 760px) {
		.install { transform: none; margin-top: 0; }
	}
</style>
