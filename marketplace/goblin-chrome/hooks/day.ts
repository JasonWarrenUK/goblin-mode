// The goblin's day (37): nine states on the local clock, read off a schedule
// the person tunes in /config, shifted for Friday afternoons, Sundays and a
// long session, with a ten-minute fade between states.

import type { Day, DayState } from '../types'

/** From most tired to most lively; the offsets walk this ladder. */
export const LADDER: readonly DayState[] = [
	'bed',
	'caught',
	'grumpy',
	'slump',
	'functional',
	'second',
	'perking',
	'prime',
	'feral',
]

export const DEFAULT_SCHEDULE = '04=bed,06=caught,08=grumpy,11=functional,14=slump,16=second,19=perking,22=prime,01=feral'

export type Slot = { minute: number; state: DayState }

const isState = (s: string): s is DayState => (LADDER as readonly string[]).includes(s)

/** `HH=state` pairs, sorted by hour; a malformed schedule falls back whole to the default. */
export const parseSchedule = (text: string): Slot[] => {
	const slots: Slot[] = []
	for (const part of text.split(',')) {
		const m = /^\s*(\d{1,2})(?::(\d{2}))?\s*=\s*([a-z]+)\s*$/.exec(part)
		if (!m || m[1] === undefined || m[3] === undefined || !isState(m[3])) {
			return text === DEFAULT_SCHEDULE ? [] : parseSchedule(DEFAULT_SCHEDULE)
		}
		const hour = Number(m[1])
		const minute = Number(m[2] ?? '0')
		if (hour > 23 || minute > 59) return text === DEFAULT_SCHEDULE ? [] : parseSchedule(DEFAULT_SCHEDULE)
		slots.push({ minute: hour * 60 + minute, state: m[3] })
	}
	return slots.sort((a, b) => a.minute - b.minute)
}

/** The slot in force at a minute of the day, and the one before it. */
export const slotAt = (slots: readonly Slot[], minuteOfDay: number): { now: Slot; before: Slot; since: number } => {
	const first = slots[0]
	if (!first) {
		const flat = { minute: 0, state: 'functional' as const }
		return { now: flat, before: flat, since: 600 }
	}
	let index = -1
	for (let i = 0; i < slots.length; i++) {
		const slot = slots[i]
		if (slot && slot.minute <= minuteOfDay) index = i
	}
	if (index === -1) index = slots.length - 1
	const now = slots[index] ?? first
	const before = slots[(index - 1 + slots.length) % slots.length] ?? first
	const since = (minuteOfDay - now.minute + 1440) % 1440
	return { now, before, since }
}

/** Move along the ladder, clamped at either end. */
export const shift = (state: DayState, delta: number): DayState => {
	const i = LADDER.indexOf(state)
	const j = Math.max(0, Math.min(LADDER.length - 1, i + delta))
	return LADDER[j] ?? state
}

/** The ladder offset for the calendar and the session's age. */
export const offset = (date: Date, sessionAgeMs: number): number => {
	let delta = 0
	if (date.getDay() === 5 && date.getHours() >= 16) delta += 1
	if (date.getDay() === 0) delta -= 1
	if (sessionAgeMs > 4 * 3_600_000) delta -= 1
	return delta
}

export const FADE_MINUTES = 10

export const dayAt = (slots: readonly Slot[], date: Date, sessionAgeMs: number): Day => {
	const { now, before, since } = slotAt(slots, date.getHours() * 60 + date.getMinutes())
	const delta = offset(date, sessionAgeMs)
	const state = shift(now.state, delta)
	return {
		state,
		from: shift(before.state, delta),
		blend: Math.min(1, since / FADE_MINUTES),
		pill: STYLE[state].pill,
	}
}

export type Pace = 'lie' | 'sway' | 'slow' | 'normal' | 'sit' | 'fast' | 'grin' | 'lively' | 'feral'

export type DayStyle = {
	/** Fraction towards white (positive) or black (negative) applied to the accent. */
	shade: number
	/** A label added to the footer's mode pills, or none. */
	pill: string | null
	/** What the hint line says when nothing more specific applies. */
	hints: readonly string[]
	/** How the idle goblin carries itself. */
	pace: Pace
	/** How often it yawns at you, or never. */
	yawnMs: number | null
}

export const STYLE: Record<DayState, DayStyle> = {
	bed: { shade: -0.55, pill: 'nO', hints: ['no.', 'go to bed', 'bed.'], pace: 'lie', yawnMs: null },
	caught: { shade: -0.3, pill: 'uGh', hints: ['...', 'what time is it', 'hm.'], pace: 'sway', yawnMs: 240_000 },
	grumpy: { shade: -0.15, pill: 'uGh', hints: ['what.', 'say it', 'hm'], pace: 'slow', yawnMs: null },
	functional: { shade: 0, pill: null, hints: ['say the thing', 'go on', 'well?'], pace: 'normal', yawnMs: null },
	slump: { shade: -0.1, pill: 'mEh', hints: ['sure', 'later', '*yawn*'], pace: 'sit', yawnMs: 300_000 },
	second: { shade: 0.05, pill: null, hints: ['right then', 'quicker', 'go on, say it'], pace: 'fast', yawnMs: null },
	perking: { shade: 0.1, pill: null, hints: ['oh good', 'tell me', 'yes?'], pace: 'grin', yawnMs: null },
	prime: { shade: 0.2, pill: 'pRiMe', hints: ['say the thing. properly.', 'you took your time', 'and?'], pace: 'lively', yawnMs: null },
	feral: { shade: 0.25, pill: 'fErAl', hints: ['heh', 'say it. SAY IT.', 'what could go wrong'], pace: 'feral', yawnMs: 180_000 },
}
