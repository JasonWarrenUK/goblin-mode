// goblin-seneschal: two mods for the machine. `/log-grievance` logs a
// grievance with Claude Code itself into the grievances file without a turn,
// the context pre-filled from the last failed tool call. `/muster-underlings`
// shows every session on the machine (an underling) from a shared heartbeat
// in $.store and sends one a line. Both are immediate commands, so they work
// while Claude is busy.

import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Heartbeat, LastError, Self } from '../types'

const GRIEVANCE_PANE = 'grievance'
const MUSTER_PANE = 'underlings'
const UNDERLING_PREFIX = 'underling:'
/** The least time between two heartbeats written for tool events. */
const BEAT_GAP_MS = 5_000
/** Where grievances are kept unless the `grievances_file` option says otherwise. */
export const DEFAULT_GRIEVANCES = '~/.claude/library/state/grievances.json'
/** Where this plugin kept them under its old name, before 1.0.0. */
const OLD_GRIEVANCES = '~/.claude/library/state/cc-pain-points.json'

const selected = atom({ plugin: 'goblin-seneschal', key: 'selected' } as const, null as string | null)
const lastError = atom({ plugin: 'goblin-seneschal', key: 'lastError' } as const, null as LastError | null)
const branch = atom({ plugin: 'goblin-seneschal', key: 'branch' } as const, '')
const repoName = atom({ plugin: 'goblin-seneschal', key: 'repoName' } as const, '')
const self = atom({ plugin: 'goblin-seneschal', key: 'self' } as const, {
	sessionId: '',
	startedAt: 0,
	isWorking: false,
	lastTool: '',
	lastToolAt: 0,
	beatAt: 0,
} as Self)

// Module-level because the validator holds `$` to top-level functions; set
// by `register` from the options. `cwd` is read only by the heartbeat, never
// drawn.
let heartbeatMs = 15_000
let staleMs = 10 * 60_000
let cwd = ''
let grievancesSetting = DEFAULT_GRIEVANCES

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v)

const basename = (path: string): string => path.replace(/[\\/]+$/, '').split(/[\\/]/).pop() ?? path

/** A kebab-case id from a description, as the grievances schema wants. */
export const slug = (text: string): string =>
	text
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-+|-+$/g, '')
		.slice(0, 48)
		.replace(/-+$/, '') || 'grievance'

/** A configured path with a leading `~/` set under the home, as a shell would. */
export const expandHome = (path: string, home: string): string => (path === '~' ? home : path.startsWith('~/') ? `${home}/${path.slice(2)}` : path)

