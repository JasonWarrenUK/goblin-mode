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

/** The face's cells: the outline in the palette's ink, the features in its accent. */
export const faceCells = (expression: Expression, palette: Palette, tint: number = 0): string => {
	const outline = rasterColour(palette.ink)
	const feature = rasterColour(shade(palette.accent, tint))
	const rows = FACES[expression].map(row =>
		Array.from(row).map((ch): Cell => [ch, /[│╭╮╰╯─╱╲]/.test(ch) ? outline : feature]),
	)
	return packCells(rows, FACE_COLUMNS, RASTER_DEFAULT)
}

/**
 * What the goblin holds while a skill of each family runs: a text object of
 * one to three cells, every glyph single-width and in the BMP so the band's
 * arithmetic holds. Box-drawing glyphs are already in the shipping band;
 * shade blocks and geometric shapes are not, since some terminals draw them
 * two cells wide.
 */
export const PROPS: Record<string, string> = {
	artefact: '[~]', // a page
	asset: '══#', // a brush
	branch: '─<', // a forked stick
	'clod-approach': '─/', // a pen
	'clod-config': '(*)', // a cog
	'clod-lens': '─O', // a lens
	'clod-role': '[^]', // a hat, in hand
	'clod-stack': '|||', // a stack
	commit: '[=]', // a sealed letter
	do: '─┬', // a hammer
	doc: '─\\', // a quill
	dossier: '[i]', // an index card
	hud: '(o)', // a dial
	import: '[<]', // an in-tray
	'next-task': '[>]', // a ticket
	pr: '[#]', // a parcel
	project: '<#]', // a tag
	red: '[!]', // a red flag
	roadmap: '[+]', // a folded map
	'skill-creator': '─*', // a wand
	theme: '[%]', // a swatch
	track: '[:]', // tally marks
}

/** The prop for a family, or empty when the family has none. */
export const propFor = (family: string | null): string => (family === null ? '' : (PROPS[family] ?? ''))

/** The face a subagent wears in the parade when its agent file sets none. */
export const DEFAULT_MINION = 'o.o'

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
	minionOut: (n: number) => (n === 1 ? 'minion out. watching.' : `${n} minions out. watching.`),
	compaction: 'memory wiped. going again.',
	clear: 'fine.',
	bounce: 'the hook bounced that message. told you.',
	bounceAgain: (n: number) => `bounced again. that is ${n} so far.`,
} as const
