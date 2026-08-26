#!/usr/bin/env bun
// validate.ts: the mechanical and originality gates for a theme core file.
//
//   bun validate.ts <family>.json [--themes-dir <dir>] [--register] [--json]
//
// Exit codes: 0 pass, 1 fail (mechanical), 2 warn-only (originality). The
// skill treats 2 as "stop and ask": only an explicit user instruction lifts
// it. --register appends the theme's signature to library/themes/seen.json
// so later themes are compared against it. --json prints the report as JSON.

import { readFileSync, writeFileSync, existsSync, readdirSync } from 'node:fs';
import { join, resolve, basename } from 'node:path';
import {
	contrastRatio,
	CONTRAST_LEVELS,
	hexToOklch,
	deltaOk,
	hueDelta,
	type Oklch,
} from './colour.ts';

const SCRIPT_DIR = new URL('.', import.meta.url).pathname;
const GLOBAL_THEMES_DIR = resolve(SCRIPT_DIR, '../../themes');
const SEEN_PATH = join(GLOBAL_THEMES_DIR, 'seen.json');
const BLOCKLIST_PATH = join(SCRIPT_DIR, 'blocklist.json');

const ORIGINALITY_THRESHOLD = 0.06; // mean deltaOk across signature swatches
const BLOCKLIST_THRESHOLD = 0.05;
const MIN_HUE_SPREAD = 20; // degrees between adjacent gradient stops
const SIGNATURE_KEYS = ['surface', 'surface-raised', 'ink', 'accent', 'accent-2'] as const;

interface Swatch {
	light: string;
	dark: string;
	role?: string;
}

interface ContrastRule {
	fg: string;
	bg: string;
	level: keyof typeof CONTRAST_LEVELS;
	ratio: number | null;
}

interface ThemeCore {
	family: string;
	palette: Record<string, Swatch>;
	gradient: { light: string[]; dark: string[] };
	contrast: { light: ContrastRule[]; dark: ContrastRule[] };
	rationale: Record<string, unknown>;
	monochrome?: boolean;
	provenance?: { seed?: string | null };
}

interface Finding {
	severity: 'fail' | 'warn' | 'info';
	check: string;
	detail: string;
}

interface Signature {
	family: string;
	source: string;
	swatches: Oklch[];
}

function loadJson<T>(path: string): T {
	return JSON.parse(readFileSync(path, 'utf8')) as T;
}

function signatureOf(theme: ThemeCore, source: string): Signature {
	const swatches: Oklch[] = [];
	for (const key of SIGNATURE_KEYS) {
		const swatch = theme.palette[key];
		if (!swatch) continue;
		swatches.push(hexToOklch(swatch.light), hexToOklch(swatch.dark));
	}
	return { family: theme.family, source, swatches };
}

function signatureDistance(a: Signature, b: Signature): number {
	const count = Math.min(a.swatches.length, b.swatches.length);
	if (count === 0) return Infinity;
	let total = 0;
	for (let index = 0; index < count; index += 1) {
		total += deltaOk(a.swatches[index], b.swatches[index]);
	}
	return total / count;
}

function checkCompleteness(theme: ThemeCore, findings: Finding[]): void {
	const walk = (node: unknown, path: string): void => {
		if (node === null) {
			findings.push({ severity: 'fail', check: 'completeness', detail: `${path} is null` });
			return;
		}
		if (Array.isArray(node)) {
			node.forEach((item, index) => walk(item, `${path}[${index}]`));
			return;
		}
		if (typeof node === 'object') {
			for (const [key, value] of Object.entries(node as Record<string, unknown>)) {
				if (key === 'ratio' || key === 'derived_from' || key === 'updated') continue;
				walk(value, path ? `${path}.${key}` : key);
			}
		}
	};
	walk(theme, '');
}

