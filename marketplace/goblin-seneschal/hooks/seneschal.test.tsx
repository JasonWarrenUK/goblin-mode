import { expect, mock, test } from 'claude-code/testing'

import { DEFAULT_GRIEVANCES, ago, entryKey, expandHome, localDate, slug } from './register'

const PLUGIN = 'goblin-seneschal'
const NOON = new Date(2026, 9, 7, 12, 0).getTime()
const GRIEVANCES = '/home/j/.claude/library/state/grievances.json'
const OLD_FILE = '/home/j/.claude/library/state/cc-pain-points.json'

type On = Parameters<typeof mock.clock>[0]

/** The world beneath the plugin: a clock, a store, a home, a session and a git that answers one branch. */
const ids = { current: 's1' }

/** The files the test holds, by path; a path not in the map is a missing file. Writes are recorded in order. */
const disk = (
	on: On,
	initial: Readonly<Record<string, string>> = {},
	failWrite: string | null = null,
	beforeRead: ((path: string, files: Map<string, string>) => void) | null = null,
) => {
	const files = new Map<string, string>(Object.entries(initial))
	const writes: string[] = []
	on('fs.exists', async ($, e) => ({ value: files.has(e.path) }))
	on('fs.read', async ($, e) => {
		beforeRead?.(e.path, files)
		const text = files.get(e.path)
		if (text === undefined) throw new Error('ENOENT')
		return { value: text }
	})
	on('fs.write', async ($, e) => {
		if (e.path === failWrite) throw new Error('EACCES: permission denied')
		writes.push(e.path)
		files.set(e.path, e.text)
		return { value: undefined }
	})
	return { files, writes, text: (path = GRIEVANCES) => files.get(path) ?? null }
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

/** Collect the toasts the plugin raises. */
const toastsOf = (on: On): string[] => {
	const toasts: string[] = []
	on('ui.toast', async ($, e, next) => {
		toasts.push(e.text)
		return next(e)
	})
	return toasts
}

const RUN = { origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 100 } } as const
const START = { cwd: '/code/app', surface: 'terminal', isInteractive: true } as const

const PANE = (id: string) =>
	({
		plugin: PLUGIN,
		surface: 'terminal',
		component: 'Pane',
		requestId: id,
		props: { title: id, isFocused: true, bodyColumns: 90, placement: 'inline', scroll: { offset: 0, bodyRows: 10 }, view: {} },
	}) as const

/** An old-format file as the plugin wrote it before 1.0.0: one open entry, one resolved, one with an odd source. */
const OLD_ENTRIES = [
	{ id: 'status-line-ate-my-prompt', description: 'the status line ate my prompt', logged: '2026-10-01', sourceSession: 'app · main', resolvedIn: null, resolvedNoted: null },
	{ id: 'worktree-blocked-git-log', description: 'worktree isolation blocked a plain git log', logged: '2026-10-02', sourceSession: '', resolvedIn: '2.1.300', resolvedNoted: '2026-10-20' },
	{ id: 'pain', description: '?', logged: '2026-10-03', sourceSession: 'wyrd · x · last failed: Bash: boom', resolvedIn: null, resolvedNoted: null },
]
const OLD_TEXT = JSON.stringify(OLD_ENTRIES, null, '\t') + '\n'

test('helpers: slug, home expansion, local date and ago', async () => {
	expect(slug('Worktree isolation blocked a plain `git log`!')).toBe('worktree-isolation-blocked-a-plain-git-log')
	expect(slug('   ')).toBe('grievance')
	expect(expandHome('~/.claude/x.json', '/home/j')).toBe('/home/j/.claude/x.json')
	expect(expandHome('/elsewhere/x.json', '/home/j')).toBe('/elsewhere/x.json')
	expect(expandHome('~', '/home/j')).toBe('/home/j')
	expect(localDate(NOON)).toBe('2026-10-07')
	expect(ago(5_000)).toBe('5s')
	expect(ago(125_000)).toBe('2m')
	expect(ago(3_700_000)).toBe('1h 1m')
})

