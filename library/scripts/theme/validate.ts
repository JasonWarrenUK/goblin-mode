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
const CORE_TEMPLATE_PATH = resolve(SCRIPT_DIR, '../../templates/themes/core.json');
const CORE_SCHEMA = 'clod-theme/core@1';

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
	swatches: Record<string, Oklch>;
}

function loadJson<T>(path: string): T {
	return JSON.parse(readFileSync(path, 'utf8')) as T;
}

function signatureOf(theme: ThemeCore, source: string): Signature {
	const swatches: Record<string, Oklch> = {};
	for (const key of SIGNATURE_KEYS) {
		const swatch = theme.palette[key];
		if (!swatch) continue;
		swatches[`${key}.light`] = hexToOklch(swatch.light);
		swatches[`${key}.dark`] = hexToOklch(swatch.dark);
	}
	return { family: theme.family, source, swatches };
}

// Compares only the swatch names present on both sides, so a theme missing
// one signature swatch is never diffed against a shifted, misnamed entry
// on the other side (see PR #16 review: positional comparison silently
// paired unrelated swatches once one side was short).
function signatureDistance(a: Signature, b: Signature): number {
	const sharedKeys = Object.keys(a.swatches).filter((key) => key in b.swatches);
	if (sharedKeys.length === 0) return Infinity;
	let total = 0;
	for (const key of sharedKeys) {
		total += deltaOk(a.swatches[key], b.swatches[key]);
	}
	return total / sharedKeys.length;
}

// Diffs the candidate against core.json's own key shape, so a theme missing
// an entire block (no "gradient", no "contrast") is caught here rather than
// producing a clean report and then crashing checkContrast/checkGradient
// with an uncaught TypeError (see PR #16 review, Finding 1).
function checkCompleteness(theme: ThemeCore, findings: Finding[]): void {
	const template = loadJson<Record<string, unknown>>(CORE_TEMPLATE_PATH);

	const walkAgainstTemplate = (templateNode: unknown, candidateNode: unknown, path: string): void => {
		if (templateNode === null) return; // a template leaf: any concrete value on the candidate satisfies it
		if (Array.isArray(templateNode)) {
			if (!Array.isArray(candidateNode) || candidateNode.length < templateNode.length) {
				findings.push({ severity: 'fail', check: 'completeness', detail: `${path} is missing entries` });
				return;
			}
			templateNode.forEach((item, index) => walkAgainstTemplate(item, candidateNode[index], `${path}[${index}]`));
			return;
		}
		if (typeof templateNode === 'object') {
			if (typeof candidateNode !== 'object' || candidateNode === null) {
				findings.push({ severity: 'fail', check: 'completeness', detail: `${path || '(root)'} is missing` });
				return;
			}
			for (const [key, value] of Object.entries(templateNode as Record<string, unknown>)) {
				if (key === '$schema' || key === 'version') continue;
				const childPath = path ? `${path}.${key}` : key;
				if (!(key in (candidateNode as Record<string, unknown>))) {
					findings.push({ severity: 'fail', check: 'completeness', detail: `${childPath} is missing` });
					continue;
				}
				walkAgainstTemplate(value, (candidateNode as Record<string, unknown>)[key], childPath);
			}
		}
	};
	walkAgainstTemplate(template, theme, '');

	// The template diff confirms every key exists; this catches values that
	// exist but were never filled in (still null, copied straight from the
	// template).
	const walkNulls = (node: unknown, path: string): void => {
		if (node === null) {
			findings.push({ severity: 'fail', check: 'completeness', detail: `${path} is null` });
			return;
		}
		if (Array.isArray(node)) {
			node.forEach((item, index) => walkNulls(item, `${path}[${index}]`));
			return;
		}
		if (typeof node === 'object') {
			for (const [key, value] of Object.entries(node as Record<string, unknown>)) {
				if (key === 'ratio' || key === 'derived_from' || key === 'updated') continue;
				walkNulls(value, path ? `${path}.${key}` : key);
			}
		}
	};
	walkNulls(theme, '');
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
			if (!file.endsWith('.json') || file === 'seen.json') continue;
			const candidate = loadJson<ThemeCore & { $schema?: string }>(join(dir, file));
			// Identify cores by their declared schema, not by "no hyphen in the
			// filename" — a hand-named core with a hyphen was silently skipped
			// under the old filter, and worse, dropped out of the originality
			// comparison set with no warning (see PR #16 review, Finding 11).
			if (candidate.$schema !== CORE_SCHEMA) continue;
			if (candidate.family === skipFamily || !candidate.palette) continue;
			signatures.push(signatureOf(candidate, join(dir, file)));
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
	// blocklist.json stores swatches as a flat hex array in SIGNATURE_KEYS
	// order (light, dark per key); key them the same way signatureOf does
	// so the comparison below can never pair a shifted, misnamed swatch.
	const blockedKeyOrder = SIGNATURE_KEYS.flatMap((key) => [`${key}.light`, `${key}.dark`]);
	for (const entry of blocklist) {
		const swatches: Record<string, Oklch> = {};
		blockedKeyOrder.slice(0, entry.swatches.length).forEach((key, index) => {
			swatches[key] = hexToOklch(entry.swatches[index]);
		});
		const blocked: Signature = { family: entry.name, source: 'blocklist', swatches };
		const distance = signatureDistance(mine, blocked);
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
	// --themes-dir takes a value, so its value must never be picked up as
	// the path when the flag comes first (see PR #16 review, Finding 5).
	const path = args.find((arg, index) => !arg.startsWith('--') && args[index - 1] !== '--themes-dir');
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

	try {
		checkCompleteness(theme, findings);
		if (findings.length === 0) {
			checkRationale(theme, findings);
			checkContrast(theme, findings);
			checkGradient(theme, findings);
			checkHueFamilies(theme, findings);
			checkOriginality(theme, [projectThemesDir, GLOBAL_THEMES_DIR], findings);
		}
	} catch (error) {
		// A gate crashing (rather than reporting a finding) is itself a
		// completeness bug; degrade to a FAIL finding instead of a raw
		// stack trace so the documented "exit 1 with findings" contract
		// holds even when a check hits something it didn't expect.
		findings.push({
			severity: 'fail',
			check: 'internal',
			detail: `a check crashed instead of reporting a finding: ${error instanceof Error ? error.message : String(error)}`,
		});
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
