// Checks on the built site in build/, which `bun run test` produces first.
// BASE_PATH is the same variable the build read, so links are checked under the
// base path GitHub Pages serves them from.

import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join, posix, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const SITE = fileURLToPath(new URL('..', import.meta.url));
const BUILD = join(SITE, 'build');
const BASE = process.env.BASE_PATH ?? '';

const walk = (dir: string): string[] =>
	readdirSync(dir).flatMap((entry) => {
		const path = join(dir, entry);
		return statSync(path).isDirectory() ? walk(path) : [path];
	});

const pages = existsSync(BUILD) ? walk(BUILD).filter((path) => path.endsWith('.html')) : [];

/** The URL path a built file is served at, under the base path. */
const servedAt = (file: string): string => {
	const rel = relative(BUILD, file).split('\\').join('/');
	return `${BASE}/${rel.replace(/index\.html$/, '')}`;
};

/** The built file a URL path resolves to, or null when it leaves the site. */
const fileFor = (urlPath: string): string | null => {
	if (BASE && !urlPath.startsWith(`${BASE}/`) && urlPath !== BASE) return null;
	const rel = urlPath.slice(BASE.length).replace(/^\//, '');
	const direct = join(BUILD, rel);
	if (rel === '' || rel.endsWith('/')) return join(direct, 'index.html');
	if (existsSync(direct) && statSync(direct).isFile()) return direct;
	return join(direct, 'index.html');
};

describe('the build', () => {
	it('prerendered the front page, every mod page and the skills wing', () => {
		// 12 before the tutorial; its shared-route placeholder gave way to an index and five levels
		expect(pages.length).toBe(17);
		for (const path of ['skills/tutorial/index.html', ...[1, 2, 3, 4, 5].map((n) => `skills/tutorial/${n}/index.html`)]) {
			expect(existsSync(join(BUILD, path)), path).toBe(true);
		}
		expect(existsSync(join(BUILD, 'index.html'))).toBe(true);
		expect(existsSync(join(BUILD, '.nojekyll'))).toBe(true);
	});

	it('ships nothing from the design record or the legacy pages', () => {
		const leaked = walk(BUILD).filter((path) => /\/(design|legacy)\//.test(path));
		expect(leaked).toEqual([]);
	});

	it('loads no font or stylesheet from another host', () => {
		for (const page of pages) expect(readFileSync(page, 'utf8')).not.toMatch(/fonts\.(googleapis|gstatic)\.com/);
	});
});

describe('every in-site link', () => {
	for (const page of pages) {
		const html = readFileSync(page, 'utf8');
		const from = servedAt(page);
		const hrefs = [...html.matchAll(/\shref="([^"]+)"/g)].map((match) => match[1] ?? '');

		it(`resolves from ${from}`, () => {
			const broken: string[] = [];
			for (const href of hrefs) {
				if (/^[a-z]+:/i.test(href) || href.startsWith('//')) continue;
				const [path = '', fragment] = href.split('#');
				const target = path === '' ? page : fileFor(posix.resolve(posix.dirname(`${from}x`), path) + (path.endsWith('/') ? '/' : ''));
				if (target === null || !existsSync(target)) {
					broken.push(href);
					continue;
				}
				if (fragment && !readFileSync(target, 'utf8').includes(`id="${fragment}"`)) broken.push(href);
			}
			expect(broken).toEqual([]);
		});
	}
});
