import { describe, expect, test } from 'claude-code/testing'

import { rasterColour, shade } from './colour'
import { FACE_COLUMNS, FACE_ROWS, faceCells } from './goblin'
import { CLOD } from './theme'

const unpack = (cells: string): Uint32Array =>
	new Uint32Array(Uint8Array.from(atob(cells), c => c.charCodeAt(0)).buffer)

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

	test("the grid is the face's columns by rows", async () => {
		expect(unpack(faceCells('grin', CLOD)).length).toBe(FACE_COLUMNS * FACE_ROWS * 3)
	})
})
