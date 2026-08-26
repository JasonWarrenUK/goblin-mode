#!/usr/bin/env bun
// card.ts: render a social card (OG 1200×630 or GitHub 1280×640) from a
// card.json spec and the `card` theme block, via satori → resvg.
//
//   bun card.ts <card.json> <out.png> [--size og|github] [--project <dir>] [--family <name>]
//
// card.json:
//   { "title": "…", "tagline": "…", "meta": "…", "hero": "docs/assets/shots/home.png" | null, "logo": null }
//
// Layout: accent bar top, logo/meta row, title + tagline on the left, hero
// screenshot on the right when present. One template, parameterised; the
// look comes from the theme.

import { readFileSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import satori from 'satori';
import { Resvg } from '@resvg/resvg-js';
import sharp from 'sharp';
import { resolveTheme, argValue } from './theme.ts';

const SCRIPT_DIR = new URL('.', import.meta.url).pathname;
const FONTS_DIR = join(SCRIPT_DIR, 'fonts');

interface CardSpec {
	title: string;
	tagline?: string;
	meta?: string;
	hero?: string | null;
	logo?: string | null;
}

interface TextStyle {
	color: string;
	font: string;
	weight: number;
	size_px: number;
	max_lines?: number;
}

interface CardBlock {
	background: { kind: 'gradient' | 'solid'; stops: string[]; angle_deg: number };
	title: TextStyle;
	tagline: TextStyle;
	meta: TextStyle;
	hero: { frame_color: string; radius_px: number; shadow: boolean; max_width_ratio: number };
	logo: { path: string | null; size_px: number; position: string };
	accent_bar?: { color: string; height_px: number };
	padding_px: number;
	sizes: Record<string, [number, number]>;
}

type FontFile = NonNullable<Parameters<typeof satori>[1]['fonts']>[number];

function fontFile(family: string, weight: number): string | null {
	const slug = family.replace(/\s+/g, '');
	const candidates = ['woff', 'ttf', 'otf'].flatMap((extension) => [
		join(FONTS_DIR, `${slug}-${weight}.${extension}`),
		join(FONTS_DIR, `${slug}-400.${extension}`),
		join(FONTS_DIR, `${slug}.${extension}`),
	]);
	return candidates.find((candidate) => existsSync(candidate)) ?? null;
}

async function loadFonts(styles: TextStyle[]): Promise<FontFile[]> {
	const fonts: FontFile[] = [];
	const seen = new Set<string>();
	for (const style of styles) {
		const key = `${style.font}:${style.weight}`;
		if (seen.has(key)) continue;
		seen.add(key);
		const path = fontFile(style.font, style.weight);
		if (!path) {
			throw new Error(`No font file for ${style.font} ${style.weight} in ${FONTS_DIR}; run \`bun fonts.ts\` or drop a static (non-variable) WOFF/TTF named ${style.font.replace(/\s+/g, '')}-${style.weight}.woff there`);
		}
		fonts.push({ name: style.font, data: await Bun.file(path).arrayBuffer(), weight: style.weight as FontFile['weight'], style: 'normal' });
	}
	return fonts;
}

async function heroDataUri(path: string, maxWidth: number, radius: number): Promise<{ uri: string; width: number; height: number }> {
	const buffer = await sharp(path).resize(maxWidth, null, { fit: 'inside' }).png().toBuffer();
	const meta = await sharp(buffer).metadata();
	const width = meta.width ?? maxWidth;
	const height = meta.height ?? 0;
	const mask = Buffer.from(`<svg width="${width}" height="${height}"><rect width="${width}" height="${height}" rx="${radius}" fill="#fff"/></svg>`);
	const rounded = await sharp(buffer).composite([{ input: mask, blend: 'dest-in' }]).png().toBuffer();
	return { uri: `data:image/png;base64,${rounded.toString('base64')}`, width, height };
}

function gradientCss(block: CardBlock['background']): string {
	return block.kind === 'gradient' ? `linear-gradient(${block.angle_deg}deg, ${block.stops.join(', ')})` : block.stops[0];
}

function text(style: TextStyle, content: string, extra: Record<string, unknown> = {}): Record<string, unknown> {
	return {
		type: 'div',
		props: {
			style: {
				display: 'flex',
				color: style.color,
				fontFamily: style.font,
				fontWeight: style.weight,
				fontSize: `${style.size_px}px`,
				lineHeight: 1.15,
				...extra,
			},
			children: content,
		},
	};
}

async function main(): Promise<void> {
	const args = process.argv.slice(2);
	const positional = args.filter((arg, index) => !arg.startsWith('--') && !args[index - 1]?.startsWith('--'));
	const [specPath, output] = positional;
	if (!specPath || !output) {
		console.error('usage: card.ts <card.json> <out.png> [--size og|github] [--project <dir>] [--family <name>]');
		process.exit(1);
	}
	const projectDir = argValue(args, '--project') ?? process.cwd();
	const theme = resolveTheme('card', projectDir, argValue(args, '--family'));
	const block = theme.block as unknown as CardBlock;
	const sizeKey = argValue(args, '--size') ?? 'og';
	const [width, height] = block.sizes[sizeKey] ?? block.sizes.og;

	const spec = JSON.parse(readFileSync(specPath, 'utf8')) as CardSpec;
	const fonts = await loadFonts([block.title, block.tagline, block.meta]);
	const pad = block.padding_px;

	const heroPath = spec.hero ? resolve(dirname(resolve(specPath)), spec.hero) : null;
	const hero = heroPath && existsSync(heroPath)
		? await heroDataUri(heroPath, Math.round(width * block.hero.max_width_ratio), block.hero.radius_px)
		: null;

	const leftColumn = {
		type: 'div',
		props: {
			style: { display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', flex: 1, gap: '20px', paddingRight: hero ? '40px' : '0' },
			children: [
				text(block.title, spec.title),
				spec.tagline ? text(block.tagline, spec.tagline) : null,
			].filter(Boolean),
		},
	};

	const heroColumn = hero
		? {
			type: 'div',
			props: {
				style: {
					display: 'flex',
					alignItems: 'flex-end',
					width: `${hero.width}px`,
					borderRadius: `${block.hero.radius_px}px`,
					border: `2px solid ${block.hero.frame_color}`,
					boxShadow: block.hero.shadow ? '0 20px 50px rgba(0,0,0,0.45)' : 'none',
					overflow: 'hidden',
				},
				children: { type: 'img', props: { src: hero.uri, width: hero.width, height: hero.height } },
			},
		}
		: null;

	const root = {
		type: 'div',
		props: {
			style: {
				display: 'flex',
				flexDirection: 'column',
				width: `${width}px`,
				height: `${height}px`,
				background: gradientCss(block.background),
			},
			children: [
				block.accent_bar ? { type: 'div', props: { style: { display: 'flex', height: `${block.accent_bar.height_px}px`, width: '100%', background: block.accent_bar.color } } } : null,
				{
					type: 'div',
					props: {
						style: { display: 'flex', flexDirection: 'column', flex: 1, padding: `${pad}px` },
						children: [
							spec.meta ? text(block.meta, spec.meta) : null,
							{
								type: 'div',
								props: {
									style: { display: 'flex', flex: 1, alignItems: 'flex-end', paddingTop: '24px' },
									children: [leftColumn, heroColumn].filter(Boolean),
								},
							},
						].filter(Boolean),
					},
				},
			].filter(Boolean),
		},
	};

	const svg = await satori(root as never, { width, height, fonts });
	const png = new Resvg(svg, { fitTo: { mode: 'width', value: width } }).render().asPng();
	await Bun.write(output, png);
	console.log(`${output} (${width}×${height}, theme ${theme.family}/${theme.scope})`);
}

main().catch((error: Error) => {
	console.error(error.message);
	process.exit(1);
});
