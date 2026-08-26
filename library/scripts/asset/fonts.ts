#!/usr/bin/env bun
// fonts.ts: fetch the font files card.ts needs into ./fonts, named <Family>-<weight>.woff.
// satori needs real font data; there is no system-font fallback. Sources are
// fontsource's CDN (Inter, Inter Tight, JetBrains Mono), all OFL.
//
//   bun fonts.ts            fetch the defaults used by the clod family
//   bun fonts.ts <url> <Family> <weight>   fetch one more

import { existsSync } from 'node:fs';
import { join } from 'node:path';

const FONTS_DIR = join(new URL('.', import.meta.url).pathname, 'fonts');

// Static instances only: satori's opentype parser cannot read variable fonts.
// fontsource publishes one static WOFF per weight, which satori accepts.
const DEFAULTS: [string, string, number][] = [
	['https://cdn.jsdelivr.net/fontsource/fonts/inter@latest/latin-400-normal.woff', 'Inter', 400],
	['https://cdn.jsdelivr.net/fontsource/fonts/inter@latest/latin-600-normal.woff', 'Inter', 600],
	['https://cdn.jsdelivr.net/fontsource/fonts/inter-tight@latest/latin-700-normal.woff', 'Inter Tight', 700],
	['https://cdn.jsdelivr.net/fontsource/fonts/jetbrains-mono@latest/latin-400-normal.woff', 'JetBrains Mono', 400],
];

async function fetchFont(url: string, family: string, weight: number): Promise<void> {
	const extension = url.split('?')[0].split('.').pop() ?? 'woff';
	const target = join(FONTS_DIR, `${family.replace(/\s+/g, '')}-${weight}.${extension}`);
	if (existsSync(target)) {
		console.log(`present  ${target}`);
		return;
	}
	const response = await fetch(url);
	if (!response.ok) throw new Error(`${url}: ${response.status}`);
	await Bun.write(target, await response.arrayBuffer());
	console.log(`fetched  ${target}`);
}

const [url, family, weight] = process.argv.slice(2);
if (url && family && weight) {
	await fetchFont(url, family, Number(weight));
} else {
	for (const entry of DEFAULTS) await fetchFont(...entry);
}
