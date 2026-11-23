// The contrast sweep: the authority on whether a reader can read the site. On every built page, at four
// viewports and in both themes, it opens every disclosure and folder, steps through every tutorial and
// Metadata stage state and file tab, and measures every text node and every ::before or ::after that
// carries text as the browser renders it: the computed colour (or -webkit-text-fill-color, or fill for SVG
// text) with its alpha multiplied by every ancestor's opacity, composited over the background chain
// behind it, a slip's paper painted on a pseudo-element included. Anything under 4.5:1 fails, named by
// page, viewport, theme, state and element. A background image, filter or blend mode behind text cannot
// be measured this way, so it fails too unless ALLOWED below names it with the reason.
//
// The static guard in tests/contrast.test.ts stays as the fast early check; this is the one that counts.

import { readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Page } from '@playwright/test';
import { METADATA } from '../src/lib/content/metadata.ts';
import { TUTORIAL } from '../src/lib/content/tutorial.ts';
import { statesOf } from '../src/lib/content/tutorial-view.ts';
import type { StagePage } from '../src/lib/content/tutorial.types.ts';
import { MOD_NAMES } from '../src/lib/mod-names.ts';

const BUILD = fileURLToPath(new URL('../build', import.meta.url));
const BASE = '/goblin-mode';

/** Every built page, as the path it is served at. */
const walk = (dir: string): string[] =>
	readdirSync(dir).flatMap((entry) => {
		const path = join(dir, entry);
		return statSync(path).isDirectory() ? walk(path) : [path];
	});
const PAGES = walk(BUILD)
	.filter((path) => path.endsWith('index.html') && !path.includes('/_app/'))
	.map((path) => `${BASE}/${relative(BUILD, path).replace(/index\.html$/, '')}`)
	.sort();

const VIEWPORTS: [number, number][] = [
	[1440, 1000],
	[1100, 800],
	[1000, 900],
	[390, 800],
];
const THEMES = ['light', 'dark'] as const;

/** The stage a page carries, from the same data the page is built from, so the sweep knows what it must reach. */
const stageOf = (path: string): StagePage | null => {
	const level = /\/skills\/tutorial\/(\d)\/$/.exec(path);
	if (level) return TUTORIAL[Number(level[1]) - 1] ?? null;
	return path.endsWith('/skills/metadata/') ? METADATA : null;
};

/** The folders on the desk: one per mod. */
const FOLDERS = Object.keys(MOD_NAMES).length;

/**
 * The least text the sweep must measure on a page; fewer means it measured the wrong thing or nothing. The
 * two index pages are short lists (skip link, back link, heading and one link per entry); every other page
 * holds far more.
 */
const floorFor = (path: string): number => (path.endsWith('/skills/') || path.endsWith('/skills/tutorial/') ? 5 : 25);

/**
 * Elements whose background image sits behind text, by selector, each with the reason and the colour the
 * sweep composites in its place to reach the worst case: text over it is measured both without that
 * colour and with it laid over the background, and must clear 4.5:1 both ways.
 */
/*
 * An allowed image must paint nothing but its worst-case colour and transparency: each colour stop in the
 * element's computed background-image is checked against `worst`, so a stop changed to any other colour
 * fails, and every other unmeasurable property on the element (a filter, a blend mode) still fails.
 */
const ALLOWED: { selector: string; reason: string; worst: string }[] = [
	{ selector: 'body', reason: "the desk's ink blots: radial gradients of --blot over --desk, darkest at their centres", worst: '--blot' },
	{ selector: '.slip.install', reason: "the install slip's ruled lines: 1px of --slip-line every 1.6rem", worst: '--slip-line' },
];

interface Finding {
	ratio: number;
	text: string;
	element: string;
	flag: string;
}

