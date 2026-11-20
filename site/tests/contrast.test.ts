// Every colour the site sets text in, held to WCAG AA's 4.5:1 against the material it sits on, in
// both variants of the goblin theme. The pairs are read from the CSS itself: each rule that sets
// `color: var(--token)` is matched to its material by its own background, by the step tones, or by
// where its selector sits (MATERIAL below). A colour rule this test cannot place fails, so a new
// pairing can never ship unchecked.

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const SITE = fileURLToPath(new URL('..', import.meta.url));
const SRC = join(SITE, 'src');
const THEME = fileURLToPath(new URL('../../.claude/themes/goblin-html.json', import.meta.url));
const tokens = (JSON.parse(readFileSync(THEME, 'utf8')) as { html: { tokens: Record<'light' | 'dark', Record<string, string>> } }).html.tokens;

/** WCAG 2.x relative luminance of a six-digit hex colour. */
const luminance = (hex: string): number => {
	const [r, g, b] = [1, 3, 5].map((i) => {
		const channel = parseInt(hex.slice(i, i + 2), 16) / 255;
		return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
	}) as [number, number, number];
	return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};

const ratio = (a: string, b: string): number => {
	const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
	return (light + 0.05) / (dark + 0.05);
};

/**
 * Where a rule with no background of its own sits: the file it is in, a pattern on its selector, the
 * material behind it. First match wins. `--link` and the step tones are handled on their own below.
 */
const MATERIAL: [RegExp, RegExp, string][] = [
	[/InstallSlip\.svelte$/, /./, '--slip'],
	[/Notice\.svelte$/, /./, '--surface'],
	[/ThemeToggle\.svelte$/, /./, '--surface'],
	[/Schedule\.svelte$/, /\.motto|^h4$|\.goblin/, '--surface'],
	[/HowTo\.svelte$/, /./, '--slip'],
	[/Roster\.svelte$/, /./, '--slip'],
	[/Situation\.svelte$/, /^\.with\b/, '--slip'],
	[/Situation\.svelte$/, /^\.before\b/, '--surface-raised'],
	[/Situation\.svelte$/, /./, '--surface'],
	[/global\.css$/, /^\.slip a$/, '--slip'],
	[/global\.css$/, /^\.stamp\./, '--surface'],
	[/tutorial\.css$/, /\.code\b/, '--exhibit'],
	[/tutorial\.css$/, /\.tab\b|\.viewbar\b/, '--card'],
	[/tutorial\.css$/, /\.leaders\b/, '--surface'],
	[/tutorial\.css$/, /\.co\b|\.exercise\b/, '--slip'],
	// a bare `code` selector reaches the code panel (an exhibit) as well as inline code, so the panel is what it must clear
	[/tutorial\.css$/, /(^| )code$/, '--exhibit'],
	[/tutorial\.css$/, /\.kicker|\.how|\.snap-title|\.pin-title|\.pin-file|\.spec-state|\.stepnav|\.step\b/, '--surface'],
	[/\[mod\]\/\+page\.svelte$/, /^\.num$|^\.facts$/, '--surface'],
];


const walk = (dir: string): string[] =>
	readdirSync(dir).flatMap((entry) => {
		const path = join(dir, entry);
		if (entry === 'generated') return [];
		return statSync(path).isDirectory() ? walk(path) : [path];
	});

/** A selector list split at its top-level commas only, so `:is(.t1, .t2)` stays whole. */
const topLevel = (list: string): string[] => {
	const parts: string[] = [];
	let depth = 0;
	let current = '';
	for (const char of list) {
		if (char === '(') depth++;
		if (char === ')') depth--;
		if (char === ',' && depth === 0) {
			parts.push(current);
			current = '';
		} else current += char;
	}
	return [...parts, current];
};

interface Rule {
	file: string;
	selector: string;
	body: string;
}

const SOURCES = walk(SRC);

/** The rules in one stylesheet's text, media queries and keyframes flattened (a keyframe stop reads as its own rule). */
export const rulesIn = (file: string, css: string): Rule[] =>
	[...css.replace(/\/\*[\s\S]*?\*\//g, '').matchAll(/([^{}@]+)\{([^{}]*)\}/g)].flatMap((match) =>
		topLevel(match[1]!)
			.map((one) => one.replace(/:global\(([^)]*)\)/g, '$1').trim().replace(/\s+/g, ' '))
			.filter(Boolean)
			.map((selector) => ({ file, selector, body: match[2]! })),
	);

/** Every rule the site can apply: stylesheets, every <style> block of every component, app.html's too. */
const rules: Rule[] = SOURCES.filter((path) => /\.(css|svelte|html)$/.test(path)).flatMap((path) => {
	const text = readFileSync(path, 'utf8');
	const css = path.endsWith('.css') ? text : [...text.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/g)].map((match) => match[1]).join('\n');
	return rulesIn(relative(SITE, path), css);
});

