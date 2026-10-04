import { describe, expect, test } from 'claude-code/testing'

import { mix, parseHex, rasterColour, RASTER_DEFAULT, shade } from './colour'
import { base64, goblinCase, packCells, pick, seconds } from './text'

describe('text', () => {
	test('goblin case alternates letters only', async () => {
		expect(goblinCase('done. 42s. took 7 things.')).toBe('dOnE. 42s. tOoK 7 tHiNgS.')
		expect(goblinCase('')).toBe('')
	})

	test('base64 matches the standard vectors', async () => {
		const enc = (s: string) => base64(new TextEncoder().encode(s))
		expect(enc('')).toBe('')
		expect(enc('f')).toBe('Zg==')
		expect(enc('fo')).toBe('Zm8=')
		expect(enc('foobar')).toBe('Zm9vYmFy')
	})

	test('cells pack to columns times rows triplets', async () => {
		const packed = packCells([[['█', 0xff8800]], []], 3, RASTER_DEFAULT)
		const bytes = Uint8Array.from(atob(packed), c => c.charCodeAt(0))
		const words = new Uint32Array(bytes.buffer)
		expect(words).toHaveLength(3 * 2 * 3)
		expect(words[0]).toBe(0x2588)
		expect(words[1]).toBe(0xff8800)
		expect(words[2]).toBe(RASTER_DEFAULT)
		expect(words[3]).toBe(32)
	})

	test('pick is stable per counter and seconds format as the engine does', async () => {
		expect(pick(['a', 'b', 'c'], 4)).toBe('b')
		expect(seconds(3_000)).toBe('3s')
		expect(seconds(64_000)).toBe('1m 4s')
	})
})

describe('colour', () => {
	test('hex parses, mixes and shades', async () => {
		expect(parseHex('#ff8800')).toEqual([255, 136, 0])
		expect(parseHex('nope')).toBeNull()
		expect(mix('#000000', '#ffffff', 0.5)).toBe('#808080')
		expect(shade('#808080', 1)).toBe('#ffffff')
		expect(shade('#808080', -1)).toBe('#000000')
		expect(mix('bad', '#123456', 0.3)).toBe('#123456')
	})

	test('raster colours are 24-bit ints with the default for bad input', async () => {
		expect(rasterColour('#ff8800')).toBe(0xff8800)
		expect(rasterColour('x')).toBe(RASTER_DEFAULT)
	})
})
