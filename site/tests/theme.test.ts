// Colour comes from the goblin theme's tokens and nowhere else: no component,
// stylesheet or route in src/ may carry a colour value of its own.

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const SITE = fileURLToPath(new URL('..', import.meta.url));
const SRC = join(SITE, 'src');

const walk = (dir: string): string[] =>
	readdirSync(dir).flatMap((entry) => {
		const path = join(dir, entry);
		if (entry === 'generated') return [];
		return statSync(path).isDirectory() ? walk(path) : [path];
	});

const COLOUR = /#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch|oklab|lab|lch)\(/;

describe('theme tokens', () => {
	const files = walk(SRC).filter((path) => /\.(svelte|css|ts|html)$/.test(path));

	it('finds the site source', () => {
		expect(files.length).toBeGreaterThan(5);
	});

	for (const file of files) {
		it(`${relative(SITE, file)} holds no colour value of its own`, () => {
			const hits = readFileSync(file, 'utf8')
				.split('\n')
				.map((line, index) => ({ line: index + 1, text: line }))
				.filter(({ text }) => COLOUR.test(text) && !/href="#|id="|#\{/.test(text));
			expect(hits).toEqual([]);
		});
	}
});