test('the old file is carried over at session start: every entry and every field, byte for byte, the old file left alone', async ($, on) => {
	world(on)
	const files = disk(on, { [OLD_FILE]: OLD_TEXT })
	const toasts = toastsOf(on)
	await $.session.start(START)
	expect(files.text()).toBe(OLD_TEXT)
	const carried = JSON.parse(files.text() ?? '') as Record<string, unknown>[]
	expect(carried).toEqual(OLD_ENTRIES)
	for (const [i, entry] of carried.entries()) {
		expect(Object.keys(entry)).toEqual(['id', 'description', 'logged', 'sourceSession', 'resolvedIn', 'resolvedNoted'])
		expect(entry).toEqual(OLD_ENTRIES[i])
	}
	expect(files.text(OLD_FILE)).toBe(OLD_TEXT)
	expect(files.writes).toEqual([GRIEVANCES])
	expect(toasts).toEqual(['3 grievances carried over from cc-pain-points.json; delete it once no session still runs goblin-util.'])
	// a second session finds the grievances file there and moves nothing
	await $.session.start(START)
	expect(files.writes).toEqual([GRIEVANCES])
})

test('a grievances file another session writes between the check and the copy is never overwritten: its entries keep their place and the old ones follow', async ($, on) => {
	world(on)
	const theirs = { id: 'theirs', description: 'theirs', logged: '2026-11-19', sourceSession: '', resolvedIn: null, resolvedNoted: null }
	// the old file is read before the grievances file is looked at; another session writes one in that gap
	const files = disk(on, { [OLD_FILE]: OLD_TEXT }, null, (path, held) => {
		if (path === OLD_FILE && !held.has(GRIEVANCES)) held.set(GRIEVANCES, listed([theirs]))
	})
	await $.session.start(START)
	expect(JSON.parse(files.text() ?? '')).toEqual([theirs, ...OLD_ENTRIES])
})

test('a grievances file another session changes between the merge reading it and writing it is left as that session wrote it', async ($, on) => {
	world(on)
	const late = listed([MINE, LATE])
	let reads = 0
	const files = disk(on, { [OLD_FILE]: OLD_TEXT, [GRIEVANCES]: listed([MINE]) }, null, (path, held) => {
		// the merge's second read, straight before its write, finds the other session's text
		if (path === GRIEVANCES && ++reads === 2) held.set(GRIEVANCES, late)
	})
	await $.session.start(START)
	expect(files.text()).toBe(late)
	expect(files.writes).toEqual([])
})

const MINE = { id: 'mine', description: 'mine', logged: '2026-11-18', sourceSession: '', resolvedIn: null, resolvedNoted: null }
/** An entry an older session logs to the old file after the first carry-over. */
const LATE = { id: 'logged-late', description: 'logged late', logged: '2026-11-19', sourceSession: 'app · main', resolvedIn: null, resolvedNoted: null }
const listed = (entries: readonly unknown[]): string => JSON.stringify(entries, null, '\t') + '\n'

test('both files present: the old entries the grievances file lacks are appended after its own, which keep their place and fields', async ($, on) => {
	world(on)
	const files = disk(on, { [OLD_FILE]: OLD_TEXT, [GRIEVANCES]: listed([MINE]) })
	const toasts = toastsOf(on)
	await $.session.start(START)
	expect(JSON.parse(files.text() ?? '')).toEqual([MINE, ...OLD_ENTRIES])
	expect(files.text(OLD_FILE)).toBe(OLD_TEXT)
	expect(toasts).toEqual(['3 grievances carried over from cc-pain-points.json; delete it once no session still runs goblin-util.'])
	// safe to run again: everything is there, so the next session writes nothing and says nothing
	await $.session.start(START)
	expect(files.writes).toEqual([GRIEVANCES])
	expect(toasts).toHaveLength(1)
})

test('an entry an older session logs to the old file after the first copy is carried at the next session start', async ($, on) => {
	world(on)
	const files = disk(on, { [OLD_FILE]: OLD_TEXT })
	const toasts = toastsOf(on)
	await $.session.start(START)
	expect(files.text()).toBe(OLD_TEXT)
	// a session still on the old plugin appends to the old file, and this session logs one of its own
	files.files.set(OLD_FILE, listed([...OLD_ENTRIES, LATE]))
	await $.command.run({ ...RUN, command: 'log-grievance', args: 'the band flickered' })
	const ids = (JSON.parse(files.text() ?? '') as { id: string }[]).map(e => e.id)
	expect(ids).toEqual([...OLD_ENTRIES.map(e => e.id), 'logged-late', 'the-band-flickered'])
	await $.session.start(START)
	expect(toasts).toEqual(['3 grievances carried over from cc-pain-points.json; delete it once no session still runs goblin-util.'])
	expect((JSON.parse(files.text() ?? '') as unknown[]).length).toBe(5)
})

