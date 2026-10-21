// The roadmap pane: `/ready` opens the whole ready set the CLI computes, in
// leverage order, with the claims in play and the milestones' progress, and
// runs again to close it. The ready set is split into subgroups (by dev unless
// this person chose otherwise), the body scrolls when it outgrows the pane,
// and the first nine rows take a digit; the rest are reached with Tab. A
// letter picks a claim in play; `c` claims a ready row after asking who
// (replacing any assignee it already had), `a` assigns or, left blank, clears
// an assignee without starting anything, `g` cycles what the set is grouped
// by, `s` asks which subgroups lead, `r` refreshes. An assignee is never
// inferred. The CLI is the plugin's own scripts/roadmap.py, the same file the
// skills run, so the pane needs python3 and nothing else. Nothing here edits
// roadmaps.json except through `claim` and `assign`.
//
// The grouping lives in the plugin's store, a file of this machine's, so each
// dev keeps their own without anything in the roadmap saying so.
//
// Colours are the engine's theme keys, never raw values: the pane follows
// whichever theme the person runs. A release tier takes one hue everywhere it
// appears (the tier row, its milestone chips, the task ids drawn from it).

import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Asking, Candidate, Claimed, GroupBy, Grouping, Milestone, Problem, Snapshot } from '../types'

const PANE = 'ready'
// Only the first nine ready rows take a digit; the rest are reached with Tab.
const DIGITS = 9
// Hotkeys for the claims in play; digits belong to the ready rows and c, a, g, s, r to the actions.
const IN_PLAY_KEYS = 'qwetyuiop'
const BAR_CELLS = 5
const TIER_LABEL_WIDTH = 11
const GROUP_BYS: readonly GroupBy[] = ['dev', 'milestone', 'tier', 'none']
const DEFAULT_GROUPING: Grouping = { by: 'dev', first: [] }
const UNASSIGNED = 'unassigned'

const snapshot = atom({ plugin: 'roadmap', key: 'snapshot' } as const, null as Snapshot | null)
const selected = atom({ plugin: 'roadmap', key: 'selected' } as const, null as string | null)
const asking = atom({ plugin: 'roadmap', key: 'asking' } as const, null as Asking | null)
const grouping = atom({ plugin: 'roadmap', key: 'grouping' } as const, null as Grouping | null)
const ordering = atom({ plugin: 'roadmap', key: 'ordering' } as const, false)

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

/** The dashes that finish a labelled rule across `columns`: `── Ready now ─────────`, with the label drawn apart so it can be bright. */
export const ruleTail = (label: string, columns: number): string => '─'.repeat(Math.max(2, columns - label.length - 4))

const isGroupBy = (v: unknown): v is GroupBy => typeof v === 'string' && (GROUP_BYS as readonly string[]).includes(v)

/** The grouping the store holds, read defensively; anything unset or odd falls back to grouping by dev in natural order. */
export const parseGrouping = (by: unknown, first: unknown): Grouping => ({
	by: isGroupBy(by) ? by : DEFAULT_GROUPING.by,
	first: Array.isArray(first) ? first.filter((s): s is string => typeof s === 'string' && s.trim() !== '').map(s => s.trim()) : [],
})

/** The next key in the cycle after `by`. */
export const nextGroupBy = (by: GroupBy): GroupBy => GROUP_BYS[(GROUP_BYS.indexOf(by) + 1) % GROUP_BYS.length] ?? 'dev'

/** The names typed into the order field: comma-separated, trimmed, blanks dropped. */
export const parseFirst = (text: string): string[] =>
	text
		.split(',')
		.map(s => s.trim())
		.filter(s => s !== '')

const milestoneNumber = (id: string): number => {
	const n = Number.parseInt(id.replace(/^\D+/, ''), 10)
	return Number.isFinite(n) ? n : Number.MAX_SAFE_INTEGER
}

export type Subgroup = { key: string; label: string; members: Candidate[] }

/**
 * The ready set split by `by`, each subgroup in leverage order. The subgroups
 * named in `first` lead in that order (matched case-insensitively on the
 * key, or on the label for a tier, whose key is only its index); the rest follow in natural order: devs alphabetically with the
 * unassigned last, milestones by number, tiers lowest first. Grouping by
 * nothing gives one unlabelled subgroup.
 */
