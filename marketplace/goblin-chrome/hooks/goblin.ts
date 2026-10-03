// The goblin's face and metre as Raster cells: the mask over a question (29)
// and the vitals bar in the band (18). Every glyph is one cell wide and in
// the BMP, as RasterProps demands.

import { rasterColour, RASTER_DEFAULT, shade } from './colour'
import { packCells, type Cell } from './text'
import type { Palette, Vitals } from '../types'

export type Expression = 'expectant' | 'nervous' | 'folded' | 'grin'

export type Mood = 'calm' | 'twitchy' | 'agitated' | 'frantic'

/** How bothered the goblin is by the session's load. */
export const moodOf = (vitals: Pick<Vitals, 'context' | 'limit'>): Mood => {
	const worst = Math.max(vitals.context, vitals.limit)
	if (worst >= 90) return 'frantic'
	if (worst >= 75) return 'agitated'
	if (worst >= 50) return 'twitchy'
	return 'calm'
}

const FACES: Record<Expression, readonly [string, string, string]> = {
	expectant: [' ╭───╮ ', ' │o o│ ', ' ╰─▽─╯ '],
	nervous: [' ╭───╮ ', ' │ò ó│ ', ' ╰─~─╯ '],
	folded: [' ╭───╮ ', ' │– –│ ', ' ╰─_─╯ '],
	grin: [' ╭───╮ ', ' │^ ^│ ', ' ╰─◡─╯ '],
}

export const FACE_COLUMNS = 7
export const FACE_ROWS = 3

/** The face's cells: the frame in the palette's line, the features in its accent. */
export const faceCells = (expression: Expression, palette: Palette, tint: number = 0): string => {
	const line = rasterColour(palette.line)
	const feature = rasterColour(shade(palette.accent, tint))
	const rows = FACES[expression].map(row =>
		Array.from(row).map((ch): Cell => [ch, /[│╭╮╰╯─]/.test(ch) ? line : feature]),
	)
	return packCells(rows, FACE_COLUMNS, RASTER_DEFAULT)
}

export const METER_COLUMNS = 12

/** A one-row bar: filled cells coloured by how full the window is, empty cells dim. */
export const meterCells = (percent: number, palette: Palette): string => {
	const filled = Math.round((Math.max(0, Math.min(100, percent)) / 100) * METER_COLUMNS)
	const colour = rasterColour(percent >= 90 ? palette.danger : percent >= 75 ? palette.warn : palette.accent)
	const empty = rasterColour(palette.line)
	const row: Cell[] = []
	for (let i = 0; i < METER_COLUMNS; i++) row.push(i < filled ? ['█', colour] : ['░', empty])
	return packCells([row], METER_COLUMNS, RASTER_DEFAULT)
}

/** What the band says beside the metre, in the goblin's register. */
export const voiceLine = (vitals: Vitals, mood: Mood): string => {
	const limit = vitals.limitKind ? ` · ${vitals.limitKind === 'five_hour' ? '5h' : vitals.limitKind === 'seven_day' ? '7d' : vitals.limitKind} ${Math.round(vitals.limit)}%` : ''
	const hoard = vitals.tools > 0 ? ` · hoard ${vitals.tools}` : ''
	const bitten = vitals.errors > 0 ? ` · bit ${vitals.errors}` : ''
	const temper: Record<Mood, string> = {
		calm: '',
		twitchy: ' · twitchy',
		agitated: ' · bag is filling',
		frantic: ' · BAG IS FULL',
	}
	return `context ${Math.round(vitals.context)}%${limit}${hoard}${bitten}${temper[mood]}`
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
	bounceAgain: (n: number) => `bounced again. that is ${n} today.`,
} as const
