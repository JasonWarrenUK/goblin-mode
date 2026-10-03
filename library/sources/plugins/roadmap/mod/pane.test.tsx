import { expect, mock, test } from 'claude-code/testing'

import { parseSnapshot, startFor } from './register'

const PLUGIN = 'roadmap'
const NOON = new Date(2026, 9, 7, 12, 0).getTime()

const READY = JSON.stringify({
	phase: 'Phase 2',
	candidates: [
		{ id: '2SE.1', description: 'index the search', milestone: 'M2', milestoneName: 'Search', milestoneDonePct: 40, transitiveUnblocks: 3, isMilestoneSink: false, assignee: '' },
		{ id: '2SE.4', description: 'close out the facets', milestone: 'M2', milestoneName: 'Search', milestoneDonePct: 40, transitiveUnblocks: 0, isMilestoneSink: true, assignee: 'Jaz' },
	],
	claimed: [{ id: '2SE.2', description: 'the ranking', assignee: 'Max', started: '2026-10-01' }],
})
const STATS = JSON.stringify({ phase: 'Phase 2', donePct: 42, milestones: [{ id: 'M1', name: 'Core', donePct: 100 }, { id: 'M2', name: 'Search', donePct: 40 }] })

type On = Parameters<typeof mock.clock>[0]

/** The world beneath the plugin: a clock, a store, and a python that answers the CLI by subcommand. */
const world = (on: On, detectExit = 0) => {
	const calls: string[][] = []
	const toasts: string[] = []
	mock.clock(on, { now: NOON })
	mock.store(on)
	on('session.start', async ($, e) => ({ cwd: e.cwd }))
	on('process.run', async ($, e) => {
		const argv = e.argv
		calls.push([...argv])
		const sub = argv[2]
		const ok = (stdout: string) => ({ value: { exitCode: 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } })
		if (sub === 'detect') return { value: { exitCode: detectExit, stdout: '', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
		if (sub === 'ready') return ok(READY)
		if (sub === 'stats') return ok(STATS)
		if (sub === 'claim') return ok(`claimed ${argv[3]}`)
		return { value: { exitCode: 1, stdout: '', stderr: 'unknown', isStdoutTruncated: false, isStderrTruncated: false } }
	})
	on('ui.open', async () => ({ value: { isPlaced: true } }))
	on('ui.toast', async ($, e) => {
		toasts.push(e.text)
		return { value: undefined }
	})
	return { calls, toasts }
}

const RUN = { origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 100 }, args: '' } as const

const PANE = {
	plugin: PLUGIN,
	surface: 'terminal',
	component: 'Pane',
	requestId: 'ready',
	props: { title: 'ready', isFocused: true, bodyColumns: 100, placement: 'inline', scroll: { offset: 0, bodyRows: 16 }, view: {} },
} as const

test('the snapshot is read defensively from the two CLI documents', async () => {
	const snap = parseSnapshot(READY, STATS, NOON)
	expect(snap).toMatchObject({ ok: true, phase: 'Phase 2', donePct: 42, at: NOON })
	expect(snap.candidates.map(c => c.id)).toEqual(['2SE.1', '2SE.4'])
	expect(snap.milestones[1]).toEqual({ id: 'M2', name: 'Search', donePct: 40 })
	expect(parseSnapshot('{"candidates": [{"id": 7}]}', '{}', NOON).candidates[0]?.id).toBe('7')
	expect(() => parseSnapshot('[]', '{}', NOON)).toThrow('not an object')
	expect(startFor('2SE.1', '/next-task-ship {id}')).toEqual({ command: 'next-task-ship', args: '2SE.1' })
	expect(startFor('2SE.1', '/ready')).toEqual({ command: 'ready', args: '' })
	expect(startFor('2SE.1', 'roadmap:claim {id} Jaz')).toEqual({ command: 'roadmap:claim', args: '2SE.1 Jaz' })
})

test('/ready refreshes from the CLI and draws the ready set in order', async ($, on) => {
	const { calls } = world(on)
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	expect(await $.command.run({ ...RUN, command: 'ready' })).toEqual({})
	expect(calls.map(c => c[2])).toEqual(['detect', 'ready', 'stats'])
	expect(calls[0]?.[1]).toEndWith('/scripts/roadmap.py')
	const ui = await $.ui.mount(PANE)
	expect((await ui.find({ type: 'Text' }))?.text).toBe('Phase 2 · 42% done · M1 100%  M2 40%')
	const rows = await ui.findAll({ type: 'Button' })
	expect(rows.map(r => r.props.label)).toEqual([
		'  2SE.1  index the search · unblocks 3 · M2 40%',
		'  2SE.4  close out the facets · unblocks 0 · M2 40% · completes it · Jaz',
	])
	expect(await ui.find({ type: 'Text', text: /claimed 2SE\.2 by Max since 2026-10-01/ })).toBeDefined()
})

test('a picked row offers claim and start; claim asks who and runs the CLI', async ($, on) => {
	const { calls, toasts } = world(on)
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	const ui = await $.ui.mount(PANE)
	expect(await ui.find({ key: 'claim' })).toBeUndefined()
	await ui.press({ key: 'row-2SE.1' })
	expect((await ui.find({ key: 'row-2SE.1' }))?.props.label).toStartWith('▶ 2SE.1')
	expect(await ui.find({ key: 'claim' })).toBeDefined()
	await ui.press({ key: 'claim' })
	const input = await ui.find({ type: 'Input', key: 'assignee' })
	expect(input?.props.label).toBe('who is doing 2SE.1')
	expect(input?.props.value).toBe('')
	await ui.input({ key: 'assignee', text: '  ' })
	expect(toasts).toEqual(['a claim needs a name.'])
	await ui.input({ key: 'assignee', text: 'Jaz' })
	expect(calls.some(c => c.slice(2).join(' ') === 'claim 2SE.1 --assignee Jaz')).toBe(true)
	expect(toasts[1]).toBe('claimed 2SE.1 for Jaz. commit roadmaps.json when you are ready.')
	expect(await ui.find({ type: 'Input' })).toBeUndefined()
})

test('start runs the configured command for the picked task', { options: { start_command: '/next-task-ship {id}' } }, async ($, on) => {
	const { toasts } = world(on)
	const ran: string[] = []
	on('command.run', { command: 'next-task-ship' }, async ($, e) => {
		ran.push(`${e.command} ${e.args}`)
		return { text: 'shipping' }
	})
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	const ui = await $.ui.mount(PANE)
	await ui.press({ key: 'row-2SE.4' })
	await ui.press({ key: 'start' })
	expect(ran).toEqual(['next-task-ship 2SE.4'])
	expect(toasts).toEqual(['running /next-task-ship 2SE.4'])
})

test('no roadmap and the old format each say so instead of a list', async ($, on) => {
	world(on, 2)
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	const ui = await $.ui.mount(PANE)
	expect((await ui.find({ type: 'Text' }))?.text).toBe('no roadmap above this directory')
	expect(await ui.find({ type: 'Button' })).toBeUndefined()
})