export const subgroup = (candidates: readonly Candidate[], by: GroupBy, first: readonly string[]): Subgroup[] => {
	if (by === 'none') return [{ key: '', label: '', members: [...candidates] }]
	const groups = new Map<string, Subgroup>()
	for (const c of candidates) {
		const { key, label } =
			by === 'dev'
				? { key: c.assignee.trim() || UNASSIGNED, label: c.assignee.trim() || UNASSIGNED }
				: by === 'milestone'
					? { key: c.milestone, label: c.milestoneName ? `${c.milestone} ${c.milestoneName}` : c.milestone }
					: { key: String(c.tier), label: c.tierLabel || TIER_NAMES[c.tier] || `Tier ${c.tier + 1}` }
		const group = groups.get(key) ?? { key, label, members: [] }
		group.members.push(c)
		groups.set(key, group)
	}
	const natural = (a: Subgroup, b: Subgroup): number => {
		if (by === 'dev') {
			if (a.key === UNASSIGNED) return 1
			if (b.key === UNASSIGNED) return -1
			return a.key.localeCompare(b.key, undefined, { sensitivity: 'base' })
		}
		if (by === 'milestone') return milestoneNumber(a.key) - milestoneNumber(b.key) || a.key.localeCompare(b.key)
		return Number(a.key) - Number(b.key)
	}
	const wanted = first.map(s => s.toLowerCase())
	const rank = (g: Subgroup): number => {
		const i = wanted.indexOf((by === 'tier' ? g.label : g.key).toLowerCase())
		return i === -1 ? wanted.length : i
	}
	return [...groups.values()].sort((a, b) => rank(a) - rank(b) || natural(a, b))
}

/** The grouping this machine remembers, into the pane's state; absent, the default. */
const loadGrouping = async ($: EngineInterface): Promise<void> => {
	try {
		const [by, first] = await Promise.all([$.store.get('groupBy'), $.store.get('groupOrder')])
		await update($, grouping, () => parseGrouping(by, first))
	} catch {
		await update($, grouping, () => DEFAULT_GROUPING)
	}
}

/** Remembers a grouping on this machine and draws it. */
const saveGrouping = async ($: EngineInterface, next: Grouping): Promise<void> => {
	await update($, grouping, () => next)
	try {
		await Promise.all([$.store.set('groupBy', next.by), $.store.set('groupOrder', next.first)])
	} catch {
		$.ui.toast('the grouping could not be saved; it holds for this session')
	}
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
		// The person typed the name on purpose, so a different assignee gives way to it.
		const ran = await run($, ['claim', id, `--assignee=${who}`, '--reassign'])
		if (ran.exitCode !== 0) return reasonOf(ran, `claim ${id} refused`)
		return `claimed ${id} for ${who}. commit roadmaps.json when you are ready.`
	} catch {
		return 'the CLI could not run'
	}
}

