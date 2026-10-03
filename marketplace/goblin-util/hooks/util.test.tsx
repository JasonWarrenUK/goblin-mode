import { expect, mock, test } from 'claude-code/testing'

import { ago, localDate, slug } from './register'

const PLUGIN = 'goblin-util'
const NOON = new Date(2026, 9, 7, 12, 0).getTime()

type On = Parameters<typeof mock.clock>[0]

/** The world beneath the plugin: a clock, a store, a home, a session and a git that answers one branch. */
const world = (on: On, entries: Readonly<Record<string, unknown>> = {}) => {
	// A store of the test's own, so what the plugin wrote can be read back directly.
	const map = new Map<string, unknown>(Object.entries(entries))
	const store = { map, sets: [] as { key: string; value: unknown }[], deletes: [] as string[] }
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
	mock.clock(on, { now: NOON })
	mock.env(on, { HOME: '/home/j' })
	on('session.start', async ($, e) => ({ cwd: e.cwd }))
	on('session.id', async () => ({ value: 's1' }))
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
	let stored = '[]'
	const writes: string[] = []
	on('fs.read', async () => ({ value: stored }))
	on('fs.write', async ($, e) => {
		writes.push(e.path)
		stored = e.text
		return { value: undefined }
	})
	on('tool.call', { tool: 'Bash' }, async () => ({ result: { stdout: '', stderr: 'fatal: boom', interrupted: false }, isError: true }))
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	await $.tool.call({ tool: 'Bash', command: 'git log' })
	const first = await $.command.run({ ...RUN, command: 'pain', args: 'worktree isolation blocked a plain git log' })
	expect(first.text).toBe('logged worktree-isolation-blocked-a-plain-git-log')
	expect(writes[0]).toBe('/home/j/.claude/library/state/cc-pain-points.json')
	const entries = JSON.parse(stored) as Record<string, unknown>[]
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
	expect(writes).toHaveLength(1)
})

test('/pain alone opens a pane whose input logs and closes it', async ($, on) => {
	world(on)
	let stored = '[{"id":"thing","description":"thing","logged":"2026-10-01","sourceSession":"","resolvedIn":null,"resolvedNoted":null}]'
	on('fs.read', async () => ({ value: stored }))
	on('fs.write', async ($, e) => {
		stored = e.text
		return { value: undefined }
	})
	const opened: string[] = []
	const closed: string[] = []
	const toasts: string[] = []
	on('ui.open', async ($, e) => {
		opened.push(e.id)
		return { value: { isPlaced: true } }
	})
	on('ui.close', async ($, e) => {
		closed.push(e.id)
		return { value: undefined }
	})
	on('ui.toast', async ($, e, next) => {
		toasts.push(e.text)
		return next(e)
	})
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	expect(await $.command.run({ ...RUN, command: 'pain', args: '' })).toEqual({})
	expect(opened).toEqual(['pain'])
	const ui = await $.ui.mount(PANE('pain'))
	expect((await ui.find({ type: 'Text', text: /nothing has failed yet/ }))?.text).toMatch(/app · feat\/search/)
	await ui.input({ key: 'pain-text', text: 'thing' })
	expect(toasts).toEqual(['already logged as thing'])
	await ui.input({ key: 'pain-text', text: 'the status line ate my prompt' })
	expect(toasts[1]).toBe('logged the-status-line-ate-my-prompt')
	expect(closed).toEqual(['pain', 'pain'])
	expect(JSON.parse(stored)).toHaveLength(2)
})

test('the fleet pane lists live rows, drops stale ones and messages a picked session', async ($, on) => {
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
	expect(sent).toEqual([{ to: expect.anything(), text: 'leave the main checkout alone' }])
	expect(toasts).toEqual(['sent to chirpdb/fix/export'])
})

test('the heartbeat writes this session and session.end removes it', async ($, on) => {
	const store = world(on)
	on('prompt.submit', async ($, e) => ({ text: e.text }))
	on('session.end', async ($, e) => ({ sessionId: e.sessionId }))
	await $.session.start({ cwd: '/code/app', surface: 'terminal', isInteractive: true })
	expect(store.sets[0]).toMatchObject({ key: 'fleet:s1', value: { id: 's1', repo: 'app', branch: 'feat/search', isWorking: false } })
	await $.prompt.submit({ text: 'go', wait: false, origin: { kind: 'composer' } })
	expect(store.sets[store.sets.length - 1]).toMatchObject({ key: 'fleet:s1', value: { isWorking: true } })
	await $.session.end({ reason: 'prompt_input_exit', sessionId: 's1', resume: { id: 's1' } })
	expect(store.deletes).toEqual(['fleet:s1'])
})
