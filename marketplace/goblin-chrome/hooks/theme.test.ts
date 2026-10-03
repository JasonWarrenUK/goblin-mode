import { describe, expect, test } from 'claude-code/testing'

import { CLOD, CLOD_LIGHT, coreNames, loadPalette, paletteFrom } from './theme'

const core = (family: string, accent = '#D9A441') => ({
	family,
	palette: {
		ink: { light: '#111111', dark: '#EDE7DA' },
		'ink-muted': { light: '#222222', dark: '#A39C8E' },
		surface: { light: '#333333', dark: '#14181F' },
		'surface-raised': { light: '#444444', dark: '#1D232C' },
		line: { light: '#555555', dark: '#2E3640' },
		accent: { light: '#666666', dark: accent },
		'accent-ink': { light: '#777777', dark: '#1A1408' },
		'accent-2': { light: '#888888', dark: '#4FB3A8' },
		ok: { light: '#999999', dark: '#6FBF73' },
		warn: { light: '#aaaaaa', dark: '#E0A83A' },
		danger: { light: '#bbbbbb', dark: '#E06C5B' },
		info: { light: '#cccccc', dark: '#6FA8DC' },
	},
})

describe('palette parsing', () => {
	test('a core file yields the dark variant by semantic name', async () => {
		expect(paletteFrom(core('ember', '#ff6600'))).toMatchObject({ family: 'ember', accent: '#ff6600', inkMuted: '#A39C8E' })
	})

	test('a target file or a short core is refused', async () => {
		expect(paletteFrom({ family: 'ember', target: 'html', html: {} })).toBeNull()
		const short = core('ember') as { palette: Record<string, unknown> }
		delete short.palette.info
		expect(paletteFrom(short)).toBeNull()
		expect(paletteFrom(null)).toBeNull()
		expect(paletteFrom([])).toBeNull()
		expect(paletteFrom(core('ember'), 'light')).toMatchObject({ accent: '#666666', ink: '#111111' })
	})

	test('core names are the unhyphenated json files only', async () => {
		expect(
			coreNames([
				{ name: 'ember.json', kind: 'file' },
				{ name: 'ember-html.json', kind: 'file' },
				{ name: 'seen.json', kind: 'file' },
				{ name: 'tidewater.json', kind: 'file' },
				{ name: 'notes', kind: 'dir' },
				{ name: 'linked.json', kind: 'other', isLink: true },
			]),
		).toEqual(['ember', 'linked', 'seen', 'tidewater'])
	})
})

describe('resolution', () => {
	const files: Record<string, unknown> = {
		'.claude/themes/ember.json': core('ember', '#ff6600'),
		'/home/j/.claude/library/themes/clod.json': core('clod', '#D9A441'),
	}
	const reader = (dir: readonly string[]) => ({
		list: async (path: string) => {
			if (path !== '.claude/themes') throw new Error('ENOENT')
			return dir.map(name => ({ name, kind: 'file' }))
		},
		read: async (path: string) => {
			const found = files[path]
			if (found === undefined) throw new Error('ENOENT')
			return JSON.stringify(found)
		},
		home: async () => '/home/j',
	})

	test('the only project family wins', async () => {
		expect((await loadPalette(reader(['ember.json', 'ember-html.json']), '')).family).toBe('ember')
	})

	test('several families with no choice fall to the global clod', async () => {
		expect((await loadPalette(reader(['ember.json', 'tidewater.json']), '')).accent).toBe('#D9A441')
	})

	test('a named family is honoured and an unknown one falls through', async () => {
		expect((await loadPalette(reader(['ember.json', 'tidewater.json']), 'ember')).family).toBe('ember')
		const fallen = await loadPalette(reader(['ember.json']), 'nope')
		expect(fallen).toEqual(CLOD)
	})

	test('no files anywhere gives the baked-in clod', async () => {
		const bare = { list: async () => [], read: async () => { throw new Error('ENOENT') }, home: async () => undefined }
		expect(await loadPalette(bare, '')).toEqual(CLOD)
		expect(await loadPalette(bare, '', 'light')).toEqual(CLOD_LIGHT)
	})
})
