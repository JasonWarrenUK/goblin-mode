import { describe, expect, test } from 'claude-code/testing'

import { metadataKey, pluginSkill, pluginSkillPaths, readMinionFace, readSkill, splitBar, topLevel } from './frontmatter'

/** installed_plugins.json as Claude Code writes it: version 2, each key `name@marketplace` mapped to its installs. */
const INSTALLED = JSON.stringify({
	version: 2,
	plugins: {
		'hookify@claude-plugins-official': [{ scope: 'user', installPath: '/c/hookify/0.1.1', version: '0.1.1' }],
		'goblin-scout@goblin-mode': [
			{ scope: 'project', installPath: '/c/goblin-scout/3.0.0', version: '3.0.0' },
			{ scope: 'user', installPath: '/c/goblin-scout/2.9.0', version: '2.9.0' },
		],
		'goblin-scout@elsewhere': [{ scope: 'user', installPath: '/x/goblin-scout/1.0.0', version: '1.0.0' }],
		'goblin-scouting@goblin-mode': [{ scope: 'user', installPath: '/c/goblin-scouting/1.0.0', version: '1.0.0' }],
	},
})

describe('pluginSkill', () => {
	test("splits the engine's plugin:directory name on the first colon", async () => {
		expect(pluginSkill('hookify:writing-rules')).toEqual({ plugin: 'hookify', dir: 'writing-rules' })
	})

	test('a personal or project skill, or a half-empty name, is not a plugin skill', async () => {
		expect(pluginSkill('pr-land')).toBeNull()
		expect(pluginSkill(':x')).toBeNull()
		expect(pluginSkill('x:')).toBeNull()
	})
})

describe('pluginSkillPaths', () => {
	test('names the skill directory under each install of that plugin, in the order the file lists them', async () => {
		expect(pluginSkillPaths(INSTALLED, { plugin: 'goblin-scout', dir: 'start-trail' })).toEqual([
			'/c/goblin-scout/3.0.0/skills/start-trail/SKILL.md',
			'/c/goblin-scout/2.9.0/skills/start-trail/SKILL.md',
			'/x/goblin-scout/1.0.0/skills/start-trail/SKILL.md',
		])
	})

	test('uses the directory name the engine reports, never the frontmatter name', async () => {
		expect(pluginSkillPaths(INSTALLED, { plugin: 'hookify', dir: 'writing-rules' })).toEqual(['/c/hookify/0.1.1/skills/writing-rules/SKILL.md'])
	})

	test('a plugin that is not installed, or a file that will not parse or has another shape, names nowhere', async () => {
		expect(pluginSkillPaths(INSTALLED, { plugin: 'goblin', dir: 'x' })).toEqual([])
		expect(pluginSkillPaths('{not json', { plugin: 'hookify', dir: 'x' })).toEqual([])
		expect(pluginSkillPaths('{"plugins": []}', { plugin: 'hookify', dir: 'x' })).toEqual([])
		expect(pluginSkillPaths('{"plugins": {"hookify@m": [{"installPath": 3}, null]}}', { plugin: 'hookify', dir: 'x' })).toEqual([])
	})

	test('a skill directory that would climb out of the install is refused', async () => {
		expect(pluginSkillPaths(INSTALLED, { plugin: 'hookify', dir: '../../etc' })).toEqual([])
	})
})

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

	test('reads the quoted faces YAML needs for a leading indicator or a number-shaped value', async () => {
		expect(readMinionFace("---\ngoblin-minion: '>.<'\n---")).toBe('>.<')
		expect(readMinionFace("---\ngoblin-minion: '@.@'\n---")).toBe('@.@')
		expect(readMinionFace("---\ngoblin-minion: '0.0'\n---")).toBe('0.0')
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
