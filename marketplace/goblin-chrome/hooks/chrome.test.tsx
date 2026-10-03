import { expect, mock, test } from 'claude-code/testing'

const PLUGIN = 'goblin-chrome'

/** The world beneath the plugin: a clock at noon on a Wednesday, an empty store, a home. */
const world = (on: Parameters<typeof mock.clock>[0]) => {
	mock.clock(on, { now: new Date(2026, 9, 7, 12, 0).getTime() })
	mock.store(on)
	mock.env(on, { HOME: '/home/j' })
}

const BAND = {
	plugin: PLUGIN,
	surface: 'terminal',
	component: 'AbovePrompt',
	props: { hasSurvey: false, isWorking: false, maxRows: 6, bodyColumns: 100, scroll: { offset: 0, bodyRows: 6 }, view: {} },
} as const

test('the band holds the goblin, the metre and a voice line in a double frame', async ($, on) => {
	world(on)
	const ui = await $.ui.mount(BAND)
	const root = await ui.find({ type: 'Box' })
	expect(root?.props.borderStyle).toBe('double')
	expect(await ui.find({ type: 'Client', key: 'goblin' })).toBeDefined()
	expect(await ui.find({ type: 'Raster', key: 'meter' })).toBeDefined()
	expect(await ui.find({ type: 'Text', text: /cOnTeXt 0%/ })).toBeDefined()
	expect((await ui.find({ type: 'Text', in: 'goblin' }))?.text).toMatch(/ᐛ/)
})

test('a narrow band drops the frame, a survey yields the band', async ($, on) => {
	world(on)
	on('ui.render', { component: 'AbovePrompt' }, async ($, e) => {
		const { Text } = $.ui.resolve(e)
		return Text({ children: ['SURVEY'] })
	})
	const short = await $.ui.mount({ ...BAND, props: { ...BAND.props, maxRows: 3 } })
	expect((await short.find({ type: 'Box' }))?.props.borderStyle).toBeUndefined()
	await short.unmount()
	const survey = await $.ui.mount({ ...BAND, props: { ...BAND.props, hasSurvey: true } })
	expect(await survey.find({ type: 'Text', text: 'SURVEY' })).toBeDefined()
	expect(await survey.find({ type: 'Client' })).toBeUndefined()
})

test('poking the goblin raises a toast', async ($, on) => {
	world(on)
	const toasts: string[] = []
	on('ui.toast', async ($, e, next) => {
		toasts.push(e.text)
		return next(e)
	})
	const ui = await $.ui.mount(BAND)
	await ui.pointer({ type: 'down', x: 1, y: 0, button: 'left', in: 'goblin' })
	await ui.advance(150)
	expect(toasts.length).toBeGreaterThan(0)
	expect(toasts[0]).toMatch(/[A-Z]/)
})

test('the hint keeps the engine line and adds a tail', async ($, on) => {
	world(on)
	on('ui.render', { component: 'PromptHint' }, async ($, e) => {
		const { Text } = $.ui.resolve(e)
		return Text({ children: [e.props.hint + (e.props.tail ?? '')] })
	})
	const ui = await $.ui.mount({
		plugin: PLUGIN,
		surface: 'terminal',
		component: 'PromptHint',
		props: { isDraft: false, isWorking: false, hint: '? for shortcuts' },
	})
	const line = (await ui.find({ type: 'Text' }))?.text ?? ''
	expect(line).toStartWith('? for shortcuts · ')
	expect(line).toMatch(/sAy tHe tHiNg/)
})

test('the footer pills are renamed', async ($, on) => {
	world(on)
	on('ui.render', { component: 'SessionMode' }, async ($, e) => {
		const { Text } = $.ui.resolve(e)
		return Text({ children: [e.props.modes.join(' & ')] })
	})
	const ui = await $.ui.mount({
		plugin: PLUGIN,
		surface: 'terminal',
		component: 'SessionMode',
		props: { modes: ['plan', 'accept edits', 'memory paused'] },
	})
	expect((await ui.find({ type: 'Text' }))?.text).toBe('sChEmInG & lEt It CoOk & fOrGeTtInG')
})