test('a grievance deleted from the grievances file after it was carried stays deleted, while a later old entry still arrives', async ($, on) => {
	world(on)
	const files = disk(on, { [OLD_FILE]: OLD_TEXT })
	await $.session.start(START)
	// the person deletes the first carried entry by hand
	files.files.set(GRIEVANCES, listed(OLD_ENTRIES.slice(1)))
	await $.session.start(START)
	expect(JSON.parse(files.text() ?? '')).toEqual(OLD_ENTRIES.slice(1))
	files.files.set(OLD_FILE, listed([...OLD_ENTRIES, LATE]))
	await $.session.start(START)
	expect(JSON.parse(files.text() ?? '')).toEqual([...OLD_ENTRIES.slice(1), LATE])
})

test('an old entry whose id clashes with a different grievance arrives under a suffixed id, and only once', async ($, on) => {
	// past the first start after 1.0.0 (a record exists), where a shared id counts as the copy
	world(on, { carriedInto: GRIEVANCES, carriedKeys: [] })
	// both plugins slug the first 48 characters, so two different grievances can share an id
	const mine = { ...MINE, id: 'the-status-line-ate-my-prompt', description: 'the status line ate my prompt when I resized the window' }
	const theirs = { ...LATE, id: 'the-status-line-ate-my-prompt', description: 'the status line ate my prompt when I resized the pane' }
	const files = disk(on, { [OLD_FILE]: listed([theirs]), [GRIEVANCES]: listed([mine]) })
	await $.session.start(START)
	expect(JSON.parse(files.text() ?? '')).toEqual([mine, { ...theirs, id: 'the-status-line-ate-my-prompt-2' }])
	await $.session.start(START)
	expect(files.writes).toEqual([GRIEVANCES])
})

test('the first start after 1.0.0, with no record yet, takes an id both files hold as carried even when its description was edited', async ($, on) => {
	world(on)
	const edited = { ...OLD_ENTRIES[0], description: 'the status line ate my prompt, with the typo fixed' }
	const files = disk(on, { [OLD_FILE]: OLD_TEXT, [GRIEVANCES]: listed([edited, OLD_ENTRIES[1], OLD_ENTRIES[2]]) })
	await $.session.start(START)
	expect(files.writes).toEqual([])
	expect(JSON.parse(files.text() ?? '')).toEqual([edited, OLD_ENTRIES[1], OLD_ENTRIES[2]])
})

test('an entry already carried under a suffixed id is not carried again when the record of it was never written', async ($, on) => {
	// the session that carried it ended between writing the file and writing the record
	world(on, { carriedInto: GRIEVANCES, carriedKeys: [] })
	const mine = { ...MINE, id: 'the-status-line-ate-my-prompt', description: 'the status line ate my prompt when I resized the window' }
	const theirs = { ...LATE, id: 'the-status-line-ate-my-prompt', description: 'the status line ate my prompt when I resized the pane' }
	const files = disk(on, { [OLD_FILE]: listed([theirs]), [GRIEVANCES]: listed([mine, { ...theirs, id: 'the-status-line-ate-my-prompt-2' }]) })
	await $.session.start(START)
	expect(files.writes).toEqual([])
})

test('the merge keeps what it does not understand in the grievances file', async ($, on) => {
	world(on)
	const files = disk(on, { [OLD_FILE]: listed([LATE]), [GRIEVANCES]: listed([MINE, 'a stray note', 3, null]) })
	await $.session.start(START)
	expect(JSON.parse(files.text() ?? '')).toEqual([MINE, 'a stray note', 3, null, LATE])
})

