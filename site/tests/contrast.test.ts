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
	[/tutorial\.css$/, /\.co\b|\.exercise\b/, '--slip'],
	// a bare `code` selector reaches the code panel (an exhibit) as well as inline code, so the panel is what it must clear
	[/tutorial\.css$/, /(^| )code$/, '--exhibit'],
	[/tutorial\.css$/, /\.kicker|\.how|\.snap-title|\.pin-title|\.pin-file|\.spec-state|\.stepnav|\.step\b/, '--surface'],
	[/\[mod\]\/\+page\.svelte$/, /^\.num$|^\.facts$/, '--surface'],
];

/**
 * Elements dimmed below full opacity, each with the reason no text is dimmed with it. Text is never
 * thinned: a past or pending state is marked by an outline, a dashed border or a tag instead.
 */
const DIMMED_WITHOUT_TEXT: [RegExp, string][] = [
	[/^\.tutorial \.leaders \.past$/, 'an earlier callout\'s leader line and dot, drawn in SVG strokes with no text'],
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

/** Every rule in the site's stylesheets and component <style> blocks, media queries flattened. */
const rules: Rule[] = walk(SRC)
	.filter((path) => /\.(css|svelte)$/.test(path))
	.flatMap((path) => {
		let text = readFileSync(path, 'utf8');
		if (path.endsWith('.svelte')) text = /<style>([\s\S]*?)<\/style>/.exec(text)?.[1] ?? '';
		text = text.replace(/\/\*[\s\S]*?\*\//g, '');
		return [...text.matchAll(/([^{}@]+)\{([^{}]*)\}/g)].flatMap((match) =>
			topLevel(match[1]!)
				.map((one) => one.replace(/:global\(([^)]*)\)/g, '$1').trim().replace(/\s+/g, ' '))
				.filter(Boolean)
				.map((selector) => ({ file: relative(SITE, path), selector, body: match[2]! })),
		);
	});

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

	it('dims nothing that holds text', () => {
		const dimmed = declarations('opacity')
			.filter(({ value }) => Number(value) > 0 && Number(value) < 1)
			.filter(({ selector }) => !DIMMED_WITHOUT_TEXT.some(([pattern]) => pattern.test(selector)))
			.map(({ where, value }) => `${where}: opacity: ${value}`);
		expect(dimmed).toEqual([]);
	});
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
