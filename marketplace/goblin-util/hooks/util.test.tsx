import { expect, mock, test } from 'claude-code/testing'

import { ago, localDate, slug } from './register'

const PLUGIN = 'goblin-util'
const NOON = new Date(2026, 9, 7, 12, 0).getTime()

type On = Parameters<typeof mock.clock>[0]

/** The world beneath the plugin: a clock, a store, a home, a session and a git that answers one branch. */
const ids = { current: 's1' }

/** A pain file the test holds: null is a missing file. */
const painFile = (on: On, initial: string | null) => {
	const file = { text: initial, writes: [] as string[] }
	on('fs.exists', async () => ({ value: file.text !== null }))
	on('fs.read', async () => {
		if (file.text === null) throw new Error('ENOENT')
		return { value: file.text }
	})
	on('fs.write', async ($, e) => {
		file.writes.push(e.path)
		file.text = e.text
		return { value: undefined }
	})
	return file
}

const world = (on: On, entries: Readonly<Record<string, unknown>> = {}) => {
	ids.current = 's1'
	const panes = { open: [] as string[] }
	on('ui.panes', async () => ({ value: panes.open.map(id => ({ id, title: id, isShown: true, isFocused: true, isPlaced: true })) }))
	on('ui.open', async ($, e) => {
		if (!panes.open.includes(e.id)) panes.open.push(e.id)
		return { value: { isPlaced: true } }
	})
	on('ui.close', async ($, e) => {
		panes.open = panes.open.filter(id => id !== e.id)
		return { value: undefined }
	})
	// A store of the test's own, so what the plugin wrote can be read back directly.
	const map = new Map<string, unknown>(Object.entries(entries))
	const clock = mock.clock(on, { now: NOON })
	const store = { map, clock, panes, sets: [] as { key: string; value: unknown }[], deletes: [] as string[] }
	on('store.get', async ($, e) => ({ value: map.get(e.key) }))
	on('store.keys', async () => ({ value: [...map.keys()] }))
	on('store.set', async ($, e) => {
		map.set(e.key, JSON.parse(JSON.stringify(e.value)))
		store.sets.push({ key: e.key, value: e.value })
		return { value: undefined }
	})
	on('store.delete', async ($, e) => {
		map.delete(e.key)
		store.deletes.push(e.key)
		return { value: undefined }
	})
	mock.env(on, { HOME: '/home/j' })
	on('session.start', async ($, e) => ({ cwd: e.cwd }))
	on('turn.start', async ($, e) => ({ turnId: e.turnId }))
	on('turn.complete', async () => ({ text: '' }))
	on('session.id', async () => ({ value: ids.current }))
	on('session.cwd', async () => ({ value: '/code/app' }))
	on('session.repo', async () => ({ value: { root: '/code/app', remote: null, internal: false, name: null } }))
	on('process.run', async () => ({
		value: { exitCode: 0, stdout: 'feat/search\n', stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
	}))
	return store
}

const RUN = { origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 100 } } as const

const PANE = (id: string) =>
	({
		plugin: PLUGIN,
		surface: 'terminal',
		component: 'Pane',
		requestId: id,
		props: { title: id, isFocused: true, bodyColumns: 90, placement: 'inline', scroll: { offset: 0, bodyRows: 10 }, view: {} },
	}) as const

test('helpers: slug, local date and ago', async () => {
	expect(slug('Worktree isolation blocked a plain `git log`!')).toBe('worktree-isolation-blocked-a-plain-git-log')
	expect(slug('   ')).toBe('pain')
	expect(localDate(NOON)).toBe('2026-10-07')
	expect(ago(5_000)).toBe('5s')
	expect(ago(125_000)).toBe('2m')
	expect(ago(3_700_000)).toBe('1h 1m')
})

test('/pain with text appends an entry with the context pre-filled', async ($, on) => {
	world(on)
	const file = painFile(on, null)
	on('tool.call', { tool: 'Bash' }, async () => ({ result: { stdout: '', stderr: 'fatal: boom', interrupted: false }, isError: true }))
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.tool.call({ tool: 'Bash', command: 'git log' })
	const first = await $.command.run({ ...RUN, command: 'pain', args: 'worktree isolation blocked a plain git log' })
	expect(first.text).toBe('logged worktree-isolation-blocked-a-plain-git-log')
	expect(file.writes[0]).toBe('/home/j/.claude/library/state/cc-pain-points.json')
	const entries = JSON.parse(file.text ?? '') as Record<string, unknown>[]
	expect(entries).toHaveLength(1)
	expect(entries[0]).toMatchObject({
		id: 'worktree-isolation-blocked-a-plain-git-log',
		logged: '2026-10-07',
		resolvedIn: null,
		resolvedNoted: null,
	})
	expect(String(entries[0]?.sourceSession)).toMatch(/^app · feat\/search · last failed: Bash: /)
	const again = await $.command.run({ ...RUN, command: 'pain', args: 'Worktree isolation blocked a plain git log' })
	expect(again.text).toBe('already logged as worktree-isolation-blocked-a-plain-git-log')
	expect(file.writes).toHaveLength(1)
})

test('a pain file that will not parse is never overwritten', async ($, on) => {
	world(on)
	const file = painFile(on, '[{"id": "kept"},')
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	const run = await $.command.run({ ...RUN, command: 'pain', args: 'something else' })
	expect(run.text).toBe('cc-pain-points.json will not parse; nothing written. fix the file first.')
	expect(file.writes).toHaveLength(0)
	expect(file.text).toBe('[{"id": "kept"},')
})

