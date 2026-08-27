#!/usr/bin/env bun
// frame.ts: turn a bare PNG (screenshot, PDF page) into a presentable card:
// gradient background, rounded corners, drop shadow, optional browser chrome.
// Every visual decision comes from the `frame` theme block.
//
//   bun frame.ts <in.png> <out.png> [--project <dir>] [--family <name>]
//                [--chrome | --no-chrome] [--max-width 1600]

import sharp, { type OverlayOptions } from 'sharp';
import { resolveTheme, argValue } from './theme.ts';

interface FrameBlock {
	background: { kind: 'gradient' | 'solid'; stops: string[]; angle_deg: number };
	chrome: 'dark' | 'light' | 'none';
	chrome_colors?: { bar: string; dots: string[] };
	margin_ratio: number;
	radius_px: number;
	shadow: { blur_px: number; offset_y_px: number; opacity: number };
	border: { width_px: number; color: string };
}

function gradientSvg(width: number, height: number, stops: string[], angle: number): Buffer {
	const radians = ((angle - 90) * Math.PI) / 180;
	const x2 = 0.5 + Math.cos(radians) / 2;
	const y2 = 0.5 + Math.sin(radians) / 2;
	const x1 = 1 - x2;
	const y1 = 1 - y2;
	const stopTags = stops
		.map((stop, index) => `<stop offset="${(index / (stops.length - 1)).toFixed(3)}" stop-color="${stop}"/>`)
		.join('');
	return Buffer.from(
		`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><defs><linearGradient id="g" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}">${stopTags}</linearGradient></defs><rect width="${width}" height="${height}" fill="url(#g)"/></svg>`,
	);
}

function roundedMask(width: number, height: number, radius: number): Buffer {
	return Buffer.from(
		`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><rect width="${width}" height="${height}" rx="${radius}" ry="${radius}" fill="#fff"/></svg>`,
	);
}

function chromeBar(width: number, height: number, bar: string, dots: string[], radius: number): Buffer {
	const circles = dots
		.map((dot, index) => `<circle cx="${18 + index * 20}" cy="${height / 2}" r="6" fill="${dot}"/>`)
		.join('');
	return Buffer.from(
		`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><path d="M0,${height} L0,${radius} Q0,0 ${radius},0 L${width - radius},0 Q${width},0 ${width},${radius} L${width},${height} Z" fill="${bar}"/>${circles}</svg>`,
	);
}

// Only these three flags take a value; --chrome/--no-chrome are bare
// booleans. Treating every preceding "--flag" as value-consuming (the old
// rule) swallowed a positional whenever a boolean flag came first (see
// PR #16 review, Finding 2).
const VALUE_FLAGS = new Set(['--project', '--family', '--max-width']);

async function main(): Promise<void> {
	const args = process.argv.slice(2);
	const positional = args.filter((arg, index) => !arg.startsWith('--') && !VALUE_FLAGS.has(args[index - 1] ?? ''));
	const [input, output] = positional;
	if (!input || !output) {
		console.error('usage: frame.ts <in.png> <out.png> [--project <dir>] [--family <name>] [--chrome|--no-chrome] [--max-width N]');
		process.exit(1);
	}

	const theme = resolveTheme('frame', argValue(args, '--project') ?? process.cwd(), argValue(args, '--family'));
	const block = theme.block as unknown as FrameBlock;
	const maxWidth = Number(argValue(args, '--max-width') ?? 1600);
	const wantChrome = args.includes('--chrome') ? true : args.includes('--no-chrome') ? false : block.chrome !== 'none';

	const source = sharp(input).resize(maxWidth, null, { fit: 'inside', withoutEnlargement: true });
	const shot = await source.png().toBuffer();
	const meta = await sharp(shot).metadata();
	const width = meta.width ?? 0;
	const height = meta.height ?? 0;

	const chromeHeight = wantChrome ? 36 : 0;
	const cardWidth = width;
	const cardHeight = height + chromeHeight;

	// Card: optional chrome bar on top of the shot, then rounded.
	const layers: OverlayOptions[] = [];
	if (wantChrome) {
		const colours = block.chrome_colors ?? { bar: block.chrome === 'light' ? '#E8E8EA' : '#1F1F24', dots: ['#FF5F57', '#FEBC2E', '#28C840'] };
		layers.push({ input: chromeBar(cardWidth, chromeHeight, colours.bar, colours.dots, block.radius_px), top: 0, left: 0 });
	}
	layers.push({ input: shot, top: chromeHeight, left: 0 });
	const cardRaw = await sharp({ create: { width: cardWidth, height: cardHeight, channels: 4, background: block.border.color } })
		.composite(layers)
		.png()
		.toBuffer();
	const card = await sharp(cardRaw)
		.composite([{ input: roundedMask(cardWidth, cardHeight, block.radius_px), blend: 'dest-in' }])
		.png()
		.toBuffer();

	// Border: a slightly larger rounded rect behind the card.
	const borderWidth = block.border.width_px;
	const borderRect = Buffer.from(
		`<svg xmlns="http://www.w3.org/2000/svg" width="${cardWidth + borderWidth * 2}" height="${cardHeight + borderWidth * 2}"><rect width="100%" height="100%" rx="${block.radius_px + borderWidth}" fill="${block.border.color}"/></svg>`,
	);

	const margin = Math.round(Math.max(cardWidth, cardHeight) * block.margin_ratio);
	const canvasWidth = cardWidth + margin * 2;
	const canvasHeight = cardHeight + margin * 2;

	const shadow = await sharp(
		Buffer.from(
			`<svg xmlns="http://www.w3.org/2000/svg" width="${canvasWidth}" height="${canvasHeight}"><rect x="${margin}" y="${margin + block.shadow.offset_y_px}" width="${cardWidth}" height="${cardHeight}" rx="${block.radius_px}" fill="rgba(0,0,0,${block.shadow.opacity})"/></svg>`,
		),
	)
		.blur(block.shadow.blur_px / 2)
		.png()
		.toBuffer();

	const background =
		block.background.kind === 'gradient'
			? gradientSvg(canvasWidth, canvasHeight, block.background.stops, block.background.angle_deg)
			: Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${canvasWidth}" height="${canvasHeight}"><rect width="100%" height="100%" fill="${block.background.stops[0]}"/></svg>`);

	await sharp(background)
		.composite([
			{ input: shadow, top: 0, left: 0 },
			{ input: borderRect, top: margin - borderWidth, left: margin - borderWidth },
			{ input: card, top: margin, left: margin },
		])
		.png()
		.toFile(output);

	console.log(`${output} (${canvasWidth}×${canvasHeight}, theme ${theme.family}/${theme.scope})`);
}

main().catch((error: Error) => {
	console.error(error.message);
	process.exit(1);
});
