import { describe, expect, test } from 'claude-code/testing'

import { rasterColour, shade } from './colour'
import { FACE_COLUMNS, faceCells } from './goblin'
import { CLOD } from './theme'

const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'

// The environment has no atob, as it has no Buffer (see `base64` in text.ts).
const unpack = (cells: string): Uint32Array => {
	const bytes: number[] = []
	let bits = 0
	let held = 0
	for (const ch of cells) {
		const value = B64.indexOf(ch)
		if (value < 0) break
		held = (held << 6) | value
		bits += 6
		if (bits >= 8) {
			bits -= 8
			bytes.push((held >> bits) & 255)
		}
	}
	return new Uint32Array(Uint8Array.from(bytes).buffer)
}

/** The foreground word of the first cell showing `glyph`. */
const foregroundOf = (cells: string, glyph: string): number | undefined => {
	const words = unpack(cells)
	for (let w = 0; w < words.length; w += 3) {
		if (words[w] === glyph.codePointAt(0)) return words[w + 1]
	}
	return undefined
}

describe('faceCells', () => {
	test('the outline takes the full ink so it reads against the surface', async () => {
		const cells = faceCells('expectant', CLOD)
		for (const glyph of ['╭', '│', '─', '╲']) {
			expect(foregroundOf(cells, glyph)).toBe(rasterColour(CLOD.ink))
		}
	})

	test('the features keep the shaded accent', async () => {
		const cells = faceCells('expectant', CLOD, 0.2)
		expect(foregroundOf(cells, 'o')).toBe(rasterColour(shade(CLOD.accent, 0.2)))
		expect(foregroundOf(cells, 'v')).toBe(rasterColour(shade(CLOD.accent, 0.2)))
	})

	test('the grid is as wide as the face', async () => {
		expect(unpack(faceCells('grin', CLOD)).length).toBe(FACE_COLUMNS * 3 * 3)
	})
})