test('the turn closes in goblin register with the real duration', async ($, on) => {
	world(on)
	const ui = await $.ui.mount({
		plugin: PLUGIN,
		surface: 'terminal',
		component: 'TurnDuration',
		props: { word: 'Baked', durationMs: 64_000 },
	})
	expect((await ui.find({ type: 'Text' }))?.text).toBe('dOnE. 1m 4s.')
})

test('a question gets a face above the engine dialog, kept once', async ($, on) => {
	world(on)
	// The engine's own dialog, as `next(e)` hands it back in a session.
	on('ui.render', { component: 'AskUserQuestion' }, async () => ({ type: 'engine', ref: 0 }))
	const ui = await $.ui.mount({
		plugin: PLUGIN,
		surface: 'terminal',
		component: 'AskUserQuestion',
		props: { tool: 'AskUserQuestion', questions: [{ question: 'Proceed?' }] },
	})
	expect(await ui.find({ type: 'Raster', key: 'face' })).toBeDefined()
	expect(await ui.find({ type: 'Text', text: /gO oN tHeN/ })).toBeDefined()
	expect(JSON.stringify(await ui.drawn()).split('"type":"engine"')).toHaveLength(2)
})

test('a bounced commit message is counted and heckled', async ($, on) => {
	world(on)
	const toasts: string[] = []
	on('ui.toast', async ($, e, next) => {
		toasts.push(e.text)
		return next(e)
	})
	on('tool.call', { tool: 'Bash' }, async () => ({
		result: { stdout: '', stderr: 'commit-msg: L1 em dash: fix the message and commit again', interrupted: false },
		isError: true,
	}))
	on('turn.start', async ($, e) => ({ turnId: e.turnId }))
	on('turn.complete', async () => ({ text: '' }))
	await $.turn.start({ text: 'commit it', turnId: 't1' })
	await $.tool.call({ tool: 'Bash', command: 'git commit -m "add — thing"' })
	expect(toasts.some(t => /bOuNcEd/.test(t))).toBe(true)
	await $.turn.complete({ answer: 'done', durationMs: 3_000, isAborted: false, turnId: 't1', reason: 'answer' })
	const line = async (durationMs: number) => {
		const ui = await $.ui.mount({ plugin: PLUGIN, surface: 'terminal', component: 'TurnDuration', props: { word: 'Baked', durationMs } })
		return (await ui.find({ type: 'Text' }))?.text
	}
	expect(await line(3_000)).toBe('dOnE. 3s. tOoK 1 tHiNg. bIt mE oNcE.')
	// an older row draws its duration alone, never the live counts
	expect(await line(9_000)).toBe('dOnE. 9s.')
})

test('the goblin paces on its own clock without unmounting, and faces the way it walks', async ($, on) => {
	world(on)
	const ui = await $.ui.mount(BAND)
	await ui.resize({ columns: 20, rows: 1, in: 'goblin' })
	await ui.advance(1_200)
	const texts = await ui.findAll({ type: 'Text', in: 'goblin' })
	expect(texts[0]?.text).toBe('  ')
	expect(texts[1]?.text).toBe('ᕕ( ᐛ )ᕗ')
	await ui.advance(10_000)
	const later = await ui.findAll({ type: 'Text', in: 'goblin' })
	expect(later.map(t => t.text).join('')).toMatch(/^ *ᕗ\( ᐛ \)ᕕ$|^ *ᕕ\( ᐛ \)ᕗ$/)
})

test('a dropped prompt leaves the goblin idle; a turn makes it watch', async ($, on) => {
	world(on)
	on('prompt.submit', async () => ({ drop: 'not now' }))
	on('turn.start', async ($, e) => ({ turnId: e.turnId }))
	await $.prompt.submit({ text: 'go', wait: false, origin: { kind: 'composer' } })
	const idle = await $.ui.mount(BAND)
	expect((await idle.find({ type: 'Client', key: 'goblin' }))?.props.props).toMatchObject({ mode: 'idle' })
	await idle.unmount()
	await $.turn.start({ text: 'go', turnId: 't2' })
	const busy = await $.ui.mount(BAND)
	expect((await busy.find({ type: 'Client', key: 'goblin' }))?.props.props).toMatchObject({ mode: 'working' })
})
