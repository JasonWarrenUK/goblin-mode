// The goblin's face as Raster cells: the mask over a question (29). Every
// glyph is one cell wide and in the BMP, as RasterProps demands.

import { rasterColour, RASTER_DEFAULT, shade } from './colour'
import { packCells, type Cell } from './text'
import type { Palette } from '../types'

export type Expression = 'expectant' | 'nervous' | 'folded' | 'grin'

// A goblin head: ears out to the sides, up when it is alert and drooping when
// it is not, a fang in the mouth when it is pleased.
const FACES: Record<Expression, readonly [string, string, string]> = {
	expectant: ['╲╭───╮╱', ' │o o│ ', ' ╰─v─╯ '],
	nervous: [" ╭───╮'", '╱│o O│╲', ' ╰─~─╯ '],
	folded: [' ╭───╮ ', '╱│- -│╲', ' ╰─_─╯ '],
	grin: ['╲╭───╮╱', ' │^ ^│ ', ' ╰vVv╯ '],
}

export const FACE_COLUMNS = 7
export const FACE_ROWS = 3

/** The face's cells: the frame in the palette's line, the features in its accent. */
export const faceCells = (expression: Expression, palette: Palette, tint: number = 0): string => {
	const line = rasterColour(palette.line)
	const feature = rasterColour(shade(palette.accent, tint))
	const rows = FACES[expression].map(row =>
		Array.from(row).map((ch): Cell => [ch, /[│╭╮╰╯─╱╲]/.test(ch) ? line : feature]),
	)
	return packCells(rows, FACE_COLUMNS, RASTER_DEFAULT)
}

export const POKE_LINES = [
	'ow.',
	'what.',
	'do that again and see.',
	'I was resting.',
	'type something instead.',
	'this is not a petting zoo.',
] as const

export const HECKLES = {
	minionBack: (ms: number) => `minion back. took ${Math.round(ms / 1000)}s. unimpressed.`,
	compaction: 'memory wiped. going again.',
	clear: 'fine.',
	bounce: 'the hook bounced that message. told you.',
	bounceAgain: (n: number) => `bounced again. that is ${n} so far.`,
} as const
