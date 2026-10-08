import { describe, expect, test } from 'claude-code/testing'

import { mirrorProp, spriteFor } from './idle'

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
		expect(spriteFor('watch', { pace: 'normal', prop: '─O' }, 1, 0)).toBe('(ಠ_ಠ)─O')
		expect(spriteFor('watch', { pace: 'normal', prop: '─O' }, 1, 2)).toBe('(-_-)─O')
		expect(spriteFor('sit', { pace: 'normal', prop: '[~]' }, 1, 0)).toBe('(ಠ‿ಠ)[~]')
		expect(spriteFor('sleep', { pace: 'normal', prop: '[~]' }, 1, 0)).toBe('(-_-) z ')
		expect(spriteFor('startle', { pace: 'normal', prop: '[~]' }, 1, 0)).toBe('(ಠoಠ)! ')
	})

	test('swaying ignores the prop, since both hands are busy', async () => {
		expect(spriteFor('pace', { pace: 'sway', prop: '[#]' }, 1, 1)).toBe('~(ಠ_ಠ)')
	})
})
