import { expect, mock, test, type Engine } from 'claude-code/testing'

const PLUGIN = 'goblin-chrome'

/** The world beneath the plugin: a clock at noon on a Wednesday, an empty store, a home. */
const world = (on: Parameters<typeof mock.clock>[0]) => {
	const clock = mock.clock(on, { now: new Date(2026, 9, 7, 12, 0).getTime() })
	mock.store(on)
	mock.env(on, { HOME: '/home/j' })
	return clock
}

const BAND = {
	plugin: PLUGIN,
	surface: 'terminal',
	component: 'AbovePrompt',
	props: { hasSurvey: false, isWorking: false, maxRows: 6, bodyColumns: 100, scroll: { offset: 0, bodyRows: 6 }, view: {} },
} as const

test('the band is one hand-drawn frame: rune, goblin and dialogue ranges split by dividers that join the rules', async ($, on) => {
	world(on)
	const ui = await $.ui.mount(BAND)
	expect(await ui.find({ type: 'Client', key: 'goblin' })).toBeDefined()
	expect(await ui.find({ type: 'Raster', key: 'meter' })).toBeUndefined()
	expect(await ui.find({ type: 'Text', text: /cOnTeXt/ })).toBeUndefined()
	expect((await ui.find({ type: 'Text', in: 'goblin' }))?.text).toMatch(/ಠ/)
	const rules = (await ui.findAll({ type: 'Text', text: /^[┏┗]/ })).map(t => t.text)
	// Opus at 100 columns: edge, 3-cell rune range (a space, the rune, a space), 51 and 42 cells, edge
	expect(rules).toEqual([
		`┏${'━'.repeat(3)}┳${'━'.repeat(51)}┳${'━'.repeat(42)}┓`,
		`┗${'━'.repeat(3)}┻${'━'.repeat(51)}┻${'━'.repeat(42)}┛`,
	])
	// the dividers and the two edges are the frame's own glyph, in its colour
	const bars = await ui.findAll({ type: 'Text', text: '┃' })
	expect(bars).toHaveLength(4)
	for (const bar of bars) expect(bar.props.color).toBe((await ui.find({ type: 'Text', text: /^┏/ }))?.props.color)
	// the rune is centred: one space either side
	const rune = await ui.find({ type: 'Text', text: 'ᛟ' })
	expect(rune).toBeDefined()
	const drawn = JSON.stringify(await ui.drawn())
	expect(drawn.indexOf('ᛟ')).toBeLessThan(drawn.indexOf('goblin'))
})

type Drawn = { type: string; props?: { paddingX?: number }; children?: (Drawn | string)[] }

/** What the goblin is saying: the text in the band's third padded range, the dialogue at the far right. */
const spoken = async (ui: { drawn: () => Promise<unknown> }): Promise<string> => {
	const ranges: Drawn[] = []
	const walk = (node: Drawn | string): void => {
		if (typeof node === 'string') return
		if (node.type === 'Box' && node.props?.paddingX === 1) ranges.push(node)
		for (const child of node.children ?? []) walk(child)
	}
	walk((await ui.drawn()) as Drawn)
	const words: string[] = []
	const collect = (node: Drawn | string): void => {
		if (typeof node === 'string') words.push(node)
		else for (const child of node.children ?? []) collect(child)
	}
	if (ranges[2]) collect(ranges[2])
	return words.join('')
}

test('a narrow band drops the frame, a survey yields the band', async ($, on) => {
	world(on)
	on('ui.render', { component: 'AbovePrompt' }, async ($, e) => {
		const { Text } = $.ui.resolve(e)
		return Text({ children: ['SURVEY'] })
	})
	const short = await $.ui.mount({ ...BAND, props: { ...BAND.props, maxRows: 3 } })
	expect(await short.find({ type: 'Text', text: /^[┏┗]/ })).toBeUndefined()
	expect(await short.find({ type: 'Client', key: 'goblin' })).toBeDefined()
	await short.unmount()
	const survey = await $.ui.mount({ ...BAND, props: { ...BAND.props, hasSurvey: true } })
	expect(await survey.find({ type: 'Text', text: 'SURVEY' })).toBeDefined()
	expect(await survey.find({ type: 'Client' })).toBeUndefined()
})

