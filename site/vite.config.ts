import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vitest/config';

/**
 * BASE_PATH is '/goblin-mode' on GitHub Pages (set by the workflow) and empty
 * locally, so `bun run dev` serves from /.
 */
const base = (process.env.BASE_PATH ?? '') as '' | `/${string}`;

export default defineConfig({
	plugins: [
		sveltekit({
			preprocess: vitePreprocess(),
			adapter: adapter({ pages: 'build', assets: 'build', strict: true }),
			paths: { base },
			prerender: {
				// The crawl is the first link check: a link to a page that does not exist,
				// or a #fragment with no matching id on its page, fails the build.
				handleHttpError: 'fail',
				handleMissingId: 'fail',
				handleUnseenRoutes: 'fail',
			},
		}),
	],
	test: {
		include: ['tests/**/*.test.ts'],
	},
});
