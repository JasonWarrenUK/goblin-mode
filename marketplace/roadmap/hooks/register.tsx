// The roadmap pane: `/ready` opens the ready set the CLI computes, in
// leverage order, with the claims in play and the milestones' progress, and
// runs again to close it. A digit picks a row; `c` claims it after asking
// who (an assignee is never inferred), `r` refreshes. The CLI is the
// plugin's own scripts/roadmap.py, the same file the skills run, so the pane
// needs python3 and nothing else. Nothing here edits roadmaps.json except
// through `claim`.
//
// Colours are the engine's theme keys, never raw values: the pane follows
// whichever theme the person runs. A release tier takes one hue everywhere it
// appears (the tier row, its milestone chips, the task ids drawn from it).

import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Candidate, Claimed, Milestone, Problem, Snapshot } from '../types'

const PANE = 'ready'
const ROWS = 9
const BAR_CELLS = 5
const TIER_LABEL_WIDTH = 11

const snapshot = atom({ plugin: 'roadmap', key: 'snapshot' } as const, null as Snapshot | null)
const selected = atom({ plugin: 'roadmap', key: 'selected' } as const, null as string | null)
const asking = atom({ plugin: 'roadmap', key: 'asking' } as const, null as string | null)

// Module-level because the validator holds `$` to top-level functions; only
// the CLI path lives here, which no drawing reads.
let cli = ''

type Ui = ReturnType<EngineInterface['ui']['resolve']>

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

const TIER_NAMES = ['Core', 'Secondary', 'Tertiary', 'Quaternary', 'Quinary']
const TIER_HUES = ['claude', 'suggestion', 'remember', 'permission'] as const

/** One hue per release tier, cycling past the fourth. */
export const tierHue = (tier: number): string => TIER_HUES[Math.max(0, tier) % TIER_HUES.length] ?? 'subtle'

/** A fixed-width bar: `███░░` for 60% in five cells. */
export const bar = (pct: number, cells: number): string => {
	const filled = Math.round((Math.max(0, Math.min(100, pct)) / 100) * cells)
	return '█'.repeat(filled) + '░'.repeat(cells - filled)
}

/** A labelled rule that fills `columns`: `── Ready now ─────────`. */
export const rule = (label: string, columns: number): string => {
	const head = `── ${label} `
	return head + '─'.repeat(Math.max(2, columns - head.length))
}

/** Milestones grouped by release tier, lowest tier first, each group in roadmap order. */
export const groupByTier = (milestones: readonly Milestone[]): { tier: number; label: string; milestones: Milestone[] }[] => {
	const tiers = [...new Set(milestones.map(m => m.tier))].sort((a, b) => a - b)
	return tiers.map(tier => {
		const members = milestones.filter(m => m.tier === tier)
		return { tier, label: members[0]?.tierLabel || TIER_NAMES[tier] || `Tier ${tier + 1}`, milestones: members }
	})
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
		tier: num(c.tier),
		tierLabel: str(c.tierLabel),
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
		tier: num(m.tier),
		tierLabel: str(m.tierLabel) || TIER_NAMES[num(m.tier)] || '',
		state: str(m.state),
	}))
	const byStatus = isRecord(stats.byStatus) ? stats.byStatus : {}
	return {
		ok: true,
		problem: 'none',
		reason: '',
		phase: str(ready.phase) || str(stats.phase),
		donePct: num(stats.donePct),
		doneCount: num(byStatus.done),
		inScope: num(stats.inScope),
		milestones,
		candidates,
		claimed,
		at,
	}
}

const refresh = async ($: EngineInterface): Promise<void> => {
	const at = await $.clock.now()
	const failed = (problem: Problem, reason: string): Snapshot => ({
		ok: false,
		problem,
		reason,
		phase: '',
		donePct: 0,
		doneCount: 0,
		inScope: 0,
		milestones: [],
		candidates: [],
		claimed: [],
		at,
	})
	try {
		const detect = await run($, ['detect'])
		if (detect.exitCode === 3) return void (await update($, snapshot, () => failed('legacy', 'old single-file roadmap')))
		if (detect.exitCode === 2) return void (await update($, snapshot, () => failed('missing', reasonOf(detect, 'no roadmap above this directory'))))
		if (detect.exitCode !== 0) return void (await update($, snapshot, () => failed('broken', reasonOf(detect, 'the CLI refused'))))
		const [ready, stats] = await Promise.all([run($, ['ready', '--json']), run($, ['stats', '--json'])])
		if (ready.exitCode !== 0 || stats.exitCode !== 0) {
			return void (await update($, snapshot, () => failed('broken', reasonOf(ready.exitCode !== 0 ? ready : stats, 'the CLI refused'))))
		}
		const next = parseSnapshot(ready.stdout, stats.stdout, at)
		await update($, snapshot, () => next)
	} catch (error) {
		await update($, snapshot, () => failed('broken', error instanceof Error && /ENOENT|not found/i.test(error.message) ? 'python3 is not on PATH' : 'the CLI could not run'))
	}
}

