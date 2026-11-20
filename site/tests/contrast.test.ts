// Every pair of text and background colour the site sets small text in, read from the
// goblin theme's tokens and held to WCAG AA's 4.5:1, in both variants. A pair is listed
// here because the CSS puts that ink on that material; a new pairing belongs here first.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

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

/** [ink, material]: where each ink is set as small text. */
const PAIRS: [string, string][] = [
	['--ink', '--desk'],
	['--desk-link', '--desk'],
	['--ink', '--surface'],
	['--accent', '--surface'],
	['--ink-muted', '--surface'],
	['--ink', '--surface-raised'],
	['--accent', '--surface-raised'],
	['--ink-muted', '--surface-raised'],
	['--slip-ink', '--slip'],
	['--slip-accent', '--slip'],
	['--slip-muted', '--slip'],
	['--exhibit-ink', '--exhibit'],
	['--exhibit-muted', '--exhibit'],
	['--accent-ink', '--accent'],
	['--card-ink', '--card'],
	['--on-slime', '--slime'],
];

describe.each(['light', 'dark'] as const)('the %s theme', (variant) => {
	for (const [ink, material] of PAIRS) {
		it(`sets ${ink} on ${material} at 4.5:1 or better`, () => {
			const fg = tokens[variant][ink];
			const bg = tokens[variant][material];
			expect(fg, `${ink} is a token`).toMatch(/^#[0-9A-Fa-f]{6}$/);
			expect(bg, `${material} is a token`).toMatch(/^#[0-9A-Fa-f]{6}$/);
			expect(ratio(fg!, bg!)).toBeGreaterThanOrEqual(4.5);
		});
	}

	it('would have caught the beetroot accent straight on the light desk', () => {
		if (variant === 'light') expect(ratio(tokens.light['--accent']!, tokens.light['--desk']!)).toBeLessThan(4.5);
	});
});
