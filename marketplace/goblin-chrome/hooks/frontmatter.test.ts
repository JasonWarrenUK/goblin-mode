import { describe, expect, test } from 'claude-code/testing'

import { metadataKey, readMinionFace, readSkill, splitBar, topLevel } from './frontmatter'

const SKILL = [
	'---',
	'name: "PR: Land"',
	'model: opus # pinned',
	'effort: high',
	'metadata:',
	'  glyph: ᛟ           # mirrors the model',
	'  family: pr         # the family prefix',
	'  goblin-spinner: merging|deleting evidence| tagging ',
	'disable-model-invocation: true',
	'---',
	'',
	'# Land the PR',
	'family: not-this',
].join('\n')

describe('readSkill', () => {
	test('reads the model, the family and the spinner words from one file', async () => {
		expect(readSkill(SKILL)).toEqual({ model: 'opus', family: 'pr', spinner: ['merging', 'deleting evidence', 'tagging'] })
	})

	test('a file without frontmatter, or without the keys, reads as nothing set', async () => {
		expect(readSkill('no frontmatter\nmodel: opus')).toEqual({ model: null, family: null, spinner: [] })
		expect(readSkill('---\nname: x\n---\nbody')).toEqual({ model: null, family: null, spinner: [] })
		expect(readSkill('---\nmodel: inherit\nmetadata:\n  glyph: ᛊ\n---')).toEqual({ model: null, family: null, spinner: [] })
	})

	test('a quoted model and a trailing comment both read as the bare value', async () => {
		expect(readSkill('---\nmodel: "opus"\n---').model).toBe('opus')
		expect(readSkill('---\nmodel: sonnet # was haiku\n---').model).toBe('sonnet')
	})

	test('metadata keys are only read under metadata, and the block ends at the next unindented line', async () => {
		const block = 'metadata:\n  family: pr\nother:\n  family: nope'
		expect(metadataKey(block, 'family')).toBe('pr')
		expect(metadataKey('family: top\nmetadata:\n  glyph: ᛟ', 'family')).toBeNull()
	})

	test('scalars drop comments and quotes', async () => {
		expect(topLevel('model: "sonnet" # was haiku', 'model')).toBe('sonnet')
		expect(topLevel("model: 'opus'", 'model')).toBe('opus')
		expect(topLevel('model:', 'model')).toBeNull()
		expect(topLevel('model: a#b', 'model')).toBe('a#b')
	})

	test('a bar list trims and drops empties', async () => {
		expect(splitBar(' a | b ||c|')).toEqual(['a', 'b', 'c'])
		expect(splitBar(null)).toEqual([])
		expect(splitBar('|')).toEqual([])
	})
})

describe('readMinionFace', () => {
	test('reads a top-level goblin-minion face from an agent file', async () => {
		expect(readMinionFace('---\nname: scope-guard\ngoblin-minion: o.O\ncolor: amber\n---\nbody')).toBe('o.O')
		expect(readMinionFace('---\nname: x\ngoblin-minion: "ಠ.ಠ"\n---')).toBe('ಠ.ಠ')
	})

	test('refuses a face the band cannot measure: too wide, blank, with a space or beyond the BMP', async () => {
		expect(readMinionFace('---\ngoblin-minion: o.o.o.o\n---')).toBeNull()
		expect(readMinionFace('---\ngoblin-minion: 三三三\n---')).toBeNull()
		expect(readMinionFace('---\ngoblin-minion: [三]\n---')).toBe('[三]')
		expect(readMinionFace('---\ngoblin-minion:\n---')).toBeNull()
		expect(readMinionFace('---\ngoblin-minion: o o\n---')).toBeNull()
		expect(readMinionFace('---\ngoblin-minion: 👺\n---')).toBeNull()
		expect(readMinionFace('---\nname: x\n---')).toBeNull()
		expect(readMinionFace('no frontmatter')).toBeNull()
	})
})