/** Sets who will do a task without starting it; a blank name clears the assignee. */
const assign = async ($: EngineInterface, id: string, assignee: string): Promise<string> => {
	const who = assignee.trim()
	try {
		const ran = await run($, who ? ['assign', id, `--assignee=${who}`] : ['assign', id, '--unassign'])
		if (ran.exitCode !== 0) return reasonOf(ran, `assign ${id} refused`)
		return `${who ? `assigned ${id} to ${who}` : `cleared ${id}'s assignee`}. commit roadmaps.json when you are ready.`
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

/** A section heading: dim rule either side, the label at full strength so it reads. */
const heading = (ui: Ui, label: string, inner: number) => {
	const { Box, Text } = ui
	return (
		<Box flexDirection="row" columnGap={1}>
			<Text dimColor>──</Text>
			<Text bold>{label}</Text>
			<Text dimColor>{ruleTail(label, inner)}</Text>
		</Box>
	)
}

/** A subgroup's heading inside the ready set: who or what it is, and how many rows it holds. */
const subheading = (ui: Ui, group: Subgroup, by: GroupBy) => {
	const { Box, Text } = ui
	const colour = by === 'dev' ? (group.key === UNASSIGNED ? undefined : 'warning') : tierHue(group.members[0]?.tier ?? 0)
	return (
		<Box key={`sub-${group.key}`} flexDirection="row" columnGap={1} paddingLeft={1}>
			<Text color={colour} bold>
				{group.label}
			</Text>
			<Text dimColor>· {group.members.length}</Text>
		</Box>
	)
}

/** One ready task: hotkey (the first nine) and id on the first line with the description, the leverage signals beneath. */
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
					hotkey={i < DIGITS ? String(i + 1) : undefined}
					dimColor={picked !== null && !isPicked}
					label={c.id}
					onPress={async () => {
						await update($, selected, () => c.id)
						await update($, asking, () => null)
						await update($, ordering, () => false)
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

/** Claims in play: who holds which task, and since when. The first nine take a letter hotkey so an assignee can be handed over. */
const claimedRows = ($: EngineInterface, ui: Ui, claimed: readonly Claimed[], picked: string | null, inner: number) => {
	const { Box, Text, Button } = ui
	return claimed.map((c, i) => (
		<Box key={`claimed-${c.id}`} flexDirection="row" columnGap={1}>
			<Text color="warning">{picked === c.id ? '▶' : '●'}</Text>
			<Button
				key={`claimed-row-${c.id}`}
				plain
				hotkey={IN_PLAY_KEYS[i]}
				dimColor={picked !== null && picked !== c.id}
				label={c.id}
				onPress={async () => {
					await update($, selected, () => c.id)
					await update($, asking, () => null)
					await update($, ordering, () => false)
				}}
			/>
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
		await loadGrouping($)
		try {
			await $.command.register({
				name: 'ready',
				description: 'The roadmap ready set in a pane, or closes it: a digit picks, c claims, a assigns, g groups, s orders, r refreshes',
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
		// the whole ready set draws, so ask for the room; the body scrolls past what the layout spares
		await $.ui.open({ id: PANE, title: 'ready', focus: true, closeOnEscape: true, rows: 28 })
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
		const [snap, picked, ask, kept, isOrdering] = await Promise.all([read($, snapshot), read($, selected), read($, asking), read($, grouping), read($, ordering)])
		if (!snap) return <Text dimColor>reading the roadmap…</Text>
		const width = Math.max(40, e.props.bodyColumns)
		if (!snap.ok) return emptyState($, ui, snap, width - 1)
		// the header's frame and padding take four columns; every line inside it shares the measure
		const inner = width - 5
		const group = kept ?? DEFAULT_GROUPING
		const groups = subgroup(snap.candidates, group.by, group.first)
		// the digits follow the drawn order, so the subgroups a person puts first get 1 upwards
		const ordered = groups.flatMap(g => g.members)
		const pickedReady = ordered.find(c => c.id === picked) ?? null
		const pickedInPlay = pickedReady ? null : (snap.claimed.find(c => c.id === picked) ?? null)
		const current = pickedReady ?? pickedInPlay
		// a task already in play is past claiming; it can only change hands
		const claimable = pickedReady !== null
		const asked = current && ask?.id === current.id ? ask : null
		let index = 0
		return (
			<Box flexDirection="column" width={width} rowGap={1}>
				{header(ui, snap, inner)}
				<Box flexDirection="column" paddingX={1}>
					{heading(ui, `Ready now · ${snap.candidates.length}`, inner)}
					{ordered.length === 0 && <Text dimColor>nothing is ready. a blocker or a gate holds everything; /roadmap:review names it.</Text>}
					<Box flexDirection="column" rowGap={1}>
						{groups.map(g => (
							<Box key={`group-${g.key}`} flexDirection="column" rowGap={1}>
								{g.label !== '' && subheading(ui, g, group.by)}
								{g.members.map(c => taskRow($, ui, c, index++, picked, inner))}
							</Box>
						))}
					</Box>
				</Box>
				{snap.claimed.length > 0 && (
					<Box flexDirection="column" paddingX={1}>
						{heading(ui, `In play · ${snap.claimed.length}`, inner)}
						{claimedRows($, ui, snap.claimed, picked, inner)}
					</Box>
				)}
				<Box flexDirection="column" paddingX={1}>
					{ask === null && !isOrdering && (
						<Box flexDirection="row" columnGap={2} flexWrap="wrap">
							{current && claimable && (
								<Button key="claim" label="claim" hotkey="c" variant="primary" onPress={() => update($, asking, () => ({ id: current.id, mode: 'claim' }))} />
							)}
							{current && <Button key="assign" label="assign" hotkey="a" onPress={() => update($, asking, () => ({ id: current.id, mode: 'assign' }))} />}
							<Button key="group" label={`group: ${group.by}`} hotkey="g" onPress={() => saveGrouping($, { ...group, by: nextGroupBy(group.by) })} />
							<Button key="order" label={group.first.length > 0 ? `first: ${group.first.join(', ')}` : 'first: natural'} hotkey="s" onPress={() => update($, ordering, () => true)} />
							<Button key="refresh" label="refresh" hotkey="r" onPress={() => refresh($)} />
						</Box>
					)}
					{isOrdering && (
						<Input
							key="first"
							label="subgroups that lead, in order"
							placeholder="names or ids, comma-separated; blank for the natural order"
							value={group.first.join(', ')}
							submitLabel="order"
							autoFocus
							onSubmit={async value => {
								await saveGrouping($, { ...group, first: parseFirst(value) })
								await update($, ordering, () => false)
							}}
						/>
					)}
					{current && asked && (
						<Input
							key="assignee"
							label={asked.mode === 'claim' ? `who is doing ${current.id}` : `who will do ${current.id}`}
							placeholder={asked.mode === 'claim' ? 'a name; never inferred, never pre-filled' : 'a name, or blank to clear; never inferred'}
							submitLabel={asked.mode}
							autoFocus
							onSubmit={async value => {
								if (asked.mode === 'claim' && !value.trim()) {
									$.ui.toast('a claim needs a name.')
									return
								}
								$.ui.toast(asked.mode === 'claim' ? await claim($, current.id, value) : await assign($, current.id, value))
								await update($, asking, () => null)
								await refresh($)
							}}
						/>
					)}
					<Text dimColor>1-9 pick (tab past nine) · q-p in play · c claim · a assign · g group by · s order · r refresh · esc or /ready closes</Text>
				</Box>
			</Box>
		)
	})
}
