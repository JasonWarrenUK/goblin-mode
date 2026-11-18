import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/**
 * BASE_PATH is '/goblin-mode' on GitHub Pages (set by the workflow) and empty
 * locally, so `bun run dev` serves from /.
 * @type {'' | `/${string}`}
 */
const base = /** @type {'' | `/${string}`} */ (process.env.BASE_PATH ?? '');

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),
	kit: {
		adapter: adapter({ pages: 'build', assets: 'build', strict: true }),
		paths: { base },
		prerender: {
			// The crawl is the link check: a link to a page that does not exist, or a
			// #fragment with no matching id on its page, fails the build.
			handleHttpError: 'fail',
			handleMissingId: 'fail',
			handleUnseenRoutes: 'fail',
		},
	},
};

export default config;
