import { expect, mock, test } from 'claude-code/testing'

import { bar, groupByTier, nextGroupBy, parseFirst, parseGrouping, parseSnapshot, reasonOf, ruleTail, subgroup, tierHue } from './register'

const PLUGIN = 'roadmap'
const NOON = new Date(2026, 9, 7, 12, 0).getTime()

const READY = JSON.stringify({
	phase: 'Phase 2',
	candidates: [
		{ id: '2SE.1', description: 'index the search', milestone: 'M2', milestoneName: 'Search', milestoneDonePct: 40, tier: 0, tierLabel: 'Core', transitiveUnblocks: 3, isMilestoneSink: false, assignee: '' },
		{ id: '2SE.4', description: 'close out the facets', milestone: 'M2', milestoneName: 'Search', milestoneDonePct: 40, tier: 0, tierLabel: 'Core', transitiveUnblocks: 0, isMilestoneSink: true, assignee: 'Jaz' },
	],
	claimed: [{ id: '2SE.2', description: 'the ranking', assignee: 'Max', started: '2026-10-01' }],
})
const STATS = JSON.stringify({
	phase: 'Phase 2',
	donePct: 42,
	inScope: 12,
	byStatus: { done: 5 },
	milestones: [
		{ id: 'M1', name: 'Core', donePct: 100, tier: 0, tierLabel: 'Core', state: 'done' },
		{ id: 'M2', name: 'Search', donePct: 40, tier: 0, tierLabel: 'Core', state: 'inProgress' },
		{ id: 'M3', name: 'Export (Secondary)', donePct: 0, tier: 1, tierLabel: 'Secondary', state: 'deferred' },
	],
})

type On = Parameters<typeof mock.clock>[0]