test('/pain alone opens a pane whose input logs and closes it', async ($, on) => {
	const store = world(on)
	const file = painFile(on, '[{"id":"thing","description":"thing","logged":"2026-10-01","sourceSession":"","resolvedIn":null,"resolvedNoted":null}]')
	const toasts: string[] = []
	on('ui.toast', async ($, e, next) => {
		toasts.push(e.text)
		return next(e)
	})
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	expect(await $.command.run({ ...RUN, command: 'pain', args: '' })).toEqual({})
	expect(store.panes.open).toEqual(['pain'])
	const ui = await $.ui.mount(PANE('pain'))
	expect((await ui.find({ type: 'Text', text: /nothing has failed yet/ }))?.text).toMatch(/app · feat\/search/)
	expect((await ui.find({ type: 'Input', key: 'pain-text' }))?.props.value).toBeUndefined()
	await ui.input({ key: 'pain-text', text: 'thing' })
	expect(toasts).toEqual(['already logged as thing'])
	// a refusal keeps the box open with what was typed
	expect(store.panes.open).toEqual(['pain'])
	await ui.input({ key: 'pain-text', text: 'the status line ate my prompt' })
	expect(toasts[1]).toBe('logged the-status-line-ate-my-prompt')
	expect(store.panes.open).toEqual([])
	expect(JSON.parse(file.text ?? '')).toHaveLength(2)
})

test('session start prunes a stale row; the fleet pane lists the rest and messages a picked session', async ($, on) => {
	const row = (id: string, repo: string, branch: string, at: number, isWorking = false) => ({
		id,
		cwd: `/code/${repo}`,
		repo,
		branch,
		isWorking,
		lastTool: 'Read',
		lastToolAt: at,
		startedAt: at - 60_000,
		at,
	})
	const store = world(on, {
		'fleet:s2': row('s2', 'chirpdb', 'fix/export', NOON - 30_000, true),
		'fleet:s3': row('s3', 'wyrd', 'main', NOON - 2 * 60_000),
		'fleet:dead': row('dead', 'old', 'x', NOON - 11 * 60_000),
		other: 'untouched',
	})
	const sent: { to: string; text: string }[] = []
	on('session.send', async ($, e) => {
		sent.push({ to: e.to, text: e.text })
		return { isDelivered: true }
	})
	const toasts: string[] = []
	on('ui.toast', async ($, e, next) => {
		toasts.push(e.text)
		return next(e)
	})
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	const ui = await $.ui.mount(PANE('fleet'))
	const rows = await ui.findAll({ type: 'Button' })
	expect(rows.map(r => r.props.label)).toEqual([
		'◀ app feat/search · idle 0s',
		'  chirpdb fix/export · working · Read',
		'  wyrd main · quiet 2m · Read',
	])
	expect(store.deletes).toEqual(['fleet:dead'])
	expect(store.map.get('other')).toBe('untouched')
	expect(await ui.find({ type: 'Input' })).toBeUndefined()
	await ui.press({ key: 'row-s2' })
	expect((await ui.find({ type: 'Input', key: 'fleet-msg' }))?.props.label).toBe('to chirpdb/fix/export')
	await ui.input({ key: 'fleet-msg', text: 'leave the main checkout alone' })
	expect(sent).toEqual([{ to: expect.stringContaining('s2'), text: 'leave the main checkout alone' }])
	expect(toasts).toEqual(['sent to chirpdb/fix/export'])
})

test('enabled false registers nothing: no heartbeat, no store writes', { options: { enabled: false } }, async ($, on) => {
	const store = world(on)
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	expect(store.sets).toEqual([])
	expect(store.map.size).toBe(0)
})

test('/fleet opens the pane and runs again to close it', async ($, on) => {
	const store = world(on)
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.command.run({ ...RUN, command: 'fleet', args: '' })
	expect(store.panes.open).toEqual(['fleet'])
	await $.command.run({ ...RUN, command: 'fleet', args: '' })
	expect(store.panes.open).toEqual([])
})

test('the heartbeat writes this session and session.end removes it', async ($, on) => {
	const store = world(on)
	on('prompt.submit', async () => ({ drop: 'not now' }))
	on('session.end', async ($, e) => ({ sessionId: e.sessionId }))
	on('tool.call', { tool: 'Read' }, async () => ({ result: { type: 'text', file: { filePath: 'x', content: '', numLines: 0, startLine: 1, totalLines: 0 } } }))
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	expect(store.sets[0]).toMatchObject({ key: 'fleet:s1', value: { id: 's1', repo: 'app', branch: 'feat/search', isWorking: false } })
	// a dropped prompt is not a turn
	await $.prompt.submit({ text: 'go', wait: false, origin: { kind: 'composer' } })
	expect(store.map.get('fleet:s1')).toMatchObject({ isWorking: false })
	await $.turn.start({ text: 'go', turnId: 't1' })
	expect(store.map.get('fleet:s1')).toMatchObject({ isWorking: true })
	// a tool event beats once the gap since the last beat has passed, with the tool in the row
	await store.clock.advance(6_000)
	await $.tool.call({ tool: 'Read', file_path: 'x' })
	expect(store.map.get('fleet:s1')).toMatchObject({ lastTool: 'Read' })
	// /clear ends the session under one id and the next beat writes under the new one
	await $.session.end({ reason: 'clear', sessionId: 's1', resume: { id: 's1' } })
	expect(store.deletes).toEqual(['fleet:s1'])
	ids.current = 's2'
	await $.turn.complete({ answer: '', durationMs: 10, isAborted: false, turnId: 't1', reason: 'answer' })
	expect(store.map.has('fleet:s1')).toBe(false)
	expect(store.map.get('fleet:s2')).toMatchObject({ id: 's2', isWorking: false, startedAt: NOON + 6_000 })
})