const claim = async ($: EngineInterface, id: string, assignee: string): Promise<string> => {
	const who = assignee.trim()
	if (!who) return 'a claim needs a name.'
	try {
		const ran = await run($, ['claim', id, `--assignee=${who}`])
		if (ran.exitCode !== 0) return reasonOf(ran, `claim ${id} refused`)
		return `claimed ${id} for ${who}. commit roadmaps.json when you are ready.`
	} catch {
		return 'the CLI could not run'
	}
}

/** One step of the empty state: a numbered line, what it does, the command that does it. */
const step = (ui: Ui, n: number, what: string, pointer: string) => {
	const { Box, Text } = ui
	const [command = '', alt = ''] = pointer.split(' or ')
	return (
		<Box key={`step-${n}`} flexDirection="row" columnGap={1} flexWrap="wrap">
			<Text color="suggestion" bold>
				{n}
			</Text>
			<Text>{what.padEnd(12)}</Text>
			<Text color="claude" bold>
				{command}
			</Text>
			{alt && <Text dimColor>or {alt}</Text>}
		</Box>
	)
}

/** No roadmap to draw: a framed card that says why and what to do about it. */
const emptyState = ($: EngineInterface, ui: Ui, snap: Snapshot, width: number) => {
	const { Box, Text, Button } = ui
	const frame = snap.problem === 'broken' ? 'error' : 'subtle'
	const content =
		snap.problem === 'legacy'
			? {
					glyph: '◈',
					title: 'Old roadmap format',
					lead: 'This roadmap is a single file. The pane reads the phase-array format.',
					steps: [step(ui, 1, 'Convert it', '/roadmap:migrate'), step(ui, 2, 'Reopen', '/ready or press r')],
				}
			: snap.problem === 'broken'
				? {
						glyph: '✗',
						title: 'The roadmap would not load',
						lead: snap.reason,
						steps: [step(ui, 1, 'Check it', '/roadmap:maintain'), step(ui, 2, 'Then', 'r or refresh')],
					}
				: {
						glyph: '◇',
						title: 'No roadmap in this project',
						lead: 'Nothing at .claude/roadmaps.json above this directory.',
						steps: [step(ui, 1, 'Start one', '/roadmap:create'), step(ui, 2, 'Reopen', '/ready or press r')],
					}
	return (
		<Box flexDirection="column" width={width} rowGap={1}>
			<Box flexDirection="column" borderStyle="round" borderColor={frame} paddingX={2} paddingY={1} rowGap={1}>
				<Box flexDirection="row" columnGap={1}>
					<Text color={frame === 'error' ? 'error' : 'claude'} bold>
						{content.glyph}
					</Text>
					<Text bold>{content.title}</Text>
				</Box>
				<Text color={snap.problem === 'broken' ? 'error' : undefined} dimColor={snap.problem !== 'broken'}>
					{content.lead}
				</Text>
				{snap.problem === 'missing' && <Text dimColor>A roadmap holds your tasks as a dependency graph. This pane then shows what is unblocked, what it unlocks and who has claimed what.</Text>}
				<Box flexDirection="column">{content.steps}</Box>
			</Box>
			<Box flexDirection="row" columnGap={2}>
				<Button key="refresh" label="refresh" hotkey="r" onPress={() => refresh($)} />
				<Text dimColor>esc or /ready closes</Text>
			</Box>
		</Box>
	)
}

/** The phase line and one row per release tier, each milestone a chip of its own progress. */
const header = (ui: Ui, snap: Snapshot, inner: number) => {
	const { Box, Text } = ui
	const tiers = groupByTier(snap.milestones)
	const barCells = Math.max(10, Math.min(24, inner - 40))
	return (
		<Box flexDirection="column" borderStyle="round" borderColor="subtle" paddingX={1} width={inner + 4}>
			<Box flexDirection="row" columnGap={2} flexWrap="wrap">
				<Text bold>{snap.phase || 'roadmap'}</Text>
				<Text color={snap.donePct >= 100 ? 'success' : 'claude'}>{bar(snap.donePct, barCells)}</Text>
				<Text bold>{snap.donePct}%</Text>
				{snap.inScope > 0 && (
					<Text dimColor>
						{snap.doneCount}/{snap.inScope} tasks
					</Text>
				)}
			</Box>
			{tiers.length > 0 && <Text dimColor>{'─'.repeat(Math.max(2, inner))}</Text>}
			{tiers.map(group => {
				const hue = tierHue(group.tier)
				const deferred = group.milestones.every(m => m.state === 'deferred')
				return (
					<Box key={`tier-${group.tier}`} flexDirection="row" columnGap={1}>
						<Box width={TIER_LABEL_WIDTH}>
							<Text color={hue} bold dimColor={deferred}>
								{`${group.tier === 0 ? '●' : '○'} ${group.label}`}
							</Text>
						</Box>
						<Box flexDirection="row" columnGap={2} flexWrap="wrap" flexGrow={1}>
							{group.milestones.map(m => (
								<Box key={`ms-${m.id}`} flexDirection="row" columnGap={1}>
									<Text color={hue} dimColor={m.state === 'deferred'} bold={m.donePct < 100 && m.donePct > 0}>
										{m.id}
									</Text>
									{m.donePct >= 100 ? (
										<Text color="success">✓</Text>
									) : (
										<Text color={m.donePct > 0 ? hue : 'subtle'} dimColor={m.donePct === 0}>
											{bar(m.donePct, BAR_CELLS)} {m.donePct}%
										</Text>
									)}
								</Box>
							))}
						</Box>
					</Box>
				)
			})}
		</Box>
	)
}

