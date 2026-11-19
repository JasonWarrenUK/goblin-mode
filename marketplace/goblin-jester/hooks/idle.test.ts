import { describe, expect, test } from 'claude-code/testing'

import { footprint, MINIONS_SHOWN, mirrorProp, paradeText, spriteFor, step, TICK_MS, viewOf } from './idle'
import type { IdleProps } from './idle'

const IDLE: IdleProps = { mode: 'idle', idleMs: 0, pace: 'normal', startleAt: 0, colour: 'claude', dim: 'subtle', prop: '', minions: [], minionColour: 'suggestion' }

/** Ten minutes of ticks through `step`: how often the picture changed between ticks, and how often it was drawn. */
const tenMinutes = (props: IdleProps, columns = 60) => {
	let live = { tick: 0, x: 0, dir: 1 as const, seenStartle: 0, pokedUntil: 0, startledUntil: 0 } as Parameters<typeof step>[0]
	let drawn = viewOf(live, props, columns)
	let previous = drawn
	let changes = 0
	let draws = 0
	const ticks = (10 * 60_000) / TICK_MS
	for (let i = 0; i < ticks; i++) {
		const { next, draw } = step(live, drawn, props, columns)
		const view = viewOf(next, props, columns)
		if (view !== previous) changes++
		if (draw) {
			draws++
			drawn = view
		}
		// a frame that changed and was not drawn would leave the band stale
		expect(drawn).toBe(view)
		previous = view
		live = next
	}
	return { ticks, changes, draws }
}

describe('redraws', () => {
	test('asleep for ten minutes, the goblin is drawn only when the picture changes: about once a beat, not every tick', async () => {
		const { ticks, changes, draws } = tenMinutes({ ...IDLE, idleMs: 11 * 60_000 })
		expect(draws).toBe(changes)
		// the zZ beat is 600 ms, five ticks
		expect(draws).toBeLessThanOrEqual(ticks / 5)
		expect(draws).toBeGreaterThan(0)
	})

	test('pacing for ten minutes at the normal pace, it is drawn once a step, not every tick', async () => {
		const { ticks, changes, draws } = tenMinutes(IDLE)
		expect(draws).toBe(changes)
		// a step is 420 ms, three and a half ticks
		expect(draws).toBeLessThanOrEqual(ticks / 3)
		expect(draws).toBeGreaterThan(0)
	})
})

describe('props in hand', () => {
	test('the goblin carries its prop in the hand it walks with, and the arrow when it has none', async () => {
		expect(spriteFor('pace', { pace: 'normal', prop: '' }, 1, 0)).toBe('(ಠ_ಠ)>')
		expect(spriteFor('pace', { pace: 'normal', prop: '' }, -1, 0)).toBe('<(ಠ_ಠ)')
		expect(spriteFor('pace', { pace: 'normal', prop: '[#]' }, 1, 0)).toBe('(ಠ_ಠ)[#]')
		expect(spriteFor('pace', { pace: 'normal', prop: '─<' }, -1, 0)).toBe('>─(ಠ_ಠ)')
	})

	test('a prop is mirrored glyph by glyph, with the handed ones swapped', async () => {
		expect(mirrorProp('─O')).toBe('O─')
		expect(mirrorProp('<#]')).toBe('[#>')
		expect(mirrorProp('─/')).toBe('\\─')
		expect(mirrorProp('══#')).toBe('#══')
	})

	test('the watching goblin holds the prop through its blink; the sitting one keeps it; sleep and startle drop it', async () => {
		expect(spriteFor('watch', { pace: 'normal', prop: '─O' }, 1, 0)).toBe('(ಠ_ಠ)─O  ')
		expect(spriteFor('watch', { pace: 'normal', prop: '─O' }, 1, 2)).toBe('(-_-)─O  ')
		expect(spriteFor('sit', { pace: 'normal', prop: '[~]' }, 1, 0)).toBe('(ಠ‿ಠ)[~]')
		expect(spriteFor('sleep', { pace: 'normal', prop: '[~]' }, 1, 0)).toBe('(-_-) z ')
		expect(spriteFor('startle', { pace: 'normal', prop: '[~]' }, 1, 0)).toBe('(ಠoಠ)! ')
	})

	test('swaying ignores the prop, since both hands are busy', async () => {
		expect(spriteFor('pace', { pace: 'sway', prop: '[#]' }, 1, 1)).toBe('~(ಠ_ಠ)')
	})
})

describe('the parade', () => {
	test('shows up to three faces a space apart, then counts the rest', async () => {
		expect(paradeText([])).toBe('')
		expect(paradeText(['o.o'])).toBe('o.o')
		expect(paradeText(['o.o', 'o.O', 'ಠ.ಠ'])).toBe('o.o o.O ಠ.ಠ')
		expect(paradeText(['o.o', 'o.O', 'ಠ.ಠ', '-.-', '^.^'])).toBe('o.o o.O ಠ.ಠ +2')
		expect(MINIONS_SHOWN).toBe(3)
	})

	test('the footprint counts the sprite with its prop and the parade with its gap', async () => {
		expect(footprint({ prop: '', minions: [] })).toEqual({ sprite: 8, parade: 0 })
		expect(footprint({ prop: '[#]', minions: [] })).toEqual({ sprite: 11, parade: 0 })
		expect(footprint({ prop: '[三]', minions: [] })).toEqual({ sprite: 12, parade: 0 })
		expect(footprint({ prop: '', minions: ['o.o', 'o.O'] })).toEqual({ sprite: 8, parade: 8 })
	})
})