test('after grievances_file has moved, an unreadable grievances file is never promised a fresh carry-over', { options: { grievances_file: '~/notes/grievances.json' } }, async ($, on) => {
	world(on, { carriedInto: GRIEVANCES, carriedKeys: [] })
	const files = disk(on, { [OLD_FILE]: OLD_TEXT, '/home/j/notes/grievances.json': '[{"id": "half' })
	const run = await $.command.run({ ...RUN, command: 'log-grievance', args: 'something bit' })
	expect(run.text).toBe('grievances.json will not parse; nothing written. fix the file first.')
	expect(files.writes).toEqual([])
})

test('an id the grievances file already holds is never carried twice, even when the old copy differs', async ($, on) => {
	world(on)
	const resolved = { ...OLD_ENTRIES[0], resolvedIn: '2.1.320', resolvedNoted: '2026-11-19' }
	const files = disk(on, { [OLD_FILE]: OLD_TEXT, [GRIEVANCES]: listed([resolved, OLD_ENTRIES[1], OLD_ENTRIES[2]]) })
	await $.session.start(START)
	expect(files.writes).toEqual([])
	expect(JSON.parse(files.text() ?? '')).toEqual([resolved, OLD_ENTRIES[1], OLD_ENTRIES[2]])
})

test('a changed grievances_file never takes the old snapshot again, yet an entry logged to the old file since arrives there', { options: { grievances_file: '~/notes/grievances.json' } }, async ($, on) => {
	const moved = '/home/j/notes/grievances.json'
	// the earlier path got the old file at the first carry-over, which recorded every entry it carried; the option has since moved
	const store = world(on, { carriedInto: GRIEVANCES, carriedKeys: OLD_ENTRIES.map(entryKey) })
	const files = disk(on, { [OLD_FILE]: listed([...OLD_ENTRIES, LATE]), [GRIEVANCES]: OLD_TEXT })
	const toasts = toastsOf(on)
	await $.session.start(START)
	expect(JSON.parse(files.text(moved) ?? '')).toEqual([LATE])
	expect(toasts).toEqual(['1 grievance carried over from cc-pain-points.json; delete it once no session still runs goblin-util.'])
	const run = await $.command.run({ ...RUN, command: 'log-grievance', args: 'something bit' })
	expect(run.text).toBe('logged something-bit')
	expect((JSON.parse(files.text(moved) ?? '') as { id: string }[]).map(e => e.id)).toEqual(['logged-late', 'something-bit'])
	expect(files.text()).toBe(OLD_TEXT)
	expect(store.map.get('carriedInto')).toBe(GRIEVANCES)
	// nothing new in the old file: the next start writes nothing
	await $.session.start(START)
	expect(toasts).toHaveLength(1)
})

test('a changed grievances_file with nothing new in the old file starts empty', { options: { grievances_file: '~/notes/grievances.json' } }, async ($, on) => {
	world(on, { carriedInto: GRIEVANCES, carriedKeys: OLD_ENTRIES.map(entryKey) })
	const files = disk(on, { [OLD_FILE]: OLD_TEXT, [GRIEVANCES]: OLD_TEXT })
	await $.session.start(START)
	expect(files.writes).toEqual([])
	await $.command.run({ ...RUN, command: 'log-grievance', args: 'something bit' })
	expect((JSON.parse(files.text('/home/j/notes/grievances.json') ?? '') as { id: string }[]).map(e => e.id)).toEqual(['something-bit'])
})

test('the first carry-over records the path it wrote', async ($, on) => {
	const store = world(on)
	disk(on, { [OLD_FILE]: OLD_TEXT })
	await $.session.start(START)
	expect(store.map.get('carriedInto')).toBe(GRIEVANCES)
})

test('an old file that will not parse beside a grievances file is named, and logging carries on into the grievances file', async ($, on) => {
	world(on)
	const files = disk(on, { [OLD_FILE]: '[{"id": "kept"},', [GRIEVANCES]: listed([MINE]) })
	const toasts = toastsOf(on)
	await $.session.start(START)
	expect(files.writes).toEqual([])
	expect(toasts).toEqual(['cc-pain-points.json will not parse; fix it and its grievances carry over at the next session.'])
	const run = await $.command.run({ ...RUN, command: 'log-grievance', args: 'something bit' })
	expect(run.text).toBe('logged something-bit')
	expect((JSON.parse(files.text() ?? '') as { id: string }[]).map(e => e.id)).toEqual(['mine', 'something-bit'])
	expect(files.text(OLD_FILE)).toBe('[{"id": "kept"},')
})

