// The roadmap pane: `/ready` opens the ready set the CLI computes, in
// leverage order, with the claims in play and the milestones' progress, and
// runs again to close it. A digit picks a row; `c` claims it after asking
// who (an assignee is never inferred), `r` refreshes. The CLI is this
// plugin's own scripts/roadmap.py, built from the same source as the roadmap
// plugin's, so the pane needs python3 and nothing else and a config that
// runs the roadmap skills from its own files enables the pane alone.
// Nothing here edits roadmaps.json except through `claim`.

import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Candidate, Claimed, Milestone, Snapshot } from '../types'

const PANE = 'ready'
const ROWS = 9

const snapshot = atom({ plugin: 'roadmap-pane', key: 'snapshot' } as const, null as Snapshot | null)
const selected = atom({ plugin: 'roadmap-pane', key: 'selected' } as const, null as string | null)
const asking = atom({ plugin: 'roadmap-pane', key: 'asking' } as const, null as string | null)

// Module-level because the validator holds `$` to top-level functions; only
// the CLI path lives here, which no drawing reads.
let cli = ''

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v)
const str = (v: unknown): string => (typeof v === 'string' ? v : typeof v === 'number' ? String(v) : '')
const num = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0)

// No cwd: the default is the session's working directory read per call, so a
// move into a worktree takes the pane with it and the CLI finds that branch's
// roadmaps.json by walking up from there.
const run = ($: EngineInterface, args: readonly string[]) => $.process.run(['python3', cli, ...args], { timeoutMs: 15_000 })

const firstLine = (text: string): string => text.trim().split('\n')[0] ?? ''

const lastLine = (text: string): string => text.trim().split('\n').pop() ?? ''

/** What the CLI said when it refused: its own `✗` line goes to stdout; a traceback's last line is the error. */
export const reasonOf = (ran: { stdout: string; stderr: string }, fallback: string): string => {
	if (/Traceback \(most recent call last\)/.test(ran.stderr)) return lastLine(ran.stderr) || fallback
	return firstLine(ran.stdout) || firstLine(ran.stderr) || fallback
}

const isPaneOpen = async ($: EngineInterface): Promise<boolean> => {
	try {
		return (await $.ui.panes()).some(p => p.id === PANE)
	} catch {
		return false
	}
}

/** Turn the CLI's two JSON documents into what the pane draws. */
export const parseSnapshot = (readyText: string, statsText: string, at: number): Snapshot => {
	const ready: unknown = JSON.parse(readyText)
	const stats: unknown = JSON.parse(statsText)
	if (!isRecord(ready) || !isRecord(stats)) throw new Error('not an object')
	const candidates: Candidate[] = (Array.isArray(ready.candidates) ? ready.candidates : []).filter(isRecord).map(c => ({
		id: str(c.id),
		description: str(c.description),
		milestone: str(c.milestone),
		milestoneName: str(c.milestoneName),
		milestoneDonePct: num(c.milestoneDonePct),
		transitiveUnblocks: num(c.transitiveUnblocks),
		isMilestoneSink: c.isMilestoneSink === true,
		assignee: str(c.assignee),
	}))
	const claimed: Claimed[] = (Array.isArray(ready.claimed) ? ready.claimed : []).filter(isRecord).map(c => ({
		id: str(c.id),
		description: str(c.description),
		assignee: str(c.assignee),
		started: str(c.started),
	}))
	const milestones: Milestone[] = (Array.isArray(stats.milestones) ? stats.milestones : []).filter(isRecord).map(m => ({
		id: str(m.id),
		name: str(m.name),
		donePct: num(m.donePct),
	}))
	return { ok: true, reason: '', phase: str(ready.phase) || str(stats.phase), donePct: num(stats.donePct), milestones, candidates, claimed, at }
}

const refresh = async ($: EngineInterface): Promise<void> => {
	const at = await $.clock.now()
	const failed = (reason: string): Snapshot => ({ ok: false, reason, phase: '', donePct: 0, milestones: [], candidates: [], claimed: [], at })
	try {
		const detect = await run($, ['detect'])
		if (detect.exitCode === 3) return void (await update($, snapshot, () => failed('old single-file roadmap: run /roadmap:migrate first')))
		if (detect.exitCode !== 0) return void (await update($, snapshot, () => failed(reasonOf(detect, 'no roadmap above this directory'))))
		const [ready, stats] = await Promise.all([run($, ['ready', '--json']), run($, ['stats', '--json'])])
		if (ready.exitCode !== 0 || stats.exitCode !== 0) {
			return void (await update($, snapshot, () => failed(reasonOf(ready.exitCode !== 0 ? ready : stats, 'the CLI refused'))))
		}
		const next = parseSnapshot(ready.stdout, stats.stdout, at)
		await update($, snapshot, () => next)
	} catch (error) {
		await update($, snapshot, () => failed(error instanceof Error && /ENOENT|not found/i.test(error.message) ? 'python3 is not on PATH' : 'the CLI could not run'))
	}
}

