// goblin-util: two mods for the machine. `/pain` logs friction with Claude
// Code itself into library/state/cc-pain-points.json without a turn, the
// context pre-filled from the last failed tool call. `/fleet` shows every
// session on the machine from a shared heartbeat in $.store and sends one a
// line. Both are immediate commands, so they work while Claude is busy.

import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Heartbeat, LastError } from '../types'

const PAIN_PANE = 'pain'
const FLEET_PANE = 'fleet'
const FLEET_PREFIX = 'fleet:'

const selected = atom({ plugin: 'goblin-util', key: 'selected' } as const, null as string | null)
const lastError = atom({ plugin: 'goblin-util', key: 'lastError' } as const, null as LastError | null)
const branch = atom({ plugin: 'goblin-util', key: 'branch' } as const, '')
const painDraft = atom({ plugin: 'goblin-util', key: 'painDraft' } as const, '')

// Module-level because the validator holds `$` to top-level functions; set
// by `register` from the options and by the hooks as the session goes.
let heartbeatMs = 15_000
let staleMs = 10 * 60_000
let sessionId = ''
let cwd = ''
let repoName = ''
let startedAt = 0
let isWorking = false
let lastTool = ''
let lastToolAt = 0

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null

const basename = (path: string): string => path.replace(/[\\/]+$/, '').split(/[\\/]/).pop() ?? path

/** A kebab-case id from a description, as the pain-points schema wants. */
export const slug = (text: string): string =>
	text
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-+|-+$/g, '')
		.slice(0, 48)
		.replace(/-+$/, '') || 'pain'

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

const painPath = async ($: EngineInterface): Promise<string> => {
	const home = await $.env.get('HOME')
	if (!home) throw new Error('HOME is not set')
	return `${home}/.claude/library/state/cc-pain-points.json`
}

const readPain = async ($: EngineInterface, path: string): Promise<Record<string, unknown>[]> => {
	try {
		const parsed: unknown = JSON.parse(await $.fs.read(path))
		return Array.isArray(parsed) ? parsed.filter(isRecord) : []
	} catch {
		return []
	}
}

/**
 * Append one pain point, unless an open entry already says the same thing.
 * Returns the one line the person sees.
 */