test('a grievances file that will not parse beside a readable old file says how to carry the old one over again', async ($, on) => {
	world(on)
	const files = disk(on, { [OLD_FILE]: OLD_TEXT, [GRIEVANCES]: '[{"id": "status-line' })
	await $.session.start(START)
	const run = await $.command.run({ ...RUN, command: 'log-grievance', args: 'something bit' })
	expect(run.text).toBe(
		'grievances.json will not parse; nothing written. fix it, or delete it and log again to carry cc-pain-points.json over afresh (anything logged since the first carry-over goes with it).',
	)
	expect(files.writes).toEqual([])
})

for (const typed of ['state/grievances.json', '$HOME/grievances.json', '~someone/grievances.json', '~']) {
	test(`a grievances_file of ${typed} is refused with a toast and the default used`, { options: { grievances_file: typed } }, async ($, on) => {
		world(on)
		const files = disk(on)
		const toasts = toastsOf(on)
		await $.session.start(START)
		expect(toasts).toEqual([`grievances_file ${typed} is not an absolute path or one under ~/; using ${DEFAULT_GRIEVANCES}.`])
		await $.command.run({ ...RUN, command: 'log-grievance', args: 'something bit' })
		expect(files.writes).toEqual([GRIEVANCES])
	})
}

test('an old file that will not parse stays where it is and is named at session start; logging waits until it is fixed', async ($, on) => {
	world(on)
	const files = disk(on, { [OLD_FILE]: '[{"id": "kept"},' })
	const toasts = toastsOf(on)
	await $.session.start(START)
	expect(files.writes).toEqual([])
	expect(files.text(OLD_FILE)).toBe('[{"id": "kept"},')
	expect(toasts).toEqual(['cc-pain-points.json will not parse; fix it and its grievances carry over at the next session.'])
	// logging now would create grievances.json and strand the old entries for good
	const run = await $.command.run({ ...RUN, command: 'log-grievance', args: 'something bit' })
	expect(run.text).toBe('cc-pain-points.json will not parse; fix it first so its grievances carry over. nothing written.')
	expect(files.writes).toEqual([])
	// once fixed, the next grievance carries it over and appends after it
	files.files.set(OLD_FILE, '[{"id":"kept","description":"kept","logged":"2026-10-01","sourceSession":"","resolvedIn":null,"resolvedNoted":null}]\n')
	const again = await $.command.run({ ...RUN, command: 'log-grievance', args: 'something bit' })
	expect(again.text).toBe('logged something-bit')
	expect((JSON.parse(files.text() ?? '') as { id: string }[]).map(e => e.id)).toEqual(['kept', 'something-bit'])
})

test('one entry carried over reads in the singular', async ($, on) => {
	world(on)
	disk(on, { [OLD_FILE]: JSON.stringify([OLD_ENTRIES[0]]) })
	const toasts = toastsOf(on)
	await $.session.start(START)
	expect(toasts).toEqual(['1 grievance carried over from cc-pain-points.json; delete it once no session still runs goblin-util.'])
})

test('a carry-over that cannot write says so, never that HOME is unset', async ($, on) => {
	world(on)
	const files = disk(on, { [OLD_FILE]: OLD_TEXT }, GRIEVANCES)
	const run = await $.command.run({ ...RUN, command: 'log-grievance', args: 'something bit' })
	// the runner reports a throwing hook in its own words; what matters is that the write's failure is named
	expect(run.text).toMatch(/^could not carry over cc-pain-points\.json: .+; nothing written\.$/)
	expect(run.text).not.toMatch(/HOME/)
	expect(files.text(OLD_FILE)).toBe(OLD_TEXT)
})

test('/log-grievance with text carries the old file over first, then appends after its entries', async ($, on) => {
	world(on)
	const files = disk(on, { [OLD_FILE]: OLD_TEXT })
	const run = await $.command.run({ ...RUN, command: 'log-grievance', args: 'the band flickered' })
	expect(run.text).toBe('logged the-band-flickered')
	const entries = JSON.parse(files.text() ?? '') as Record<string, unknown>[]
	expect(entries.slice(0, 3)).toEqual(OLD_ENTRIES)
	expect(entries[3]).toMatchObject({ id: 'the-band-flickered', resolvedIn: null })
})