const claim = async ($: EngineInterface, id: string, assignee: string): Promise<string> => {
	const who = assignee.trim()
	if (!who) return 'a claim needs a name.'
	try {
		const ran = await run($, ['claim', id, '--assignee', who])
		if (ran.exitCode !== 0) return reasonOf(ran, `claim ${id} refused`)
		return `claimed ${id} for ${who}. commit roadmaps.json when you are ready.`
	} catch {
		return 'the CLI could not run'
	}
}

export const register: Register = on => {
	on('session.start', async ($, e, next) => {
		cli = `${$.plugin.root}/scripts/roadmap.py`
		try {
			await $.command.register({
				name: 'ready',
				description: 'The roadmap ready set in a pane, or closes it: a digit picks, c claims, r refreshes',
				immediate: true,
			})
		} catch {
			// the name is taken; nothing else to do
		}
		// Only while the pane is actually placed: an unplaced or closed pane spawns nothing.
		$.clock.every(120_000, () => {
			void isPaneOpen($).then(open => {
				if (open) void refresh($)
			})
		})
		return next(e)
	})

	// Open or close: the pane is a tab beside any other, /diff included, and
	// the same command takes it down again.
	on('command.run', { command: 'ready' }, async $ => {
		if (await isPaneOpen($)) {
			await $.ui.close({ id: PANE })
			return {}
		}
		await refresh($)
		await $.ui.open({ id: PANE, title: 'ready', focus: true, closeOnEscape: true, rows: 16 })
		return {}
	})

	// A change to the roadmap by any route redraws the pane while it is open.
	on('tool.call', async ($, e, next) => {
		const ran = await next(e)
		if (e.agentId) return ran
		const touched =
			((e.tool === 'Edit' || e.tool === 'Write') && /roadmaps\.json$/.test(e.file_path)) ||
			(e.tool === 'Bash' && /roadmap\.py|roadmaps\.json/.test(e.command))
		if (touched && (await isPaneOpen($))) await refresh($)
		return ran
	})

	on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e, next) => {
		if (e.surface !== 'terminal') return next(e)
		const { Box, Text, Button, Input } = $.ui.resolve(e)
		const [snap, picked, ask] = await Promise.all([read($, snapshot), read($, selected), read($, asking)])
		if (!snap) return <Text dimColor>reading the roadmap…</Text>
		if (!snap.ok) return <Text color="yellow">{snap.reason}</Text>
		const rows = snap.candidates.slice(0, ROWS)
		const current = rows.find(c => c.id === picked) ?? null
		const progress = snap.milestones.map(m => `${m.id} ${m.donePct}%`).join('  ')
		return (
			<Box flexDirection="column" width={Math.max(40, e.props.bodyColumns)}>
				<Text bold>
					{snap.phase || 'roadmap'} · {snap.donePct}% done{progress ? ` · ${progress}` : ''}
				</Text>
				{rows.length === 0 && <Text dimColor>nothing is ready. a blocker or a gate holds everything; /roadmap:review names it.</Text>}
				{rows.map((c, i) => (
					<Button
						key={`row-${c.id}`}
						plain
						hotkey={String(i + 1)}
						dimColor={picked !== null && picked !== c.id}
						label={`${picked === c.id ? '▶' : ' '} ${c.id}  ${c.description} · unblocks ${c.transitiveUnblocks} · ${c.milestone} ${c.milestoneDonePct}%${c.isMilestoneSink ? ' · completes it' : ''}${c.assignee ? ` · ${c.assignee}` : ''}`}
						onPress={async () => {
							await update($, selected, () => c.id)
							await update($, asking, () => null)
						}}
					/>
				))}
				{snap.candidates.length > ROWS && <Text dimColor>{snap.candidates.length - ROWS} more below the fold</Text>}
				{snap.claimed.map(c => (
					<Text dimColor>
						claimed {c.id} by {c.assignee || 'someone'} since {c.started || '?'}
					</Text>
				))}
				{current && ask === null && (
					<Box flexDirection="row" columnGap={2}>
						<Button key="claim" label="claim" hotkey="c" variant="primary" onPress={() => update($, asking, () => current.id)} />
						<Button key="refresh" label="refresh" hotkey="r" onPress={() => refresh($)} />
					</Box>
				)}
				{current && ask === current.id && (
					<Input
						key="assignee"
						label={`who is doing ${current.id}`}
						placeholder="a name; never inferred, never pre-filled"
						submitLabel="claim"
						autoFocus
						onSubmit={async value => {
							if (!value.trim()) {
								$.ui.toast('a claim needs a name.')
								return
							}
							$.ui.toast(await claim($, current.id, value))
							await update($, asking, () => null)
							await refresh($)
						}}
					/>
				)}
				<Text dimColor>a digit picks · c claim · r refresh · esc or /ready closes</Text>
			</Box>
		)
	})
}