/** Runs in the page: every readable text and its contrast, or the flag that stopped it being measured. */
const measure = (allowed: { selector: string; worst: string }[]): { measured: number; findings: Finding[] } => {
	const canvas = document.createElement('canvas');
	canvas.width = canvas.height = 1;
	const ctx = canvas.getContext('2d', { willReadFrequently: true })!;
	/** Any CSS colour (a mix, oklab, a named colour) resolved to sRGB with alpha. */
	const rgba = (css: string): number[] => {
		ctx.clearRect(0, 0, 1, 1);
		ctx.fillStyle = 'rgba(0, 0, 0, 0)';
		ctx.fillStyle = css;
		ctx.fillRect(0, 0, 1, 1);
		const d = ctx.getImageData(0, 0, 1, 1).data;
		return [d[0]!, d[1]!, d[2]!, d[3]! / 255];
	};
	const over = (top: number[], under: number[]): number[] => [0, 1, 2].map((i) => top[i]! * top[3]! + under[i]! * (1 - top[3]!)).concat(1);
	const luminance = (c: number[]): number => {
		const [r, g, b] = c.slice(0, 3).map((v) => {
			const x = v / 255;
			return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
		}) as [number, number, number];
		return 0.2126 * r + 0.7152 * g + 0.0722 * b;
	};
	const ratio = (a: number[], b: number[]): number => {
		const [x, y] = [luminance(a), luminance(b)].sort((p, q) => q - p) as [number, number];
		return (x + 0.05) / (y + 0.05);
	};
	const name = (el: Element): string => {
		const parts: string[] = [];
		for (let e: Element | null = el; e && parts.length < 4; e = e.parentElement) {
			const cls = typeof e.className === 'string' ? e.className.split(/\s+/).filter((c) => c && !c.startsWith('svelte-')).join('.') : '';
			parts.push(e.tagName.toLowerCase() + (cls ? `.${cls}` : ''));
		}
		return parts.join(' < ');
	};
	const allowance = (el: Element): { selector: string; worst: string } | undefined => allowed.find(({ selector }) => el.matches(selector));

	/**
	 * Every way a layer escapes measurement: an image, a colour-changing filter, a blend mode. A filter
	 * made only of drop-shadow() paints outside the element and leaves its colours alone, so it is measurable.
	 */
	const unmeasurable = (cs: CSSStyleDeclaration): string[] => {
		const flags: string[] = [];
		const filter = cs.filter.replace(/drop-shadow\((?:[^()]|\([^()]*\))*\)/g, '').trim();
		if (cs.backgroundImage !== 'none') flags.push(`background-image ${cs.backgroundImage.slice(0, 40)}`);
		if (filter && filter !== 'none') flags.push(`filter ${cs.filter}`);
		if (cs.mixBlendMode !== 'normal') flags.push(`mix-blend-mode ${cs.mixBlendMode}`);
		if (cs.backdropFilter && cs.backdropFilter !== 'none') flags.push(`backdrop-filter ${cs.backdropFilter}`);
		return flags;
	};
	/** The colour stops an image paints that are neither transparent nor the declared worst case. */
	const strayStops = (image: string, worst: number[]): string[] =>
		(image.match(/rgba?\([^)]*\)|color\([^)]*\)|oklab\([^)]*\)|oklch\([^)]*\)|#[0-9a-fA-F]{3,8}\b/g) ?? []).filter((stop) => {
			const colour = rgba(stop);
			return colour[3]! > 0 && colour.some((channel, i) => Math.abs(channel - worst[i]!) > (i === 3 ? 0.02 : 2));
		});

	/** The paint behind an element: its own and its ancestors' backgrounds, a full-cover pseudo backing included, down to the first opaque one. */
	const behind = (el: Element): { colour: number[]; worst: number[]; flag: string } => {
		const layers: number[][] = [];
		let flag = '';
		let worstLayer: number[] | null = null;
		for (let e: Element | null = el; e; e = e.parentElement) {
			const own = getComputedStyle(e);
			const allowedHere = allowance(e);
			for (const found of unmeasurable(own)) {
				if (allowedHere && found.startsWith('background-image')) {
					worstLayer = rgba(getComputedStyle(document.documentElement).getPropertyValue(allowedHere.worst).trim());
					const stray = strayStops(own.backgroundImage, worstLayer);
					if (stray.length && !flag) flag = `background-image on ${name(e)} paints ${stray.join(', ')}, not only ${allowedHere.worst}`;
				} else if (!flag) flag = `${found} on ${name(e)}`;
			}
			const own_ = rgba(own.backgroundColor);
			const backing = ['::before', '::after']
				.map((pseudo) => getComputedStyle(e!, pseudo))
				.filter((ps) => ps.content !== 'none' && ps.content !== 'normal' && ps.position === 'absolute' && ps.top === '0px' && ps.left === '0px' && ps.right === '0px' && ps.bottom === '0px')
				.map((ps) => rgba(ps.backgroundColor))
				.find((c) => c[3]! > 0);
			if (own_[3]! > 0) layers.push(own_);
			if (backing) layers.push(backing);
			if (own_[3]! >= 0.999 || (backing && backing[3]! >= 0.999)) break;
		}
		let colour = rgba(getComputedStyle(document.documentElement).backgroundColor);
		if (colour[3] === 0) colour = [255, 255, 255, 1];
		for (let i = layers.length - 1; i >= 0; i--) colour = over(layers[i]!, colour);
		// the allowed image sits just above the opaque layer it was found on
		const worst = worstLayer ? over(worstLayer, colour) : colour;
		return { colour, worst, flag };
	};

	/** Hidden from sight: not rendered, invisible, fully transparent or clipped to a pixel (screen-reader text). */
	const hidden = (el: Element): boolean => {
		for (let e: Element | null = el; e; e = e.parentElement) {
			const cs = getComputedStyle(e);
			if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') return true;
			if (cs.clipPath.startsWith('inset(50%')) return true;
			const r = e.getBoundingClientRect();
			if ((cs.overflow === 'hidden' || cs.overflow === 'clip') && (r.width <= 1 || r.height <= 1)) return true;
		}
		const r = el.getBoundingClientRect();
		return r.width < 1 || r.height < 1;
	};
	const opacity = (el: Element): number => {
		let o = 1;
		for (let e: Element | null = el; e; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity);
		return o;
	};

	const findings: Finding[] = [];
	const check = (el: Element, text: string, pseudo?: string): void => {
		if (hidden(el)) return;
		const cs = getComputedStyle(el, pseudo ?? null);
		if (pseudo && (cs.display === 'none' || cs.visibility === 'hidden')) return;
		const svgText = el instanceof SVGElement;
		const fill = svgText ? cs.fill : cs.webkitTextFillColor && rgba(cs.webkitTextFillColor).join() !== rgba(cs.color).join() ? cs.webkitTextFillColor : cs.color;
		let { colour: bg, worst, flag } = behind(el);
		if (pseudo) {
			const own = rgba(cs.backgroundColor);
			if (own[3]! > 0) {
				bg = over(own, bg);
				worst = over(own, worst);
			}
			const pseudoFlag = unmeasurable(cs)[0];
			if (pseudoFlag && !flag) flag = `${pseudoFlag} on ${name(el)}${pseudo}`;
		}
		const ink = rgba(fill);
		// SVG text also thins by fill-opacity; a stroke would change its edges in a way this cannot measure
		if (svgText && cs.stroke !== 'none' && !flag) flag = `stroke ${cs.stroke} on SVG text ${name(el)}`;
		const alpha = ink[3]! * opacity(el) * (pseudo ? parseFloat(cs.opacity) : 1) * (svgText ? parseFloat(cs.fillOpacity) : 1);
		const lowest = Math.min(...[bg, worst].map((ground) => ratio(over([ink[0]!, ink[1]!, ink[2]!, alpha], ground), ground)));
		findings.push({ ratio: lowest, text: text.slice(0, 40), element: name(el) + (pseudo ?? ''), flag });
	};

	const seen = new Set<Element>();
	const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
	for (let node = walker.nextNode(); node; node = walker.nextNode()) {
		const text = node.nodeValue?.trim();
		const el = node.parentElement;
		if (!text || !el || ['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(el.tagName) || seen.has(el)) continue;
		seen.add(el);
		check(el, text);
	}
	for (const el of document.querySelectorAll('body *')) {
		for (const pseudo of ['::before', '::after']) {
			const content = getComputedStyle(el, pseudo).content;
			const text = content.startsWith('"') ? content.slice(1, -1) : content.startsWith('attr(') ? (el.getAttribute(content.slice(5, -1)) ?? '') : '';
			if (text.trim()) check(el, text.trim(), pseudo);
		}
	}
	return { measured: findings.length, findings: findings.filter((finding) => finding.ratio < 4.5 || finding.flag) };
};

/** Measures the page as it stands and records anything under 4.5:1 or unmeasurable; returns how many texts it measured. */
const record = async (page: Page, where: string, failures: Map<string, string>): Promise<number> => {
	// a fade or flash mid-flight is not the state a reader settles on: let every finite animation finish
	await page.evaluate(() =>
		Promise.race([
			Promise.all(document.getAnimations().filter((a) => a.effect?.getTiming().iterations !== Infinity).map((a) => a.finished.catch(() => undefined))),
			new Promise((done) => setTimeout(done, 3000)),
		]),
	);
	const { measured, findings } = await page.evaluate(measure, ALLOWED.map(({ selector, worst }) => ({ selector, worst })));
	for (const f of findings) {
		const key = `${f.element}|${f.text}|${f.flag}|${f.ratio.toFixed(2)}`;
		if (!failures.has(key)) failures.set(key, `${where}: ${f.flag ? `cannot measure (${f.flag})` : `${f.ratio.toFixed(2)}:1`} ${f.element} "${f.text}"`);
	}
	return measured;
};

/** Scrolls the whole page a screen at a time, measuring at each stop, so scroll-driven states are seen. */
const sweepScroll = async (page: Page, where: string, failures: Map<string, string>, height: number): Promise<number> => {
	const total = await page.evaluate(() => document.documentElement.scrollHeight);
	let most = 0;
	for (let y = 0; y < total; y += Math.round(height * 0.6)) {
		await page.evaluate((top) => window.scrollTo(0, top), y);
		await page.waitForTimeout(250);
		most = Math.max(most, await record(page, `${where} at y=${y}`, failures));
	}
	return most;
};

for (const [width, height] of VIEWPORTS) {
	for (const theme of THEMES) {
		test(`${theme} ${width}x${height}: every text on every page reads at 4.5:1 or better`, async ({ browser }) => {
			const context = await browser.newContext({ viewport: { width, height }, colorScheme: theme, reducedMotion: 'no-preference' });
			const page = await context.newPage();
			const failures = new Map<string, string>();
			const states: string[] = [];
			// what the sweep must reach, checked as it goes, so a renamed control fails here instead of passing unseen
			const unreached: string[] = [];
			for (const path of PAGES) {
				const response = await page.goto(path);
				expect(response?.status(), `${path} served`).toBe(200);
				await page.evaluate(() => document.fonts.ready);
				const where = `${path} ${theme} ${width}x${height}`;
				let measured = 0;

				const expected = stageOf(path);
				// the stage renders static until its script has run; with motion allowed it must then pin or list
				if (expected) await page.waitForFunction(() => document.querySelector('.tut')?.getAttribute('data-mode') !== 'static', undefined, { timeout: 5000 }).catch(() => undefined);
				const stage = await page.evaluate(() => document.querySelector('.tut')?.getAttribute('data-mode') ?? null);
				if (expected) {
					const want = statesOf(expected);
					if (stage !== 'pinned' && stage !== 'list') unreached.push(`${where}: the stage reports mode ${stage}, not pinned or list`);
					const steps = await page.locator('button.step-btn').count();
					if (steps !== want.length) unreached.push(`${where}: ${steps} step controls found, ${want.length} states expected`);
					if (stage === 'pinned') {
						for (let i = 0; i < steps; i++) {
							await page.evaluate((k) => (document.querySelectorAll('button.step-btn')[k] as HTMLButtonElement).click(), i);
							await page.waitForTimeout(900);
							const files = want[i]?.files.length ?? 1;
							const tabs = await page.locator('.tut .specimen .tab').count();
							if (tabs !== (files > 1 ? files : 0)) unreached.push(`${where} step ${i + 1}: ${tabs} file tabs found, ${files} files expected`);
							for (let t = 0; t < Math.max(1, tabs); t++) {
								if (t > 0) {
									await page.evaluate((k) => (document.querySelectorAll('.tut .specimen .tab')[k] as HTMLButtonElement).click(), t);
									await page.waitForTimeout(400);
								}
								states.push(`${where} step ${i + 1} tab ${t + 1}`);
								measured = Math.max(measured, await record(page, `${where} step ${i + 1} tab ${t + 1}`, failures));
							}
						}
					}
				} else if (stage !== null) unreached.push(`${where}: a stage the sweep has no data for`);

				// every disclosure open, then the page a screen at a time (list-mode steps change as they scroll in)
				await page.evaluate(() => document.querySelectorAll('details').forEach((d) => (d.open = true)));
				states.push(`${where} all open`);
				measured = Math.max(measured, await sweepScroll(page, `${where} all open`, failures, height));

				if (stage === 'list') {
					await page.getByRole('button', { name: 'File', exact: true }).first().click();
					states.push(`${where} file view`);
					measured = Math.max(measured, await sweepScroll(page, `${where} file view`, failures, height));
				}

				// the desk's folders, one per mod, open one at a time
				const folders = await page.locator('.folders [aria-expanded]').count();
				if (path === `${BASE}/` && folders !== FOLDERS) unreached.push(`${where}: ${folders} folders found, ${FOLDERS} mods expected`);
				for (let i = 0; i < folders; i++) {
					await page.evaluate((k) => (document.querySelectorAll('.folders [aria-expanded]')[k] as HTMLElement).click(), i);
					await page.waitForTimeout(350);
					states.push(`${where} folder ${i + 1}`);
					measured = Math.max(measured, await record(page, `${where} folder ${i + 1}`, failures));
				}
				if (measured < floorFor(path)) unreached.push(`${where}: only ${measured} texts measured, under the floor of ${floorFor(path)}`);
			}
			expect(unreached, 'every page, stage state, file tab and folder the content says exists').toEqual([]);
			await context.close();
			test.info().annotations.push({ type: 'states', description: `${states.length} states on ${PAGES.length} pages` });
			expect([...failures.values()], `${states.length} states measured`).toEqual([]);
		});
	}
}

test('finds every built page', () => {
	expect(PAGES.length).toBe(14);
});
