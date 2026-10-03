// Hex colour arithmetic for the chrome: blend two colours, shade one.
// RGB space is enough for a terminal; nothing here is measured for contrast.

const clamp = (n: number): number => Math.max(0, Math.min(255, Math.round(n)))

export const parseHex = (hex: string): [number, number, number] | null => {
	const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim())
	if (!m || m[1] === undefined) return null
	const n = parseInt(m[1], 16)
	return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

export const toHex = (rgb: readonly [number, number, number]): string =>
	'#' + rgb.map(c => clamp(c).toString(16).padStart(2, '0')).join('')

/** `t` of the way from `a` to `b`; a bad hex on either side returns the other. */
export const mix = (a: string, b: string, t: number): string => {
	const pa = parseHex(a)
	const pb = parseHex(b)
	if (!pa) return b
	if (!pb) return a
	const k = Math.max(0, Math.min(1, t))
	return toHex([
		pa[0] + (pb[0] - pa[0]) * k,
		pa[1] + (pb[1] - pa[1]) * k,
		pa[2] + (pb[2] - pa[2]) * k,
	])
}

/** Lighten (`delta` > 0) or darken (`delta` < 0) by a fraction of the way to white or black. */
export const shade = (hex: string, delta: number): string =>
	delta >= 0 ? mix(hex, '#ffffff', delta) : mix(hex, '#000000', -delta)

/** The 24-bit integer a Raster cell takes, or the terminal's default for a bad hex. */
export const RASTER_DEFAULT = 0x01000000

export const rasterColour = (hex: string): number => {
	const p = parseHex(hex)
	return p ? (p[0] << 16) | (p[1] << 8) | p[2] : RASTER_DEFAULT
}
