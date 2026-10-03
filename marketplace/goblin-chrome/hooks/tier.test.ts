import { describe, expect, test } from 'claude-code/testing'

import { CLOD } from './theme'
import { frameFor, pinnedModel, RUNE, tierOf } from './tier'

describe('tiers', () => {
	test('model ids and aliases map to three tiers', async () => {
		expect(tierOf('claude-haiku-4-5-20251001')).toBe('small')
		expect(tierOf('sonnet')).toBe('mid')
		expect(tierOf('claude-opus-5-5')).toBe('top')
		expect(tierOf('claude-fable-5-1')).toBe('top')
		expect(tierOf('something-new')).toBe('mid')
	})

	test('a skill frontmatter model line is read, comments and all', async () => {
		expect(pinnedModel('---\nname: x\nmodel: sonnet # was haiku\neffort: low\n---\nbody')).toBe('sonnet')
		expect(pinnedModel('---\nname: x\n---\nmodel: opus')).toBeNull()
		expect(pinnedModel('no frontmatter')).toBeNull()
	})

	test('each tier has its own frame and the runes follow the convention', async () => {
		expect(frameFor('top', null, CLOD)).toMatchObject({ borderStyle: 'double', borderDimColor: false, rune: RUNE.top })
		expect(frameFor('mid', null, CLOD)).toMatchObject({ borderStyle: 'round', rune: 'ᛊ' })
		expect(frameFor('small', null, CLOD)).toMatchObject({ borderStyle: 'classic', borderDimColor: true, rune: 'ᚺ' })
	})

	test('a served model that differs from the pin draws the mismatch', async () => {
		const f = frameFor('top', 'mid', CLOD)
		expect(f.borderStyle).toBe('singleDouble')
		expect(f.borderColor).toBe(CLOD.warn)
		expect(f.rune).toBe('ᛊ→ᛟ')
		expect(frameFor('mid', 'mid', CLOD).borderStyle).toBe('round')
	})
})
