<script lang="ts">
	import CopyCommand from '../CopyCommand.svelte';
	import type { HowTo } from '#lib/content/mod-files.types.ts';
	import type { ModFacts } from '#lib/facts.ts';

	interface Props {
		name: string;
		howTo: HowTo;
		mod: ModFacts;
		addCommand: string;
		fill: (text: string) => string;
	}

	let { name, howTo, mod, addCommand, fill }: Props = $props();
	const installBoth = $derived(mod.installCommand ? `${addCommand}\n${mod.installCommand}` : addCommand);
</script>

<section class="howto" id="how-to" aria-labelledby="howto-title">
	<h2 id="howto-title">How to Use It</h2>

	<details class="slip torn">
		<summary>Install and first run</summary>
		<p>Add the marketplace once, then install the mod.</p>
		<CopyCommand command={installBoth} label={`install ${name}`} />
		{#each howTo.firstRun as paragraph, index (index)}<p>{@html fill(paragraph)}</p>{/each}
	</details>

	<details class="slip torn">
		<summary>Configure it</summary>
		{#each howTo.configure as paragraph, index (index)}<p>{@html fill(paragraph)}</p>{/each}
		{#if mod.options.length > 0}
			<div class="scroll">
				<table>
					<thead><tr><th>Option</th><th>What it does</th><th>Default</th></tr></thead>
					<tbody>
						{#each mod.options as option (option.key)}
							<tr>
								<td><code>{option.key}</code><br /><span class="title">{option.title}</span></td>
								<td>{option.description}</td>
								<td><code>{option.default === '' ? 'none' : option.default}</code></td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else}
			<p>{name} takes no options in Claude Code's plugin settings.</p>
		{/if}
	</details>

	<details class="slip torn">
		<summary>Commands and skills</summary>
		{#if mod.commands.length > 0}
			<div class="scroll">
				<table>
					<thead><tr><th>Command</th><th>What it does</th></tr></thead>
					<tbody>
						{#each mod.commands as command (command.invocation)}
							<tr><td><code>{command.invocation}</code></td><td>{command.description}</td></tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else}
			<p>{name} adds no commands or skills. It works on its own once installed.</p>
		{/if}
	</details>

	<details class="slip torn">
		<summary>Turn it off or remove it</summary>
		{#each howTo.remove as paragraph, index (index)}<p>{@html fill(paragraph)}</p>{/each}
	</details>
</section>

<style>
	.howto { display: grid; gap: 0.9rem; scroll-margin-top: 1rem; }
	h2 { font-size: clamp(1.7rem, 3.5vw, 2.3rem); }
	details { padding: 0.2rem 1.1rem 0.4rem; }
	details:nth-of-type(3n + 1) { transform: rotate(-0.45deg); }
	details:nth-of-type(3n + 2) { --rag: var(--rag-b); transform: rotate(0.35deg); }
	details:nth-of-type(3n) { --rag: var(--rag-c); transform: rotate(-0.3deg); }
	details::before { left: auto; right: 1.5rem; margin-left: 0; transform: rotate(4deg); }
	details:nth-of-type(even)::before { left: 1.5rem; right: auto; transform: rotate(-5deg); }
	summary { cursor: pointer; padding: 0.75rem 0; font-weight: 600; font-size: 1.02rem; }
	details[open] summary { border-bottom: 1px solid var(--slip-line); margin-bottom: 0.75rem; }
	details > :not(summary) { margin: 0 0 0.9rem; }
	table { border-collapse: collapse; width: 100%; font-size: 0.88rem; }
	th, td { text-align: left; padding: 0.35rem 0.5rem; border-bottom: 1px solid var(--slip-line); vertical-align: top; }
	.title { color: var(--ink-muted); font-size: 0.85em; }
	/* a long default (the jester's schedule) wraps instead of widening the table */
	td :global(code) { overflow-wrap: anywhere; }
	.scroll { overflow-x: auto; }
	details :global(code:not(.cmd)) { color: var(--slip-accent); font-size: 0.88em; }
	@media (max-width: 760px) {
		details { transform: none !important; }
	}
</style>