/**
 * Every way a rule thins what it paints: an `opacity` or `filter: opacity()` below 1 (as a number, a
 * percentage or a value the test cannot read, such as `var()`), and any keyframe stop after the first
 * that is not fully opaque. A `0` outside keyframes hides an element and is allowed; a first stop may
 * fade in from anything.
 */
export const dimmings = (from: Rule[]): string[] => {
	const problems: string[] = [];
	for (const rule of from) {
		const stop = /^(?:from|to|\d+(?:\.\d+)?%)$/.test(rule.selector);
		const firstStop = /^(?:from|0%)$/.test(rule.selector);
		const values = [
			...[...rule.body.matchAll(/(?:^|[;\s])opacity:\s*([^;]+)/g)].map((match) => ({ kind: 'opacity', raw: match[1]! })),
			...[...rule.body.matchAll(/(?:^|[;\s])filter:[^;]*\bopacity\(([^)]*)\)/g)].map((match) => ({ kind: 'filter: opacity()', raw: match[1]! })),
		];
		for (const { kind, raw } of values) {
			const value = raw.replace(/!important/, '').trim();
			const number = /^(\d*\.?\d+)(%?)$/.exec(value);
			const where = `${rule.file} ${rule.selector}: ${kind} ${raw.trim()}`;
			if (!number) {
				problems.push(`${where} (not a plain number)`);
				continue;
			}
			const level = Number(number[1]) / (number[2] ? 100 : 1);
			if (stop && !firstStop && level < 1) problems.push(where);
			else if (!stop && kind === 'filter: opacity()' && level < 1) problems.push(where);
			else if (!stop && level > 0 && level < 1) problems.push(where);
		}
	}
	return problems;
};

/** Colour or opacity set where the stylesheet scan cannot see it: inline styles, style directives, script. */
export const offSheetColour = (files: { path: string; text: string }[]): string[] => {
	const property = '(?:color|opacity|filter|background(?:-color)?|-webkit-text-fill-color|fill|stroke)';
	const markup = [new RegExp(`style="[^"]*\\b${property}\\s*:`), new RegExp(`style:${property}\\b`)];
	const script = [/\.style\.(?:color|opacity|filter|background|backgroundColor|webkitTextFillColor|fill|stroke)\b/, new RegExp(`setProperty\\(\\s*['"]${property}['"]`)];
	return files.flatMap(({ path, text }) => {
		const checks = path.endsWith('.ts') ? script : markup;
		return text
			.split('\n')
			.map((line, index) => ({ line: index + 1, text: line }))
			.filter(({ text: line }) => checks.some((check) => check.test(line)) || /-webkit-text-fill-color/.test(line))
			.map(({ line, text: content }) => `${path}:${line}: ${content.trim()}`);
	});
};

const tokenIn = (body: string, property: RegExp): string | undefined => property.exec(body)?.[1];

/** The step tones from tutorial.css: each class's --on ink on its --tone material. */
const tones: [string, string][] = rules
	.filter((rule) => /^\.t[1-5r]$/.test(rule.selector))
	.map((rule) => [tokenIn(rule.body, /--on:\s*var\((--[\w-]+)\)/)!, tokenIn(rule.body, /--tone:\s*var\((--[\w-]+)\)/)!]);

interface Pair {
	ink: string;
	material: string;
	where: string;
}

const pairs: Pair[] = [];
const unplaced: string[] = [];
for (const rule of rules) {
	const ink = tokenIn(rule.body, /(?:^|[;\s])color:\s*var\((--[\w-]+)\)/);
	if (!ink) continue;
	const where = `${rule.file} ${rule.selector}`;
	if (ink === '--link') {
		pairs.push({ ink: '--desk-link', material: '--desk', where }, { ink: '--accent', material: '--surface', where });
		continue;
	}
	if (ink === '--on') {
		for (const [on, tone] of tones) pairs.push({ ink: on, material: tone, where: `${where} (${on} on ${tone})` });
		continue;
	}
	const own = tokenIn(rule.body, /background(?:-color)?:\s*var\((--[\w-]+)\)/);
	const placed = own ?? MATERIAL.find(([file, selector]) => file.test(rule.file) && selector.test(rule.selector))?.[2];
	if (placed) pairs.push({ ink, material: placed, where });
	else unplaced.push(where);
}

/** Every `color:` declaration and every `opacity:` declaration, with where it is. */
const declarations = (property: string): { where: string; selector: string; value: string }[] =>
	rules.flatMap((rule) =>
		[...rule.body.matchAll(new RegExp(`(?:^|[;\\s])${property}:\\s*([^;]+)`, 'g'))].map((match) => ({
			where: `${rule.file} ${rule.selector}`,
			selector: rule.selector,
			value: match[1]!.trim(),
		})),
	);

