<script lang="ts">
	import { skillPage, skillsIndex } from '$lib/paths';

	interface Props {
		pages: readonly { slug: string; title: string }[];
	}

	let { pages }: Props = $props();
</script>

<section class="boxfile" aria-labelledby="build-title">
	<div>
		<h2 id="build-title"><a class="label" href={skillsIndex()}>Build Your Own</a></h2>
		<p>How the skills behind these mods are put together, a topic at a time.</p>
	</div>
	<ul>
		{#each pages as page (page.slug)}
			<li><a href={skillPage(page.slug)}>{page.title}</a></li>
		{/each}
	</ul>
</section>

<style>
	.boxfile {
		position: relative;
		background: var(--surface-raised);
		color: var(--ink);
		padding: 1.5rem;
		border: 2px solid var(--ink);
		border-radius: var(--radius-md);
		box-shadow: var(--shadow);
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: 1rem 2rem;
		align-items: start;
	}
	.label {
		display: inline-block;
		background: var(--slip);
		color: var(--slip-ink);
		font-family: var(--font-marker);
		font-weight: 400;
		padding: 0.2rem 0.7rem;
		transform: rotate(-1.5deg);
		font-size: 1.15rem;
		text-decoration: none;
	}
	p { margin: 0.8rem 0 0; }
	ul { margin: 0; padding-left: 1.1rem; display: grid; gap: 0.3rem; }
	@media (max-width: 760px) {
		.boxfile { grid-template-columns: minmax(0, 1fr); }
	}
</style>
