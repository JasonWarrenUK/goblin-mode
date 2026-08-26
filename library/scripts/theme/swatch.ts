#!/usr/bin/env bun
// swatch.ts: render a self-contained HTML swatch page for one family or all.
//
//   bun swatch.ts --themes-dir <dir> [--family <name>] -o out.html
//
// Shows both variants of the core palette, the gradient, contrast ratios and
// whichever target files exist alongside the core, so `theme-factory display`
// has one thing to publish. Follows the Artifact rules: light tokens on :root,
// dark under prefers-color-scheme (guarded) and [data-theme="dark"].

import { readFileSync, writeFileSync, readdirSync, existsSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { contrastRatio } from './colour.ts';

interface Swatch {
	light: string;
	dark: string;
	role?: string;
}

interface ThemeCore {
	family: string;
	rationale: { mood: string; inspiration: string; anchor_reason: string; rule_bent: string };
	anchor: { name: string; hex: string };
	palette: Record<string, Swatch>;
	gradient: { light: string[]; dark: string[] };
	typography: { display: { family: string }; body: { family: string }; mono: { family: string } };
	contrast: Record<'light' | 'dark', { fg: string; bg: string; level: string; ratio: number | null }[]>;
	provenance: { created: string | null; seed: string | null };
}

function escapeHtml(text: string): string {
	return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function loadFamilies(dir: string, only: string | null): { core: ThemeCore; targets: string[] }[] {
	if (!existsSync(dir)) return [];
	const files = readdirSync(dir).filter((file) => file.endsWith('.json') && file !== 'seen.json');
	const cores = files.filter((file) => !file.includes('-'));
	return cores
		.map((file) => {
			const core = JSON.parse(readFileSync(join(dir, file), 'utf8')) as ThemeCore;
			const targets = files
				.filter((other) => other.startsWith(`${core.family}-`))
				.map((other) => other.slice(core.family.length + 1, -5));
			return { core, targets };
		})
		.filter(({ core }) => !only || core.family === only);
}

function renderVariant(core: ThemeCore, variant: 'light' | 'dark'): string {
	const swatches = Object.entries(core.palette)
		.map(([name, swatch]) => {
			const hex = swatch[variant];
			const onSurface = contrastRatio(hex, core.palette.surface[variant]);
			return `<div class="swatch" style="background:${hex}">
	<span class="chip" style="background:${core.palette.surface[variant]};color:${core.palette.ink[variant]}">${name}<br><code>${hex}</code><br><small>${onSurface}:1 on surface</small></span>
</div>`;
		})
		.join('\n');
	const gradient = `linear-gradient(135deg, ${core.gradient[variant].join(', ')})`;
	const contrast = core.contrast[variant]
		.map((rule) => {
			const ratio = rule.ratio ?? contrastRatio(core.palette[rule.fg][variant], core.palette[rule.bg][variant]);
			return `<tr><td>${rule.fg}</td><td>${rule.bg}</td><td>${rule.level}</td><td>${ratio}:1</td></tr>`;
		})
		.join('');
	return `<section class="variant" style="background:${core.palette.surface[variant]};color:${core.palette.ink[variant]};border-color:${core.palette.line[variant]}">
	<h3>${variant}</h3>
	<div class="grid">${swatches}</div>
	<div class="gradient" style="background:${gradient}"></div>
	<p style="font-family:'${core.typography.display.family}', system-ui;font-size:1.6rem;margin:.5rem 0 0">Display: ${escapeHtml(core.typography.display.family)}</p>
	<p style="font-family:'${core.typography.body.family}', system-ui">Body: ${escapeHtml(core.typography.body.family)}. The quick brown fox jumps over the lazy dog.</p>
	<p style="font-family:'${core.typography.mono.family}', ui-monospace, monospace;background:${core.palette['surface-raised'][variant]};padding:.5rem;border-radius:6px">Mono: ${escapeHtml(core.typography.mono.family)} · const x = 42;</p>
	<table><thead><tr><th>fg</th><th>bg</th><th>level</th><th>ratio</th></tr></thead><tbody>${contrast}</tbody></table>
</section>`;
}

function renderFamily({ core, targets }: { core: ThemeCore; targets: string[] }): string {
	return `<article class="family">
	<header>
		<h2>${escapeHtml(core.family)} <small>anchor ${escapeHtml(core.anchor.name)} <code>${core.anchor.hex}</code></small></h2>
		<p class="mood">${escapeHtml(core.rationale.mood)}</p>
		<dl>
			<dt>Inspiration</dt><dd>${escapeHtml(core.rationale.inspiration)}</dd>
			<dt>Anchor</dt><dd>${escapeHtml(core.rationale.anchor_reason)}</dd>
			<dt>Rule bent</dt><dd>${escapeHtml(core.rationale.rule_bent)}</dd>
			<dt>Targets</dt><dd>${targets.length ? targets.map(escapeHtml).join(', ') : 'core only'}</dd>
		</dl>
	</header>
	${renderVariant(core, 'light')}
	${renderVariant(core, 'dark')}
</article>`;
}

function main(): void {
	const args = process.argv.slice(2);
	const dirIndex = args.indexOf('--themes-dir');
	const familyIndex = args.indexOf('--family');
	const outIndex = args.indexOf('-o');
	if (dirIndex < 0 || outIndex < 0) {
		console.error('usage: swatch.ts --themes-dir <dir> [--family <name>] -o out.html');
		process.exit(1);
	}
	const families = loadFamilies(resolve(args[dirIndex + 1]), familyIndex >= 0 ? args[familyIndex + 1] : null);
	if (families.length === 0) {
		console.error('No theme families found');
		process.exit(1);
	}
	const title = families.length === 1 ? `${families[0].core.family} theme` : 'Theme swatches';
	const html = `<title>${escapeHtml(title)}</title>
<style>
:root { --page: #F4F2EE; --page-ink: #1B1B1F; --rule: #D6D2CA; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --page: #141417; --page-ink: #ECEAE4; --rule: #2C2C32; } }
:root[data-theme="dark"] { --page: #141417; --page-ink: #ECEAE4; --rule: #2C2C32; }
body { background: var(--page); color: var(--page-ink); font-family: system-ui, sans-serif; margin: 0; padding: 2rem; }
.family { max-width: 72rem; margin: 0 auto 3rem; }
.family header { margin-bottom: 1rem; }
.family h2 small { font-weight: 400; opacity: .7; font-size: .6em; }
.mood { font-size: 1.1rem; margin: .25rem 0 .75rem; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: .25rem 1rem; font-size: .9rem; }
dt { opacity: .6; }
dd { margin: 0; }
.variant { border: 1px solid; border-radius: 12px; padding: 1.25rem; margin-bottom: 1rem; }
.variant h3 { margin: 0 0 .75rem; text-transform: uppercase; letter-spacing: .1em; font-size: .8rem; opacity: .7; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr)); gap: .5rem; }
.swatch { height: 6.5rem; border-radius: 8px; display: flex; align-items: flex-end; padding: .4rem; }
.chip { font-size: .7rem; line-height: 1.3; padding: .3rem .4rem; border-radius: 4px; }
.gradient { height: 2.5rem; border-radius: 8px; margin-top: .75rem; }
table { border-collapse: collapse; font-size: .8rem; margin-top: .75rem; }
th, td { text-align: left; padding: .2rem .6rem .2rem 0; border-bottom: 1px solid currentColor; opacity: .85; }
</style>
${families.map(renderFamily).join('\n')}
`;
	writeFileSync(args[outIndex + 1], html);
	console.log(args[outIndex + 1]);
}

main();
