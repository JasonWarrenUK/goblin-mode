<script lang="ts">
	import '@fontsource/cabin-sketch/latin-700.css';
	import '@fontsource/special-elite/latin-400.css';
	import '@fontsource/ibm-plex-mono/latin-400.css';
	import '@fontsource/ibm-plex-sans/latin-400.css';
	import '@fontsource/ibm-plex-sans/latin-600.css';
	import '@fontsource/permanent-marker/latin-400.css';
	import '$lib/generated/theme.css';
	import '$lib/styles/global.css';

	let { children } = $props();
</script>

{@render children()}
