// Colour maths shared by the theme scripts. sRGB <-> OKLCH, WCAG contrast,
// perceptual distance. No dependencies: the maths is short and the point is
// that every skill gets the same numbers.

export interface Oklch {
	l: number;
	c: number;
	h: number;
}

export interface Rgb {
	r: number;
	g: number;
	b: number;
}

export function hexToRgb(hex: string): Rgb {
	const clean = hex.replace('#', '').trim();
	if (!/^[0-9a-fA-F]{6}$/.test(clean)) {
		throw new Error(`Not a 6-digit hex colour: ${hex}`);
	}
	return {
		r: parseInt(clean.slice(0, 2), 16) / 255,
		g: parseInt(clean.slice(2, 4), 16) / 255,
		b: parseInt(clean.slice(4, 6), 16) / 255,
	};
}

export function rgbToHex({ r, g, b }: Rgb): string {
	const channel = (value: number): string =>
		Math.round(Math.min(1, Math.max(0, value)) * 255)
			.toString(16)
			.padStart(2, '0');
	return `#${channel(r)}${channel(g)}${channel(b)}`.toUpperCase();
}

function srgbToLinear(channel: number): number {
	return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
}

function linearToSrgb(channel: number): number {
	return channel <= 0.0031308 ? channel * 12.92 : 1.055 * channel ** (1 / 2.4) - 0.055;
}

export function relativeLuminance(hex: string): number {
	const { r, g, b } = hexToRgb(hex);
	return 0.2126 * srgbToLinear(r) + 0.7152 * srgbToLinear(g) + 0.0722 * srgbToLinear(b);
}

export function contrastRatio(foreground: string, background: string): number {
	const lighter = Math.max(relativeLuminance(foreground), relativeLuminance(background));
	const darker = Math.min(relativeLuminance(foreground), relativeLuminance(background));
	return Math.round(((lighter + 0.05) / (darker + 0.05)) * 100) / 100;
}

export const CONTRAST_LEVELS: Record<string, number> = {
	'AA-large': 3,
	AA: 4.5,
	AAA: 7,
};

// Björn Ottosson's OKLab, via linear sRGB.
export function hexToOklch(hex: string): Oklch {
	const { r, g, b } = hexToRgb(hex);
	const lr = srgbToLinear(r);
	const lg = srgbToLinear(g);
	const lb = srgbToLinear(b);

	const l = Math.cbrt(0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb);
	const m = Math.cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb);
	const s = Math.cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb);

	const labL = 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s;
	const labA = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s;
	const labB = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s;

	const chroma = Math.sqrt(labA * labA + labB * labB);
	let hue = (Math.atan2(labB, labA) * 180) / Math.PI;
	if (hue < 0) hue += 360;
	return { l: labL, c: chroma, h: chroma < 0.0001 ? 0 : hue };
}

export function oklchToHex({ l, c, h }: Oklch): string {
	const hueRad = (h * Math.PI) / 180;
	const labA = c * Math.cos(hueRad);
	const labB = c * Math.sin(hueRad);

	const lCube = (l + 0.3963377774 * labA + 0.2158037573 * labB) ** 3;
	const mCube = (l - 0.1055613458 * labA - 0.0638541728 * labB) ** 3;
	const sCube = (l - 0.0894841775 * labA - 1.291485548 * labB) ** 3;

	const lr = 4.0767416621 * lCube - 3.3077115913 * mCube + 0.2309699292 * sCube;
	const lg = -1.2684380046 * lCube + 2.6097574011 * mCube - 0.3413193965 * sCube;
	const lb = -0.0041960863 * lCube - 0.7034186147 * mCube + 1.707614701 * sCube;

	return rgbToHex({ r: linearToSrgb(lr), g: linearToSrgb(lg), b: linearToSrgb(lb) });
}

// Perceptual distance in OKLab; ~0.02 is roughly a just-noticeable difference.
export function deltaOk(a: Oklch, b: Oklch): number {
	const ax = a.c * Math.cos((a.h * Math.PI) / 180);
	const ay = a.c * Math.sin((a.h * Math.PI) / 180);
	const bx = b.c * Math.cos((b.h * Math.PI) / 180);
	const by = b.c * Math.sin((b.h * Math.PI) / 180);
	return Math.sqrt((a.l - b.l) ** 2 + (ax - bx) ** 2 + (ay - by) ** 2);
}

export function hueDelta(a: number, b: number): number {
	const raw = Math.abs(a - b) % 360;
	return raw > 180 ? 360 - raw : raw;
}

// Rotate hue in OKLCH, keeping lightness and chroma; clamps to gamut by
// reducing chroma until the round-trip stays inside sRGB.
export function rotateHue(hex: string, degrees: number): string {
	const source = hexToOklch(hex);
	let candidate: Oklch = { ...source, h: (source.h + degrees + 360) % 360 };
	for (let attempt = 0; attempt < 20; attempt += 1) {
		const out = oklchToHex(candidate);
		const back = hexToOklch(out);
		if (deltaOk(candidate, back) < 0.02) return out;
		candidate = { ...candidate, c: candidate.c * 0.9 };
	}
	return oklchToHex(candidate);
}
