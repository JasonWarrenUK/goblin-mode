// The scout's pane: `/scout-waypoints` opens every ready waypoint the CLI
// computes, in leverage order, with the trails in play and the milestones'
// progress, and runs again to close it. The ready set is split into subgroups
// (by scout unless this person chose otherwise), the body scrolls when it
// outgrows the pane, and the first nine rows take a digit; the rest are
// reached with Tab. A letter picks a trail in play; `c` starts a trail on a
// ready row after asking which scout (replacing any assignee it already had),
// `a` assigns or, left blank, clears an assignee without starting anything,
// `g` cycles what the set is grouped by, `s` asks which subgroups lead, `r`
// refreshes. An assignee is never inferred. The CLI is the plugin's own
// scripts/roadbook.py, the same file the skills run, so the pane needs python3
// and nothing else. Nothing here edits roadbook.json except through `claim`
// and `assign`.
//
// The grouping lives in the plugin's store, a file of this machine's, so each
// scout keeps their own without anything in the roadbook saying so.
//
// Colours are the engine's theme keys, never raw values: the pane follows
// whichever theme the person runs. A release tier takes one hue everywhere it
// appears (the tier row, its milestone chips, the waypoint ids drawn from it).

import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Asking, Candidate, Claimed, GroupBy, Grouping, Milestone, Problem, Snapshot } from '../types'

const COMMAND = 'scout-waypoints'
const PANE = 'waypoints'
// Only the first nine ready rows take a digit; the rest are reached with Tab.
const DIGITS = 9
// Hotkeys for the trails in play; digits belong to the ready rows and c, a, g, s, r to the actions.
const IN_PLAY_KEYS = 'qwetyuiop'
const BAR_CELLS = 5
const TIER_LABEL_WIDTH = 11
const GROUP_BYS: readonly GroupBy[] = ['scout', 'milestone', 'tier', 'none']
const DEFAULT_GROUPING: Grouping = { by: 'scout', first: [] }
const UNASSIGNED = 'unassigned'

const snapshot = atom({ plugin: 'goblin-scout', key: 'snapshot' } as const, null as Snapshot | null)
const selected = atom({ plugin: 'goblin-scout', key: 'selected' } as const, null as string | null)
const asking = atom({ plugin: 'goblin-scout', key: 'asking' } as const, null as Asking | null)
const grouping = atom({ plugin: 'goblin-scout', key: 'grouping' } as const, null as Grouping | null)
const ordering = atom({ plugin: 'goblin-scout', key: 'ordering' } as const, false)

// Module-level because the validator holds `$` to top-level functions; only
// the CLI path lives here, which no drawing reads.
let cli = ''

type Ui = ReturnType<EngineInterface['ui']['resolve']>

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v)
const str = (v: unknown): string => (typeof v === 'string' ? v : typeof v === 'number' ? String(v) : '')
const num = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0)

// No cwd: the default is the session's working directory read per call, so a
// move into a worktree takes the pane with it and the CLI finds that branch's
// roadbook.json by walking up from there.
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

/** The grouping the store holds, read defensively; anything unset or odd falls back to grouping by scout in natural order. */
export const parseGrouping = (by: unknown, first: unknown): Grouping => ({
	by: isGroupBy(by) ? by : DEFAULT_GROUPING.by,
	first: Array.isArray(first) ? first.filter((s): s is string => typeof s === 'string' && s.trim() !== '').map(s => s.trim()) : [],
})

/** The next key in the cycle after `by`. */
export const nextGroupBy = (by: GroupBy): GroupBy => GROUP_BYS[(GROUP_BYS.indexOf(by) + 1) % GROUP_BYS.length] ?? 'scout'

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
 * key, or on the label for a tier, whose key is only its index); the rest
 * follow in natural order: scouts alphabetically with the unassigned last,
 * milestones by number, tiers lowest first. Grouping by nothing gives one
 * unlabelled subgroup.
 */