/** One ready task: hotkey and id on the first line with the description, the leverage signals beneath. */
const taskRow = ($: EngineInterface, ui: Ui, c: Candidate, i: number, picked: string | null, inner: number) => {
	const { Box, Text, Button } = ui
	const hue = tierHue(c.tier)
	const isPicked = picked === c.id
	const lead = 3 + 3 + c.id.length + 1
	return (
		<Box key={`task-${c.id}`} flexDirection="column">
			<Box flexDirection="row" columnGap={1}>
				<Text color={hue} bold>
					{isPicked ? '▶' : ' '}
				</Text>
				<Button
					key={`row-${c.id}`}
					plain
					hotkey={String(i + 1)}
					dimColor={picked !== null && !isPicked}
					label={c.id}
					onPress={async () => {
						await update($, selected, () => c.id)
						await update($, asking, () => null)
					}}
				/>
				<Box width={Math.max(10, inner - lead)}>
					<Text bold={isPicked} dimColor={picked !== null && !isPicked} wrap={isPicked ? 'wrap' : 'truncate-end'}>
						{c.description}
					</Text>
				</Box>
			</Box>
			<Box flexDirection="row" flexWrap="wrap" paddingLeft={5} columnGap={1}>
				<Text dimColor>↳</Text>
				<Text color={hue}>unblocks {c.transitiveUnblocks}</Text>
				<Text dimColor>·</Text>
				<Text dimColor>
					{c.milestone} {c.milestoneName ? `${c.milestoneName} ` : ''}
					{c.milestoneDonePct}%
				</Text>
				{c.isMilestoneSink && <Text color="success">completes it</Text>}
				{c.assignee && <Text color="warning">● {c.assignee}</Text>}
			</Box>
		</Box>
	)
}

/** Claims in play: who holds which task, and since when. */
const claimedRows = (ui: Ui, claimed: readonly Claimed[], inner: number) => {
	const { Box, Text } = ui
	return claimed.map(c => (
		<Box key={`claimed-${c.id}`} flexDirection="row" columnGap={1}>
			<Text color="warning">●</Text>
			<Text bold>{c.id}</Text>
			<Text color="warning">{c.assignee || 'someone'}</Text>
			<Text dimColor>since {c.started || '?'}</Text>
			<Box width={Math.max(8, inner - c.id.length - (c.assignee || 'someone').length - (c.started || '?').length - 14)}>
				<Text dimColor wrap="truncate-end">
					{c.description}
				</Text>
			</Box>
		</Box>
	))
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
		const ui = $.ui.resolve(e)
		const { Box, Text, Button, Input } = ui
		const [snap, picked, ask] = await Promise.all([read($, snapshot), read($, selected), read($, asking)])
		if (!snap) return <Text dimColor>reading the roadmap…</Text>
		const width = Math.max(40, e.props.bodyColumns)
		if (!snap.ok) return emptyState($, ui, snap, width - 1)
		// the header's frame and padding take four columns; every line inside it shares the measure
		const inner = width - 5
		const rows = snap.candidates.slice(0, ROWS)
		const current = rows.find(c => c.id === picked) ?? null
		return (
			<Box flexDirection="column" width={width} rowGap={1}>
				{header(ui, snap, inner)}
				<Box flexDirection="column" paddingX={1}>
					<Text color="subtle">{rule(`Ready now · ${snap.candidates.length}`, inner)}</Text>
					{rows.length === 0 && <Text dimColor>nothing is ready. a blocker or a gate holds everything; /roadmap:review names it.</Text>}
					<Box flexDirection="column" rowGap={1}>
						{rows.map((c, i) => taskRow($, ui, c, i, picked, inner))}
					</Box>
					{snap.candidates.length > ROWS && <Text dimColor>+{snap.candidates.length - ROWS} more below the fold</Text>}
				</Box>
				{snap.claimed.length > 0 && (
					<Box flexDirection="column" paddingX={1}>
						<Text color="subtle">{rule(`In play · ${snap.claimed.length}`, inner)}</Text>
						{claimedRows(ui, snap.claimed, inner)}
					</Box>
				)}
				<Box flexDirection="column" paddingX={1}>
					{ask === null && (
						<Box flexDirection="row" columnGap={2}>
							{current && <Button key="claim" label="claim" hotkey="c" variant="primary" onPress={() => update($, asking, () => current.id)} />}
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
					<Text dimColor>1-9 pick · c claim · r refresh · esc or /ready closes</Text>
				</Box>
			</Box>
		)
	})
}