/** The local calendar date, as the skill writes `logged`. */
export const localDate = (ms: number): string => {
	const d = new Date(ms)
	const pad = (n: number) => String(n).padStart(2, '0')
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export const ago = (ms: number): string => {
	const s = Math.max(0, Math.round(ms / 1000))
	if (s < 60) return `${s}s`
	const m = Math.floor(s / 60)
	if (m < 60) return `${m}m`
	return `${Math.floor(m / 60)}h ${m % 60}m`
}

/** The grievances file and the old file it replaces, both with the home set in. */
const grievancePaths = async ($: EngineInterface): Promise<{ grievances: string; oldFile: string }> => {
	const home = await $.env.get('HOME')
	if (!home) throw new Error('HOME is not set')
	return { grievances: expandHome(grievancesSetting, home), oldFile: expandHome(OLD_GRIEVANCES, home) }
}

/** The file's last path segment, for the lines a person reads. */
const fileName = (path: string): string => basename(path)

/** The file's entries and its text as read, or null text when it is missing; throws on a file that will not parse. */
const readGrievances = async ($: EngineInterface, path: string): Promise<{ entries: Record<string, unknown>[]; text: string | null }> => {
	if (!(await $.fs.exists(path))) return { entries: [], text: null }
	const text = await $.fs.read(path)
	const parsed: unknown = JSON.parse(text)
	if (!Array.isArray(parsed)) throw new Error('not a list')
	return { entries: parsed.filter(isRecord), text }
}

/**
 * The one-off move from the file this plugin kept before 1.0.0: when the
 * grievances file is missing and `cc-pain-points.json` exists, its text is
 * written to the grievances file byte for byte. No entry key ever carried the
 * old word, so nothing inside is rewritten. The old file is left where it is
 * (a mod can write but not delete), and an existing grievances file is never
 * touched. An old file that will not parse is reported, never moved, so the
 * caller can hold back until a person fixes it. A failed write throws.
 */
export type CarryOver = { kind: 'moved'; count: number } | { kind: 'unreadable' } | { kind: 'nothing' }

export const carryOverOldGrievances = async ($: EngineInterface): Promise<CarryOver> => {
	let paths: Awaited<ReturnType<typeof grievancePaths>>
	try {
		paths = await grievancePaths($)
	} catch {
		return { kind: 'nothing' }
	}
	if (paths.grievances === paths.oldFile) return { kind: 'nothing' }
	if (await $.fs.exists(paths.grievances)) return { kind: 'nothing' }
	if (!(await $.fs.exists(paths.oldFile))) return { kind: 'nothing' }
	const text = await $.fs.read(paths.oldFile)
	let count: number
	try {
		const parsed: unknown = JSON.parse(text)
		if (!Array.isArray(parsed)) return { kind: 'unreadable' }
		count = parsed.length
	} catch {
		// a file that will not parse stays where it is, for a person to fix
		return { kind: 'unreadable' }
	}
	// $.fs has no exclusive create, so look again straight before writing: a
	// session that carried over and logged in the meantime keeps its entry.
	if (await $.fs.exists(paths.grievances)) return { kind: 'nothing' }
	await $.fs.write(paths.grievances, text)
	return { kind: 'moved', count }
}

/** `n` and the noun, plural unless one. */
export const counted = (n: number, noun: string): string => `${n === 0 ? 'no' : n} ${noun}${n === 1 ? '' : 's'}`

/**
 * Append one grievance, unless an open entry already says the same thing.
 * Returns the one line the person sees; only a line beginning `logged `
 * means something was written.
 */
const logGrievance = async ($: EngineInterface, description: string): Promise<string> => {
	const text = description.trim()
	if (!text) return 'nothing to log.'
	let path: string
	try {
		path = (await grievancePaths($)).grievances
	} catch {
		return 'HOME is not set; nothing written.'
	}
	// A grievance written now would create the grievances file and leave the
	// old one's entries behind for good, so an unreadable old file holds it back.
	try {
		const carried = await carryOverOldGrievances($)
		if (carried.kind === 'unreadable') return 'cc-pain-points.json will not parse; fix it first so its grievances carry over. nothing written.'
	} catch (error) {
		return `could not carry over cc-pain-points.json: ${error instanceof Error ? error.message : String(error)}; nothing written.`
	}
	let first: Awaited<ReturnType<typeof readGrievances>>
	try {
		first = await readGrievances($, path)
	} catch {
		return `${fileName(path)} will not parse; nothing written. fix the file first.`
	}
	const open = first.entries.find(
		e => e.resolvedIn === null && typeof e.description === 'string' && e.description.trim().toLowerCase() === text.toLowerCase(),
	)
	if (open) return `already logged as ${String(open.id)}`
	const ids = new Set(first.entries.map(e => e.id))
	const base = slug(text)
	let id = base
	for (let n = 2; ids.has(id); n++) id = `${base}-${n}`
	const [err, b, repo, now] = await Promise.all([read($, lastError), read($, branch), read($, repoName), $.clock.now()])
	const source = [repo, b, err ? `last failed: ${err.tool}: ${err.text}` : '']
		.filter(part => part !== '')
		.join(' · ')
	// Another session may have written since the first read: a whole-file write
	// would drop its entry, so read again and give up when the file moved.
	let again: Awaited<ReturnType<typeof readGrievances>>
	try {
		again = await readGrievances($, path)
	} catch {
		return `${fileName(path)} changed under me and will not parse; nothing written.`
	}
	if (again.text !== first.text) return `${fileName(path)} changed while I read it; try again.`
	const entries = [...again.entries, { id, description: text, logged: localDate(now), sourceSession: source, resolvedIn: null, resolvedNoted: null }]
	await $.fs.write(path, JSON.stringify(entries, null, '\t') + '\n')
	return `logged ${id}`
}

const refreshBranch = async ($: EngineInterface): Promise<void> => {
	try {
		const ran = await $.process.run(['git', 'branch', '--show-current'], { timeoutMs: 5_000 })
		await update($, branch, () => (ran.exitCode === 0 ? ran.stdout.trim() : ''))
	} catch {
		await update($, branch, () => '')
	}
}

const isHeartbeat = (v: unknown): v is Heartbeat =>
	isRecord(v) && typeof v.id === 'string' && typeof v.at === 'number' && typeof v.repo === 'string' && typeof v.branch === 'string'

/**
 * Write this session's row to the shared store, under the id the session
 * has now (a /clear changes it with no session.start), and prune rows that
 * went stale. `force` skips the gap that throttles tool-event beats.
 */
const beat = async ($: EngineInterface, force = true): Promise<void> => {
	const now = await $.clock.now()
	const me = await read($, self)
	if (!force && now - me.beatAt < BEAT_GAP_MS) return
	let sessionId = me.sessionId
	let startedAt = me.startedAt
	try {
		sessionId = await $.session.id()
	} catch {
		// no id to write under
	}
	if (!sessionId) return
	if (sessionId !== me.sessionId) startedAt = now
	await update($, self, s => ({ ...s, sessionId, startedAt, beatAt: now }))
	const row: Heartbeat = {
		id: sessionId,
		cwd,
		repo: await read($, repoName),
		branch: await read($, branch),
		isWorking: me.isWorking,
		lastTool: me.lastTool,
		lastToolAt: me.lastToolAt,
		startedAt,
		at: now,
	}
	await $.store.set(UNDERLING_PREFIX + sessionId, row)
	for (const key of await $.store.keys()) {
		if (!key.startsWith(UNDERLING_PREFIX) || key === UNDERLING_PREFIX + sessionId) continue
		const other = await $.store.get(key)
		if (!isHeartbeat(other) || now - other.at > staleMs) await $.store.delete(key)
	}
}

/** Every underling's row in the store, this session first; never writes. */
const underlings = async ($: EngineInterface): Promise<Heartbeat[]> => {
	const me = await read($, self)
	const rows: Heartbeat[] = []
	for (const key of await $.store.keys()) {
		if (!key.startsWith(UNDERLING_PREFIX)) continue
		const row = await $.store.get(key)
		if (isHeartbeat(row)) rows.push(row)
	}
	return rows.sort((a, b) =>
		a.id === me.sessionId ? -1 : b.id === me.sessionId ? 1 : a.repo.localeCompare(b.repo) || a.branch.localeCompare(b.branch),
	)
}

const isPaneOpen = async ($: EngineInterface, id: string): Promise<boolean> => {
	try {
		return (await $.ui.panes()).some(p => p.id === id)
	} catch {
		return false
	}
}

export const register: Register = (on, options) => {
	if (options.enabled === false) return

	heartbeatMs = (typeof options.heartbeat_seconds === 'number' ? options.heartbeat_seconds : 15) * 1000
	staleMs = (typeof options.stale_minutes === 'number' ? options.stale_minutes : 10) * 60_000
	grievancesSetting = typeof options.grievances_file === 'string' && options.grievances_file.trim() !== '' ? options.grievances_file.trim() : DEFAULT_GRIEVANCES

	on('session.start', async ($, e, next) => {
		cwd = e.cwd
		// The old file's entries become grievances before anything reads them.
		try {
			const carried = await carryOverOldGrievances($)
			if (carried.kind === 'moved') $.ui.toast(`${counted(carried.count, 'grievance')} carried over from cc-pain-points.json, which you may now delete.`)
			if (carried.kind === 'unreadable') $.ui.toast('cc-pain-points.json will not parse; fix it and its grievances carry over at the next session.')
		} catch {
			// the move is retried at the next session or the next grievance
		}
		try {
			const repo = await $.session.repo()
			await update($, repoName, () => basename(repo?.root ?? e.cwd))
		} catch {
			await update($, repoName, () => basename(e.cwd))
		}
		await refreshBranch($)
		await beat($)
		$.clock.every(heartbeatMs, () => {
			void beat($)
		})
		$.clock.every(10_000, () => {
			void isPaneOpen($, MUSTER_PANE).then(open => {
				if (open) $.ui.invalidate('ui.render')
			})
		})
		// One try each: a taken name must not cost the other command.
		try {
			await $.command.register({
				name: 'log-grievance',
				description: 'Log a grievance with Claude Code itself, no turn: /log-grievance <what happened>, or alone for a box',
				argumentHint: '[what happened]',
				immediate: true,
			})
		} catch {
			// the name is taken
		}
		try {
			await $.command.register({
				name: 'muster-underlings',
				description: 'Every underling (Claude Code session) on this machine, and a line to one of them',
				immediate: true,
			})
		} catch {
			// the name is taken
		}
		return next(e)
	})

	on('session.end', async ($, e, next) => {
		await $.store.delete(UNDERLING_PREFIX + e.sessionId).catch(() => undefined)
		return next(e)
	})

	// A turn, not a submission: a prompt a hook drops starts nothing.
	on('turn.start', async ($, e, next) => {
		await update($, self, s => ({ ...s, isWorking: true }))
		await beat($)
		return next(e)
	})

	on('turn.complete', async ($, e, next) => {
		if (e.agentId) return next(e)
		await update($, self, s => ({ ...s, isWorking: false }))
		await beat($)
		return next(e)
	})

	on('tool.call', async ($, e, next) => {
		if (!e.agentId) {
			const now = await $.clock.now()
			await update($, self, s => ({ ...s, lastTool: e.tool, lastToolAt: now }))
		}
		const ran = await next(e)
		if (e.agentId) return ran
		if (ran.deny === undefined && ran.isError === true) {
			const text = typeof ran.text === 'string' ? ran.text : ''
			const me = await read($, self)
			await update($, lastError, () => ({ tool: e.tool, text: text.replace(/\s+/g, ' ').trim().slice(0, 160), at: me.lastToolAt }))
		}
		const movedBranch =
			e.tool === 'EnterWorktree' || e.tool === 'ExitWorktree' || (e.tool === 'Bash' && /\bgit\b[^|;&]*\b(checkout|switch|worktree)\b/.test(e.command))
		if (movedBranch) await refreshBranch($)
		await beat($, movedBranch)
		return ran
	})

	// Each pane command opens its pane, or closes it when it is already up: a
	// pane is a tab beside any other, /diff included, and the same word takes
	// it down again.
	on('command.run', { command: 'log-grievance' }, async ($, e) => {
		if (e.args.trim()) return { text: await logGrievance($, e.args) }
		if (await isPaneOpen($, GRIEVANCE_PANE)) await $.ui.close({ id: GRIEVANCE_PANE })
		else await $.ui.open({ id: GRIEVANCE_PANE, title: 'grievance', focus: true, closeOnEscape: true, rows: 7 })
		return {}
	})

	on('command.run', { command: 'muster-underlings' }, async $ => {
		if (await isPaneOpen($, MUSTER_PANE)) await $.ui.close({ id: MUSTER_PANE })
		else await $.ui.open({ id: MUSTER_PANE, title: 'underlings', focus: true, closeOnEscape: true, rows: 12 })
		return {}
	})

	on('ui.render', { component: 'Pane', requestId: GRIEVANCE_PANE }, async ($, e, next) => {
		if (e.surface !== 'terminal') return next(e)
		const { Box, Text, Input } = $.ui.resolve(e)
		const [err, b, repo, now] = await Promise.all([read($, lastError), read($, branch), read($, repoName), $.clock.now()])
		const context = [repo, b, err ? `last failed ${ago(now - err.at)} ago: ${err.tool}: ${err.text}` : 'nothing has failed yet']
			.filter(part => part !== '')
			.join(' · ')
		return (
			<Box flexDirection="column" rowGap={0}>
				<Text bold>log a grievance with Claude Code itself. no turn, no judgement.</Text>
				<Text dimColor wrap="truncate-end">
					{context}
				</Text>
				<Input
					key="grievance-text"
					label="grievance"
					placeholder="what happened, in your own words"
					submitLabel="log"
					autoFocus
					onSubmit={async value => {
						const line = await logGrievance($, value)
						$.ui.toast(line)
						// Only a write closes the box; a refusal keeps what was typed in view.
						if (line.startsWith('logged ')) await $.ui.close({ id: GRIEVANCE_PANE })
					}}
				/>
			</Box>
		)
	})

	on('ui.render', { component: 'Pane', requestId: MUSTER_PANE }, async ($, e, next) => {
		if (e.surface !== 'terminal') return next(e)
		const { Box, Text, Input, Button } = $.ui.resolve(e)
		const [rows, picked, me, now] = await Promise.all([underlings($), read($, selected), read($, self), $.clock.now()])
		const target = rows.find(r => r.id === picked && r.id !== me.sessionId)
		const width = Math.max(40, e.props.bodyColumns)
		return (
			<Box flexDirection="column" width={width}>
				{rows.length <= 1 && <Text dimColor>no other underlings.</Text>}
				{rows.map((row, i) => {
					const here = row.id === me.sessionId
					const quiet = now - row.at > 60_000
					const state = row.isWorking ? 'working' : `idle ${ago(now - Math.max(row.lastToolAt, row.startedAt))}`
					const label = `${here ? '◀' : ' '} ${row.repo} ${row.branch || '(no branch)'} · ${quiet ? `quiet ${ago(now - row.at)}` : state}${row.lastTool ? ` · ${row.lastTool}` : ''}`
					return (
						<Button
							key={`row-${row.id}`}
							label={label}
							plain
							{...(i < 9 ? { hotkey: String(i + 1) } : {})}
							dimColor={quiet}
							onPress={() => update($, selected, () => row.id)}
						/>
					)
				})}
				{target && (
					<Input
						key="underling-msg"
						label={`to ${target.repo}/${target.branch || target.id}`}
						placeholder="one line, delivered as a message"
						submitLabel="send"
						onSubmit={async value => {
							if (!value.trim()) return
							const sent = await $.session.send({ to: { sessionId: target.id }, text: value.trim() })
							$.ui.toast(sent.isDelivered ? `sent to ${target.repo}/${target.branch || target.id}` : `not delivered: ${sent.reason}`)
						}}
					/>
				)}
				<Text dimColor>you and {counted(Math.max(0, rows.length - 1), 'underling')} · a digit picks one · esc closes</Text>
			</Box>
		)
	})
}
