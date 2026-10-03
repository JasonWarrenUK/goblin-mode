// goblin-chrome: the hooks module. Every drawing reads the same state: the
// palette (38), the day (37), the frame by tier (36), the vitals (18) and
// the idle clock (28). The hint and the pills (27) and the question mask and
// heckles (29) read it too. One switch in the options turns the lot off.

import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, RenderElement } from 'claude-code'

import type { Day, Frame, Idle, Palette, Tier, Vitals } from '../types'
import { mix, shade } from './colour'
import { dayAt, parseSchedule, STYLE } from './day'
import {
	faceCells,
	FACE_COLUMNS,
	FACE_ROWS,
	HECKLES,
	meterCells,
	METER_COLUMNS,
	moodOf,
	POKE_LINES,
	voiceLine,
	type Expression,
} from './goblin'
import { goblinCase, pick, seconds } from './text'
import { CLOD, loadPalette } from './theme'
import { DEFAULT_TIER, frameFor, pinnedModel, tierOf } from './tier'

const PLUGIN = 'goblin-chrome'

const palette = atom({ plugin: 'goblin-chrome', key: 'palette' } as const, CLOD)
const day = atom({ plugin: 'goblin-chrome', key: 'day' } as const, {
	state: 'functional',
	from: 'functional',
	blend: 1,
	pill: null,
} as Day)
const frame = atom({ plugin: 'goblin-chrome', key: 'frame' } as const, frameFor(DEFAULT_TIER, null, CLOD))
const vitals = atom({ plugin: 'goblin-chrome', key: 'vitals' } as const, {
	context: 0,
	limit: 0,
	limitKind: '',
	tools: 0,
	errors: 0,
	turnMs: 0,
	bounces: 0,
} as Vitals)
const idle = atom({ plugin: 'goblin-chrome', key: 'idle' } as const, {
	lastPromptAt: 0,
	lastTurnEndAt: 0,
	sessionStartAt: 0,
	isWorking: false,
	draftSince: 0,
} as Idle)

/** The accent as the day colours it: faded from the previous state's shade over ten minutes. */
const accentOf = (p: Palette, d: Day): string =>
	mix(shade(p.accent, STYLE[d.from].shade), shade(p.accent, STYLE[d.state].shade), d.blend)

const MODE_PILLS: readonly [RegExp, string][] = [
	[/plan/i, 'sChEmInG'],
	[/accept/i, 'lEt It CoOk'],
	[/auto/i, 'uNsUpErViSeD'],
	[/bypass/i, 'nO rUlEs'],
	[/focus/i, 'hYpErFoCuS'],
	[/memory/i, 'fOrGeTtInG'],
]

export const pillFor = (mode: string): string => {
	for (const [re, pill] of MODE_PILLS) if (re.test(mode)) return pill
	return goblinCase(mode)
}

// Module-level because the validator holds `$` to top-level functions: these
// are the helpers every hook shares, and the variables they read are set by
// `register` from the options and by the hooks as the session goes.
let schedule = parseSchedule('')
let servedTier: Tier = DEFAULT_TIER
let pinnedTier: Tier | null = null
let lastYawnAt = 0

const refreshDay = async ($: EngineInterface): Promise<void> => {
	const now = await $.clock.now()
	const i = await read($, idle)
	const next = dayAt(schedule, new Date(now), i.sessionStartAt ? now - i.sessionStartAt : 0)
	await update($, day, () => next)
	const style = STYLE[next.state]
	if (style.yawnMs !== null && now - lastYawnAt > style.yawnMs && !i.isWorking) {
		lastYawnAt = now
		$.ui.toast(goblinCase('yawn.'))
	}
}

const refreshVitals = async ($: EngineInterface): Promise<void> => {
	try {
		const usage = await $.session.usage()
		let worst: { kind: string; percentUsed: number } | null = null
		for (const l of usage.rateLimits) if (worst === null || l.percentUsed > worst.percentUsed) worst = l
		const limit = worst
		await update($, vitals, v => ({
			...v,
			context: usage.context.percent ?? v.context,
			limit: limit?.percentUsed ?? 0,
			limitKind: limit?.kind ?? '',
		}))
	} catch {
		// headless, or no reading yet
	}
}

const refreshFrame = async ($: EngineInterface): Promise<void> => {
	const p = await read($, palette)
	await update($, frame, () => frameFor(servedTier, pinnedTier, p))
}

