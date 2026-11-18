<script lang="ts">
	interface Props {
		command: string;
		label: string;
	}

	let { command, label }: Props = $props();
	let copied = $state(false);
	let code = $state<HTMLElement>();

	const selectCommand = (): void => {
		if (!code) return;
		const range = document.createRange();
		range.selectNodeContents(code);
		const selection = window.getSelection();
		selection?.removeAllRanges();
		selection?.addRange(range);
	};

	const copy = async (): Promise<void> => {
		try {
			await navigator.clipboard.writeText(command);
			copied = true;
			setTimeout(() => (copied = false), 1500);
		} catch {
			selectCommand();
		}
	};
</script>

<div class="row">
	<code class="cmd" bind:this={code}>{command}</code>
	<button type="button" class="copy" onclick={copy} aria-label={`Copy: ${label}`}>{copied ? 'Copied' : 'Copy'}</button>
</div>

<style>
	.row { display: flex; gap: 0.4rem; align-items: stretch; min-width: 0; }
	.row :global(.cmd) { flex: 1; }
	.copy {
		all: unset;
		cursor: pointer;
		font-family: var(--font-print);
		font-size: 0.75rem;
		font-weight: 600;
		padding: 0 0.6rem;
		border: 2px solid currentColor;
		border-radius: var(--radius-sm);
	}
	.copy:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
</style>