/** The world beneath the plugin: a clock, a store, and a python that answers the CLI by subcommand. */
const world = (on: On, detectExit = 0, readyRefusal: string | null = null, ready = READY, stored: Record<string, unknown> = {}) => {
	const calls: string[][] = []
	const toasts: string[] = []
	// the plugin's store in memory, seeded with `stored`, so a test reads back what the pane kept
	const saved: Record<string, unknown> = { ...stored }
	mock.clock(on, { now: NOON })
	on('store.get', async ($, e) => ({ value: saved[e.key] }))
	on('store.set', async ($, e) => {
		saved[e.key] = e.value
		return { value: undefined }
	})
	on('session.start', async ($, e) => ({ cwd: e.cwd }))
	const panes = { open: [] as string[] }
	on('ui.panes', async () => ({ value: panes.open.map(id => ({ id, title: id, isShown: true, isFocused: true, isPlaced: true })) }))
	on('ui.close', async ($, e) => {
		panes.open = panes.open.filter(id => id !== e.id)
		return { value: undefined }
	})
	on('process.run', async ($, e) => {
		const argv = e.argv
		calls.push([...argv])
		// the CLI is run in the session's own working directory, read per call
		expect(e.init?.cwd).toBeUndefined()
		const sub = argv[2]
		const ok = (stdout: string) => ({ value: { exitCode: 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } })
		if (sub === 'detect') return { value: { exitCode: detectExit, stdout: detectExit === 2 ? '✗ could not locate .claude/roadmaps.json above the current directory' : '', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
		if (sub === 'ready' && readyRefusal !== null) return { value: { exitCode: 2, stdout: readyRefusal, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
		if (sub === 'ready') return ok(ready)
		if (sub === 'stats') return ok(STATS)
		if (sub === 'claim') return ok(`claimed ${argv[3]}`)
		if (sub === 'assign') return ok(`assigned ${argv[3]}`)
		return { value: { exitCode: 1, stdout: '', stderr: 'unknown', isStdoutTruncated: false, isStderrTruncated: false } }
	})
	on('ui.open', async ($, e) => {
		if (!panes.open.includes(e.id)) panes.open.push(e.id)
		return { value: { isPlaced: true } }
	})
	on('ui.toast', async ($, e) => {
		toasts.push(e.text)
		return { value: undefined }
	})
	return { calls, toasts, panes, saved }
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
	expect(snap).toMatchObject({ ok: true, problem: 'none', phase: 'Phase 2', donePct: 42, doneCount: 5, inScope: 12, at: NOON })
	expect(snap.candidates.map(c => c.id)).toEqual(['2SE.1', '2SE.4'])
	expect(snap.milestones[1]).toEqual({ id: 'M2', name: 'Search', donePct: 40, tier: 0, tierLabel: 'Core', state: 'inProgress' })
	expect(snap.milestones[2]?.tier).toBe(1)
	expect(parseSnapshot('{"candidates": [{"id": 7}]}', '{}', NOON).candidates[0]?.id).toBe('7')
	expect(() => parseSnapshot('[]', '{}', NOON)).toThrow('not an object')
	expect(reasonOf({ stdout: '✗ 2 active phases; pass --phase NAME\n', stderr: '' }, 'x')).toBe('✗ 2 active phases; pass --phase NAME')
	expect(reasonOf({ stdout: '', stderr: 'Traceback (most recent call last):\n  File "x"\nKeyError: \'tasks\'\n' }, 'x')).toBe("KeyError: 'tasks'")
	expect(reasonOf({ stdout: '', stderr: '' }, 'fallback')).toBe('fallback')
})

test('the drawing helpers are pure', () => {
	expect(bar(0, 5)).toBe('░░░░░')
	expect(bar(60, 5)).toBe('███░░')
	expect(bar(100, 5)).toBe('█████')
	expect(bar(250, 5)).toBe('█████')
	expect(`── Ready now · 2 ${ruleTail('Ready now · 2', 24)}`).toBe('── Ready now · 2 ───────')
	expect(ruleTail('x', 3)).toBe('──')
	expect(tierHue(0)).not.toBe(tierHue(1))
	expect(tierHue(4)).toBe(tierHue(0))
	const groups = groupByTier(parseSnapshot(READY, STATS, NOON).milestones)
	expect(groups.map(g => [g.tier, g.label, g.milestones.map(m => m.id)])).toEqual([
		[0, 'Core', ['M1', 'M2']],
		[1, 'Secondary', ['M3']],
	])
	expect(nextGroupBy('dev')).toBe('milestone')
	expect(nextGroupBy('none')).toBe('dev')
	expect(parseFirst(' Jason, jaz ,, ')).toEqual(['Jason', 'jaz'])
	expect(parseGrouping(undefined, undefined)).toEqual({ by: 'dev', first: [] })
	expect(parseGrouping('tier', ['Jaz', 7, ' '])).toEqual({ by: 'tier', first: ['Jaz'] })
	expect(parseGrouping('weekday', 'Jaz')).toEqual({ by: 'dev', first: [] })
})

const candidate = (id: string, assignee: string, milestone: string, tier: number) => ({
	id,
	description: id,
	milestone,
	milestoneName: `about ${milestone}`,
	milestoneDonePct: 0,
	tier,
	tierLabel: '',
	transitiveUnblocks: 0,
	isMilestoneSink: false,
	assignee,
})

test('the ready set splits into subgroups that keep leverage order, led by the names asked for', () => {
	const set = [candidate('A', 'Jaz', 'M11', 1), candidate('B', '', 'M8', 1), candidate('C', 'Jason', 'M2', 0), candidate('D', 'jaz', 'M8', 1), candidate('E', '', 'M2', 0)]
	const ids = (groups: ReturnType<typeof subgroup>) => groups.map(g => [g.label, g.members.map(c => c.id)])
	// devs alphabetically, the unassigned last, the two spellings of Jaz kept apart since the roadmap keeps them apart
	expect(ids(subgroup(set, 'dev', []))).toEqual([
		['Jason', ['C']],
		['Jaz', ['A']],
		['jaz', ['D']],
		['unassigned', ['B', 'E']],
	])
	// a name put first leads whatever its case; the rest keep the natural order
	expect(ids(subgroup(set, 'dev', ['JAZ'])).map(g => g[0])).toEqual(['Jaz', 'jaz', 'Jason', 'unassigned'])
	expect(ids(subgroup(set, 'dev', ['unassigned', 'Jason'])).map(g => g[0])).toEqual(['unassigned', 'Jason', 'Jaz', 'jaz'])
	// milestones by number, not by string, so M8 comes before M11
	expect(ids(subgroup(set, 'milestone', []))).toEqual([
		['M2 about M2', ['C', 'E']],
		['M8 about M8', ['B', 'D']],
		['M11 about M11', ['A']],
	])
	expect(ids(subgroup(set, 'milestone', ['m8'])).map(g => g[0])).toEqual(['M8 about M8', 'M2 about M2', 'M11 about M11'])
	expect(ids(subgroup(set, 'tier', []))).toEqual([
		['Core', ['C', 'E']],
		['Secondary', ['A', 'B', 'D']],
	])
	expect(ids(subgroup(set, 'none', []))).toEqual([['', ['A', 'B', 'C', 'D', 'E']]])
})

test('/ready refreshes from the CLI and draws the header, the ready set in order and the claims', async ($, on) => {
	const { calls } = world(on)
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	expect(await $.command.run({ ...RUN, command: 'ready' })).toEqual({})
	expect(calls.map(c => c[2])).toEqual(['detect', 'ready', 'stats'])
	expect(calls[0]?.[1]).toEndWith('/scripts/roadmap.py')
	const ui = await $.ui.mount(PANE)
	expect(await ui.find({ type: 'Text', text: 'Phase 2' })).toBeDefined()
	expect(await ui.find({ type: 'Text', text: '42%' })).toBeDefined()
	expect(await ui.find({ type: 'Text', text: '5/12 tasks' })).toBeDefined()
	expect(await ui.find({ type: 'Text', text: /Core/ })).toBeDefined()
	expect(await ui.find({ type: 'Text', text: /Secondary/ })).toBeDefined()
	const rows = await ui.findAll({ type: 'Button' })
	// grouped by dev out of the box: Jaz's row leads, the unassigned one follows, the digits follow the drawn order
	expect(rows.map(r => r.props.label)).toEqual(['2SE.4', '2SE.1', '2SE.2', 'group: dev', 'first: natural', 'refresh'])
	expect(rows.map(r => r.props.hotkey)).toEqual(['1', '2', 'q', 'g', 's', 'r'])
	expect(await ui.find({ type: 'Text', text: 'Ready now · 2' })).toBeDefined()
	expect(await ui.find({ key: 'sub-Jaz' })).toBeDefined()
	expect(await ui.find({ key: 'sub-unassigned' })).toBeDefined()
	expect(await ui.find({ type: 'Text', text: 'index the search' })).toBeDefined()
	expect(await ui.find({ type: 'Text', text: 'unblocks 3' })).toBeDefined()
	expect(await ui.find({ type: 'Text', text: 'completes it' })).toBeDefined()
	expect(await ui.find({ type: 'Text', text: '● Jaz' })).toBeDefined()
	expect(await ui.find({ type: 'Text', text: 'since 2026-10-01' })).toBeDefined()
})

test('a picked row offers claim; claim asks who and runs the CLI', async ($, on) => {
	const { calls, toasts } = world(on)
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	const ui = await $.ui.mount(PANE)
	expect(await ui.find({ key: 'claim' })).toBeUndefined()
	expect(await ui.find({ type: 'Text', text: '▶' })).toBeUndefined()
	await ui.press({ key: 'row-2SE.1' })
	expect(await ui.find({ type: 'Text', text: '▶' })).toBeDefined()
	expect(await ui.find({ key: 'claim' })).toBeDefined()
	await ui.press({ key: 'claim' })
	const input = await ui.find({ type: 'Input', key: 'assignee' })
	expect(input?.props.label).toBe('who is doing 2SE.1')
	expect(input?.props.value).toBeUndefined()
	await ui.input({ key: 'assignee', text: '  ' })
	expect(toasts).toEqual(['a claim needs a name.'])
	await ui.input({ key: 'assignee', text: 'Jaz' })
	expect(calls.some(c => c.slice(2).join(' ') === 'claim 2SE.1 --assignee=Jaz --reassign')).toBe(true)
	expect(toasts[1]).toBe('claimed 2SE.1 for Jaz. commit roadmaps.json when you are ready.')
	expect(await ui.find({ type: 'Input' })).toBeUndefined()
})

test('claiming a row that already has an assignee replaces it', async ($, on) => {
	const { calls } = world(on)
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	const ui = await $.ui.mount(PANE)
	await ui.press({ key: 'row-2SE.4' })
	await ui.press({ key: 'claim' })
	await ui.input({ key: 'assignee', text: 'Max' })
	expect(calls.some(c => c.slice(2).join(' ') === 'claim 2SE.4 --assignee=Max --reassign')).toBe(true)
})

test('assign asks who and sets the assignee without claiming', async ($, on) => {
	const { calls, toasts } = world(on)
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	const ui = await $.ui.mount(PANE)
	expect(await ui.find({ key: 'assign' })).toBeUndefined()
	await ui.press({ key: 'row-2SE.1' })
	await ui.press({ key: 'assign' })
	const input = await ui.find({ type: 'Input', key: 'assignee' })
	expect(input?.props.label).toBe('who will do 2SE.1')
	await ui.input({ key: 'assignee', text: 'Jaz' })
	expect(calls.some(c => c.slice(2).join(' ') === 'assign 2SE.1 --assignee=Jaz')).toBe(true)
	expect(calls.some(c => c[2] === 'claim')).toBe(false)
	expect(toasts).toEqual(['assigned 2SE.1 to Jaz. commit roadmaps.json when you are ready.'])
	expect(await ui.find({ type: 'Input' })).toBeUndefined()
})

test('a blank assign clears the assignee', async ($, on) => {
	const { calls, toasts } = world(on)
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	const ui = await $.ui.mount(PANE)
	await ui.press({ key: 'row-2SE.4' })
	await ui.press({ key: 'assign' })
	await ui.input({ key: 'assignee', text: '  ' })
	expect(calls.some(c => c.slice(2).join(' ') === 'assign 2SE.4 --unassign')).toBe(true)
	expect(toasts).toEqual(["cleared 2SE.4's assignee. commit roadmaps.json when you are ready."])
})

test('a claim in play can be picked and reassigned, but not claimed again', async ($, on) => {
	const { calls } = world(on)
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	const ui = await $.ui.mount(PANE)
	await ui.press({ key: 'claimed-row-2SE.2' })
	expect(await ui.find({ key: 'claim' })).toBeUndefined()
	expect(await ui.find({ key: 'assign' })).toBeDefined()
	await ui.press({ key: 'assign' })
	await ui.input({ key: 'assignee', text: 'Dan' })
	expect(calls.some(c => c.slice(2).join(' ') === 'assign 2SE.2 --assignee=Dan')).toBe(true)
})

test('a claim past the ninth has no hotkey but can still be picked and reassigned', async ($, on) => {
	const claimed = Array.from({ length: 10 }, (_, i) => ({ id: `9X.${i + 1}`, description: `claim ${i + 1}`, assignee: 'Max', started: '2026-10-01' }))
	const { calls } = world(on, 0, null, JSON.stringify({ ...JSON.parse(READY), claimed }))
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	const ui = await $.ui.mount(PANE)
	await ui.press({ key: 'claimed-row-9X.10' })
	expect(await ui.find({ type: 'Text', text: '▶' })).toBeDefined()
	expect(await ui.find({ key: 'assign' })).toBeDefined()
	await ui.press({ key: 'assign' })
	await ui.input({ key: 'assignee', text: 'Dan' })
	expect(calls.some(c => c.slice(2).join(' ') === 'assign 9X.10 --assignee=Dan')).toBe(true)
})

test('every ready row draws; past the ninth a row has no digit but can still be picked', async ($, on) => {
	const candidates = Array.from({ length: 12 }, (_, i) => candidate(`9R.${i + 1}`, '', 'M9', 1))
	world(on, 0, null, JSON.stringify({ ...JSON.parse(READY), candidates }))
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	const ui = await $.ui.mount(PANE)
	const rows = (await ui.findAll({ type: 'Button' })).filter(r => r.key?.startsWith('row-'))
	expect(rows).toHaveLength(12)
	expect(rows.map(r => r.props.hotkey)).toEqual(['1', '2', '3', '4', '5', '6', '7', '8', '9', undefined, undefined, undefined])
	expect(await ui.find({ type: 'Text', text: /more below the fold/ })).toBeUndefined()
	await ui.press({ key: 'row-9R.12' })
	expect(await ui.find({ key: 'claim' })).toBeDefined()
	await ui.press({ key: 'claim' })
	expect((await ui.find({ type: 'Input', key: 'assignee' }))?.props.label).toBe('who is doing 9R.12')
})

test('g cycles what the set is grouped by and the store remembers it', async ($, on) => {
	const { saved } = world(on)
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	const ui = await $.ui.mount(PANE)
	expect(await ui.find({ key: 'sub-Jaz' })).toBeDefined()
	await ui.press({ key: 'group' })
	expect((await ui.find({ key: 'group' }))?.props.label).toBe('group: milestone')
	expect(await ui.find({ key: 'sub-Jaz' })).toBeUndefined()
	expect(await ui.find({ key: 'sub-M2' })).toBeDefined()
	expect(await ui.find({ type: 'Text', text: 'M2 Search' })).toBeDefined()
	expect(saved.groupBy).toBe('milestone')
	// the leverage order comes back inside one milestone
	const rows = (await ui.findAll({ type: 'Button' })).filter(r => r.key?.startsWith('row-'))
	expect(rows.map(r => r.props.label)).toEqual(['2SE.1', '2SE.4'])
	await ui.press({ key: 'group' })
	await ui.press({ key: 'group' })
	expect((await ui.find({ key: 'group' }))?.props.label).toBe('group: none')
	expect(await ui.find({ key: 'sub-M2' })).toBeUndefined()
	expect(await ui.find({ key: 'sub-Jaz' })).toBeUndefined()
	await ui.press({ key: 'group' })
	expect((await ui.find({ key: 'group' }))?.props.label).toBe('group: dev')
})

test('s asks which subgroups lead; the names reorder the rows and their digits, and the store keeps them', async ($, on) => {
	const candidates = [candidate('1J.1', 'Jason', 'M1', 0), candidate('1Z.1', 'Jaz', 'M1', 0), candidate('1Z.2', 'Jaz', 'M1', 0), candidate('1U.1', '', 'M1', 0)]
	const { saved } = world(on, 0, null, JSON.stringify({ ...JSON.parse(READY), candidates }))
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	const ui = await $.ui.mount(PANE)
	const order = async () => (await ui.findAll({ type: 'Button' })).filter(r => r.key?.startsWith('row-')).map(r => `${r.props.hotkey}:${r.props.label}`)
	expect(await order()).toEqual(['1:1J.1', '2:1Z.1', '3:1Z.2', '4:1U.1'])
	await ui.press({ key: 'order' })
	const input = await ui.find({ type: 'Input', key: 'first' })
	expect(input?.props.value).toBe('')
	expect(await ui.find({ key: 'refresh' })).toBeUndefined()
	await ui.input({ key: 'first', text: 'jaz, unassigned' })
	expect(await ui.find({ type: 'Input' })).toBeUndefined()
	expect(await order()).toEqual(['1:1Z.1', '2:1Z.2', '3:1U.1', '4:1J.1'])
	expect((await ui.find({ key: 'order' }))?.props.label).toBe('first: jaz, unassigned')
	expect(saved.groupOrder).toEqual(['jaz', 'unassigned'])
	// the field opens holding what is set, and a blank answer restores the natural order
	await ui.press({ key: 'order' })
	expect((await ui.find({ type: 'Input', key: 'first' }))?.props.value).toBe('jaz, unassigned')
	await ui.input({ key: 'first', text: '  ' })
	expect(await order()).toEqual(['1:1J.1', '2:1Z.1', '3:1Z.2', '4:1U.1'])
	expect(saved.groupOrder).toEqual([])
})

test('a grouping kept on this machine is read at the start of the session', async ($, on) => {
	const candidates = [candidate('1J.1', 'Jason', 'M1', 0), candidate('1Z.1', 'Jaz', 'M1', 0)]
	world(on, 0, null, JSON.stringify({ ...JSON.parse(READY), candidates }), { groupBy: 'dev', groupOrder: ['Jaz'] })
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	const ui = await $.ui.mount(PANE)
	const rows = (await ui.findAll({ type: 'Button' })).filter(r => r.key?.startsWith('row-'))
	expect(rows.map(r => r.props.label)).toEqual(['1Z.1', '1J.1'])
	expect((await ui.find({ key: 'order' }))?.props.label).toBe('first: Jaz')
})

test('a name that starts with a dash is bound to --assignee, not read as an option', async ($, on) => {
	const { calls } = world(on)
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	const ui = await $.ui.mount(PANE)
	await ui.press({ key: 'row-2SE.1' })
	await ui.press({ key: 'claim' })
	await ui.input({ key: 'assignee', text: '-J' })
	expect(calls.some(c => c.slice(2).join(' ') === 'claim 2SE.1 --assignee=-J --reassign')).toBe(true)
	await ui.press({ key: 'row-2SE.1' })
	await ui.press({ key: 'claim' })
	await ui.input({ key: 'assignee', text: '--reassign' })
	expect(calls.some(c => c.slice(2).join(' ') === 'claim 2SE.1 --assignee=--reassign --reassign')).toBe(true)
})

test('refresh is offered before a row is picked, and hidden while the assignee input is open', async ($, on) => {
	const { calls } = world(on)
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	const ui = await $.ui.mount(PANE)
	expect(await ui.find({ key: 'claim' })).toBeUndefined()
	expect(await ui.find({ key: 'refresh' })).toBeDefined()
	const before = calls.length
	await ui.press({ key: 'refresh' })
	expect(calls.slice(before).map(c => c[2])).toEqual(['detect', 'ready', 'stats'])
	await ui.press({ key: 'row-2SE.1' })
	await ui.press({ key: 'claim' })
	expect(await ui.find({ key: 'refresh' })).toBeUndefined()
})

test('/ready opens the pane and runs again to close it', async ($, on) => {
	const { calls, panes } = world(on)
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	expect(panes.open).toEqual(['ready'])
	const runs = calls.length
	await $.command.run({ ...RUN, command: 'ready' })
	expect(panes.open).toEqual([])
	// closing runs no CLI
	expect(calls).toHaveLength(runs)
	const ui = await $.ui.mount(PANE)
	expect(await ui.find({ key: 'start' })).toBeUndefined()
})

test('no roadmap draws a card that says so and names the skill that starts one', async ($, on) => {
	world(on, 2)
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	const ui = await $.ui.mount(PANE)
	expect(await ui.find({ type: 'Text', text: 'No roadmap in this project' })).toBeDefined()
	expect(await ui.find({ type: 'Text', text: '/roadmap:create' })).toBeDefined()
	expect(await ui.find({ key: 'refresh' })).toBeDefined()
	expect(await ui.find({ key: 'claim' })).toBeUndefined()
})

test('the old single-file format points at migrate', async ($, on) => {
	world(on, 3)
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	const ui = await $.ui.mount(PANE)
	expect(await ui.find({ type: 'Text', text: 'Old roadmap format' })).toBeDefined()
	expect(await ui.find({ type: 'Text', text: '/roadmap:migrate' })).toBeDefined()
})

test("the CLI's own refusal reaches the pane", async ($, on) => {
	world(on, 0, '✗ 2 active phases; pass --phase NAME\n')
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'ready' })
	const ui = await $.ui.mount(PANE)
	expect(await ui.find({ type: 'Text', text: 'The roadmap would not load' })).toBeDefined()
	expect(await ui.find({ type: 'Text', text: '✗ 2 active phases; pass --phase NAME' })).toBeDefined()
})
