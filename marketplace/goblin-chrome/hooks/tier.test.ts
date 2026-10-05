import { describe, expect, test } from 'claude-code/testing'

import { CLOD } from './theme'
import { bandRule, frameFor, GLYPHS, glyphsFor, pinnedModel, RUNE, tierOf } from './tier'

describe('band rules', () => {
	test('each border style joins the dividers to the rules with its own tees', async () => {
		expect(bandRule('double', 'top', [3, 2])).toBe('╔═══╦══╗')
		expect(bandRule('double', 'bottom', [3, 2, 1])).toBe('╚═══╩══╩═╝')
		expect(bandRule('round', 'top', [2, 2])).toBe('╭──┬──╮')
		expect(bandRule('singleDouble', 'top', [2, 2])).toBe('╓──╥──╖')
		expect(bandRule('singleDouble', 'bottom', [2, 2])).toBe('╙──╨──╜')
	})

	test('each model draws its own frame: Fable double, Opus heavy, Sonnet round, Haiku dotted', async () => {
		const frameOf = (tier: Parameters<typeof frameFor>[0]) => glyphsFor(frameFor(tier, null, CLOD).borderStyle)
		const sketch = (tier: Parameters<typeof frameFor>[0]) => {
			const g = frameOf(tier)
			return [bandRule(frameFor(tier, null, CLOD).borderStyle, 'top', [3, 1]), `${g.vertical} X ${g.vertical}`, bandRule(frameFor(tier, null, CLOD).borderStyle, 'bottom', [3, 1])]
		}
		expect(sketch('fable')).toEqual(['╔═══╦═╗', '║ X ║', '╚═══╩═╝'])
		expect(sketch('top')).toEqual(['┏━━━┳━┓', '┃ X ┃', '┗━━━┻━┛'])
		expect(sketch('mid')).toEqual(['╭───┬─╮', '│ X │', '╰───┴─╯'])
		expect(sketch('small')).toEqual(['+┈┈┈+┈+', '┊ X ┊', '+┈┈┈+┈+'])
	})

	test('every frame the tiers draw has a glyph set, and an unknown style falls to the Haiku frame', async () => {
		for (const tier of ['top', 'mid', 'small', 'fable'] as const) {
			for (const pinned of [null, tier === 'top' ? 'mid' : 'top'] as const) {
				expect(GLYPHS[frameFor(tier, pinned, CLOD).borderStyle]).toBeDefined()
			}
		}
		expect(glyphsFor('nonsense')).toBe(GLYPHS.classic!)
	})
})

describe('tiers', () => {
	test('model ids and aliases map to four tiers', async () => {
		expect(tierOf('claude-haiku-4-5-20251001')).toBe('small')
		expect(tierOf('sonnet')).toBe('mid')
		expect(tierOf('claude-opus-5-5')).toBe('top')
		expect(tierOf('claude-fable-5-1')).toBe('fable')
		expect(tierOf('something-new')).toBe('mid')
	})

	test('a skill frontmatter model line is read, comments and all', async () => {
		expect(pinnedModel('---\nname: x\nmodel: sonnet # was haiku\neffort: low\n---\nbody')).toBe('sonnet')
		expect(pinnedModel('---\nname: x\n---\nmodel: opus')).toBeNull()
		expect(pinnedModel('no frontmatter')).toBeNull()
		expect(pinnedModel('---\nmodel: inherit\n---')).toBeNull()
		expect(pinnedModel('---\nmodel: "opus"\n---')).toBe('opus')
	})

	test('each tier has its own frame and the runes follow the convention', async () => {
		expect(frameFor('top', null, CLOD)).toMatchObject({ borderStyle: 'bold', borderDimColor: false, rune: RUNE.top })
		expect(frameFor('mid', null, CLOD)).toMatchObject({ borderStyle: 'round', rune: 'ᛊ' })
		expect(frameFor('small', null, CLOD)).toMatchObject({ borderStyle: 'classic', borderDimColor: true, rune: 'ᚺ' })
		expect(frameFor('fable', null, CLOD)).toMatchObject({ borderStyle: 'double', borderDimColor: false, rune: 'ᚠ' })
	})

	test('each tier takes its own theme colour, none shared and none the mismatch warn', async () => {
		const colours = {
			fable: frameFor('fable', null, CLOD).borderColor,
			top: frameFor('top', null, CLOD).borderColor,
			mid: frameFor('mid', null, CLOD).borderColor,
			small: frameFor('small', null, CLOD).borderColor,
		}
		expect(colours).toEqual({ fable: CLOD.accent, top: CLOD.accent2, mid: CLOD.info, small: CLOD.ok })
		expect(new Set(Object.values(colours)).size).toBe(4)
		expect(frameFor('top', 'mid', CLOD).borderColor).toBe(CLOD.warn)
	})

	test('a served model that differs from the pin draws the mismatch', async () => {
		const f = frameFor('top', 'mid', CLOD)
		expect(f.borderStyle).toBe('singleDouble')
		expect(f.borderColor).toBe(CLOD.warn)
		expect(f.rune).toBe('ᛊ→ᛟ')
		expect(frameFor('mid', 'mid', CLOD).borderStyle).toBe('round')
	})

	test('a fable pin answered by opus, and the reverse, draw the mismatch', async () => {
		expect(frameFor('top', 'fable', CLOD)).toMatchObject({ borderStyle: 'singleDouble', borderColor: CLOD.warn, rune: 'ᚠ→ᛟ' })
		expect(frameFor('fable', 'top', CLOD)).toMatchObject({ borderStyle: 'singleDouble', rune: 'ᛟ→ᚠ' })
	})
})
