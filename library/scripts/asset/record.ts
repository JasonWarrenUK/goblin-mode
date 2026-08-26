#!/usr/bin/env node
// record.ts: run a Playwright flow with video recording on. Node, not Bun:
// Playwright's launch path has a history of hanging under Bun.
//
//   node --experimental-strip-types record.ts <flow.ts> <out.webm> [--width 1280] [--height 720] [--mp4]
//
// flow.ts default-exports `async (page) => { … }`. The context is created
// here so the flow only drives the page. --mp4 converts via ffmpeg.

import { chromium, type Page } from 'playwright';
import { mkdtempSync, renameSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';

function argValue(args: string[], flag: string): string | null {
	const index = args.indexOf(flag);
	return index >= 0 ? args[index + 1] : null;
}

async function main(): Promise<void> {
	const args = process.argv.slice(2);
	const positional = args.filter((arg, index) => !arg.startsWith('--') && !args[index - 1]?.startsWith('--'));
	const [flowPath, output] = positional;
	if (!flowPath || !output) {
		console.error('usage: record.ts <flow.ts> <out.webm> [--width N] [--height N] [--mp4]');
		process.exit(1);
	}
	const width = Number(argValue(args, '--width') ?? 1280);
	const height = Number(argValue(args, '--height') ?? 720);

	const flowModule = await import(pathToFileURL(resolve(flowPath)).href);
	const flow = flowModule.default as (page: Page) => Promise<void>;

	const dir = mkdtempSync(join(tmpdir(), 'asset-record-'));
	const browser = await chromium.launch({ headless: true });
	const context = await browser.newContext({ viewport: { width, height }, recordVideo: { dir, size: { width, height } } });
	const page = await context.newPage();
	try {
		await flow(page);
	} finally {
		await context.close();
		await browser.close();
	}
	const recorded = readdirSync(dir).find((file) => file.endsWith('.webm'));
	if (!recorded) throw new Error('Playwright produced no video');
	renameSync(join(dir, recorded), output);
	console.log(output);

	if (args.includes('--mp4')) {
		const mp4 = output.replace(/\.webm$/, '.mp4');
		execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', output, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4]);
		console.log(mp4);
	}
}

main().catch((error: Error) => {
	console.error(error.message);
	process.exit(1);
});
