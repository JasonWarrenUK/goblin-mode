import { describe, expect, test } from 'claude-code/testing'

import { metadataKey, pluginSkill, pluginSkillPaths, readMinionFace, readSkill, splitBar, topLevel } from './frontmatter'

/** installed_plugins.json as Claude Code writes it: version 2, each key `name@marketplace` mapped to its installs. */
const INSTALLED = JSON.stringify({
	version: 2,
	plugins: {
		'hookify@claude-plugins-official': [{ scope: 'user', installPath: '/c/hookify/0.1.1', version: '0.1.1' }],
		'goblin-scout@goblin-mode': [
			{ scope: 'project', projectPath: '/code/other', installPath: '/c/goblin-scout/2.4.0', version: '2.4.0' },
			{ scope: 'user', installPath: '/c/goblin-scout/2.9.0', version: '2.9.0' },
			{ scope: 'project', projectPath: '/code/app', installPath: '/c/goblin-scout/3.0.0', version: '3.0.0' },
			{ scope: 'project', projectPath: '/code/app/.claude/worktrees/x', installPath: '/c/goblin-scout/3.1.0', version: '3.1.0' },
			{ scope: 'local', projectPath: '/code/app', installPath: '/c/goblin-scout/3.2.0', version: '3.2.0' },
			{ scope: 'project', installPath: '/c/goblin-scout/0.1.0', version: '0.1.0' },
		],
		'goblin-scout@elsewhere': [{ scope: 'user', installPath: '/x/goblin-scout/1.0.0', version: '1.0.0' }],
		'goblin-scouting@goblin-mode': [{ scope: 'user', installPath: '/c/goblin-scouting/1.0.0', version: '1.0.0' }],
	},
})

const SCOUT = { plugin: 'goblin-scout', dir: 'start-trail' }
const at = (version: string, root = '/c'): string => `${root}/goblin-scout/${version}/skills/start-trail/SKILL.md`

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
	test("outside any project's installs, only user installs count, in the order the file lists them", async () => {
		expect(pluginSkillPaths(INSTALLED, SCOUT, '/home/j/.claude')).toEqual([at('2.9.0'), at('1.0.0', '/x')])
	})

	test("in a project, its local install comes first, then its project install, then the user's, as Claude Code ranks the scopes", async () => {
		expect(pluginSkillPaths(INSTALLED, SCOUT, '/code/app')).toEqual([at('3.2.0'), at('3.0.0'), at('2.9.0'), at('1.0.0', '/x')])
	})

	test("from a subdirectory or a worktree inside the project, the most specific project's install wins", async () => {
		expect(pluginSkillPaths(INSTALLED, SCOUT, '/code/app/src')).toEqual([at('3.2.0'), at('3.0.0'), at('2.9.0'), at('1.0.0', '/x')])
		expect(pluginSkillPaths(INSTALLED, SCOUT, '/code/app/.claude/worktrees/x')).toEqual([at('3.2.0'), at('3.1.0'), at('3.0.0'), at('2.9.0'), at('1.0.0', '/x')])
	})

	test("another project's install, a path that only shares a prefix, or a project install without its path is never read", async () => {
		expect(pluginSkillPaths(INSTALLED, SCOUT, '/code/application')).toEqual([at('2.9.0'), at('1.0.0', '/x')])
		expect(pluginSkillPaths(INSTALLED, SCOUT, '/code/other')).toEqual([at('2.4.0'), at('2.9.0'), at('1.0.0', '/x')])
	})

	test('uses the directory name the engine reports, never the frontmatter name', async () => {
		expect(pluginSkillPaths(INSTALLED, { plugin: 'hookify', dir: 'writing-rules' }, '/code/app')).toEqual(['/c/hookify/0.1.1/skills/writing-rules/SKILL.md'])
	})

	test('a plugin that is not installed, or a file that will not parse or has another shape, names nowhere', async () => {
		expect(pluginSkillPaths(INSTALLED, { plugin: 'goblin', dir: 'x' }, '/code/app')).toEqual([])
		expect(pluginSkillPaths('{not json', { plugin: 'hookify', dir: 'x' }, '/code/app')).toEqual([])
		expect(pluginSkillPaths('{"plugins": []}', { plugin: 'hookify', dir: 'x' }, '/code/app')).toEqual([])
		expect(pluginSkillPaths('{"plugins": {"hookify@m": [{"installPath": 3}, null]}}', { plugin: 'hookify', dir: 'x' }, '/code/app')).toEqual([])
	})

	test('a skill directory that would climb out of the install is refused', async () => {
		expect(pluginSkillPaths(INSTALLED, { plugin: 'hookify', dir: '../../etc' }, '/code/app')).toEqual([])
	})

	test('a project path recorded with a trailing slash still matches its own root, and only paths beneath it', async () => {
		const slashed = JSON.stringify({ plugins: { 'goblin-scout@m': [{ scope: 'project', projectPath: '/a/proj/', installPath: '/c/s' }] } })
		const here = '/c/s/skills/start-trail/SKILL.md'
		expect(pluginSkillPaths(slashed, SCOUT, '/a/proj')).toEqual([here])
		expect(pluginSkillPaths(slashed, SCOUT, '/a/proj/x')).toEqual([here])
		expect(pluginSkillPaths(slashed, SCOUT, '/a/proj-two')).toEqual([])
	})

	test('a user install recorded with a null project path is read; a project install with one is not', async () => {
		const user = JSON.stringify({ plugins: { 'goblin-scout@m': [{ scope: 'user', projectPath: null, installPath: '/c/s' }] } })
		const project = JSON.stringify({ plugins: { 'goblin-scout@m': [{ scope: 'project', projectPath: null, installPath: '/c/s' }] } })
		expect(pluginSkillPaths(user, SCOUT, '/a/proj')).toEqual(['/c/s/skills/start-trail/SKILL.md'])
		expect(pluginSkillPaths(project, SCOUT, '/a/proj')).toEqual([])
	})

	test("an install of an unrecognised scope bound to another project's path is never read", async () => {
		for (const scope of ['workspace', 'constructor', 'toString']) {
			const bound = JSON.stringify({ plugins: { 'goblin-scout@m': [{ scope, projectPath: '/other', installPath: '/c/s' }] } })
			expect(pluginSkillPaths(bound, SCOUT, '/a/proj')).toEqual([])
		}
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

	test('a spinner word from a stranger is capped in length and loses its control characters', async () => {
		const [long] = splitBar('x'.repeat(300))
		expect(Array.from(long ?? '').length).toBe(40)
		expect(splitBar('\u001b[31mred\u001b[0m|tab\there|bell\u0007')).toEqual(['[31mred[0m', 'tabhere', 'bell'])
		// a word that was nothing but control characters is dropped, never drawn blank
		expect(splitBar('\u001b\u0007|ok')).toEqual(['ok'])
	})

	test('a spinner word loses bidi overrides, isolates, zero-width characters and line separators too', async () => {
		expect(splitBar('\u202eevil\u202c|\u2066iso\u2069|zero\u200bwidth|line\u2028para\u2029end')).toEqual(['evil', 'iso', 'zerowidth', 'lineparaend'])
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