export const subgroup = (candidates: readonly Candidate[], by: GroupBy, first: readonly string[]): Subgroup[] => {
	if (by === 'none') return [{ key: '', label: '', members: [...candidates] }]
	const groups = new Map<string, Subgroup>()
	for (const c of candidates) {
		const { key, label } =
			by === 'scout'
				? { key: c.assignee.trim() || UNASSIGNED, label: c.assignee.trim() || UNASSIGNED }
				: by === 'milestone'
					? { key: c.milestone, label: c.milestoneName ? `${c.milestone} ${c.milestoneName}` : c.milestone }
					: { key: String(c.tier), label: c.tierLabel || TIER_NAMES[c.tier] || `Tier ${c.tier + 1}` }
		const group = groups.get(key) ?? { key, label, members: [] }
		group.members.push(c)
		groups.set(key, group)
	}
	const natural = (a: Subgroup, b: Subgroup): number => {
		if (by === 'scout') {
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

/** Milestones grouped by release tier, lowest tier first, each group in roadbook order. */
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
		if (detect.exitCode === 2) return void (await update($, snapshot, () => failed('missing', reasonOf(detect, 'no roadbook above this directory'))))
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
	if (!who) return "a trail needs a scout's name."
	try {
		// The person typed the name on purpose, so a different assignee gives way to it.
		const ran = await run($, ['claim', id, `--assignee=${who}`, '--reassign'])
		if (ran.exitCode !== 0) return reasonOf(ran, `trail on ${id} refused`)
		return `${who} is on the trail to ${id}. commit roadbook.json when you are ready.`
	} catch {
		return 'the CLI could not run'
	}
}

/** Sets which scout will take a waypoint without starting it; a blank name clears the assignee. */
const assign = async ($: EngineInterface, id: string, assignee: string): Promise<string> => {
	const who = assignee.trim()
	try {
		const ran = await run($, who ? ['assign', id, `--assignee=${who}`] : ['assign', id, '--unassign'])
		if (ran.exitCode !== 0) return reasonOf(ran, `assign ${id} refused`)
		return `${who ? `assigned ${id} to ${who}` : `cleared ${id}'s assignee`}. commit roadbook.json when you are ready.`
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

/** No roadbook to draw: a framed card that says why and what to do about it. */
const emptyState = ($: EngineInterface, ui: Ui, snap: Snapshot, width: number) => {
	const { Box, Text, Button } = ui
	const frame = snap.problem === 'broken' ? 'error' : 'subtle'
	const content =
		snap.problem === 'legacy'
			? {
					glyph: '◈',
					title: 'Old single-file roadmap',
					lead: 'This project keeps its plan in one Markdown file. The pane reads a roadbook.',
					steps: [step(ui, 1, 'Convert it', '/goblin-scout:rebind-roadbook'), step(ui, 2, 'Reopen', `/${COMMAND} or press r`)],
				}
			: snap.problem === 'broken'
				? {
						glyph: '✗',
						title: 'The roadbook would not load',
						lead: snap.reason,
						steps: [step(ui, 1, 'Check it', '/goblin-scout:tend-roadbook'), step(ui, 2, 'Then', 'r or refresh')],
					}
				: {
						glyph: '◇',
						title: 'No roadbook in this project',
						lead: 'Nothing at .claude/roadbook.json above this directory.',
						steps: [step(ui, 1, 'Start one', '/goblin-scout:start-roadbook'), step(ui, 2, 'Reopen', `/${COMMAND} or press r`)],
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
				{snap.problem === 'missing' && <Text dimColor>A roadbook holds your waypoints as a dependency graph. This pane then shows what is unblocked, what it unlocks and which scout is on which trail.</Text>}
				<Box flexDirection="column">{content.steps}</Box>
			</Box>
			<Box flexDirection="row" columnGap={2}>
				<Button key="refresh" label="refresh" hotkey="r" onPress={() => refresh($)} />
				<Text dimColor>esc or /{COMMAND} closes</Text>
			</Box>
		</Box>
	)
}

// ---------------------------------------------------------------- the wordmark
//
// The mod's short name in spaced capitals between two heavy rules, in the right of the header card:
//
//   ╺━━━━━━━╸
//   S C O U T
//   ╺━━━━━━━╸
//
// The component is goblin-warband's, pasted whole with only WORDMARK_WORD changed (one author for the pattern).
// To reuse it in another mod, copy WORDMARK_WORD, wordmark, packFacts, headerLayout and the header's
// drawing, and change only WORDMARK_WORD. Every glyph is one cell (Ghostty draws ╺ ━ ╸ as its own sprites).

export const WORDMARK_WORD = 'SCOUT'
/** The columns between the facts and the wordmark. */
export const WORDMARK_GAP = 2
/** Narrower than this for the facts, and the wordmark is left out: the facts matter more than the name. */
export const WORDMARK_MIN_FACTS = 24

/** The three lines of the wordmark, each exactly as wide as the spaced word. */
export const wordmark = (word: string): { rule: string; word: string; width: number } => {
	const spaced = [...word.toUpperCase()].join(' ')
	const width = [...spaced].length
	return { rule: `╺${'━'.repeat(Math.max(0, width - 2))}╸`, word: spaced, width }
}

const cells = (text: string): number => [...text].length

/** `text` cut to `width` cells, the last one an ellipsis when anything was cut. */
export const fit = (text: string, width: number): string => {
	const chars = [...text]
	if (chars.length <= width) return text
	return width <= 0 ? '' : `${chars.slice(0, width - 1).join('')}…`
}

/**
 * The facts laid over `lines` lines of `width` cells, in order, two spaces apart. A fact that does not fit on the
 * line it would start goes to the next line; one that fits on none is left out, and the facts after it still get
 * their turn. Nothing is cut mid-fact, so no line is ever wider than `width`.
 */
export const packFacts = (facts: readonly string[], width: number, lines: number): { lines: string[]; dropped: string[] } => {
	const out: string[] = Array.from({ length: lines }, () => '')
	const dropped: string[] = []
	let at = 0
	for (const fact of facts) {
		let placed = false
		for (let line = at; line < lines; line++) {
			const next = out[line] ? `${out[line]}  ${fact}` : fact
			if (cells(next) <= width) {
				out[line] = next
				at = line
				placed = true
				break
			}
		}
		if (!placed) dropped.push(fact)
	}
	return { lines: out, dropped }
}

/**
 * The header card's text, measured to its content width (the card's inner width less its border and padding):
 * the title line across the whole width, then three lines whose left holds the facts and whose right holds the
 * wordmark. The raid name is cut with an ellipsis to leave room for the role; the facts follow packFacts.
 * Below WORDMARK_MIN_FACTS cells for the facts the wordmark is dropped and the facts take the whole width.
 */
export const headerLayout = (name: string, role: string, facts: readonly string[], content: number, word = WORDMARK_WORD) => {
	const mark = wordmark(word)
	const withMark = content - mark.width - WORDMARK_GAP >= WORDMARK_MIN_FACTS
	const left = withMark ? content - mark.width - WORDMARK_GAP : content
	const title = { name: fit(name, Math.max(1, content - WORDMARK_GAP - cells(role))), role }
	// the first fact line sits beside the top rule, which carries no word: the facts start one line down, as in the sketch
	const packed = packFacts(facts, left, withMark ? 2 : 3)
	const rows = withMark
		? [
				{ left: '', right: mark.rule },
				{ left: packed.lines[0] ?? '', right: mark.word },
				{ left: packed.lines[1] ?? '', right: mark.rule },
			]
		: packed.lines.filter(Boolean).map(line => ({ left: line, right: '' }))
	return { title, rows, left, markWidth: withMark ? mark.width : 0, dropped: packed.dropped }
}

/** The cells of the phase's progress bar among the header's facts. */
const HEADER_BAR_CELLS = 10

/** The header's facts, in the order they are packed beside the wordmark. */
export const headerFacts = (snap: Snapshot): string[] => [
	`${bar(snap.donePct, HEADER_BAR_CELLS)} ${snap.donePct}%`,
	`${snap.candidates.length} ready`,
	`${snap.claimed.length} on the trail`,
	`${snap.milestones.length} milestone${snap.milestones.length === 1 ? '' : 's'}`,
]

/** The title line's right: how far along the phase is, in waypoints. */
export const headerRole = (snap: Snapshot): string => (snap.inScope > 0 ? `${snap.doneCount}/${snap.inScope} waypoints done` : '')

/** The phase line, the facts beside the wordmark and one row per release tier, each milestone a chip of its own progress. */
const header = (ui: Ui, snap: Snapshot, inner: number) => {
	const { Box, Text } = ui
	const tiers = groupByTier(snap.milestones)
	// the card is drawn inner + 4 wide; less its round border and paddingX 1 a side, its content is inner
	const layout = headerLayout(snap.phase || 'roadbook', headerRole(snap), headerFacts(snap), inner)
	return (
		<Box flexDirection="column" borderStyle="round" borderColor="subtle" paddingX={1} width={inner + 4}>
			<Box flexDirection="row" columnGap={WORDMARK_GAP}>
				<Text color="claude" weight="bold" wrap="truncate-end">
					{layout.title.name}
				</Text>
				<Text>{layout.title.role}</Text>
			</Box>
			{layout.rows.map((row, index) => (
				<Box key={`header-${index}`} flexDirection="row" columnGap={WORDMARK_GAP}>
					<Box width={layout.left}>
						<Text dimColor wrap="truncate-end">
							{row.left}
						</Text>
					</Box>
					{layout.markWidth ? (
						<Text color="claude" weight={index === 1 ? 'bold' : undefined}>
							{row.right}
						</Text>
					) : null}
				</Box>
			))}
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
	const colour = by === 'scout' ? (group.key === UNASSIGNED ? undefined : 'warning') : tierHue(group.members[0]?.tier ?? 0)
	return (
		<Box key={`sub-${group.key}`} flexDirection="row" columnGap={1} paddingLeft={1}>
			<Text color={colour} bold>
				{group.label}
			</Text>
			<Text dimColor>· {group.members.length}</Text>
		</Box>
	)
}

/** One ready waypoint: hotkey (the first nine) and id on the first line with the description, the leverage signals beneath. */
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

/** Trails in play: which scout is on which waypoint, and since when. The first nine take a letter hotkey so an assignee can be handed over. */
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
		cli = `${$.plugin.root}/scripts/roadbook.py`
		await loadGrouping($)
		try {
			await $.command.register({
				name: COMMAND,
				description: 'The ready waypoints of the roadbook in a pane, or closes it: a digit picks, c starts a trail, a assigns a scout, g groups, s orders, r refreshes',
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
	on('command.run', { command: COMMAND }, async $ => {
		if (await isPaneOpen($)) {
			await $.ui.close({ id: PANE })
			return {}
		}
		await refresh($)
		// the whole ready set draws, so ask for the room; the body scrolls past what the layout spares
		await $.ui.open({ id: PANE, title: 'waypoints', focus: true, closeOnEscape: true, rows: 28 })
		return {}
	})

	// A change to the roadbook by any route redraws the pane while it is open,
	// a 2.x project's roadmaps.json included until its first write moves it.
	on('tool.call', async ($, e, next) => {
		const ran = await next(e)
		if (e.agentId) return ran
		const touched =
			((e.tool === 'Edit' || e.tool === 'Write') && /(roadbook|roadmaps)(\.local)?\.json$/.test(e.file_path)) ||
			(e.tool === 'Bash' && /roadbook\.py|(roadbook|roadmaps)(\.local)?\.json/.test(e.command))
		if (touched && (await isPaneOpen($))) await refresh($)
		return ran
	})

	on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e, next) => {
		if (e.surface !== 'terminal') return next(e)
		const ui = $.ui.resolve(e)
		const { Box, Text, Button, Input } = ui
		const [snap, picked, ask, kept, isOrdering] = await Promise.all([read($, snapshot), read($, selected), read($, asking), read($, grouping), read($, ordering)])
		if (!snap) return <Text dimColor>reading the roadbook…</Text>
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
		// a waypoint already on a trail is past starting; it can only change hands
		const claimable = pickedReady !== null
		const asked = current && ask?.id === current.id ? ask : null
		let index = 0
		return (
			<Box flexDirection="column" width={width} rowGap={1}>
				{header(ui, snap, inner)}
				<Box flexDirection="column" paddingX={1}>
					{heading(ui, `Ready now · ${snap.candidates.length}`, inner)}
					{ordered.length === 0 && <Text dimColor>nothing is ready. a blocker or a gate holds everything; /goblin-scout:review-roadbook names it.</Text>}
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
						{heading(ui, `On the trail · ${snap.claimed.length}`, inner)}
						{claimedRows($, ui, snap.claimed, picked, inner)}
					</Box>
				)}
				<Box flexDirection="column" paddingX={1}>
					{ask === null && !isOrdering && (
						<Box flexDirection="row" columnGap={2} flexWrap="wrap">
							{current && claimable && (
								<Button key="claim" label="start trail" hotkey="c" variant="primary" onPress={() => update($, asking, () => ({ id: current.id, mode: 'claim' }))} />
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
							label={asked.mode === 'claim' ? `which scout is on ${current.id}` : `which scout will take ${current.id}`}
							placeholder={asked.mode === 'claim' ? 'a name; never inferred, never pre-filled' : 'a name, or blank to clear; never inferred'}
							submitLabel={asked.mode}
							autoFocus
							onSubmit={async value => {
								if (asked.mode === 'claim' && !value.trim()) {
									$.ui.toast("a trail needs a scout's name.")
									return
								}
								$.ui.toast(asked.mode === 'claim' ? await claim($, current.id, value) : await assign($, current.id, value))
								await update($, asking, () => null)
								await refresh($)
							}}
						/>
					)}
					<Text dimColor>1-9 pick (tab past nine) · q-p on the trail · c start trail · a assign · g group by · s order · r refresh · esc or /{COMMAND} closes</Text>
				</Box>
			</Box>
		)
	})
}
