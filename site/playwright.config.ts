// The browser contrast sweep (e2e/contrast.e2e.ts): Chromium at a pinned version, serving the built
// site from build/ under the Pages base path. Run `bun run build` first; `bun run test` does.

import { defineConfig } from '@playwright/test';

const PORT = 4319;

export default defineConfig({
	testDir: 'e2e',
	testMatch: '**/*.e2e.ts',
	fullyParallel: true,
	workers: process.env.CI ? 2 : 4,
	timeout: 15 * 60_000,
	reporter: [['list']],
	use: {
		baseURL: `http://localhost:${PORT}`,
		browserName: 'chromium',
	},
	webServer: {
		command: `bunx vite preview --port ${PORT} --strictPort`,
		url: `http://localhost:${PORT}/goblin-mode/`,
		reuseExistingServer: false,
		env: { BASE_PATH: '/goblin-mode' },
		timeout: 60_000,
	},
});
