import { describe, expect, test } from 'claude-code/testing'

import { footprint, MINIONS_SHOWN, mirrorProp, paradeText, spriteFor } from './idle'

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