const logPain = async ($: EngineInterface, description: string): Promise<string> => {
	const text = description.trim()
	if (!text) return 'nothing to log.'
	const path = await painPath($)
	const entries = await readPain($, path)
	const open = entries.find(
		e => e.resolvedIn === null && typeof e.description === 'string' && e.description.trim().toLowerCase() === text.toLowerCase(),
	)
	if (open) return `already logged as ${String(open.id)}`
	const ids = new Set(entries.map(e => e.id))
	const base = slug(text)
	let id = base
	for (let n = 2; ids.has(id); n++) id = `${base}-${n}`
	const [err, b, now] = await Promise.all([read($, lastError), read($, branch), $.clock.now()])
	const source = [repoName, b, err ? `last failed: ${err.tool}: ${err.text}` : '']
		.filter(part => part !== '')
		.join(' · ')
	entries.push({ id, description: text, logged: localDate(now), sourceSession: source, resolvedIn: null, resolvedNoted: null })
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

/** Write this session's row to the shared store. */
const beat = async ($: EngineInterface): Promise<void> => {
	if (!sessionId) return
	const row: Heartbeat = {
		id: sessionId,
		cwd,
		repo: repoName,
		branch: await read($, branch),
		isWorking,
		lastTool,
		lastToolAt,
		startedAt,
		at: await $.clock.now(),
	}
	await $.store.set(FLEET_PREFIX + sessionId, row)
}

const isHeartbeat = (v: unknown): v is Heartbeat =>
	isRecord(v) && typeof v.id === 'string' && typeof v.at === 'number' && typeof v.repo === 'string' && typeof v.branch === 'string'

/** Every live row in the store, this session first, stale rows dropped on the way. */
const fleet = async ($: EngineInterface): Promise<Heartbeat[]> => {
	const now = await $.clock.now()
	const rows: Heartbeat[] = []
	for (const key of await $.store.keys()) {
		if (!key.startsWith(FLEET_PREFIX)) continue
		const row = await $.store.get(key)
		if (!isHeartbeat(row)) continue
		if (now - row.at > staleMs) {
			await $.store.delete(key)
			continue
		}
		rows.push(row)
	}
	return rows.sort((a, b) => (a.id === sessionId ? -1 : b.id === sessionId ? 1 : a.repo.localeCompare(b.repo) || a.branch.localeCompare(b.branch)))
}

export const register: Register = (on, options) => {
	heartbeatMs = (typeof options.heartbeat_seconds === 'number' ? options.heartbeat_seconds : 15) * 1000
	staleMs = (typeof options.stale_minutes === 'number' ? options.stale_minutes : 10) * 60_000

	on('session.start', async ($, e, next) => {
		const now = await $.clock.now()
		startedAt = now
		cwd = e.cwd
		try {
			sessionId = await $.session.id()
			const repo = await $.session.repo()
			repoName = basename(repo?.root ?? e.cwd)
		} catch {
			repoName = basename(e.cwd)
		}
		await refreshBranch($)
		await beat($)
		$.clock.every(heartbeatMs, () => {
			void beat($)
		})
		$.clock.every(10_000, () => {
			$.ui.invalidate('ui.render')
		})
		try {
			await $.command.register({
				name: 'pain',
				description: 'Log friction with Claude Code itself, no turn: /pain <what happened>, or alone for a box',
				argumentHint: '[what happened]',
				immediate: true,
			})
			await $.command.register({
				name: 'fleet',
				description: 'Every Claude Code session on this machine, and a line to one of them',
				immediate: true,
			})
		} catch {
			// a name already taken; the pane still works through the other command
		}
		return next(e)
	})

	on('session.end', async ($, e, next) => {
		if (sessionId) await $.store.delete(FLEET_PREFIX + sessionId).catch(() => undefined)
		return next(e)
	})

	on('prompt.submit', async ($, e, next) => {
		isWorking = true
		await beat($)
		return next(e)
	})

	on('turn.complete', async ($, e, next) => {
		if (e.agentId) return next(e)
		isWorking = false
		await beat($)
		return next(e)
	})

	on('tool.call', async ($, e, next) => {
		if (!e.agentId) {
			lastTool = e.tool
			lastToolAt = await $.clock.now()
		}
		const ran = await next(e)
		if (e.agentId) return ran
		if (ran.deny === undefined && ran.isError === true) {
			const text = typeof ran.text === 'string' ? ran.text : ''
			await update($, lastError, () => ({ tool: e.tool, text: text.replace(/\s+/g, ' ').trim().slice(0, 160), at: lastToolAt }))
		}
		if (e.tool === 'EnterWorktree' || e.tool === 'ExitWorktree' || (e.tool === 'Bash' && /\bgit\b[^|;&]*\b(checkout|switch|worktree)\b/.test(e.command))) {
			await refreshBranch($)
			await beat($)
		}
		return ran
	})

	on('command.run', { command: 'pain' }, async ($, e) => {
		if (e.args.trim()) return { text: await logPain($, e.args) }
		await update($, painDraft, () => '')
		await $.ui.open({ id: PAIN_PANE, title: 'pain', focus: true, closeOnEscape: true, rows: 7 })
		return {}
	})

	on('command.run', { command: 'fleet' }, async $ => {
		await $.ui.open({ id: FLEET_PANE, title: 'fleet', focus: true, closeOnEscape: true, rows: 12 })
		return {}
	})

	on('ui.render', { component: 'Pane', requestId: PAIN_PANE }, async ($, e, next) => {
		if (e.surface !== 'terminal') return next(e)
		const { Box, Text, Input } = $.ui.resolve(e)
		const [err, b, now] = await Promise.all([read($, lastError), read($, branch), $.clock.now()])
		const context = [repoName, b, err ? `last failed ${ago(now - err.at)} ago: ${err.tool}: ${err.text}` : 'nothing has failed yet']
			.filter(part => part !== '')
			.join(' · ')
		return (
			<Box flexDirection="column" rowGap={0}>
				<Text bold>log friction with Claude Code itself. no turn, no judgement.</Text>
				<Text dimColor wrap="truncate-end">
					{context}
				</Text>
				<Input
					key="pain-text"
					label="pain"
					placeholder="what happened, in your own words"
					value=""
					submitLabel="log"
					autoFocus
					onSubmit={async value => {
						const line = await logPain($, value)
						$.ui.toast(line)
						await $.ui.close({ id: PAIN_PANE })
					}}
				/>
			</Box>
		)
	})

	on('ui.render', { component: 'Pane', requestId: FLEET_PANE }, async ($, e, next) => {
		if (e.surface !== 'terminal') return next(e)
		const { Box, Text, Input, Button } = $.ui.resolve(e)
		const [rows, picked, now] = await Promise.all([fleet($), read($, selected), $.clock.now()])
		const target = rows.find(r => r.id === picked && r.id !== sessionId)
		const width = Math.max(40, e.props.bodyColumns)
		return (
			<Box flexDirection="column" width={width}>
				{rows.length <= 1 && <Text dimColor>only you.</Text>}
				{rows.map((row, i) => {
					const here = row.id === sessionId
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
						key="fleet-msg"
						label={`to ${target.repo}/${target.branch || target.id}`}
						placeholder="one line, delivered as a message"
						value=""
						submitLabel="send"
						onSubmit={async value => {
							if (!value.trim()) return
							const sent = await $.session.send({ to: { sessionId: target.id }, text: value.trim() })
							$.ui.toast(sent.isDelivered ? `sent to ${target.repo}/${target.branch || target.id}` : `not delivered: ${sent.reason}`)
						}}
					/>
				)}
				<Text dimColor>{rows.length} live · a digit picks a row · esc closes</Text>
			</Box>
		)
	})
}