function checkRationale(theme: ThemeCore, findings: Finding[]): void {
	const required = ['mood', 'inspiration', 'anchor_reason', 'rule_bent'];
	for (const key of required) {
		const value = theme.rationale?.[key];
		if (typeof value !== 'string' || value.trim().length < 12) {
			findings.push({
				severity: 'fail',
				check: 'rationale',
				detail: `rationale.${key} must be a sentence, got ${JSON.stringify(value)}`,
			});
		}
	}
	const rejected = theme.rationale?.rejected;
	if (!Array.isArray(rejected) || rejected.length === 0) {
		findings.push({
			severity: 'fail',
			check: 'rationale',
			detail: 'rationale.rejected must list at least one palette that was considered and turned down',
		});
	}
}

function checkContrast(theme: ThemeCore, findings: Finding[]): void {
	for (const variant of ['light', 'dark'] as const) {
		for (const rule of theme.contrast[variant]) {
			const fg = theme.palette[rule.fg]?.[variant];
			const bg = theme.palette[rule.bg]?.[variant];
			if (!fg || !bg) {
				findings.push({
					severity: 'fail',
					check: 'contrast',
					detail: `${variant}: ${rule.fg} on ${rule.bg} references a missing swatch`,
				});
				continue;
			}
			const ratio = contrastRatio(fg, bg);
			rule.ratio = ratio;
			const needed = CONTRAST_LEVELS[rule.level];
			if (needed === undefined) {
				findings.push({ severity: 'fail', check: 'contrast', detail: `unknown level ${rule.level}` });
			} else if (ratio < needed) {
				findings.push({
					severity: 'fail',
					check: 'contrast',
					detail: `${variant}: ${rule.fg} (${fg}) on ${rule.bg} (${bg}) is ${ratio}:1, needs ${needed}:1 for ${rule.level}`,
				});
			}
		}
	}
}

function checkGradient(theme: ThemeCore, findings: Finding[]): void {
	for (const variant of ['light', 'dark'] as const) {
		const stops = theme.gradient[variant].map(hexToOklch);
		if (stops.length < 2) {
			findings.push({ severity: 'fail', check: 'gradient', detail: `${variant}: needs at least two stops` });
			continue;
		}
		const deltas = stops.slice(1).map((stop, index) => stop.l - stops[index].l);
		const monotonic = deltas.every((delta) => delta >= -0.01) || deltas.every((delta) => delta <= 0.01);
		if (!monotonic) {
			findings.push({
				severity: 'fail',
				check: 'gradient',
				detail: `${variant}: lightness must move in one direction across stops (got L ${stops.map((s) => s.l.toFixed(2)).join(' → ')})`,
			});
		}
		for (let index = 1; index < stops.length; index += 1) {
			const spread = hueDelta(stops[index - 1].h, stops[index].h);
			const bothChromatic = stops[index - 1].c > 0.03 && stops[index].c > 0.03;
			if (bothChromatic && spread < MIN_HUE_SPREAD) {
				findings.push({
					severity: 'warn',
					check: 'gradient',
					detail: `${variant}: stops ${index - 1}→${index} are only ${spread.toFixed(0)}° apart in hue; risk of a muddy blend`,
				});
			}
		}
	}
}

function checkHueFamilies(theme: ThemeCore, findings: Finding[]): void {
	if (theme.monochrome) return;
	const hues: number[] = [];
	for (const key of ['accent', 'accent-2', 'ok', 'warn', 'danger', 'info']) {
		const swatch = theme.palette[key];
		if (!swatch) continue;
		const colour = hexToOklch(swatch.dark);
		if (colour.c > 0.03) hues.push(colour.h);
	}
	const families = hues.filter((hue, index) => hues.findIndex((other) => hueDelta(hue, other) < 25) === index);
	if (families.length < 3) {
		findings.push({
			severity: 'fail',
			check: 'hue-families',
			detail: `only ${families.length} distinct hue families among accent/status swatches; need 3, or set "monochrome": true deliberately`,
		});
	}
}

function loadExistingSignatures(themesDirs: string[], skipFamily: string): Signature[] {
	const signatures: Signature[] = [];
	for (const dir of themesDirs) {
		if (!existsSync(dir)) continue;
		for (const file of readdirSync(dir)) {
			if (!file.endsWith('.json') || file.includes('-') || file === 'seen.json') continue;
			const theme = loadJson<ThemeCore>(join(dir, file));
			if (theme.family === skipFamily || !theme.palette) continue;
			signatures.push(signatureOf(theme, join(dir, file)));
		}
	}
	if (existsSync(SEEN_PATH)) {
		const seen = loadJson<Signature[]>(SEEN_PATH);
		for (const entry of seen) {
			if (entry.family !== skipFamily) signatures.push(entry);
		}
	}
	return signatures;
}

