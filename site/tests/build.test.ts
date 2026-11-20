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
		// 12 before the tutorial; its shared-route placeholder gave way to an index and five levels (17);
		// the Red Family page (16), A Skill Is One Goblin (15) and Everyone Gets a File (14) were withdrawn on 2026-11-20;
		// the Metadata page has its own route
		expect(pages.length).toBe(14);
		expect(existsSync(join(BUILD, 'skills/metadata/index.html'))).toBe(true);
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

	it('stamps every unbuilt line of the archivist scene that mixes built and unbuilt work', () => {
		const page = readFileSync(join(BUILD, 'mods/goblin-archivist/index.html'), 'utf8');
		const scene = page.slice(page.indexOf('id="v-5"'), page.indexOf('</details>', page.indexOf('id="v-5"')));
		const items = [...scene.matchAll(/<li>([\s\S]*?)<\/li>/g)].map((match) => match[1] ?? '');
		const withSide = items.slice(-3);
		expect(withSide[0]).toContain('writes nothing in it');
		expect(withSide[0]).not.toContain('Not built yet');
		expect(withSide[1]).toContain('Not built yet');
		expect(withSide[2]).toContain('Not built yet');
	});

	it('opens every page with a skip link to its main content', () => {
		for (const page of pages) {
			const html = readFileSync(page, 'utf8');
			const body = html.slice(html.indexOf('<body'));
			const firstLink = /<a\b[^>]*href="([^"]+)"/.exec(body)?.[1];
			expect(firstLink, servedAt(page)).toBe('#main');
			expect(html, servedAt(page)).toMatch(/<main\b[^>]*\bid="main"/);
		}
	});

	it('gives every copy button a polite live region that announces the copy', () => {
		for (const page of pages) {
			const html = readFileSync(page, 'utf8');
			const buttons = (html.match(/class="copy\b/g) ?? []).length;
			const regions = (html.match(/aria-live="polite"[^>]*>[^<]*<\/span>/g) ?? []).length;
			expect(regions, servedAt(page)).toBeGreaterThanOrEqual(buttons);
		}
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
