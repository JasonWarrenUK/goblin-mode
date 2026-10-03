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