function checkOriginality(theme: ThemeCore, themesDirs: string[], findings: Finding[]): void {
	const mine = signatureOf(theme, 'candidate');
	let nearest: { distance: number; signature: Signature } | null = null;
	for (const other of loadExistingSignatures(themesDirs, theme.family)) {
		const distance = signatureDistance(mine, other);
		if (!nearest || distance < nearest.distance) nearest = { distance, signature: other };
	}
	if (nearest) {
		const detail = `nearest existing theme is "${nearest.signature.family}" (${nearest.signature.source}) at distance ${nearest.distance.toFixed(3)}`;
		if (nearest.distance < ORIGINALITY_THRESHOLD) {
			findings.push({ severity: 'warn', check: 'originality', detail: `${detail}; below ${ORIGINALITY_THRESHOLD}. Justify as an intentional variant or shift the anchor.` });
		} else {
			findings.push({ severity: 'info', check: 'originality', detail });
		}
	}

	if (!existsSync(BLOCKLIST_PATH)) return;
	const blocklist = loadJson<{ name: string; why: string; swatches: string[] }[]>(BLOCKLIST_PATH);
	for (const entry of blocklist) {
		const blocked: Signature = { family: entry.name, source: 'blocklist', swatches: entry.swatches.map(hexToOklch) };
		const mineSubset: Signature = { ...mine, swatches: mine.swatches.slice(0, blocked.swatches.length) };
		const distance = signatureDistance(mineSubset, blocked);
		if (distance < BLOCKLIST_THRESHOLD) {
			findings.push({
				severity: 'warn',
				check: 'blocklist',
				detail: `resembles "${entry.name}" (${entry.why}) at distance ${distance.toFixed(3)}`,
			});
		}
	}
}

function main(): void {
	const args = process.argv.slice(2);
	const path = args.find((arg) => !arg.startsWith('--'));
	if (!path) {
		console.error('usage: validate.ts <family>.json [--themes-dir <dir>] [--register] [--json]');
		process.exit(1);
	}
	const themesDirIndex = args.indexOf('--themes-dir');
	const projectThemesDir = themesDirIndex >= 0 ? resolve(args[themesDirIndex + 1]) : resolve(path, '..');
	const register = args.includes('--register');
	const asJson = args.includes('--json');

	const theme = loadJson<ThemeCore>(path);
	const findings: Finding[] = [];

	checkCompleteness(theme, findings);
	if (findings.length === 0) {
		checkRationale(theme, findings);
		checkContrast(theme, findings);
		checkGradient(theme, findings);
		checkHueFamilies(theme, findings);
		checkOriginality(theme, [projectThemesDir, GLOBAL_THEMES_DIR], findings);
	}

	const failed = findings.some((finding) => finding.severity === 'fail');
	const warned = findings.some((finding) => finding.severity === 'warn');

	if (!failed) {
		// Persist computed ratios so the file documents its own guarantee.
		writeFileSync(path, `${JSON.stringify(theme, null, '\t')}\n`);
	}

	if (register && !failed) {
		const seen = existsSync(SEEN_PATH) ? loadJson<Signature[]>(SEEN_PATH) : [];
		const filtered = seen.filter((entry) => entry.family !== theme.family);
		filtered.push(signatureOf(theme, basename(path)));
		writeFileSync(SEEN_PATH, `${JSON.stringify(filtered, null, '\t')}\n`);
	}

	const verdict = failed ? 'FAIL' : warned ? 'WARN' : 'PASS';
	if (asJson) {
		console.log(JSON.stringify({ verdict, family: theme.family, findings }, null, 2));
	} else {
		console.log(`${verdict}: ${theme.family}`);
		for (const finding of findings) {
			console.log(`  [${finding.severity}] ${finding.check}: ${finding.detail}`);
		}
	}
	process.exit(failed ? 1 : warned ? 2 : 0);
}

main();
