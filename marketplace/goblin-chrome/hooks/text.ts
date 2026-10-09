// Small text and byte helpers shared by the drawings.

/** aLtErNaTiNg CaPs, the house spinner style: each word starts lower, letters alternate, everything else stays. */
export const goblinCase = (text: string): string => {
	let upper = false
	let out = ''
	for (const ch of text) {
		if (/[a-z]/i.test(ch)) {
			out += upper ? ch.toUpperCase() : ch.toLowerCase()
			upper = !upper
		} else {
			out += ch
			if (/\s/.test(ch)) upper = false
		}
	}
	return out
}

const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'

/** Standard padded base64 of bytes; the environment has no Buffer. */
export const base64 = (bytes: Uint8Array): string => {
	let out = ''
	for (let i = 0; i < bytes.length; i += 3) {
		const a = bytes[i] ?? 0
		const b = bytes[i + 1]
		const c = bytes[i + 2]
		const n = (a << 16) | ((b ?? 0) << 8) | (c ?? 0)
		out += B64[(n >> 18) & 63]
		out += B64[(n >> 12) & 63]
		out += b === undefined ? '=' : B64[(n >> 6) & 63]
		out += c === undefined ? '=' : B64[n & 63]
	}
	return out
}

export type Cell = readonly [char: string, fg: number, bg?: number]

/**
 * Pack rows of cells into a Raster's `cells`: little-endian u32 triplets of
 * code point, foreground and background, row-major. Every row is padded or
 * cut to `columns` so the grid is always `columns * rows`.
 */
export const packCells = (rows: readonly (readonly Cell[])[], columns: number, blank: number): string => {
	const words = new Uint32Array(columns * rows.length * 3)
	let w = 0
	for (const row of rows) {
		for (let x = 0; x < columns; x++) {
			const cell = row[x]
			words[w++] = cell ? cell[0].codePointAt(0) ?? 32 : 32
			words[w++] = cell ? cell[1] : blank
			words[w++] = cell?.[2] ?? blank
		}
	}
	return base64(new Uint8Array(words.buffer))
}

/**
 * Whether a code point is East Asian Wide or Fullwidth, which a terminal
 * draws two cells wide: CJK ideographs, Hangul, kana and the fullwidth
 * forms. Ambiguous-width glyphs (box drawing, shades, arrows, geometric
 * shapes) count one, as the band's own frame already relies on.
 */
const isWide = (cp: number): boolean =>
	(cp >= 0x1100 && cp <= 0x115f) ||
	(cp >= 0x2e80 && cp <= 0x303e) ||
	(cp >= 0x3041 && cp <= 0x33ff) ||
	(cp >= 0x3400 && cp <= 0x4dbf) ||
	(cp >= 0x4e00 && cp <= 0x9fff) ||
	(cp >= 0xa000 && cp <= 0xa4cf) ||
	(cp >= 0xac00 && cp <= 0xd7a3) ||
	(cp >= 0xf900 && cp <= 0xfaff) ||
	(cp >= 0xfe30 && cp <= 0xfe4f) ||
	(cp >= 0xff00 && cp <= 0xff60) ||
	(cp >= 0xffe0 && cp <= 0xffe6) ||
	cp >= 0x1f300

/** The terminal cells a string takes: two for each wide glyph, one for the rest. */
export const cells = (text: string): number => {
	let n = 0
	for (const ch of text) n += isWide(ch.codePointAt(0) ?? 0) ? 2 : 1
	return n
}

/** Pick one line from a list by a counter, so the same minute shows the same line. */
export const pick = <T,>(items: readonly T[], n: number): T => {
	const item = items[Math.abs(Math.floor(n)) % items.length]
	if (item === undefined) throw new Error('pick: empty list')
	return item
}

export const seconds = (ms: number): string => {
	const s = Math.round(ms / 1000)
	if (s < 60) return `${s}s`
	const m = Math.floor(s / 60)
	return `${m}m ${s - m * 60}s`
}