test('/log-grievance with text appends an entry with the context pre-filled', async ($, on) => {
	world(on)
	const files = disk(on)
	on('tool.call', { tool: 'Bash' }, async () => ({ result: { stdout: '', stderr: 'fatal: boom', interrupted: false }, isError: true }))
	await $.session.start(START)
	await $.tool.call({ tool: 'Bash', command: 'git log' })
	const first = await $.command.run({ ...RUN, command: 'log-grievance', args: 'worktree isolation blocked a plain git log' })
	expect(first.text).toBe('logged worktree-isolation-blocked-a-plain-git-log')
	expect(files.writes[0]).toBe(GRIEVANCES)
	const entries = JSON.parse(files.text() ?? '') as Record<string, unknown>[]
	expect(entries).toHaveLength(1)
	expect(entries[0]).toMatchObject({
		id: 'worktree-isolation-blocked-a-plain-git-log',
		logged: '2026-10-07',
		resolvedIn: null,
		resolvedNoted: null,
	})
	expect(String(entries[0]?.sourceSession)).toMatch(/^app · feat\/search · last failed: Bash: /)
	const again = await $.command.run({ ...RUN, command: 'log-grievance', args: 'Worktree isolation blocked a plain git log' })
	expect(again.text).toBe('already logged as worktree-isolation-blocked-a-plain-git-log')
	expect(files.writes).toHaveLength(1)
})

test('the grievances_file option moves the file, with a leading ~/ set under the home', { options: { grievances_file: '~/notes/grievances.json' } }, async ($, on) => {
	world(on)
	const files = disk(on)
	await $.session.start(START)
	await $.command.run({ ...RUN, command: 'log-grievance', args: 'something bit' })
	expect(files.writes).toEqual(['/home/j/notes/grievances.json'])
})

test('a grievances file that will not parse is never overwritten', async ($, on) => {
	world(on)
	const files = disk(on, { [GRIEVANCES]: '[{"id": "kept"},' })
	await $.session.start(START)
	const run = await $.command.run({ ...RUN, command: 'log-grievance', args: 'something else' })
	expect(run.text).toBe('grievances.json will not parse; nothing written. fix the file first.')
	expect(files.writes).toHaveLength(0)
	expect(files.text()).toBe('[{"id": "kept"},')
})

test('/log-grievance alone opens a pane whose input logs and closes it', async ($, on) => {
	const store = world(on)
	const files = disk(on, {
		[GRIEVANCES]: '[{"id":"thing","description":"thing","logged":"2026-10-01","sourceSession":"","resolvedIn":null,"resolvedNoted":null}]',
	})
	const toasts = toastsOf(on)
	await $.session.start(START)
	expect(await $.command.run({ ...RUN, command: 'log-grievance', args: '' })).toEqual({})
	expect(store.panes.open).toEqual(['grievance'])
	const ui = await $.ui.mount(PANE('grievance'))
	expect((await ui.find({ type: 'Text', text: /nothing has failed yet/ }))?.text).toMatch(/app · feat\/search/)
	expect((await ui.find({ type: 'Input', key: 'grievance-text' }))?.props.label).toBe('grievance')
	await ui.input({ key: 'grievance-text', text: 'thing' })
	expect(toasts).toEqual(['already logged as thing'])
	// a refusal keeps the box open with what was typed
	expect(store.panes.open).toEqual(['grievance'])
	await ui.input({ key: 'grievance-text', text: 'the status line ate my prompt' })
	expect(toasts[1]).toBe('logged the-status-line-ate-my-prompt')
	expect(store.panes.open).toEqual([])
	expect(JSON.parse(files.text() ?? '')).toHaveLength(2)
})