export const register: Register = (on, options) => {
	if (options.enabled === false) return

	schedule = parseSchedule(typeof options.schedule === 'string' ? options.schedule : '')
	servedTier = DEFAULT_TIER
	pinnedTier = null
	lastYawnAt = 0
	const wantedTheme = typeof options.theme === 'string' ? options.theme : ''
	const audio = options.audio === true

	on('session.start', async ($, e, next) => {
		const now = await $.clock.now()
		await update($, idle, i => ({ ...i, sessionStartAt: now, lastTurnEndAt: now }))
		const loaded = await loadPalette(
			{
				list: path => $.fs.list(path),
				read: path => $.fs.read(path),
				home: () => $.env.get('HOME'),
			},
			wantedTheme,
		)
		await update($, palette, () => loaded)
		await refreshFrame($)
		await refreshDay($)
		await refreshVitals($)
		$.clock.every(60_000, () => {
			void refreshDay($)
		})
		$.clock.every(30_000, () => {
			void refreshVitals($)
			void update($, idle, i => ({ ...i }))
		})
		return next(e)
	})

	on('classic.SessionStart', { source: ['clear', 'resume', 'fork'] }, async ($, e, next) => {
		const now = await $.clock.now()
		await update($, idle, i => ({ ...i, sessionStartAt: now, lastTurnEndAt: now, isWorking: false }))
		await update($, vitals, v => ({ ...v, tools: 0, errors: 0 }))
		await refreshFrame($)
		await refreshDay($)
		return next(e)
	})

	on('prompt.submit', async ($, e, next) => {
		const now = await $.clock.now()
		await update($, idle, i => ({ ...i, lastPromptAt: now, isWorking: true, draftSince: 0 }))
		await update($, vitals, v => ({ ...v, tools: 0, errors: 0 }))
		return next(e)
	})

	on('prompt.edit', async ($, e, next) => {
		const now = await $.clock.now()
		await update($, idle, i => (i.draftSince === 0 ? { ...i, draftSince: now } : i))
		return next(e)
	})

	on('tool.call', async ($, e, next) => {
		if (!e.agentId) await update($, vitals, v => ({ ...v, tools: v.tools + 1 }))
		const ran = await next(e)
		if (e.agentId) return ran
		if (ran.deny === undefined && ran.isError === true) {
			await update($, vitals, v => ({ ...v, errors: v.errors + 1 }))
		}
		if (e.tool === 'Bash' && /\bgit\b[^|;&]*\bcommit\b/.test(e.command) && ran.deny === undefined) {
			const text = typeof ran.text === 'string' ? ran.text : ''
			const out = ran.result as { stderr?: unknown } | undefined
			const stderr = typeof out?.stderr === 'string' ? out.stderr : ''
			if (/commit-msg:/.test(stderr) || /commit-msg:/.test(text)) {
				const v = await read($, vitals)
				const bounces = v.bounces + 1
				await update($, vitals, cur => ({ ...cur, bounces }))
				$.ui.toast(goblinCase(bounces === 1 ? HECKLES.bounce : HECKLES.bounceAgain(bounces)))
				if (audio) void $.audio.play({ asset: 'fx/cackle.wav' }).catch(() => undefined)
			}
		}
		return ran
	})

	on('turn.step', async function* ($, e, next) {
		const result = yield* next(e)
		if (!e.agentId && result.usage?.model) {
			const tier = tierOf(result.usage.model)
			if (tier !== servedTier) {
				servedTier = tier
				await refreshFrame($)
			}
		}
		return result
	})

	on('skill.prompt', async ($, e, next) => {
		try {
			const home = await $.env.get('HOME')
			const text = home ? await $.fs.read(`${home}/.claude/skills/${e.skill}/SKILL.md`) : ''
			const model = pinnedModel(text)
			pinnedTier = model ? tierOf(model) : null
		} catch {
			pinnedTier = null
		}
		await refreshFrame($)
		return next(e)
	})

	on('turn.complete', async ($, e, next) => {
		if (e.agentId) {
			$.ui.toast(goblinCase(HECKLES.minionBack(e.durationMs)))
			return next(e)
		}
		const now = await $.clock.now()
		await update($, idle, i => ({ ...i, lastTurnEndAt: now, isWorking: false }))
		await update($, vitals, v => ({ ...v, turnMs: e.durationMs }))
		if (pinnedTier !== null) {
			pinnedTier = null
			await refreshFrame($)
		}
		await refreshVitals($)
		return next(e)
	})

	on('session.compact', async ($, e, next) => {
		if (!e.agentId) $.ui.toast(goblinCase(HECKLES.compaction))
		return next(e)
	})

	on('command.run', { command: 'clear' }, async ($, e, next) => {
		$.ui.toast(HECKLES.clear)
		return next(e)
	})

	on('ui.message', async ($, e, next) => {
		const data = e.data as { poke?: unknown } | null
		if (data && data.poke === true) {
			const now = await $.clock.now()
			$.ui.toast(goblinCase(pick(POKE_LINES, Math.floor(now / 1000))))
			return {}
		}
		return next(e)
	})

	// The band (18 and 28): the idle goblin, the vitals metre and the voice line,
	// framed by tier and coloured by the day.
	on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
		if (e.props.hasSurvey || e.surface !== 'terminal') return next(e)
		const { Box, Text, Client, Raster } = $.ui.resolve(e)
		const [p, d, f, v, i] = await Promise.all([read($, palette), read($, day), read($, frame), read($, vitals), read($, idle)])
		const now = await $.clock.now()
		const mood = moodOf(v)
		const accent = accentOf(p, d)
		const since = Math.max(i.lastTurnEndAt, i.lastPromptAt, i.sessionStartAt)
		const idleMs = i.isWorking || since === 0 ? 0 : Math.max(0, now - since)
		const goblinWidth = Math.max(10, Math.min(24, e.props.bodyColumns - METER_COLUMNS - 48))
		const framed = e.props.maxRows >= 5
		return (
			<Box
				flexDirection="row"
				columnGap={1}
				width={e.props.bodyColumns}
				{...(framed ? { borderStyle: f.borderStyle, borderColor: f.borderColor, borderDimColor: f.borderDimColor, paddingX: 1 } : {})}
			>
				<Client
					key="goblin"
					module="./idle.tsx"
					width={goblinWidth}
					props={{
						mode: e.props.isWorking || i.isWorking ? 'working' : 'idle',
						idleMs,
						pace: STYLE[d.state].pace,
						startleAt: i.lastPromptAt,
						colour: accent,
						dim: p.inkMuted,
					}}
				/>
				<Raster key="meter" columns={METER_COLUMNS} rows={1} cells={meterCells(v.context, p)} />
				<Text color={mood === 'frantic' ? p.danger : mood === 'agitated' ? p.warn : p.inkMuted} wrap="truncate-end">
					{goblinCase(voiceLine(v, mood))}
				</Text>
				{framed && (
					<Text color={f.borderColor} dimColor={f.borderDimColor}>
						{f.rune}
					</Text>
				)}
			</Box>
		)
	})

	// The line that closes a turn (18).
	on('ui.render', { component: 'TurnDuration' }, async ($, e, next) => {
		if (e.surface !== 'terminal') return next(e)
		const { Text } = $.ui.resolve(e)
		const [p, v, d] = await Promise.all([read($, palette), read($, vitals), read($, day)])
		const bits = [`done. ${seconds(e.props.durationMs)}.`]
		if (v.tools > 0) bits.push(`took ${v.tools} thing${v.tools === 1 ? '' : 's'}.`)
		if (v.errors > 0) bits.push(`bit me ${v.errors === 1 ? 'once' : `${v.errors} times`}.`)
		return (
			<Text color={accentOf(p, d)} dimColor>
				{goblinCase(bits.join(' '))}
			</Text>
		)
	})

	// The footer pills (27).
	on('ui.render', { component: 'SessionMode' }, async ($, e, next) => {
		const d = await read($, day)
		const modes = e.props.modes.map(pillFor)
		if (d.pill) modes.push(d.pill)
		return next({ ...e, props: { ...e.props, modes } })
	})

	// The hint under the prompt (27): the engine's line stays live, the tail is ours.
	on('ui.render', { component: 'PromptHint' }, async ($, e, next) => {
		const [d, i] = await Promise.all([read($, day), read($, idle)])
		const now = await $.clock.now()
		const since = Math.max(i.lastTurnEndAt, i.lastPromptAt, i.sessionStartAt)
		const idleMs = since === 0 ? 0 : Math.max(0, now - since)
		let line: string
		if (e.props.isDraft && e.props.isWorking) line = 'queueing. patience.'
		else if (e.props.isDraft && i.draftSince > 0 && now - i.draftSince > 60_000) line = 'type or regret'
		else if (e.props.isDraft) line = pick(STYLE[d.state].hints, Math.floor(now / 60_000))
		else if (i.lastPromptAt === 0) line = 'say the thing'
		else if (!e.props.isWorking && idleMs > 2 * 60_000) line = 'still there?'
		else line = pick(STYLE[d.state].hints, Math.floor(now / 60_000))
		return next({ ...e, props: { ...e.props, tail: ` · ${goblinCase(line)}` } })
	})

	// The question mask (29): a face above the engine's own dialog, kept once.
	on('ui.render', { component: 'AskUserQuestion' }, async ($, e, next) => {
		const theirs = (await next(e)) as RenderElement
		if (e.surface !== 'terminal') return theirs
		const { Box, Text, Raster } = $.ui.resolve(e)
		const [p, d, f, v] = await Promise.all([read($, palette), read($, day), read($, frame), read($, vitals)])
		const questions = e.props.questions.length
		const expression: Expression =
			v.errors > 0 ? 'nervous' : d.state === 'prime' || d.state === 'feral' ? 'grin' : questions >= 3 ? 'folded' : 'expectant'
		const lines: Record<Expression, string> = {
			expectant: 'go on then.',
			nervous: 'it went wrong and now it wants you.',
			folded: 'an interrogation. lovely.',
			grin: 'oh, it wants something.',
		}
		return (
			<Box flexDirection="column">
				<Box flexDirection="row" columnGap={1} borderStyle={f.borderStyle} borderColor={f.borderColor} borderDimColor={f.borderDimColor} paddingX={1}>
					<Raster key="face" columns={FACE_COLUMNS} rows={FACE_ROWS} cells={faceCells(expression, p, STYLE[d.state].shade)} />
					<Text color={accentOf(p, d)}>{goblinCase(lines[expression])}</Text>
				</Box>
				{theirs}
			</Box>
		)
	})
}
