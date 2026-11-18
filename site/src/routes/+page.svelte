<script lang="ts">
	import BoxFile from '$lib/components/BoxFile.svelte';
	import InstallSlip from '$lib/components/InstallSlip.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import Schedule from '$lib/components/Schedule.svelte';
	import { modSummary, SCHEDULES, type Schedule as ScheduleKey } from '$lib/content/mods';
	import { SKILL_PAGES } from '$lib/content/skills';
	import { facts, MOD_ORDER, type ModKey } from '$lib/facts';

	const mods = MOD_ORDER.map((key) => modSummary(facts, key));
	const scheduleKeys: readonly ScheduleKey[] = ['snacks', 'feasts'];

	let open = $state<ModKey | null>(null);
	let picked = $state<string | undefined>(undefined);

	const toggle = (key: ModKey): void => {
		open = open === key ? null : key;
		if (open && facts.mods[open].installable) picked = open;
	};
</script>

<svelte:head>
	<title>Goblin Mode</title>
	<meta
		name="description"
		content="Five mods for Claude Code that make your config more arcane, opaque and finicky: a grievance log, a goblin, a roadbook, a warband and an archivist."
	/>
</svelte:head>

<main class="desk">
	<div class="top">
		<Notice {facts} />
		<InstallSlip addCommand={facts.marketplace.addCommand} {mods} bind:picked />
	</div>

	{#each scheduleKeys as key (key)}
		{@const filed = mods.filter((mod) => mod.schedule === key)}
		<Schedule
			id={key}
			title={SCHEDULES[key].title}
			blurb={SCHEDULES[key].blurb(filed)}
			mods={filed}
			{open}
			ontoggle={toggle}
		/>
	{/each}

	<BoxFile pages={SKILL_PAGES} />
</main>

<style>
	.top {
		display: grid;
		grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
		gap: 2rem;
		align-items: start;
	}
	@media (max-width: 760px) {
		.top { grid-template-columns: minmax(0, 1fr); gap: 1.25rem; }
	}
</style>
