import { describe, expect, test } from 'claude-code/testing'

import { rasterColour, shade } from './colour'
import { DEFAULT_MINION, FACE_COLUMNS, FACE_ROWS, faceCells, PROP_MAX_CELLS, propFor, PROPS } from './goblin'
import { cells } from './text'
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

describe('props', () => {
	test('every family prop fits the cap in terminal cells and is BMP text without spaces, so the band can measure it', async () => {
		for (const [family, prop] of Object.entries(PROPS)) {
			expect(cells(prop), family).toBeGreaterThanOrEqual(1)
			expect(cells(prop), family).toBeLessThanOrEqual(PROP_MAX_CELLS)
			for (const ch of Array.from(prop)) {
				expect((ch.codePointAt(0) ?? 0) <= 0xffff, `${family}: ${ch}`).toBe(true)
				expect(/\s/.test(ch), `${family}: ${ch}`).toBe(false)
			}
		}
		// the one wide glyph in the table is measured as two cells
		expect(cells(PROPS['clod-stack']!)).toBe(4)
	})

	test('every family in the config has a prop, and no two families share one', async () => {
		const families = [
			'artefact', 'asset', 'branch', 'clod-approach', 'clod-config', 'clod-lens', 'clod-role', 'clod-stack', 'commit', 'do', 'doc',
			'dossier', 'hud', 'import', 'next-task', 'pr', 'project', 'red', 'skill-creator', 'theme', 'track',
		]
		for (const family of families) expect(propFor(family), family).not.toBe('')
		expect(new Set(Object.values(PROPS)).size).toBe(Object.keys(PROPS).length)
	})

	test('an unknown or missing family walks empty-handed', async () => {
		expect(propFor('nonsense')).toBe('')
		expect(propFor(null)).toBe('')
	})

	test('the default minion face is band-safe', async () => {
		expect(cells(DEFAULT_MINION)).toBeLessThanOrEqual(5)
	})
})