test('session start prunes a stale row; the underlings pane lists the rest and messages a picked one', async ($, on) => {
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
		'underling:s2': row('s2', 'chirpdb', 'fix/export', NOON - 30_000, true),
		'underling:s3': row('s3', 'wyrd', 'main', NOON - 2 * 60_000),
		'underling:dead': row('dead', 'old', 'x', NOON - 11 * 60_000),
		other: 'untouched',
	})
	disk(on)
	const sent: { to: string; text: string }[] = []
	on('session.send', async ($, e) => {
		sent.push({ to: e.to, text: e.text })
		return { isDelivered: true }
	})
	const toasts = toastsOf(on)
	await $.session.start(START)
	const ui = await $.ui.mount(PANE('underlings'))
	const rows = await ui.findAll({ type: 'Button' })
	expect(rows.map(r => r.props.label)).toEqual([
		'◀ app feat/search · idle 0s',
		'  chirpdb fix/export · working · Read',
		'  wyrd main · quiet 2m · Read',
	])
	expect(store.deletes).toEqual(['underling:dead'])
	expect(store.map.get('other')).toBe('untouched')
	expect(await ui.find({ type: 'Input' })).toBeUndefined()
	expect((await ui.find({ type: 'Text', text: /a digit picks one/ }))?.text).toBe('you and 2 underlings · a digit picks one · esc closes')
	await ui.press({ key: 'row-s2' })
	expect((await ui.find({ type: 'Input', key: 'underling-msg' }))?.props.label).toBe('to chirpdb/fix/export')
	await ui.input({ key: 'underling-msg', text: 'leave the main checkout alone' })
	expect(sent).toEqual([{ to: expect.stringContaining('s2'), text: 'leave the main checkout alone' }])
	expect(toasts).toEqual(['sent to chirpdb/fix/export'])
})

test('enabled false registers nothing: no heartbeat, no store writes, no carry-over', { options: { enabled: false } }, async ($, on) => {
	const store = world(on)
	const files = disk(on, { [OLD_FILE]: OLD_TEXT })
	await $.session.start(START)
	expect(store.sets).toEqual([])
	expect(store.map.size).toBe(0)
	expect(files.writes).toEqual([])
})

test('/muster-underlings opens the pane and runs again to close it', async ($, on) => {
	const store = world(on)
	disk(on)
	await $.session.start(START)
	await $.command.run({ ...RUN, command: 'muster-underlings', args: '' })
	expect(store.panes.open).toEqual(['underlings'])
	// alone, the footer counts no underlings, never "1 underlings"
	const ui = await $.ui.mount(PANE('underlings'))
	expect((await ui.find({ type: 'Text', text: /a digit picks one/ }))?.text).toBe('you and no underlings · a digit picks one · esc closes')
	await ui.unmount()
	await $.command.run({ ...RUN, command: 'muster-underlings', args: '' })
	expect(store.panes.open).toEqual([])
})

test('the heartbeat writes this session and session.end removes it', async ($, on) => {
	const store = world(on)
	disk(on)
	on('prompt.submit', async () => ({ drop: 'not now' }))
	on('session.end', async ($, e) => ({ sessionId: e.sessionId }))
	on('tool.call', { tool: 'Read' }, async () => ({ result: { type: 'text', file: { filePath: 'x', content: '', numLines: 0, startLine: 1, totalLines: 0 } } }))
	await $.session.start(START)
	expect(store.sets[0]).toMatchObject({ key: 'underling:s1', value: { id: 's1', repo: 'app', branch: 'feat/search', isWorking: false } })
	// a dropped prompt is not a turn
	await $.prompt.submit({ text: 'go', wait: false, origin: { kind: 'composer' } })
	expect(store.map.get('underling:s1')).toMatchObject({ isWorking: false })
	await $.turn.start({ text: 'go', turnId: 't1' })
	expect(store.map.get('underling:s1')).toMatchObject({ isWorking: true })
	// a tool event beats once the gap since the last beat has passed, with the tool in the row
	await store.clock.advance(6_000)
	await $.tool.call({ tool: 'Read', file_path: 'x' })
	expect(store.map.get('underling:s1')).toMatchObject({ lastTool: 'Read' })
	// /clear ends the session under one id and the next beat writes under the new one
	await $.session.end({ reason: 'clear', sessionId: 's1', resume: { id: 's1' } })
	expect(store.deletes).toEqual(['underling:s1'])
	ids.current = 's2'
	await $.turn.complete({ answer: '', durationMs: 10, isAborted: false, turnId: 't1', reason: 'answer' })
	expect(store.map.has('underling:s1')).toBe(false)
	expect(store.map.get('underling:s2')).toMatchObject({ id: 's2', isWorking: false, startedAt: NOON + 6_000 })
})