describe('the forms of colour the contrast check can measure', () => {
	it('sets every text colour through a theme token, never a mix, currentColor or a named colour', () => {
		const unmeasurable = declarations('color')
			.filter(({ value }) => !/^var\(--[\w-]+(?:,\s*var\(--[\w-]+\))?\)$|^inherit$/.test(value))
			.map(({ where, value }) => `${where}: color: ${value}`);
		expect(unmeasurable).toEqual([]);
	});

	it('dims nothing, in any form', () => {
		expect(dimmings(rules)).toEqual([]);
	});

	it('reads every form of dimming the review found passing unseen', () => {
		const probe = (selector: string, body: string): Rule => ({ file: 'probe.css', selector, body });
		const found = dimmings([
			probe('.a', 'opacity: 30%'),
			probe('.b', 'filter: drop-shadow(0 0 1px black) opacity(0.3)'),
			probe('.c', 'opacity: 0.3 !important'),
			probe('.d', 'opacity: var(--dim)'),
			probe('to', 'opacity: 0'),
			probe('50%', 'opacity: 0.5'),
			probe('from', 'opacity: 0'),
			probe('.leaving', 'opacity: 0'),
			probe('.solid', 'opacity: 1'),
		]);
		expect(found.map((line) => line.split(' ')[1])).toEqual(['.a:', '.b:', '.c:', '.d:', 'to:', '50%:']);
	});

	it('sets no colour or opacity outside a stylesheet: no inline style, style directive or script', () => {
		const files = SOURCES.filter((path) => /\.(svelte|html|ts)$/.test(path)).map((path) => ({ path: relative(SITE, path), text: readFileSync(path, 'utf8') }));
		expect(offSheetColour(files)).toEqual([]);
	});

	it('catches colour set by an inline style, a style directive, script or text fill', () => {
		const found = offSheetColour([
			{ path: 'a.svelte', text: '<h4 style="color:silver">' },
			{ path: 'b.svelte', text: '<h4 style:color="silver">' },
			{ path: 'c.svelte', text: '.motto { -webkit-text-fill-color: var(--surface) }' },
			{ path: 'd.ts', text: "note.style.opacity = '0.3';" },
			{ path: 'e.svelte', text: '<div style="display: contents">' },
			{ path: 'f.svelte', text: '<div style:--states={n}>' },
		]);
		expect(found.map((line) => line.split(':')[0])).toEqual(['a.svelte', 'b.svelte', 'c.svelte', 'd.ts']);
	});
});

/**
 * The one thing that tells an earlier step's mark from the current one: a leader line's stroke, a gutter
 * label's outline. Each must clear 3:1, WCAG's floor for a graphic that carries meaning.
 */
const markers: Pair[] = rules
	.filter((rule) => /\.past\b|pastpin/.test(rule.selector))
	.flatMap((rule) => {
		const where = `${rule.file} ${rule.selector}`;
		const material = MATERIAL.find(([file, selector]) => file.test(rule.file) && selector.test(rule.selector))?.[2] ?? '--unplaced';
		const inks = [
			tokenIn(rule.body, /(?:^|[;\s])stroke:\s*var\((--[\w-]+)\)/),
			tokenIn(rule.body, /box-shadow:[^;]*\binset\b[^;]*var\((--[\w-]+)\)/),
			tokenIn(rule.body, /border-color:\s*var\((--[\w-]+)\)/),
		].filter((ink): ink is string => Boolean(ink));
		return inks.flatMap((ink) =>
			ink === '--tone' ? tones.map(([, tone]) => ({ ink: tone, material, where: `${where} (${tone})` })) : [{ ink, material, where }],
		);
	});

describe('the marks that tell an earlier step apart', () => {
	it('finds the past leader lines and past gutter labels', () => {
		expect(markers.length).toBeGreaterThan(0);
	});

	for (const variant of ['light', 'dark'] as const) {
		for (const { ink, material, where } of markers) {
			it(`${variant}: ${where} draws ${ink} on ${material} at 3:1 or better`, () => {
				expect(tokens[variant][material], `${material} is a token`).toMatch(/^#[0-9A-Fa-f]{6}$/);
				expect(ratio(tokens[variant][ink]!, tokens[variant][material]!)).toBeGreaterThanOrEqual(3);
			});
		}
	}
});

describe('the contrast of every colour rule', () => {
	it('places every rule that sets a text colour on a material', () => {
		expect(unplaced, 'add each to MATERIAL with the material behind it').toEqual([]);
	});

	it('reads the step tones from tutorial.css', () => {
		expect(tones.length).toBe(6);
	});

	for (const variant of ['light', 'dark'] as const) {
		for (const { ink, material, where } of pairs) {
			it(`${variant}: ${where} sets ${ink} on ${material} at 4.5:1 or better`, () => {
				const fg = tokens[variant][ink];
				const bg = tokens[variant][material];
				expect(fg, `${ink} is a token`).toMatch(/^#[0-9A-Fa-f]{6}$/);
				expect(bg, `${material} is a token`).toMatch(/^#[0-9A-Fa-f]{6}$/);
				expect(ratio(fg!, bg!)).toBeGreaterThanOrEqual(4.5);
			});
		}
	}

	it('would have caught the beetroot accent straight on the light desk', () => {
		expect(ratio(tokens.light['--accent']!, tokens.light['--desk']!)).toBeLessThan(4.5);
	});
});