test('poking the goblin makes it speak in the band, then fall silent', async ($, on) => {
	const clock = world(on)
	const toasts: string[] = []
	on('ui.toast', async ($, e, next) => {
		toasts.push(e.text)
		return next(e)
	})
	const ui = await $.ui.mount(BAND)
	expect(await spoken(ui)).toBe('')
	await ui.pointer({ type: 'down', x: 1, y: 0, button: 'left', in: 'goblin' })
	await ui.advance(150)
	expect(await spoken(ui)).toMatch(/[A-Z]/)
	expect(toasts).toEqual([])
	await clock.advance(7_000)
	expect(await spoken(ui)).toBe('')
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
	expect(line).toStartWith('? for shortcuts')
	expect(line).toMatch(/sAy tHe tHiNg/)
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

test('a bounced commit message is counted and heckled in the band', async ($, on) => {
	world(on)
	on('tool.call', { tool: 'Bash' }, async () => ({
		result: { stdout: '', stderr: 'commit-msg: L1 em dash: fix the message and commit again', interrupted: false },
		isError: true,
	}))
	on('turn.start', async ($, e) => ({ turnId: e.turnId }))
	on('turn.complete', async () => ({ text: '' }))
	await $.turn.start({ text: 'commit it', turnId: 't1' })
	await $.tool.call({ tool: 'Bash', command: 'git commit -m "add — thing"' })
	const band = await $.ui.mount(BAND)
	expect(await spoken(band)).toMatch(/bOuNcEd/)
	await band.unmount()
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
	expect(texts[1]?.text).toBe('(ಠ_ಠ)>')
	await ui.advance(10_000)
	const later = await ui.findAll({ type: 'Text', in: 'goblin' })
	expect(later.map(t => t.text).join('')).toMatch(/^ *<\(ಠ_ಠ\)$|^ *\(ಠ_ಠ\)>$/)
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

/** Serve skill files from a map of path to text; a relative key matches under the working directory, never under the home, and anything else is a missing file. */
const skillFiles = (on: Parameters<typeof mock.clock>[0], files: Record<string, string>) => {
	on('fs.read', async (_$, e) => {
		const hit = Object.keys(files).find(k => e.path === k || (!k.startsWith('/') && !e.path.startsWith('/home/j/') && e.path.endsWith(`/${k}`)))
		const text = hit === undefined ? undefined : files[hit]
		return text === undefined ? { deny: 'ENOENT' } : { value: text }
	})
	on('skill.prompt', async (_$, e) => ({ text: e.text }))
}

/** The band's top-left corner after a skill ran: `┏` for Opus, `╓` for the mismatch frame. */
const borderAfterSkill = async ($: Engine) => {
	await $.skill.prompt({ skill: 'x', text: '' })
	const ui = await $.ui.mount(BAND)
	return (await ui.find({ type: 'Text', text: /^[┏╔╓╭+]/ }))?.text?.[0]
}

test('a project skill pinning a smaller model draws the mismatch frame', async ($, on) => {
	world(on)
	skillFiles(on, { '.claude/skills/x/SKILL.md': '---\nname: x\nmodel: haiku\n---\nbody' })
	expect(await borderAfterSkill($)).toBe('╓')
})

const PR_LAND = '---\nname: pr-land\nmodel: opus\nmetadata:\n  glyph: ᛟ\n  family: pr\n  goblin-spinner: merging|deleting evidence|tagging\n---\nbody'

/** The main loop's spinner id as a live session draws it: the session's own UUID, never a fixed word. */
const MAIN_LOOP = '4f7f27db-de9c-47fb-a784-47fbea7cf901'

const SPINNER = {
	plugin: PLUGIN,
	surface: 'terminal',
	component: 'Spinner',
	requestId: MAIN_LOOP,
	props: { word: 'Baked', message: null, suffix: '…', mode: 'thinking' },
} as const

/** The spinner's word as drawn: the engine's own row, beneath ours. */
const spinnerWord = async ($: Engine, requestId: string = MAIN_LOOP) => {
	const ui = await $.ui.mount({ ...SPINNER, requestId })
	const word = (await ui.find({ type: 'Text' }))?.text
	await ui.unmount()
	return word
}

test('a skill with spinner words takes over the spinner for the turn, one word a minute, dressed like the house verbs', async ($, on) => {
	const clock = world(on)
	skillFiles(on, { '.claude/skills/pr-land/SKILL.md': PR_LAND })
	on('ui.render', { component: 'Spinner' }, async ($, e) => {
		const { Text } = $.ui.resolve(e)
		return Text({ children: [e.props.word] })
	})
	on('turn.start', async ($, e) => ({ turnId: e.turnId }))
	on('turn.complete', async () => ({ text: '' }))
	on('agent.spawn', async () => ({ model: 'claude-sonnet-5-5', agentId: 'agent-1' }))
	expect(await spinnerWord($)).toBe('Baked')
	await $.turn.start({ text: '/pr-land', turnId: 't1' })
	await $.skill.prompt({ skill: 'pr-land', text: '' })
	const first = await spinnerWord($)
	expect(first).toMatch(/^••• [a-zA-Z ]+ •••$/)
	expect(first).toMatch(/[A-Z]/)
	await clock.advance(60_000)
	const second = await spinnerWord($)
	expect(second).not.toBe(first)
	// a subagent's spinner (its id is the agent id) keeps the engine's word; the main loop's keeps ours
	await $.agent.spawn({ ...SPAWN, subagentType: 'Explore' })
	expect(await spinnerWord($, 'agent-1')).toBe('Baked')
	expect(await spinnerWord($)).toMatch(/^••• /)
	await $.turn.complete({ answer: 'done', durationMs: 3_000, isAborted: false, turnId: 't1', reason: 'answer' })
	expect(await spinnerWord($)).toBe('Baked')
})

test('a skill without spinner words leaves the spinner alone', async ($, on) => {
	world(on)
	skillFiles(on, { '.claude/skills/x/SKILL.md': '---\nname: x\nmetadata:\n  family: pr\n---\nbody' })
	on('ui.render', { component: 'Spinner' }, async ($, e) => {
		const { Text } = $.ui.resolve(e)
		return Text({ children: [e.props.word] })
	})
	await $.skill.prompt({ skill: 'x', text: '' })
	expect(await spinnerWord($)).toBe('Baked')
})

/** The idle goblin's props as the band hands them over. */
const goblinProps = async ($: Engine) => {
	const ui = await $.ui.mount(BAND)
	const props = (await ui.find({ type: 'Client', key: 'goblin' }))?.props.props as Record<string, unknown> | undefined
	await ui.unmount()
	return props
}

test("the goblin holds the family's prop while the skill runs and drops it when the turn completes", async ($, on) => {
	world(on)
	skillFiles(on, { '.claude/skills/pr-land/SKILL.md': PR_LAND })
	on('turn.start', async ($, e) => ({ turnId: e.turnId }))
	on('turn.complete', async () => ({ text: '' }))
	expect(await goblinProps($)).toMatchObject({ prop: '' })
	await $.turn.start({ text: '/pr-land', turnId: 't1' })
	await $.skill.prompt({ skill: 'pr-land', text: '' })
	expect(await goblinProps($)).toMatchObject({ prop: '[#]', mode: 'working' })
	// the watching goblin is drawn with the parcel in hand
	const ui = await $.ui.mount(BAND)
	await ui.resize({ columns: 30, rows: 1, in: 'goblin' })
	await ui.advance(150)
	expect((await ui.findAll({ type: 'Text', in: 'goblin' })).map(t => t.text).join('')).toMatch(/\(ಠ_ಠ\)\[#\]$/)
	await ui.unmount()
	await $.turn.complete({ answer: 'done', durationMs: 3_000, isAborted: false, turnId: 't1', reason: 'answer' })
	expect(await goblinProps($)).toMatchObject({ prop: '' })
})

const SPAWN = {
	tool_use_id: 'tu1',
	prompt: 'look around',
	description: 'explore',
	provider: { plugin: 'engine', tier: 'core' },
	parentModel: 'claude-opus-5-5',
	background: true,
	fork: false,
} as const

test('each subagent out is a minion beside the goblin, wearing its agent file face, until its turn completes', async ($, on) => {
	world(on)
	skillFiles(on, { '/home/j/.claude/agents/scope-guard.md': '---\nname: scope-guard\ngoblin-minion: o.O\n---\nbody' })
	let n = 0
	on('agent.spawn', async () => ({ model: 'claude-sonnet-5-5', agentId: `a${++n}` }))
	on('turn.complete', async () => ({ text: '' }))
	on('classic.SessionStart', async () => ({}))
	expect(await goblinProps($)).toMatchObject({ minions: [] })
	await $.agent.spawn({ ...SPAWN, subagentType: 'scope-guard' })
	await $.agent.spawn({ ...SPAWN, subagentType: 'Explore' })
	expect(await goblinProps($)).toMatchObject({ minions: ['o.O', 'o.o'] })
	const band = await $.ui.mount(BAND)
	expect(await spoken(band)).toMatch(/2 mInIoNs oUt/)
	await band.unmount()
	// the first one home leaves the parade; the second stays
	await $.turn.complete({ answer: 'found it', durationMs: 41_000, isAborted: false, turnId: 't-a1', reason: 'answer', agentId: 'a1' })
	expect(await goblinProps($)).toMatchObject({ minions: ['o.o'] })
	const after = await $.ui.mount(BAND)
	expect(await spoken(after)).toMatch(/mInIoN bAcK/)
	await after.unmount()
	// the main turn ending leaves the minion still out; only its own turn, or a fresh session, ends it
	await $.turn.complete({ answer: 'done', durationMs: 60_000, isAborted: false, turnId: 't1', reason: 'answer' })
	expect(await goblinProps($)).toMatchObject({ minions: ['o.o'] })
	await $.classic.SessionStart({ source: 'clear' })
	expect(await goblinProps($)).toMatchObject({ minions: [] })
})

test('subagents spawned together all join the parade', async ($, on) => {
	world(on)
	let n = 0
	on('agent.spawn', async () => ({ model: 'claude-sonnet-5-5', agentId: `p${++n}` }))
	await Promise.all(['Explore', 'Plan', 'scope-guard'].map(subagentType => $.agent.spawn({ ...SPAWN, subagentType })))
	expect(await goblinProps($)).toMatchObject({ minions: ['o.o', 'o.o', 'o.o'] })
})

test('a refused spawn adds no minion', async ($, on) => {
	world(on)
	on('agent.spawn', async () => ({ deny: 'no' }))
	await $.agent.spawn({ ...SPAWN, subagentType: 'Explore' }).catch(() => undefined)
	expect(await goblinProps($)).toMatchObject({ minions: [] })
})

test('a personal skill shadows a project skill of the same name', async ($, on) => {
	world(on)
	skillFiles(on, {
		'/home/j/.claude/skills/x/SKILL.md': '---\nname: x\nmodel: opus\n---\nbody',
		'.claude/skills/x/SKILL.md': '---\nname: x\nmodel: haiku\n---\nbody',
	})
	expect(await borderAfterSkill($)).toBe('┏')
})
