#!/usr/bin/env bun
// emit.ts: turn a target theme file into the exact text its consumer reads.
//
//   bun emit.ts <family>-<target>.json [--variant light|dark] [-o out]
//
// html    → CSS :root block (light on :root, dark under prefers-color-scheme
//           and [data-theme="dark"], per artefact-conventions)
// vhs     → the `Set …` lines to paste at the top of a .tape
// freeze  → freeze --config JSON
// ghostty → terminal-config key/value theme file
// card, frame, tui → the block as JSON (their consumers are our own scripts)
//
// Nothing here makes a design decision; that all happened in the theme file.

import { readFileSync, writeFileSync } from 'node:fs';

type Json = Record<string, unknown>;

function loadJson(path: string): Json {
	return JSON.parse(readFileSync(path, 'utf8')) as Json;
}

function emitHtml(block: Json): string {
	const tokens = block.tokens as { light: Record<string, string>; dark: Record<string, string> };
	const type = block.type as Record<string, string>;
	const shape = block.shape as Record<string, string>;
	const fonts = (block.google_fonts as string[]) ?? [];

	const lines = (entries: Record<string, string>, indent: string): string =>
		Object.entries(entries)
			.map(([key, value]) => `${indent}${key}: ${value};`)
			.join('\n');

	const fontLink = fonts.length
		? `<link rel="stylesheet" href="https://fonts.googleapis.com/css2?${fonts.map((font) => `family=${font}`).join('&')}&display=swap">\n`
		: '';

	return `${fontLink}<style>
:root {
${lines(tokens.light, '\t')}
${lines(type, '\t')}
${lines(shape, '\t')}
}
@media (prefers-color-scheme: dark) {
	:root:not([data-theme="light"]) {
${lines(tokens.dark, '\t\t')}
	}
}
:root[data-theme="dark"] {
${lines(tokens.dark, '\t')}
}
body { background: var(--surface); color: var(--ink); font-family: var(--font-body); }
</style>
`;
}

function emitVhs(block: Json): string {
	const theme = block.Theme as Json;
	const settings: string[] = [];
	for (const [key, value] of Object.entries(block)) {
		if (key === 'Theme' || value === null || value === undefined) continue;
		// VHS parses durations (50ms) and enum words bare; quoting a duration
		// turns it into a string it then mis-parses. `#` opens a comment, so hex
		// colours must be quoted, as must anything with whitespace (font names).
		const needsQuotes = typeof value === 'string' && (/\s/.test(value) || value.startsWith('#'));
		const rendered = needsQuotes ? `"${value}"` : String(value);
		settings.push(`Set ${key} ${rendered}`);
	}
	settings.push(`Set Theme ${JSON.stringify(theme)}`);
	return `${settings.join('\n')}\n`;
}

function emitGhostty(block: Json): string {
	const palette = block.palette as string[];
	const lines = palette.map((hex, index) => `palette = ${index}=${hex.toLowerCase()}`);
	for (const key of [
		'background',
		'foreground',
		'cursor-color',
		'selection-background',
		'selection-foreground',
		'gradient-start',
		'gradient-mid',
		'gradient-end',
	]) {
		const value = block[key];
		if (typeof value === 'string') lines.push(`${key} = ${value.toLowerCase()}`);
	}
	return `${lines.join('\n')}\n`;
}

function main(): void {
	const args = process.argv.slice(2);
	const path = args.find((arg) => !arg.startsWith('-'));
	if (!path) {
		console.error('usage: emit.ts <family>-<target>.json [-o out]');
		process.exit(1);
	}
	const outIndex = args.indexOf('-o');
	const outPath = outIndex >= 0 ? args[outIndex + 1] : null;

	const file = loadJson(path);
	const target = file.target as string;
	const block = file[target] as Json | undefined;
	if (!block) {
		console.error(`No "${target}" block in ${path}`);
		process.exit(1);
	}

	let output: string;
	switch (target) {
		case 'html':
			output = emitHtml(block);
			break;
		case 'vhs':
			output = emitVhs(block);
			break;
		case 'ghostty':
			output = emitGhostty(block);
			break;
		case 'freeze':
		case 'card':
		case 'frame':
		case 'tui':
			output = `${JSON.stringify(block, null, '\t')}\n`;
			break;
		default:
			console.error(`No emitter for target "${target}". Add one here and a template in library/templates/themes/.`);
			process.exit(1);
	}

	if (outPath) {
		writeFileSync(outPath, output);
		console.log(outPath);
	} else {
		process.stdout.write(output);
	}
}

main();
