// goblin-chrome: the hooks module. Every drawing reads the same state: the
// palette (38), the day (37), the frame by tier (36), the vitals (18) and
// the idle clock (28). The hint (27) and the question mask and heckles (29)
// read it too. One switch in the options turns the lot off.

import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, RenderElement } from 'claude-code'

import type { Day, Frame, Idle, Palette, Run, Tier, Vitals } from '../types'
import { mix, shade } from './colour'
import { dayAt, parseSchedule, STYLE } from './day'
import { readMinionFace, readSkill } from './frontmatter'
import {
	DEFAULT_MINION,
	faceCells,
	FACE_COLUMNS,
	FACE_ROWS,
	HECKLES,
	POKE_LINES,
	propFor,
	type Expression,
} from './goblin'
import { goblinCase, pick, seconds } from './text'
import { CLOD, loadPalette, type Variant } from './theme'
import { bandRule, DEFAULT_TIER, frameFor, glyphsFor, tierOf } from './tier'

const PLUGIN = 'goblin-chrome'

const palette = atom({ plugin: 'goblin-chrome', key: 'palette' } as const, CLOD)
const day = atom({ plugin: 'goblin-chrome', key: 'day' } as const, {
	state: 'functional',
	from: 'functional',
	blend: 1,
} as Day)
const frame = atom({ plugin: 'goblin-chrome', key: 'frame' } as const, frameFor(DEFAULT_TIER, null, CLOD))
const vitals = atom({ plugin: 'goblin-chrome', key: 'vitals' } as const, {
	tools: 0,
	errors: 0,
	turnMs: 0,
	turnTools: 0,
	turnErrors: 0,
	bounces: 0,
} as Vitals)
const idle = atom({ plugin: 'goblin-chrome', key: 'idle' } as const, {
	lastPromptAt: 0,
	lastTurnEndAt: 0,
	sessionStartAt: 0,
	isWorking: false,
	draftSince: 0,
	saying: '',
	sayingUntil: 0,
} as Idle)
const NO_RUN: Run = { skill: null, family: null, spinner: [], minions: [] }
const run = atom({ plugin: 'goblin-chrome', key: 'run' } as const, NO_RUN)

/** How the spinner dresses a skill's word, matching the house `spinnerVerbs`. */
const spinnerWord = (word: string): string => `••• ${goblinCase(word)} •••`

/** The accent as the day colours it: faded from the previous state's shade over ten minutes. */
const accentOf = (p: Palette, d: Day): string =>
	mix(shade(p.accent, STYLE[d.from].shade), shade(p.accent, STYLE[d.state].shade), d.blend)

// Module-level because the validator holds `$` to top-level functions: these
// are the helpers every hook shares, and the variables they read are set by
// `register` from the options and by the hooks as the session goes. The tiers
// the frame depends on live in the `frame` atom, which survives a hot reload.
let schedule = parseSchedule('')
let lastYawnAt = 0

/** How long a line stays in the band's dialogue range. */
const SAY_MS = 6_000

/** The goblin speaks: the line shows in the band's dialogue range for a few seconds, then clears itself. */
const say = async ($: EngineInterface, line: string): Promise<void> => {
	const now = await $.clock.now()
	const until = now + SAY_MS
	await update($, idle, i => ({ ...i, saying: goblinCase(line), sayingUntil: until }))
	$.clock.after(SAY_MS, () => {
		void update($, idle, i => (i.sayingUntil === until ? { ...i, saying: '', sayingUntil: 0 } : i))
	})
}

const refreshDay = async ($: EngineInterface): Promise<void> => {
	const now = await $.clock.now()
	const i = await read($, idle)
	const next = dayAt(schedule, new Date(now), i.sessionStartAt ? now - i.sessionStartAt : 0)
	await update($, day, () => next)
	const style = STYLE[next.state]
	if (style.yawnMs !== null && now - lastYawnAt > style.yawnMs && !i.isWorking) {
		lastYawnAt = now
		await say($, 'yawn.')
	}
}

/** Redraw the frame from the atom's own tiers, with `patch` replacing whichever it names. */
const refreshFrame = async ($: EngineInterface, patch: { served?: Tier; pinned?: Tier | null } = {}): Promise<void> => {
	const p = await read($, palette)
	await update($, frame, current =>
		frameFor(patch.served ?? current.served, patch.pinned === undefined ? current.pinned : patch.pinned, p),
	)
}

export const register: Register = (on, options) => {
	if (options.enabled === false) return

	schedule = parseSchedule(typeof options.schedule === 'string' ? options.schedule : '')
	lastYawnAt = 0
	const wantedTheme = typeof options.theme === 'string' ? options.theme : ''
	const audio = options.audio === true

	on('session.start', async ($, e, next) => {
		const now = await $.clock.now()
		lastYawnAt = now
		await update($, idle, i => ({ ...i, sessionStartAt: now, lastTurnEndAt: now }))
		let variant: Variant = 'dark'
		try {
			const row = (await $.config.list()).find(r => r.key === 'theme')
			if (typeof row?.value === 'string' && /light/i.test(row.value)) variant = 'light'
		} catch {
			// no config to read; dark it is
		}
		const loaded = await loadPalette(
			{
				list: path => $.fs.list(path),
				read: path => $.fs.read(path),
				home: () => $.env.get('HOME'),
			},
			wantedTheme,
			variant,
		)
		await update($, palette, () => loaded)
		await refreshFrame($)
		await refreshDay($)
		$.clock.every(60_000, () => {
			void refreshDay($)
		})
		$.clock.every(30_000, () => {
			void update($, idle, i => ({ ...i }))
		})
		return next(e)
	})

	on('classic.SessionStart', { source: ['clear', 'resume', 'fork'] }, async ($, e, next) => {
		const now = await $.clock.now()
		await update($, idle, i => ({ ...i, sessionStartAt: now, lastTurnEndAt: now, isWorking: false }))
		await update($, vitals, v => ({ ...v, tools: 0, errors: 0 }))
		await update($, run, () => NO_RUN)
		await refreshFrame($)
		await refreshDay($)
		return next(e)
	})

	on('prompt.submit', async ($, e, next) => {
		const now = await $.clock.now()
		await update($, idle, i => ({ ...i, lastPromptAt: now, draftSince: 0 }))
		return next(e)
	})

	// A turn, not a submission: a dropped prompt never starts one.
	on('turn.start', async ($, e, next) => {
		await update($, idle, i => (i.isWorking ? i : { ...i, isWorking: true }))
		await update($, vitals, v => ({ ...v, tools: 0, errors: 0 }))
		return next(e)
	})

	// One write when a draft begins, one when it empties; nothing per keystroke.
	on('prompt.edit', async ($, e, next) => {
		const i = await read($, idle)
		const isEmpty = e.text.length - (e.end - e.start) + e.inputText.length === 0
		if (isEmpty && i.draftSince !== 0) await update($, idle, cur => ({ ...cur, draftSince: 0 }))
		else if (!isEmpty && i.draftSince === 0) {
			const now = await $.clock.now()
			await update($, idle, cur => ({ ...cur, draftSince: now }))
		}
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
				await say($, bounces === 1 ? HECKLES.bounce : HECKLES.bounceAgain(bounces))
				if (audio) void $.audio.play({ asset: 'fx/cackle.wav' }).catch(() => undefined)
			}
		}
		return ran
	})

	on('turn.step', async function* ($, e, next) {
		const result = yield* next(e)
		if (!e.agentId && result.usage?.model) {
			const tier = tierOf(result.usage.model)
			if (tier !== (await read($, frame)).served) await refreshFrame($, { served: tier })
		}
		return result
	})

	// The skill's frontmatter sets the frame's pin, the prop in the goblin's
	// hand and the spinner's words, all until the turn completes. Plugin skills
	// live elsewhere and read as nothing set.
	on('skill.prompt', async ($, e, next) => {
		let pinned: Tier | null = null
		let family: string | null = null
		let spinner: readonly string[] = []
		try {
			// Personal shadows project, as Claude Code resolves a skill of the same name.
			const home = await $.env.get('HOME')
			const personal = home ? await $.fs.read(`${home}/.claude/skills/${e.skill}/SKILL.md`).catch(() => '') : ''
			const text = personal || (await $.fs.read(`.claude/skills/${e.skill}/SKILL.md`))
			const fm = readSkill(text)
			pinned = fm.model ? tierOf(fm.model) : null
			family = fm.family
			spinner = fm.spinner
		} catch {
			pinned = null
		}
		await update($, run, r => ({ ...r, skill: e.skill, family, spinner }))
		await refreshFrame($, { pinned })
		return next(e)
	})

	// A subagent out is a minion in the band, wearing its agent file's face,
	// until its own turn completes. Personal agents shadow project ones.
	on('agent.spawn', async ($, e, next) => {
		const ran = await next(e)
		const agentId = (ran as { agentId?: unknown }).agentId
		if (typeof agentId !== 'string') return ran
		let face = DEFAULT_MINION
		try {
			const home = await $.env.get('HOME')
			const personal = home ? await $.fs.read(`${home}/.claude/agents/${e.subagentType}.md`).catch(() => '') : ''
			const text = personal || (await $.fs.read(`.claude/agents/${e.subagentType}.md`))
			face = readMinionFace(text) ?? DEFAULT_MINION
		} catch {
			face = DEFAULT_MINION
		}
		const r = await read($, run)
		const minions = [...r.minions.filter(m => m.agentId !== agentId), { agentId, type: e.subagentType, face }]
		await update($, run, cur => ({ ...cur, minions }))
		await say($, HECKLES.minionOut(minions.length))
		return ran
	})

	on('turn.complete', async ($, e, next) => {
		if (e.agentId) {
			const agentId = e.agentId
			await update($, run, r => ({ ...r, minions: r.minions.filter(m => m.agentId !== agentId) }))
			await say($, HECKLES.minionBack(e.durationMs))
			return next(e)
		}
		const now = await $.clock.now()
		await update($, idle, i => ({ ...i, lastTurnEndAt: now, isWorking: false }))
		await update($, vitals, v => ({ ...v, turnMs: e.durationMs, turnTools: v.tools, turnErrors: v.errors }))
		// The run ends with the turn: the pin, the prop, the spinner's words and any minion still out.
		await update($, run, () => NO_RUN)
		if ((await read($, frame)).pinned !== null) await refreshFrame($, { pinned: null })
		return next(e)
	})

	// The spinner's word while a skill with `goblin-spinner` runs (one word a
	// minute, in the house dress); a subagent's spinner keeps the engine's.
	on('ui.render', { component: 'Spinner' }, async ($, e, next) => {
		if (e.requestId !== 'main' && e.requestId !== '') return next(e)
		const r = await read($, run)
		if (r.spinner.length === 0) return next(e)
		const now = await $.clock.now()
		return next({ ...e, props: { ...e.props, word: spinnerWord(pick(r.spinner, Math.floor(now / 60_000))) } })
	})

	on('session.compact', async ($, e, next) => {
		if (!e.agentId) await say($, HECKLES.compaction)
		return next(e)
	})

	on('command.run', { command: 'clear' }, async ($, e, next) => {
		await say($, HECKLES.clear)
		return next(e)
	})

	on('ui.message', async ($, e, next) => {
		const data = e.data as { poke?: unknown } | null
		if (data && data.poke === true) {
			const now = await $.clock.now()
			await say($, pick(POKE_LINES, Math.floor(now / 1000)))
			return {}
		}
		return next(e)
	})

	// The band (18 and 28): three ranges split by dividers, the tier's rune, the
	// idle goblin and the goblin's dialogue, framed by tier and coloured by the day.
	on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
		if (e.props.hasSurvey || e.surface !== 'terminal') return next(e)
		const { Box, Text, Client } = $.ui.resolve(e)
		const [p, d, f, i, r] = await Promise.all([read($, palette), read($, day), read($, frame), read($, idle), read($, run)])
		const now = await $.clock.now()
		const accent = accentOf(p, d)
		const since = Math.max(i.lastTurnEndAt, i.lastPromptAt, i.sessionStartAt)
		const idleMs = i.isWorking || since === 0 ? 0 : Math.max(0, now - since)
		const framed = e.props.maxRows >= 5
		// The frame is drawn by hand so the dividers join the rules with tees: three ranges, each
		// padded by a cell either side, so the rune sits centred in a range as wide as itself plus
		// two (a mismatch such as `ᛊ→ᛟ` widens it). The room left for the goblin and its dialogue is
		// the band less that range, the dividers, the other paddings and, when framed, the two outer
		// edges. The dialogue takes under half, up to a long heckle's length.
		const g = glyphsFor(f.borderStyle)
		const runeRange = Array.from(f.rune).length + 2
		const room = Math.max(0, e.props.bodyColumns - (framed ? 2 : 0) - 2 - runeRange - 4)
		const sayingWidth = Math.min(42, Math.max(14, Math.floor(room * 0.45)))
		const goblinWidth = Math.max(10, room - sayingWidth)
		const ranges = [runeRange, goblinWidth + 2, sayingWidth + 2]
		const saying = now < i.sayingUntil ? i.saying : ''
		const bar = (
			<Text color={f.borderColor} dimColor={f.borderDimColor}>
				{g.vertical}
			</Text>
		)
		return (
			<Box flexDirection="column" width={e.props.bodyColumns}>
				{framed && (
					<Text color={f.borderColor} dimColor={f.borderDimColor} wrap="truncate-end">
						{bandRule(f.borderStyle, 'top', ranges)}
					</Text>
				)}
				<Box flexDirection="row" width={e.props.bodyColumns}>
					{framed && bar}
					<Box width={ranges[0]} paddingX={1}>
						<Text color={f.borderColor} dimColor={f.borderDimColor}>
							{f.rune}
						</Text>
					</Box>
					{bar}
					<Box width={ranges[1]} paddingX={1}>
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
								prop: propFor(r.family),
								minions: r.minions.map(m => m.face),
								minionColour: p.accent2,
							}}
						/>
					</Box>
					{bar}
					<Box width={ranges[2]} paddingX={1}>
						<Text color={accent} wrap="truncate-end">
							{saying}
						</Text>
					</Box>
					{framed && bar}
				</Box>
				{framed && (
					<Text color={f.borderColor} dimColor={f.borderDimColor} wrap="truncate-end">
						{bandRule(f.borderStyle, 'bottom', ranges)}
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
		// Only the row for the turn that just ended knows its counts; older rows keep the duration alone.
		if (e.props.durationMs === v.turnMs) {
			if (v.turnTools > 0) bits.push(`took ${v.turnTools} thing${v.turnTools === 1 ? '' : 's'}.`)
			if (v.turnErrors > 0) bits.push(`bit me ${v.turnErrors === 1 ? 'once' : `${v.turnErrors} times`}.`)
		}
		return (
			<Text color={accentOf(p, d)} dimColor>
				{goblinCase(bits.join(' '))}
			</Text>
		)
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
		return next({ ...e, props: { ...e.props, tail: goblinCase(line) } })
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
